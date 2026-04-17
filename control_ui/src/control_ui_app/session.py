from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Callable, Optional

from .hci import (
    COMMAND_AG_CLOSE_AUDIO,
    COMMAND_AG_CONNECT,
    COMMAND_AG_DISCONNECT,
    COMMAND_AG_OPEN_AUDIO,
    COMMAND_AG_SEND_STRING,
    COMMAND_AG_SET_CIND,
    COMMAND_AUDIO_SINK_CONNECT,
    COMMAND_AUDIO_SINK_DISCONNECT,
    COMMAND_AUDIO_SRC_CONNECT,
    COMMAND_AUDIO_SRC_DISCONNECT,
    COMMAND_AVRC_CT_CONNECT,
    COMMAND_AVRC_CT_DISCONNECT,
    COMMAND_AVRC_CT_NEXT,
    COMMAND_AVRC_CT_PAUSE,
    COMMAND_AVRC_CT_PLAY,
    COMMAND_AVRC_CT_PREV,
    COMMAND_AVRC_CT_STOP,
    COMMAND_AVRC_TG_CONNECT,
    COMMAND_AVRC_TG_DISCONNECT,
    COMMAND_BOND,
    COMMAND_GET_VERSION,
    COMMAND_HF_CLOSE_AUDIO,
    COMMAND_HF_CONNECT,
    COMMAND_HF_DISCONNECT,
    COMMAND_HF_OPEN_AUDIO,
    COMMAND_HF_SEND_RAW_AT,
    COMMAND_INQUIRY,
    COMMAND_PIN_REPLY,
    COMMAND_READ_LOCAL_BDA,
    COMMAND_SET_PAIRING_MODE,
    COMMAND_SET_VISIBILITY,
    COMMAND_UNBOND_DEVICE,
    COMMAND_USER_CONFIRMATION,
    EVENT_CONNECTED_DEVICE_NAME,
    EVENT_DEVICE_STARTED,
    EVENT_INQUIRY_COMPLETE,
    EVENT_INQUIRY_RESULT,
    EVENT_MISC_BRIDGE_IDENTITY,
    EVENT_MISC_VERSION,
    EVENT_PAIRING_COMPLETE,
    EVENT_PIN_REQUEST,
    EVENT_READ_LOCAL_BDA,
    EVENT_USER_CONFIRMATION,
    Packet,
    bd_addr_to_command,
    bd_addr_to_display,
    decode_eir_name,
    decode_rx_message,
    decode_tx_message,
    encode_handle_text,
    encode_pin_reply,
    encode_user_confirmation_reply,
    encode_wiced_command,
    opcode,
    parse_version_payload,
    try_extract_packet,
)
from .models import RemoteDevice, SessionInfo

try:
    import serial
    from serial.tools import list_ports
except Exception as exc:  # pragma: no cover - dependency may be absent locally
    serial = None
    list_ports = None
    SERIAL_IMPORT_ERROR = str(exc)
else:
    SERIAL_IMPORT_ERROR = ""


EventSink = Callable[[str, dict], None]


@dataclass
class SerialPortInfo:
    device: str
    description: str
    manufacturer: str = ""
    product: str = ""
    serial_number: str = ""
    hwid: str = ""
    vid: Optional[int] = None
    pid: Optional[int] = None
    interface: str = ""

    def dropdown_label(self) -> str:
        primary = self.product or self.description or self.manufacturer or "Serial device"
        vendor = self.manufacturer or "USB"
        return f"{self.device} | {primary} | {vendor} | WICED HCI"

    def short_label(self) -> str:
        return self.dropdown_label()

    def detail_lines(self) -> list[str]:
        lines = [f"Port: {self.device}"]
        if self.description:
            lines.append(f"Description: {self.description}")
        if self.product:
            lines.append(f"Product: {self.product}")
        if self.manufacturer:
            lines.append(f"Manufacturer: {self.manufacturer}")
        if self.serial_number:
            lines.append(f"USB Serial: {self.serial_number}")
        if self.vid is not None and self.pid is not None:
            lines.append(f"VID:PID: {self.vid:04X}:{self.pid:04X}")
        if self.interface:
            lines.append(f"Interface: {self.interface}")
        if self.hwid:
            lines.append(f"HWID: {self.hwid}")
        lines.append("Control link: WICED HCI over USB serial")
        return lines


class SerialBridgeSession:
    def __init__(self, info: SessionInfo, event_sink: EventSink) -> None:
        self.info = info
        self._event_sink = event_sink
        self._serial: Optional[serial.Serial] = None if serial else None
        self._reader_thread: Optional[threading.Thread] = None
        self._sequence_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._last_command_at = 0.0
        self._pending_ag_auto_connect_address: Optional[str] = None

    @staticmethod
    def serial_supported() -> bool:
        return serial is not None

    @staticmethod
    def list_ports() -> list[SerialPortInfo]:
        if list_ports is None:
            return []
        ports = []
        for port in list_ports.comports():
            ports.append(
                SerialPortInfo(
                    device=port.device,
                    description=port.description or port.device,
                    manufacturer=getattr(port, "manufacturer", "") or "",
                    product=getattr(port, "product", "") or "",
                    serial_number=getattr(port, "serial_number", "") or "",
                    hwid=getattr(port, "hwid", "") or "",
                    vid=getattr(port, "vid", None),
                    pid=getattr(port, "pid", None),
                    interface=getattr(port, "interface", "") or "",
                )
            )
        return sorted(ports, key=lambda item: item.device)

    def open(self, port: str, baud_rate: Optional[int] = None) -> bool:
        if serial is None:
            self._log(f"pyserial is not available: {SERIAL_IMPORT_ERROR}")
            return False
        if self.info.is_open:
            self.close()
        self.info.port = port.strip()
        if baud_rate is not None:
            self.info.baud_rate = int(baud_rate)
        self.info.bridge_identity = ""
        self.info.local_bda = ""
        self.info.sdk_version = ""
        self.info.chip = ""
        self.info.supported_groups.clear()
        self.info.discovered_devices.clear()
        self.info.ag_connected = False
        self.info.avrc_connected = False
        self.info.a2dp_connected = False
        self._buffer.clear()
        self._stop_event.clear()
        try:
            self._serial = serial.Serial(self.info.port, self.info.baud_rate, timeout=0.2)
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
        except Exception as exc:
            self._serial = None
            self.info.is_open = False
            self.info.last_status = f"Open failed: {exc}"
            self._emit("state", status=self.info.last_status)
            self._log(self.info.last_status)
            return False
        self.info.is_open = True
        self.info.last_status = f"Opened {self.info.port}"
        self._reader_thread = threading.Thread(target=self._reader_loop, name=f"serial-{self.info.label}", daemon=True)
        self._reader_thread.start()
        self._emit("state", status=self.info.last_status)
        self._log(f"Opened serial link on {self.info.port}")
        self.request_version()
        self.request_local_bda()
        return True

    def close(self) -> None:
        with self._close_lock:
            already_closed = not self.info.is_open and self._serial is None
            reader_thread = self._reader_thread
            sequence_thread = self._sequence_thread
            self._stop_event.set()
            serial_port = self._serial
            self._serial = None
            self._buffer.clear()

            if serial_port is not None:
                try:
                    if hasattr(serial_port, "cancel_read"):
                        serial_port.cancel_read()
                except Exception:
                    pass
                try:
                    if hasattr(serial_port, "cancel_write"):
                        serial_port.cancel_write()
                except Exception:
                    pass
                try:
                    serial_port.close()
                except Exception:
                    pass

            current_thread = threading.current_thread()
            if reader_thread is not None and reader_thread.is_alive() and reader_thread is not current_thread:
                reader_thread.join(timeout=1.0)
            if sequence_thread is not None and sequence_thread.is_alive() and sequence_thread is not current_thread:
                sequence_thread.join(timeout=1.0)

            self._reader_thread = None
            self._sequence_thread = None
            self.info.is_open = False
            self.info.ag_connected = False
            self.info.avrc_connected = False
            self.info.a2dp_connected = False
            self.info.service_handle = 0
            self.info.avrc_handle = 0
            self.info.last_status = "Closed"
            self._emit("state", status=self.info.last_status)
            if not already_closed:
                self._log("Closed serial session and released COM port")

    def request_version(self) -> None:
        self.send(COMMAND_GET_VERSION)

    def request_local_bda(self) -> None:
        self.send(COMMAND_READ_LOCAL_BDA)

    def start_inquiry(self) -> None:
        self.send(COMMAND_INQUIRY, b"\x01")

    def stop_inquiry(self) -> None:
        self.send(COMMAND_INQUIRY, b"\x00")

    def set_visibility(self, discoverable: bool, connectable: bool) -> None:
        self.send(COMMAND_SET_VISIBILITY, bytes([1 if discoverable else 0, 1 if connectable else 0]))

    def set_pairing_mode(self, enabled: bool) -> None:
        self.send(COMMAND_SET_PAIRING_MODE, bytes([1 if enabled else 0]))

    def apply_pairable_visibility(self, pairable: bool, visible: bool) -> None:
        self.set_pairing_mode(pairable)
        connectable = True
        self.set_visibility(visible, connectable)
        self._log(
            "Applied board visibility settings: "
            f"pairable={'yes' if pairable else 'no'}, "
            f"discoverable={'yes' if visible else 'no'}, "
            f"connectable={'yes' if connectable else 'no'}"
        )

    def enable_phone_pairing(self) -> None:
        self.apply_pairable_visibility(True, True)

    def bond(self, address: str) -> None:
        self._remember_remote(address)
        self.send(COMMAND_BOND, bd_addr_to_command(address))

    def unbond(self, address: str) -> None:
        self.send(COMMAND_UNBOND_DEVICE, bd_addr_to_command(address))

    def hf_connect(self, address: str) -> None:
        self._remember_remote(address)
        self.send(COMMAND_HF_CONNECT, bd_addr_to_command(address))

    def hf_disconnect(self) -> None:
        payload = b""
        if self.info.service_handle > 0:
            payload = bytes([self.info.service_handle & 0xFF, (self.info.service_handle >> 8) & 0xFF])
        self.send(COMMAND_HF_DISCONNECT, payload)

    def hf_audio_open(self) -> None:
        payload = b""
        if self.info.service_handle > 0:
            payload = bytes([self.info.service_handle & 0xFF, (self.info.service_handle >> 8) & 0xFF])
        self.send(COMMAND_HF_OPEN_AUDIO, payload)

    def hf_audio_close(self) -> None:
        payload = b""
        if self.info.service_handle > 0:
            payload = bytes([self.info.service_handle & 0xFF, (self.info.service_handle >> 8) & 0xFF])
        self.send(COMMAND_HF_CLOSE_AUDIO, payload)

    def hf_send_raw_at(self, text: str, handle: Optional[int] = None) -> None:
        rfcomm_handle = handle if handle is not None else self.info.service_handle
        if rfcomm_handle <= 0:
            self._log("Cannot send HF AT because no HF service handle is available")
            return
        command_text = text.strip()
        if not command_text:
            self._log("Cannot send an empty HF AT command")
            return
        if not command_text.upper().startswith("AT"):
            command_text = f"AT{command_text}"
        if not command_text.endswith("\r"):
            command_text += "\r"
        self.send(COMMAND_HF_SEND_RAW_AT, encode_handle_text(rfcomm_handle, command_text))

    def ag_connect(self, address: str) -> None:
        self._remember_remote(address)
        self.send(COMMAND_AG_CONNECT, bd_addr_to_command(address))

    def ag_disconnect(self) -> None:
        payload = b""
        if self.info.service_handle > 0:
            payload = bytes([self.info.service_handle & 0xFF, (self.info.service_handle >> 8) & 0xFF])
        self.send(COMMAND_AG_DISCONNECT, payload)

    def ag_audio_open(self) -> None:
        payload = b""
        if self.info.service_handle > 0:
            payload = bytes([self.info.service_handle & 0xFF, (self.info.service_handle >> 8) & 0xFF])
        self.send(COMMAND_AG_OPEN_AUDIO, payload)

    def ag_audio_close(self) -> None:
        payload = b""
        if self.info.service_handle > 0:
            payload = bytes([self.info.service_handle & 0xFF, (self.info.service_handle >> 8) & 0xFF])
        self.send(COMMAND_AG_CLOSE_AUDIO, payload)

    def ag_set_cind(self, cind_values: str) -> None:
        self.send(COMMAND_AG_SET_CIND, cind_values.encode("ascii", errors="ignore"))

    def ag_send_string(self, text: str, handle: Optional[int] = None) -> None:
        app_handle = handle if handle is not None else self.info.service_handle
        if app_handle <= 0:
            self._log("Cannot send AG text because no AG service handle is available")
            return
        self.send(COMMAND_AG_SEND_STRING, encode_handle_text(app_handle, text))

    def a2dp_sink_connect(self, address: str) -> None:
        self._remember_remote(address)
        self.send(COMMAND_AUDIO_SINK_CONNECT, bd_addr_to_command(address))

    def a2dp_sink_disconnect(self) -> None:
        self.send(COMMAND_AUDIO_SINK_DISCONNECT)

    def a2dp_source_connect(self, address: str) -> None:
        self._remember_remote(address)
        self.send(COMMAND_AUDIO_SRC_CONNECT, bd_addr_to_command(address))

    def a2dp_source_disconnect(self) -> None:
        self.send(COMMAND_AUDIO_SRC_DISCONNECT)

    def avrc_ct_connect(self, address: str) -> None:
        self._remember_remote(address)
        self.send(COMMAND_AVRC_CT_CONNECT, bd_addr_to_command(address))

    def avrc_ct_disconnect(self) -> None:
        self.send(COMMAND_AVRC_CT_DISCONNECT)

    def avrc_tg_connect(self, address: str) -> None:
        self._remember_remote(address)
        self.send(COMMAND_AVRC_TG_CONNECT, bd_addr_to_command(address))

    def avrc_tg_disconnect(self) -> None:
        self.send(COMMAND_AVRC_TG_DISCONNECT)

    def avrc_play(self) -> None:
        self.send(COMMAND_AVRC_CT_PLAY)

    def avrc_pause(self) -> None:
        self.send(COMMAND_AVRC_CT_PAUSE)

    def avrc_stop(self) -> None:
        self.send(COMMAND_AVRC_CT_STOP)

    def avrc_next(self) -> None:
        self.send(COMMAND_AVRC_CT_NEXT)

    def avrc_prev(self) -> None:
        self.send(COMMAND_AVRC_CT_PREV)

    def reply_user_confirmation(self, raw_bda: bytes, accepted: bool) -> None:
        self.send(COMMAND_USER_CONFIRMATION, encode_user_confirmation_reply(raw_bda, accepted))

    def reply_pin(self, raw_bda: bytes, pin: str) -> None:
        self.send(COMMAND_PIN_REPLY, encode_pin_reply(raw_bda, pin))

    def reconnect_preferred(self, side: str) -> None:
        address = self.info.preferred_remote_address.strip()
        if not address:
            self._log("No preferred remote address is saved")
            return
        if side == "phone":
            self.hf_connect(address)
            self.a2dp_sink_connect(address)
            self.avrc_ct_connect(address)
        else:
            self.ag_connect(address)
            self.a2dp_source_connect(address)
            self.avrc_tg_connect(address)

    def connect_previous_ag(self) -> None:
        address = self.info.preferred_remote_address.strip()
        if not address:
            self._log("No previous car-side address is saved")
            return
        if not self.info.is_open:
            self._log("Open the car-side serial session before starting one-step connect")
            return
        if self._sequence_thread is not None and self._sequence_thread.is_alive():
            self._log("AG one-step connect is already running")
            return
        self._sequence_thread = threading.Thread(
            target=self._run_ag_connect_previous,
            args=(address,),
            name=f"ag-connect-{self.info.label}",
            daemon=True,
        )
        self._sequence_thread.start()

    def pair_ag_device(self, address: str) -> None:
        if not address:
            self._log("No car-side address was provided for pairing")
            return
        if not self.info.is_open:
            self._log("Open the car-side serial session before starting one-click pair")
            return
        if self._sequence_thread is not None and self._sequence_thread.is_alive():
            self._log("AG one-click pair is already running")
            return
        self._sequence_thread = threading.Thread(
            target=self._run_ag_pair_sequence,
            args=(address,),
            name=f"ag-pair-{self.info.label}",
            daemon=True,
        )
        self._sequence_thread.start()

    def _run_ag_connect_previous(self, address: str) -> None:
        steps: list[tuple[str, Callable[[], None], float]] = [
            ("Disconnecting old AG service link", self.ag_disconnect, 0.6),
            ("Disconnecting old A2DP source link", self.a2dp_source_disconnect, 0.6),
            ("Disconnecting old AVRCP target link", self.avrc_tg_disconnect, 0.6),
            (f"Removing old bond for {address}", lambda: self.unbond(address), 1.0),
            (f"Creating fresh bond with {address}", lambda: self.bond(address), 1.6),
            (f"Connecting AG profile to {address}", lambda: self.ag_connect(address), 0.8),
            (f"Connecting A2DP source profile to {address}", lambda: self.a2dp_source_connect(address), 0.8),
            (f"Connecting AVRCP target profile to {address}", lambda: self.avrc_tg_connect(address), 0.8),
        ]
        self._remember_remote(address)
        self._log(f"Starting AG one-step reconnect for {address}")
        for label, action, wait_seconds in steps:
            if self._stop_event.is_set() or not self.info.is_open:
                self._log("AG one-step reconnect stopped because the session was closed")
                return
            self._log(label)
            action()
            if self._stop_event.wait(wait_seconds):
                self._log("AG one-step reconnect interrupted while waiting for the next step")
                return
        self._log("AG one-step reconnect finished")

    def _run_ag_pair_sequence(self, address: str) -> None:
        steps: list[tuple[str, Callable[[], None], float]] = [
            ("Disconnecting old AG service link", self.ag_disconnect, 0.6),
            ("Disconnecting old A2DP source link", self.a2dp_source_disconnect, 0.6),
            ("Disconnecting old AVRCP target link", self.avrc_tg_disconnect, 0.6),
            (f"Removing old bond for {address}", lambda: self.unbond(address), 1.0),
            (f"Starting fresh bond with {address}", lambda: self.bond(address), 1.6),
        ]
        self._remember_remote(address)
        self._pending_ag_auto_connect_address = address
        self._log(f"Starting AG one-click pair for {address}")
        for label, action, wait_seconds in steps:
            if self._stop_event.is_set() or not self.info.is_open:
                self._pending_ag_auto_connect_address = None
                self._log("AG one-click pair stopped because the session was closed")
                return
            self._log(label)
            action()
            if self._stop_event.wait(wait_seconds):
                self._pending_ag_auto_connect_address = None
                self._log("AG one-click pair interrupted while waiting for the next step")
                return
        self._log("AG bond started; respond to any PIN or numeric comparison prompts if shown")

    def _start_ag_profile_connect_after_pair(self, address: str) -> None:
        if self._stop_event.is_set() or not self.info.is_open:
            self._log("AG profile connect skipped because the session is closed")
            return
        if self._sequence_thread is not None and self._sequence_thread.is_alive():
            self._log("AG profile connect is waiting for the current sequence to finish")
            return
        self._sequence_thread = threading.Thread(
            target=self._run_ag_profile_connect_sequence,
            args=(address,),
            name=f"ag-profile-connect-{self.info.label}",
            daemon=True,
        )
        self._sequence_thread.start()

    def _run_ag_profile_connect_sequence(self, address: str) -> None:
        steps: list[tuple[str, Callable[[], None], float]] = [
            (f"Connecting AG profile to {address}", lambda: self.ag_connect(address), 1.0),
            (f"Connecting A2DP source profile to {address}", lambda: self.a2dp_source_connect(address), 1.0),
            (f"Connecting AVRCP target profile to {address}", lambda: self.avrc_tg_connect(address), 1.0),
        ]
        self._remember_remote(address)
        self._log(f"Pairing completed; connecting AG profiles for {address}")
        for label, action, wait_seconds in steps:
            if self._stop_event.is_set() or not self.info.is_open:
                self._log("AG profile connect stopped because the session was closed")
                return
            self._log(label)
            action()
            if self._stop_event.wait(wait_seconds):
                self._log("AG profile connect interrupted while waiting for the next step")
                return
        self._log("AG one-click pair finished with AG, A2DP, and AVRCP connect attempts")

    def send(self, opcode_value: int, payload: bytes = b"") -> bool:
        if not self.info.is_open or self._serial is None:
            self._log("Cannot send a command while the serial port is closed")
            return False
        packet = encode_wiced_command(opcode_value, payload)
        try:
            with self._lock:
                self._serial.write(packet)
                self._serial.flush()
        except Exception as exc:
            self.info.last_status = f"Write failed: {exc}"
            self._emit("state", status=self.info.last_status)
            self._log(self.info.last_status)
            self.close()
            return False
        self._last_command_at = time.time()
        self._log(decode_tx_message(opcode_value, payload))
        return True

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            serial_port = self._serial
            if serial_port is None:
                break
            try:
                chunk = serial_port.read(512)
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                self.info.last_status = f"Read failed: {exc}"
                self._emit("state", status=self.info.last_status)
                self._log(self.info.last_status)
                break
            if not chunk:
                continue
            self._buffer.extend(chunk)
            while True:
                packet = try_extract_packet(self._buffer)
                if packet is None:
                    break
                self._handle_packet(packet)
        if not self._stop_event.is_set():
            self.close()

    def _handle_packet(self, packet: Packet) -> None:
        message = decode_rx_message(packet.opcode, packet.payload)
        self._log(message)

        if packet.opcode == EVENT_DEVICE_STARTED:
            self.request_version()
            self.request_local_bda()
            self.info.last_status = "Board started"
        elif packet.opcode == EVENT_MISC_VERSION:
            version, chip, groups = parse_version_payload(packet.payload)
            self.info.sdk_version = version
            self.info.chip = chip
            self.info.supported_groups = groups
            self.info.last_status = "Firmware info received"
        elif packet.opcode == EVENT_MISC_BRIDGE_IDENTITY:
            self.info.bridge_identity = packet.payload.decode("utf-8", errors="ignore").strip("\x00")
            self.info.last_status = f"Identity detected: {self.info.bridge_identity}"
        elif packet.opcode == EVENT_READ_LOCAL_BDA and len(packet.payload) >= 6:
            self.info.local_bda = bd_addr_to_display(packet.payload[:6])
        elif packet.opcode == EVENT_INQUIRY_RESULT and len(packet.payload) >= 10:
            address = bd_addr_to_display(reversed(packet.payload[:6]))
            cod = " ".join(f"{value:02X}" for value in packet.payload[6:9])
            rssi = packet.payload[9] if packet.payload[9] < 128 else packet.payload[9] - 256
            name = decode_eir_name(packet.payload[10:])
            device = self.info.discovered_devices.get(address, RemoteDevice(address=address))
            device.name = name or device.name
            device.cod = cod
            device.rssi = rssi
            device.source = self.info.label
            self.info.discovered_devices[address] = device
        elif packet.opcode == EVENT_CONNECTED_DEVICE_NAME and len(packet.payload) >= 7:
            address = bd_addr_to_display(reversed(packet.payload[:6]))
            name = packet.payload[6:].decode("utf-8", errors="ignore").strip("\x00")
            device = self.info.discovered_devices.get(address, RemoteDevice(address=address))
            device.name = name or device.name
            self.info.discovered_devices[address] = device
        elif packet.opcode == EVENT_USER_CONFIRMATION and len(packet.payload) >= 10:
            numeric_value = packet.payload[6] | (packet.payload[7] << 8) | (packet.payload[8] << 16) | (packet.payload[9] << 24)
            self._emit(
                "user_confirmation",
                raw_bda=bytes(packet.payload[:6]),
                address=bd_addr_to_display(packet.payload[:6]),
                numeric_value=numeric_value,
            )
        elif packet.opcode == EVENT_PIN_REQUEST and len(packet.payload) >= 6:
            self._emit(
                "pin_request",
                raw_bda=bytes(packet.payload[:6]),
                address=bd_addr_to_display(packet.payload[:6]),
            )
        elif packet.opcode == opcode(0x03, 0x01):
            if len(packet.payload) >= 2:
                self.info.service_handle = packet.payload[0] | (packet.payload[1] << 8)
            self.info.last_status = "HF service opened"
        elif packet.opcode == opcode(0x03, 0x03):
            self.info.ag_connected = True
            if len(packet.payload) >= 2:
                self.info.service_handle = packet.payload[0] | (packet.payload[1] << 8)
            self.info.last_status = "HF service connected"
        elif packet.opcode == opcode(0x03, 0x04):
            self.info.ag_connected = False
            self.info.service_handle = 0
            self.info.last_status = "HF service disconnected"
        elif packet.opcode == opcode(0x0E, 0x01):
            if len(packet.payload) >= 2:
                self.info.service_handle = packet.payload[0] | (packet.payload[1] << 8)
            self.info.last_status = "AG service opened"
        elif packet.opcode == opcode(0x0E, 0x03):
            self.info.ag_connected = True
            if len(packet.payload) >= 2:
                self.info.service_handle = packet.payload[0] | (packet.payload[1] << 8)
            self.info.last_status = "AG service connected"
        elif packet.opcode == opcode(0x0E, 0x02):
            self.info.ag_connected = False
            self.info.service_handle = 0
            self.info.last_status = "AG service disconnected"
        elif packet.opcode in {opcode(0x11, 0x01), opcode(0x07, 0x01)}:
            self.info.avrc_connected = True
            if len(packet.payload) >= 8:
                self.info.avrc_handle = packet.payload[6] | (packet.payload[7] << 8)
            self.info.last_status = "AVRCP connected"
        elif packet.opcode in {opcode(0x11, 0x02), opcode(0x07, 0x02)}:
            self.info.avrc_connected = False
            self.info.avrc_handle = 0
            self.info.last_status = "AVRCP disconnected"
        elif packet.opcode in {opcode(0x05, 0x02), opcode(0x14, 0x02)}:
            self.info.a2dp_connected = True
            self.info.last_status = "A2DP connected"
        elif packet.opcode in {opcode(0x05, 0x05), opcode(0x14, 0x05)}:
            self.info.a2dp_connected = False
            self.info.last_status = "A2DP disconnected"
        elif packet.opcode == EVENT_PAIRING_COMPLETE and packet.payload:
            self.info.last_status = f"Pairing result: {packet.payload[0]}"
            pending_address = self._pending_ag_auto_connect_address
            self._pending_ag_auto_connect_address = None
            if pending_address:
                if packet.payload[0] == 0:
                    self._start_ag_profile_connect_after_pair(pending_address)
                else:
                    self._log(f"AG pairing failed for {pending_address}; skipping profile connects")
        elif packet.opcode == EVENT_INQUIRY_COMPLETE:
            self.info.last_status = "Inquiry complete"

        self._emit("state", status=self.info.last_status)
        self._emit("packet", opcode=packet.opcode, payload=packet.payload, message=message)

    def _remember_remote(self, address: str) -> None:
        self.info.preferred_remote_address = address
        device = self.info.discovered_devices.get(address)
        self.info.preferred_remote_name = device.name if device else self.info.preferred_remote_name

    def _emit(self, kind: str, **payload: object) -> None:
        self._event_sink(kind, payload)

    def _log(self, message: str) -> None:
        self._emit("log", message=message)
