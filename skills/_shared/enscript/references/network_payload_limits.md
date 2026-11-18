# Payload limits of `ScriptRPC` and `ScriptInputUserData`

How much a receiver can read over each channel, how deep the input queue is, whether RPC order holds, and what an acknowledgement proves. Both channels are vanilla classes: `ScriptRPC` at `P:\scripts\3_game\gameplay.c:104` and `ScriptInputUserData` at `P:\scripts\3_game\gameplay.c:120` (`input_user_data.md`).

Every limit below is measured in game on DayZDiag 1.30, with a diag client and server on one machine over loopback and a small test mod. None of it can be checked on `P:\`: these are run time results on one executable, not source facts and not guaranteed limits. Wire size, fragmentation, packet loss and Internet latency are not measured. Measure again before you rely on an exact boundary.

## Strings

| Channel | Read | Not read |
|---|---|---|
| `ScriptRPC` | 1,023 ASCII characters; 511 two byte UTF-8 characters (`Length()` 1,022) | 1,024 ASCII characters: `ctx.Read` fails, the server logs a script VM exception, nothing crashes |
| `ScriptInputUserData` | 143 ASCII characters; 72 two byte characters (`Length()` 144) | 144 ASCII characters: `CanStoreInputUserData()` is true but `Write` returns false and nothing arrives. 143 two byte characters (`Length()` 286) also fail |

`Length()` returns bytes for UTF-8 text. The input channel's byte limit lies between 144 accepted and 286 rejected; the exact value is not known.

## Arrays

| Payload | `ScriptRPC` | `ScriptInputUserData` |
|---|---|---|
| `array<int>` | Read at every size tried, up to 4,096; no upper limit found | Read up to 128. At 140 and above, `Write` returns false while the guard says true. 129 to 139 are untested |
| `array<string>` | 64 strings of 16 characters read | 16 strings of 8 characters read; 32 strings of 8 characters fail `Write` |
| `array<array<int>>` built by hand | Rows are lost: reading a row throws `NULL pointer to instance` in `array<int>.Count`, and the receiver sees 4 rows of 0 | Same |
| `array<ref array<int>>` | 4 by 4 read intact | Same |

Declare a nested payload as `array<ref array<int>>`, and check that each row exists before calling `Count()` on it. `array<float>`, `array<bool>` and maps are untested.

## Input queue

In a burst of ten, four `ScriptInputUserData` packets were sent and received at every payload size tried (1 to 143 characters); for the other six, `CanStoreInputUserData()` returned false. Check the guard before each send and retry once the queue drains.

## RPC order

Ten small RPCs alternating `guaranteed=true` and `guaranteed=false` all arrive, but grouped: the five guaranteed ones first, then the five others. Order across the two modes is not kept. Carry a sequence number and make handlers safe to run twice.

## What an acknowledgement proves

An acknowledgement RPC sent back after the read attempt arrives even when `ctx.Read` failed. It proves the message reached the handler, not that the payload was read. Send the acknowledgement only after `ctx.Read` succeeds, and tie it to the sequence number, the length actually received and a checksum of the content.

## What to do

- Keep `ScriptRPC` strings under 1,024 bytes and split larger data.
- Keep `ScriptInputUserData` payloads small: check `CanStoreInputUserData()` and the return of every `Write` before `Send()`.
- On receipt, check that each `Read` returned true and that a declared count matches what was read.
