# Context Restore

## Current Setup

### 1) HF board firmware (`NavTool-PhoneConnect`)
- Project role: HFP HF.
- Responsibility: phone-facing endpoint.
- Exposes HCI/UART control interface (current working baud setup is `921600`).

### 2) AG board firmware (`NavTool-CarConnect`)
- Project role: HFP AG.
- Responsibility: car/head-unit-facing endpoint (AG side).
- Exposes HCI/UART control interface for orchestration.

### 3) Python UI (host orchestration)
- Detects board identity and assigns roles (HF vs AG).
- Performs startup control flow to initialize the bridge and bring links up.
- Coordinates control/state visibility for operator workflows.

## Bridge Behavior Summary
- HF FW and AG FW are the transport/profile endpoints.
- UI provides orchestration/control-plane actions.
- Bridge identity is used to distinguish endpoints during bring-up.

## Refactor Note (Important)
- Python UI must be used only to initialize/start the bridge.
- Python UI must not interfere with live bridge traffic after initialization.
- Runtime bridge data/control flow should continue board-to-board without UI in the active traffic path.
