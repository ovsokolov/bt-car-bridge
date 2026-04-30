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

## TEST-20260428-20

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Start Phase 3 call-control return path over bridge protocol
- Board(s): UI
- Goal:
  - expose car-originated call controls as AG-to-HF bridge semantic lines while the UI is still the active PUART relay
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
- Procedure:
  - on car AG `AT+CHLD=1`, `AT+CHLD=2`, or `ATA` during incoming call, push `BR1,ANSWER` to Phone/HF PUART
  - on car AG `AT+CHLD=0` during incoming call, push `BR1,REJECT` to Phone/HF PUART
  - on car AG `AT+CHUP`, push `BR1,HANGUP` to Phone/HF PUART
  - keep existing direct Phone/HF raw AT forwarding active so the current UI-relayed lab setup can still answer/hang up without physical crosswire firmware execution
- Expected result:
  - when answering from the car side, Phone/HF HCI pane shows `[RECEIVED over PUART] BR1,ANSWER`
  - when rejecting/hanging up from the car side, Phone/HF HCI pane shows `[RECEIVED over PUART] BR1,REJECT` or `BR1,HANGUP`
  - actual phone call control still works through the existing UI-to-HF HCI raw AT path
- Actual result:
  - source changes staged
  - `python -m py_compile src\control_ui_app\ui.py src\control_ui_app\session.py src\control_ui_app\hci.py` passed
- Status: `READY_FOR_SOFTWARE_TEST`

## TEST-20260428-21

- Date/Time: 2026-04-28 workspace prep
- Phase/Topic: Persist paired-device NVRAM and auto reconnect preferred peers
- Board(s): UI, HF, AG
- Finding:
  - the AG/Audio_Watch firmware stores link keys by sending NVRAM chunks to the host and expects the host to push them back on the next startup
  - the UI previously displayed NVRAM events but did not persist/replay them
  - user rejected this direction because reconnect must not depend on the UI
- Files changed:
  - `control_uart_ui/src/control_ui_app/hci.py`
  - `control_uart_ui/src/control_ui_app/models.py`
  - `control_uart_ui/src/control_ui_app/session.py`
  - `control_uart_ui/src/control_ui_app/storage.py`
  - `control_uart_ui/src/control_ui_app/ui.py`
- Procedure:
  - UI-based NVRAM persistence/replay was removed from the working tree
  - next implementation must move link-key persistence/reconnect behavior into HF/AG firmware
- Expected result:
  - after one successful pairing, board reboot/reopen should reconnect without requiring UI-side NVRAM replay
  - the user should not need to make HF pairable/visible or discover the car on AG side every run once the firmware owns persisted peers
- Actual result:
  - UI-side approach superseded before test
- Status: `SUPERSEDED_BY_FIRMWARE_RECONNECT_PLAN`

## TEST-20260428-22

- Date/Time: 2026-04-28 pair-log review
- Phase/Topic: HF firmware-owned reconnect after power cycle
- Board(s): HF / PhoneConnect
- Finding:
  - `Documents/pair-log.txt` shows HF paired/connected to phone address `AD:19:09:E1:BC:48` around `13:52:57`
  - after HF reboot at `13:53:15`, the board returned as `NavTool-PhoneConnect-HFTEST6-S3-AI00`
  - there was no `AUTORECONNECT` HCI marker and no reconnect events after reboot
- Files changed:
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/headset_control.c`
- Procedure:
  - bump HF identity marker to `HFTEST7`
  - after successful `btheadset_post_bt_init()`, make HF non-pairable, non-discoverable, connectable on BR/EDR
  - if the headset library reports a saved reconnect peer, call `bt_hs_spk_control_reconnect()`
  - log reconnect decision through HCI bridge event `0xFF25`
- Expected result:
  - next flashed HF image reports `NavTool-PhoneConnect-HFTEST7-...`
  - HCI log prints `[PUART bridge] AUTORECONNECT:attempt HFP_HF+A2DP_SINK` when a saved peer exists
  - if no saved peer exists, HCI log prints `[PUART bridge] AUTORECONNECT:no bonded peer`
- Actual result:
  - source changed only; no build/flash was run by Codex per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## 2026-04-29 AGTEST50 Rollback To Stable Command-Disabled AG

- Date/Time: 2026-04-29 AG rollback after unstable car-originated command experiments
- Phase/Topic: Return AG firmware to known stable receive/simulate behavior
- Board(s): AG / CarConnect
- Finding:
  - car-originated AT-command observers and delayed PUART command TX remained unstable
  - rollback target is the stable command-disabled AG shape: receive HF status lines over PUART and simulate the car-facing HFP AG call state only
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v1/app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v3/app.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST50` as a rollback marker
  - removed the SDK `HCI_CONTROL_AG_EVENT_AT_CMD` post-send observer hook
  - removed HCI transport TX-complete flush callbacks used by the experiment
  - removed AG-side `BR1,ANSWER/REJECT/HANGUP` emitters
  - kept AG receive/simulate path for `BR1,INCOMING/RING/CID/ACTIVE/ENDED`
- Expected result:
  - AG should return to the stable behavior seen before car-originated command TX attempts
  - incoming call display/status path should still work
  - car-originated answer/reject/hangup remains intentionally incomplete until a safer non-invasive source path is chosen
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260430-01

- Date/Time: 2026-04-30 AGTEST63 CLCC request adapter
- Phase/Topic: Firmware-owned response to car `AT+CLCC` without restoring unstable AG parser experiments
- Board(s): AG / CarConnect
- Finding:
  - AGTEST61/62 logs showed the car sends `AT+CLCC` / `HCI_CONTROL_AG_EVENT_CLCC_REQ` after `BR1,INCOMING/RING/CID`
  - CYBT-343026-EVAL uses 20706 `btstack_v1`; the local AG public startup API is `hfp_ag_startup(..., features)` and does not expose the newer callback-style AG event handler used by btstack-v3/PSoC Edge examples
  - the newer callback design is present behind `BTSTACK_VER >= 0x03000001`, commonly on newer targets such as CYW20721B2/CYW20719B2-class examples, not this 20706 btstack-v1 build
- Files changed:
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
  - `mtb_shared_overrides/README.md`
- Procedure:
  - bumped AG identity to `AGTEST63`
  - added one narrow weak SDK hook: `hci_control_ag_bridge_on_clcc_req(handle)` is called only for `HCI_CONTROL_AG_EVENT_CLCC_REQ`
  - app firmware implementation only records a pending CLCC handle from the SDK event path
  - existing AG app timer context flushes the pending CLCC response using the same app/HCI command path as the official audio gateway example: `HCI_CONTROL_AG_COMMAND_STR`
  - CLCC response uses app-owned bridge state: incoming status sends `+CLCC: 1,1,4,0,0,"<number>",145`, active status sends `+CLCC: 1,1,0,0,0,"<number>",145`, followed by `OK`
  - no parser-side PUART writes, no `HCI_CONTROL_AG_EVENT_AT_CMD` observer, no answer/reject/hangup behavior, no direct `hfp_ag_send_RING_to_hf()`, and no unsolicited CLCC
- Expected result:
  - when car logs `Phone AT command: AT+CLCC`, AG HCI should next show `AG_CALL:CLCC req`, `AG_CALL:STR +CLCC: ...`, `AG_CALL:STR OK`, and `AG_CALL:CLCC response`
  - if the missing car screen was caused by no CLCC response, the call screen should now appear after the first CLCC request
  - if AGTEST63 is unstable, roll back only the SDK weak hook plus app CLCC pending flush; do not change reconnect or existing BR1 call-status behavior
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260430-01

- Date/Time: 2026-04-30 AG call-initiation app/HCI path hardening
- Phase/Topic: Present phone-originated incoming call on car side without `mtb_shared` hooks
- Board(s): AG / CarConnect
- Finding:
  - AG reconnect/passive connect behavior was reported working again after stale SDK object cleanup
  - call-initiation should remain app-owned: incoming `BR1,*` lines from HF are translated inside tracked AG app code into existing AG HCI command handler calls
  - no vendor SDK parser changes are required for this direction
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
- Procedure:
  - bumped AG identity to `AGTEST62`
  - kept `BR1,INCOMING/ACTIVE/ENDED` on the existing `HCI_CONTROL_AG_COMMAND_SET_CIND` plus `HCI_CONTROL_AG_COMMAND_STR` path
  - changed `BR1,RING` to assert incoming `callsetup=1` before sending `RING`
  - changed `BR1,CID,<number>` to assert incoming `callsetup=1` before sending `+CLIP`
  - moved `hci_control_ag_bridge_handle_line()` from the PUART byte receive path into the AG PUART flush timer path, so the ISR/drain path only queues completed lines
  - sanitized `BR1,CID,<number>` by storing only phone-number characters so quoted or spaced UI text still becomes a clean CLIP number
  - removed AGTEST57-59 experiments that forced SDK indicator bitmap bits, used direct `hfp_ag_send_RING_to_hf()`, logged custom flag state, or sent unsolicited synthetic `+CLCC`
  - confirmed `examples/mtb-example-btsdk-audio-gateway-master` uses the same command-handler model: `HCI_CONTROL_AG_COMMAND_SET_CIND` calls `hfp_ag_set_cind()`, and `HCI_CONTROL_AG_COMMAND_STR` calls `hfp_ag_send_cmd_str()`
  - added diagnostics only: log `AG_CALL:CIND <values>`, `AG_CALL:STR <text>`, and `AG_CALL:CLIP skip ...` before calling the same example-style command path
  - `BR1,RING` and `BR1,CID` now always re-assert `CIND 0,1,0,1,5,5,0` and `+CIEV: 2,1` before `RING`/`+CLIP`, even if AG local state was already incoming
- Expected result:
  - if `BR1,INCOMING` is missed, late, or arrives before the car HFP link is ready, the next `BR1,RING` or `BR1,CID,<number>` still starts the car incoming-call UI
  - repeated `BR1,RING` remains safe because duplicate incoming state updates are ignored, while `RING` still repeats
  - AG HCI should show `RX:BR1,...` followed by `AG_CALL:...`; if it only shows `RX:` and `AG_CALL:no car HFP link`, the car HFP profile is not connected yet
  - AG HCI should show `RX:BR1,...` followed by `AG_CALL:incoming` / `AG_CALL:ring` / `AG_CALL:CLIP sent`
  - if the car still shows no call screen while AG receives `AT+CLCC`, the likely clean-design blocker is that this 20706 AG library forwards `CLCC_REQ` to the HCI host and does not expose a firmware callback in the btstack-v1 startup signature
  - AGTEST62 expected markers include `AG_CALL:CIND 0,1,0,1,5,5,0`, `AG_CALL:STR +CIEV: 2,1`, `AG_CALL:STR RING`, and either `AG_CALL:STR +CLIP: ...` or `AG_CALL:CLIP skip disabled/no cid` on every `BR1,RING`
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-05

- Date/Time: 2026-04-29 end-of-day checkpoint
- Phase/Topic: Preserve working AG call display baseline before car-command retry
- Board(s): HF / PhoneConnect and AG / CarConnect
- Finding:
  - user confirmed the current path works for call initiation/display
  - UI semantic injection remains disabled; UI is only the temporary raw PUART relay
  - current missing piece is car-originated answer/reject/hangup from AG to HF
- Decision:
  - do not roll back the current working HF-to-AG call simulation baseline
  - tomorrow's test should add only passive detection of car `ATA/CHUP/CHLD`
  - detection must queue `BR1,ANSWER/REJECT/HANGUP` toward HF without locally changing AG call state or opening/closing SCO
  - AG should wait for HF/phone feedback (`BR1,ACTIVE` or `BR1,ENDED`) before updating the car-facing call state
- Next-session implementation preference:
  - first try the existing AG `HCI_CONTROL_AG_EVENT_AT_CMD` event path in tracked/app code
  - avoid adding new behavior inside the `mtb_shared` AG parser
  - if app code can observe the AT event, write `BR1,ANSWER/REJECT/HANGUP` to AG PUART immediately from app-owned code
  - do not emit extra nested HCI events from inside the AT event path
- Status: `PAUSED_FOR_NEXT_SESSION`

## TEST-20260429-04

- Date/Time: 2026-04-29 AGTEST51 mtb_shared parser rollback
- Phase/Topic: Remove remaining vendor-parser call-control side effects
- Board(s): AG / CarConnect
- Finding:
  - after AG command TX rollback, `mtb_shared` still had behavior-changing AG parser edits for car `ATA`, `AT+CHUP`, and `AT+CHLD`
  - those edits made AG locally mutate call state and open/close SCO even though no command was sent to HF
  - this matched the log symptom where car `ATA` produced `AG Audio Open` while HF kept sending `BR1,RING`
- Files changed:
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag_command.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST51`
  - restored stock-like `ATA`, `CHUP`, and `CHLD` handling: acknowledge only; do not locally answer/hang up, mutate call indicators, or open/close SCO
  - kept AG incoming-call simulation support for `BR1,INCOMING/RING/CID/ACTIVE/ENDED`
  - kept `BIND/BIEV`, `CREG`, and local CLCC/indicator support needed for car compatibility and call-screen display
- Expected result:
  - car button presses should no longer force local AG audio/state changes without the phone-side HF
  - car-originated answer/reject/hangup remains intentionally disabled
  - incoming call display path should remain available for testing stability
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-03

- Date/Time: 2026-04-29 AGTEST50 rollback after unstable command TX retry
- Phase/Topic: Return AG firmware to stable command-disabled behavior
- Board(s): AG / CarConnect
- Finding:
  - user requested rollback after the AG-side car-originated command experiment still did not work reliably
  - the safe baseline is AG receiving HF-originated call-state lines and simulating the car-facing HFP AG call state only
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v1/app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v3/app.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST50`
  - removed the SDK `HCI_CONTROL_AG_EVENT_AT_CMD` post-send observer hook
  - removed HCI transport TX-complete flush callbacks
  - removed AG-side `BR1,ANSWER/REJECT/HANGUP` emitters
  - kept AG receive/simulate handling for `BR1,INCOMING/RING/CID/ACTIVE/ENDED`
- Expected result:
  - AG should return to stable incoming-call display behavior
  - car-originated answer/reject/hangup is intentionally disabled again
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-02

- Date/Time: 2026-04-29 AG stability rollback
- Phase/Topic: Stabilize AG after attempted car-originated command TX
- Board(s): AG / CarConnect
- Finding:
  - user reported AG became unstable after adding AG-side translation from car HFP AT commands to `BR1,ANSWER/REJECT/HANGUP`
  - direct PUART writes from inside the vendor HFP AG AT parser are treated as unsafe for this build
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag_command.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST37`
  - removed `hci_control_ag_bridge_send_command_line()` and its header declaration
  - removed direct `BR1,ANSWER`, `BR1,REJECT`, and `BR1,HANGUP` PUART command writes from the vendor AG parser
  - kept the stable AG call-status receiver path for incoming `BR1,INCOMING/RING/CID/ACTIVE/ENDED`
  - refreshed the tracked AG SDK override patch
- Expected result:
  - AG startup and incoming-call display return to the pre-command-TX stable behavior
  - car-originated answer/reject/hangup is still not complete and needs a safer non-UI firmware path later
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-03

- Date/Time: 2026-04-29 AG AT-hook rollback
- Phase/Topic: Restore stable AG behavior after flag-only AT observer still failed
- Board(s): AG / CarConnect
- Finding:
  - user reported the flag-only `AGTEST47` still errored
  - because `AGTEST47` had no timer flush, no bridge PUART TX, and no custom bridge HCI send, the remaining suspect was the `HCI_CONTROL_AG_EVENT_AT_CMD` observer/parsing itself
- Files changed:
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.h`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST48`
  - removed `hfp_ag_bridge_note_at_command()` and the `HCI_CONTROL_AG_EVENT_AT_CMD` hook from the SDK AG library
  - removed the unused AG app command flag storage/function/prototype
  - refreshed the tracked AG SDK override patch so it no longer contains the failed AT-command observer
- Expected result:
  - AG remains stable and still handles incoming `BR1,INCOMING/RING/CID/ACTIVE/ENDED` from HF over PUART
  - car-originated answer/reject/hangup is intentionally not implemented in `AGTEST48`
  - original AG HCI raw AT command events should still appear because the SDK still copies AT command data into `HCI_CONTROL_AG_EVENT_AT_CMD`
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-04

- Date/Time: 2026-04-29 AG transport-complete command TX retry
- Phase/Topic: Send car Answer/Reject/Hangup without parser-side or AT-event-build side effects
- Board(s): AG / CarConnect
- Finding:
  - `ag-hci-log.txt` showed car `ATA` reaches AG and opens AG audio, but HF keeps sending `BR1,RING` because AGTEST48 intentionally sends no command back to HF
  - repeated `BR1,RING` after car answer explains the apparent call-screen instability: AG is still simulating an incoming call because the phone-side HF was never commanded to answer
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v1/app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/COMPONENT_btstack_v3/app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST49`
  - kept the original `HCI_CONTROL_AG_EVENT_AT_CMD` payload build/send path intact
  - after `wiced_transport_send_data()` returns for `HCI_CONTROL_AG_EVENT_AT_CMD`, AG records a pending command flag from `ATA`, `AT+CHUP`, or `AT+CHLD`
  - the existing HCI transport TX-complete callback flushes the pending flag to PUART as `BR1,ANSWER`, `BR1,REJECT`, or `BR1,HANGUP`
  - no custom `AG_CMD_TX` HCI status event is sent for this test path
- Expected result:
  - car Answer sends `BR1,ANSWER` from AG PUART after the raw AT HCI event has been transmitted
  - UI raw relay forwards it to HF PUART; HF answers the phone and should then emit `BR1,ACTIVE`, stopping repeated ringing
  - if this is unstable, rollback to AGTEST48/45 and treat car-originated commands as requiring a different source than the AG HFP library path
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-03

- Date/Time: 2026-04-29 AG car-originated command TX retry
- Phase/Topic: Send Answer/Reject/Hangup from car HFP commands to HF over PUART without parser-side writes
- Board(s): AG / CarConnect
- Finding:
  - `AGTEST37` was stable after removing direct PUART writes from the vendor HFP AG parser
  - HF's stable phone-status TX path queues lines and flushes outside the HFP event handler, so AG should follow that pattern
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag_command.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST39`
  - added an AG PUART TX queue in `wiced_app.c`
  - corrected the first retry that used a 25 ms timer; AG now flushes immediately after queueing, matching the HF status TX pattern
  - the parser now only enqueues semantic commands:
    - `ATA` -> `BR1,ANSWER`
    - `AT+CHUP` -> `BR1,REJECT` while incoming, otherwise `BR1,HANGUP`
    - `AT+CHLD=0` -> `BR1,REJECT`
    - `AT+CHLD=1/2` -> `BR1,ANSWER`
  - AG HCI logs outgoing bridge commands with `TX:BR1,...`
- Expected result:
  - pressing car Answer/Reject/Hangup queues and immediately flushes an AG PUART TX line
  - UI raw relay forwards that line to HF PUART
  - HF `HFTEST13` receives the line and performs the phone HFP action
  - AG should remain as stable as `AGTEST37`; if it regresses, revert this test and design a fully app-owned command callback path
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-04

- Date/Time: 2026-04-29 AG AT-event command TX retry
- Phase/Topic: Move car-originated command bridge from parser internals to AG AT event surface
- Board(s): AG / CarConnect
- Finding:
  - user confirmed `AGTEST40` is stable after removing AG command bridge calls from `hfp_ag_command.c`
  - `hfp_ag_parse_AT_command()` already emits `HCI_CONTROL_AG_EVENT_AT_CMD` after command parsing/handling completes
  - `hfp_ag.c` already uses stable app-level hooks from `hfp_ag_hci_send_ag_event()` for open/connected/closed events
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST41`
  - left `hfp_ag_command.c` free of bridge command emission
  - added `hci_control_ag_at_command_received()` in app-level AG code
  - hooked `HCI_CONTROL_AG_EVENT_AT_CMD` in `hfp_ag.c` to call the app-level observer after parsing
  - translated car AT commands:
    - `ATA` -> `BR1,ANSWER`
    - `AT+CHUP` -> `BR1,REJECT` while incoming, otherwise `BR1,HANGUP`
    - `AT+CHLD=0` -> `BR1,REJECT`
    - `AT+CHLD=1/2` -> `BR1,ANSWER`
- Expected result:
  - AG remains stable like `AGTEST40`
  - pressing car Answer/Reject/Hangup emits one `BR1,*` line over AG PUART
  - UI raw relay forwards the line to HF PUART, where `HFTEST13` performs the phone action
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-05

- Date/Time: 2026-04-29 AG command TX rollback after AT-event instability
- Phase/Topic: Return AG to stable receive-only bridge behavior
- Board(s): AG / CarConnect
- Finding:
  - user reported `AGTEST41` was unstable
  - both AG command TX attempts were unstable:
    - direct parser hook in `hfp_ag_command.c`
    - later AT-event observer hook from `hfp_ag.c`
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST42`
  - removed the AT-event observer hook from `hfp_ag.c`
  - removed app-level AG command TX helpers from `hci_control_hfp_ag.c`
  - kept AG receive/simulate handling for `BR1,INCOMING/RING/CID/ACTIVE/ENDED`
- Expected result:
  - AG returns to stable `AGTEST40` behavior with new identity marker
  - car-originated answer/reject/hangup remains disabled until a non-invasive path is found
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-06

- Date/Time: 2026-04-29 AG answer/reject trace-only diagnostic
- Phase/Topic: Locate car-originated HFP AG commands without bridge side effects
- Board(s): AG / CarConnect
- Finding:
  - `AGTEST42` was stable with AG command TX disabled
  - AG exposes raw car AT commands through `HCI_CONTROL_AG_EVENT_AT_CMD`
  - lower command decode path maps to `BTA_AG_HF_CMD_A`, `BTA_AG_HF_CMD_CHUP`, `BTA_AG_HF_CMD_D`, `BTA_AG_HF_CMD_BLDN`, and `BTA_AG_HF_CMD_CHLD`
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag_command.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST43`
  - added `WICED_BT_TRACE` only at `HCI_CONTROL_AG_EVENT_AT_CMD`
  - added `WICED_BT_TRACE` labels for `ATD` and `AT+BLDN`
  - kept existing trace labels for `ATA`, `AT+CHUP`, and `AT+CHLD`
  - no `BR1,ANSWER/REJECT/HANGUP` emitters were added
  - no PUART writes or HCI bridge-status writes were added for command TX
- Expected result:
  - AG remains stable like `AGTEST42`
  - existing HCI AT command events should still show raw car commands in the UI
  - if WICED trace routing is visible in the test setup, the new trace labels identify the AG callback/parser path
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-07

- Date/Time: 2026-04-29 AG AT flag diagnostic in HCI
- Phase/Topic: Make car-originated AG AT detection visible in HCI without command TX
- Board(s): AG / CarConnect
- Finding:
  - user requested our diagnostic flag in the AG AT path and visible in HCI
  - previous command TX attempts remain disabled
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
- Procedure:
  - bumped AG identity to `AGTEST44`
  - added HCI-visible status lines from the AG AT event callback:
    - `AG_AT_FLAG:ATA answer`
    - `AG_AT_FLAG:CHUP reject_or_hangup`
    - `AG_AT_FLAG:ATD dial`
    - `AG_AT_FLAG:BLDN redial`
    - `AG_AT_FLAG:CHLD call_control`
  - no `BR1,ANSWER/REJECT/HANGUP` emitters were added
  - no AG PUART command TX was added
- Expected result:
  - pressing car buttons should show `AG_AT_FLAG:*` in AG HCI logs while preserving AG stability
- Actual result:
  - source changed only; Codex did not build or flash per user rule
  - SDK override patch refresh was attempted but the patch file was locked by another process; refresh it after the file is closed if this image passes testing
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-08

- Date/Time: 2026-04-29 AG nested-HCI diagnostic rollback
- Phase/Topic: Remove AG AT flag diagnostic after instability
- Board(s): AG / CarConnect
- Finding:
  - user reported `AGTEST44` was still unstable
  - likely cause is nested HCI transport use: `hfp_ag_hci_send_ag_event()` was already preparing/sending `HCI_CONTROL_AG_EVENT_AT_CMD`, and the diagnostic called `hci_control_send_bridge_status_line()` from inside that path
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST45`
  - removed `AG_AT_FLAG:*` HCI bridge-status emission
  - restored `HCI_CONTROL_AG_EVENT_AT_CMD` to only copy/send the original raw AT command event
  - refreshed the AG SDK override patch
- Expected result:
  - AG returns to stable command-disabled behavior
  - UI can still display raw `Phone AT command: ATA/CHUP/...` from the existing event
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-09

- Date/Time: 2026-04-29 AG deferred command flag retry
- Phase/Topic: Retry car-originated command TX using flag-only AT hook and app timer flush
- Board(s): AG / CarConnect
- Finding:
  - direct PUART/HCI work from the AG parser or AT event path destabilized AG
  - safer model is to capture only a byte flag in `HCI_CONTROL_AG_EVENT_AT_CMD`, then emit from a known app timer context
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch`
- Procedure:
  - bumped AG identity to `AGTEST46`
  - `HCI_CONTROL_AG_EVENT_AT_CMD` now only calls `hci_control_ag_bridge_note_car_command()` with a byte command flag
  - no PUART write, no HCI status send, and no allocation is done inside the AG AT event path
  - the existing AG PUART RX flush timer calls `hci_control_ag_bridge_flush_pending_car_commands()`
  - safe timer context writes/logs:
    - `ATA` / `AT+CHLD=1/2` -> `BR1,ANSWER`
    - `AT+CHUP` -> `BR1,REJECT` while call setup is incoming, otherwise `BR1,HANGUP`
    - `AT+CHLD=0` -> `BR1,REJECT`
    - `ATD` / `AT+BLDN` currently log flags only, because no bridge dial/redial command is defined yet
- Expected result:
  - AG remains stable
  - car Answer/Reject/Hangup emits a `BR1,*` command from app timer context, not from AG stack callback context
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260428-23

- Date/Time: 2026-04-28 pair-log review
- Phase/Topic: Correct HF firmware-owned reconnect trigger
- Board(s): HF / PhoneConnect
- Finding:
  - latest `Documents/pair-log.txt` shows HF returned as `NavTool-PhoneConnect-HFTEST7-S3-AI00` at `14:00:34`
  - the log shows immediate low-level traffic involving the previously paired phone `AD:19:09:E1:BC:48`, but the expected `AUTORECONNECT` HCI marker never appears
  - source review found the reconnect gate used `bt_hs_spk_control_reconnect_peer_bdaddr_get()`, which only returns true after reconnect is already in progress, not before reconnect starts
- Files changed:
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/headset_control.c`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
  - `control_uart_ui/dual_chip_hfp_bridge_debug_log.md`
- Procedure:
  - bump HF identity marker to `HFTEST8`
  - schedule reconnect 2 seconds after successful `btheadset_post_bt_init()` instead of calling immediately
  - check saved link-key slot 0 with `bt_hs_spk_control_link_keys_get()` and `bt_hs_spk_control_misc_data_content_check()`
  - if a saved peer exists, make HF non-pairable, non-discoverable, connectable, then call `bt_hs_spk_control_reconnect()`
  - log `AUTORECONNECT:start HFP_HF+A2DP_SINK`, `AUTORECONNECT:requested`, or `AUTORECONNECT:no bonded peer` through HCI event `0xFF25`
- Expected result:
  - next flashed HF image reports `NavTool-PhoneConnect-HFTEST8-...`
  - after boot, Phone/HF HCI pane prints `[PUART bridge] AUTORECONNECT:start HFP_HF+A2DP_SINK` followed by `[PUART bridge] AUTORECONNECT:requested` when a saved peer exists
  - if no saved peer exists, Phone/HF HCI pane prints `[PUART bridge] AUTORECONNECT:no bonded peer`
- Actual result:
  - source changed only; no build/flash was run by Codex per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260428-24

- Date/Time: 2026-04-28 reconnect behavior refinement
- Phase/Topic: Retry reconnect when phone Bluetooth is toggled while HF stays powered
- Board(s): HF / PhoneConnect
- Finding:
  - HFTEST8 reconnect works when the board is power-cycled while the phone is already available
  - when the board remains powered, phone Bluetooth is turned off, then phone Bluetooth is turned on again, HFTEST8 does not automatically reconnect
  - root cause: HFTEST8 only schedules a reconnect shortly after boot; it does not keep retrying after a later BR/EDR disconnect
- Files changed:
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/headset_control.c`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
  - `control_uart_ui/dual_chip_hfp_bridge_debug_log.md`
- Procedure:
  - bump HF identity marker to `HFTEST9`
  - register `headset_control_conn_status_cb` with the headset library `conn_status_change_cb`
  - on BR/EDR link-up, mark connected and stop the reconnect retry timer
  - on BR/EDR link-down, mark disconnected and start a 10-second periodic reconnect retry timer
  - each retry keeps HF non-pairable, non-discoverable, connectable, checks saved link-key slot 0, and calls `bt_hs_spk_control_reconnect()` if not already reconnecting
- Expected result:
  - after phone Bluetooth off, Phone/HF HCI pane logs `[PUART bridge] AUTORECONNECT:BR_EDR link down retry scheduled`
  - while disconnected, Phone/HF HCI pane periodically logs reconnect retry/request markers
  - after phone Bluetooth is turned on again, HF reconnects without requiring pairable/visible mode and logs `[PUART bridge] AUTORECONNECT:link restored stop retry`
- Actual result:
  - source changed only; no build/flash was run by Codex per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260428-25

- Date/Time: 2026-04-28 reconnect behavior refinement
- Phase/Topic: Add AG firmware reconnect retry when peer disappears while AG stays powered
- Board(s): AG / CarConnect
- Finding:
  - AG had the same shape as HF before retry support: `hci_control_auto_reconnect_bonded_peer()` attempted saved-peer reconnect once after startup
  - if the peer disappears and later returns while AG remains powered, AG needs a firmware-owned retry loop instead of depending on the UI or peer to initiate
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
  - `control_uart_ui/dual_chip_hfp_bridge_debug_log.md`
- Procedure:
  - bump AG identity marker to `AGTEST2`
  - register `hci_control_connection_status_cb` through `wiced_bt_dev_register_connection_status_change()`
  - on BR/EDR link-up, mark connected and stop the reconnect retry timer
  - on BR/EDR link-down, mark disconnected and start a 10-second periodic reconnect retry timer
  - each retry uses the first restored local NVRAM peer and calls `hfp_ag_connect()` and `a2dp_app_hci_control_connect()`
- Expected result:
  - next flashed AG image reports `NavTool-CarConnect-AGTEST2-...`
  - when the peer drops while AG remains powered, Car/AG HCI pane logs `[PUART bridge] AUTORECONNECT:BR_EDR link down retry scheduled`
  - while disconnected, Car/AG HCI pane periodically logs `AUTORECONNECT:attempt HFP_AG+A2DP_SRC`
  - when the peer returns and BR/EDR reconnects, Car/AG HCI pane logs `[PUART bridge] AUTORECONNECT:link restored stop retry`
- Actual result:
  - source changed only; no build/flash was run by Codex per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260428-26

- Date/Time: 2026-04-28 AG inquiry and pairing support
- Phase/Topic: Keep manual inquiry from fighting firmware reconnect; route legacy PIN pairing through UI
- Board(s): AG / CarConnect
- Finding:
  - after adding AG reconnect retry, manual Start Inquiry can compete with the firmware retry loop because the retry loop may start HFP AG and A2DP source connection attempts while the operator is trying to discover a new peer
  - numeric comparison pairing was already supported: firmware sends `HCI_CONTROL_EVENT_USER_CONFIRMATION` and UI replies with `HCI_CONTROL_COMMAND_USER_CONFIRMATION`
  - legacy PIN pairing was not UI-driven: firmware auto-replied with default `0000`, so the UI PIN dialog path would never be used on AG
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
  - `control_uart_ui/dual_chip_hfp_bridge_debug_log.md`
- Procedure:
  - bump AG identity marker to `AGTEST3`
  - on manual inquiry start, stop AG reconnect retry and mark inquiry active
  - while inquiry is active, suppress firmware reconnect attempts with `AUTORECONNECT:paused for inquiry`
  - emit HCI bridge status markers `INQUIRY:start`, `INQUIRY:complete`, `INQUIRY:stop`, or `INQUIRY:start failed`
  - on `BTM_PIN_REQUEST_EVT`, send `HCI_CONTROL_EVENT_PIN_REQUEST` to the UI instead of auto-replying `0000`
  - handle `HCI_CONTROL_COMMAND_PIN_REPLY` from UI and call `wiced_bt_dev_pin_code_reply()`
- Expected result:
  - next flashed AG image reports `NavTool-CarConnect-AGTEST3-...`
  - pressing Start Inquiry on AG shows `[PUART bridge] INQUIRY:start` and discovered devices populate when peers are discoverable
  - if legacy PIN pairing is requested, UI shows PIN prompt and firmware uses the entered PIN
  - numeric comparison prompt remains supported as before
- Actual result:
  - source changed only; no build/flash was run by Codex per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260428-27

- Date/Time: 2026-04-28 AG reconnect reset toward known older behavior
- Phase/Topic: Remove split-brain AG reconnect ownership and add required pairing/profile traces
- Board(s): AG / CarConnect
- Finding:
  - current AG reconnect path had become unstable because reconnect/profile sequencing was split between `wiced_app.c` and `hci_control.c`
  - backup project used older firmware-owned staging in `wiced_app.c`: HFP AG first, then AVRCP TG, then A2DP source via `av_app_initiate_sdp()`
  - UI must only select/manual-pair and display logs; reconnect and profile sequence must remain firmware-owned
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
  - `control_uart_ui/dual_chip_hfp_bridge_debug_log.md`
- Procedure:
  - bump AG identity marker to `AGTEST16`
  - keep `hci_control_ag_init()` as the AG init path and log `INIT:HFP_AG`
  - log SDP registration result with `INIT:SDP registered` or `INIT:SDP failed`
  - enable connectable/discoverable/pairable after `BTM_ENABLED_EVT`
  - log link-key save/restore with `PAIR:link keys save` and `PAIR:link key restore ok/fail`
  - restore backup-style staged reconnect in `wiced_app.c`: `AUTO_AG:stage HFP_AG`, `AUTO_AG:stage AVRCP_TG`, `AUTO_AG:stage A2DP_SRC`
  - make HFP AG service open/close callbacks in `hci_control.c` log-only so they do not start competing reconnect/A2DP timers
  - cancel firmware reconnect when manual bond/unbond starts
- Expected result:
  - next flashed AG image reports `NavTool-CarConnect-AGTEST16-...`
  - on boot with saved bond, Car/AG HCI pane reports SDP/profile init, link-key restore, boot connectable/pairable/discoverable, then staged HFP/AVRCP/A2DP reconnect
  - if reconnect still fails, the HCI markers should categorize it as no SDP, no AG init, no link-key restore, no AG service connect request, or remote not initiating/accepting profile connection
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260428-28

- Date/Time: 2026-04-28 AG reconnect event gating after AGTEST16 hardware log
- Phase/Topic: Wait for HFP AG open before AVRCP/A2DP reconnect stages
- Board(s): AG / CarConnect
- Finding:
  - AGTEST16 pairing succeeded and link keys were saved
  - staged reconnect fired immediately: `AUTO_AG:stage HFP_AG`, then `AUTO_AG:stage AVRCP_TG`, then `AUTO_AG:stage A2DP_SRC`
  - actual AG service open happened much later, after A2DP had already failed
  - failure category from the log: AG init and link-key save were OK, AG service connect request was issued, but A2DP was attempted before HFP AG service opened
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag.c`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
  - `control_uart_ui/dual_chip_hfp_bridge_debug_log.md`
- Procedure:
  - bump AG identity marker to `AGTEST17`
  - change `wiced_app.c` staged reconnect so HFP stage does not automatically advance to AVRCP/A2DP by timer
  - after HFP stage calls `hfp_ag_connect()`, log `AUTO_AG:wait HFP_AG open`
  - add `hf_autoreconnect_hfp_opened()` to continue the staged timer only after AG open/connected callback
  - add `hci_control_ag_service_opened()` and call it from local `hfp_ag.c` on successful `HCI_CONTROL_AG_EVENT_OPEN`
  - keep `hci_control_ag_service_connected()` as a second possible continuation point
- Expected result:
  - next flashed AG image reports `NavTool-CarConnect-AGTEST17-...`
  - after pairing or boot reconnect, Car/AG HCI pane shows `AUTO_AG:stage HFP_AG` then `AUTO_AG:wait HFP_AG open`
  - only after `AG Service Open` should HCI show `AUTO_AG:HFP_AG open continue`, `AUTO_AG:stage AVRCP_TG`, and `AUTO_AG:stage A2DP_SRC`
  - A2DP should no longer be attempted before HFP AG service open
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260428-29

- Date/Time: 2026-04-28 AG HFP battery/HF indicator command tolerance
- Phase/Topic: Avoid silent no-response for `AT+BIEV` / `AT+BIND`
- Board(s): AG / CarConnect
- Finding:
  - local AG parser command table recognizes `+BIEV` and `+BIND`
  - `+BIEV` is the HFP HF indicator update used for things like HF battery level
  - the handler did not have cases for `BTA_AG_HF_CMD_BIEV` or `BTA_AG_HF_CMD_BIND`, so those commands could fall through without an `OK`
  - `+CBC` already replies `OK`; the main missing battery-related response was `+BIEV`
- Files changed:
  - `headset_hfp_uart_ag/mtb_shared/wiced_btsdk/dev-kit/libraries/btsdk-audio/release-v4.9.5/COMPONENT_hfp_audio_gateway/hfp_ag_command.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
  - `control_uart_ui/dual_chip_hfp_bridge_debug_log.md`
- Procedure:
  - bump AG identity marker to `AGTEST18`
  - add no-op `OK` handling for `BTA_AG_HF_CMD_BIND`
  - add no-op `OK` handling for `BTA_AG_HF_CMD_BIEV`
- Expected result:
  - if the car/HF sends battery/HF-indicator setup during HFP negotiation, AG responds instead of leaving the peer waiting
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260428-30

- Date/Time: 2026-04-28 initial AG connect isolation
- Phase/Topic: Stop firmware reconnect work and restore controlled first-pair profile connect
- Board(s): AG / CarConnect
- Finding:
  - AGTEST18 log showed pairing and key save succeeded, and `AG Service Open` eventually appeared
  - firmware auto sequence was still controlling the profile path and waiting on a local SDK hook that did not visibly fire in the HCI log
  - current priority is initial pair/connect, not reboot reconnect
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `control_uart_ui/src/control_ui_app/session.py`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
  - `control_uart_ui/dual_chip_hfp_bridge_debug_log.md`
- Procedure:
  - bump AG identity marker to `AGTEST19`
  - disable firmware auto reconnect after pairing and on boot for this test
  - after pairing success, UI Connect Selected flow starts initial AG profile connect again
  - UI waits up to 18 seconds for `AG Service Open` before attempting A2DP source
  - if pairing sequence worker is still finishing when pairing-complete arrives, UI waits for it instead of skipping profile connect
- Expected result:
  - next flashed AG image reports `NavTool-CarConnect-AGTEST19-...`
  - after pairing, HCI pane logs `AUTO_AG:disabled after pair`
  - UI logs `AG pairing completed ... starting initial profile connect`
  - UI logs `Connecting AG profile ...`
  - after `AG Service Open`, UI logs `AG service opened on handle ...; connecting A2DP source ...`
- Actual result:
  - source changed only; Codex did not build or flash per user rule
  - `python -m py_compile control_uart_ui/src/control_ui_app/session.py` passed
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260428-31

- Date/Time: 2026-04-28 transfer proven initial HFP connect into firmware
- Phase/Topic: Firmware-owned initial HFP AG connect after pairing, no A2DP/reconnect automation
- Board(s): AG / CarConnect
- Finding:
  - AGTEST19 hardware log proved the stable initial sequence: pair, UI sends AG profile connect, `AG Service Open`, SLC completes, and A2DP can connect afterward
  - user wants that initial HFP connect behavior moved into firmware, while leaving A2DP manual/unchanged for now
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `control_uart_ui/src/control_ui_app/session.py`
  - `control_uart_ui/dual_chip_hfp_bridge_context.md`
  - `control_uart_ui/dual_chip_hfp_bridge_debug_log.md`
- Procedure:
  - bump AG identity marker to `AGTEST20`
  - add a one-shot `ag_initial_hfp_connect_timer`
  - on successful BR/EDR pairing, firmware queues initial HFP AG connect after 1 second
  - firmware logs `AUTO_AG:HFP only after pair`, `AUTO_AG:queue initial HFP_AG`, and `AUTO_AG:initial HFP_AG connect`
  - UI no longer starts AG profile connect after pairing; it logs `firmware owns initial HFP connect`
  - do not start A2DP or AVRCP from firmware in this step
- Expected result:
  - next flashed AG image reports `NavTool-CarConnect-AGTEST20-...`
  - after pairing, Car/AG HCI pane shows firmware HFP-only connect markers
  - HFP AG service opens/connects without UI sending `AG Connect`
  - A2DP remains manual for this test
- Actual result:
  - source changed only; Codex did not build or flash per user rule
  - `python -m py_compile control_uart_ui/src/control_ui_app/session.py` passed
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260428-32

- Date/Time: 2026-04-28 end-of-day reconnect/profile checkpoint
- Phase/Topic: Confirm stable paired-peer reconnect and prepare next car-command step
- Board(s): HF / PhoneConnect and AG / CarConnect
- Finding:
  - user confirmed both boards reconnect to their paired peers automatically after reboot/power-cycle
  - AG initial pairing now brings up both HFP AG and A2DP Source
  - the A2DP initial-connect blocker was SDP callback status `WICED_BT_SDP_DB_FULL`; accepting it as usable, then searching the partial DB for `UUID_SERVCLASS_AUDIO_SINK`, allowed A2DP to continue
  - audio streaming/content testing is intentionally deferred because there is no meaningful audio test path yet
- Commits:
  - `d313326 Improve AG profile connection flow`
  - `5b2bdee Improve HF auto reconnect flow`
- Next step:
  - continue with car-originated commands over the current UI-relayed PUART bridge path
  - do not switch to physical cross-wire until the user explicitly says so
- Status: `CONFIRMED_COMPLETE`

## TEST-20260429-01

- Date/Time: 2026-04-29 car-originated call-control bring-up
- Phase/Topic: Route Answer/Reject/Hangup from car AG side to phone HF side over PUART semantics
- Board(s): HF / PhoneConnect and AG / CarConnect
- Finding:
  - `ag-hci-log.txt` shows the car button press reaches AG HCI as `Phone AT command: ATA`
  - no `BR1,ANSWER` appeared in PUART logs, so the missing hop was AG AT command -> bridge semantic command
  - HF firmware was only logging PUART RX lines and did not execute `BR1,ANSWER` / `BR1,REJECT` / `BR1,HANGUP`
  - the natural AG firmware AT hook is inside ignored `mtb_shared`; do not rely on hidden SDK edits for committed behavior
- Files changed:
  - `control_uart_ui/src/control_ui_app/ui.py`
  - `headset_hfp_uart_hf/mtb-example-btsdk-audio-headset-standalone/headset_control.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
- Procedure:
  - bump HF identity marker to `HFTEST13`
  - bump AG identity marker to `AGTEST35`
  - initially tested UI semantic mapping for car-side `ATA` / `AT+CHLD` / `AT+CHUP`, then rejected that approach because the UI must not own bridge semantics
  - disabled UI semantic PUART injection with `_semantic_puart_injection_enabled = False`; helpers now log `Skipped UI semantic injection ...` and return without writing to the opposite PUART
  - HF firmware consumes `BR1,ANSWER` and calls `wiced_bt_hfp_hf_perform_call_action(...ANSWER...)`
  - HF firmware consumes `BR1,REJECT` / `BR1,HANGUP` and calls `wiced_bt_hfp_hf_perform_call_action(...HANGUP...)`
  - HF firmware now uses the tracked app-level `config.hfp.post_handler` to originate call-status bridge lines from HFP events: `BR1,INCOMING`, repeated `BR1,RING`, one-shot `BR1,CID,<number>`, `BR1,ACTIVE`, and `BR1,ENDED`
  - HF firmware queues outgoing PUART status lines and flushes them from the existing 1-second PUART timer, also logging each line as HCI `TX:...`
  - removed the AG-side command-originating experiment after AG stability concern; AG remains responsible only for receiving/simulating phone call status from incoming `BR1,*` lines
- Expected result:
  - incoming phone call makes HF firmware write `BR1,INCOMING`, `BR1,RING`, and `BR1,CID,<number>` to HF PUART
  - UI raw relay moves those lines to AG PUART with no semantic translation
  - AG HCI shows `[RECEIVED over PUART] BR1,...` and updates the car call screen
  - Car PUART write timeouts caused by UI semantic injection should stop after restarting the UI with the new gate
  - car-originated answer/reject/hangup still needs firmware-originated command TX from AG or another non-UI semantic source; do not consider that complete yet
- Actual result:
  - source changed only; Codex did not build or flash per user rule
  - `python -m py_compile control_uart_ui/src/control_ui_app/ui.py` passed
  - `git diff --check` passed
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`

## TEST-20260429-02

- Date/Time: 2026-04-29 AG car-command stability isolation
- Phase/Topic: Determine whether AG instability is caused by side effects or by the AT-event hook itself
- Board(s): AG / CarConnect
- Finding:
  - `AGTEST46` was still reported unstable even after moving command TX to the existing app timer context
  - next isolation step is to remove every custom side effect from the car AT event path
- Files changed:
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.h`
  - `headset_hfp_uart_ag/mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
- Procedure:
  - bumped AG identity to `AGTEST47`
  - left the SDK `HCI_CONTROL_AG_EVENT_AT_CMD` observer in place so it only sets `ag_bridge_pending_car_commands`
  - removed the AG timer call to `hci_control_ag_bridge_flush_pending_car_commands()`
  - removed AG bridge command PUART TX and custom `AG_CMD_TX` / `AG_CMD_FLAG` HCI status sends
- Expected result:
  - car AT commands should still appear through the original SDK `HCI_CONTROL_AG_EVENT_AT_CMD` HCI event
  - no `BR1,ANSWER/REJECT/HANGUP` should be emitted by AG in this test image
  - if `AGTEST47` is stable, the instability was caused by deferred bridge side effects; if unstable, the event hook/parsing itself is suspect
- Actual result:
  - source changed only; Codex did not build or flash per user rule
- Status: `READY_FOR_USER_BUILD_AND_HARDWARE_TEST`
