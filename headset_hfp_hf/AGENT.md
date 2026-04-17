# HF Project Agent Notes

## Purpose
This project is the `PhoneConnect` firmware for the `CYBT-343026-EVAL` dev kit. It is based on the standalone headset example, but this workspace is configured to act as the HFP HF side of the bridge system rather than the original AG-oriented setup.
The active Python host/control interface for this bridge is in `C:\BT_Projects\control_ui` (outside this workspace).

## Primary Goals
- Present to the phone as `NavTool-PhoneConnect`.
- Participate in the larger phone-to-car bridge architecture with the AG project and the Python control UI.
- Keep Bluetooth signaling and host-control behavior visible to the host app over USB serial.
- Avoid pushing audio through UART; direct devkit-to-devkit hardware pins are the intended audio path.

## Bridge Repo Map
- Python control UI (active): `C:\BT_Projects\control_ui`
- AG firmware workspace: `C:\BT_Projects\headset_hfp_ag`
- HF firmware workspace (this repo): `C:\BT_Projects\headset_hfp_hf`

## Naming Note
- Unless the user explicitly says `OLD` or `REFERENCE`, any mention of `client control`, `control client`, or `control UI` refers to the active Python UI at `C:\BT_Projects\control_ui`.

## Git Workflow
- Git repository root: `C:\BT_Projects`
- Treat `C:\BT_Projects` as the source-control root for `control_ui`, `headset_hfp_ag`, `headset_hfp_hf`, and `mtb-example-btsdk-audio-watch`.
- After each meaningful completed change set, create a Git commit instead of leaving work only in the working tree.
- After a restart or new Codex session, check `C:\BT_Projects` Git status early and continue making local commits as work progresses.
- Before committing, review the diff to avoid accidentally committing unrelated generated files or temporary artifacts.
- If Git is not on `PATH`, use `C:\Program Files\Git\cmd\git.exe`.

## Important Locations
- App root: `mtb-example-btsdk-audio-headset-standalone`
- HF control path: `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_hf.c`
- AG wrapper copy still exists here for shared-role builds: `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
- App config / advertised name: `mtb-example-btsdk-audio-headset-standalone/wiced_app_cfg.c`
- Build role defaults: `mtb-example-btsdk-audio-headset-standalone/makefile`
- Shared host API copy: `mtb_shared/wiced_btsdk/tools/btsdk-host-apps-bt-ble/release-v4.9.3/include/hci_control_api.h`

## Key Decisions
- Default build role in this workspace is HF:
  - `HFP_HF_INCLUDED=1`
  - `HFP_AG_INCLUDED=0`
- PhoneConnect should behave as the phone-facing media sink and AVRCP controller:
  - `A2DP sink`
  - `AVRCP CT`
  - not `AVRCP TG` unless requirements explicitly change
- Device name should remain `NavTool-PhoneConnect` unless requirements explicitly change.
- Firmware now emits a custom bridge identity event so host tools can identify the board over serial.
- Direct hardware audio between devkits is the design direction; UART is for control/logging only.
- `ClientControl` (Qt sample under `mtb_shared/.../client_control`) is legacy reference material only, not the active bridge UI.

## Notes For Future Codex Sessions
- Read `project_status.md` first for the current state and next actions.
- Read `codex-handoff.md` for the recent change history and bridge context.
- For host-side behavior and reconnect/shutdown loops, treat `C:\BT_Projects\control_ui` as source of truth.
- When a firmware change is logically shared by both bridge sides, update both `C:\BT_Projects\headset_hfp_hf` and `C:\BT_Projects\headset_hfp_ag` in the same pass unless there is a documented reason not to.
- If a change meaningfully alters pairing, visibility, reconnect, profile roles, logging, or operator workflow, update `AGENT.md`, `project_status.md`, and `codex-handoff.md` before finishing the task.
- After updating code or docs, make the matching Git commit from `C:\BT_Projects` before finishing the task when possible.
- When touching bridge behavior, also check whether `C:\BT_Projects\control_ui` markdown files need the same update so the three repos stay in sync.
- Be careful not to reintroduce fake phone-state simulation on the AG wrapper path unless explicitly requested.
- If changing role/profile behavior, keep the bridge architecture aligned with:
  - Phone <-> PhoneConnect
  - Python control UI in the middle
  - CarConnect <-> Car
