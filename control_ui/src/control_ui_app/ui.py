from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable, Optional

from .hci import (
    EVENT_AG_AT_CMD,
    EVENT_AG_CLCC_REQ,
    EVENT_AG_AUDIO_CLOSE,
    EVENT_AG_AUDIO_OPEN,
    EVENT_HF_AT_BASE,
    EVENT_HF_AUDIO_CLOSE,
    EVENT_HF_AUDIO_OPEN,
    GROUP_AVRC_TARGET,
    GROUP_HF,
    opcode,
)
from .models import BridgeState, RemoteDevice
from .session import SERIAL_IMPORT_ERROR, SerialBridgeSession, SerialPortInfo
from .storage import apply_saved_state, save_state


EXPECTED_IDENTITIES = {
    "phone": "NavTool-PhoneConnect",
    "car": "NavTool-CarConnect",
}

SIDE_ROLE_HINTS = {
    "phone": "HF side: keep the board hidden until you intentionally enable phone pairing",
    "car": "AG side: run inquiry, select the car device, then use one-click pair",
}


@dataclass
class SideWidgets:
    port_var: tk.StringVar
    port_detail_var: tk.StringVar
    status_var: tk.StringVar
    identity_var: tk.StringVar
    bda_var: tk.StringVar
    version_var: tk.StringVar
    groups_var: tk.StringVar
    preferred_var: tk.StringVar
    pairable_var: Optional[tk.BooleanVar]
    visible_var: Optional[tk.BooleanVar]
    listbox: tk.Listbox
    log_text: tk.Text
    open_button: ttk.Button
    close_button: ttk.Button
    refresh_button: ttk.Button
    port_combo: ttk.Combobox
    devices: list[str]


class BridgeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("NavTool Bridge Control")
        self.root.geometry("1540x940")

        self.state = BridgeState()
        apply_saved_state(self.state)

        self._event_queue: Queue[tuple[str, str, dict]] = Queue()
        self._port_options: list[str] = []
        self._port_map: dict[str, SerialPortInfo] = {}
        self._port_label_to_device: dict[str, str] = {}
        self._side_widgets: dict[str, SideWidgets] = {}

        self.phone_session = SerialBridgeSession(self.state.phone_session, self._make_event_sink("phone"))
        self.car_session = SerialBridgeSession(self.state.car_session, self._make_event_sink("car"))
        self.sessions = {
            "phone": self.phone_session,
            "car": self.car_session,
        }

        self.summary_var = tk.StringVar(value="Ready")
        self._bridge_enabled = True
        self._phone_hf_cind = {
            1: "0",
            2: "0",
            3: "0",
            4: "0",
            5: "5",
            6: "0",
            7: "5",
        }

        self._build_ui()
        self.refresh_ports()
        self._refresh_all_views()
        self.root.after(100, self._drain_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if not SerialBridgeSession.serial_supported():
            messagebox.showwarning(
                "pyserial missing",
                "pyserial is not installed. The UI can open, but serial control is disabled.\n\n"
                f"Import error: {SERIAL_IMPORT_ERROR}",
            )

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Bridge Summary:").pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.summary_var).pack(side=tk.LEFT, padx=(6, 12))
        ttk.Button(top, text="Refresh Ports", command=self.refresh_ports).pack(side=tk.LEFT)
        ttk.Button(top, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=(8, 0))

        middle = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        middle.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        phone_frame = ttk.Frame(middle, padding=8)
        car_frame = ttk.Frame(middle, padding=8)
        middle.add(phone_frame, weight=1)
        middle.add(car_frame, weight=1)

        self._side_widgets["phone"] = self._build_side(phone_frame, "phone", "Phone Board")
        self._side_widgets["car"] = self._build_side(car_frame, "car", "Car Board")

        bottom = ttk.LabelFrame(self.root, text="Unified Bridge Trace", padding=8)
        bottom.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.bridge_log = tk.Text(bottom, height=12, wrap="word")
        self.bridge_log.pack(fill=tk.BOTH, expand=True)
        self.bridge_log.configure(state=tk.DISABLED)

    def _build_side(self, parent: ttk.Frame, side: str, title: str) -> SideWidgets:
        session = self.sessions[side]
        info = session.info

        frame = ttk.LabelFrame(parent, text=title, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        port_var = tk.StringVar(value=info.port)
        port_detail_var = tk.StringVar(value="Select a COM port to view USB/HCI details")
        status_var = tk.StringVar(value="Closed")
        identity_var = tk.StringVar(value="")
        bda_var = tk.StringVar(value="")
        version_var = tk.StringVar(value="")
        groups_var = tk.StringVar(value="")
        preferred_var = tk.StringVar(value=info.preferred_remote_address)
        pairable_var = tk.BooleanVar(value=False) if side == "phone" else None
        visible_var = tk.BooleanVar(value=False) if side == "phone" else None

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(row, text="Port").pack(side=tk.LEFT)
        port_combo = ttk.Combobox(row, textvariable=port_var, state="normal", width=42)
        port_combo.pack(side=tk.LEFT, padx=(6, 6))
        port_combo.bind("<<ComboboxSelected>>", lambda _event, key=side: self._on_port_changed(key))
        port_combo.bind("<FocusOut>", lambda _event, key=side: self._on_port_changed(key))

        refresh_button = ttk.Button(row, text="Refresh", command=self.refresh_ports)
        refresh_button.pack(side=tk.LEFT, padx=(0, 6))

        open_button = ttk.Button(row, text="Open", command=lambda key=side: self.open_session(key))
        open_button.pack(side=tk.LEFT)
        close_button = ttk.Button(row, text="Close", command=lambda key=side: self.close_session(key))
        close_button.pack(side=tk.LEFT, padx=(6, 0))
        if side == "phone":
            ttk.Button(row, text="Enable Phone Pairing", command=self.enable_phone_pairing).pack(side=tk.LEFT, padx=(6, 0))

        hint_row = ttk.Frame(frame)
        hint_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(hint_row, text=SIDE_ROLE_HINTS[side]).pack(side=tk.LEFT)

        detail_row = ttk.Frame(frame)
        detail_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(detail_row, textvariable=port_detail_var, justify=tk.LEFT, wraplength=680).pack(side=tk.LEFT, fill=tk.X, expand=True)

        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, pady=(0, 6))
        for label_text, var in (
            ("Expected", tk.StringVar(value=EXPECTED_IDENTITIES[side])),
            ("Identity", identity_var),
            ("Local BDA", bda_var),
            ("Version", version_var),
            ("Groups", groups_var),
            ("Status", status_var),
        ):
            label_row = ttk.Frame(status_frame)
            label_row.pack(fill=tk.X, pady=0)
            ttk.Label(label_row, text=f"{label_text}:", width=10).pack(side=tk.LEFT)
            ttk.Label(label_row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        if side == "car":
            actions = ttk.Frame(frame)
            actions.pack(fill=tk.X, pady=(0, 6))
            ttk.Button(actions, text="Start Inquiry", command=self.car_session.start_inquiry).pack(side=tk.LEFT, padx=(0, 4), pady=2)
            ttk.Button(actions, text="Stop Inquiry", command=self.car_session.stop_inquiry).pack(side=tk.LEFT, padx=(0, 4), pady=2)
            ttk.Button(actions, text="Pair Selected", command=self.pair_selected_car_device).pack(side=tk.LEFT, padx=(0, 4), pady=2)

        content = ttk.Panedwindow(frame, orient=tk.HORIZONTAL if side == "car" else tk.VERTICAL)
        content.pack(fill=tk.BOTH, expand=True)

        logs_frame = ttk.LabelFrame(content, text="Per-Side Trace", padding=6)
        if side == "car":
            devices_frame = ttk.LabelFrame(content, text="Discovered Devices", padding=6)
            content.add(devices_frame, weight=1)
            listbox = tk.Listbox(devices_frame, height=12, exportselection=False)
            listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
            listbox.bind("<<ListboxSelect>>", lambda _event, key=side: self._on_device_selected(key))
            device_scroll = ttk.Scrollbar(devices_frame, orient=tk.VERTICAL, command=listbox.yview)
            device_scroll.pack(fill=tk.Y, side=tk.RIGHT)
            listbox.configure(yscrollcommand=device_scroll.set)
            content.add(logs_frame, weight=4)
        else:
            listbox = tk.Listbox(frame, height=1, exportselection=False)
            content.add(logs_frame, weight=1)

        log_text = tk.Text(logs_frame, height=24 if side == "phone" else 28, wrap="word")
        log_text.pack(fill=tk.BOTH, expand=True)
        log_text.configure(state=tk.DISABLED)

        return SideWidgets(
            port_var=port_var,
            port_detail_var=port_detail_var,
            status_var=status_var,
            identity_var=identity_var,
            bda_var=bda_var,
            version_var=version_var,
            groups_var=groups_var,
            preferred_var=preferred_var,
            pairable_var=pairable_var,
            visible_var=visible_var,
            listbox=listbox,
            log_text=log_text,
            open_button=open_button,
            close_button=close_button,
            refresh_button=refresh_button,
            port_combo=port_combo,
            devices=[],
        )

    def _make_event_sink(self, side: str) -> Callable[[str, dict], None]:
        def sink(kind: str, payload: dict) -> None:
            self._event_queue.put((side, kind, payload))
        return sink

    def refresh_ports(self) -> None:
        ports = SerialBridgeSession.list_ports()
        self._port_map = {port.device: port for port in ports}
        self._port_label_to_device = {port.dropdown_label(): port.device for port in ports}
        self._port_options = [port.dropdown_label() for port in ports]
        for side, widgets in self._side_widgets.items():
            widgets.port_combo["values"] = self._port_options
            self._sync_port_var_from_device(side)
            self._update_port_detail(side)
        if ports:
            self.summary_var.set("Detected ports: " + ", ".join(port.device for port in ports))
        else:
            self.summary_var.set("No serial ports detected")

    def open_session(self, side: str) -> None:
        port = self._resolve_selected_port(side)
        if not port:
            messagebox.showinfo("Port required", f"Select a COM port for the {side} board first.")
            return
        self.sessions[side].info.port = port
        self._sync_port_var_from_device(side)
        if self.sessions[side].open(port):
            if side == "phone":
                self.apply_phone_flags()
        self._save_state()

    def close_session(self, side: str) -> None:
        self.sessions[side].close()
        self.refresh_ports()
        self._refresh_side(side)

    def apply_phone_flags(self) -> None:
        widgets = self._side_widgets["phone"]
        pairable = widgets.pairable_var.get() if widgets.pairable_var is not None else True
        visible = widgets.visible_var.get() if widgets.visible_var is not None else True
        if self.phone_session.info.is_open:
            self.phone_session.apply_pairable_visibility(pairable, visible)
        else:
            self.phone_session.info.last_status = (
                f"HF defaults armed: pairable={'yes' if pairable else 'no'}, visible={'yes' if visible else 'no'}"
            )
            self._refresh_side("phone")

    def enable_phone_pairing(self) -> None:
        widgets = self._side_widgets["phone"]
        if widgets.pairable_var is not None:
            widgets.pairable_var.set(True)
        if widgets.visible_var is not None:
            widgets.visible_var.set(True)
        self.apply_phone_flags()

    def pair_selected_car_device(self) -> None:
        device = self._selected_device("car")
        if device is None:
            messagebox.showinfo("No device selected", "Select a discovered device on the car side first.")
            return
        widgets = self._side_widgets["car"]
        widgets.preferred_var.set(device.address)
        self._save_preferred_from_entry("car")
        self.car_session.pair_ag_device(device.address)
        self._save_state()

    def use_selected_device(self, side: str) -> None:
        device = self._selected_device(side)
        if device is None:
            messagebox.showinfo("No device selected", f"Select a discovered device on the {side} side first.")
            return
        widgets = self._side_widgets[side]
        widgets.preferred_var.set(device.address)
        session_info = self.sessions[side].info
        session_info.preferred_remote_address = device.address
        session_info.preferred_remote_name = device.name
        self._save_state()
        self._refresh_side(side)

    def _with_selected_address(self, side: str, callback: Callable[[SerialBridgeSession, str], None]) -> None:
        device = self._selected_device(side)
        if device is None:
            messagebox.showinfo("No device selected", f"Select a discovered device on the {side} side first.")
            return
        callback(self.sessions[side], device.address)
        self._save_state()

    def _selected_device(self, side: str) -> RemoteDevice | None:
        widgets = self._side_widgets[side]
        selection = widgets.listbox.curselection()
        if not selection:
            return None
        address = widgets.devices[selection[0]]
        return self.sessions[side].info.discovered_devices.get(address)

    def _on_device_selected(self, side: str) -> None:
        device = self._selected_device(side)
        if device is None:
            return
        self._side_widgets[side].preferred_var.set(device.address)

    def _resolve_selected_port(self, side: str) -> str:
        raw_value = self._side_widgets[side].port_var.get().strip()
        if raw_value in self._port_label_to_device:
            return self._port_label_to_device[raw_value]
        if raw_value in self._port_map:
            return raw_value
        if "|" in raw_value:
            candidate = raw_value.split("|", 1)[0].strip()
            if candidate in self._port_map:
                return candidate
        return raw_value

    def _sync_port_var_from_device(self, side: str) -> None:
        widgets = self._side_widgets[side]
        device_name = self.sessions[side].info.port.strip()
        port = self._port_map.get(device_name)
        if port is not None:
            widgets.port_var.set(port.dropdown_label())
        elif device_name:
            widgets.port_var.set(device_name)

    def _on_port_changed(self, side: str) -> None:
        resolved = self._resolve_selected_port(side)
        self.sessions[side].info.port = resolved
        self._sync_port_var_from_device(side)
        self._update_port_detail(side)
        self._save_state()

    def _update_port_detail(self, side: str) -> None:
        widgets = self._side_widgets[side]
        port_name = self.sessions[side].info.port.strip() or self._resolve_selected_port(side)
        port = self._port_map.get(port_name)
        if port is None:
            widgets.port_detail_var.set("USB details unavailable. Refresh ports or choose a detected COM port.\nControl link: WICED HCI over USB serial")
            return
        lines = port.detail_lines()
        lines.append(f"Expected board: {EXPECTED_IDENTITIES[side]}")
        widgets.port_detail_var.set("\n".join(lines))

    def _save_preferred_from_entry(self, side: str) -> None:
        session_info = self.sessions[side].info
        session_info.preferred_remote_address = self._side_widgets[side].preferred_var.get().strip()
        self._save_state()

    def clear_logs(self) -> None:
        for widgets in self._side_widgets.values():
            self._replace_text(widgets.log_text, "")
        self._replace_text(self.bridge_log, "")

    def _drain_events(self) -> None:
        try:
            while True:
                side, kind, payload = self._event_queue.get_nowait()
                self._handle_event(side, kind, payload)
        except Empty:
            pass
        self.root.after(100, self._drain_events)

    def _handle_event(self, side: str, kind: str, payload: dict) -> None:
        session = self.sessions[side]
        info = session.info

        if kind == "log":
            message = str(payload.get("message", ""))
            timestamp = datetime.now().strftime("%H:%M:%S")
            label = f"[{timestamp}] [{info.label}] {message}\n"
            self._append_text(self._side_widgets[side].log_text, label)
            self._append_text(self.bridge_log, label)
        elif kind == "state":
            self._refresh_side(side)
            identity = info.bridge_identity.strip()
            expected = EXPECTED_IDENTITIES[side]
            if identity and identity != expected:
                self.summary_var.set(f"Identity mismatch on {info.label}: expected {expected}, got {identity}")
        elif kind == "user_confirmation":
            numeric_value = payload.get("numeric_value", 0)
            address = payload.get("address", "")
            accepted = messagebox.askyesno(
                f"{info.label} numeric comparison",
                f"{info.label} requested numeric comparison for {address}.\n\nValue: {numeric_value}\n\nAccept?",
            )
            session.reply_user_confirmation(payload["raw_bda"], accepted)
        elif kind == "pin_request":
            address = payload.get("address", "")
            pin = simpledialog.askstring(
                f"{info.label} PIN request",
                f"Enter PIN for {address}",
                parent=self.root,
            )
            if pin:
                session.reply_pin(payload["raw_bda"], pin)
        elif kind == "packet":
            self._handle_bridge_packet(side, payload)
        self._refresh_side(side)
        self._update_summary()

    def _handle_bridge_packet(self, side: str, payload: dict) -> None:
        if not self._bridge_enabled:
            return
        opcode_value = int(payload.get("opcode", 0))
        raw_payload = payload.get("payload", b"")
        if not isinstance(raw_payload, (bytes, bytearray)):
            return
        packet_payload = bytes(raw_payload)

        if side == "phone":
            self._bridge_phone_packet(opcode_value, packet_payload)
        else:
            self._bridge_car_packet(opcode_value, packet_payload)

    def _bridge_phone_packet(self, opcode_value: int, payload: bytes) -> None:
        if opcode_value == EVENT_HF_AUDIO_OPEN:
            self._bridge_ag_audio("open")
            return
        if opcode_value == EVENT_HF_AUDIO_CLOSE:
            self._bridge_ag_audio("close")
            return
        if opcode_value < EVENT_HF_AT_BASE or opcode_value >= opcode(GROUP_HF, 0x40):
            return

        handle, number, text = self._parse_value_payload(payload)
        event_code = opcode_value & 0xFF

        if event_code == 0x03:
            self._send_car_result("RING", "Phone HF RING -> Car AG RING")
        elif event_code == 0x04:
            self._send_car_result(f"+VGS: {number}", f"Phone HF VGS={number} -> Car AG +VGS")
        elif event_code == 0x05:
            self._send_car_result(f"+VGM: {number}", f"Phone HF VGM={number} -> Car AG +VGM")
        elif event_code == 0x08 and text:
            ag_cind = self._convert_phone_cind_to_ag(text)
            self.car_session.ag_set_cind(ag_cind)
            self._bridge_trace(f"Phone HF +CIND {text} -> Car AG Set CIND {ag_cind}")
            self._send_car_result(f"+CIND: {ag_cind}", f"Phone HF +CIND {text} -> Car AG +CIND {ag_cind}")
        elif event_code == 0x09 and text:
            clip = f'+CLIP: "{text}",{number}'
            self._send_car_result(clip, f"Phone HF CLIP {text}/{number} -> Car AG {clip}")
        elif event_code == 0x0A and text:
            ag_index, value = self._bridge_phone_ciev_to_car(text)
            if ag_index is not None:
                self._send_car_result(
                    f"+CIEV: {ag_index},{value}",
                    f"Phone HF +CIEV {text} -> Car AG +CIEV {ag_index},{value}",
                )
        elif event_code == 0x0E and text:
            self._send_car_result(f"+CNUM: {text}", f"Phone HF +CNUM {text} -> Car AG +CNUM")
        elif event_code == 0x0F:
            self._send_car_result(f"+BTRH: {number}", f"Phone HF +BTRH {number} -> Car AG +BTRH")
        elif event_code == 0x10 and text:
            self._send_car_result(f"+COPS: {text}", f"Phone HF +COPS {text} -> Car AG +COPS")
        elif event_code == 0x11 and text:
            self._send_car_result(f"+CLCC: {text}", f"Phone HF +CLCC {text} -> Car AG +CLCC")
        elif event_code == 0x12 and text:
            self._send_car_result(f"+BIND: {text}", f"Phone HF +BIND {text} -> Car AG +BIND")
        elif event_code == 0x13:
            self._send_car_result(f"+BCS: {number}", f"Phone HF +BCS {number} -> Car AG +BCS")
        elif event_code == 0x00:
            self._send_car_result("OK", "Phone HF OK -> Car AG OK")
        elif event_code == 0x01:
            self._send_car_result("ERROR", "Phone HF ERROR -> Car AG ERROR")
        elif event_code == 0x02:
            self._send_car_result(f"+CME ERROR: {number}", f"Phone HF +CME ERROR {number} -> Car AG +CME ERROR")

    def _bridge_car_packet(self, opcode_value: int, payload: bytes) -> None:
        if opcode_value == EVENT_AG_AUDIO_OPEN:
            self._bridge_hf_audio("open")
            return
        if opcode_value == EVENT_AG_AUDIO_CLOSE:
            self._bridge_hf_audio("close")
            return
        if opcode_value == EVENT_AG_AT_CMD:
            handle, at_text = self._parse_ag_at_payload(payload)
            if at_text:
                self.phone_session.hf_send_raw_at(at_text)
                self._bridge_trace(f"Car AG AT {at_text} -> Phone HF raw AT {at_text}")
            return
        if opcode_value == EVENT_AG_CLCC_REQ:
            self.phone_session.hf_send_raw_at("AT+CLCC")
            self._bridge_trace("Car AG CLCC request -> Phone HF raw AT AT+CLCC")
            return
        if opcode_value == opcode(GROUP_AVRC_TARGET, 0x03):
            self.phone_session.avrc_play()
            self._bridge_trace("Car AVRCP Play received -> Phone AVRCP Play command")
        elif opcode_value == opcode(GROUP_AVRC_TARGET, 0x04):
            self.phone_session.avrc_stop()
            self._bridge_trace("Car AVRCP Stop received -> Phone AVRCP Stop command")
        elif opcode_value == opcode(GROUP_AVRC_TARGET, 0x05):
            self.phone_session.avrc_pause()
            self._bridge_trace("Car AVRCP Pause received -> Phone AVRCP Pause command")
        elif opcode_value == opcode(GROUP_AVRC_TARGET, 0x06):
            self.phone_session.avrc_next()
            self._bridge_trace("Car AVRCP Next received -> Phone AVRCP Next command")
        elif opcode_value == opcode(GROUP_AVRC_TARGET, 0x07):
            self.phone_session.avrc_prev()
            self._bridge_trace("Car AVRCP Previous received -> Phone AVRCP Previous command")

    def _bridge_phone_ciev_to_car(self, text: str) -> tuple[Optional[int], Optional[str]]:
        parts = [part.strip() for part in text.split(",", 1)]
        if len(parts) != 2:
            return (None, None)
        try:
            phone_index = int(parts[0])
        except ValueError:
            return (None, None)
        value = parts[1]
        self._phone_hf_cind[phone_index] = value
        ag_index = {1: 4, 2: 1, 3: 2, 4: 3, 5: 5, 6: 7, 7: 6}.get(phone_index)
        if ag_index is None:
            return (None, None)
        self.car_session.ag_set_cind(self._current_ag_cind())
        self._bridge_trace(
            f"Phone HF +CIEV {phone_index},{value} -> Car AG indicator {ag_index},{value} | CIND {self._current_ag_cind()}"
        )
        return (ag_index, value)

    def _convert_phone_cind_to_ag(self, text: str) -> str:
        values = [part.strip() for part in text.split(",")]
        if len(values) >= 7:
            for index, value in enumerate(values[:7], start=1):
                self._phone_hf_cind[index] = value
        return self._current_ag_cind()

    def _current_ag_cind(self) -> str:
        return ",".join(
            (
                self._phone_hf_cind[2],
                self._phone_hf_cind[3],
                self._phone_hf_cind[4],
                self._phone_hf_cind[1],
                self._phone_hf_cind[5],
                self._phone_hf_cind[7],
                self._phone_hf_cind[6],
            )
        )

    def _send_car_result(self, text: str, trace: str) -> None:
        self.car_session.ag_send_string(text)
        self._bridge_trace(trace)

    def _bridge_hf_audio(self, action: str) -> None:
        if action == "open":
            self.phone_session.hf_audio_open()
            self._bridge_trace("Car AG audio open -> Phone HF audio open")
        else:
            self.phone_session.hf_audio_close()
            self._bridge_trace("Car AG audio close -> Phone HF audio close")

    def _bridge_ag_audio(self, action: str) -> None:
        if action == "open":
            self.car_session.ag_audio_open()
            self._bridge_trace("Phone HF audio open -> Car AG audio open")
        else:
            self.car_session.ag_audio_close()
            self._bridge_trace("Phone HF audio close -> Car AG audio close")

    def _parse_value_payload(self, payload: bytes) -> tuple[int, int, str]:
        handle = payload[0] | (payload[1] << 8) if len(payload) >= 2 else 0
        number = payload[2] | (payload[3] << 8) if len(payload) >= 4 else 0
        text = payload[4:].split(b"\x00", 1)[0].decode("utf-8", errors="ignore") if len(payload) > 4 else ""
        return (handle, number, text)

    def _parse_ag_at_payload(self, payload: bytes) -> tuple[int, str]:
        handle = payload[0] | (payload[1] << 8) if len(payload) >= 2 else 0
        text = payload[2:].split(b"\x00", 1)[0].decode("utf-8", errors="ignore").strip()
        return (handle, text)

    def _bridge_trace(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._append_text(self.bridge_log, f"[{timestamp}] [Bridge] {message}\n")

    def _refresh_all_views(self) -> None:
        for side in self.sessions:
            self._refresh_side(side)
        self._update_summary()

    def _refresh_side(self, side: str) -> None:
        session = self.sessions[side]
        info = session.info
        widgets = self._side_widgets[side]

        self._sync_port_var_from_device(side)
        widgets.identity_var.set(info.bridge_identity or "<waiting>")
        widgets.bda_var.set(info.local_bda or "<unknown>")
        widgets.version_var.set(info.sdk_version or "<unknown>")
        widgets.groups_var.set(", ".join(f"0x{group:02X}" for group in info.supported_groups) or "<unknown>")
        widgets.preferred_var.set(info.preferred_remote_address)
        self._update_port_detail(side)

        status_bits = ["Open" if info.is_open else "Closed"]
        status_bits.append(f"Service={'Yes' if info.ag_connected else 'No'}")
        status_bits.append(f"A2DP={'Yes' if info.a2dp_connected else 'No'}")
        status_bits.append(f"AVRCP={'Yes' if info.avrc_connected else 'No'}")
        if info.last_status:
            status_bits.append(info.last_status)
        widgets.status_var.set(" | ".join(status_bits))

        widgets.open_button.configure(state=tk.NORMAL if not info.is_open else tk.DISABLED)
        widgets.close_button.configure(state=tk.NORMAL if info.is_open else tk.DISABLED)

        devices = sorted(
            info.discovered_devices.values(),
            key=lambda item: ((item.name or "").lower(), item.address),
        )
        current_selection = widgets.listbox.curselection()
        selected_address = widgets.devices[current_selection[0]] if current_selection else ""
        widgets.devices = [device.address for device in devices]

        widgets.listbox.delete(0, tk.END)
        selected_index = None
        for index, device in enumerate(devices):
            label = self._device_label(device)
            widgets.listbox.insert(tk.END, label)
            if device.address == selected_address:
                selected_index = index
        if selected_index is not None:
            widgets.listbox.selection_set(selected_index)

    def _device_label(self, device: RemoteDevice) -> str:
        name = device.name.strip() or "<unknown>"
        rssi = "?" if device.rssi is None else str(device.rssi)
        return f"{name} [{device.address}] RSSI={rssi}"

    def _update_summary(self) -> None:
        phone = self.phone_session.info
        car = self.car_session.info
        phone_mode = "visible/pairable" if self._side_widgets["phone"].visible_var.get() and self._side_widgets["phone"].pairable_var.get() else "hidden/not pairable"
        self.summary_var.set(
            f"Phone={phone.bridge_identity or phone.port or 'offline'} ({phone_mode}) | "
            f"Car={car.bridge_identity or car.port or 'offline'} | "
            f"Tracked peers: phone={len(phone.discovered_devices)}, car={len(car.discovered_devices)}"
        )

    def _append_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.insert(tk.END, text)
        widget.see(tk.END)
        widget.configure(state=tk.DISABLED)

    def _replace_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        if text:
            widget.insert(tk.END, text)
        widget.configure(state=tk.DISABLED)

    def _save_state(self) -> None:
        save_state(self.state)

    def _on_close(self) -> None:
        self._save_state()
        for session in self.sessions.values():
            session.close()
        self.refresh_ports()
        self.root.destroy()


def run_app() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    app = BridgeApp(root)
    app.root.mainloop()
