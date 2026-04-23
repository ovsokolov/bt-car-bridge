# HFP Bridge Master Implementation Plan (UI + AG FW + HF FW)

## 1) Objective

Implement end-to-end HFP bridge using `HFPB1` wire protocol with these hard boundaries:

1. UI is transport-only relay (no HFP decision logic).
2. AG firmware owns car-facing policy and synthetic call behavior.
3. HF firmware owns phone-facing adaptation and raw HFP line bridging.

Reference protocol spec:
- `C:\BT_Projects\control_uart_ui\docs\hfp_bridge_wire_format_v1.md`

## 2) Architecture Contract

- Canonical wire protocol: `HFPB1` framed text line with CRC and ACK/NAK.
- HFP signaling payload: raw HFP text line in payload JSON `line` field.
- Transport control frames: `SYN`, `ACK`, `NAK`, `RST`, `HBT`, optional `SNP`.
- UI forwards full frame lines unchanged in both directions.
- Firmware owns retry, dedupe, queue/replay, reconnect policy.

## 3) Phase Plan (Single Execution Flow)

## Phase 0 - Protocol Lock and Test Vectors

Goal:
- freeze `HFPB1` semantics before code divergence.

Work:
1. Finalize field constraints and reserved bits in protocol doc.
2. Add CRC16 test vectors and at least 10 golden frame examples.
3. Define critical vs non-critical HFP line policy table.

Exit criteria:
- AG and HF teams both sign off protocol and vectors.
- no further format changes without version bump.

## Phase 1 - UI Transport-Only Refactor

Goal:
- remove all profile/HFP logic from host path.

Work:
1. Remove packet semantic bridge code from UI.
2. Implement raw line relay thread paths `phone->car` and `car->phone`.
3. Keep only transport observability (timestamps, side tags, counters, errors).

Exit criteria:
- UI does not parse `line` payload semantics.
- UI can run as passive relay for protocol integration tests.

## Phase 2 - Common FW Transport Core (Both Repos)

Goal:
- establish reliable `HFPB1` stack on each board.

Work:
1. Implement encoder/decoder, CRC16, sequence manager.
2. Implement ACK/NAK, retry with backoff, duplicate suppression.
3. Implement critical/non-critical queues and replay flags.
4. Implement session handshake (`SYN`) and reset (`RST`).

Exit criteria:
- board-level loopback can send/receive/ack/retry/replay deterministically.

## Phase 3 - AG Firmware Policy Engine

Goal:
- AG becomes single policy authority for car behavior.

Work:
1. Parse inbound raw HFP lines and classify by policy.
2. Apply indicator/index mapping and synthetic events as needed.
3. Drive AG local stack with deterministic call-state transitions.
4. Produce outbound raw HFP responses/events for HF side.

Exit criteria:
- AG handles call-critical bridge behavior with no host decision logic.

## Phase 4 - HF Firmware Adapter Layer

Goal:
- HF side normalizes phone-facing HFP behavior into bridge frames.

Work:
1. Convert local HF events and AT lines to `HFPB1` `T=HFP`.
2. Consume AG-originated `HFP` lines and apply to local HF stack path.
3. Align reconnection/session reset behavior with AG side.
4. Ensure handle/session safety around disconnect/reconnect.

Exit criteria:
- HF can bridge bi-directionally with AG via `HFPB1` only.

## Phase 5 - End-to-End Integration via UI Relay

Goal:
- prove system behavior on real phone + car with passive UI relay.

Work:
1. Validate incoming call, answer, reject, hangup.
2. Validate call waiting / held / CLCC / CIEV consistency.
3. Validate transient link drop with replay and recovery.
4. Validate queue pressure and duplicate frame behavior.

Exit criteria:
- critical call-control flows are stable and repeatable.

## Phase 6 - Hardening and Direct RX/TX Readiness

Goal:
- preserve same protocol when moving off host relay.

Work:
1. Isolate transport binding in firmware (host-uart vs direct-uart).
2. Run soak tests: reconnect storms, burst indicators, timeout paths.
3. Produce release checklist and conformance logs.

Exit criteria:
- no protocol changes needed to migrate to direct board-to-board UART.

## 4) Repo-by-Repo Task Checklist (File-Level TODO)

## 4.1 `control_uart_ui` checklist

Target repo:
- `C:\BT_Projects\control_uart_ui`

### `src/control_ui_app/ui.py`
- [ ] Remove `_handle_bridge_packet()` semantic forwarding logic.
- [ ] Remove `_parse_value_payload()` and `_parse_ag_at_payload()` semantic dependencies from relay path.
- [ ] Add passive relay status widgets/counters only (`rx_lines`, `tx_lines`, `crc_fail`, `timeouts`).
- [ ] Ensure trace shows raw frame line + direction tag (`HF->AG`, `AG->HF`).

### `src/control_ui_app/session.py`
- [ ] Add raw line send API (transport-level), separate from HCI profile helpers.
- [ ] Add per-side relay callback path that surfaces full raw line bytes/strings.
- [ ] Keep port lifecycle and reconnection support; do not add HFP semantics.
- [ ] Keep thread-safe bounded transport buffer for relay.

### `src/control_ui_app/hci.py`
- [ ] Mark current HCI decode helpers as non-relay path (legacy/diagnostic only).
- [ ] Add minimal helper for raw line formatting if needed by UI log pane.
- [ ] Ensure no protocol-level policy mapping is introduced here.

### `src/control_ui_app/models.py`
- [ ] Add passive relay metrics fields (line counters, relay errors, last relay status).
- [ ] Remove now-unused bridge semantic state fields if no longer needed by UI.

### `main.py`
- [ ] Keep startup unchanged, ensure app launches in passive relay mode by default.

### `docs/`
- [ ] Keep [hfp_bridge_wire_format_v1.md](C:\BT_Projects\control_uart_ui\docs\hfp_bridge_wire_format_v1.md) as protocol source.
- [ ] Add `docs/hfp_bridge_conformance_ui.md` with relay-only acceptance checks.

## 4.2 `headset_hfp_uart_ag` checklist

Target repo:
- `C:\BT_Projects\headset_hfp_uart_ag`

### `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.c`
- [ ] Introduce `HFPB1` frame RX parser and TX encoder integration points.
- [ ] Add transport state machine (`sid`, `seq`, retry, dedupe, queue).
- [ ] Implement raw HFP `line` ingress policy classification.
- [ ] Centralize mapping/synthetic logic for `RING`, `+CLIP`, `+CLCC`, `+CIEV`, `OK`, `ERROR`.
- [ ] Add deterministic critical/non-critical queue handling and replay.
- [ ] Add clear trace tags for `ACK/NAK`, retry, replay, overflow, reset.

### `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_ag.h`
- [ ] Add public declarations for bridge transport/policy entry points.
- [ ] Add constants for queue limits, retry timings, and policy flags.

### `mtb-example-btsdk-audio-headset-standalone/hci_control.c`
- [ ] Route UART-bridge command group/event path into AG bridge transport handlers.
- [ ] Ensure command dispatcher supports session control frames (`SYN/RST/HBT`).

### `mtb-example-btsdk-audio-headset-standalone/hci_control_misc.c`
- [ ] Expose capability/version response entries relevant to `HFPB1`.
- [ ] Add optional diagnostics counters exposure for host view.

### `mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
- [ ] Hook reconnect events into bridge session reset flow.
- [ ] Ensure startup path triggers clean transport session initialization.

### `mtb_shared/.../include/hci_control_api.h` (shared copy used by repo)
- [ ] Add/align command/event opcodes for raw bridge frame transport if required.
- [ ] Keep opcode compatibility with HF repo in lockstep.

### `docs/` (new in AG repo recommended)
- [ ] Add `docs/hfpb1_ag_policy_matrix.md` mapping inbound lines to AG actions.

## 4.3 `headset_hfp_uart_hf` checklist

Target repo:
- `C:\BT_Projects\headset_hfp_uart_hf`

### `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_hf.c`
- [ ] Integrate `HFPB1` RX/TX transport core (`sid`, `seq`, crc, ack/nak, retry).
- [ ] Encode local HF events/AT lines to `T=HFP` payload JSON `line`.
- [ ] Decode inbound AG `T=HFP` lines and route to local HF stack APIs.
- [ ] Harden raw AT apply path for reconnect edge cases and invalid session state.
- [ ] Add replay-safe idempotency around call-critical actions.

### `mtb-example-btsdk-audio-headset-standalone/hci_control_hfp_hf.h`
- [ ] Add declarations/config for bridge transport state and limits.

### `mtb-example-btsdk-audio-headset-standalone/hci_control.c`
- [ ] Add command/event routing for bridge transport frames and control types.
- [ ] Ensure handlers are side-effect safe on duplicate/retry frames.

### `mtb-example-btsdk-audio-headset-standalone/wiced_app.c`
- [ ] Tie HF reconnect events to `SYN` re-handshake and queue replay trigger.
- [ ] Clear transient session state on link loss before re-open.

### `mtb_shared/.../include/hci_control_api.h` (shared copy used by repo)
- [ ] Mirror AG-side opcode changes exactly.
- [ ] Keep transport command/event contracts byte-identical across both repos.

### `docs/` (new in HF repo recommended)
- [ ] Add `docs/hfpb1_hf_adapter_rules.md` for raw line normalization rules.

## 5) Cross-Repo Milestones and Ownership

1. Milestone A: protocol and vectors frozen.
2. Milestone B: UI passive relay merged.
3. Milestone C: AG/HF transport cores merged.
4. Milestone D: AG policy + HF adapter integrated.
5. Milestone E: hardware validation matrix passes.

Recommended ownership:
- UI passive relay: host-app owner.
- Transport core parity: one AG + one HF owner co-reviewing each change.
- Policy behavior: AG owner.
- Phone adaptation behavior: HF owner.

## 6) Validation Matrix (Must Pass)

1. Incoming call to phone -> ring/clip/clcc appears on car side.
2. Car answer -> phone call active.
3. Car hangup -> phone call terminated.
4. Call waiting/held transitions remain coherent.
5. Link drop mid-call does not lose critical commands after reconnect.
6. Duplicate and retry frames do not cause duplicate call actions.
7. Queue overflow behavior follows documented critical/non-critical policy.

## 7) Definition of Done

1. UI is strictly pass-through and observability only.
2. AG firmware contains all car-facing bridge policy logic.
3. HF firmware contains all phone-facing adaptation logic.
4. `HFPB1` protocol is consistently implemented on both firmware sides.
5. End-to-end hardware tests pass with deterministic logs and recovery behavior.
