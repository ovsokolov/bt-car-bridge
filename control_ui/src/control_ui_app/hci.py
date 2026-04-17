from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


HCI_WICED_PKT = 0x19

GROUP_DEVICE = 0x00
GROUP_HF = 0x03
GROUP_AUDIO = 0x05
GROUP_AVRC_TARGET = 0x07
GROUP_AG = 0x0E
GROUP_AVRC_CONTROLLER = 0x11
GROUP_AUDIO_SINK = 0x14
GROUP_MISC = 0xFF


GROUP_NAMES = {
    GROUP_DEVICE: "Device",
    GROUP_HF: "Hands-Free",
    GROUP_AUDIO: "A2DP Source",
    GROUP_AVRC_TARGET: "AVRCP Target",
    GROUP_AG: "Audio Gateway",
    GROUP_AVRC_CONTROLLER: "AVRCP Controller",
    GROUP_AUDIO_SINK: "A2DP Sink",
    GROUP_MISC: "Misc",
}


def opcode(group: int, code: int) -> int:
    return ((group & 0xFF) << 8) | (code & 0xFF)


COMMAND_INQUIRY = opcode(GROUP_DEVICE, 0x07)
COMMAND_SET_VISIBILITY = opcode(GROUP_DEVICE, 0x08)
COMMAND_SET_PAIRING_MODE = opcode(GROUP_DEVICE, 0x09)
COMMAND_UNBOND = opcode(GROUP_DEVICE, 0x0A)
COMMAND_USER_CONFIRMATION = opcode(GROUP_DEVICE, 0x0B)
COMMAND_BOND = opcode(GROUP_DEVICE, 0x10)
COMMAND_UNBOND_DEVICE = opcode(GROUP_DEVICE, 0x13)
COMMAND_PIN_REPLY = opcode(GROUP_DEVICE, 0x15)
COMMAND_READ_LOCAL_BDA = opcode(GROUP_DEVICE, 0x0F)
COMMAND_GET_VERSION = opcode(GROUP_MISC, 0x02)

COMMAND_HF_CONNECT = opcode(GROUP_HF, 0x01)
COMMAND_HF_DISCONNECT = opcode(GROUP_HF, 0x02)
COMMAND_HF_OPEN_AUDIO = opcode(GROUP_HF, 0x03)
COMMAND_HF_CLOSE_AUDIO = opcode(GROUP_HF, 0x04)

COMMAND_AG_CONNECT = opcode(GROUP_AG, 0x01)
COMMAND_AG_DISCONNECT = opcode(GROUP_AG, 0x02)
COMMAND_AG_OPEN_AUDIO = opcode(GROUP_AG, 0x03)
COMMAND_AG_CLOSE_AUDIO = opcode(GROUP_AG, 0x04)

COMMAND_AVRC_CT_CONNECT = opcode(GROUP_AVRC_CONTROLLER, 0x01)
COMMAND_AVRC_CT_DISCONNECT = opcode(GROUP_AVRC_CONTROLLER, 0x02)
COMMAND_AVRC_CT_PLAY = opcode(GROUP_AVRC_CONTROLLER, 0x03)
COMMAND_AVRC_CT_STOP = opcode(GROUP_AVRC_CONTROLLER, 0x04)
COMMAND_AVRC_CT_PAUSE = opcode(GROUP_AVRC_CONTROLLER, 0x05)
COMMAND_AVRC_CT_NEXT = opcode(GROUP_AVRC_CONTROLLER, 0x06)
COMMAND_AVRC_CT_PREV = opcode(GROUP_AVRC_CONTROLLER, 0x07)
COMMAND_AVRC_TG_CONNECT = opcode(GROUP_AVRC_TARGET, 0x01)
COMMAND_AVRC_TG_DISCONNECT = opcode(GROUP_AVRC_TARGET, 0x02)
COMMAND_AUDIO_SRC_CONNECT = opcode(GROUP_AUDIO, 0x01)
COMMAND_AUDIO_SRC_DISCONNECT = opcode(GROUP_AUDIO, 0x02)
COMMAND_AUDIO_SINK_CONNECT = opcode(GROUP_AUDIO_SINK, 0x01)
COMMAND_AUDIO_SINK_DISCONNECT = opcode(GROUP_AUDIO_SINK, 0x02)

EVENT_AG_OPEN = opcode(GROUP_AG, 0x01)
EVENT_AG_CLOSE = opcode(GROUP_AG, 0x02)
EVENT_AG_CONNECTED = opcode(GROUP_AG, 0x03)
EVENT_AG_AUDIO_OPEN = opcode(GROUP_AG, 0x04)
EVENT_AG_AUDIO_CLOSE = opcode(GROUP_AG, 0x05)
EVENT_AG_AT_CMD = opcode(GROUP_AG, 0x06)

EVENT_AVRC_TG_CONNECTED = opcode(GROUP_AVRC_TARGET, 0x01)
EVENT_AVRC_TG_DISCONNECTED = opcode(GROUP_AVRC_TARGET, 0x02)

EVENT_AUDIO_SRC_COMMAND_STATUS = opcode(GROUP_AUDIO, 0x01)
EVENT_AUDIO_SRC_CONNECTED = opcode(GROUP_AUDIO, 0x02)
EVENT_AUDIO_SRC_CONNECTION_FAILED = opcode(GROUP_AUDIO, 0x04)
EVENT_AUDIO_SRC_DISCONNECTED = opcode(GROUP_AUDIO, 0x05)

EVENT_DEVICE_STARTED = opcode(GROUP_DEVICE, 0x05)
EVENT_INQUIRY_RESULT = opcode(GROUP_DEVICE, 0x06)
EVENT_INQUIRY_COMPLETE = opcode(GROUP_DEVICE, 0x07)
EVENT_PAIRING_COMPLETE = opcode(GROUP_DEVICE, 0x08)
EVENT_COMMAND_STATUS = opcode(GROUP_DEVICE, 0x01)
EVENT_USER_CONFIRMATION = opcode(GROUP_DEVICE, 0x0B)
EVENT_CONNECTED_DEVICE_NAME = opcode(GROUP_DEVICE, 0x0A)
EVENT_PIN_REQUEST = opcode(GROUP_DEVICE, 0x12)
EVENT_READ_LOCAL_BDA = opcode(GROUP_DEVICE, 0x0D)
EVENT_CONNECTION_STATUS = opcode(GROUP_DEVICE, 0x11)

EVENT_MISC_VERSION = opcode(GROUP_MISC, 0x02)
EVENT_MISC_BRIDGE_IDENTITY = opcode(GROUP_MISC, 0x03)


SUPPORTED_GROUP_NAMES = {
    GROUP_HF: "HF",
    GROUP_AG: "AG",
    GROUP_AUDIO: "A2DP Source",
    GROUP_AVRC_CONTROLLER: "AVRCP Controller",
    GROUP_AVRC_TARGET: "AVRCP Target",
    GROUP_AUDIO_SINK: "A2DP Sink",
}

HF_AT_EVENT_NAMES = {
    0x00: "HF OK",
    0x01: "HF Error",
    0x02: "HF CME Error",
    0x03: "HF Ring",
    0x04: "HF Speaker Volume",
    0x05: "HF Microphone Volume",
    0x06: "HF Call Waiting",
    0x07: "HF Call Hold",
    0x08: "HF CIND",
    0x09: "HF CLIP",
    0x0A: "HF CIEV",
    0x0B: "HF BINP",
    0x0C: "HF BVRA",
    0x0D: "HF BSIR",
    0x0E: "HF CNUM",
    0x0F: "HF BTRH",
    0x10: "HF COPS",
    0x11: "HF CLCC",
    0x12: "HF BIND",
    0x13: "HF BCS",
    0x14: "HF Unknown AT",
}

HF_INDICATOR_NAMES = {
    1: "service",
    2: "call",
    3: "call setup",
    4: "call held",
    5: "signal",
    6: "roaming",
    7: "battery",
}

STATUS_NAMES = {
    0: "Success",
    1: "In Progress",
    2: "Already Connected",
    3: "Not Connected",
    4: "Bad Handle",
    5: "Wrong State",
    6: "Invalid Arguments",
    7: "Failed",
    8: "Unknown Group",
    9: "Unknown Command",
    10: "Client Not Registered",
    11: "Out Of Memory",
    12: "Disallowed",
}

TX_OPCODE_NAMES = {
    COMMAND_INQUIRY: "Inquiry",
    COMMAND_SET_VISIBILITY: "Set Visibility",
    COMMAND_SET_PAIRING_MODE: "Set Pairing Mode",
    COMMAND_UNBOND: "Unbond",
    COMMAND_UNBOND_DEVICE: "Unbond Device",
    COMMAND_USER_CONFIRMATION: "User Confirmation Reply",
    COMMAND_BOND: "Bond",
    COMMAND_PIN_REPLY: "PIN Reply",
    COMMAND_READ_LOCAL_BDA: "Read Local BDA",
    COMMAND_GET_VERSION: "Get Version",
    COMMAND_HF_CONNECT: "HF Connect",
    COMMAND_HF_DISCONNECT: "HF Disconnect",
    COMMAND_HF_OPEN_AUDIO: "HF Audio Open",
    COMMAND_HF_CLOSE_AUDIO: "HF Audio Close",
    COMMAND_AG_CONNECT: "AG Connect",
    COMMAND_AG_DISCONNECT: "AG Disconnect",
    COMMAND_AG_OPEN_AUDIO: "AG Audio Open",
    COMMAND_AG_CLOSE_AUDIO: "AG Audio Close",
    COMMAND_AVRC_CT_CONNECT: "AVRCP CT Connect",
    COMMAND_AVRC_CT_DISCONNECT: "AVRCP CT Disconnect",
    COMMAND_AVRC_CT_PLAY: "AVRCP Play",
    COMMAND_AVRC_CT_STOP: "AVRCP Stop",
    COMMAND_AVRC_CT_PAUSE: "AVRCP Pause",
    COMMAND_AVRC_CT_NEXT: "AVRCP Next",
    COMMAND_AVRC_CT_PREV: "AVRCP Previous",
    COMMAND_AVRC_TG_CONNECT: "AVRCP TG Connect",
    COMMAND_AVRC_TG_DISCONNECT: "AVRCP TG Disconnect",
    COMMAND_AUDIO_SRC_CONNECT: "A2DP Source Connect",
    COMMAND_AUDIO_SRC_DISCONNECT: "A2DP Source Disconnect",
    COMMAND_AUDIO_SINK_CONNECT: "A2DP Sink Connect",
    COMMAND_AUDIO_SINK_DISCONNECT: "A2DP Sink Disconnect",
}

RX_OPCODE_NAMES = {
    opcode(GROUP_DEVICE, 0x04): "NVRAM Data Request",
    EVENT_DEVICE_STARTED: "Device Started",
    EVENT_INQUIRY_RESULT: "Inquiry Result",
    EVENT_INQUIRY_COMPLETE: "Inquiry Complete",
    EVENT_PAIRING_COMPLETE: "Pairing Complete",
    opcode(GROUP_DEVICE, 0x09): "Encryption Changed",
    EVENT_USER_CONFIRMATION: "User Confirmation Request",
    EVENT_CONNECTED_DEVICE_NAME: "Connected Device Name",
    EVENT_PIN_REQUEST: "PIN Request",
    EVENT_READ_LOCAL_BDA: "Read Local BDA",
    EVENT_MISC_VERSION: "Version",
    EVENT_MISC_BRIDGE_IDENTITY: "Bridge Identity",
    EVENT_COMMAND_STATUS: "Command Status",
    EVENT_CONNECTION_STATUS: "Connection Status",
    opcode(GROUP_HF, 0x03): "HF Service Connected",
    opcode(GROUP_HF, 0x04): "HF Service Disconnected",
    opcode(GROUP_HF, 0x05): "HF Audio Connected",
    opcode(GROUP_HF, 0x06): "HF Audio Disconnected",
    opcode(GROUP_AG, 0x01): "AG Service Open",
    opcode(GROUP_AG, 0x02): "AG Service Close",
    opcode(GROUP_AG, 0x03): "AG Service Connected",
    opcode(GROUP_AG, 0x04): "AG Audio Open",
    opcode(GROUP_AG, 0x05): "AG Audio Close",
    opcode(GROUP_AG, 0x06): "AG AT Command",
    opcode(GROUP_AVRC_CONTROLLER, 0x01): "AVRCP CT Connected",
    opcode(GROUP_AVRC_CONTROLLER, 0x02): "AVRCP CT Disconnected",
    opcode(GROUP_AVRC_CONTROLLER, 0x03): "AVRCP Track Info",
    opcode(GROUP_AVRC_CONTROLLER, 0x04): "AVRCP Play Status",
    opcode(GROUP_AVRC_CONTROLLER, 0xFF): "AVRCP CT Command Status",
    opcode(GROUP_AVRC_TARGET, 0x01): "AVRCP TG Connected",
    opcode(GROUP_AVRC_TARGET, 0x02): "AVRCP TG Disconnected",
    opcode(GROUP_AVRC_TARGET, 0x03): "AVRCP Play Received",
    opcode(GROUP_AVRC_TARGET, 0x04): "AVRCP Stop Received",
    opcode(GROUP_AVRC_TARGET, 0x05): "AVRCP Pause Received",
    opcode(GROUP_AVRC_TARGET, 0x06): "AVRCP Next Received",
    opcode(GROUP_AVRC_TARGET, 0x07): "AVRCP Previous Received",
    opcode(GROUP_AVRC_TARGET, 0x0C): "AVRCP Volume Level",
    opcode(GROUP_AUDIO, 0x01): "A2DP Source Command Status",
    opcode(GROUP_AUDIO, 0x02): "A2DP Source Connected",
    opcode(GROUP_AUDIO, 0x04): "A2DP Source Connection Failed",
    opcode(GROUP_AUDIO, 0x05): "A2DP Source Disconnected",
    opcode(GROUP_AUDIO_SINK, 0x01): "A2DP Sink Command Status",
    opcode(GROUP_AUDIO_SINK, 0x02): "A2DP Sink Connected",
    opcode(GROUP_AUDIO_SINK, 0x04): "A2DP Sink Connection Failed",
    opcode(GROUP_AUDIO_SINK, 0x05): "A2DP Sink Disconnected",
    opcode(GROUP_AUDIO_SINK, 0x08): "A2DP Sink Codec Configured",
    opcode(GROUP_AUDIO_SINK, 0x09): "A2DP Sink Start Indication",
    opcode(GROUP_AUDIO_SINK, 0x0B): "A2DP Sink Suspended",
}


@dataclass
class Packet:
    opcode: int
    payload: bytes


def encode_wiced_command(opcode_value: int, payload: bytes = b"") -> bytes:
    length = len(payload)
    return bytes(
        [
            HCI_WICED_PKT,
            opcode_value & 0xFF,
            (opcode_value >> 8) & 0xFF,
            length & 0xFF,
            (length >> 8) & 0xFF,
        ]
    ) + payload


def try_extract_packet(buffer: bytearray) -> Optional[Packet]:
    if len(buffer) < 5:
        return None
    if buffer[0] != HCI_WICED_PKT:
        del buffer[0]
        return None
    opcode_value = buffer[1] | (buffer[2] << 8)
    length = buffer[3] | (buffer[4] << 8)
    total = 5 + length
    if len(buffer) < total:
        return None
    payload = bytes(buffer[5:total])
    del buffer[:total]
    return Packet(opcode=opcode_value, payload=payload)


def bd_addr_to_display(raw: Iterable[int]) -> str:
    values = list(raw)
    return ":".join(f"{value:02X}" for value in values)


def bd_addr_to_command(address: str) -> bytes:
    values = bytes(int(part, 16) for part in address.split(":"))
    if len(values) != 6:
        raise ValueError("Bluetooth address must contain 6 octets")
    return bytes(reversed(values))


def decode_eir_name(eir: bytes) -> str:
    offset = 0
    while offset < len(eir):
        length = eir[offset]
        if length == 0:
            break
        next_offset = offset + 1 + length
        if next_offset > len(eir):
            break
        tag = eir[offset + 1]
        data = eir[offset + 2:next_offset]
        if tag in (0x08, 0x09):
            return data.decode("utf-8", errors="ignore").strip("\x00")
        offset = next_offset
    return ""


def parse_version_payload(payload: bytes) -> tuple[str, str, list[int]]:
    if len(payload) < 9:
        return ("", "", [])
    version = f"{payload[0]}.{payload[1]}.{payload[2]} build {payload[3] | (payload[4] << 8)}"
    chip = str(payload[5] | (payload[6] << 8) | (payload[7] << 24))
    groups = list(payload[9:])
    return (version, chip, groups)


def encode_user_confirmation_reply(raw_bda: bytes, accepted: bool) -> bytes:
    return bytes(reversed(raw_bda)) + bytes([1 if accepted else 0])


def encode_pin_reply(raw_bda: bytes, pin: str) -> bytes:
    encoded = pin.encode("ascii", errors="ignore")[:16]
    return bytes(reversed(raw_bda)) + bytes([len(encoded)]) + encoded


def tx_opcode_name(opcode_value: int) -> str:
    return TX_OPCODE_NAMES.get(opcode_value, f"Command 0x{opcode_value:04X}")


def rx_opcode_name(opcode_value: int) -> str:
    return RX_OPCODE_NAMES.get(opcode_value, f"Event 0x{opcode_value:04X}")


def _ascii_text(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="ignore")
    text = text.replace("\r", " ").replace("\n", " ").replace("\x00", " ")
    return " ".join(text.split())


def _find_at_text(payload: bytes) -> str:
    text = _ascii_text(payload)
    at_index = text.find("AT")
    return text[at_index:] if at_index >= 0 else text


def _handle_text(payload: bytes) -> str:
    if len(payload) >= 2:
        handle = payload[0] | (payload[1] << 8)
        return str(handle)
    return "unknown"


def _status_name(code: int) -> str:
    return f"{STATUS_NAMES.get(code, f'Status {code}')} (0x{code:02X})"


def _decode_addr_handle(payload: bytes) -> tuple[str | None, int | None]:
    if len(payload) >= 8:
        address = bd_addr_to_display(reversed(payload[:6]))
        handle = payload[6] | (payload[7] << 8)
        return (address, handle)
    if len(payload) >= 2:
        return (None, payload[0] | (payload[1] << 8))
    return (None, None)


def _decode_addr_status_handle(payload: bytes) -> tuple[str | None, int | None, int | None]:
    if len(payload) >= 9:
        address = bd_addr_to_display(reversed(payload[:6]))
        status = payload[6]
        handle = payload[7] | (payload[8] << 8)
        return (address, status, handle)
    if len(payload) >= 2:
        return (None, None, payload[0] | (payload[1] << 8))
    return (None, None, None)


def _group_name_with_code(group: int) -> str:
    if group == GROUP_AUDIO:
        return "A2DP Audio / Source group (0x05)"
    return f"{SUPPORTED_GROUP_NAMES.get(group, f'Group {group}')} (0x{group:02X})"


def _payload_hex(payload: bytes) -> str:
    return " ".join(f"{value:02X}" for value in payload) if payload else "none"


def _opcode_hex(opcode_value: int) -> str:
    return f"0x{opcode_value:04X}"


def _hf_at_payload(payload: bytes) -> tuple[str, int | None, str]:
    handle = payload[0] | (payload[1] << 8) if len(payload) >= 2 else None
    number = payload[2] | (payload[3] << 8) if len(payload) >= 4 else None
    text = payload[4:].split(b"\x00", 1)[0].decode("utf-8", errors="ignore").strip() if len(payload) > 4 else ""
    return (f"handle {handle}" if handle is not None else "handle unknown", number, text)


def _decode_hf_at_event(opcode_value: int, payload: bytes) -> str | None:
    if (opcode_value >> 8) != GROUP_HF:
        return None
    event_code = opcode_value & 0xFF
    if event_code < 0x20 or event_code > 0x34:
        return None

    at_code = event_code - 0x20
    event_name = HF_AT_EVENT_NAMES.get(at_code, f"HF AT Event 0x{at_code:02X}")
    handle_text, number, text = _hf_at_payload(payload)
    suffix = f"{event_name} ({_opcode_hex(opcode_value)})"

    if at_code == 0x0A and text:
        parts = [part.strip() for part in text.split(",", 1)]
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            indicator_id = int(parts[0])
            indicator_value = int(parts[1])
            indicator_name = HF_INDICATOR_NAMES.get(indicator_id, f"indicator {indicator_id}")
            return (
                f"{suffix}: {handle_text}, {indicator_name}={indicator_value} "
                f"(raw {text}; hex {_payload_hex(payload)})"
            )
    if at_code in {0x04, 0x05} and text:
        volume_type = "speaker" if at_code == 0x04 else "microphone"
        return f"{suffix}: {handle_text}, {volume_type} volume={text} (hex {_payload_hex(payload)})"
    if at_code in {0x11, 0x12, 0x13}:
        details = text or (str(number) if number is not None else "no details")
        return f"{suffix}: {handle_text}, {details} (hex {_payload_hex(payload)})"
    if at_code == 0x03:
        return f"{suffix}: {handle_text} (hex {_payload_hex(payload)})"
    if text:
        return f"{suffix}: {handle_text}, {text} (hex {_payload_hex(payload)})"
    if number is not None and number != 0:
        return f"{suffix}: {handle_text}, value={number} (hex {_payload_hex(payload)})"
    return f"{suffix}: {handle_text} (hex {_payload_hex(payload)})"


def _codec_name(codec_id: int) -> str:
    return {
        0: "SBC",
        1: "AAC",
        2: "APT-X",
        3: "APT-X HD",
        4: "LDAC",
    }.get(codec_id, f"Codec {codec_id}")


def tx_profile_name(opcode_value: int) -> str:
    return TX_OPCODE_NAMES.get(opcode_value, tx_opcode_name(opcode_value))


def decode_tx_message(opcode_value: int, payload: bytes) -> str:
    name = tx_opcode_name(opcode_value)
    if opcode_value in {
        COMMAND_HF_CONNECT,
        COMMAND_AG_CONNECT,
        COMMAND_AVRC_CT_CONNECT,
        COMMAND_AVRC_TG_CONNECT,
        COMMAND_AUDIO_SRC_CONNECT,
        COMMAND_AUDIO_SINK_CONNECT,
        COMMAND_BOND,
        COMMAND_UNBOND,
        COMMAND_UNBOND_DEVICE,
    } and len(payload) >= 6:
        return f"{name} to {bd_addr_to_display(reversed(payload[:6]))}"
    if opcode_value == COMMAND_SET_PAIRING_MODE and payload:
        return f"Pairable mode {'enabled' if payload[0] else 'disabled'}"
    if opcode_value == COMMAND_SET_VISIBILITY and len(payload) >= 2:
        return (
            "Visibility set: "
            f"discoverable={'yes' if payload[0] else 'no'}, connectable={'yes' if payload[1] else 'no'}"
        )
    if opcode_value == COMMAND_INQUIRY and payload:
        return f"Inquiry {'started' if payload[0] else 'stopped'}"
    if opcode_value == COMMAND_USER_CONFIRMATION and len(payload) >= 7:
        return f"Numeric comparison {'accepted' if payload[6] else 'rejected'}"
    if opcode_value == COMMAND_PIN_REPLY and len(payload) >= 7:
        return f"PIN reply sent ({payload[6]} digits)"
    return name


def decode_rx_message(opcode_value: int, payload: bytes) -> str:
    name = rx_opcode_name(opcode_value)
    hf_at_message = _decode_hf_at_event(opcode_value, payload)
    if hf_at_message is not None:
        return hf_at_message
    if opcode_value == EVENT_DEVICE_STARTED:
        return "Board booted and HCI control is ready"
    if opcode_value == EVENT_MISC_VERSION:
        version, chip, groups = parse_version_payload(payload)
        group_names = ", ".join(_group_name_with_code(group) for group in groups)
        return f"Firmware version {version}, chip {chip}, supported groups: {group_names or 'none reported'}"
    if opcode_value == EVENT_MISC_BRIDGE_IDENTITY:
        identity = payload.decode("utf-8", errors="ignore").strip("\x00")
        return f"Board identity is {identity}"
    if opcode_value == EVENT_READ_LOCAL_BDA and len(payload) >= 6:
        return f"Local Bluetooth address: {bd_addr_to_display(payload[:6])}"
    if opcode_value == opcode(GROUP_DEVICE, 0x04):
        return f"Firmware requested NVRAM data ({len(payload)} bytes)"
    if opcode_value == opcode(GROUP_DEVICE, 0x09) and len(payload) >= 7:
        return f"Link encryption {'enabled' if payload[0] else 'disabled'} for {bd_addr_to_display(payload[1:7])}"
    if opcode_value == EVENT_COMMAND_STATUS and payload:
        return f"Last command result: {_status_name(payload[0])}"
    if opcode_value == EVENT_PAIRING_COMPLETE and payload:
        return f"Pairing completed with result: {_status_name(payload[0])}"
    if opcode_value == EVENT_USER_CONFIRMATION and len(payload) >= 10:
        numeric_value = payload[6] | (payload[7] << 8) | (payload[8] << 16) | (payload[9] << 24)
        return f"Numeric comparison requested: {numeric_value}"
    if opcode_value == EVENT_PIN_REQUEST and len(payload) >= 6:
        return f"PIN code requested for {bd_addr_to_display(payload[:6])}"
    if opcode_value == EVENT_INQUIRY_COMPLETE:
        return "Device search completed"
    if opcode_value == EVENT_INQUIRY_RESULT and len(payload) >= 10:
        addr = bd_addr_to_display(reversed(payload[:6]))
        rssi = payload[9] if payload[9] < 128 else payload[9] - 256
        name_text = decode_eir_name(payload[10:]) or "Unnamed device"
        return f"Found {name_text} at {addr} with RSSI {rssi}"
    if opcode_value == EVENT_CONNECTION_STATUS:
        text = _ascii_text(payload)
        return f"Connection status update: {text}" if text else "Connection status update received"
    if opcode_value == EVENT_AG_AT_CMD:
        at_text = _find_at_text(payload)
        return f"Phone AT command: {at_text or 'received'}"
    if opcode_value in {
        opcode(GROUP_HF, 0x03),
        opcode(GROUP_HF, 0x04),
        opcode(GROUP_HF, 0x05),
        opcode(GROUP_HF, 0x06),
        opcode(GROUP_AG, 0x01),
        opcode(GROUP_AG, 0x02),
        opcode(GROUP_AG, 0x03),
        opcode(GROUP_AG, 0x04),
        opcode(GROUP_AG, 0x05),
        opcode(GROUP_AVRC_CONTROLLER, 0x02),
        opcode(GROUP_AVRC_TARGET, 0x02),
        opcode(GROUP_AUDIO, 0x05),
        opcode(GROUP_AUDIO_SINK, 0x04),
        opcode(GROUP_AUDIO_SINK, 0x05),
    }:
        return f"{name} ({_opcode_hex(opcode_value)}) on handle {_handle_text(payload)}"
    if opcode_value in {
        opcode(GROUP_AVRC_TARGET, 0x01),
        opcode(GROUP_AUDIO, 0x02),
        opcode(GROUP_AUDIO_SINK, 0x02),
    }:
        address, handle = _decode_addr_handle(payload)
        details = []
        if address:
            details.append(f"peer {address}")
        if handle is not None:
            details.append(f"handle {handle}")
        if opcode_value == opcode(GROUP_AUDIO, 0x02) and len(payload) >= 9:
            details.append(f"absolute-volume-capable={'yes' if payload[8] else 'no'}")
        return f"{name} ({_opcode_hex(opcode_value)}): {', '.join(details) or f'hex {_payload_hex(payload)}'}"
    if opcode_value == opcode(GROUP_AVRC_CONTROLLER, 0x01):
        address, status, handle = _decode_addr_status_handle(payload)
        details = []
        if address:
            details.append(f"peer {address}")
        if status is not None:
            details.append(f"status {_status_name(status)}")
        if handle is not None:
            details.append(f"handle {handle}")
        return f"{name} ({_opcode_hex(opcode_value)}): {', '.join(details) or f'hex {_payload_hex(payload)}'}"
    if opcode_value in {
        opcode(GROUP_AVRC_TARGET, 0x03),
        opcode(GROUP_AVRC_TARGET, 0x04),
        opcode(GROUP_AVRC_TARGET, 0x05),
        opcode(GROUP_AVRC_TARGET, 0x06),
        opcode(GROUP_AVRC_TARGET, 0x07),
    }:
        return name
    if opcode_value in {
        opcode(GROUP_AUDIO, 0x01),
        opcode(GROUP_AUDIO_SINK, 0x01),
        opcode(GROUP_AVRC_CONTROLLER, 0xFF),
        opcode(GROUP_AVRC_TARGET, 0xFF),
    } and payload:
        return f"{name} ({_opcode_hex(opcode_value)}): {_status_name(payload[0])}"
    if opcode_value == opcode(GROUP_AUDIO_SINK, 0x08) and payload:
        return f"A2DP sink codec configured ({_opcode_hex(opcode_value)}): {_codec_name(payload[0])}"
    if opcode_value == opcode(GROUP_AUDIO_SINK, 0x09):
        return f"A2DP sink start requested ({_opcode_hex(opcode_value)})"
    if opcode_value == opcode(GROUP_AUDIO_SINK, 0x0B):
        return f"A2DP sink stream suspended ({_opcode_hex(opcode_value)})"
    if opcode_value == opcode(GROUP_AVRC_TARGET, 0x0C) and payload:
        percent = round((payload[0] / 127) * 100)
        return f"AVRCP volume updated to about {percent}% ({_opcode_hex(opcode_value)})"
    text = _ascii_text(payload)
    if text:
        return f"{name} ({_opcode_hex(opcode_value)}): {text} [hex: {_payload_hex(payload)}]"
    return f"{name} ({_opcode_hex(opcode_value)}) received ({len(payload)} bytes, hex: {_payload_hex(payload)})"
