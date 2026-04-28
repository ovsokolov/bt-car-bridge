# Dual-Chip HFP Bridge Debug Log

Use this file as the running debug record for all future lab work.

## Recording Rules

- add a new entry for each meaningful test run
- never delete old entries just because they were wrong
- if a conclusion is later disproved, mark it as superseded in a later entry
- include exact observed log lines whenever possible
- always record the flashed identity marker when firmware was changed
- do not commit or push new changes until the user confirms the relevant test passed

## Status Values

- `PASS`
- `FAIL`
- `INCONCLUSIVE`

## Entry Template

```md
## TEST-YYYYMMDD-XX

- Date/Time:
- Phase/Topic:
- Board(s):
- Firmware identity expected:
- Files changed:
- Procedure:
- Expected result:
- Actual result:
- Status:
- Conclusion:
- Next step:
```

## Current Working Summary

- HF staged identity method was introduced to locate startup failure boundaries:
  - `-S1` = reached after `hci_control_init()`
  - `-S2` = reached after `app_stack_init()`
  - `-S3` = reached after `wiced_audio_buffer_initialize(...)`
- Observed result:
  - `NavTool-PhoneConnect-HFTEST4-S2`
- Current working conclusion:
  - HF most likely fails at or before `wiced_audio_buffer_initialize(...)`

Superseded by later baseline migration:

- HF now boots from the clean `Audio_Headset_Standalone` base on `CYBT-343026-EVAL`
- AG now boots from the local `Audio_Watch` base on `CYBT-343026-EVAL`
- both boards have reached `S3-AI00`
- current work has moved to Phase 1.3 bridge PUART hello exchange

## Resume Point

If work resumes later, start here:

- current highest-value finding is `NavTool-PhoneConnect-HFTEST4-S2`
- this means HF likely stops at or before `wiced_audio_buffer_initialize(...)`
- next debugging step is to instrument the audio-buffer init path itself and expose the exact failure result through identity or another already-proven HCI-visible channel
- do not restart from PUART pin guessing unless this audio-init hypothesis is disproved

## TEST-20260425-01

- Date/Time: 2026-04-25 evening, local lab session
- Phase/Topic: HF startup boundary isolation
- Board(s): HF only
- Firmware identity expected: `NavTool-PhoneConnect-HFTEST4-S1/S2/S3`
- Files changed:
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
- Procedure:
  - flash HF debug image with staged identity markers
  - open HF over HCI in `control_uart_ui`
  - read version and identity
- Expected result:
  - identity suffix indicates furthest startup stage reached
- Actual result:
  - HCI log reported `NavTool-PhoneConnect-HFTEST4-S2`
- Status: `PASS`
- Conclusion:
  - HF startup reaches `hci_control_init()` and `app_stack_init()`
  - HF startup does not reach the post-`wiced_audio_buffer_initialize(...)` marker
- Next step:
  - debug `wiced_audio_buffer_initialize(...)` path directly

## TEST-20260425-02

- Date/Time: 2026-04-25 late morning / midday, local lab session
- Phase/Topic: AG startup boundary comparison against HF
- Board(s): AG only
- Firmware identity expected: `NavTool-CarConnect-AGTEST1-S1/S2/S3`
- Files changed:
  - `CYW9207606EVAL/Audio_Gateway/hci_audio_gateway.c`
- Procedure:
  - flash AG debug image with staged identity markers
  - open AG over HCI in `control_uart_ui`
  - read version and identity
- Expected result:
  - identity suffix indicates furthest startup stage reached in AG reference project
- Actual result:
  - HCI log reported `NavTool-CarConnect-AGTEST1-S3`
- Status: `PASS`
- Conclusion:
  - AG reference project gets past `wiced_bt_stack_init(...)`
  - AG reference project gets past `wiced_audio_buffer_initialize(...)`
  - this makes the HF `...-S2` result more likely to be HF-project-specific, config-specific, or initialization-order-specific rather than a universal 20706 audio-buffer failure
- Next step:
  - compare HF and AG audio buffer configuration and surrounding startup path directly

## TEST-20260428-01

- Date/Time: 2026-04-28 local lab session
- Phase/Topic: Phase 0 baseline after clean HF/AG project migration
- Board(s): HF and AG
- Firmware identity expected:
  - HF: `NavTool-PhoneConnect-HFTEST6-S3-AI00`
  - AG: `NavTool-CarConnect-AGTEST1-S3-AI00`
- Files changed:
  - HF app migrated to clean `Audio_Headset_Standalone` base
  - AG app migrated to local `Audio_Watch` base
  - HCI identity/profile/audio-init diagnostics added on both sides
  - PUART heartbeat added on both sides
- Procedure:
  - flash each board
  - open HCI UART from `control_uart_ui` at `921600`
  - request version and local BDA
  - observe PUART heartbeat
- Expected result:
  - both boards identify over HCI
  - both boards report `S3-AI00`
  - local BDAs differ
  - PUART emits periodic text
- Actual result:
  - HF reported `NavTool-PhoneConnect-HFTEST6-S3-AI00`
  - HF reported combined audio role `A2DP_SINK|HF`, role byte `0x0C`
  - AG reported `NavTool-CarConnect-AGTEST1-S3-AI00`
  - AG reported profile summary `profiles=LE+A2DP_SRC+AVRCP_CT+AVRCP_TG+HFP_AG audio_role=A2DP_SRC`
  - AG reported `Audio init diag: stage=S3, result=0x00, role=0x02, free_before=23464, free_after=11176, tx_buf=0, codec_buf=0x3000`
  - AG local BDA reported `20:70:6A:20:D3:40`
- Status: `PASS`
- Conclusion:
  - Phase 0 baseline is effectively restored on both boards
  - AG HFP AG is represented by profile/component init, not by a dedicated `wiced_bt_audio_buf_config.role` bit on `CYW20706A2`
- Next step:
  - start Phase 1.3 with protocol-shaped PUART hello exchange and HCI-visible TX/RX bridge-line diagnostics

## TEST-20260428-02

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Phase 1.3 bridge PUART hello staging
- Board(s): HF and AG
- Firmware identity expected:
  - HF: `NavTool-PhoneConnect-HFTEST6-S3-AI00`
  - AG: `NavTool-CarConnect-AGTEST1-S3-AI00`
- Files changed:
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/headset_control.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `control_uart_ui/src/control_ui_app/hci.py`
- Procedure:
  - replace lab PUART heartbeats with `BR1,HELLO,HF` and `BR1,HELLO,AG`
  - enable bounded PUART line RX on both boards
  - mirror bridge TX/RX lines to HCI event `0xFF25`
  - decode `0xFF25` in `control_uart_ui`
- Expected result:
  - each board logs `Bridge PUART TX:BR1,HELLO,<role>` over HCI
  - when PUART TX/RX are cross-wired, each board logs peer `RX` hello over HCI
  - PUART carries bridge text without intentional debug trace noise
- Actual result:
  - code staged; build not run in this shell because `make` is not on PATH
- Status: `INCONCLUSIVE`
- Conclusion:
  - ready for local ModusToolbox rebuild/flash validation
- Next step:
  - rebuild HF and AG, flash, then capture HCI logs for `0xFF25` bridge-line events

## TEST-20260428-03

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Host-side PUART relay while boards are not cross-wired
- Board(s): HF and AG
- Files changed:
  - `control_uart_ui/src/control_ui_app/session.py`
  - `control_uart_ui/src/control_ui_app/ui.py`
- Procedure:
  - add raw PUART transmit support to `RawTraceSession`
  - add manual `Send Line` and `Peer Hello` controls to both PUART Trace panes
  - add enabled-by-default relay for `BR1,...` lines between Phone PUART and Car PUART trace ports
- Expected result:
  - HF firmware sends `BR1,HELLO,HF` on Phone PUART
  - UI forwards that line to AG/Car PUART when both PUART trace ports are open
  - AG firmware reports the received line over HCI event `0xFF25`
  - reverse direction works the same for `BR1,HELLO,AG`
- Actual result:
  - host UI code staged
  - `python -m py_compile` passed for `session.py` and `ui.py`
- Status: `READY_FOR_HARDWARE_TEST`
- Next step:
  - open both HCI ports and both PUART trace ports in the UI
  - confirm HCI shows `Bridge PUART RX:BR1,HELLO,<peer>`

## TEST-20260428-04

- Date/Time: 2026-04-28 log cleanup
- Phase/Topic: Make PUART reception proof obvious in HCI logs
- Board(s): AG firmware and UI decoder
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `control_uart_ui/src/control_ui_app/hci.py`
- Procedure:
  - remove AG-only HCI heartbeat event `0xFF21`
  - decode bridge-line `0xFF25` payload prefix `RX:` as `[RECEIVED over PUART]`
  - decode bridge-line `0xFF25` payload prefix `TX:` as `[SENT over PUART]`
- Expected result:
  - AG HCI pane no longer shows periodic `Event 0xFF21`
  - receiver proof appears as `[RECEIVED over PUART] BR1,HELLO,<peer>`
  - local transmit proof appears as `[SENT over PUART] BR1,HELLO,<role>`
- Actual result:
  - source changes staged
  - no remaining AG heartbeat references found in `wiced_app.c`
  - `python -m py_compile` passed for `hci.py`
- Status: `READY_FOR_HARDWARE_TEST`

## TEST-20260428-05

- Date/Time: 2026-04-28 hardware test
- Phase/Topic: Bidirectional PUART hello through host UI relay
- Board(s): HF and AG
- Transport rule:
  - UI remains the active PUART relay for now
  - do not assume physical crosswire until explicitly changed
- Expected result:
  - PhoneConnect shows `[RECEIVED over PUART] BR1,HELLO,AG`
  - CarConnect shows `[RECEIVED over PUART] BR1,HELLO,HF`
- Actual result:
  - user confirmed both sides now receive messages over PUART
- Status: `PASS`
- Conclusion:
  - Phase 1 PUART transport skeleton is working bidirectionally through the UI relay
- Next step:
  - start sending semantic bridge messages over the same UI-relayed PUART path

## TEST-20260428-06

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Phase 2.1 semantic HFP messages over UI-relayed PUART
- Board(s): HF and AG
- Transport rule:
  - UI remains the active PUART relay/pusher
  - physical crosswire is not assumed
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
- Procedure:
  - on phone-side HFP call state transition to incoming, push `BR1,INCOMING[,number]` to Car PUART
  - on phone-side CLIP, push `BR1,CID,<number>` to Car PUART
  - on phone-side active call state, push `BR1,ACTIVE` to Car PUART
  - on phone-side return to idle, push `BR1,ENDED` to Car PUART
  - on phone-side HF audio callbacks, push `BR1,AUDIO_OPEN` / `BR1,AUDIO_CLOSE` to Car PUART
- Expected result:
  - AG HCI pane confirms semantic lines as `[RECEIVED over PUART] BR1,<message>`
  - Bridge Trace shows each UI push reason and target `car_trace`
- Actual result:
  - code staged
  - `python -m py_compile` passed for `ui.py`
- Status: `READY_FOR_HARDWARE_TEST`

## TEST-20260428-07

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Stop periodic PUART hello spam
- Board(s): HF and AG firmware, UI
- Files changed:
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/headset_control.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `control_uart_ui/src/control_ui_app/ui.py`
- Procedure:
  - remove automatic periodic `BR1,HELLO,HF` and `BR1,HELLO,AG` transmit from firmware
  - keep a silent periodic PUART RX flush timer so received lines still appear on HCI as `0xFF25`
  - remove the confusing control-pane `Send PUART Hello` button
  - continue using the PUART Trace pane `Peer Hello` and `Send Line` controls for manual tests
  - clarify PUART Trace manual controls:
    - `Inject Into Board` sends to the board connected to the current pane
    - `Send To Other Board` sends to the opposite board's PUART port
- Expected result:
  - HCI panes no longer receive periodic `[SENT over PUART] BR1,HELLO,...`
  - manual UI sends still produce `[RECEIVED over PUART] BR1,...` on the receiving board
- Actual result:
  - source changes staged
  - no remaining firmware `HELLO_LINE`, `synchronous_write`, or bridge `TX:` heartbeat path found
  - `python -m py_compile` passed for `ui.py`
- Status: `READY_FOR_BUILD_AND_FLASH`

## TEST-20260428-08

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Accept firmware identity suffixes in UI board guard
- Board(s): UI
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
- Procedure:
  - replace exact identity match with prefix-aware check
  - accept `NavTool-PhoneConnect-*` in the PhoneConnect pane
  - accept `NavTool-CarConnect-*` in the CarConnect pane
- Expected result:
  - Phone pairing visibility is not blocked for `NavTool-PhoneConnect-HFTEST6-S3-AI00`
  - wrong-board protection still blocks identities that do not match the expected prefix
- Actual result:
  - source change staged
  - `python -m py_compile` passed for `ui.py`
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-09

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: HF discoverable command path
- Board(s): UI and HF
- Files changed:
  - `control_uart_ui/src/control_ui_app/hci.py`
  - `control_uart_ui/src/control_ui_app/session.py`
  - `control_uart_ui/src/control_ui_app/ui.py`
- Finding:
  - HF firmware does not handle UI generic device commands `0x0008` / `0x0009`
  - HF firmware does handle `HCI_CONTROL_HCI_AUDIO_COMMAND_BUTTON` (`0x2930`)
  - discoverable mode maps to `PLAY_PAUSE_BUTTON`, `BUTTON_VERY_LONG_DURATION_EVENT`, `BUTTON_STATE_HELD`
- Procedure:
  - when enabling PhoneConnect pairing, send HCI Audio Button payload `00 10 00`
  - this emulates long-press SW15 / discoverable mode
- Expected result:
  - HF enters discoverable/connectable mode
  - phone can find the HF board
- Actual result:
  - source change staged
  - Python compile check pending/passed in local run
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-10

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Restore advertised Bluetooth names
- Board(s): HF and AG firmware
- Files changed:
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/wiced_app_cfg.c`
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/headset_control_le.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v1/app_cfg.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v1/app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v1/cycfg_bt.cybt`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v3/app_cfg.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v3/cycfg_bt.cybt`
- Procedure:
  - change HF Bluetooth device name from `Headset` to `NavTool-PhoneConnect`
  - change HF LE GAP name from `Headset LE` to `NavTool-PhoneConnect`
  - change AG Bluetooth/GAP names from `Watch` to `NavTool-CarConnect`
  - stop AG stack config from relying on generated `app_gap_device_name` for the BR/EDR local name
  - keep v1 BLE advertising local-name length as a compile-time constant (`18`) because static initializers cannot use `app_gap_device_name_len`
- Expected result:
  - phone discovery sees HF as `NavTool-PhoneConnect`
  - car/HF discovery sees AG as `NavTool-CarConnect`
- Actual result:
  - source changes staged
  - search no longer finds active `"Headset"`, `"Headset LE"`, or `"Watch"` name literals in the patched config paths
- Status: `READY_FOR_BUILD_AND_FLASH`

## TEST-20260428-11

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: UI responsiveness during HF incoming-call event burst
- Board(s): UI
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
  - `control_uart_ui/src/control_ui_app/session.py`
- Finding:
  - UI event draining used an unbounded loop, so a burst of HFP/HCI events could starve the Tk main loop
  - HCI and PUART serial writes had no explicit write timeout, so a blocked COM write could make the UI appear hung
- Procedure:
  - limit UI queue processing to `75` events per Tk tick
  - reschedule the next drain at `1 ms` only while backlog remains
  - cap each text log to `2500` lines
  - open HCI and PUART serial ports with `write_timeout=0.2`
- Expected result:
  - when HF receives an incoming call, the UI keeps repainting and remains clickable
  - bridge events may drain over several short UI ticks instead of freezing the window
- Actual result:
  - source changes staged
  - `python -m py_compile src\control_ui_app\ui.py src\control_ui_app\session.py src\control_ui_app\hci.py` passed
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-12

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: UI responsiveness second pass after incoming-call slowdown remained
- Board(s): UI
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
- Finding:
  - first event-drain guard improved the UI only slightly
  - the UI was still inserting many small log chunks into Tk text widgets during HF call bursts
  - HF log lines were duplicated into the unified Bridge Trace, doubling render pressure
  - PUART relay and Car AG command writes still ran inline while handling UI events
- Procedure:
  - lower per-tick event processing from `75` to `25`
  - batch text-widget appends and flush them every `50 ms`
  - keep raw side HCI logs in their own side panes only; Bridge Trace now records bridge decisions, not every HCI line
  - add a serial worker queue for PUART relay, PUART semantic pushes, Car AG `SEND_STRING`, and Car AG `Set CIND`
- Expected result:
  - HF incoming-call burst should no longer make the UI painfully slow
  - Phone/HF call events should still push `BR1,...` semantic lines to the Car/AG PUART side
- Actual result:
  - source changes staged
  - `python -m py_compile src\control_ui_app\ui.py src\control_ui_app\session.py src\control_ui_app\hci.py` passed
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-13

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: HF incoming call logs appear only on HF, no AG semantic receive
- Board(s): UI
- Evidence:
  - inspected `C:\Users\ovsok\Documents\HCI-call-log.txt`
  - HF call events are present, including `+CIEV: 2,1`, `RING`, and `+CLIP: "+13474070958",145,...`
  - those call events are wrapped inside opcode `0x0003` instead of arriving as the existing `0x03xx` HF AT event opcodes
  - log also contains many all-zero audio payload packets on `0x2902` and `0x140A`
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
  - `control_uart_ui/src/control_ui_app/session.py`
- Procedure:
  - suppress all-zero `0x2902` and `0x140A` audio payload packets before UI logging/event dispatch
  - add wrapped-HCI text parser for Phone/HF opcode `0x0003`
  - map wrapped `RING`, `+CLIP`, `+CIEV`, and `+CIND` text into the same bridge logic used by normal HF AT events
- Expected result:
  - UI slowdown from zero-payload audio spam should drop sharply
  - wrapped HF `RING` should generate `BR1,INCOMING` to Car/AG PUART
  - wrapped HF `+CLIP` should generate `BR1,CID,<number>` to Car/AG PUART
- Actual result:
  - source changes staged
  - `python -m py_compile src\control_ui_app\ui.py src\control_ui_app\session.py src\control_ui_app\hci.py` passed
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-14

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Correct wrapped-HCI incoming state and suppress duplicate caller ID
- Board(s): UI
- Evidence:
  - AG HCI received `BR1,ACTIVE` followed by repeated `BR1,CID,+13474070958`
  - log starts with wrapped `+CIEV: 2,1`, then `RING`, then `+CLIP`
  - wrapped `+CIEV: 2,0` appears later near call teardown
  - non-zero `0x2902` audio payload packets still flood the log after audio starts
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
  - `control_uart_ui/src/control_ui_app/session.py`
- Procedure:
  - in wrapped-HCI path only, treat `+CIEV: 2,1` as incoming setup instead of active call
  - in wrapped-HCI path only, treat `+CIEV: 2,0` as call ended/idle
  - suppress duplicate `BR1,CID,<number>` while the same incoming call remains active
  - suppress large `0x2902` / `0x140A` audio payload packets regardless of whether payload is all-zero
- Expected result:
  - AG should receive `BR1,INCOMING` instead of premature `BR1,ACTIVE`
  - AG should receive caller ID once per incoming call unless the number changes
  - HF HCI pane should no longer be flooded by audio payload packets
- Actual result:
  - source changes staged
  - `python -m py_compile src\control_ui_app\ui.py src\control_ui_app\session.py src\control_ui_app\hci.py` passed
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-15

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Add repeated ring pulse separate from caller ID
- Board(s): UI
- Finding:
  - duplicate `BR1,CID,<number>` should stay suppressed per incoming call
  - AG still needs a repeated ring indication while the phone continues emitting `RING`
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
- Procedure:
  - send `BR1,RING` on every normal HF `RING`
  - send `BR1,RING` on every wrapped-HCI `RING`
  - keep `BR1,CID,<number>` deduped until the call ends or a new caller ID appears
- Expected result:
  - AG receives `BR1,INCOMING`
  - AG receives one `BR1,CID,<number>`
  - AG receives repeated `BR1,RING` pulses as phone repeats `RING`
  - AG stops ringing on later `BR1,ACTIVE` or `BR1,ENDED`
- Actual result:
  - source changes staged
  - compile check pending/passed locally
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-16

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Force one-shot incoming bridge event independent of stale UI call state
- Board(s): UI
- Evidence:
  - inspected `C:\Users\ovsok\Documents\HCI-call-log.txt`
  - first call event sequence is wrapped `+CIEV: 2,1`, then `RING`, then `+CLIP`, then a later `+CIEV: 2,0`
  - AG received `BR1,CID`, later `BR1,RING`, then `BR1,ENDED`, but did not show `BR1,INCOMING`
  - likely cause: `_refresh_phone_call_state()` returned early because the UI already believed the phone state was incoming
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
- Procedure:
  - add `_incoming_bridge_sent` as a separate one-shot latch for the AG `BR1,INCOMING` line
  - send `BR1,INCOMING` from incoming-call hints even if the internal call-state transition was already consumed
  - reset `_incoming_bridge_sent` when phone indicators return idle/ended
- Expected result:
  - AG receives `BR1,INCOMING` once per incoming call episode
  - AG still receives repeated `BR1,RING`
  - AG still receives deduped `BR1,CID,<number>`
  - AG receives `BR1,ENDED` when wrapped `+CIEV: 2,0` arrives
- Actual result:
  - source changes staged
  - `python -m py_compile src\control_ui_app\ui.py src\control_ui_app\session.py src\control_ui_app\hci.py` passed
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-17

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Correct wrapped-HCI answered-call transition
- Board(s): UI
- Evidence:
  - inspected `C:\Users\ovsok\Documents\HCI-call-log.txt`
  - answered call sequence at `13:07:46` is wrapped `+CIEV: 1,1`, then wrapped `+CIEV: 2,0`
  - previous logic treated every wrapped `+CIEV: 2,0` as ended, so AG received `BR1,ENDED` instead of `BR1,ACTIVE`
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
  - `control_uart_ui/dual_chip_hfp_bridge_debug_log.md`
- Procedure:
  - treat wrapped `+CIEV: 1,1` as active call and emit `BR1,ACTIVE`
  - treat wrapped `+CIEV: 2,0` as setup-complete if normalized call state is already active
  - treat wrapped `+CIEV: 1,0` as call ended and emit `BR1,ENDED`
  - reset the incoming one-shot latch when wrapped `+CIEV: 2,1` starts a new incoming setup
- Expected result:
  - AG receives `BR1,INCOMING` at call start after restarting the UI with this patch
  - AG receives `BR1,ACTIVE` when the call is answered
  - AG does not receive `BR1,ENDED` until the later wrapped `+CIEV: 1,0` or true idle/end transition
- Actual result:
  - source changes staged
  - `python -m py_compile src\control_ui_app\ui.py src\control_ui_app\session.py src\control_ui_app\hci.py` passed
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-18

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Retry missing incoming semantic before CID/RING follow-ons
- Board(s): UI
- Evidence:
  - AG now receives proper `BR1,ACTIVE` and `BR1,ENDED`
  - AG still does not show `BR1,INCOMING`
  - HF log still contains wrapped `+CIEV: 2,1` at the start of each call
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
- Procedure:
  - make `_send_bridge_protocol_line()` return whether the target PUART session was open and the write was queued
  - only set `_incoming_bridge_sent` after `BR1,INCOMING` is actually queued
  - retry `BR1,INCOMING` after caller ID is parsed, before sending `BR1,CID`
- Expected result:
  - AG receives `BR1,INCOMING` before or near the first `BR1,CID`
  - AG still receives repeated `BR1,RING`
  - AG still receives `BR1,ACTIVE` on answer and `BR1,ENDED` on hangup
- Actual result:
  - source changes staged
  - `python -m py_compile src\control_ui_app\ui.py src\control_ui_app\session.py src\control_ui_app\hci.py` passed
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-19

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Preserve burst PUART RX logs in firmware HCI pane
- Board(s): HF and AG firmware
- Evidence:
  - AG PUART pane showed `TX BR1,INCOMING`, `TX BR1,RING`, and `TX BR1,CID,...` in the same second
  - AG HCI pane only showed later received lines, making it look like `INCOMING` was missing
  - firmware PUART RX logger stored only one pending RX line before the 1-second HCI flush, so later lines overwrote earlier lines
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/headset_control.c`
- Procedure:
  - replace the single pending PUART RX line slot with an 8-line ring queue on both firmware sides
  - drain all queued RX lines to HCI on each periodic flush
  - keep HCI send out of the PUART interrupt callback
- Expected result:
  - AG HCI pane shows `[RECEIVED over PUART] BR1,INCOMING`, `[RECEIVED over PUART] BR1,RING`, and `[RECEIVED over PUART] BR1,CID,...` even when they arrive in the same second
  - HF side gets the same protection for future AG-to-HF bursts
- Actual result:
  - source changes staged
  - firmware build/flash test pending
- Status: `READY_FOR_BUILD_AND_FLASH`
