# Project Status

## Workspace
- Repo: `C:\BT_Projects\headset_hfp_hf`
- Git root: `C:\BT_Projects`
- App root: `mtb-example-btsdk-audio-headset-standalone`
- Board target: `CYBT-343026-EVAL`
- App name: `Headset_Standalone`
- Role default: HFP HF

## Current Baseline
- `makefile` was rebuilt after corruption and is now readable text again.
- The workspace is configured for HF by default:
  - `HFP_HF_INCLUDED=1`
  - `HFP_AG_INCLUDED=0`
- PhoneConnect is now configured to stop building AVRCP Target in this HF workspace, keeping the phone-facing side aligned with `AVRCP CT + A2DP sink`.
- The HF workspace now also carries explicit runtime `a2dp_profile_role` state so EIR and supported-group reporting can describe PhoneConnect as sink-oriented even though the inherited standalone module still uses a source-named compile flag.
- HF media reconnect is now staged from real profile events instead of a blind timer chain:
  - pairing success can still start a full reconnect
  - HFP service reconnect advances the firmware to AVRCP CT reconnect
  - AVRCP CT reconnect advances the firmware to A2DP sink reconnect
- The legacy A2DP module now uses role-aware peer-service lookup instead of hardcoded source wording, and the HF sink path will retry the A2DP reconnect stage a few times if the first post-reboot SDP attempt fails.
- LE, AMS, and ANCS are enabled by default.
- PANU and PANNAP are disabled by default.
- `libs/mtb.mk` and the `core-make` include are restored in the app `makefile`.

## Known Good References
- Project intent and bridge context: `AGENT.md`
- App documentation: `mtb-example-btsdk-audio-headset-standalone/README.md`
- Generated build metadata snapshot: `mtb-example-btsdk-audio-headset-standalone/build/get_app_info.txt`

## External Related Repos
- Python control UI: `C:\BT_Projects\control_ui`
- AG firmware workspace: `C:\BT_Projects\headset_hfp_ag`
- HF firmware workspace: `C:\BT_Projects\headset_hfp_hf`
- Shared Git repo root for all of the above: `C:\BT_Projects`

## Open Issues
- `project_status.md` and `codex-handoff.md` were corrupted and rebuilt from scratch.
- A full `make` validation was not completed in this session from plain PowerShell because:
  - `make` is not on `PATH` in the current shell
  - the bundled ModusToolbox Cygwin `make.exe` crashed in this session with a Windows permission or mapping error
- Real hardware retest is still needed to confirm the new event-driven AVRCP and A2DP reconnect path after a board reboot, especially whether the bounded A2DP retry closes the gap seen after HFP reconnect.

## Suggested Next Step
- Open the project from the proper ModusToolbox shell and run a clean non-destructive validation such as `make get_app_info` or `make build`.
- If build errors appear, use `AGENT.md` plus `README.md` as the source of truth for restoring intended HF behavior.
- After each meaningful change, commit from `C:\BT_Projects` so the four sibling project folders stay tracked together.
- On the next restart, resume from `C:\BT_Projects` Git status first and keep committing locally after each completed change set.

## Important Files
- App makefile: `mtb-example-btsdk-audio-headset-standalone/makefile`
- HF control path: `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_hf.c`
- AG wrapper copy: `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
- App config and advertised-name area: `mtb-example-btsdk-audio-headset-standalone/wiced_app_cfg.c`
