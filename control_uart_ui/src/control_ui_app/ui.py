from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
import tkinter as tk
from tkinter import messagebox, ttk

from .models import BridgeState
from .session import SERIAL_IMPORT_ERROR, SerialBridgeSession, SerialPortInfo
from .storage import apply_saved_state, save_state

PREDEFINED_TEST_FRAMES: list[tuple[str, str]] = [
    ("Heartbeat HF->AG", "HFPB1|HBT|HF|AG|01AF22C0|00000001|--------|N|00|100|-|0000"),
    ("Heartbeat AG->HF", "HFPB1|HBT|AG|HF|77B91011|00000001|--------|N|00|110|-|0000"),
    (
        "Unsolicited CLIP HF->AG",
        "HFPB1|HFP|HF|AG|01AF22C0|0000002A|--------|C|00|1244332|eyJtc2dfdmVyIjoxLCJkaXIiOiJIRl9UT19BRyIsImtpbmQiOiJVTlNPTCIsImxpbmUiOiIrQ0xJUDogXCIrMTM0NzQwNzA5NThcIiwxNDUifQ|A1B2",
    ),
    (
        "Critical command AG->HF",
        "HFPB1|HFP|AG|HF|77B91011|00000010|--------|C|00|553991|eyJtc2dfdmVyIjoxLCJkaXIiOiJBR19UT19IRiIsImtpbmQiOiJDTUQiLCJsaW5lIjoiQVQrQ0hVUCJ9|C3D4",
    ),
]


@dataclass
class SideWidgets:
    port_var: tk.StringVar
    status_var: tk.StringVar
    stats_var: tk.StringVar
    open_button: ttk.Button
    close_button: ttk.Button
    port_combo: ttk.Combobox


class BridgeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("NavTool UART Relay (Phase 1)")
        self.root.geometry("1400x900")

        self.state = BridgeState()
        apply_saved_state(self.state)

        self._event_queue: Queue[tuple[str, str, dict]] = Queue()
        self._port_options: list[str] = []
        self._port_map: dict[str, SerialPortInfo] = {}
        self._port_label_to_device: dict[str, str] = {}
        self._side_widgets: dict[str, SideWidgets] = {}
        self._relay_enabled = tk.BooleanVar(value=True)
        self._last_test_report = "No test has been run yet."

        self.phone_session = SerialBridgeSession(self.state.phone_session, self._make_event_sink("phone"))
        self.car_session = SerialBridgeSession(self.state.car_session, self._make_event_sink("car"))
        self.sessions = {"phone": self.phone_session, "car": self.car_session}

        self.summary_var = tk.StringVar(value="Ready")

        self._build_ui()
        self.refresh_ports()
        self._refresh_all_views()
        self.root.after(100, self._drain_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if not SerialBridgeSession.serial_supported():
            messagebox.showwarning(
                "pyserial missing",
                "pyserial is not installed. Serial control is disabled.\n\n"
                f"Import error: {SERIAL_IMPORT_ERROR}",
            )

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Summary:").pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.summary_var).pack(side=tk.LEFT, padx=(6, 10))
        ttk.Button(top, text="Refresh Ports", command=self.refresh_ports).pack(side=tk.LEFT)
        ttk.Button(top, text="Clear Trace", command=self.clear_trace).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Checkbutton(top, text="Relay Enabled", variable=self._relay_enabled).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(top, text="Send Test HF->AG", command=lambda: self._open_inject_popup("HF->AG")).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(top, text="Send Test AG->HF", command=lambda: self._open_inject_popup("AG->HF")).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(top, text="Run Auto Relay Test", command=self._run_auto_relay_test).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(top, text="Run Pass Scenario", command=self._run_pass_scenario).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(top, text="Run Fail Scenario", command=self._run_fail_scenario).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(top, text="Show Last Test Report", command=self._show_last_test_report).pack(side=tk.LEFT, padx=(8, 0))

        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        phone = ttk.Frame(body, padding=8)
        car = ttk.Frame(body, padding=8)
        trace = ttk.Frame(body, padding=8)
        body.add(phone, weight=1)
        body.add(car, weight=1)
        body.add(trace, weight=2)

        self._side_widgets["phone"] = self._build_side(phone, "phone", "Phone Side")
        self._side_widgets["car"] = self._build_side(car, "car", "Car Side")

        trace_box = ttk.LabelFrame(trace, text="Raw Relay Trace", padding=8)
        trace_box.pack(fill=tk.BOTH, expand=True)
        self.trace_text = tk.Text(trace_box, wrap="word")
        self.trace_text.pack(fill=tk.BOTH, expand=True)
        self.trace_text.configure(state=tk.DISABLED)

    def _build_side(self, parent: ttk.Frame, side: str, title: str) -> SideWidgets:
        info = self.sessions[side].info
        frame = ttk.LabelFrame(parent, text=title, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        port_var = tk.StringVar(value=info.port)
        status_var = tk.StringVar(value="Closed")
        stats_var = tk.StringVar(value="RX=0 TX=0 ERR=0")

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(row, text="Port").pack(side=tk.LEFT)
        port_combo = ttk.Combobox(row, textvariable=port_var, state="normal", width=36)
        port_combo.pack(side=tk.LEFT, padx=(6, 6))
        port_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_port_changed(side))
        port_combo.bind("<FocusOut>", lambda _e: self._on_port_changed(side))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(0, 6))
        open_button = ttk.Button(buttons, text="Open Port", command=lambda: self.open_session(side))
        open_button.pack(side=tk.LEFT)
        close_button = ttk.Button(buttons, text="Close Port", command=lambda: self.close_session(side))
        close_button.pack(side=tk.LEFT, padx=(8, 0))

        self._label_value(frame, "Status", status_var)
        self._label_value(frame, "Relay Stats", stats_var)

        return SideWidgets(
            port_var=port_var,
            status_var=status_var,
            stats_var=stats_var,
            open_button=open_button,
            close_button=close_button,
            port_combo=port_combo,
        )

    def _label_value(self, parent: ttk.Frame, label: str, var: tk.StringVar) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X)
        ttk.Label(row, text=f"{label}:", width=12).pack(side=tk.LEFT)
        ttk.Label(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def clear_trace(self) -> None:
        self.trace_text.configure(state=tk.NORMAL)
        self.trace_text.delete("1.0", tk.END)
        self.trace_text.configure(state=tk.DISABLED)

    def _append_trace(self, text: str) -> None:
        self.trace_text.configure(state=tk.NORMAL)
        self.trace_text.insert(tk.END, text)
        self.trace_text.see(tk.END)
        self.trace_text.configure(state=tk.DISABLED)

    def _trace(self, source: str, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._append_trace(f"[{ts}] [{source}] {message}\n")

    def refresh_ports(self) -> None:
        ports = SerialBridgeSession.list_ports()
        self._port_map.clear()
        self._port_label_to_device.clear()
        labels: list[str] = []
        for p in ports:
            label = p.dropdown_label()
            labels.append(label)
            self._port_map[p.device.upper()] = p
            self._port_label_to_device[label] = p.device
        self._port_options = labels
        for side, widgets in self._side_widgets.items():
            widgets.port_combo["values"] = self._port_options
            self._sync_port_var_from_device(side)
        self._refresh_all_views()

    def _on_port_changed(self, side: str) -> None:
        widgets = self._side_widgets[side]
        selected = widgets.port_var.get().strip()
        if not selected:
            return
        resolved = self._port_label_to_device.get(selected, selected)
        self.sessions[side].info.port = resolved
        widgets.port_var.set(resolved)
        self._refresh_side(side)
        self._update_summary()

    def _sync_port_var_from_device(self, side: str) -> None:
        info = self.sessions[side].info
        widgets = self._side_widgets[side]
        device = info.port.strip()
        if not device:
            widgets.port_var.set("")
            return
        p = self._port_map.get(device.upper())
        widgets.port_var.set(p.dropdown_label() if p else device)

    def open_session(self, side: str) -> None:
        info = self.sessions[side].info
        self._on_port_changed(side)
        if not info.port:
            messagebox.showwarning("Port required", f"Select a COM port for {info.label}.")
            return
        self.sessions[side].open(info.port)
        self._refresh_all_views()

    def close_session(self, side: str) -> None:
        self.sessions[side].close()
        self._refresh_all_views()

    def _make_event_sink(self, side: str):
        def _sink(kind: str, payload: dict) -> None:
            self._event_queue.put((side, kind, payload))
        return _sink

    def _drain_events(self) -> None:
        while True:
            try:
                side, kind, payload = self._event_queue.get_nowait()
            except Empty:
                break
            self._handle_event(side, kind, payload)
        self.root.after(100, self._drain_events)

    def _handle_event(self, side: str, kind: str, payload: dict) -> None:
        source = "HF" if side == "phone" else "AG"
        if kind == "log":
            self._trace(source, str(payload.get("message", "")))
        elif kind == "line":
            line = str(payload.get("line", ""))
            self._trace(source, f"RX {line}")
            if self._relay_enabled.get():
                target_side = "car" if side == "phone" else "phone"
                target = self.sessions[target_side]
                sent = target.send_line(line)
                direction = "HF->AG" if side == "phone" else "AG->HF"
                if sent:
                    self._trace("LINK", f"TX {direction} {line}")
                else:
                    self._trace("LINK", f"DROP {direction} {line}")
        self._refresh_side(side)
        other_side = "car" if side == "phone" else "phone"
        self._refresh_side(other_side)
        self._update_summary()

    def _refresh_all_views(self) -> None:
        for side in self.sessions:
            self._refresh_side(side)
        self._update_summary()

    def _refresh_side(self, side: str) -> None:
        info = self.sessions[side].info
        w = self._side_widgets[side]
        self._sync_port_var_from_device(side)
        state = "Open" if info.is_open else "Closed"
        w.status_var.set(f"{state} | {info.last_status or 'Idle'}")
        w.stats_var.set(f"RX={info.relay_rx_lines} TX={info.relay_tx_lines} ERR={info.relay_errors}")
        w.open_button.configure(state=tk.NORMAL if not info.is_open else tk.DISABLED)
        w.close_button.configure(state=tk.NORMAL)

    def _update_summary(self) -> None:
        p = self.phone_session.info
        c = self.car_session.info
        self.summary_var.set(
            f"Relay={'ON' if self._relay_enabled.get() else 'OFF'} | "
            f"Phone={p.port or 'offline'} RX/TX={p.relay_rx_lines}/{p.relay_tx_lines} | "
            f"Car={c.port or 'offline'} RX/TX={c.relay_rx_lines}/{c.relay_tx_lines}"
        )

    def _on_close(self) -> None:
        for side in ("phone", "car"):
            self.sessions[side].close()
        save_state(self.state)
        self.root.destroy()

    def _open_inject_popup(self, direction: str) -> None:
        popup = tk.Toplevel(self.root)
        popup.title(f"Inject Predefined Test ({direction})")
        popup.transient(self.root)
        popup.grab_set()
        popup.geometry("920x260")

        selection_var = tk.StringVar(value=PREDEFINED_TEST_FRAMES[0][0])
        frame_map = {label: line for label, line in PREDEFINED_TEST_FRAMES}
        preview_var = tk.StringVar(value=frame_map[selection_var.get()])

        ttk.Label(popup, text=f"Direction: {direction}", padding=(10, 10, 10, 0)).pack(anchor="w")
        row = ttk.Frame(popup, padding=(10, 8, 10, 8))
        row.pack(fill=tk.X)
        ttk.Label(row, text="Frame Preset").pack(side=tk.LEFT)
        selector = ttk.Combobox(row, textvariable=selection_var, state="readonly", values=list(frame_map.keys()), width=42)
        selector.pack(side=tk.LEFT, padx=(8, 0))

        preview = tk.Text(popup, height=6, wrap="word")
        preview.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        preview.insert("1.0", preview_var.get())
        preview.configure(state=tk.DISABLED)

        def refresh_preview() -> None:
            line = frame_map.get(selection_var.get(), "")
            preview_var.set(line)
            preview.configure(state=tk.NORMAL)
            preview.delete("1.0", tk.END)
            preview.insert("1.0", line)
            preview.configure(state=tk.DISABLED)

        selector.bind("<<ComboboxSelected>>", lambda _e: refresh_preview())

        buttons = ttk.Frame(popup, padding=(10, 0, 10, 10))
        buttons.pack(fill=tk.X)

        def send_selected() -> None:
            line = frame_map.get(selection_var.get(), "")
            if not line:
                return
            self._inject_frame(direction, line)
            popup.destroy()

        ttk.Button(buttons, text="Send", command=send_selected).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Cancel", command=popup.destroy).pack(side=tk.LEFT, padx=(8, 0))

    def _inject_frame(self, direction: str, line: str) -> bool:
        if direction == "HF->AG":
            source_side, target_side = "phone", "car"
            source_tag, link_tag = "HF", "HF->AG"
        else:
            source_side, target_side = "car", "phone"
            source_tag, link_tag = "AG", "AG->HF"

        source = self.sessions[source_side]
        target = self.sessions[target_side]

        source.info.relay_rx_lines += 1
        self._trace(source_tag, f"INJECT RX {line}")

        if not self._relay_enabled.get():
            self._trace("LINK", f"RELAY OFF {link_tag} {line}")
            self._refresh_all_views()
            return False

        sent = target.send_line(line)
        if sent:
            self._trace("LINK", f"TX {link_tag} {line}")
        else:
            self._trace("LINK", f"DROP {link_tag} {line}")
        self._refresh_all_views()
        return sent

    def _run_auto_relay_test(self) -> None:
        phone = self.phone_session.info
        car = self.car_session.info
        if not phone.is_open or not car.is_open:
            messagebox.showwarning("Ports not open", "Open both Phone and Car ports before running the automated relay test.")
            return
        if not self._relay_enabled.get():
            messagebox.showwarning("Relay disabled", "Enable relay before running the automated relay test.")
            return

        cases: list[tuple[str, str, str]] = [
            ("HF->AG", PREDEFINED_TEST_FRAMES[0][0], PREDEFINED_TEST_FRAMES[0][1]),
            ("AG->HF", PREDEFINED_TEST_FRAMES[1][0], PREDEFINED_TEST_FRAMES[1][1]),
            ("HF->AG", PREDEFINED_TEST_FRAMES[2][0], PREDEFINED_TEST_FRAMES[2][1]),
            ("AG->HF", PREDEFINED_TEST_FRAMES[3][0], PREDEFINED_TEST_FRAMES[3][1]),
        ]

        lines: list[str] = []
        pass_count = 0
        fail_count = 0

        self._trace("TEST", "Starting automated relay test")
        for direction, label, frame in cases:
            if direction == "HF->AG":
                target = self.car_session.info
            else:
                target = self.phone_session.info
            before_tx = target.relay_tx_lines
            before_err = target.relay_errors
            sent = self._inject_frame(direction, frame)
            after_tx = target.relay_tx_lines
            after_err = target.relay_errors

            if sent and after_tx == before_tx + 1 and after_err == before_err:
                pass_count += 1
                lines.append(f"PASS: {label} ({direction})")
            else:
                fail_count += 1
                reason = "send_line failed"
                if sent and after_tx != before_tx + 1:
                    reason = "tx counter did not increment as expected"
                elif after_err != before_err:
                    reason = "error counter increased"
                lines.append(f"FAIL: {label} ({direction}) -> {reason}")

        final_status = "PASS" if fail_count == 0 else "FAIL"
        summary = f"Auto Relay Test: {final_status} (pass={pass_count}, fail={fail_count})"
        report = "\n".join([summary, ""] + lines)
        self._last_test_report = report
        self._trace("TEST", summary)
        messagebox.showinfo("Auto Relay Test Result", report)

    def _show_last_test_report(self) -> None:
        messagebox.showinfo("Last Test Report", self._last_test_report)

    def _run_pass_scenario(self) -> None:
        self._run_auto_relay_test()

    def _run_fail_scenario(self) -> None:
        phone = self.phone_session.info
        car = self.car_session.info
        if not phone.is_open or not car.is_open:
            messagebox.showwarning("Ports not open", "Open both Phone and Car ports before running the fail scenario.")
            return

        # Deterministic fail-path validation: force relay off for one injected frame.
        original_relay_state = self._relay_enabled.get()
        test_line = PREDEFINED_TEST_FRAMES[0][1]
        target = self.car_session.info
        before_tx = target.relay_tx_lines
        before_err = target.relay_errors
        self._relay_enabled.set(False)
        sent = self._inject_frame("HF->AG", test_line)
        self._relay_enabled.set(original_relay_state)
        after_tx = target.relay_tx_lines
        after_err = target.relay_errors

        passed = (not sent) and (after_tx == before_tx) and (after_err == before_err)
        status = "PASS" if passed else "FAIL"
        report = (
            f"Fail Scenario: {status}\n\n"
            f"Expected behavior:\n"
            f"- Relay disabled causes no TX forwarding\n"
            f"- No write error is generated\n\n"
            f"Observed:\n"
            f"- sent={sent}\n"
            f"- car tx delta={after_tx - before_tx}\n"
            f"- car err delta={after_err - before_err}"
        )
        self._last_test_report = report
        self._trace("TEST", f"Fail scenario {status.lower()}")
        messagebox.showinfo("Fail Scenario Result", report)


def run() -> None:
    root = tk.Tk()
    app = BridgeApp(root)
    root.mainloop()


def run_app() -> None:
    run()


if __name__ == "__main__":
    run()
