# Script network limits (DayZDiag 1.30.164289.70)

Covers the measured string payload sizes over `ScriptRPC` and `ScriptInputUserData`, the input queue depth, RPC burst ordering and what an ACK does and does not prove. Array payloads are in `script-network-arrays.md` and `script-network-array-types.md`.

Status: measured in game on DayZDiag 1.30.164289.70 with a small test mod (the probe), on 2026-11-12. Not yet checked on `P:\`: these are runtime measurements on one executable, not source facts, and the probe and its logs are not in this repo. Both channels are vanilla classes: `ScriptRPC` at `P:\scripts\3_game\gameplay.c:104` and `ScriptInputUserData` at `P:\scripts\3_game\gameplay.c:120`. The source map of the input channel is `script-input-user-data.md`.

The measurements come from a local DayZ diag client and server pair. No reverse engineering was used. The numbers describe the tested string payloads on this executable, not wire bytes or universal engine limits.

## ScriptRPC string payload

A repeated ASCII string was sent from the client to the server through a custom `ScriptRPC`; the server read the payload and the probe sent an ACK after the read attempt.

- 1023 ASCII characters were read successfully (`read_ok=true`); at 1024 the server recorded `read_ok=false` with `blob_len=0` and a script VM exception on the failed read, and the probe still sent its ACK. No process crash was recorded.
- With two-byte UTF-8 `ñ`, 511 characters (`Length()=1022`) were read successfully; 512 characters (`Length()=1024`) and 1023 characters (`Length()=2046`) recorded `read_ok=false` with `blob_len=0`.

[DESIGN] Practical reading: keep `ScriptRPC` string payloads at or below the observed successful sizes and fragment larger data. Do not treat the probe's ACK as proof that the payload was read.

## ScriptInputUserData string payload

Different sizes were sent through `ScriptInputUserData` than in the RPC sweep, and read by the server.

- 143 ASCII characters arrived (`read_ok=true`); at 144, `CanStoreInputUserData()` was still true but `Write` returned false and nothing arrived.
- With two-byte UTF-8 `ñ`, 71 and 72 characters (`Length()` 142 and 144) arrived; 143 characters (`Length()=286`) was rejected by `Write`. The probe did not isolate a character limit from a byte limit: the observed byte boundary lies somewhere between 144 bytes accepted and 286 bytes rejected, so no 144-byte limit is stated here.

[DESIGN] Practical reading: always check the return value of `Write`; `CanStoreInputUserData()==true` is not enough.

## Input queue

For each tested payload size, ten input slots were checked in a burst (payload sizes of 1, 16, 64, 128 and 143 characters). At every tested size, four messages were sent and received, and six were not sent because `CanStoreInputUserData()` returned false. Four were admitted at every tested size; this does not exclude a byte or per-frame budget.

[DESIGN] Practical reading: check the gate before sending and retry after the queue drains.

## RPC burst and ordering

Ten small RPCs were sent, alternating `guaranteed=true` and `guaranteed=false`. All ten arrived on the server, in the order 5000, 5002, 5004, 5006, 5008, then 5001, 5003, 5005, 5007, 5009, so the original interleaving was not preserved, and the client received all ten ACKs.

[DESIGN] Practical reading: carry a sequence number and make handlers idempotent; do not rely on send order across reliability modes.

## ACK semantics

The probe's ACK is the probe's own design, not engine behaviour: its handler sent the ACK after the read attempt, whether or not the read succeeded. The ACK was a small RPC carrying sequence and declared size, not the payload. An ACK arrived for RPC payloads whose `ctx.Read(blob)` had failed, including 1024, 2048 and 4096 ASCII characters; the server log records a script VM exception on those failed reads, and nothing crashed.

[DESIGN] Practical reading: the probe's ACK means the RPC envelope reached the handler, not that the payload was read. Send an ACK only after `ctx.Read` succeeds, and bind it to the sequence, the actual received length and a hash or checksum of the received content; a declared length or a small ACK alone does not prove payload integrity.

## Measurement scope

- The executable that ran was DayZDiag 1.30.164289.70; the script logs show only the define `DAYZ_1_30`. The value 26220720 is the buildid of the DayZ Server install, which provided the mission folder, not the executable that ran, and is not used as the build here.
- Local loopback client/server on one machine; the client launch shows `-connect=127.0.0.1 -port=2302`. Packet loss was not measured, and no Internet latency was measured.
- Strings only: ASCII and two-byte UTF-8; arrays, integers and binary serialization were not measured in these string runs.
- `Length()` returned bytes for UTF-8; the exact wire overhead was not measured.
- No fragmentation and no real-loss test were measured, and no reverse engineering was used.
