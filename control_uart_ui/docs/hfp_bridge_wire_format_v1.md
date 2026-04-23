# HFP Bridge Wire Format v1 (`HFPB1`) - Raw HFP Payload Model

## 1. Design Decision

This v1 format uses:
- a small reliable transport envelope (`seq`, `ack/nak`, `sid`, `crc`, replay flags)
- **raw HFP protocol lines as payload** (for example `AT+CHUP`, `RING`, `+CLIP: "+13474070958",145`)

No custom semantic topics like `CALL.ANSWER` are used for HFP signaling.

UI must stay passive and forward lines unchanged.

## 2. Frame Format (Single Line, Fixed Order)

```text
HFPB1|<T>|<SRC>|<DST>|<SID>|<SEQ>|<REF>|<PRI>|<FLG>|<TS>|<PL>|<CRC>\n
```

Field order is mandatory in v1.

## 3. Field Definitions

1. `HFPB1`
- literal protocol marker/version.

2. `<T>` frame type
- `HFP` raw HFP line payload frame
- `ACK` positive acknowledgment
- `NAK` negative acknowledgment
- `SYN` session start/hello
- `RST` session reset
- `HBT` heartbeat
- `SNP` optional state snapshot (transport/session state only)

3. `<SRC>`
- `HF` or `AG`

4. `<DST>`
- `HF` or `AG`

5. `<SID>` session id
- 8 hex uppercase chars (example: `01AF22C0`)
- regenerated when local bridge link/session restarts.

6. `<SEQ>` sequence id
- 8 hex uppercase chars, monotonic per (`SRC`,`SID`)
- starts from `00000001`.

7. `<REF>` referenced sequence
- sequence being acknowledged/rejected for `ACK`/`NAK`
- `--------` when not applicable.

8. `<PRI>` priority
- `C` critical (call-control/call-state-critical)
- `N` non-critical (telemetry/optional indicators)

9. `<FLG>` flags (2-hex bitmask)
- bit0 `0x01`: retry retransmission
- bit1 `0x02`: duplicate context
- bit2 `0x04`: replay after reconnect
- bit3 `0x08`: reserved for future use
- bits4-7 reserved, must be `0` in v1

10. `<TS>` timestamp
- milliseconds since boot, decimal unsigned.

11. `<PL>` payload
- for `HFP`: base64url of UTF-8 JSON wrapper (see section 4)
- for control types (`ACK`,`NAK`,`SYN`,`RST`,`HBT`,`SNP`): base64url JSON control payload
- use `-` for empty payload.

12. `<CRC>`
- CRC16-CCITT-FALSE (poly `0x1021`, init `0xFFFF`, no reflect, xorout `0x0000`)
- calculated over bytes from `H` in `HFPB1` through final `|` before `<CRC>`
- 4 hex uppercase chars.

## 4. HFP Payload Wrapper (JSON inside `PL`)

`T=HFP` payload JSON:

```json
{
  "msg_ver": 1,
  "dir": "HF_TO_AG" | "AG_TO_HF",
  "kind": "CMD" | "RESP" | "UNSOL",
  "line": "raw hfp line without CR/LF"
}
```

Rules:
- `line` is the actual HFP text (examples below).
- Sender strips trailing `\r`/`\n` before encoding.
- Receiver re-adds required terminator for local stack API as needed.
- `kind` helps policy engines classify behavior but does not replace raw HFP line semantics.

Examples for `line`:
- `AT+CHUP`
- `AT+CLCC`
- `RING`
- `+CLIP: "+13474070958",145`
- `+CIEV: 3,1`
- `+CLCC: 1,1,4,0,0,"+13474070958",145`
- `OK`
- `ERROR`

## 5. ACK / NAK / Reliability

## 5.1 ACK-required frames
- `HFP` with `PRI=C` requires `ACK` or `NAK`
- `SYN`, `RST`, `SNP` require `ACK` or `NAK`
- `HFP` with `PRI=N` may be best-effort

## 5.2 ACK payload JSON
```json
{"msg_ver":1,"rc":"OK"}
```

## 5.3 NAK payload JSON
```json
{"msg_ver":1,"rc":"BAD_FMT|BAD_CRC|BAD_STATE|UNSUPPORTED|OVERFLOW|TIMEOUT","reason":"short_text"}
```

## 5.4 Retry policy
- timeout: 150 ms initial
- backoff: 150, 300, 600, 1200, 2400 ms
- max retries: 5
- retransmissions set `FLG |= 0x01`

## 5.5 Duplicate policy
- dedupe by (`SRC`,`SID`,`SEQ`) with cache >= 256 entries
- do not re-apply duplicate side effects
- resend prior `ACK`/`NAK` when available

## 6. Queue / Replay / Reconnect

Queueing:
- critical queue depth: 64
- non-critical queue depth: 256
- if critical queue full: return `NAK rc=OVERFLOW` (never silent drop)
- if non-critical queue full: drop oldest non-critical first

Replay after reconnect:
- mark replay frames with `FLG |= 0x04`
- replay order:
  1. critical frames original order
  2. non-critical frames original order

Reconnect handshake:
1. `SYN` from initiator
2. peer `ACK`
3. optional `SNP` session snapshot
4. normal `HFP` traffic resumes

On fatal parser/state mismatch:
- send `RST`
- clear transient queues/state
- restart from `SYN`

## 7. Priority Guidance for HFP Lines

Recommended `PRI=C` lines:
- `AT+CHUP`, `ATA`, `ATD...`, `AT+CHLD...`, `AT+CLCC`
- `RING`
- `+CIEV` with call/callsetup/callheld indicators
- `+CLIP`
- `OK`/`ERROR` responses to critical commands

Recommended `PRI=N` lines:
- signal/battery/service indicators not affecting immediate call control
- optional informational responses

## 8. Size / Charset Constraints

- frame max: 1024 bytes including newline
- ASCII printable only for outer frame
- payload JSON is UTF-8 then base64url-encoded
- `line` max length: 512 chars (before base64url)

## 9. Normative UI Behavior

UI relay must:
- forward full frames unchanged (`HF->AG`, `AG->HF`)
- preserve per-direction ordering
- log raw RX/TX frame lines with timestamp + side tag
- never parse HFP semantics, remap indexes, inject synthetic lines, or alter retries

## 10. Example Frames

Note: CRC values below are illustrative placeholders.

HF -> AG raw unsolicited caller ID:
```text
HFPB1|HFP|HF|AG|01AF22C0|0000002A|--------|C|00|1244332|eyJtc2dfdmVyIjoxLCJkaXIiOiJIRl9UT19BRyIsImtpbmQiOiJVTlNPTCIsImxpbmUiOiIrQ0xJUDogXCIrMTM0NzQwNzA5NThcIiwxNDUifQ|A1B2
```

AG -> HF raw command:
```text
HFPB1|HFP|AG|HF|77B91011|00000010|--------|C|00|553991|eyJtc2dfdmVyIjoxLCJkaXIiOiJBR19UT19IRiIsImtpbmQiOiJDTUQiLCJsaW5lIjoiQVQrQ0hVUCJ9|C3D4
```

ACK AG -> HF:
```text
HFPB1|ACK|AG|HF|77B91011|00000011|0000002A|C|00|554001|eyJtc2dfdmVyIjoxLCJyYyI6Ik9LIn0|1122
```

NAK HF -> AG:
```text
HFPB1|NAK|HF|AG|01AF22C0|0000002B|00000010|C|00|1244401|eyJtc2dfdmVyIjoxLCJyYyI6IkJBRF9TVEFURSIsInJlYXNvbiI6Im5vX2FjdGl2ZV9zZXNzaW9uIn0|3344
```

## 11. Compatibility

- Breaking format changes require `HFPB2`.
- Unknown `T` must be rejected with `NAK rc=UNSUPPORTED` when possible.
- Unknown JSON fields in payload must be ignored (forward compatibility).

