# HFP HF Context Reference (`headset_hfp_hf`)

## Scope analyzed
- Source root: `C:\BT_Projects\test\headset_hfp_hf`
- Primary app root: `C:\BT_Projects\test\headset_hfp_hf\mtb-example-btsdk-audio-headset-standalone`
- Focus: runtime behavior for HFP HF role, host-command plumbing, reconnect/bond logic, and bridge-specific customizations.

## Top-level project map
- `AGENT.md`, `project_status.md`, `codex-handoff.md`
  - Local operating notes and session continuity docs.
- `mtb-example-btsdk-audio-headset-standalone/`
  - Main embedded firmware app (BTSDK headset/watch-derived sample customized for bridge use).
- `mtb_shared/`
  - Shared BTSDK dependencies and host reference artifacts (includes `hci_control_api.h` and client-control host code).

## Build-time role and defaults
From `makefile`:
- Default target: `CYBT-343026-EVAL`
- Default role in this repo:
  - `HFP_HF_INCLUDED=1`
  - `HFP_AG_INCLUDED=0`
- Device name configured in runtime config: `NavTool-PhoneConnect` (from `wiced_app_cfg.c`)
- Deterministic local address default when not provided:
  - HF default: `20706A20D341`
  - AG default: `20706A20D340`
- Other enabled features by default:
  - AVRCP CT/TG enabled
  - A2DP path enabled in this sample framework
  - LE/ANCS/AMS enabled
  - PAN disabled

Note: The app still contains both AG and HF support codepaths in source, but compile-time flags select active behavior.

## Core runtime entry and initialization flow
### 1) Boot entry
- `wiced_app.c` -> `APPLICATION_START()`
  - Calls `hci_control_init()`
  - Initializes BT stack (`app_stack_init`)
  - Initializes audio buffers (`wiced_audio_buffer_initialize`)
  - Initializes LE handlers if enabled

### 2) BTM enabled event
- `btm_event_handler()` -> `BTM_ENABLED_EVT` -> `btm_enabled_event_handler()`
  - Writes EIR (`write_eir`)
  - Loads SDP DB (`wiced_bt_sdp_db_init`)
  - Calls `hci_control_post_init()`
  - Applies role-specific local address adjustment (`apply_role_specific_local_address`)
  - Enables pairing visibility only when no bonded peer (`enable_pairing_visibility_when_unbonded`)
  - Starts delayed bond dump timer
  - Starts staged auto-reconnect timer chain

### 3) Post-init profile setup
- `hci_control.c` -> `hci_control_post_init()`
  - Initializes LE control
  - Initializes A2DP audio app
  - Initializes AVRCP controller/target based on role
  - Initializes HFP module (`hci_control_hf_init()` when HF role compiled)
  - Sets default BR/EDR visibility hidden and non-connectable until host enables pairing
  - Sends `HCI_CONTROL_EVENT_DEVICE_STARTED` in selected paths

## HCI command routing architecture
Main dispatcher:
- `hci_control_proc_rx_cmd()` in `hci_control.c`
- Routes by high-byte group ID to handlers:
  - Device, LE/GATT, Audio, AVRCP CT/TG, AG, HF, PAN, Misc, Test

HF-specific route:
- Group `HCI_CONTROL_GROUP_HF (0x03)` -> `hci_control_hf_handle_command()`

Protocol constants:
- From `mtb_shared/.../include/hci_control_api.h`
- HF commands/events/AT command IDs and misc bridge identity event are defined there.

## HFP HF module behavior (`hci_control_hfp_hf.c`)
### Context and state
- Main state struct: `bluetooth_hfp_context_t handsfree_ctxt_data`
  - Tracks peer address, call/callsetup/callheld, SCO index/state, RFCOMM handle, volumes

### HF initialization
- `hci_control_hf_init()`:
  - Initializes timer for SCO fallback behavior
  - Calls `handsfree_hfp_init()`, which sets feature mask and calls `wiced_bt_hfp_hf_init(...)`

### Connection events
- `handsfree_connection_event_handler()`
  - On connected:
    - Emits HF OPEN event to host
    - Emits selected profile type event (HFP/HSP)
    - Creates SCO as acceptor
    - Continues staged auto-reconnect flow to AVRCP
  - On disconnected:
    - Removes SCO if needed
    - Emits HF CLOSE event
    - If disconnect was local host-requested, suppresses auto-reconnect
    - Else schedules full reconnect to remembered peer

### AT command handling from host
- `hci_control_hf_at_command()` maps host AT opcodes to profile APIs:
  - Volume updates, answer/hangup/dial, CLCC/CNUM/CIND, CHLD, BVRA, BTRH, BIA/BIEV, DTMF, etc.
- `hci_control_hf_send_at_cmd()` builds and sends raw `AT...` lines to profile stack.

### Custom extension: raw AT passthrough
- Additional command defined locally:
  - `HCI_CONTROL_HF_COMMAND_SEND_RAW_AT = ((HCI_CONTROL_GROUP_HF << 8) | 0x40)`
- Implemented in `hci_control_hf_handle_command()`:
  - Payload format: `[handle_lo, handle_hi, ascii_at_command...]`
  - Sends directly via `wiced_bt_hfp_hf_send_at_cmd(handle, string)`
- Purpose: allows host bridge/UI to forward arbitrary car-side AT strings to phone-facing HF link.

### HF event forwarding to host
- `handsfree_event_callback()` transforms profile events into HCI transport events:
  - Connection/service indicators
  - `RING`, `OK`, `ERROR`, `CMEE`
  - `CLIP`, `CLCC`, `CNUM`, `BIND`
  - Volume and codec selection events
  - `+CIEV` style indicator updates

### SCO/audio management
- `hci_control_hf_sco_management_callback()`
  - Handles SCO connected/disconnected/request/change
  - Starts/stops AudioManager stream on supported targets
  - Emits HF audio open/close events to host
  - Recreates acceptor SCO after disconnect for subsequent calls

## Auto-reconnect and bond recovery design (`wiced_app.c`)
Staged reconnect enum:
- `HF_AUTORECONNECT_HFP`
- `HF_AUTORECONNECT_AVRCP`
- `HF_AUTORECONNECT_A2DP`

Flow:
1. On boot, find last bonded peer and schedule reconnect.
2. Stage 1: connect HFP
3. Stage 2: connect AVRCP
4. Stage 3: initiate A2DP SDP/connect (HF side primes I2S route before A2DP connect)

Continuation hooks:
- `hf_autoreconnect_restart_full(...)`
- `hf_autoreconnect_continue_from_hfp(...)`
- `hf_autoreconnect_continue_from_avrcp(...)`

Failure handling:
- If stage result is not success/pending/busy/already-connected, retries full reconnect after delay.

Stale bond recovery:
- Triggered on pairing or BR/EDR encryption failure paths.
- Deletes stored key material for peer and forces pairable/discoverable/connectable to recover.

Unbonded startup behavior:
- If no bonded peer found, firmware auto-enables pairable/discoverable/connectable for first-time pairing.
- If bonded peer exists, keeps hidden default policy unless host changes visibility.

## A2DP/AVRCP interactions relevant to HF bridge
`hci_control_audio.c`:
- Implements A2DP signaling, stream start/stop, codec negotiation, route selection.
- Handles `HCI_CONTROL_AUDIO_DATA_FORMAT` to set audio format/route (`I2S`/other).
- On A2DP disconnect, may continue reconnect sequencing (handoff with HF/AVRCP reconnect logic).
- HF auto-reconnect stage uses `av_app_initiate_sdp(...)` and on HF path sets route command for I2S first.

## Misc bridge-specific host identity
`hci_control_misc.c`:
- On `HCI_CONTROL_MISC_COMMAND_GET_VERSION`, firmware sends:
  - standard version event
  - custom bridge identity event `HCI_CONTROL_MISC_EVENT_BRIDGE_IDENTITY`
- Identity string in HF build: `"NavTool-PhoneConnect"`
- AG build string (for counterpart project) is `"NavTool-CarConnect"`

## Key files for day-to-day changes
- Build flags/profile defaults:
  - `mtb-example-btsdk-audio-headset-standalone/makefile`
- Stack/device/SDP config and name:
  - `mtb-example-btsdk-audio-headset-standalone/wiced_app_cfg.c`
- App bootstrap, BTM events, reconnect/bond logic:
  - `mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
  - `mtb-example-btsdk-audio-headset-standalone/wiced_app.h`
- Host protocol dispatch and role init:
  - `mtb-example-btsdk-audio-headset-standalone/hci_control.c`
  - `mtb-example-btsdk-audio-headset-standalone/hci_control.h`
- HF profile logic and custom raw AT command:
  - `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_hf.c`
  - `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_hf.h`
- Bridge identity event:
  - `mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
- HCI protocol opcode definitions:
  - `mtb_shared/wiced_btsdk/tools/btsdk-host-apps-bt-ble/release-v4.9.3/include/hci_control_api.h`

## Practical debugging checkpoints
- Confirm active role path:
  - Build macros in `makefile` (`HFP_HF_INCLUDED`/`HFP_AG_INCLUDED`)
  - Runtime `hfp_profile_role` in traces
- Confirm identity and host feature discovery:
  - Trigger misc version command and verify bridge identity event
- Confirm reconnect chain progress:
  - Trace tags `[AUTO_HF]`/`[AUTO_AG]` and stage transitions
- Confirm stale-bond handling:
  - Look for `stale bond recovery` traces and NVRAM key deletion
- Confirm raw AT passthrough:
  - Send opcode `0x0340` with RFCOMM handle + ASCII AT text and inspect phone-side behavior

## Notes on duplicate component folders
- `COMPONENT_btstack_v1/` and `COMPONENT_btstack_v3/` both exist with app variants.
- Active one is selected by BSP/component settings at build time.
- Most custom bridge behavior in this project is in top-level app sources (`wiced_app*.c`, `hci_control*.c`), not only component-specific folders.

## HCI baudrate tracking and dependencies
### Current effective HCI transport baud for this project
- For current default target `CYBT-343026-EVAL`, app `makefile` explicitly adds:
  - `-DWICED_HCI_BAUDRATE=921600`
  - and sets `HCI_UART_DEFAULT_BAUD_3M=0`
- Both transport implementations (`COMPONENT_btstack_v1/app.c` and `COMPONENT_btstack_v3/app.c`) use:
  - `APP_TRANSPORT_HCI_BAUD = WICED_HCI_BAUDRATE` if defined, else `HCI_UART_DEFAULT_BAUD`.
- Result: this repo currently runs HCI transport at `921600` on `CYBT-343026-EVAL`.

### Fallback path if `WICED_HCI_BAUDRATE` is not defined
- BSP defaults are in:
  - `mtb_shared/wiced_btsdk/dev-kit/bsp/TARGET_CYBT-343026-EVAL/release-v4.7.0/CYBT-343026-EVAL.mk`
  - `mtb_shared/wiced_btsdk/dev-kit/bsp/TARGET_CYBT-343026-EVAL/release-v4.7.0/wiced_platform.h`
- For this BSP, default is `HCI_UART_DEFAULT_BAUD=115200` unless `HCI_UART_DEFAULT_BAUD_3M=1`.

### Important distinction: debug trace baud is separate
- `wiced_app.c` configures PUART debug trace at `921600` (`wiced_hal_puart_configuration(921600,...)`).
- This does not set HCI transport baud for host HCI control.
- Changing HCI transport baud does not automatically change debug-trace UART behavior.

### Project dependencies to review if HCI baudrate changes
1. Firmware transport define
- `mtb-example-btsdk-audio-headset-standalone/makefile`
- Keep `WICED_HCI_BAUDRATE` aligned with host-side serial setting.

2. Host ClientControl defaults (included in repo as shared tools)
- `mtb_shared/.../client_control/Windows/clientcontrol.ini` default `Baud=921600`
- `mtb_shared/.../client_control/source/device_manager.cpp` default fallback `921600`
- Supported baud list in ClientControl includes `115200`, `921600`, `921600` (and `4000000` except macOS).

3. Legacy Python audio client scripts (reference tooling)
- `audio-lib-pro/utils/audio_client/play_headset.py` hardcodes `921600`
- `audio-lib-pro/utils/audio_client/play_headset_no_pyaudio.py` hardcodes `921600`
- `audio-lib-pro/utils/audio_client/fw_dl.py` starts at `115200` then switches to `921600`
- If these scripts are used, their configured baud must match firmware transport baud.

4. Documentation/operator guidance
- `README.md` contains mixed baud guidance (generic 3M/115200 statements).
- If project baud changes, update README notes to avoid operator mismatch.

### Practical change checklist
- Change firmware baud define in app `makefile`.
- Rebuild/flash firmware.
- Update host tool baud (ClientControl or Python script) to same rate.
- Verify `DEVICE_STARTED` event reception over HCI at new baud.
- Validate major command paths: misc version, HF connect, AT command, and reconnect traces.

## Working vs non-working identity investigation (2026-04-23)
### Comparison scope
- Working reference: `C:\BT_Projects\test\headset_hfp_hf`
- Non-working project: `C:\BT_Projects\headset_hfp_uart_hf`
- Focus: why board does not return bridge identity on host connect attempt.

### What matched (no firmware-side identity regression found)
- App sources under `mtb-example-btsdk-audio-headset-standalone` are effectively the same for identity path:
  - `hci_control_misc.c` handles `HCI_CONTROL_MISC_COMMAND_GET_VERSION` and emits `HCI_CONTROL_MISC_EVENT_BRIDGE_IDENTITY`.
  - Identity string is `NavTool-PhoneConnect` for HF build.
- Transport and role compile-time settings match in both builds:
  - `-DWICED_APP_HFP_HF_INCLUDED`
  - `-DWICED_HCI_TRANSPORT=1` (UART)
  - `-DWICED_HCI_BAUDRATE=921600` for `CYBT-343026-EVAL`.
- `mtb_shared` C/H/MK/TXT/XML/JSON content matched in this comparison.

### Critical runtime mismatch to watch
- Firmware is built for HCI UART `921600` on `CYBT-343026-EVAL`.
- ClientControl default config (`clientcontrol.ini`) is `Baud=921600`.
- If host connects at `921600` while firmware is `921600`, board will not decode host commands, so no version/identity event comes back.

### Additional high-probability causes
1. COM port is wrong or already open by another app.
- Evidence: `det_and_id.log` shows repeated `Could not establish transport connection: Failed to open the specified port!`.

2. Flow-control mismatch.
- ClientControl defaults `FlowControl=true`; if host wiring/platform does not match RTS/CTS expectations, transport can appear dead.

3. Board image mismatch at test time.
- Both `download.log` files show successful flashing, but always verify the currently attached board was flashed from the intended workspace right before connect test.

### Fast verification sequence
1. Set host port to the actual board COM port.
2. Set host baud explicitly to `921600`.
3. Disable/adjust flow control if hardware wiring does not support RTS/CTS.
4. Reconnect and issue `GET_VERSION` command.
5. Confirm both events return:
   - version event
   - `HCI_CONTROL_MISC_EVENT_BRIDGE_IDENTITY` with `NavTool-PhoneConnect`.
