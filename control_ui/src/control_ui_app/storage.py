from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import BridgeState, SessionInfo


STATE_FILE = Path(__file__).resolve().parents[2] / "bridge_state.json"


def apply_saved_state(state: BridgeState) -> None:
    data = _load_json()
    for key in ("phone", "car"):
        _apply_to_session(state.session_by_key(key), data.get(key, {}))


def save_state(state: BridgeState) -> None:
    payload = {
        "phone": _serialize_session(state.phone_session),
        "car": _serialize_session(state.car_session),
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_json() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _apply_to_session(session: SessionInfo, data: Any) -> None:
    if not isinstance(data, dict):
        return
    session.port = str(data.get("port", "") or "")
    session.preferred_remote_address = str(data.get("preferred_remote_address", "") or "")
    session.preferred_remote_name = str(data.get("preferred_remote_name", "") or "")


def _serialize_session(session: SessionInfo) -> dict[str, str]:
    return {
        "port": session.port,
        "preferred_remote_address": session.preferred_remote_address,
        "preferred_remote_name": session.preferred_remote_name,
    }
