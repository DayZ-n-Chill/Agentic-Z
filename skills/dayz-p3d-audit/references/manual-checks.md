# Checks the audit script does not run

Faults that `/dayz-p3d-audit` cannot see from one `.p3d`, with how to measure each by hand, and rules for trusting any new gate you build. Open this when the audit passes and the model still misbehaves, or before copying numbers between sibling models.

**Not yet checked on `P:\`**, except the vanilla LOD counts in the performance section: these are measured results from mod projects (LFPowerGrid, LFQuad, LFDucati, an HH-60G helicopter) and tool behaviour (binarize, an ODOL to MLOD converter).

**Contents**

- Sibling-model frame parity (before copying rotation offsets)
- UV audit step
- Resolution LOD count (performance)
- Resolve every face index
- Trusting a FAIL from a new gate on a binarized model
- The resolved-vertex budget
- Which channel did a "vanilla value" arrive through
- On Linux

## Sibling-model frame parity, before copying rotation offsets (SP-221)

Two `.p3d` of the SAME family can differ 90° in authorship frame. Before copying
rotation offsets from one kit to another, verify frame parity. Compare Memory LOD
(res `1e15`) selections point-to-point between the two models. If the coordinates
correspond by an **axis permutation** — measured here `(x, y, z) → (x, -z, y)` —
the models do NOT share a frame and their config rotation offsets are **not
interchangeable**. The discriminator of "which way it mounts" is the **thin axis
of the Geometry LOD** (`1e13`): that axis must sit perpendicular to the mounting
surface, and pitch comes from there, not from the family or the model name.
**The visual LOD bbox is NOT a signal** — measured counterexample in the same
session: `gate_and.p3d` (Y≈2, Z≈1.16, pitch 90) and `switch_v2.p3d` (Y=1, Z≈2,
pitch 90) have opposite long axes and the SAME pitch. Corollary: "the two kits
are identical except this override" is a hypothesis about CONFIG; measure the
model before acting on it.

Measured 2026-08-10 on LFPowerGrid (a batch reorientation of placed kits). `switch_v2.p3d`
vs `switch_v2_remote.p3d`, memory points: `switch_axis` (-0.0407, 0.0288, -0.1472)
→ (-0.0407, 0.1472, 0.0288); `ce_center` (0.0001, 0.0366, -0.1286) → (0.0001,
0.1286, 0.0366); `boundingbox_max` (0.1833, 0.1039, -0.3665) → (0.1833, 0.3665,
0.1039); Geometry LOD 0.293/0.0911/0.4185 → 0.293/0.4185/0.0911. It refuted a review finding that a pitch had been
forgotten on one kit: applying the "forgotten" pitch would have PRODUCED the symptom it was meant to cure. MLOD
parser used (memory points + extents per LOD, PowerShell, without py3d) is
reusable. See also the model pipeline skill (`dayz-model-pipeline`).

## UV audit step (SP-051, added 2026-07-06)

`audit_p3d.py` reads no UVs. A UV audit beyond out-of-range values was run with a project-local
script (`uv_audit.py` of the LFQuad project, not shipped here). Its checks: zero-uv%, NaN, bounds vs ODOL int16 quantization
(range ≤ ~32 on 2048 tex — min/max over the WHOLE LOD), degenerate faces, mirrored islands
(signed UV area — breaks _nohq), Monte-Carlo overlap per group and cross-group, island count
(union-find) + texel density (px/m; healthy reference ≈ 292 px/m LFQuad wheels; 27 px/m =
measured cause of bake artifacts). Gotchas: whitelist `proxy:*` faces (degenerate by design),
exclude full-frame tris (UV area > 0.2) from cross-group overlap, classic raster misses
subpixel islands. The full symptom to fix catalog is the UV mapping material of the `uv-clean-atlas` skill.

## Resolution LOD count: a performance check (added 2026-07-14)

WARN (performance, not a correctness killer): flag any model that ships with only ONE
resolution LOD. With a single LOD the engine loads the full mesh at any distance (no
distance-based decimation), inflating client/server load; it is a documented cause of
stutter and random disconnects when many such models are near the player. Vanilla
reference: the plate carrier's ground model `P:\DZ\characters\vests\plate_carrier_g.p3d` has four visual LODs
and its holster and pouches models five each (LOD lists read from the file headers); most vanilla gear ships
three to five (`_shared/models/lods.md`).

- Heuristic: `resolution_LOD_count >= 2` for any non-trivial visible model; a genuinely
  low-poly prop (a few hundred faces) may legitimately keep one.
- Manual (not automated in `audit_p3d.py`): open in Object Builder / py3d and count
  Resolution LODs; or compare face counts across LODs (identical counts = the ladder is a
  copy, not a decimation; see the LODs and geometry reference of `dayz-model-pipeline`).
- Fix: author decimated LODs (the user decides, per the decimation gate of the model pipeline skill).

Source: community report (YouTube Oqz8-FNQypI, 2026) + BI LOD wiki recommendation of at
least one resolution LOD. Related BI cap: 30+ total LODs can crash the binarizer.

## Resolve every face index (SP-142, added 2026-08-31)

Counts, selection names, proxy centroids, and material pairs live in a different space from
face indices. A freshly assembled or surgically edited `.p3d` must have a gate that
dereferences every face corner's `point_index` and `normal_index` against the live pools.
Fail on the first out-of-range value and name the LOD, face, corner, index, and pool length.
Do not treat matching cardinalities as an equivalent check.

Run `binarize` as the authoritative serialization check, with the previous known-good model
as a control in the same run. This separates a product failure from a broken test bench and
makes pre-existing log noise comparable. A binarize pass proves that this index/serialization
gate passed; it still does not replace the in-game spawn gate (SP-216, `winding-diagnostics.md`, "How to verify", item 5).

## Trusting a FAIL from a new gate on a binarized ODOL: run the control piece first (added 2026-09-28)

[DESIGN] Before trusting a FAIL from a new ODOL gate, run the gate on a piece that already works in game (here `drivewheel`): if the control also fails, the gate is wrong, not the model — two rebuild cycles stopped on a bad gate while the model was fine. [EXACT] In a binarized ODOL the named selections of the VISUAL LODs are stored as faces (also `drivewheel` and `damper_1`, which do move in game); read their vertices through the face corner indices. Memory and Geometry LOD selections list vertices. And write gate expressions against the tool's real output, not its vocabulary: the anatomy dump writes animation types as numbers (0 rotation, 4 translation), so an expression matching the string `rotation` never fires.

## The resolved-vertex budget (SP-359)

A `.p3d` can pass this entire audit with 0 CRITICAL and still be rejected by the engine when it
loads the MLOD with `Too many vertices`, which surfaces in-game as
`PHYSICS (E): Won't simulate, it has no geometry` even when the Geometry LOD is perfect.

What the script does today (`check_lod0_vertex_budget`): it counts the `(point, normal, uv)` triples of the most detailed
Visual LOD and fails only past 65,535. A per-LOD count with a warning past 90 % of the ceiling measured for that
model is not built.

The ceiling is per-model, not a constant — `RESOLVED_LIMIT = 65535` is a false friend. Measured
cliff on the HH-60G: 46,133 triples load, 46,134 do not (25 in-game verdicts, zero false).

The authoritative gate is `binarize.exe`, not this count, and it has three states: PASS /
CAPACITY_FAIL / OTHER_FAIL. CAPACITY_FAIL means do not go in-game to "fix" Geometry; OTHER_FAIL
means do not touch geometry at all. Evidence and the measured cliff: SP-122 and the binarize vertex budget reference of the dayz-vehicles skill.
One `OTHER_FAIL` measured since is a size limit of the collision LODs that prints nothing; its
two checks and its fix, which moves pieces to another model and changes none of them, are in
that file, item 3 (SP-458).

## Which channel did a "vanilla value" arrive through (LL-364)

Before citing "vanilla equals N" for a field, ask THROUGH WHAT CHANNEL that N arrived. If material is distributed in derived format (ODOL) and the number was produced by a converter, the right question is not what it is worth but whether field survives conversion: an ODOL to MLOD converter (`odol_to_mlod.py`, an external tool) writes bare `face.flags = 0`, so any "vanilla uses flags=N" measured there is the instrument answering itself. Measured 2026-08-24 via round-trip: `binarize.exe` DISCARDS MLOD per-face `flags` field — three MLODs differing only in it binarize to a byte-for-byte identical model, while two positive controls (point moved 1 cm, texture cleared on same faces) do change output. And a neighboring field in derived format carrying same bit (`Section.special`, per section) is NOT the same field.

## On Linux

Everything above is the Windows workflow and stays valid there. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in the shared Linux and Proton notes (`_shared/linux-proton.md`); this section only says what changes for this skill.

- Pack, sign and binarize with dayzmake >= 1.0.0, bzed's DayZ fork of armake2 (https://github.com/bzed/dayzmake), pinned to `v1.0.0` (the release binary `dayzmake-v1.0.0-debian-trixie-x86_64.tar.gz` from https://github.com/bzed/dayzmake/releases/tag/v1.0.0, or `cargo install --git https://github.com/bzed/dayzmake --tag v1.0.0`): use `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. Upstream armake2 is no substitute: it is built for Arma, its V3 file hash omits `*.c` files (dayzmake v1.0.0 includes them) and lacks the DayZ-only functions dayzmake keeps adding. `skills/_shared/scripts/dayz-mod-pack.sh` wraps them (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`; its notes are in `skills/dayz-build-pbo/references/dayzmake-linux.md`). The author's 2026-11-03 textured-cube comparison with BI binarize from a `P:` root matched byte for byte (fork commit `7dcb3cf`, then still named armake2; `v1.0.0` contains it); this is not an in-game ODOL check. See the shared Linux and Proton notes (`skills/_shared/linux-proton.md`) for setup and limits.
- `P:\` is a plain directory mapped by `dayz-proton.sh init <dir>` (the script is `skills/_shared/scripts/dayz-proton.sh`); a `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...`.
- Object Builder and TexView run under Proton: `dayz-proton.sh gui ObjectBuilder <p3d>`, `gui TexView <paa>`. Object Builder opened and displayed a model; editing in it was not exercised. Offline checks (`py3d`, the model preflight tool under `scripts/tools/dayz-model-preflight/`, `dayz-3d-viewer`) are Python and run natively.
- In-game checks: the Linux notes of the `dayz-test-ingame` skill (`skills/dayz-test-ingame/references/linux.md`).
