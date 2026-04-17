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
- The new bridge pass has only host-level and selective firmware forwarding so far:
  - HFP bridging is semantic and AT/result based
  - AVRCP bridging is passthrough-command based where events are exposed
  - A2DP is still connect/control orchestration only, not transparent media forwarding

## Current Bridge Path
- `control_ui` now contains the first explicit two-board bridge logic.
- Phone-side HF events are converted into AG-side indicators/result strings for the car board.
- Car-side AG AT requests are forwarded to the phone-side HF link.
- HF firmware now accepts a custom raw AT passthrough command from the host in `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_hf.c`.
- This needs hardware validation with both boards connected because the bridge logic is now stateful and conversion-heavy.

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
