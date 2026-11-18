# Checks the audit script does not run

Covers the faults `/dayz-p3d-audit` cannot see from one `.p3d`, how to measure each by hand, and how to trust a new check you build. Open it when the audit passes and the model still misbehaves, or before copying numbers between sibling models.

Except the vanilla LOD counts in "Resolution LOD count", these are results measured on mod projects (power grid kits, a quad, a motorbike, a helicopter) and on tool behaviour (binarize, an ODOL to MLOD converter); they are not checked on `P:\`.

## Sibling-model frame parity

Two `.p3d` files of the same family can be authored in frames a quarter turn apart. Before copying rotation offsets from one model to another, compare their Memory LOD (`1e15`) points one by one. If the coordinates match through a swap of axes, for example `(x, y, z)` to `(x, -z, y)`, the models do not share a frame and their config rotation offsets are not interchangeable.

What tells how a model mounts is the thin axis of its Geometry LOD (`1e13`): that axis sits perpendicular to the mounting surface, and the pitch follows from it, not from the family or the model name. The Visual LOD's bounding box tells nothing: two kits with opposite long axes (Y about 2 and Z about 1.16, against Y 1 and Z about 2) take the same pitch of 90. "The two kits are identical except this override" is a claim about the config; measure the models before acting on it.

Measured on two switch models of a power grid mod, a plain and a remote version:

| Point or extent | First model | Second model |
|---|---|---|
| `switch_axis` | (-0.0407, 0.0288, -0.1472) | (-0.0407, 0.1472, 0.0288) |
| `ce_center` | (0.0001, 0.0366, -0.1286) | (0.0001, 0.1286, 0.0366) |
| `boundingbox_max` | (0.1833, 0.1039, -0.3665) | (0.1833, 0.3665, 0.1039) |
| Geometry LOD extents | 0.293, 0.0911, 0.4185 | 0.293, 0.4185, 0.0911 |

A review had flagged a pitch as forgotten on one of them; applying it would have caused the fault it meant to cure. The comparison needs only the memory points and the extents per LOD, which any MLOD reader gives, py3d included. See also `_shared/models/generated-model-pipeline.md`.

## UV checks

`audit_p3d.py` reads no UVs. A fuller UV check, built as a script local to one project and not shipped here, looks at:

- the share of zero UVs, and NaN values;
- the range against ODOL int16 quantization (about 32 at most on a 2048 texture), taken as the min and max over the whole LOD;
- degenerate faces;
- mirrored islands (signed UV area), which break `_nohq` maps;
- overlap within a group and across groups (Monte Carlo sampling);
- the island count (union find) and the texel density in pixels per metre: healthy wheels read about 292 px/m, and 27 px/m was the measured cause of bake artifacts.

Leave `proxy:*` faces out (they are degenerate by design), leave full frame triangles (UV area over 0.2) out of the cross-group overlap, and remember that a plain raster misses islands smaller than a pixel. Which in-game symptom points at which UV fault is in `_shared/models/uv-mapping.md`; the repair is the clean UV atlas of `dayz-model-tools` (`_shared/models/tools-uv-atlas.md`).

## Resolution LOD count

A performance WARNING, not a correctness killer: flag a model that ships with only one resolution LOD. With one LOD the engine draws the full mesh at every distance, which loads client and server; stutter and random disconnects are reported when many such models are near the player (reported, not measured here).

Vanilla gear ships three to five (`_shared/models/lods.md`): the plate carrier's ground model `P:\DZ\characters\vests\plate_carrier_g.p3d` has four Visual LODs, and its holster and pouches models five each (read from the file headers).

- Aim for at least two resolution LODs on any visible model of some size; a low poly prop of a few hundred faces may keep one.
- `audit_p3d.py` does not count them. Open the model in Object Builder or py3d and count the resolution LODs, and compare face counts across them: identical counts mean the LODs are copies, not reductions (`_shared/models/lods-authoring.md`).
- Fix: author reduced LODs; the user decides, at the decimation step of the model pipeline.

30 or more LODs in total can crash the binarizer (reported, not checked here).

## Resolve every face index

Counts, selection names, proxy centroids and material pairs live apart from face indices. A `.p3d` freshly assembled or edited by script needs a check that looks up every face corner's `point_index` and `normal_index` in the live pools. Fail on the first value out of range and name the LOD, face, corner, index and pool length. Matching counts are not the same check.

Run `binarize` as the final word on serialization, with the last known good model as a control in the same run; that separates a broken model from a broken test bench and makes old log noise comparable. A binarize pass shows this check passed; it still does not replace the spawn in game (`winding-diagnostics.md`, "Offline checks do not clear a spawn").

## Trusting a FAIL from a new check on a binarized model

Before trusting a FAIL from a new check on an ODOL, run it on a piece that already works in game, such as a drive wheel. If the control fails too, the check is wrong, not the model.

- In a binarized ODOL the named selections of the Visual LODs are stored as faces, `drivewheel` and `damper_1` among them, which do move in game. Read their vertices through the face corner indices. Memory and Geometry LOD selections list vertices.
- Write check expressions against the tool's real output, not its vocabulary: the anatomy dump writes animation types as numbers (0 rotation, 4 translation), so an expression that matches the string `rotation` never fires.

## The resolved vertex budget

A `.p3d` can pass this whole audit with no CRITICAL and still be refused when the engine loads the MLOD with `Too many vertices`, which shows in game as `PHYSICS (E): Won't simulate, it has no geometry` even when the Geometry LOD is perfect.

`check_lod0_vertex_budget` counts the `(point, normal, uv)` triples of the most detailed Visual LOD and fails only past 65,535. There is no per LOD count with a warning near the limit measured for a model. The limit is per model, not a constant, so `RESOLVED_LIMIT = 65535` misleads: on one helicopter, 46,133 triples load and 46,134 do not (25 in-game verdicts, none contradicting).

`binarize.exe` decides, not this count, and it has three results: PASS, CAPACITY_FAIL and OTHER_FAIL. On CAPACITY_FAIL do not go in game to fix the Geometry LOD; on OTHER_FAIL do not touch geometry at all. The record and the measured limit are in `_shared/vehicles/binarize-vertex-budget.md`. One OTHER_FAIL measured since is a size limit of the collision LODs that prints nothing; its two checks and its fix, which moves pieces to another model and changes none of them, are in item 3 of that file.

## Where a "vanilla value" came from

Before citing "vanilla uses N" for a field, ask how that N reached you. Vanilla models ship as ODOL, so a number read through a converter answers whether the field survives conversion, not what vanilla uses. An ODOL to MLOD converter (`odol_to_mlod.py`, an outside tool) writes `face.flags = 0` on every face, so any "vanilla uses flags=N" read from its output is the tool answering itself.

Measured by round trip: `binarize.exe` drops the per face `flags` field of an MLOD. Three MLODs that differ only in it binarize to the same file byte for byte, while two positive controls (a point moved 1 cm, the texture cleared on the same faces) do change the output. The per section `Section.special` of the ODOL can carry the same bit, but it is not the same field.

## On Linux

The Windows workflow above still holds there. The Proton setup, the tools that work and their pitfalls are in `_shared/linux-proton.md`; this section says only what changes for this skill.

- Pack, sign and binarize with dayzmake, the DayZ build of armake2, at a pinned release; which version and how to install it are in `skills/dayz-build-pbo/references/dayzmake-linux.md`, "Get the right dayzmake". Use `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. The original armake2 is no substitute: it is built for Arma, its V3 file hash leaves out `*.c` files (dayzmake includes them), and it lacks dayzmake's DayZ functions. `scripts/tools/dayz-linux/dayz-mod-pack.sh` wraps them (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`; its notes are in that same file). A textured cube binarized with dayzmake 1.0.0 matched Bohemia's binarize from a `P:` root byte for byte; that is not a check of the ODOL in game.
- `P:\` is a plain folder mapped by `dayz-proton.sh init <dir>` (`scripts/tools/dayz-linux/dayz-proton.sh`); a `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...`.
- Object Builder and TexView run under Proton: `dayz-proton.sh gui ObjectBuilder <p3d>`, `gui TexView <paa>`. Object Builder opens and shows a model; editing in it is not tested. The offline checks (py3d, the model preflight tool under `scripts/tools/dayz-model-preflight/`, the 3D viewer under `scripts/tools/dayz-3d-viewer/`) are Python and run natively.
- In-game checks: the Linux notes of `/dayz-launch-test` (`skills/dayz-launch-test/references/linux.md`).
