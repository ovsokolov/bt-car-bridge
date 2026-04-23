# Codex Handoff

## What Happened
- The app `makefile` became corrupted and was replaced with a fresh text version.
- `project_status.md` and `codex-handoff.md` were also found to be NUL-filled and unreadable.
- This handoff file is a clean restart point built from the current repo state and `AGENT.md`.

## Current Understanding
- This repo is the HF side of the bridge system for `CYBT-343026-EVAL`.
- The firmware should act as the HFP Hands-free side, not the default AG-oriented sample behavior.
- The active host-side control UI lives in `C:\BT_Projects\control_ui`.
- The matching AG firmware workspace lives in `C:\BT_Projects\headset_hfp_ag`.
- A shared Git repository is now initialized at `C:\BT_Projects`.

## Current Build Defaults
- `APPNAME=Headset_Standalone`
- `TARGET=CYBT-343026-EVAL`
- `HFP_HF_INCLUDED=1`
- `HFP_AG_INCLUDED=0`
- `LE_INCLUDED=1`
- `ANCS_INCLUDED=1`
- `AMS_INCLUDED=1`
- `PANU_SUPPORT=0`
- `PANNAP_SUPPORT=0`

## Files To Read First Next Time
- `AGENT.md`
- `project_status.md`
- `mtb-example-btsdk-audio-headset-standalone/makefile`
- `mtb-example-btsdk-audio-headset-standalone/README.md`
- `mtb-example-btsdk-audio-headset-standalone/build/get_app_info.txt`

## Practical Next Actions
- Validate the rebuilt `makefile` from the real ModusToolbox shell.
- If the user wants bridge behavior changes, compare this repo with:
  - `C:\BT_Projects\headset_hfp_ag`
  - `C:\BT_Projects\control_ui`
- Keep HF and AG repos aligned when a change is supposed to affect both bridge sides.
- After each meaningful completed change, commit from `C:\BT_Projects` instead of leaving work uncommitted.
- In the next session, start by checking `C:\BT_Projects` Git status so local commits continue consistently after restart.

## Current Bridge Experiment
- The latest bridge pass is intentionally incremental, not a full raw packet tunnel yet.
- `control_ui` now forwards:
  - car-side AG AT commands toward the phone-side HF link
  - phone-side HF `RING` / `+CIEV` / `+CLIP` / `+CLCC` / `+CNUM` / `OK` / `ERROR` style events toward the car-side AG link
  - car-side AVRCP target passthrough events to phone-side AVRCP controller commands
  - HF/AG audio open-close events across the two boards
- The UI bridge log now shows conversion-oriented lines such as phone-side indicator input mapped to car-side AG indicator output.
- HF firmware now has a narrow custom host command in `hci_control_hfp_hf.c` for raw AT passthrough so the UI can forward car-issued HFP AT strings to the phone-facing HF connection.
- A2DP is still only coordinated at the profile/control level from the UI. It is not raw media-packet forwarding.

## Notes
- `AGENT.md` remained readable and should be treated as the most trustworthy local project note.
- The rebuilt docs are intentionally minimal and factual so they can serve as a clean baseline after corruption.

## Process Guardrail
- From now on, every behavior/code change must be committed immediately after a quick validation step (good or bad result). Do not batch multiple experiments into one uncommitted working tree state.

## Legacy UI References
- Old host control UI reference path (read-only baseline for call-flow behavior):
  - `C:\BT_Projects\headset_hfp_hf\mtb_shared\wiced_btsdk\tools\btsdk-host-apps-bt-ble\release-v4.9.3\client_control\source`
- Additional profile/reference project to compare multi-profile behavior:
  - `C:\BT_Projects\mtb-example-btsdk-audio-watch-ama-master`
