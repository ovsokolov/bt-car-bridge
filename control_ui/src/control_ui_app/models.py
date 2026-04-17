from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RemoteDevice:
    address: str
    name: str = ""
    cod: str = ""
    rssi: Optional[int] = None
    source: str = ""
    paired: bool = False
    transport: str = "bredr"

    def display_name(self) -> str:
        label = self.name.strip() or "<unknown>"
        return f"{label} [{self.address}] RSSI={self.rssi if self.rssi is not None else '?'}"


@dataclass
class SessionInfo:
    label: str
    port: str = ""
    baud_rate: int = 3000000
    is_open: bool = False
    bridge_identity: str = ""
    local_bda: str = ""
    sdk_version: str = ""
    chip: str = ""
    supported_groups: List[int] = field(default_factory=list)
    discovered_devices: Dict[str, RemoteDevice] = field(default_factory=dict)
    preferred_remote_address: str = ""
    preferred_remote_name: str = ""
    pending_connect_after_pair: bool = False
    pending_bond_after_unbond_address: str = ""
    pending_bond_after_unbond_payload: bytes = b""
    ag_connected: bool = False
    avrc_connected: bool = False
    a2dp_connected: bool = False
    service_handle: int = 0
    avrc_handle: int = 0
    media_retry_count: int = 0
    ag_last_activity_at: float = 0.0
    a2dp_retry_job_active: bool = False
    a2dp_retry_after_id: str = ""
    last_status: str = ""


@dataclass
class BridgeState:
    phone_session: SessionInfo = field(default_factory=lambda: SessionInfo(label="PhoneConnect"))
    car_session: SessionInfo = field(default_factory=lambda: SessionInfo(label="CarConnect"))
    bridge_log: List[str] = field(default_factory=list)

    def session_by_key(self, key: str) -> SessionInfo:
        return self.phone_session if key == "phone" else self.car_session
