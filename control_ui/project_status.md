# Project Status

## Workspace
- Repo: `C:\BT_Projects\control_ui`
- Git root: `C:\BT_Projects`
- Entry point: `main.py`
- App package: `src/control_ui_app`
- UI stack: Python + Tkinter
- Serial dependency: `pyserial>=3.5`

## Current Baseline
- The COM-port dropdown now shows richer labels directly in the selector, including the port name, device description or product, manufacturer hint, and `WICED HCI` role hint.
- The operator UI still shows richer COM-port details below the selector, including USB identity fields and the note that the control link is WICED HCI over USB serial.
- There is a top-level `Refresh Ports` control and an additional per-side `Refresh` button next to each COM-port selector.
- Closing a session actively cancels pending serial reads and writes, joins worker threads, clears buffers, and refreshes the visible COM-port list to help release the port cleanly.
- The phone-side panel has default-on HF visibility and pairable checkboxes and applies those flags after opening the serial link.
- The car-side panel has a one-step `Connect Previous` action that disconnects old links, removes the old bond, re-bonds, and reconnects AG, A2DP source, and AVRCP target for the remembered remote.
- Logs are more readable and less hex-heavy, including AT-command text decoding and clearer profile and event wording.

## Validation
- `python -m py_compile` passed for the control_ui package.
- Tkinter smoke test passed by constructing `BridgeApp` without entering the main loop.
- Close-path smoke test passed by explicitly closing both side sessions in-process.
- Dropdown-label UI smoke test passed after switching the selector to rich port labels.
- Readable AT-command decode sanity check passed.

## Open Issues
- Real hardware behavior still needs validation with both boards attached.
- The AG one-step reconnect uses timed command sequencing and may need tuning once tested against the actual car-side firmware timing.
- Automatic bridge translation for HFP, AVRCP, and A2DP events is still future work.

## Suggested Next Step
- Run `python main.py` from `C:\BT_Projects\control_ui`.
- Confirm the dropdown itself now shows the expected USB/HCI hints for each COM port.
- Open and close both board sessions a few times and confirm the COM ports are immediately reusable.
- Use car-side `Connect Previous` against the remembered remote and confirm the rebond and reconnect flow on hardware.
- After each meaningful change, commit from `C:\BT_Projects` so control_ui and the two firmware repos stay aligned.

## Important Files
- Entry point: `main.py`
- HCI parser and readable log decode: `src/control_ui_app/hci.py`
- Session engine and COM-port labeling or shutdown handling: `src/control_ui_app/session.py`
- Tkinter operator UI: `src/control_ui_app/ui.py`
- Models: `src/control_ui_app/models.py`
- Saved preferences: `bridge_state.json`
