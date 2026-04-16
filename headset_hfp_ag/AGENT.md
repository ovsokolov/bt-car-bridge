# AG Project Agent Notes

## Purpose
This project is the `CarConnect` firmware for the `CYBT-343026-EVAL` dev kit. It acts as the car-facing side of the bridge system and should present as the phone/AG counterpart to the car.

## Primary Goals
- Present to the car as `NavTool-CarConnect`.
- Act as the AG side for HFP toward the car.
- Support the bridge system together with the HF firmware and the Python host UI.
- Keep control/logging on USB serial while audio is handled over direct hardware pins between devkits.

## Important Locations
- App root: `mtb-example-btsdk-audio-headset-standalone`
- AG control path: `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
- App config / advertised name: `mtb-example-btsdk-audio-headset-standalone/wiced_app_cfg.c`
- Shared host API copy: `mtb_shared/wiced_btsdk/tools/btsdk-host-apps-bt-ble/release-v4.9.3/include/hci_control_api.h`
- ClientControl source copy: `mtb_shared/wiced_btsdk/tools/btsdk-host-apps-bt-ble/release-v4.9.3/client_control/source`

## Key Decisions
- Device name should remain `NavTool-CarConnect` unless requirements explicitly change.
- Legacy fake-phone/ring state simulation added for ClientControl compatibility has been removed from the AG wrapper.
- Firmware emits a custom bridge identity event so host tools can identify the connected board over serial.
- This project is part of a three-project system:
  - `headset_hfp_ag` = car-facing AG firmware
  - `headset_hfp_hf` = phone-facing HF firmware
  - `control_ui` = Python host controller and logs/UI

## Notes For Future Codex Sessions
- Start with `project_status.md` for current state.
- Use `codex-handoff.md` for recent history and bridge assumptions.
- Avoid reintroducing synthetic call/ring behavior unless specifically requested.
- Keep the bridge architecture in mind: real phone and car events should drive behavior now.
- If a change materially affects bridge behavior, pairing, reconnect, profile roles, visibility, or operator workflow, update `AGENT.md`, `project_status.md`, and `codex-handoff.md` in every affected repo before ending the task.
