# Dual-Chip HFP Bridge Debug Log

Use this file as the running debug record for all future lab work.

## Recording Rules

- add a new entry for each meaningful test run
- never delete old entries just because they were wrong
- if a conclusion is later disproved, mark it as superseded in a later entry
- include exact observed log lines whenever possible
- always record the flashed identity marker when firmware was changed

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
- Expected result:
  - HCI panes no longer receive periodic `[SENT over PUART] BR1,HELLO,...`
  - manual UI sends still produce `[RECEIVED over PUART] BR1,...` on the receiving board
- Actual result:
  - source changes staged
  - no remaining firmware `HELLO_LINE`, `synchronous_write`, or bridge `TX:` heartbeat path found
  - `python -m py_compile` passed for `ui.py`
- Status: `READY_FOR_BUILD_AND_FLASH`
