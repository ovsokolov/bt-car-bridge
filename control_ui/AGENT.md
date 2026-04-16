# Control UI Agent Notes

## Purpose
This project is the Python host UI and bridge-control workspace. It is intended to connect to both devkits over USB serial, identify them as `NavTool-PhoneConnect` and `NavTool-CarConnect`, coordinate pairing/connection workflows, log activity, and eventually drive the bridge behavior between the phone-facing and car-facing firmware.

## Primary Goals
- Open and manage two serial connections at the same time.
- Discover and label which board is connected to which COM port.
- Support inquiry, pairing, connection, and profile control flows needed for the bridge.
- Provide clear logs that show which side produced each event or data item.
- Coordinate HFP, A2DP, and AVRCP control flows while audio stays off-UART.

## Important Locations
- Entry point: `main.py`
- App package: `src/control_ui_app`
- HCI framing/parser: `src/control_ui_app/hci.py`
- Serial/session management: `src/control_ui_app/session.py`
- Tkinter UI: `src/control_ui_app/ui.py`
- Bridge documentation: `docs/bridge_spec.md`, `docs/bridge_spec.pdf`

## Key Decisions
- UI is currently a Python/Tkinter app.
- Serial transport is WICED HCI-style framed traffic.
- The app is a control/logging/orchestration layer, not an audio transport.
- Audio is planned to move directly between devkits over hardware pins.

## Notes For Future Codex Sessions
- Read `project_status.md` first for the current state.
- Read `codex-handoff.md` for what has already been scaffolded and what is still missing.
- Keep the three-project system aligned:
  - `control_ui`
  - `headset_hfp_ag`
  - `headset_hfp_hf`
- If changing commands/events, coordinate with both firmware workspaces and their shared host API copies.
- If a change meaningfully affects operator workflow, pairing, visibility, reconnect, or profile orchestration, update `AGENT.md`, `project_status.md`, and `codex-handoff.md` before finishing.
