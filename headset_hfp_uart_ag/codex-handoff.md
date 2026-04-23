# Codex Handoff

## What This Project Is
This workspace is the AG-side firmware for the bridge concept. The board should connect to the car and present as `NavTool-CarConnect`.

## Changes Already Made
- Updated runtime and advertised name to `NavTool-CarConnect`.
- Updated configurator/generated Bluetooth name paths to stay consistent with the visible name.
- Fixed the old hardcoded short BLE advertisement name handling in the btstack v1 app code so the full name can be exposed.
- Adjusted the btstack v1 advertisement initializer to use `MAX_LEN_GAP_DEVICE_NAME` instead of `app_gap_device_name_len`, because the latter is generated as a variable and is not valid in a static initializer.
- Added a custom host event `HCI_CONTROL_MISC_EVENT_BRIDGE_IDENTITY` in both the host-tools include copy and the firmware-facing SDK include copy.
- Updated `hci_control_misc.c` so the board reports `NavTool-CarConnect` over serial during version reporting.
- Patched the bundled ClientControl source to log the bridge identity event.
- Removed AG-side fake call/ring simulation logic from `hci_control_hfp_ag.c`.
- Changed classic PIN pairing flow so firmware sends PIN requests to the host UI instead of auto-replying with the built-in firmware PIN.
- Fixed the PIN-request callback call site to pass the BD_ADDR data rather than the pointer-to-array wrapper required by the event struct.
- Added explicit handling for host unbond commands in the firmware device command switch so host-side re-pair testing can remove existing bonds cleanly.
- Added the missing forward declaration for the local bonded-device delete helper so the new unbond handler builds cleanly.
- Added explicit handling for `HCI_CONTROL_COMMAND_BOND` so host-side bonding requests now invoke BR/EDR security bonding instead of being ignored.

## AG Cleanup Summary
The old wrapper included custom state management to make a car and ClientControl behave as if a real phone were present:
- repeating ring timer
- forced incoming call indicator latching
- `RING` / `+CIND` / `+CIEV` rewriting
- extra call-waiting state handling

That logic was removed so the bridge can be driven by actual external phone/car events and host coordination instead of local simulation.

## Architecture Context
- Car should see this board as the AG/phone side.
- The phone-facing board lives in `headset_hfp_hf`.
- The Python UI in `control_ui` is intended to orchestrate the two serial links and logs.
- Audio is planned over hardware pins between the two devkits, not UART.

## Open Work
- Rebuild and validate AG firmware behavior after cleanup.
- Confirm no repeated synthetic ring behavior remains.
- Add only the host-visible events/commands needed for the new bridge workflow.
- Continue reducing assumptions inherited from the old watch-derived project where necessary.
- Validate PIN-based car pairing and numeric-comparison pairing with the updated Python UI.

## Cautions
- Shared SDK library code still references `hci_control_ag_local_call_state_update`, so the symbol remains as a no-op wrapper hook.
- Do not remove supporting event-driven behavior without checking shared-library expectations.
