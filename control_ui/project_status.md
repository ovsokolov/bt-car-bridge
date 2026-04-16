# Project Status

## Workspace
- Repo: `C:\BT_Projects\control_ui`
- Git root: `C:\BT_Projects`
- Entry point: `main.py`
- App package: `src/control_ui_app`
- UI stack: Python + Tkinter
- Serial dependency: `pyserial>=3.5`

## Current Baseline
- The operator UI now shows richer COM-port details including USB identity fields and the note that the control link is WICED HCI over USB serial.
- The phone-side panel now has default-on HF visibility and pairable checkboxes and applies those flags after opening the serial link.
- The car-side panel now has a one-step `Connect Previous` action that disconnects old links, removes the old bond, re-bonds, and reconnects AG, A2DP source, and AVRCP target for the remembered remote.
- Logs are more readable and less hex-heavy, including AT-command text decoding and clearer profile/event wording.
- The app still supports:
  - two independent serial sessions
  - board-identity display for PhoneConnect and CarConnect
  - per-side discovery lists
  - bond and unbond actions
  - manual HF, AG, A2DP, and AVRCP command controls
  - per-side trace logs plus a unified bridge trace
  - numeric-comparison and PIN prompts
  - saved preferred remote addresses in `bridge_state.json`

## Validation
- `python -m py_compile` passed for the control_ui package.
- Tkinter smoke test passed by constructing `BridgeApp` without entering the main loop.
- Readable AT-command decode sanity check passed.

## Open Issues
- Real hardware behavior still needs validation with both boards attached.
- The AG one-step reconnect uses timed command sequencing and may need tuning once tested against the actual car-side firmware timing.
- Automatic bridge translation for HFP, AVRCP, and A2DP events is still future work.

## Suggested Next Step
- Run `python main.py` from `C:\BT_Projects\control_ui`.
- Verify the correct COM port details are shown for each board.
- Open the phone-side board and confirm the default HF visibility and pairable flags are applied.
- Use car-side `Connect Previous` against the remembered remote and confirm the rebond and reconnect flow on hardware.
- After each meaningful change, commit from `C:\BT_Projects` so control_ui and the two firmware repos stay aligned.

## Important Files
- Entry point: `main.py`
- HCI parser and readable log decode: `src/control_ui_app/hci.py`
- Session engine and AG reconnect sequence: `src/control_ui_app/session.py`
- Tkinter operator UI: `src/control_ui_app/ui.py`
- Models: `src/control_ui_app/models.py`
- Saved preferences: `bridge_state.json`
