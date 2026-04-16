# Codex Handoff

## What Changed
- The control UI was extended beyond the initial rebuild to improve bring-up workflow and readability.
- `hci.py` now produces more operator-friendly log text, especially for AT commands and common profile events.
- `session.py` now exposes richer COM-port metadata and adds a one-step AG reconnect sequence for the remembered remote device.
- `ui.py` now shows COM-port details, adds default-on HF visibility and pairable checkboxes on the phone side, and adds a `Connect Previous` action on the car side.

## Current Operator Flow
- Choose a COM port and review the USB/HCI details shown under the port selector.
- Open the phone-side serial session.
  - The phone-side UI keeps `Visible to phone` and `Pairable` enabled by default.
  - Opening the phone-side session applies those flags automatically.
- Open the car-side serial session.
  - Use `Connect Previous` to remove the old bond, create a fresh bond, and reconnect AG, A2DP source, and AVRCP target for the saved car-side peer.
- Use the unified trace and per-side trace logs for readable event monitoring rather than raw hex-oriented output.

## Validation Completed
- `python -m py_compile` passed.
- Tkinter smoke test passed:
  - `BridgeApp` constructs successfully.
- Readable AT-command decoding sanity check passed.

## Practical Next Actions
- Test both boards on real COM ports and verify the USB/HCI details shown in the UI match the expected devices.
- Confirm the phone-side board remains visible and pairable by default after opening.
- Validate the AG `Connect Previous` timing against the real car-side reconnect flow.
- If reconnect timing is off, tune the waits in `SerialBridgeSession._run_ag_connect_previous()`.
- If deeper protocol visibility is needed, continue improving `decode_rx_message()` in `hci.py` rather than adding hex dumps back into the main trace.
- After each meaningful completed change, commit from `C:\BT_Projects`.

## Files To Read First Next Time
- `AGENT.md`
- `project_status.md`
- `README.md`
- `docs/bridge_spec.md`
- `src/control_ui_app/hci.py`
- `src/control_ui_app/session.py`
- `src/control_ui_app/ui.py`

## Notes
- The current AG one-step reconnect is intentionally pragmatic: disconnect, unbond, bond, then reconnect service profiles.
- The UI is still a control and trace tool, not the final end-to-end bridge translator.
