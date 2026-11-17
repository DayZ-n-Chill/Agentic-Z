# Script network array types (DayZDiag 1.30.164289.70)

Covers what was measured when `array<int>`, `array<string>` and nested arrays were sent over `ScriptRPC` and `ScriptInputUserData`. Earlier, smaller runs are in `script-network-arrays.md`; string payloads are in `script-network-limits.md`.

Status: measured results from the author's `NetProbe` test mod. Not yet checked on `P:\`: these are runtime measurements on one executable, not source facts, and the probe source and logs are not in this repo. Both channels are vanilla classes: `ScriptRPC` at `P:\scripts\3_game\gameplay.c:104` and `ScriptInputUserData` at `P:\scripts\3_game\gameplay.c:120`. The source map of the input channel is `script-input-user-data.md`. The `[EXACT][CLAIM-...]` tags are claim IDs in `scripts/dev/knowledge-pack/sources/claims.json`.

Local runtime probe of `array<int>`, `array<string>` and nested arrays over `ScriptRPC` and `ScriptInputUserData`, on `DayZDiag_x64.exe` 1.30.164289.70 (client RPT `DayZDiag_x64_2026-11-13_14-06-36.RPT:2,7`; server RPT `DayZDiag_x64_2026-11-13_14-06-18.RPT:2,7`, both in the probe's own profile folders). The installed DayZ Server appmanifest buildid was `26220720`; the DayZ client appmanifest buildid was `26403755`. The probe ran a diag client and server on loopback on one machine. It measured what the receiver read and whether the client saw an ACK; it did not measure wire size, fragmentation, packet loss or Internet latency.

The probe source is the author's `NetProbe` mod; the author's probe note `dayz-script-network-array-types-probe.md` (the "vault note" below) records the raw log line numbers. The final PBO was built with `AddonBuilder` (`Build Successful`) and has SHA-256 `6660d5be63325f8b51594bbeda234f06bc833e55b5601e324aecd9b41b6023fb`. Run: `33141e55-0737-4c29-8ced-05b4c20178d5`.

## `array<int>` over `ScriptRPC`

The client wrote sequence, count and an `array<int>`; the server read them and returned an ACK carrying sequence and count. Counts 512, 1024 and 2048 read back with `read_ok=true` and matching content checksums. Count 4096 read back with `read_ok=true` and `values.Count()=4096`, but the server did not log its checksum in this pass.

| count | client `Write` | server `Read` | server `values.Count()` | server checksum |
|---:|---|---|---:|---:|
| 512 | true | true | 512 | 130816 |
| 1024 | true | true | 1024 | 523776 |
| 2048 | true | true | 2048 | 2096128 |
| 4096 | true | true | 4096 | not logged |

Evidence: vault note `:12-23`; client log `script_2026-11-13_14-06-36.log:344-351`; server log `script_2026-11-13_14-06-18.log:108-117`. [EXACT][CLAIM-NET-ARRAY-TYPES-RPC]

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

Evidence: vault note `:25-43`; client log `script_2026-11-13_14-06-36.log:354-381`; server log `script_2026-11-13_14-06-18.log:120-132`. [EXACT][CLAIM-NET-ARRAY-TYPES-INPUT]

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

Evidence: vault note `:45-59`; client log `script_2026-11-13_14-06-36.log:382-400`; server log `script_2026-11-13_14-06-18.log:134-139`. [EXACT][CLAIM-NET-STRING-ARRAY-RPC] [EXACT][CLAIM-NET-STRING-ARRAY-INPUT]

## Nested arrays

A manually built `array<array<int>>` logged `inner=4` for each row during construction, but reading the rows back threw a VM exception: `NULL pointer to instance. Variable '#return' during call 'array<int>.Count'` (`RunNested`). The client therefore recorded `inner=0`; the server received `outer=4`, `inner=0`, `checksum=0` and `read_ok=true`. Passing the array through an `out` parameter did not change the result. Changing the declaration to `array<ref array<int>>` preserved the four inner elements. [EXACT][CLAIM-NET-NESTED-DECL]

With `array<ref array<int>>`, a 4×4 matrix built as `row * 4 + col` was read over both channels with `outer=4`, `inner=4` and checksum `120`. Practical rule: declare manually built nested payloads as `array<ref array<int>>` and check that each row exists before calling `inner.Count()` on receipt; do not assume `array<array<int>>` preserves the inner elements when read through `Get`.

| channel | declaration | client outer/inner/checksum | server outer/inner/checksum | `read_ok` |
|---|---|---|---:|---|
| `ScriptRPC` | `array<array<int>>` | 4 / 0 / 0 | 4 / 0 / 0 | true |
| `ScriptInputUserData` | `array<array<int>>` | 4 / 0 / 0 | 4 / 0 / 0 | true |
| `ScriptRPC` | `array<ref array<int>>` | 4 / 4 / 120 | 4 / 4 / 120 | true |
| `ScriptInputUserData` | `array<ref array<int>>` | 4 / 4 / 120 | 4 / 4 / 120 | true |

Evidence: vault note `:61-74`; failure client log `script_2026-11-13_14-00-14.log:403-431`; failure server log `script_2026-11-13_13-59-55.log:140-141`; success client log `script_2026-11-13_14-06-36.log:401-415`; success server log `script_2026-11-13_14-06-18.log:140-141`. [EXACT][CLAIM-NET-NESTED-ARRAY]

## ACK and checksum

The server sent its ACK after reading sequence and count; the ACK carried sequence and count, not a content hash. The checksums above were logged server-side, not inside the ACK. The client's `read_ok=true` on the ACK proves only that the ACK fields were read; payload read success is the server log's `read_ok`, and checksum equality is the integrity check. An ACK does not prove that every value is correct.

Evidence: vault note `:76-78`; client log `script_2026-11-13_14-06-36.log:344-415`; server log `script_2026-11-13_14-06-18.log:108-141`. [EXACT][CLAIM-NET-ARRAY-TYPES-ACK]

## Scope

These are local loopback observations on `DayZDiag_x64.exe` 1.30.164289.70, not universal limits. They cover `array<int>` over `ScriptRPC` through 4096 elements (no upper bound observed), `array<int>` over `ScriptInputUserData` through 128 accepted and 140 rejected, `array<string>` at the sizes above, and a 4×4 `array<ref array<int>>`. They do not cover `array<float>`, `array<bool>`, maps, `ScriptRPC` arrays above 4096 integers, the exact input byte boundary, wire size, fragmentation, packet loss or Internet latency.

[EXACT][CLAIM-NET-ARRAY-TYPES-SCOPE]
