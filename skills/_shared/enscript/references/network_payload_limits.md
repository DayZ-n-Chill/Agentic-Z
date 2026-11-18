# Reference: measured payload limits of `ScriptRPC` and `ScriptInputUserData`

How much a receiver could read over each channel, how deep the input queue is, whether RPC order survives, and what an acknowledgement proves. Both channels are vanilla classes: `ScriptRPC` at `P:\scripts\3_game\gameplay.c:104` and `ScriptInputUserData` at `P:\scripts\3_game\gameplay.c:120` (`input_user_data.md`).

Status: measured in game on `DayZDiag_x64.exe` 1.30.164289, a diag client and server on loopback on one machine (`-connect=127.0.0.1`), with a small test mod. Not yet checked on `P:\`: these are runtime results on one executable, not source facts and not universal limits. Wire size, fragmentation, packet loss and Internet latency were not measured. Re-measure before relying on an exact boundary.

## Strings

| Channel | Read | Not read |
|---|---|---|
| `ScriptRPC` | 1,023 ASCII characters; 511 two-byte UTF-8 characters (`Length()` 1,022) | 1,024 ASCII characters: `ctx.Read` failed, the server logged a script VM exception, nothing crashed |
| `ScriptInputUserData` | 143 ASCII characters; 72 two-byte characters (`Length()` 144) | 144 ASCII characters: `CanStoreInputUserData()` was true but `Write` returned false and nothing arrived; 143 two-byte characters (`Length()` 286) also failed |

`Length()` returns bytes for UTF-8 text. The input channel's byte boundary lies between 144 accepted and 286 rejected; it was not isolated.

## Arrays

| Payload | `ScriptRPC` | `ScriptInputUserData` |
|---|---|---|
| `array<int>` | Read at every size tried up to 4,096; no upper bound found | Read up to 128; at 140 and above `Write` returned false while the guard said true. 129 to 139 were not tried |
| `array<string>` | 64 strings of 16 characters read | 16 strings of 8 characters read; 32 strings of 8 characters failed `Write` |
| `array<array<int>>` built by hand | Rows lost: reading a row threw `NULL pointer to instance` in `array<int>.Count`, the receiver saw 4 rows of 0 | Same |
| `array<ref array<int>>` | 4 by 4 read intact | Same |

Declare a nested payload as `array<ref array<int>>`, and check that each row exists before calling `Count()` on it. `array<float>`, `array<bool>` and maps were not tried.

## Input queue

In a burst, four `ScriptInputUserData` packets were sent and received at every payload size tried (1 to 143 characters); for the other six, `CanStoreInputUserData()` returned false. Check the guard before each send and retry after the queue drains.

## RPC order

Ten small RPCs alternating `guaranteed=true` and `guaranteed=false` all arrived, but grouped: the five guaranteed ones first, then the five others. Order across reliability modes is not kept. Carry a sequence number and make handlers idempotent.

## What an acknowledgement proves

An acknowledgement RPC sent back after the read attempt arrived even when `ctx.Read` had failed. It proves the message reached the handler, not that the payload was read. Send the acknowledgement only after `ctx.Read` succeeded, and bind it to the sequence, the length actually received and a checksum of the content.

## What to do

- Keep `ScriptRPC` strings under 1,024 bytes and split larger data.
- Keep `ScriptInputUserData` payloads small: check `CanStoreInputUserData()` and the return of every `Write` before `Send()`.
- On receipt, check that each `Read` returned true and that a declared count matches what was read.
