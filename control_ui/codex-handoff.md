# Codex Handoff

## What Changed
- The COM-port selector now shows richer labels directly in the dropdown instead of only raw `COMx` names.
- `session.py` now builds a dropdown label that includes the port, product or description, manufacturer hint, and `WICED HCI` role hint.
- `ui.py` now keeps a mapping between the human-readable dropdown labels and the underlying COM-port device name so the UI stays readable without breaking open or close behavior.
- The phone-side panel is now reduced to a minimal HF workflow: open the board, then use one `Enable Phone Pairing` action when you want the phone to initiate pairing.
- The car-side panel is now reduced to inquiry plus one `Pair Selected` action that disconnects old links, removes the previous bond for that address, and starts a fresh AG bond while still honoring PIN and numeric-comparison prompts.
- In project notes, `client control`, `control client`, and `control UI` now refer to `C:\BT_Projects\control_ui` unless the user explicitly says `OLD` or `REFERENCE`.
- `hci.py` now decodes more raw profile events into readable text and correctly parses the payload layout for AVRCP and A2DP connection events so logs no longer invent garbage handles from the peer address bytes.

## Current Operator Flow
- Use the per-side port dropdown and look for labels such as:
  - `COM7 | KitProg3 USB-UART | Infineon | WICED HCI`
- Choose a port from the richer dropdown label list.
- The UI resolves that display label back to the actual `COMx` device when opening the board session.
- The detailed panel below the selector still shows the full USB metadata for the currently selected port.
- Use the per-side `Refresh` button or the top-level `Refresh Ports` control to rescan devices.

## Validation Completed
- `python -m py_compile` passed.
- Tkinter smoke test passed.
- Explicit close-path smoke test passed for both side sessions.
- Dropdown-label UI smoke test passed after switching the selector to rich labels.
- Readable AT-command decoding sanity check passed.

## Practical Next Actions
- Test with the real boards attached and confirm the dropdown labels still make it obvious which USB serial device is the HCI control port.
- Validate that the phone side opens hidden and not pairable, then confirm `Enable Phone Pairing` is enough for the phone to discover and bond.
- Validate that AG `Pair Selected` removes any old bond and then succeeds through either numeric comparison or PIN entry when hardware requests it.
- After each meaningful completed change, commit from `C:\BT_Projects`.

## Files To Read First Next Time
- `AGENT.md`
- `project_status.md`
- `README.md`
- `docs/bridge_spec.md`
- `src/control_ui_app/session.py`
- `src/control_ui_app/ui.py`

## Notes
- The UI is still a control and trace tool, not the final end-to-end bridge translator.
- The dropdown-label mapping is intentionally separate from the saved device name so persisted state keeps using the stable `COMx` value.
