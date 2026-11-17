# Script network arrays (DayZDiag 1.30.164289.70)

Covers the first measured run of `array<int>` over `ScriptRPC` (up to 256 elements) and `ScriptInputUserData` (up to 37). The later, larger run is in `script-network-array-types.md`; string payloads are in `script-network-limits.md`.

Status: measured results from the author's `NetProbe` test mod. Not yet checked on `P:\`: these are runtime measurements on one executable, not source facts, and the probe source and logs are not in this repo. Both channels are vanilla classes: `ScriptRPC` at `P:\scripts\3_game\gameplay.c:104` and `ScriptInputUserData` at `P:\scripts\3_game\gameplay.c:120`. The source map of the input channel is `script-input-user-data.md`. The `[EXACT][CLAIM-...]` tags are claim IDs in `scripts/dev/knowledge-pack/sources/claims.json`.

Local runtime probe of `array<int>` over `ScriptRPC` and `ScriptInputUserData`, with the probe `@NetProbe`. It measured what the receiver read and whether the client saw the probe's ACK; it did not measure wire size, fragmentation, packet loss or Internet latency.

## `ScriptRPC` with `array<int>`

The client wrote sequence, count and an `array<int>` of 1, 64, 255 and 256 elements. The server read sequence, count and the array, then sent the probe's ACK carrying sequence and count. All four writes succeeded and all four reads returned `read_ok=true`; `values.Count()` matched the declared count. The client received all four ACKs with `read_ok=true`.

| count | client `Write` | server `Read` | server `values.Count()` | client ACK `read_ok` |
|---:|---|---|---:|---|
| 1 | true | true | 1 | true |
| 64 | true | true | 64 | true |
| 255 | true | true | 255 | true |
| 256 | true | true | 256 | true |

Evidence: client log `script_2026-11-12_20-11-39.log:322-330`; server log `script_2026-11-12_20-11-16.log:119-126`. [EXACT][CLAIM-NET-ARRAY-RPC]

## `ScriptInputUserData` with `array<int>`

The client wrote message type, sequence, count and an `array<int>` of 1, 16, 32, 36 and 37 elements. The server read sequence, count and the array. For this channel the probe's ACK travelled back as a `ScriptRPC` (rpc `NETPROBE_RPC_ARRAY_ACK`), and the client logged it as `ARRAY_RPC_ACK_RECV`. All five writes succeeded and all five reads returned `read_ok=true`; `values.Count()` matched the declared count. The client received all five ACKs with `read_ok=true`. This channel was not tested with 64, 128, 255 or 256 elements.

| count | client `Write` | server `Read` | server `values.Count()` | client ACK `read_ok` |
|---:|---|---|---:|---|
| 1 | true | true | 1 | true |
| 16 | true | true | 16 | true |
| 32 | true | true | 32 | true |
| 36 | true | true | 36 | true |
| 37 | true | true | 37 | true |

Evidence: client log `script_2026-11-12_20-11-39.log:331-347`; server log `script_2026-11-12_20-11-16.log:127-136`; `NetProbePlayer.c:47-54`; `NetProbeGame.c:5`. [EXACT][CLAIM-NET-ARRAY-INPUT]

## ACK and read status

The probe sends its ACK unconditionally after the read attempt, whether or not the read succeeded, so an ACK alone does not prove that the declared count was read. The read is proven by the server log, which recorded `read_ok=true` and `values.Count()` matching the declared count for every array message here. The ACK carried sequence and count, not a content hash, and does not prove that the receiver validated every value.

Evidence: `NetProbeGame.c:76-99`; `NetProbePlayer.c:45-54`; server log `script_2026-11-12_20-11-16.log:119-136`; client log `script_2026-11-12_20-11-39.log:327-330,334,337,340,343,346`. [EXACT][CLAIM-NET-ARRAY-ACK]

## Scope

- The executable that ran was DayZDiag 1.30.164289.70; the script logs show only the define `DAYZ_1_30`. The value 26220720 is the buildid of the DayZ Server install, which provided the mission folder, not the executable that ran, and is not used as the build here.
- The game connection was local loopback: the client launch shows `-connect=127.0.0.1 -port=2302`. Packet loss was not measured.
- Run `ae70ec7d-d975-4b9a-b6cb-07236d87cb8b`. The probe PBO was 12672 bytes with SHA-256 `ca0b88c18a1cf6dc9e31d8b161c260f66b0bdcbaea1e55d325d7b69624fd957e`; its AddonBuilder build reported `Build Successful`. The vault note reports a duplicate-declaration fix in `NetProbePlayer.c` before that rebuild; no raw build log in the attached evidence shows that fix.
- These are local observations, not universal limits. They cover `array<int>` only; `array<string>`, `array<float>`, `array<bool>`, nested arrays and maps were not tested. No wire size, no real packet loss, no fragmentation and no Internet latency were measured. `ScriptRPC` worked through 256 integers and `ScriptInputUserData` worked through 37 integers in this probe.

Evidence: `DayZDiag_x64_2026-11-12_20-11-39.RPT:3,7`; `DayZDiag_x64_2026-11-12_20-11-16.RPT:2-3,7`; `audit-events-excerpt.txt:42-45`; `netprobe-build4.log:30-33`; `pbo-entries.txt:1`; `appmanifest_223350.acf:6,13`; server log `script_2026-11-12_20-11-16.log:4`; server log `script_2026-11-12_20-11-16.log:119-136`; the author's probe note `dayz-script-network-arrays-probe.md:17,21,60-66`. [EXACT][CLAIM-NET-ARRAY-SCOPE]

## Practical reading

- [DESIGN] For compact state, an `array<int>` over `ScriptRPC` worked at 256 elements in this probe; do not fragment at 64 merely because of the serializer.
- [DESIGN] For `ScriptInputUserData`, keep arrays small until a larger run is measured; check `CanStoreInputUserData()` and the return of `Write` before `Send()`.
- [DESIGN] On the receiving side, check that `ctx.Read` succeeded and that `values.Count()` matches the declared count before accepting the message.
- [DESIGN] For anti-cheat and idempotency, sequence plus count is advice only and was not measured as protection here; add a hash or a per-element check when the values themselves matter.
