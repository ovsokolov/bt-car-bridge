from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Callable, Optional

from .models import SessionInfo

try:
    import serial
    from serial.tools import list_ports
except Exception as exc:  # pragma: no cover
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
        return f"{self.device} | {primary} | {vendor}"


class SerialBridgeSession:
    def __init__(self, info: SessionInfo, event_sink: EventSink) -> None:
        self.info = info
        self._event_sink = event_sink
        self._serial: Optional[serial.Serial] = None if serial else None
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._line_buffer = bytearray()
        self._tx_lock = threading.Lock()
        self._close_lock = threading.Lock()

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
        self.info.relay_rx_lines = 0
        self.info.relay_tx_lines = 0
        self.info.relay_errors = 0
        self._line_buffer.clear()
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
        return True

    def close(self) -> None:
        with self._close_lock:
            already_closed = not self.info.is_open and self._serial is None
            self._stop_event.set()
            serial_port = self._serial
            self._serial = None
            self._line_buffer.clear()
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
            reader_thread = self._reader_thread
            if reader_thread is not None and reader_thread.is_alive() and reader_thread is not threading.current_thread():
                reader_thread.join(timeout=1.0)
            self._reader_thread = None
            self.info.is_open = False
            self.info.last_status = "Closed"
            self._emit("state", status=self.info.last_status)
            if not already_closed:
                self._log("Closed serial session")

    def send_line(self, line: str) -> bool:
        serial_port = self._serial
        if not self.info.is_open or serial_port is None:
            self.info.relay_errors += 1
            self._log("Relay dropped: destination port is closed")
            return False
        text = line.rstrip("\r\n")
        payload = (text + "\n").encode("utf-8", errors="replace")
        try:
            with self._tx_lock:
                serial_port.write(payload)
                serial_port.flush()
        except Exception as exc:
            self.info.relay_errors += 1
            self.info.last_status = f"Write failed: {exc}"
            self._emit("state", status=self.info.last_status)
            self._log(self.info.last_status)
            return False
        self.info.relay_tx_lines += 1
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
                self.info.relay_errors += 1
                self.info.last_status = f"Read failed: {exc}"
                self._emit("state", status=self.info.last_status)
                self._log(self.info.last_status)
                break
            if not chunk:
                continue
            self._line_buffer.extend(chunk)
            while True:
                newline_index = self._line_buffer.find(b"\n")
                if newline_index < 0:
                    break
                raw = bytes(self._line_buffer[:newline_index])
                del self._line_buffer[:newline_index + 1]
                line = raw.decode("utf-8", errors="replace").rstrip("\r")
                self.info.relay_rx_lines += 1
                self._emit("line", line=line)
        if not self._stop_event.is_set():
            self.close()

    def _emit(self, kind: str, **payload: object) -> None:
        self._event_sink(kind, payload)

    def _log(self, message: str) -> None:
        self._emit("log", message=message)
