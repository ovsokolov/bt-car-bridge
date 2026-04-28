# Dual-Chip HFP + AVRCP Bridge Context

## Goal

Build a two-board Bluetooth bridge on `CYBT-343026-EVAL` kits where:

- `HF` board connects to the real phone as an HFP Hands-Free device and AVRCP peer
- `AG` board connects to the real car as an HFP Audio Gateway device and AVRCP peer
- `PUART` is used only for board-to-board bridge control messages
- `PCM/I2S` carries SCO audio
- `HCI UART` is reserved for host debug, trace, and optional lab control

This is not a raw Bluetooth packet tunnel.

## Current Resume Point - 2026-04-28

Both copied baseline projects now boot on `CYBT-343026-EVAL` and are visible through `control_uart_ui` at `921600`.

Confirmed HF side:

- active base: `Audio_Headset_Standalone`
- identity: `NavTool-PhoneConnect-HFTEST6-S3-AI00`
- local BDA observed: `20:70:6A:20:D3:3F`
- profiles observed: `LE+A2DP_SINK+AVRCP_CT+AVRCP_TG+HFP_HF`
- audio buffer role observed: `A2DP_SINK|HF`, role byte `0x0C`
- PUART heartbeat was visible before Phase 1.3 changes

Confirmed AG side:

- active base: local `Audio_Watch`
- identity: `NavTool-CarConnect-AGTEST1-S3-AI00`
- local BDA observed: `20:70:6A:20:D3:40`
- profiles observed: `LE+A2DP_SRC+AVRCP_CT+AVRCP_TG+HFP_AG`
- audio buffer role observed: `A2DP_SRC`, role byte `0x02`
- `CYW20706A2` SDK does not define an AG audio-buffer role bit
- PUART heartbeat and HCI heartbeat were visible before Phase 1.3 changes

Current Phase 1.3 code staged:

- HF transmits `BR1,HELLO,HF\r\n` on PUART once per second
- AG transmits `BR1,HELLO,AG\r\n` on PUART once per second
- both boards enable PUART RX and parse bounded line-oriented input
- both boards mirror bridge TX/RX lines to HCI event `0xFF25`
- `control_uart_ui` decodes `0xFF25` as `Bridge PUART ...`
- debug trace is no longer intentionally routed to PUART on these Phase 1.3 paths

Next lab test:

- rebuild and flash HF and AG
- first verify each board still reports identity/audio init over HCI
- watch HCI logs for `Bridge PUART TX:BR1,HELLO,<role>`
- wire HF PUART TX to AG PUART RX and AG PUART TX to HF PUART RX, with common ground
- watch for `Bridge PUART RX:BR1,HELLO,<peer-role>` on each HCI port

The intended design is:

- HF receives real phone-side HFP events
- HF translates them into simplified bridge messages over PUART
- AG consumes those bridge messages and synthesizes phone-like behavior toward the car
- AG sends simplified bridge commands/events back to HF for actions that must occur on the phone side
- HF and AG apply the same translation model for AVRCP metadata and media-control actions

## Core Principle

Do not mirror raw Bluetooth events, raw AT traffic, or raw AVRCP packets across the bridge as the primary architecture.

Instead:

- each chip owns its local Bluetooth stack behavior
- each chip translates between local stack callbacks and a small bridge protocol
- the UART bridge carries semantic state and commands, not profile internals

This keeps the system more stable and decoupled from local stack implementation details.

## System Architecture

```text
Phone <-> HF board <== PUART control ==> AG board <-> Car
                 \\                     //
                  \\--- PCM/I2S SCO ---//

Host PC <-> HCI UART on each board (debug / trace / lab control)
```

Responsibilities:

- HF board
  - real HFP HF role toward the phone
  - local AVRCP phone-facing role
  - observes incoming call / active call / audio state from phone side
  - executes answer / reject / hangup / dial actions toward phone when commanded
  - publishes media metadata / playback state as bridge messages when needed
  - executes media-control actions toward phone when commanded

- AG board
  - real HFP AG role toward the car
  - local AVRCP car-facing role
  - synthesizes phone-like behavior toward the car
  - raises commands back to HF when the car initiates an action
  - maps bridge media messages into car-visible metadata and media state

- UI / host tools
  - open HCI UART ports
  - display logs, state, trace, version, identity, BDA
  - optionally inject lab test commands
  - must not own HFP bridge policy

## Transport Split

### PUART

Use PUART strictly for board-to-board bridge communication.

Recommended usage:

- line-oriented text protocol for first implementation
- one message per line
- bounded payload
- no audio payloads
- no debug trace mixed into this channel

### HCI UART

Use HCI UART for:

- firmware control from host tools
- `GET_VERSION`
- `READ_LOCAL_BDA`
- device started / identity / status events
- HCI trace and debug in lab workflows

This is the standard AIROC host-control path, not the bridge transport path.

### PCM / I2S

Use PCM/I2S only for SCO audio path.

Do not move call audio over PUART.

## Observed Local Project Facts

From the current workspace:

- HF firmware identity is `NavTool-PhoneConnect`
- AG firmware identity is `NavTool-CarConnect`
- custom bridge identity is emitted on the HCI misc/version path
- current HCI UART setup in the HF workspace is tracked as `921600`
- debug trace routing and HCI transport are separate concepts in this codebase

Important distinction:

- PUART debug text configuration is not the same as HCI transport configuration
- changing debug route or PUART baud does not automatically change HCI control transport baud

## Recent Debug Findings

The recent HF-side PUART investigation produced one important result that should guide the next session:

- HF debug images were stamped with identity markers like `HFTEST1`, `HFTEST2`, `HFTEST3`, `HFTEST4`
- to locate the exact failing startup boundary, startup stage markers were added as an identity suffix:
  - `-S1` = reached after `hci_control_init()`
  - `-S2` = reached after `app_stack_init()`
  - `-S3` = reached after `wiced_audio_buffer_initialize(...)`

Observed result:

- HCI log showed `NavTool-PhoneConnect-HFTEST4-S2`

Interpretation:

- HF startup gets past `hci_control_init()`
- HF startup gets past `app_stack_init()`
- HF startup does not reach the post-`wiced_audio_buffer_initialize(...)` stage

Practical implication:

- the immediate blocker is most likely at or before `wiced_audio_buffer_initialize(...)`
- this means the lack of PUART heartbeat, missing raw PUART text, missing LED/timer activity, and missing later-stage debug markers should not currently be blamed on PUART wiring first
- next debugging should focus on why HF does not progress beyond audio buffer initialization

Notes from the same investigation:

- BSP/platform packages consistently map eval-board PUART as:
  - `TX = P31`
  - `RX = P04`
- the board/platform package mismatch theory is currently weak
- the more useful current theory is startup abort before later debug/test hooks become active

## Debug Process

Use the debugging workflow below for every future lab session.

Rules:

- record every meaningful test in the running debug log
- do not rely on memory or chat history as the primary source of truth
- every test entry must include both:
  - what was changed
  - what was observed
- every test must end with an explicit result:
  - `PASS`
  - `FAIL`
  - `INCONCLUSIVE`
- if a test changes the firmware image, update the visible identity marker so the flashed image can be proven from HCI
- if a test is intended to isolate a failure boundary, encode the boundary into a host-visible path when possible
  - preferred order:
    - identity/version-visible markers
    - HCI events
    - LED/GPIO proof
    - raw UART/PUART text

Recommended debugging order:

1. Prove the exact image on the board
2. Prove the exact startup stage reached
3. Prove whether the callback / timer / state transition executes
4. Only then prove transport visibility on PUART or other side channels

Do not skip recording:

- COM port used
- baud rate used
- flashed identity marker
- exact observed log lines
- whether the result changed the active theory

## Debug Record Keeping

Use a dedicated running markdown log for tests:

- [dual_chip_hfp_bridge_debug_log.md](C:\BT_Projects\control_uart_ui\dual_chip_hfp_bridge_debug_log.md)

Expected usage:

- append a new test entry after each meaningful debug run
- do not overwrite previous conclusions unless a later test disproves them
- if a conclusion is disproved, mark the old one as superseded rather than silently replacing it

Minimum fields for each entry:

- test id
- date/time
- phase / topic
- target board(s)
- firmware identity expected
- files changed
- exact procedure
- expected result
- actual result
- status: `PASS` / `FAIL` / `INCONCLUSIVE`
- conclusion
- next step

## Current Debug Focus

Current highest-value HF finding:

- `NavTool-PhoneConnect-HFTEST4-S2`

Current interpretation:

- HF reaches `hci_control_init()`
- HF reaches `app_stack_init()`
- HF does not reach the post-`wiced_audio_buffer_initialize(...)` stage

Therefore, the current main debugging focus should be:

- debug failure at or before `wiced_audio_buffer_initialize(...)`

and not primarily:

- PUART electrical routing
- BTSpy behavior
- raw bridge protocol logic

## Recommended Bridge Protocol Direction

Start with a compact semantic protocol.

Example message set:

HF -> AG:

- `HELLO,HF`
- `INCOMING,<number optional>`
- `CID,<number>`
- `ACTIVE`
- `ENDED`
- `AUDIO_OPEN`
- `AUDIO_CLOSE`

AG -> HF:

- `HELLO,AG`
- `ANSWER`
- `REJECT`
- `HANGUP`

Optional later:

- `OUTGOING,<number>`
- `DIAL,<number>`
- `REDIAL`
- `DTMF,<digit>`
- `HELD`
- `RESUME`

AVRCP/media examples:

HF -> AG:

- `META_TITLE,<text>`
- `META_ARTIST,<text>`
- `META_ALBUM,<text>`
- `META_PLAYBACK,PLAYING`
- `META_PLAYBACK,PAUSED`

AG -> HF:

- `PLAY`
- `PAUSE`
- `NEXT`
- `PREV`
- `VOL_UP`
- `VOL_DOWN`

Recommended wire format for v1:

```text
BR1,HELLO,HF
BR1,INCOMING,+12125551212
BR1,CID,+12125551212
BR1,ACTIVE
BR1,ENDED
BR1,AUDIO_OPEN
BR1,AUDIO_CLOSE
BR1,ANSWER
BR1,REJECT
BR1,HANGUP
BR1,META_TITLE,Example Song
BR1,META_ARTIST,Example Artist
BR1,META_PLAYBACK,PLAYING
BR1,PLAY
BR1,PAUSE
BR1,NEXT
```

Rules:

- transmit with `\\r\\n`
- parser accepts `\\n` and trims `\\r`
- ignore unknown lines
- bound payload length
- log malformed messages locally

## Why This Approach Fits Better

Advantages over raw event mirroring:

- less coupling to internal HFP callback details
- easier to debug on a serial console
- simpler recovery from malformed or duplicated messages
- easier to evolve role-specific logic independently
- better fit for future direct RX/TX board communication if UI is removed
- gives HFP and AVRCP one common bridge model instead of inventing separate transport strategies

## Initial Scope Recommendation

Keep v1 intentionally small:

1. single call only
2. incoming call path first
3. answer / reject / hangup
4. active / ended
5. audio open / close
6. no multi-call or call waiting in v1
7. no retry / replay layer in v1 unless real testing proves it is needed

For AVRCP, keep v1 intentionally small too:

1. play / pause / next / prev only
2. title / artist / playback-state metadata only
3. bounded text length and truncation rules
4. no album art or large binary metadata over PUART
5. no raw vendor-dependent AVRCP tunneling

## Phased Plan

### Phase 0: Baseline and Instrumentation

Goals:

- verify both boards boot cleanly
- verify HCI UART control on both boards
- verify bridge identity, version, local BDA, and device-started flow
- verify PUART electrical link and baud with a minimal text echo or hello exchange
- defer PCM/I2S audio validation until a later phase
- verify local AVRCP role behavior on each side using standard host/HCI tools where possible

Success criteria:

- each board identified correctly over HCI
- HCI traces readable at the expected host baud
- PUART hello exchanged between boards
- no unintended debug text contaminating PUART channel

### Phase 0 Execution Checklist

Use this as the practical bring-up list for the current restart.

Known current assumptions from the workspace:

- HF HCI identity: `NavTool-PhoneConnect`
- AG HCI identity: `NavTool-CarConnect`
- HF HCI baud: `921600`
- AG HCI baud: `921600`
- `GET_VERSION`, `READ_LOCAL_BDA`, and `DEVICE_STARTED` are already present on the HCI path

Tasks:

1. Flash known-good HF and AG firmware images
2. Open HF HCI port from host at `921600`
3. Confirm host sees:
   - `DEVICE_STARTED`
   - version response
   - bridge identity `NavTool-PhoneConnect`
   - local BDA
4. Open AG HCI port from host at `921600`
5. Confirm host sees:
   - `DEVICE_STARTED`
   - version response
   - bridge identity `NavTool-CarConnect`
   - local BDA
6. Verify no PUART bridge code is active yet
7. Add the smallest possible PUART lab check:
   - one boot `HELLO` line, or
   - one manual echo/test line
8. Confirm PUART carries only bridge/test text and no HCI/debug trace noise
9. Capture exact COM port mapping for:
   - HF HCI
   - AG HCI
   - any separate PUART test wiring if exposed in lab setup

Pass criteria:

- both boards identify correctly every time over HCI
- no ambiguity about which board is HF vs AG
- both sides respond to host commands reliably at `921600`
- PUART channel is available for a clean bridge protocol start

Failure criteria:

- missing identity or version response
- unstable HCI port open or baud mismatch
- debug text leaking into the future PUART bridge channel
- uncertain COM-port-to-board mapping

### Phase 0 Manual Test Procedure

Run this procedure one board at a time first, then with both connected.

#### HF board bring-up

1. Connect only the HF board to the PC
2. Open the HF HCI port at `921600`
3. Watch for startup events
4. Issue `GET_VERSION`
5. Issue `READ_LOCAL_BDA`

Expected pass result:

- HCI port opens reliably
- `DEVICE_STARTED` is received
- version event is received
- identity event reports `NavTool-PhoneConnect`
- local BDA event is received

Fail result means one of:

- wrong COM port
- wrong baud
- board not flashed with expected image
- HCI path broken or held by another app

#### AG board bring-up

1. Disconnect HF or leave it idle and connect only the AG board
2. Open the AG HCI port at `921600`
3. Watch for startup events
4. Issue `GET_VERSION`
5. Issue `READ_LOCAL_BDA`

Expected pass result:

- HCI port opens reliably
- `DEVICE_STARTED` is received
- version event is received
- identity event reports `NavTool-CarConnect`
- local BDA event is received

Fail result means one of:

- wrong COM port
- wrong baud
- board not flashed with expected image
- HCI path broken or held by another app

#### Dual-board mapping check

1. Connect both boards
2. Open both HCI ports
3. Confirm the identities stay stable:
   - HF port always reports `NavTool-PhoneConnect`
   - AG port always reports `NavTool-CarConnect`
4. Record the COM mapping in lab notes

Expected pass result:

- there is no ambiguity about which board is on which port
- both ports can be opened independently at `921600`

#### Minimal PUART sanity check

This is not full bridge logic yet.

Goal:

- confirm PUART can carry one clean lab message without HCI/debug contamination

Minimal recommended test:

- add one one-way boot hello or one manual test string later in firmware, such as:
  - `BR1,HELLO,HF`
  - `BR1,HELLO,AG`

Expected pass result:

- one clean line arrives on the peer side
- no extra debug trace appears on the PUART bridge channel

#### Phase 0 completion decision

Phase 0 is complete when:

- HF HCI identification is stable
- AG HCI identification is stable
- COM-port ownership is known
- both sides answer HCI version/BDA queries reliably
- the team is confident PUART is available as a clean future bridge channel

### Phase 1: Bridge Transport Skeleton

Goals:

- reserve `PUART` for bridge traffic only
- keep debug/trace on the host-side HCI/WICED debug path
- add `bridge_protocol.*`
- add `bridge_puart.*`
- initialize PUART cleanly on both boards
- implement line rx buffering and line tx helpers
- add `HELLO,HF` / `HELLO,AG`

Success criteria:

- no firmware debug text appears on the PUART bridge pins
- boards exchange hello messages reliably after boot
- malformed line does not crash parser
- logs clearly show tx/rx bridge lines

Recommended steps:

1. Phase 1.1: remove PUART debug routing and reserve PUART for the bridge
2. Phase 1.2: add `bridge_protocol.*` and `bridge_puart.*` skeleton on both boards
3. Phase 1.3: implement and verify `BR1,HELLO,<role>` exchange

Current status:

- Phase 1.1 completed: both UART firmware repos now keep debug on the host-side path instead of forcing `PUART`
- Phase 1.2 completed: bridge protocol and PUART skeleton files are added on HF and AG, with PUART initialization moved into `hci_control_post_init()`
- Phase 1.3 paused: `HELLO` transmit logic remains in source, but active bridge startup hooks were removed again until HF HCI bring-up is stable and exposed PUART routing is verified on the devkits

### Phase 2: Inbound Call Path

Goals:

- HF maps real incoming phone call callback to `INCOMING`
- HF maps caller ID to `CID`
- AG consumes `INCOMING` and starts synthesized ring behavior immediately
- AG consumes `CID` and updates caller ID state if available

Success criteria:

- real phone incoming call causes car-facing AG behavior
- caller ID may arrive later without blocking ring start

### Phase 3: Call Control Return Path

Goals:

- AG detects car-originated answer / reject / hangup actions
- AG sends `ANSWER`, `REJECT`, `HANGUP` over PUART
- HF executes corresponding phone-side HFP operations

Success criteria:

- answering on the car answers on the phone side through HF
- hangup from either side ends call cleanly

### Phase 4: Active Call and Audio State

Goals:

- HF sends `ACTIVE` when call is truly active
- HF sends `ENDED` when call ends
- local audio callbacks map to `AUDIO_OPEN` / `AUDIO_CLOSE`
- AG uses these to keep car-facing behavior aligned with real phone state

Success criteria:

- active and ended state stay synchronized
- audio state is reflected correctly without trying to route audio over UART

### Phase 5: AVRCP Media Controls

Goals:

- AG detects car-originated media controls
- AG sends semantic media commands over PUART
- HF maps them to local AVRCP operations toward the phone
- HF reports playback-state changes back to AG

Success criteria:

- car play/pause/next/prev actions reach the phone side correctly
- playback state remains aligned between phone-facing and car-facing sides

### Phase 6: AVRCP Metadata

Goals:

- HF observes local metadata updates from the phone side
- HF sends bounded metadata messages over PUART
- AG updates car-facing metadata presentation

Success criteria:

- title / artist / playback state appear correctly on the car side
- metadata truncation is deterministic and safe
- metadata update rate does not destabilize the PUART channel

### Phase 7: Robustness

Goals:

- duplicate message tolerance
- invalid-state guards
- PUART reconnect / restart behavior
- optional hello/state resync after reboot

Success criteria:

- transient board reset does not leave system permanently confused
- duplicate `INCOMING` or `ENDED` lines do not break call logic

### Phase 8: UI / Lab Tooling

Goals:

- keep host UI focused on HCI inspection and testing
- show board identity, BDA, version, and trace
- optionally add test actions for lab-only bridge injection
- do not move bridge policy into UI

Success criteria:

- UI helps observe and test the system
- system still works conceptually without UI in the path

## Proposed File Layout

Names can change, but this split is a good starting point:

- `src/bridge_protocol.h`
- `src/bridge_protocol.c`
- `src/bridge_puart.h`
- `src/bridge_puart.c`
- `src/bridge_hf_side.h`
- `src/bridge_hf_side.c`
- `src/bridge_ag_side.h`
- `src/bridge_ag_side.c`
- `src/bridge_avrcp.h`
- `src/bridge_avrcp.c`

Suggested ownership:

- `bridge_protocol.*`
  - enums
  - parse/encode helpers
  - message validation

- `bridge_puart.*`
  - PUART init
  - rx accumulation
  - tx send line
  - callback / ISR hookup

- `bridge_hf_side.*`
  - local HFP HF callbacks to bridge messages
  - bridge commands back into phone-side HFP actions

- `bridge_ag_side.*`
  - bridge events into AG-side synthetic behavior
  - car-side actions back into bridge commands

- `bridge_avrcp.*`
  - media command/message mapping
  - metadata encode/truncate helpers
  - playback-state normalization

## Important Design Limits for v1

To keep the first milestone achievable:

- no raw HFP AT tunneling as the main bridge mechanism
- no raw Bluetooth event mirroring
- no raw AVRCP packet tunneling
- no audio over UART
- no multi-call support in v1
- no call waiting / hold / swap in v1
- no album art or large binary metadata over PUART in v1

## Open Questions for Future Work

These decisions should be made early:

1. Outgoing call support
   - does the car need to initiate dialing through AG -> HF -> phone?

2. Call waiting / multi-call
   - likely out of scope for v1

3. Audio ownership
   - exact rule for when AG should synthesize audio-open behavior versus waiting for true local callback

4. Reboot recovery
   - whether `HELLO` alone is enough or if state resync is required

5. Lab control strategy
   - which host-side HCI commands remain useful for diagnostics without becoming part of bridge policy

6. AVRCP role mapping
   - exact controller/target role pairing on HF side and AG side for the intended phone/car combinations

7. Metadata policy
   - which metadata fields are mandatory
   - max payload size and truncation suffix rules

## Implementation Ideas

Useful early ideas:

- add a `bridge_state_t` on each side to reject impossible transitions
- add a small per-board text log for bridge tx/rx lines
- keep bridge parser independent from HCI code
- expose a simple "bridge status" HCI command later if needed for diagnostics
- keep protocol human-readable until real throughput or robustness data says otherwise
- keep HFP and AVRCP as separate bridge domains sharing one framing layer
- include a profile field in future framing if message volume grows, for example `BR1,HFP,...` and `BR1,AVRCP,...`
- while the boards are not physically cross-wired, use the UI PUART Trace tab as the software patch cable:
  - Phone PUART `BR1,...` lines relay to Car PUART
  - Car PUART `BR1,...` lines relay to Phone PUART
  - manual `Peer Hello` buttons send `BR1,HELLO,AG` into Phone PUART and `BR1,HELLO,HF` into Car PUART
- current lab rule: the UI is the active PUART relay until explicitly switching to physical crosswire

## Commit Naming Convention

Use phase-numbered commit messages so the project history stays easy to follow.

Recommended format:

`Phase X.Y: short action description`

Examples:

- `Phase 0.1: restore baseline HCI UI communication`
- `Phase 0.2: verify HF and AG identity over HCI`
- `Phase 1.1: add PUART bridge transport skeleton`
- `Phase 1.2: implement HF and AG hello exchange`
- `Phase 2.1: forward incoming call event from HF to AG`
- `Phase 3.1: send answer and hangup commands from AG to HF`

Guidelines:

- one logical result per commit
- include the phase and sub-step when possible
- keep the title short and action-oriented
- if a phase has multiple implementation steps, use `X.Y`
- if useful, add validation notes in the commit body

Preferred commit body structure when needed:

- what changed
- why it changed
- how it was validated

## Local References

- `C:\\BT_Projects\\headset_hfp_uart_hf\\reference_hfp.md`
- `C:\\BT_Projects\\headset_hfp_uart_hf\\AGENT.md`
- `C:\\BT_Projects\\examples\\mtb-example-btsdk-audio-watch\\hci_control.c`
- `C:\\BT_Projects\\headset_hfp_uart_hf\\mtb-example-btsdk-audio-headset-standalone\\hci_control.c`

## Official References

- AIROC BTSDK docs index: https://infineon.github.io/btsdk-docs/BT-SDK/index.html
- AIROC HCI UART Control Protocol: https://infineon.github.io/btsdk-docs/BT-SDK/AIROC-HCI-Control-Protocol.pdf
- CYW20706 `hci_control_api.h` reference: https://infineon.github.io/btsdk-docs/BT-SDK/20706-A2_Bluetooth/API/hci__control__api_8h.html
- CYW20706 PUART driver docs: https://infineon.github.io/btsdk-docs/BT-SDK/20706-A2_Bluetooth/API/group___p_u_a_r_t_driver.html
- Trace utilities docs: https://infineon.github.io/btsdk-docs/BT-SDK/20706-A2_Bluetooth/API/group__wiced__utils.html
- Transport docs: https://infineon.github.io/btsdk-docs/BT-SDK/20706-A2_Bluetooth/API/group___transport.html
- Audio utilities docs: https://infineon.github.io/btsdk-docs/BT-SDK/20706-A2_Bluetooth/API/group__wicedbt__audio__utils.html
