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
- The phone-side panel is now intentionally minimal: the board opens hidden and not pairable by default, there is no HF inquiry list, and a single `Enable Phone Pairing` action makes the board visible and pairable when the operator is ready.
- The car-side panel is now intentionally minimal: inquiry remains visible, most profile buttons are removed, and a single `Pair Selected` action disconnects old links, removes the previous bond for the selected address, and starts a fresh AG bonding flow.
- Numeric comparison and PIN pairing prompts are still handled through Tk dialogs when the firmware requests them.
- In project notes, `client control`, `control client`, and `control UI` now mean `C:\BT_Projects\control_ui` unless the user explicitly says `OLD` or `REFERENCE`.
- The log decoder now parses more profile-specific events into readable text, including HF indicator events and the address or handle layout used by AVRCP and A2DP connect events.
- Logs are more readable and less hex-heavy, including AT-command text decoding and clearer profile and event wording.

## Validation
- `python -m py_compile` passed for the control_ui package.
- Tkinter smoke test passed by constructing `BridgeApp` without entering the main loop.
- Close-path smoke test passed by explicitly closing both side sessions in-process.
- Dropdown-label UI smoke test passed after switching the selector to rich port labels.
- Readable AT-command decode sanity check passed.

## Open Issues
- Real hardware behavior still needs validation with both boards attached.
- The AG one-click pair flow uses timed command sequencing and may need tuning once tested against the actual car-side firmware timing.
- Automatic bridge translation for HFP, AVRCP, and A2DP events is still future work.

## Suggested Next Step
- Run `python main.py` from `C:\BT_Projects\control_ui`.
- Confirm the dropdown still shows the expected USB/HCI hints for each COM port.
- Open and close both board sessions a few times and confirm the COM ports are immediately reusable.
- Confirm the phone side opens hidden and not pairable, then verify `Enable Phone Pairing` makes the board discoverable and pairable to the phone.
- Use car-side `Pair Selected` against a discovered car device and confirm old bonds are removed before the new pairing flow begins.
- After each meaningful change, commit from `C:\BT_Projects` so control_ui and the two firmware repos stay aligned.

## Important Files
- Entry point: `main.py`
- HCI parser and readable log decode: `src/control_ui_app/hci.py`
- Session engine and COM-port labeling or shutdown handling: `src/control_ui_app/session.py`
- Tkinter operator UI: `src/control_ui_app/ui.py`
- Models: `src/control_ui_app/models.py`
- Saved preferences: `bridge_state.json`
