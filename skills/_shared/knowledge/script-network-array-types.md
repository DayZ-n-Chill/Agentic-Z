# Script network array types (DayZDiag 1.30.164289.70)

Covers what was measured when `array<int>`, `array<string>` and nested arrays were sent over `ScriptRPC` and `ScriptInputUserData`. Earlier, smaller runs are in `script-network-arrays.md`; string payloads are in `script-network-limits.md`.

Status: measured in game on `DayZDiag_x64.exe` 1.30.164289.70 with a small test mod (the probe), on 2026-11-13. Not yet checked on `P:\`: these are runtime measurements on one executable, not source facts, and the probe and its logs are not in this repo. Both channels are vanilla classes: `ScriptRPC` at `P:\scripts\3_game\gameplay.c:104` and `ScriptInputUserData` at `P:\scripts\3_game\gameplay.c:120`. The source map of the input channel is `script-input-user-data.md`.

The probe ran a diag client and a diag server on loopback on one machine. The installed DayZ Server appmanifest buildid was `26220720`; the DayZ client appmanifest buildid was `26403755`. The probe measured what the receiver read and whether the client saw an ACK; it did not measure wire size, fragmentation, packet loss or Internet latency.

## `array<int>` over `ScriptRPC`

The client wrote sequence, count and an `array<int>`; the server read them and returned an ACK carrying sequence and count. Counts 512, 1024 and 2048 read back with `read_ok=true` and matching content checksums. Count 4096 read back with `read_ok=true` and `values.Count()=4096`, but the server did not log its checksum in this pass.

| count | client `Write` | server `Read` | server `values.Count()` | server checksum |
|---:|---|---|---:|---:|
| 512 | true | true | 512 | 130816 |
| 1024 | true | true | 1024 | 523776 |
| 2048 | true | true | 2048 | 2096128 |
| 4096 | true | true | 4096 | not logged |

## `array<int>` over `ScriptInputUserData`

The client wrote message type, sequence, count and an `array<int>`; the server read them and returned an ACK. Counts 40, 48, 64, 96 and 128 wrote and read with matching checksums. At 140, 143, 144, 192, 255 and 256 elements, `CanStoreInputUserData()` was true but `msg.Write(values)` returned false and the server received nothing. The observed boundary is between 128 and 140; 129 to 139 were not tested, so the exact threshold is not isolated.

| count | `CanStoreInputUserData()` | client `Write` | server `Read` | server checksum |
|---:|---|---|---|---:|
| 40 | true | true | true | 780 |
| 48 | true | true | true | 1128 |
| 64 | true | true | true | 2016 |
| 96 | true | true | true | 4560 |
| 128 | true | true | true | 8128 |
| 140 | true | false | no message | — |
| 143 | true | false | no message | — |
| 144 | true | false | no message | — |
| 192 | true | false | no message | — |
| 255 | true | false | no message | — |
| 256 | true | false | no message | — |

## `array<string>`

`ScriptRPC` read arrays of 1, 16 and 64 strings of 16 ASCII `"S"` characters with `read_ok=true` and matching checksums (`-252021808`, `262618368`, `1050473472`). `ScriptInputUserData` read arrays of 1, 8 and 16 strings of 8 characters with matching checksums; 32 strings of 8 characters (256 bytes) failed `Write` although `CanStoreInputUserData()` was true. The 128-byte case passed and the 256-byte case failed; this pass did not isolate the exact byte boundary.

| channel | elements | bytes per element | result |
|---|---:|---:|---|
| `ScriptRPC` | 1 | 16 | read, checksum matched |
| `ScriptRPC` | 16 | 16 | read, checksum matched |
| `ScriptRPC` | 64 | 16 | read, checksum matched |
| `ScriptInputUserData` | 1 | 8 | read, checksum matched |
| `ScriptInputUserData` | 8 | 8 | read, checksum matched |
| `ScriptInputUserData` | 16 | 8 | read, checksum matched |
| `ScriptInputUserData` | 32 | 8 | `Write=false`, no message |

## Nested arrays

A manually built `array<array<int>>` logged `inner=4` for each row during construction, but reading the rows back threw a VM exception: `NULL pointer to instance. Variable '#return' during call 'array<int>.Count'`. The client therefore recorded `inner=0`; the server received `outer=4`, `inner=0`, `checksum=0` and `read_ok=true`. Passing the array through an `out` parameter did not change the result. Changing the declaration to `array<ref array<int>>` preserved the four inner elements.

With `array<ref array<int>>`, a 4×4 matrix built as `row * 4 + col` was read over both channels with `outer=4`, `inner=4` and checksum `120`. Practical rule: declare manually built nested payloads as `array<ref array<int>>` and check that each row exists before calling `inner.Count()` on receipt; do not assume `array<array<int>>` preserves the inner elements when read through `Get`.

| channel | declaration | client outer/inner/checksum | server outer/inner/checksum | `read_ok` |
|---|---|---|---:|---|
| `ScriptRPC` | `array<array<int>>` | 4 / 0 / 0 | 4 / 0 / 0 | true |
| `ScriptInputUserData` | `array<array<int>>` | 4 / 0 / 0 | 4 / 0 / 0 | true |
| `ScriptRPC` | `array<ref array<int>>` | 4 / 4 / 120 | 4 / 4 / 120 | true |
| `ScriptInputUserData` | `array<ref array<int>>` | 4 / 4 / 120 | 4 / 4 / 120 | true |

## ACK and checksum

The server sent its ACK after reading sequence and count; the ACK carried sequence and count, not a content hash. The checksums above were logged server-side, not inside the ACK. The client's `read_ok=true` on the ACK proves only that the ACK fields were read; payload read success is the server log's `read_ok`, and checksum equality is the integrity check. An ACK does not prove that every value is correct.

## Scope

These are local loopback observations on `DayZDiag_x64.exe` 1.30.164289.70, not universal limits. They cover `array<int>` over `ScriptRPC` through 4096 elements (no upper bound observed), `array<int>` over `ScriptInputUserData` through 128 accepted and 140 rejected, `array<string>` at the sizes above, and a 4×4 `array<ref array<int>>`. They do not cover `array<float>`, `array<bool>`, maps, `ScriptRPC` arrays above 4096 integers, the exact input byte boundary, wire size, fragmentation, packet loss or Internet latency.
