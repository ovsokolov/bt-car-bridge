from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
import time
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
    GROUP_AUDIO,
    GROUP_AVRC_CONTROLLER,
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

CALL_STATE_IDLE = "idle"
CALL_STATE_INCOMING = "incoming"
CALL_STATE_ACTIVE = "active"
CALL_STATE_HELD = "held"
CALL_STATE_OUTGOING = "outgoing"


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
        self._avrc_bridge_enabled = True
        self._phone_hf_cind = {
            1: "0",
            2: "0",
            3: "0",
            4: "0",
            5: "5",
            6: "0",
            7: "5",
        }
        self._phone_call_state = CALL_STATE_IDLE
        self._car_audio_open = False
        self._pending_car_at_responses = 0
        self._pending_car_codec_responses = 0
        self._pending_car_clcc_requests = 0
        self._car_answer_pending = False
        self._last_car_ata_forward_at = 0.0
        self._last_phone_ring_at = 0.0
        self._last_phone_clip_at = 0.0
        self._last_phone_real_ring_at = 0.0
        self._last_phone_real_clip_at = 0.0
        self._incoming_fallback_ring_after_id: Optional[str] = None
        self._last_phone_clcc_probe_at = 0.0
        self._last_phone_hf_handle = 0
        self._pending_phone_hf_at: list[str] = []
        self._pending_car_results: list[tuple[str, str]] = []
        self._last_clip_number = ""
        self._last_clip_type = "129"
        self._call_has_real_clip = False
        self._ring_placeholder_clip_sent = False
        self._last_phone_avrc_ct_attempt_at = 0.0
        self._phone_avrc_ct_connected = False
        self._phone_avrc_tg_connected = False
        self._last_phone_avrc_control = ""
        self._last_phone_avrc_control_at = 0.0
        self._phone_avrc_control_retry_remaining = 0
        self._pending_phone_avrc_retry: Optional[str] = None
        self._last_phone_avrc_tg_disconnect_at = 0.0
        self._car_avrc_tg_connected = False
        self._car_avrc_tg_notifications_registered = False
        self._car_tg_registration_enabled = False
        self._phone_avrc_attr_cache: dict[int, str] = {}
        self._phone_avrc_play_state = 0
        self._phone_avrc_song_pos_ms = 0
        self._last_forwarded_track_signature: tuple[tuple[int, str], ...] = tuple()
        self._last_forwarded_status_signature: tuple[int, int, int] = (-1, -1, -1)
        self._last_car_avrc_status_forward_at = 0.0
        self._pending_car_avrc_track_flush = False
        self._car_avrc_suppressed_by_call = False
        self._car_avrc_suppressed_by_hfp = False
        # Test toggle: disable all Car AVRCP TG push traffic (notifications, metadata, status).
        self._car_tg_push_enabled = False

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
        tabs = ttk.Notebook(self.root)
        tabs.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        control_tab = ttk.Frame(tabs, padding=8)
        trace_tab = ttk.Frame(tabs, padding=8)
        tabs.add(control_tab, text="Control")
        tabs.add(trace_tab, text="Bridge Trace")

        top = ttk.Frame(control_tab)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Bridge Summary:").pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.summary_var).pack(side=tk.LEFT, padx=(6, 12))
        ttk.Button(top, text="Refresh Ports", command=self.refresh_ports).pack(side=tk.LEFT)
        ttk.Button(top, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=(8, 0))

        middle = ttk.Panedwindow(control_tab, orient=tk.HORIZONTAL)
        middle.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        phone_frame = ttk.Frame(middle, padding=8)
        car_frame = ttk.Frame(middle, padding=8)
        middle.add(phone_frame, weight=1)
        middle.add(car_frame, weight=1)

        self._side_widgets["phone"] = self._build_side(phone_frame, "phone", "Phone Board")
        self._side_widgets["car"] = self._build_side(car_frame, "car", "Car Board")

        trace_top = ttk.Frame(trace_tab)
        trace_top.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(trace_top, text="Clear Trace", command=self.clear_bridge_trace).pack(side=tk.LEFT)

        trace_box = ttk.LabelFrame(trace_tab, text="Unified Bridge Trace (All Sides + Bridge)", padding=8)
        trace_box.pack(fill=tk.BOTH, expand=True)
        self.bridge_log = tk.Text(trace_box, height=24, wrap="word")
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
            phone_actions = ttk.Frame(frame)
            phone_actions.pack(fill=tk.X, pady=(0, 6))
            ttk.Button(phone_actions, text="Enable Phone Pairing", command=self.enable_phone_pairing).pack(side=tk.LEFT)
            ttk.Label(
                phone_actions,
                text="Makes the PhoneConnect board discoverable and pairable so the phone can start pairing.",
                wraplength=620,
                justify=tk.LEFT,
            ).pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)

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
            ttk.Button(actions, text="Connect Selected", command=self.pair_selected_car_device).pack(side=tk.LEFT, padx=(0, 4), pady=2)

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
        self.sessions[side].open(port)
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
            identity = self.phone_session.info.bridge_identity.strip()
            expected = EXPECTED_IDENTITIES["phone"]
            target_port = self.phone_session.info.port or "<unknown port>"
            if identity and identity != expected:
                self.phone_session._log(
                    f"Blocked phone pairing visibility command on {target_port} because identity is {identity}, expected {expected}"
                )
                messagebox.showwarning(
                    "Wrong board on PhoneConnect",
                    f"Phone pairing was blocked because the board opened in the PhoneConnect pane is:\n\n"
                    f"{identity}\n\nExpected:\n{expected}\n\n"
                    f"Target port: {target_port}",
                )
                return
            self.phone_session._log(
                f"Applying phone pairing visibility on {target_port} for identity {identity or expected}"
            )
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

    def clear_bridge_trace(self) -> None:
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

        if side == "phone" and opcode_value == opcode(GROUP_HF, 0x03) and len(packet_payload) >= 2:
            self._last_phone_hf_handle = packet_payload[0] | (packet_payload[1] << 8)
            if len(packet_payload) >= 8:
                remote = ":".join(f"{value:02X}" for value in reversed(packet_payload[2:8]))
                if remote and not self.phone_session.info.preferred_remote_address:
                    self.phone_session.info.preferred_remote_address = remote
                    self._bridge_trace(f"Learned phone peer address from HF service event: {remote}")

        if side == "phone" and opcode_value == opcode(GROUP_HF, 0x03):
            # HF reconnects can happen while AVRCP CT is still valid; do not clear CT state here.
            self._flush_pending_phone_hf_at()
        if side == "phone" and opcode_value == opcode(GROUP_HF, 0x04):
            # Keep AVRCP CT readiness unchanged here. During call flows the HF SLC can
            # briefly flap while AVRCP CT remains connected, and clearing this state
            # causes media controls to get stuck in passive-mode "not connected".
            self._bridge_trace("Phone HF service disconnected; keeping AVRCP CT ready state unchanged")
        if side == "phone" and opcode_value in {opcode(GROUP_AUDIO, 0x02), opcode(GROUP_AVRC_TARGET, 0x01)}:
            self._learn_phone_peer_from_media_event(packet_payload, opcode_value)
        if side == "phone" and opcode_value == opcode(GROUP_AVRC_CONTROLLER, 0x01):
            if not self._avrc_bridge_enabled:
                return
            self._phone_avrc_ct_connected = True
            self._bridge_trace("Phone AVRCP CT connected; media control forwarding is enabled")
        if side == "phone" and opcode_value == opcode(GROUP_AVRC_CONTROLLER, 0x02):
            if not self._avrc_bridge_enabled:
                return
            self._phone_avrc_ct_connected = False
            self._bridge_trace("Phone AVRCP CT disconnected; media control forwarding is paused")
        if side == "phone" and opcode_value == opcode(GROUP_AVRC_TARGET, 0x01):
            if not self._avrc_bridge_enabled:
                return
            self._phone_avrc_tg_connected = True
            self._bridge_trace("Phone AVRCP TG connected")
        if side == "phone" and opcode_value == opcode(GROUP_AVRC_TARGET, 0x02):
            if not self._avrc_bridge_enabled:
                return
            self._phone_avrc_tg_connected = False
            self._bridge_trace("Phone AVRCP TG disconnected")
        if side == "phone" and opcode_value == opcode(GROUP_AVRC_TARGET, 0xFF):
            if not self._avrc_bridge_enabled:
                return
            if packet_payload:
                status = packet_payload[0]
                if status == 0x09:
                    self._bridge_trace("Phone reported AVRCP target Unknown Command while forwarding media control")
        if side == "phone" and opcode_value == opcode(GROUP_AVRC_CONTROLLER, 0xFF):
            if not self._avrc_bridge_enabled:
                return
            if packet_payload:
                status = packet_payload[0]
                if status != 0:
                    if self._phone_avrc_ct_connected:
                        self._bridge_trace(
                            f"Phone AVRCP CT command status is non-success ({status}) but CT is already connected; keeping CT ready state"
                        )
                    else:
                        self._phone_avrc_ct_connected = False
                        self._bridge_trace(
                            f"Phone AVRCP CT command status is non-success ({status}); CT not connected, will retry later"
                        )
        if side == "car" and opcode_value == opcode(GROUP_AVRC_TARGET, 0x01):
            if not self._avrc_bridge_enabled:
                self._bridge_trace("AVRCP bridge disabled: skipping Car AVRCP TG setup")
                return
            self._car_avrc_tg_connected = True
            self._car_avrc_tg_notifications_registered = False
            self._bridge_trace("Car AVRCP TG connected; ready to receive bridged metadata/status")
            if self._car_tg_registration_enabled:
                self.car_session.avrc_tg_register_notifications()
                self._car_avrc_tg_notifications_registered = True
                self._bridge_trace("Requested Car AVRCP TG notification registration")
            else:
                self._bridge_trace("Bridge-side Car AVRCP TG notification registration is disabled")
            if not self._car_tg_push_enabled:
                self._bridge_trace("Car AVRCP TG metadata/status push is disabled for call-behavior testing")
            self._last_forwarded_track_signature = tuple()
            self._last_forwarded_status_signature = (-1, -1, -1)
            if not self._car_tg_push_enabled:
                pass
            elif self._car_avrc_suppressed_by_hfp:
                self._bridge_trace("Deferred cached phone AVRCP push because Car HFP AG session is active")
            else:
                self._forward_cached_phone_avrc_to_car()
        if side == "car" and opcode_value == opcode(GROUP_AVRC_TARGET, 0x02):
            if not self._avrc_bridge_enabled:
                return
            self._car_avrc_tg_connected = False
            self._car_avrc_tg_notifications_registered = False
            self._bridge_trace("Car AVRCP TG disconnected; pausing metadata/status forwarding")

        if side == "phone":
            self._bridge_phone_packet(opcode_value, packet_payload)
        else:
            self._bridge_car_packet(opcode_value, packet_payload)

    def _bridge_phone_packet(self, opcode_value: int, payload: bytes) -> None:
        if not self._avrc_bridge_enabled and (opcode_value >> 8) in {GROUP_AVRC_CONTROLLER, GROUP_AVRC_TARGET}:
            return
        if opcode_value == opcode(GROUP_AVRC_CONTROLLER, 0x03):
            self._bridge_trace(self._describe_phone_avrc_track_info(payload))
            self._forward_phone_avrc_track_info_to_car(payload)
            return
        if opcode_value == opcode(GROUP_AVRC_CONTROLLER, 0x04):
            self._bridge_trace(self._describe_phone_avrc_play_status(payload))
            self._forward_phone_avrc_play_status_to_car(payload)
            return
        if opcode_value == opcode(GROUP_AVRC_CONTROLLER, 0x05):
            self._forward_phone_avrc_position_to_car(payload)
            return
        if opcode_value == opcode(GROUP_HF, 0x04):
            self._car_answer_pending = False
            self._pending_car_codec_responses = 0
        if opcode_value == EVENT_HF_AUDIO_OPEN:
            # Audio open alone is not a reliable "active call" signal on all stacks.
            # Keep call state driven by +CIEV/+CLCC to avoid sticky call=1 and AVRCP suppression.
            self._bridge_ag_audio("open")
            return
        if opcode_value == EVENT_HF_AUDIO_CLOSE:
            self._bridge_ag_audio("close")
            return
        if opcode_value < EVENT_HF_AT_BASE or opcode_value >= opcode(GROUP_HF, 0x40):
            return

        handle, number, text = self._parse_value_payload(payload)
        event_code = opcode_value - EVENT_HF_AT_BASE

        if event_code == 0x03:
            now = time.monotonic()
            self._last_phone_ring_at = now
            self._last_phone_real_ring_at = now
            self._bridge_phone_incoming_call_hint()
            self._send_car_result("RING", "Phone HF RING -> Car AG RING")
            if self._last_clip_number:
                clip_type = self._last_clip_type if self._last_clip_type.isdigit() else "129"
                clip = f'+CLIP: "{self._last_clip_number}",{clip_type}'
                self._send_car_result(clip, f"Phone HF RING with cached caller ID -> Car AG {clip}")
            else:
                self._send_placeholder_clip_if_needed("Phone HF RING fallback")
        elif event_code == 0x04:
            self._send_car_result(f"+VGS: {number}", f"Phone HF VGS={number} -> Car AG +VGS")
        elif event_code == 0x05:
            self._send_car_result(f"+VGM: {number}", f"Phone HF VGM={number} -> Car AG +VGM")
        elif event_code == 0x08 and text:
            ag_cind = self._convert_phone_cind_to_ag(text)
            self._refresh_phone_call_state(f"Phone HF +CIND {text}")
            self._update_answer_pending_from_call_state()
            self._update_car_avrc_call_gate(f"Phone HF +CIND {text}")
            self._send_car_cind_update(f"Phone HF +CIND {text}")
            self._send_car_result(f"+CIND: {ag_cind}", f"Phone HF +CIND {text} -> Car AG +CIND {ag_cind}")
        elif event_code == 0x09 and text:
            self._bridge_phone_incoming_call_hint()
            now = time.monotonic()
            self._last_phone_clip_at = now
            self._last_phone_real_clip_at = now
            self._call_has_real_clip = True
            clip_number = self._normalize_clip_number(text)
            self._last_clip_number = clip_number
            self._last_clip_type = str(number if number > 0 else 129)
            clip = f'+CLIP: "{clip_number}",{number}'
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
            normalized_clcc = self._normalize_clcc(text)
            self._apply_call_state_from_clcc(normalized_clcc)
            # Forward CLCC only when the car explicitly requested it.
            if self._pending_car_clcc_requests > 0:
                self._pending_car_clcc_requests = max(0, self._pending_car_clcc_requests - 1)
                self._send_car_result(f"+CLCC: {normalized_clcc}", f"Phone HF +CLCC {text} -> Car AG +CLCC {normalized_clcc}")
                clip_from_clcc = self._clip_from_clcc(normalized_clcc)
                if clip_from_clcc:
                    self._send_car_result(clip_from_clcc, f"Phone HF +CLCC {normalized_clcc} -> Car AG {clip_from_clcc}")
                    clcc_parts = [part.strip() for part in normalized_clcc.split(",")]
                    if len(clcc_parts) >= 7:
                        self._last_clip_number = clcc_parts[5].strip().strip('"')
                        self._last_clip_type = clcc_parts[6].strip().strip('"') or "129"
                        self._call_has_real_clip = True
            else:
                self._bridge_trace(f"Ignored Phone HF +CLCC {text} because car did not request CLCC")
        elif event_code == 0x12 and text:
            self._send_car_result(f"+BIND: {text}", f"Phone HF +BIND {text} -> Car AG +BIND")
        elif event_code == 0x13:
            if not (self._is_phone_call_state_busy() or self._is_phone_incoming_call_state()):
                self._bridge_trace(
                    f"Ignored Phone HF +BCS {number} while call state is idle (prevents unsolicited codec/audio negotiation)"
                )
            else:
                self._send_car_result(f"+BCS: {number}", f"Phone HF +BCS {number} -> Car AG +BCS")
                # Some stacks emit an immediate OK/ERROR for codec negotiation without a
                # preceding car-side AT event visible to this bridge. Preserve one response.
                self._pending_car_codec_responses = min(self._pending_car_codec_responses + 1, 4)
        elif event_code == 0x00:
            if self._pending_car_at_responses > 0:
                self._pending_car_at_responses -= 1
                self._send_car_result("OK", "Phone HF OK -> Car AG OK")
            elif self._pending_car_codec_responses > 0:
                self._pending_car_codec_responses -= 1
                self._send_car_result("OK", "Phone HF codec-negotiation OK -> Car AG OK")
            else:
                self._bridge_trace("Ignored Phone HF OK because there is no pending car-side AT command")
        elif event_code == 0x01:
            if self._pending_car_at_responses > 0:
                self._pending_car_at_responses -= 1
                self._send_car_result("ERROR", "Phone HF ERROR -> Car AG ERROR")
            elif self._pending_car_codec_responses > 0:
                self._pending_car_codec_responses -= 1
                self._send_car_result("ERROR", "Phone HF codec-negotiation ERROR -> Car AG ERROR")
            else:
                self._bridge_trace("Ignored Phone HF ERROR because there is no pending car-side AT command")
        elif event_code == 0x02:
            if self._pending_car_at_responses > 0:
                self._pending_car_at_responses -= 1
                self._send_car_result(f"+CME ERROR: {number}", f"Phone HF +CME ERROR {number} -> Car AG +CME ERROR")
            elif self._pending_car_codec_responses > 0:
                self._pending_car_codec_responses -= 1
                self._send_car_result(
                    f"+CME ERROR: {number}",
                    f"Phone HF codec-negotiation +CME ERROR {number} -> Car AG +CME ERROR",
                )
            else:
                self._bridge_trace("Ignored Phone HF +CME ERROR because there is no pending car-side AT command")

    def _bridge_car_packet(self, opcode_value: int, payload: bytes) -> None:
        if not self._avrc_bridge_enabled and (opcode_value >> 8) == GROUP_AVRC_TARGET:
            return
        if opcode_value in {opcode(0x0E, 0x01), opcode(0x0E, 0x03)}:
            if not self._car_avrc_suppressed_by_hfp:
                self._car_avrc_suppressed_by_hfp = True
                self._bridge_trace("Paused Car AVRCP TG metadata/status forwarding while Car HFP AG session is active")
            self._flush_pending_car_results()
            return
        if opcode_value == opcode(0x0E, 0x02):
            if self._car_avrc_suppressed_by_hfp:
                self._car_avrc_suppressed_by_hfp = False
                self._bridge_trace("Resumed Car AVRCP TG metadata/status forwarding after Car HFP AG session closed")
                self._forward_cached_phone_avrc_to_car()
            return
        if opcode_value == EVENT_AG_AUDIO_OPEN:
            self._car_audio_open = True
            self._bridge_trace("Observed Car AG audio open")
            return
        if opcode_value == EVENT_AG_AUDIO_CLOSE:
            self._car_audio_open = False
            self._bridge_trace("Observed Car AG audio close")
            return
        if opcode_value == EVENT_AG_AT_CMD:
            handle, at_text = self._parse_ag_at_payload(payload)
            if at_text:
                at_upper = at_text.strip().upper()
                if at_upper.startswith("AT+CHLD"):
                    if at_upper == "AT+CHLD=0" and self._is_phone_incoming_call_state():
                        send_state = self._send_or_queue_phone_hf_at(
                            "AT+CHUP",
                            "Car AG CHLD=0 reject",
                            allow_stale_handle=True,
                        )
                        if send_state != "dropped":
                            self._pending_car_at_responses += 1
                            self._bridge_trace("Car AG AT AT+CHLD=0 -> Phone HF raw AT AT+CHUP (reject incoming)")
                        return
                    if at_upper == "AT+CHLD=0" and self._is_phone_single_active_call_state():
                        send_state = self._send_or_queue_phone_hf_at(
                            "AT+CHUP",
                            "Car AG CHLD=0 end active call",
                            allow_stale_handle=True,
                        )
                        if send_state != "dropped":
                            self._pending_car_at_responses += 1
                            self._bridge_trace("Car AG AT AT+CHLD=0 -> Phone HF raw AT AT+CHUP (end active call)")
                        return
                    if at_upper in {"AT+CHLD=1", "AT+CHLD=2"} and self._is_phone_incoming_call_state():
                        now = time.monotonic()
                        if now - self._last_car_ata_forward_at < 0.35:
                            self._bridge_trace(
                                f"Ignored Car AG AT {at_text} duplicate burst during incoming-call answer"
                            )
                            return
                        send_state = self._send_or_queue_phone_hf_at(
                            "ATA",
                            f"Car AG {at_text} answer",
                            allow_stale_handle=True,
                        )
                        if send_state != "dropped":
                            self._pending_car_at_responses += 1
                            self._car_answer_pending = True
                            self._last_car_ata_forward_at = now
                            self._bridge_trace(f"Car AG AT {at_text} -> Phone HF raw AT ATA (answer incoming)")
                        return
                    if self._phone_hf_cind[2] != "1" or self._phone_hf_cind[3] != "0":
                        self._bridge_trace(
                            f"Ignored Car AG AT {at_text} while call is not active/stable (prevents unsolicited auto-answer)"
                        )
                        return
                    if self.phone_session.info.service_handle <= 0:
                        self._bridge_trace(
                            f"Dropped Car AG AT {at_text} because HF service handle is unavailable (avoid stale hold/answer control)"
                        )
                        return
                if at_upper.startswith("AT+BCS"):
                    if not (self._is_phone_call_state_busy() or self._is_phone_incoming_call_state()):
                        self._bridge_trace(
                            f"Ignored Car AG AT {at_text} because call state is idle (prevents unsolicited audio negotiation)"
                        )
                        return
                if at_upper == "ATA":
                    now = time.monotonic()
                    if now - self._last_car_ata_forward_at < 0.35:
                        self._bridge_trace("Ignored Car AG AT ATA duplicate burst")
                        return
                    if not self._is_phone_answer_window():
                        self._bridge_trace("Ignored Car AG AT ATA because no valid incoming-call answer window is active")
                        return
                    send_state = self._send_or_queue_phone_hf_at("ATA", "Car AG ATA", allow_stale_handle=True)
                    if send_state != "dropped":
                        self._pending_car_at_responses += 1
                        self._car_answer_pending = True
                        self._last_car_ata_forward_at = now
                        self._bridge_trace("Car AG AT ATA -> Phone HF raw AT ATA")
                    return
                if at_upper == "AT+CHUP":
                    send_state = self._send_or_queue_phone_hf_at(
                        at_text,
                        f"Car AG AT {at_text}",
                        allow_stale_handle=True,
                    )
                elif at_upper == "AT+CLCC":
                    self._pending_car_clcc_requests += 1
                    allow_stale_clcc = self._is_phone_incoming_call_state() or self._phone_hf_cind[2] == "1"
                    send_state = self._send_or_queue_phone_hf_at(
                        at_text,
                        "Car AG CLCC request",
                        allow_stale_handle=allow_stale_clcc,
                    )
                    if send_state in {"queued", "dropped"}:
                        if self._send_cached_clcc_to_car("Car AG AT+CLCC while HF handle unavailable"):
                            self._pending_car_clcc_requests = max(0, self._pending_car_clcc_requests - 1)
                else:
                    send_state = self._send_or_queue_phone_hf_at(at_text, f"Car AG AT {at_text}")
                if send_state != "dropped":
                    self._pending_car_at_responses += 1
                    self._bridge_trace(f"Car AG AT {at_text} -> Phone HF raw AT {at_text}")
            return
        if opcode_value == EVENT_AG_CLCC_REQ:
            self._pending_car_clcc_requests += 1
            allow_stale_clcc = self._is_phone_incoming_call_state() or self._phone_hf_cind[2] == "1"
            send_state = self._send_or_queue_phone_hf_at(
                "AT+CLCC",
                "Car AG CLCC request event",
                allow_stale_handle=allow_stale_clcc,
            )
            if send_state != "dropped":
                self._pending_car_at_responses += 1
            if send_state in {"queued", "dropped"}:
                if self._send_cached_clcc_to_car("Car AG CLCC request while HF handle unavailable"):
                    self._pending_car_clcc_requests = max(0, self._pending_car_clcc_requests - 1)
            self._bridge_trace("Car AG CLCC request -> Phone HF raw AT AT+CLCC")
            return
        if opcode_value == opcode(GROUP_AVRC_TARGET, 0x03):
            self._send_phone_avrc_control("play", "Car AVRCP Play received")
        elif opcode_value == opcode(GROUP_AVRC_TARGET, 0x04):
            self._send_phone_avrc_control("stop", "Car AVRCP Stop received")
        elif opcode_value == opcode(GROUP_AVRC_TARGET, 0x05):
            self._send_phone_avrc_control("pause", "Car AVRCP Pause received")
        elif opcode_value == opcode(GROUP_AVRC_TARGET, 0x06):
            self._send_phone_avrc_control("next", "Car AVRCP Next received")
        elif opcode_value == opcode(GROUP_AVRC_TARGET, 0x07):
            self._send_phone_avrc_control("prev", "Car AVRCP Previous received")

    def _bridge_phone_ciev_to_car(self, text: str) -> tuple[Optional[int], Optional[str]]:
        parts = [part.strip() for part in text.split(",", 1)]
        if len(parts) != 2:
            return (None, None)
        try:
            phone_index = int(parts[0])
        except ValueError:
            return (None, None)
        value = parts[1]
        if not value.isdigit():
            self._bridge_trace(f"Ignored Phone HF +CIEV {text} because value is not numeric")
            return (None, None)
        self._phone_hf_cind[phone_index] = value
        self._refresh_phone_call_state(f"Phone HF +CIEV {phone_index},{value}")
        self._update_answer_pending_from_call_state()
        self._update_car_avrc_call_gate(f"Phone HF +CIEV {phone_index},{value}")
        if self._phone_hf_cind[2] == "0" and self._phone_hf_cind[3] == "0":
            self._call_has_real_clip = False
            self._last_clip_number = ""
            self._last_clip_type = "129"
            self._ring_placeholder_clip_sent = False
        elif phone_index == 3 and value == "0":
            # Ensure each new incoming-call setup phase can emit a fallback placeholder
            # if the phone delays or omits CLIP/CLCC.
            self._ring_placeholder_clip_sent = False
        if phone_index == 3 and value == "1":
            now = time.monotonic()
            # Fallback: some phone/HF stacks do not emit RING/CLIP consistently after reconnect.
            if (now - self._last_phone_ring_at) > 2.0:
                self._last_phone_ring_at = now
                self._send_car_result("RING", "Phone HF +CIEV 3,1 fallback -> Car AG RING")
            if not self._call_has_real_clip:
                self._bridge_trace("Phone HF +CIEV 3,1 fallback: waiting for real caller ID (CLIP/CLCC)")
                self._send_placeholder_clip_if_needed("Phone HF +CIEV 3,1 fallback")
            if self._last_clip_number:
                clip = f'+CLIP: "{self._last_clip_number}",{self._last_clip_type if self._last_clip_type.isdigit() else "129"}'
                self._send_car_result(clip, f"Phone HF +CIEV 3,1 fallback -> Car AG {clip}")
            self._send_synthetic_clcc("Phone HF +CIEV 3,1 fallback", 4)
        ag_index = {1: 4, 2: 1, 3: 2, 4: 3, 5: 6, 6: 7, 7: 5}.get(phone_index)
        if ag_index is None:
            return (None, None)
        self._send_car_cind_update(f"Phone HF +CIEV {phone_index},{value}")
        self._bridge_trace(
            f"Phone HF +CIEV {phone_index},{value} -> Car AG indicator {ag_index},{value} | CIND {self._current_ag_cind()}"
        )
        return (ag_index, value)

    def _bridge_phone_incoming_call_hint(self) -> None:
        changed = self._set_call_indicators("0", "1", "0")
        self._refresh_phone_call_state("Phone HF inferred incoming call")
        self._car_answer_pending = False
        if not changed:
            return
        self._send_car_cind_update("Phone HF inferred incoming call")
        self._send_car_result("+CIEV: 1,0", "Phone HF inferred incoming call -> Car AG +CIEV 1,0")
        self._send_car_result("+CIEV: 2,1", "Phone HF inferred incoming call -> Car AG +CIEV 2,1")

    def _bridge_phone_active_call_hint(self, reason: str) -> None:
        changed = self._set_call_indicators("1", "0", "0")
        self._refresh_phone_call_state(reason)
        self._update_answer_pending_from_call_state()
        if not changed:
            return
        self._send_car_cind_update(reason)
        self._send_car_result("+CIEV: 1,1", f"{reason} -> Car AG +CIEV 1,1")
        self._send_car_result("+CIEV: 2,0", f"{reason} -> Car AG +CIEV 2,0")
        self._send_car_result("+CIEV: 3,0", f"{reason} -> Car AG +CIEV 3,0")
        self._send_synthetic_clcc(reason, 0)

    def _convert_phone_cind_to_ag(self, text: str) -> str:
        values = [part.strip() for part in text.split(",")]
        if len(values) >= 7:
            for index, value in enumerate(values[:7], start=1):
                if value.isdigit():
                    self._phone_hf_cind[index] = value
                else:
                    self._bridge_trace(f"Ignored Phone HF +CIND value '{value}' at index {index} because it is not numeric")
        return self._current_ag_cind()

    def _current_ag_cind(self) -> str:
        return ",".join(
            (
                self._phone_hf_cind[2],
                self._phone_hf_cind[3],
                self._phone_hf_cind[4],
                self._phone_hf_cind[1],
                self._phone_hf_cind[7],
                self._phone_hf_cind[5],
                self._phone_hf_cind[6],
            )
        )

    def _send_car_result(self, text: str, trace: str) -> None:
        if self.car_session.info.service_handle <= 0:
            if len(self._pending_car_results) >= 60:
                self._pending_car_results.pop(0)
            self._pending_car_results.append((text, trace))
            self._bridge_trace(f"Queued Car AG send '{text}' because no AG service handle is available yet")
            return
        self.car_session.ag_send_string(text)
        self._bridge_trace(trace)

    def _flush_pending_car_results(self) -> None:
        if self.car_session.info.service_handle <= 0 or not self._pending_car_results:
            return
        self._send_car_cind_update("Flushing queued phone->car AG results")
        queued = list(self._pending_car_results)
        self._pending_car_results.clear()
        self._bridge_trace(f"Flushing {len(queued)} queued Phone->Car AG result(s)")
        for text, trace in queued:
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
        if self.car_session.info.service_handle <= 0:
            self._bridge_trace(f"Skipped Car AG audio {action} because no AG service handle is available yet")
            return
        if action == "open":
            if self._car_audio_open:
                self._bridge_trace("Skipped Car AG audio open because AG audio is already open")
                return
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

    def _normalize_clip_number(self, text: str) -> str:
        cleaned = text.strip().strip('"').strip()
        if cleaned:
            return cleaned
        return text.strip()

    def _clip_from_clcc(self, text: str) -> Optional[str]:
        parts = [part.strip() for part in text.split(",")]
        if len(parts) < 7:
            return None
        number = parts[5].strip().strip('"')
        number_type = parts[6].strip().strip('"')
        if not number:
            return None
        if not number_type.isdigit():
            number_type = "129"
        if number_type == "145" and not number.startswith("+"):
            number = f"+{number}"
        return f'+CLIP: "{number}",{number_type}'

    def _normalize_clcc(self, text: str) -> str:
        parts = [part.strip() for part in text.split(",")]
        if len(parts) < 7:
            return text
        number = parts[5].strip().strip('"')
        number_type = parts[6].strip().strip('"')
        if number_type == "145" and number and not number.startswith("+"):
            number = f"+{number}"
        parts[5] = f'"{number}"' if number else parts[5]
        parts[6] = number_type if number_type else parts[6]
        return ",".join(parts)

    def _apply_call_state_from_clcc(self, text: str) -> None:
        parts = [part.strip() for part in text.split(",")]
        if len(parts) < 3 or not parts[2].isdigit():
            return
        clcc_status = int(parts[2])
        updates = None
        if clcc_status == 0:
            updates = ("1", "0", "0")
        elif clcc_status == 1:
            updates = ("1", "0", "1")
        elif clcc_status in {2, 3}:
            updates = ("0", "2", "0")
        elif clcc_status == 4:
            updates = ("0", "1", "0")
        elif clcc_status == 5:
            updates = ("1", "1", "0")
        elif clcc_status == 6:
            updates = ("1", "0", "2")
        if updates is None:
            return
        call_val, setup_val, held_val = updates
        changed = self._set_call_indicators(call_val, setup_val, held_val)
        self._refresh_phone_call_state(f"Phone HF +CLCC status {clcc_status}")
        self._update_answer_pending_from_call_state()
        self._update_car_avrc_call_gate(f"Phone HF +CLCC status {clcc_status}")
        if not changed:
            return
        self._send_car_cind_update(f"Phone HF +CLCC status {clcc_status}")
        self._send_car_result(f"+CIEV: 1,{call_val}", f"Phone HF +CLCC status {clcc_status} -> Car AG +CIEV 1,{call_val}")
        self._send_car_result(f"+CIEV: 2,{setup_val}", f"Phone HF +CLCC status {clcc_status} -> Car AG +CIEV 2,{setup_val}")
        self._send_car_result(f"+CIEV: 3,{held_val}", f"Phone HF +CLCC status {clcc_status} -> Car AG +CIEV 3,{held_val}")

    def _derive_phone_call_state(self) -> str:
        call_val = self._phone_hf_cind[2]
        setup_val = self._phone_hf_cind[3]
        held_val = self._phone_hf_cind[4]
        if setup_val == "1":
            return CALL_STATE_INCOMING
        if call_val == "1" and held_val != "0":
            return CALL_STATE_HELD
        if call_val == "1":
            return CALL_STATE_ACTIVE
        if setup_val in {"2", "3"}:
            return CALL_STATE_OUTGOING
        if held_val != "0":
            return CALL_STATE_HELD
        return CALL_STATE_IDLE

    def _refresh_phone_call_state(self, reason: str) -> None:
        new_state = self._derive_phone_call_state()
        if new_state == self._phone_call_state:
            return
        old_state = self._phone_call_state
        self._phone_call_state = new_state
        self._bridge_trace(f"Phone call state {old_state} -> {new_state} ({reason})")
        if new_state == CALL_STATE_INCOMING:
            self._ensure_incoming_fallback_ring_refresh()
        else:
            self._cancel_incoming_fallback_ring_refresh()

    def _ensure_incoming_fallback_ring_refresh(self) -> None:
        if self._incoming_fallback_ring_after_id is not None:
            return
        self._incoming_fallback_ring_after_id = self.root.after(3000, self._incoming_fallback_ring_refresh_tick)

    def _cancel_incoming_fallback_ring_refresh(self) -> None:
        if self._incoming_fallback_ring_after_id is None:
            return
        try:
            self.root.after_cancel(self._incoming_fallback_ring_after_id)
        except tk.TclError:
            pass
        self._incoming_fallback_ring_after_id = None

    def _incoming_fallback_ring_refresh_tick(self) -> None:
        self._incoming_fallback_ring_after_id = None
        if not self._is_phone_incoming_call_state():
            return
        now = time.monotonic()
        if (now - self._last_phone_real_ring_at) > 2.0:
            self._last_phone_ring_at = now
            self._send_car_result("RING", "Phone HF incoming-state refresh -> Car AG RING")
            if not self._call_has_real_clip:
                self._send_placeholder_clip_if_needed("Phone HF incoming-state refresh")
            self._send_synthetic_clcc("Phone HF incoming-state refresh", 4)
        self._ensure_incoming_fallback_ring_refresh()

    def _send_car_cind_update(self, reason: str) -> None:
        ag_cind = self._current_ag_cind()
        if self.car_session.info.service_handle <= 0:
            self._bridge_trace(f"Deferred Car AG Set CIND {ag_cind} ({reason}) because no AG service handle is available yet")
            return
        self.car_session.ag_set_cind(ag_cind)
        self._bridge_trace(f"{reason} -> Car AG Set CIND {ag_cind}")

    def _is_phone_incoming_call_state(self) -> bool:
        return self._phone_call_state == CALL_STATE_INCOMING

    def _send_placeholder_clip_if_needed(self, reason: str) -> None:
        if self._call_has_real_clip:
            return
        if self._ring_placeholder_clip_sent:
            return
        clip = '+CLIP: "Unknown",129'
        self._send_car_result(clip, f"{reason} -> Car AG fallback {clip}")
        self._ring_placeholder_clip_sent = True

    def _send_synthetic_clcc(self, reason: str, status: int) -> None:
        number_type = self._last_clip_type if self._last_clip_type.isdigit() else "129"
        number = self._last_clip_number.strip()
        if number:
            clcc = f'+CLCC: 1,1,{status},0,0,"{number}",{number_type}'
        else:
            clcc = f'+CLCC: 1,1,{status},0,0,"",{number_type}'
        self._send_car_result(clcc, f"{reason} -> Car AG fallback {clcc}")

    def _is_phone_call_state_busy(self) -> bool:
        return self._phone_call_state != CALL_STATE_IDLE

    def _is_phone_single_active_call_state(self) -> bool:
        return (
            self._phone_call_state == CALL_STATE_ACTIVE
            and self._phone_hf_cind[2] == "1"
            and self._phone_hf_cind[3] == "0"
            and self._phone_hf_cind[4] == "0"
        )

    def _update_car_avrc_call_gate(self, reason: str) -> None:
        busy = self._is_phone_call_state_busy() or self._is_phone_incoming_call_state()
        if busy:
            if not self._car_avrc_suppressed_by_call:
                self._car_avrc_suppressed_by_call = True
                self._bridge_trace(f"Paused Car AVRCP TG metadata/status forwarding during call state ({reason})")
            return
        if self._car_avrc_suppressed_by_call:
            self._car_avrc_suppressed_by_call = False
            self._bridge_trace(f"Resumed Car AVRCP TG metadata/status forwarding after call state cleared ({reason})")
            self._forward_cached_phone_avrc_to_car()

    def _is_phone_answer_window(self) -> bool:
        # Keep answer gating driven by explicit call state, not timing windows.
        return self._is_phone_incoming_call_state()

    def _update_answer_pending_from_call_state(self) -> None:
        # Clear pending answer state as soon as the call is no longer incoming.
        if self._phone_call_state != CALL_STATE_INCOMING:
            self._car_answer_pending = False

    def _set_call_indicators(self, call_val: str, setup_val: str, held_val: str) -> bool:
        changed = False
        if self._phone_hf_cind[2] != call_val:
            self._phone_hf_cind[2] = call_val
            changed = True
        if self._phone_hf_cind[3] != setup_val:
            self._phone_hf_cind[3] = setup_val
            changed = True
        if self._phone_hf_cind[4] != held_val:
            self._phone_hf_cind[4] = held_val
            changed = True
        return changed

    def _send_or_queue_phone_hf_at(self, at_text: str, source: str, allow_stale_handle: bool = False) -> str:
        if self.phone_session.info.service_handle > 0:
            self.phone_session.hf_send_raw_at(at_text)
            return "sent"
        at_upper = at_text.strip().upper()
        is_bootstrap = self._is_bootstrap_car_ag_at(at_upper)
        if is_bootstrap:
            # Keep AG bootstrap negotiation intact across startup races.
            # Dropping these causes missing CLIP/CMER subscription and call forwarding gaps.
            if len(self._pending_phone_hf_at) >= 80:
                self._pending_phone_hf_at.pop(0)
            self._pending_phone_hf_at.append(at_text)
            self._bridge_trace(
                f"Queued {source} bootstrap AT {at_text} (waiting for HF service handle)"
            )
            return "queued"
        # For explicit user call-control actions only, allow sending on last known HF handle.
        if allow_stale_handle and self._last_phone_hf_handle > 0:
            self.phone_session.hf_send_raw_at(at_text, handle=self._last_phone_hf_handle)
            self._bridge_trace(
                f"Sent {source} -> Phone HF raw AT {at_text} using last known HF handle {self._last_phone_hf_handle}"
            )
            return "sent"
        if self._last_phone_hf_handle > 0:
            self._bridge_trace(
                f"HF service handle unavailable; refusing stale-handle send for {source} AT {at_text}"
            )
        no_queue_prefixes = ("ATA", "ATD", "AT+BLDN", "AT+VTS", "AT+CLCC", "AT+CHLD", "AT+BCS", "AT+CHUP")
        if at_upper.startswith(no_queue_prefixes):
            self._bridge_trace(
                f"Dropped {source} -> Phone HF raw AT {at_text} because HF service handle is unavailable"
            )
            return "dropped"
        # Keep queue bounded, but prefer retaining latest call-control commands.
        if len(self._pending_phone_hf_at) >= 80:
            self._pending_phone_hf_at.pop(0)
        self._pending_phone_hf_at.append(at_text)
        self._bridge_trace(f"Queued {source} -> Phone HF raw AT {at_text} (waiting for HF service handle)")
        return "queued"

    def _is_bootstrap_car_ag_at(self, at_upper: str) -> bool:
        bootstrap_prefixes = (
            "AT+BRSF",
            "AT+CIND=?",
            "AT+CIND?",
            "AT+CMER",
            "AT+CLIP=",
            "AT+CCWA=",
            "AT+XAPL",
            "AT+CNUM",
            "AT+COPS?",
            "AT+NREC",
            "AT+CGMI",
            "AT+CGMM",
            "AT+CCLK?",
            "AT+VGM=",
            "AT+VGS=",
        )
        return at_upper.startswith(bootstrap_prefixes)

    def _flush_pending_phone_hf_at(self) -> None:
        if self.phone_session.info.service_handle <= 0 or not self._pending_phone_hf_at:
            return
        queued = list(self._pending_phone_hf_at)
        self._pending_phone_hf_at.clear()
        self._bridge_trace(f"Flushing {len(queued)} queued Car->Phone HF AT command(s)")
        for at_text in queued:
            self.phone_session.hf_send_raw_at(at_text)

    def _send_cached_clcc_to_car(self, reason: str) -> bool:
        if not self._is_phone_incoming_call_state():
            return False
        if not self._last_clip_number:
            return False
        number_type = self._last_clip_type if self._last_clip_type.isdigit() else "129"
        clcc = f'+CLCC: 1,1,4,0,0,"{self._last_clip_number}",{number_type}'
        self._send_car_result(clcc, f"{reason} -> Car AG cached {clcc}")
        return True

    def _ensure_phone_avrc_ct_link(self) -> None:
        if self._phone_avrc_ct_connected:
            return
        address = self.phone_session.info.preferred_remote_address.strip()
        if not address:
            self._bridge_trace("Cannot request Phone AVRCP CT connect yet: phone peer address is unknown")
            return
        now = time.monotonic()
        if now - self._last_phone_avrc_ct_attempt_at < 5.0:
            return
        self._last_phone_avrc_ct_attempt_at = now
        self.phone_session.avrc_ct_connect(address)
        self._bridge_trace(f"Requested Phone AVRCP CT connect to {address} for metadata/control events")

    def _request_phone_avrc_tg_disconnect(self, reason: str) -> None:
        now = time.monotonic()
        if now - self._last_phone_avrc_tg_disconnect_at < 1.0:
            return
        self._last_phone_avrc_tg_disconnect_at = now
        self.phone_session.avrc_tg_disconnect()
        self._bridge_trace(f"{reason} -> requested Phone AVRCP TG disconnect so CT commands are accepted")

    def _send_phone_avrc_control(self, command: str, source: str, is_retry: bool = False) -> None:
        if not self._avrc_bridge_enabled:
            return
        action_map = {
            "play": self.phone_session.avrc_play,
            "pause": self.phone_session.avrc_pause,
            "stop": self.phone_session.avrc_stop,
            "next": self.phone_session.avrc_next,
            "prev": self.phone_session.avrc_prev,
        }
        action = action_map.get(command)
        if action is None:
            self._bridge_trace(f"Skipped forwarding {source} because AVRCP command '{command}' is unsupported")
            return
        if self._is_phone_call_state_busy() or self._is_phone_incoming_call_state():
            if not is_retry:
                self._pending_phone_avrc_retry = None
                self._phone_avrc_control_retry_remaining = 0
            self._bridge_trace(
                f"Suppressed {source} -> Phone AVRCP {command.upper()} because call state is active/incoming"
            )
            return
        if not self._phone_avrc_ct_connected:
            self._bridge_trace(
                f"Skipped forwarding {source} because phone AVRCP CT link is not connected "
                "(UI passive profile mode: no auto connect/disconnect)"
            )
            return
        if not is_retry:
            self._last_phone_avrc_control = command
            self._last_phone_avrc_control_at = time.monotonic()
            self._phone_avrc_control_retry_remaining = 1
        action()
        self._bridge_trace(f"{source} -> Phone AVRCP {command.upper()} command")

    def _queue_phone_avrc_retry(self, command: str) -> None:
        if not command:
            return
        self._pending_phone_avrc_retry = command
        if self._phone_avrc_tg_connected:
            self._request_phone_avrc_tg_disconnect("Queued phone AVRCP retry")
            return
        self.root.after(150, self._retry_pending_phone_avrc_control)

    def _retry_pending_phone_avrc_control(self) -> None:
        command = self._pending_phone_avrc_retry
        if not command:
            return
        if not self._phone_avrc_ct_connected:
            self._ensure_phone_avrc_ct_link()
            return
        if self._phone_avrc_tg_connected:
            self._request_phone_avrc_tg_disconnect("Pending phone AVRCP retry")
            return
        if self._phone_avrc_control_retry_remaining <= 0:
            self._pending_phone_avrc_retry = None
            self._bridge_trace(f"Skipped AVRCP retry for {command.upper()} because retry budget is exhausted")
            return
        self._phone_avrc_control_retry_remaining -= 1
        self._pending_phone_avrc_retry = None
        self._send_phone_avrc_control(command, "Retried Car AVRCP control", is_retry=True)

    def _learn_phone_peer_from_media_event(self, payload: bytes, opcode_value: int) -> None:
        if len(payload) < 6:
            return
        remote = ":".join(f"{value:02X}" for value in reversed(payload[:6]))
        if not remote:
            return
        if self.phone_session.info.preferred_remote_address == remote:
            return
        self.phone_session.info.preferred_remote_address = remote
        if opcode_value == opcode(GROUP_AUDIO, 0x02):
            source = "phone A2DP connected event"
        else:
            source = "phone AVRCP TG connected event"
        self._bridge_trace(f"Learned phone peer address from {source}: {remote}")

    def _is_car_avrc_tg_ready(self) -> bool:
        return self._car_avrc_tg_connected or self.car_session.info.avrc_connected

    def _parse_phone_avrc_track_info_payload(self, payload: bytes) -> Optional[tuple[int, str]]:
        if len(payload) < 6:
            return None
        attr_id = ((payload[2] << 8) | payload[3]) & 0xFF
        text_len = payload[4] | (payload[5] << 8)
        text_bytes = payload[6 : 6 + text_len]
        text = text_bytes.decode("utf-8", errors="ignore").strip("\x00")
        return (attr_id, text)

    def _parse_phone_avrc_play_state(self, payload: bytes) -> Optional[int]:
        if len(payload) >= 3:
            return payload[2]
        return None

    def _parse_phone_avrc_song_pos_ms(self, payload: bytes) -> Optional[int]:
        if len(payload) >= 6:
            return int.from_bytes(payload[2:6], "little", signed=False)
        return None

    def _duration_text_to_ms(self, text: str) -> int:
        stripped = text.strip()
        if not stripped:
            return 0
        try:
            value = int(stripped)
        except ValueError:
            return 0
        if value < 0:
            return 0
        # Phone metadata typically reports duration in seconds for AVRCP attr 0x07.
        if value < 100000:
            return value * 1000
        return value

    def _current_phone_song_len_ms(self) -> int:
        duration_text = self._phone_avrc_attr_cache.get(0x07, "")
        return self._duration_text_to_ms(duration_text)

    def _forward_current_phone_play_status_to_car(self, reason: str) -> None:
        if not self._car_tg_push_enabled:
            return
        if not self._is_car_avrc_tg_ready():
            return
        if self._car_avrc_suppressed_by_hfp:
            return
        if self._car_avrc_suppressed_by_call:
            return
        song_len_ms = self._current_phone_song_len_ms()
        signature = (self._phone_avrc_play_state, song_len_ms, self._phone_avrc_song_pos_ms)
        if signature == self._last_forwarded_status_signature:
            return
        last_state, last_len, last_pos = self._last_forwarded_status_signature
        if (
            last_state == signature[0]
            and last_len == signature[1]
            and last_pos >= 0
            and abs(signature[2] - last_pos) < 3000
            and (time.monotonic() - self._last_car_avrc_status_forward_at) < 1.0
        ):
            return
        self.car_session.avrc_tg_player_status(signature[0], signature[1], signature[2])
        self._last_forwarded_status_signature = signature
        self._last_car_avrc_status_forward_at = time.monotonic()
        self._bridge_trace(
            f"{reason} -> Car AVRCP TG player status state={signature[0]}, len_ms={signature[1]}, pos_ms={signature[2]}"
        )

    def _forward_phone_avrc_track_info_to_car(self, payload: bytes) -> None:
        parsed = self._parse_phone_avrc_track_info_payload(payload)
        if parsed is None:
            return
        attr_id, text = parsed
        if not (0x01 <= attr_id <= 0x07):
            return
        previous = self._phone_avrc_attr_cache.get(attr_id)
        self._phone_avrc_attr_cache[attr_id] = text
        if not self._car_tg_push_enabled:
            return
        if self._car_avrc_suppressed_by_hfp:
            return
        if self._car_avrc_suppressed_by_call:
            return
        if not self._is_car_avrc_tg_ready():
            return
        if previous == text:
            return
        self._schedule_car_avrc_track_flush()

    def _forward_phone_avrc_play_status_to_car(self, payload: bytes) -> None:
        state = self._parse_phone_avrc_play_state(payload)
        if state is None:
            return
        self._phone_avrc_play_state = state
        self._forward_current_phone_play_status_to_car("Phone AVRCP play status")

    def _forward_phone_avrc_position_to_car(self, payload: bytes) -> None:
        song_pos_ms = self._parse_phone_avrc_song_pos_ms(payload)
        if song_pos_ms is None:
            return
        self._phone_avrc_song_pos_ms = song_pos_ms

    def _forward_cached_phone_avrc_to_car(self) -> None:
        if not self._car_tg_push_enabled:
            return
        if not self._is_car_avrc_tg_ready():
            return
        if self._car_avrc_suppressed_by_hfp:
            return
        if self._car_avrc_suppressed_by_call:
            return
        if self._phone_avrc_attr_cache:
            self._flush_car_avrc_track_info("Re-sent cached phone AVRCP metadata to Car AVRCP TG after reconnect")
        self._forward_current_phone_play_status_to_car("Re-sent cached phone AVRCP status")

    def _schedule_car_avrc_track_flush(self) -> None:
        if self._pending_car_avrc_track_flush:
            return
        self._pending_car_avrc_track_flush = True
        self.root.after(120, self._flush_car_avrc_track_info)

    def _flush_car_avrc_track_info(self, reason: str = "Phone AVRCP track metadata") -> None:
        self._pending_car_avrc_track_flush = False
        if not self._car_tg_push_enabled:
            return
        if not self._is_car_avrc_tg_ready():
            return
        if self._car_avrc_suppressed_by_hfp:
            return
        if self._car_avrc_suppressed_by_call:
            return
        if not self._phone_avrc_attr_cache:
            return
        attributes: list[tuple[int, str]] = []
        for aid in sorted(self._phone_avrc_attr_cache):
            text = self._phone_avrc_attr_cache.get(aid, "").strip()
            # Many car head units ignore/behave poorly with zero-length metadata attributes.
            # Forward only meaningful text values.
            if not text:
                continue
            attributes.append((aid, text))
        if not attributes:
            # Keep a minimal valid title so TG receives at least one concrete attribute.
            attributes = [(0x01, "Not Provided")]
        signature = tuple(attributes)
        if signature == self._last_forwarded_track_signature:
            return
        self.car_session.avrc_tg_track_info(attributes)
        self._last_forwarded_track_signature = signature
        self._bridge_trace(f"{reason} -> Car AVRCP TG ({len(attributes)} attribute(s))")
        self._forward_current_phone_play_status_to_car("Track metadata update")

    def _describe_phone_avrc_track_info(self, payload: bytes) -> str:
        if len(payload) >= 6:
            # Observed format on this SDK:
            # [handle_le:2][attr_id_be:2][text_len_le:2][utf8_text...]
            attr_id = (payload[2] << 8) | payload[3]
            text_len = payload[4] | (payload[5] << 8)
            text_bytes = payload[6 : 6 + text_len]
            text = text_bytes.decode("utf-8", errors="ignore").strip("\x00 \r\n\t")
            attr_name = {
                0x0001: "title",
                0x0002: "artist",
                0x0003: "album",
                0x0004: "track",
                0x0005: "total tracks",
                0x0006: "genre",
                0x0007: "duration",
            }.get(attr_id, f"attr 0x{attr_id:04X}")
            if text:
                return f"Phone AVRCP Track Info observed: {attr_name}='{text}'"
            hex_text = " ".join(f"{b:02X}" for b in payload)
            return f"Phone AVRCP Track Info observed ({attr_name}, empty text, hex: {hex_text})"
        text = payload.decode("utf-8", errors="ignore").strip("\x00 \r\n\t")
        if text:
            return f"Phone AVRCP Track Info observed: {text}"
        hex_text = " ".join(f"{b:02X}" for b in payload) if payload else "none"
        return f"Phone AVRCP Track Info observed (non-text payload, hex: {hex_text})"

    def _describe_phone_avrc_play_status(self, payload: bytes) -> str:
        if not payload:
            return "Phone AVRCP Play Status observed (empty payload)"
        hex_text = " ".join(f"{b:02X}" for b in payload)
        # Observed format on this SDK: [handle_le:2][play_status:1]
        if len(payload) >= 3:
            state = payload[2]
            state_name = {
                0: "stopped",
                1: "playing",
                2: "paused",
                3: "fwd-seek",
                4: "rev-seek",
                0xFF: "error",
            }.get(state, f"unknown({state})")
            return f"Phone AVRCP Play Status observed: {state_name} (state={state}, hex: {hex_text})"
        if len(payload) >= 1:
            state = payload[0]
            return f"Phone AVRCP Play Status observed: state={state} (hex: {hex_text})"
        return f"Phone AVRCP Play Status observed (hex: {hex_text})"

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
