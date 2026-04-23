# NavTool Control UI

`control_ui` is a bridge-oriented host application workspace for the two-devkit
NavTool Bluetooth proxy project.

Current contents:

- `docs/bridge_spec.md`: editable project specification
- `docs/bridge_spec.html`: printable HTML version of the specification
- `docs/bridge_spec.pdf`: rendered PDF output
- `main.py`: Python UI entry point
- `src/control_ui_app/`: bridge-oriented Python modules
- `requirements.txt`: host-side Python dependencies

The first app revision focuses on:

- opening two USB serial sessions at the same time
- identifying the connected devkits as `NavTool-PhoneConnect` and `NavTool-CarConnect`
- searching for remote devices from each devkit
- toggling pairability and visibility
- selecting discovered devices
- issuing pairing and profile-management commands
- collecting logs with clear source attribution
- remembering the last phone-side and car-side peer devices for reconnect

The live bridge logic for HFP, A2DP, and AVRCP translation is represented as
structure and placeholders in this first scaffold, but is not yet a complete
end-to-end proxy.

The UI now also remembers the previously selected phone and car peers in
`bridge_state.json` and can reconnect the side-appropriate profile set after the
correct board identity is detected on a serial port.

It now also prompts for Bluetooth numeric-comparison confirmation and classic
PIN entry when those pairing flows are requested by the firmware.

## Running

Install Python 3.11+ and the dependencies from `requirements.txt`, then run:

```powershell
python main.py
```

If `pyserial` is not installed, the UI will start in a limited mode and explain
what is missing.
