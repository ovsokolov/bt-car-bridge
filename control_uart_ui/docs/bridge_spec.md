# NavTool Dual-Devkit Bridge Specification

## Purpose

This project creates a dual-devkit Bluetooth bridge in which:

- `NavTool-PhoneConnect` connects to a phone
- `NavTool-CarConnect` connects to a car head unit
- a Windows host app coordinates both devkits over USB serial
- audio is routed directly between devkits over dedicated hardware pins, not over UART

The bridge goal is to make the phone and the car behave as though they are
directly connected, while the host app translates and supervises the control
plane between the two embedded endpoints.

## Scope

Phase 1 scope:

- dual serial-port host UI
- explicit devkit identity reporting
- remote discovery and pairing workflows for both devkits
- HFP, A2DP, and AVRCP session visibility
- bridge-oriented logging with source attribution
- command hooks needed for test bring-up

Later phases:

- HFP signaling bridge
- AVRCP command and metadata bridge
- A2DP session coordination
- direct devkit-to-devkit audio path coordination
- recovery and automation flows

## System Roles

### Protocol Role Matrix

| Link | Side A | Side B |
|---|---|---|
| Phone HFP | Phone = AG | PhoneConnect = HF |
| Car HFP | CarConnect = AG | Car = HF |
| Phone A2DP | Phone = Source | PhoneConnect = Sink |
| Car A2DP | CarConnect = Source | Car = Sink |
| Phone AVRCP | Phone = Target | PhoneConnect = controller-facing proxy |
| Car AVRCP | CarConnect = target-facing proxy | Car = Controller |

### System Component Matrix

| Function | Phone | PhoneConnect | Host UI | CarConnect | Car |
|---|---|---|---|---|---|
| HFP role | AG | HF | control/translation | AG | HF |
| A2DP role | Source | Sink | session coordination | Source | Sink |
| AVRCP role | Target | proxy | translation | proxy | Controller |
| Serial control | none | USB serial | dual-port master | USB serial | none |
| Audio path | BT air link | hardware link endpoint | no UART audio | hardware link endpoint | BT air link |

## Behavioral Flow Matrix

| Feature | Initiator | Bridge Action | Receiver |
|---|---|---|---|
| HFP answer/hangup/dial | Car or Phone | map HFP command/state | opposite side |
| HFP indicators | Phone | map to AG-facing state | Car |
| HFP SCO intent | either side | coordinate audio open/close | opposite devkit |
| A2DP start/stop | Phone | coordinate media session state | Car |
| AVRCP commands | Car | forward/map to phone side | Phone |
| AVRCP playback status | Phone | forward/map to car side | Car |
| AVRCP metadata | Phone | forward/map to car side | Car |
| Absolute volume | policy driven | optional mapping | opposite side |

## Host UI Requirements

The host application shall:

- open and manage two independent USB serial connections
- label each connected devkit by explicit bridge identity, not only by COM port
- display which devkit provided each event and each log line
- support BR/EDR inquiry from each devkit independently
- show discovered remote devices for the phone-facing and car-facing side separately
- allow the operator to set pairable and discoverable/connectable state per devkit
- allow selecting a discovered device and invoking profile connect/disconnect actions
- show local BD_ADDR, SDK/chip version, and supported feature groups for each devkit
- collect a unified bridge log in addition to per-device logs

## Firmware Support Requirements

Each devkit firmware shall:

- report a stable bridge identity string over WICED HCI misc events
- continue reporting SDK version and supported feature groups
- preserve existing profile control interfaces for HF, AG, AVRCP, and A2DP bring-up
- keep direct audio transport on hardware pins outside the UART control path

Identity strings:

- HF build: `NavTool-PhoneConnect`
- AG build: `NavTool-CarConnect`

## Control-Plane Design

The host app owns:

- serial framing and packet parsing
- per-devkit session state
- discovery results and remote-device selection
- bridge logging
- future translation policy between phone-side and car-side events

The host app does not carry:

- SCO audio samples over UART
- A2DP media samples over UART

## Audio Design Constraints

Audio shall be transported directly between devkits over hardware pins.

The project still requires explicit definition of:

- HFP audio physical interface
- A2DP audio physical interface
- master/slave clocking
- sample rates
- mono/stereo format expectations
- session open/close coordination responsibilities

## Risks

- HFP control semantics are not a byte-for-byte relay and require translation
- AVRCP status/metadata synchronization varies by phone and car implementation
- A2DP source/sink behavior may still require timing coordination even without UART media transport
- feature mismatch between phone and car can require bridge policy decisions
- recovery behavior after disconnects must be designed explicitly

## Non-Goals For Initial Test App

- full transparent HFP signaling bridge
- complete AVRCP metadata mirroring
- A2DP media transport over UART
- autonomous recovery for all failure cases
- multi-phone or multi-car support

## Initial Host App Deliverables

1. Detect and open two serial ports.
2. Identify each devkit as `PhoneConnect` or `CarConnect`.
3. Issue `GetVersion` and display bridge identity, chip, BD_ADDR, and supported groups.
4. Start and stop inquiry independently on both sides.
5. Show discovered devices and decoded EIR names.
6. Allow pairability and visibility control.
7. Allow profile-oriented connect and disconnect commands for test bring-up.
8. Log all device-originated events with clear source tags.
