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

## Notes
- `AGENT.md` remained readable and should be treated as the most trustworthy local project note.
- The rebuilt docs are intentionally minimal and factual so they can serve as a clean baseline after corruption.
