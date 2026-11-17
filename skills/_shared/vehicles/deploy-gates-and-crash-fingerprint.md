# Deploy gates, config syntax and crash fingerprints

Gates that prove the packed PBO holds what was approved, the one offline syntax gate for `config.cpp`, and how to compare native crashes.

> Status: the measurements below were taken on third-party vehicle mods (a helicopter, a sports coupe and a quad), not on vanilla, and are not yet checked on `P:\`. A citation written with its full `P:\` path was opened on the vanilla data.

## Vanilla anchors checked on `P:\`

- The nested inheritance a `CfgConvert` base-class canary has to resolve is the vanilla form `class SimulationModule: SimulationModule` (`P:\DZ\vehicles\wheeled\config.cpp:1371`) with `class Axles: Axles` inside it (`P:\DZ\vehicles\wheeled\config.cpp:1431`).

## Packaging: a fix that lives in the generator and not in the binary does not exist

When the fix is *adding or changing a PROPERTY* of a `.p3d` (`autocenter`, `class`, `sbsource`,
`lodnoshadow`), a SHA-based manifest cannot see it — it compares the same wrong file on both sides
and reports green. Measured case (a helicopter): `autocenter=0` was added to the hull's visual LOD
in both assemblers and the PBO was packed minutes later from `.p3d` built before; measured
afterwards on the **48 extracted** models, the 8 sub-models carried it and **all 40 hulls did
not**. The post-`ExtractPbo` gate must READ the property, per LOD, on the extracted files.
Two riders that make the gate survive contact:

- Declare the expectation **in a table with a reason per row, never as "all LODs"**. A healthy pack
  contains **controls that exist in order NOT to change** (an A/B control arm, a byte-frozen
  baseline); a blanket gate rejects them and gets switched off on its first run.
- The producer must satisfy its own gate. Here "all LODs" would have rejected the canonical
  assembler's own output, because the Memory LOD has no geometry to re-centre and therefore never
  carries `autocenter`. Exclusions are declared, not assumed.

## Deployment identity: the artifact a gate validates must be byte-linked to the one the game loads

A native-contract gate that consumes a separate ODOL stage says NOTHING about the deployed PBO.
`-packonly` copies whatever format sits in the compilable tree, and pairing MLOD↔ODOL stage files
by homonymous path is not closure. Measured case (a sports coupe): the gate validated the ODOL
stage doors (~2.1 MB each) while the live PBO carried the source MLOD (8.7/8.1 MB, byte-identical
to the MLOD stage) — nothing in the pipeline linked the two artifacts, and the mismatch surfaced
only during post-crash analysis. Rule, before ANY deploy of a gated artifact: list the PBO, extract
or slice every `.p3d` entry by offset, and require (a) the expected signature (`ODOL` where the
contract is ODOL) and (b) SHA-256 equal to the approved stage — fail on wrong signature, missing
entry, casefold/slash collision, or hash mismatch. Corollary: record the mounted PBO's SHA-256
contemporaneously at every runtime launch; without that seal, no post-crash analysis can prove
which artifact the process actually loaded.

## Native crash fingerprint: compare code bytes, not fault addresses

The RPT's `Fault address` is not an identifier — ASLR moves the module base, so the same code site
prints different addresses across runs and reads as "different bugs". What identifies the detection
site is `Prev. code bytes` + `Fault code bytes` (16 bytes each) plus the engine `Version`.
Measured case (a sports coupe): six `C0000374` crashes split across two addresses (`3523D5F9` and
`57B5D5F9`) had **byte-identical** code bytes and identical low 16 bits — one code site, one engine
build. Reading them by address had produced the false claim that the ODOL-era and MLOD-era crashes
were unrelated; the byte comparison also killed the hypothesis that the artifact FORMAT was the
discriminating variable, since the crash appeared in both. Report "same/different detection
signature", never "same/different bug": `C0000374` is detected on free, not where the
out-of-bounds write happened, so an identical signature still does not prove identical cause.

## config.cpp syntax has one offline gate, CfgConvert, and it only counts with canaries

`-packonly` does NOT rapify, so the config ships as text and the first parser that reads it is
the game's. The DayZ script validator does not check syntax either. What works:

    "...\DayZ Tools\Bin\CfgConvert\CfgConvert.exe" -bin -dst <tmp>.bin <config.cpp>

Gate it with two canaries that MUST fail, or a green proves nothing:

| canary | what CfgConvert answers |
|---|---|
| remove the brace that closes `CfgVehicles` | `line NNN: /CfgVehicles/: Missing '}'` |
| misspell a base class inside the new block | `Undefined base class 'ClutchTypo'` |

The second is worth more than it looks: it proves the parser RESOLVES the nested `class X: X`
chains, which is the real risk when writing variant classes. And one thing that does NOT work as
a canary: dropping the `;` after a closing `}` - CfgConvert accepts it, so it is not a syntax
error in that grammar and a gate built on it declares itself vacuous for the wrong reason.
