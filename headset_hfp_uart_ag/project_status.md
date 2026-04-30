# AG Project Status

## Summary
This project is the `CarConnect` firmware workspace for the car-facing side of the bridge system.

## Completed
- Visible device name updated to `NavTool-CarConnect`.
- Generated/configurator Bluetooth name data aligned with the new name.
- BLE advertisement name-length handling fixed so the full name is not truncated.
- btstack v1 advertisement initializer fixed to use a compile-time GAP name length constant so the project builds with regenerated GATT data.
- Shared host API copy updated with bridge identity event support.
- Firmware-facing SDK include copy updated with bridge identity event support.
- Firmware emits bridge identity over the serial host interface.
- Bundled ClientControl source logs the bridge identity event.
- AG wrapper fake call/ring simulation removed.
- Classic PIN pairing now routes through host UI request/reply flow instead of fixed firmware auto-reply.
- PIN request callback call site corrected to match the helper function BD_ADDR parameter type.
- Firmware now explicitly handles host unbond commands so devkit-side bonds can be removed during repeated pairing tests.
- Unbond handler build issue fixed by declaring the local bonded-device delete helper before first use.
- Firmware now explicitly handles host bond commands so the Python UI can initiate BR/EDR pairing from the devkit side.
- Car-originated HFP actions now have a firmware PUART return path:
  - AG observes car `ATA` / `AT+CHLD=1` / `AT+CHLD=2` and queues `BR1,ANSWER` to the HF board.
  - AG observes car `AT+CHLD=0` and queues `BR1,REJECT` to the HF board.
  - AG observes car `AT+CHUP` and queues `BR1,REJECT` while incoming, otherwise `BR1,HANGUP`.

## In Progress
- Shifting the project from ClientControl-oriented simulation toward real bridge-driven behavior.
- Aligning firmware PUART bridge behavior with real car and phone HFP actions.

## Pending
- Build and flash verification after cleanup.
- Car-side validation with real bridge-driven HFP events.
- Validate that car-screen answer/reject/end actions produce `AG_CMD:TX BR1,ANSWER/REJECT/HANGUP`, then confirm HF reports `HF_CMD:ANSWER/HANGUP sent to phone`.
- Review A2DP/AVRCP support needed for the broader bridge plan.
- Add any missing host commands/events required for pairing, state sync, and bridge diagnostics.
- Validate PIN-based car pairing and numeric-comparison pairing with the updated Python UI.

## Known Constraints
- Audio is not intended to travel over UART.
- The board should identify itself over serial as `NavTool-CarConnect`.
- Legacy test-flow assumptions from the watch-derived source may still exist elsewhere and should be audited carefully before removal.
