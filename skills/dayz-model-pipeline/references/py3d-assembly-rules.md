# py3d assembly rules

Rules for writing or editing a `.p3d` with py3d beyond the basic API: which py3d to install, where mass may sit, how to cut and replace geometry without breaking selections, what the validator's findings mean, and which checks no offline tool can replace. `py3d-direct-generation.md` has the API itself. These are measurements of the py3d library and of the binarize and spawn steps on generated models, so they are tool behavior and nothing here is checked on `P:\`; notes on reading an MLOD with py3d are in `_shared/py3d-mlod-notes.md`.

Evidence labels: `[EXACT]` is measured, `[DESIGN]` is a rule derived from it.

## Which py3d

This skill needs the py3d that ships in this repo at `scripts/tools/py3d`, version 1.6.0 or later. It is an MLOD codec with guards against writing a corrupt file, the DayZ LOD constants, `validate()`, proxies, the recipe helpers and the command line `python -m py3d`.

```cmd
python -m pip install -e scripts\tools\py3d
python -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,6,0), (py3d.__version__, py3d.__file__)"
```

- Do not run `pip install py3d`: the package of that name on PyPI is an unrelated point cloud library.
- Do not install any other MLOD library that imports as `py3d`: it has none of the guards or helpers named above, and one environment holds only one package of that import name. Uninstall such a copy before installing this one; the assert above tells you which one is active. `/dayz-p3d-audit` uses this same py3d (its `requirements.txt` names `scripts/tools/py3d`).

## Mass only on the Geometry LOD: `point.mass = None`, never `0.0` (added 2026-06-02)

### Rule

When assembling a LOD that is not the Geometry LOD (Fire Geometry `7e15`, View Geometry `6e15`, LandContact `2e15`, Memory `1e15`, shadow, or a visual LOD below 1000) with py3d, set `point.mass = None` on each point. Never set `point.mass = 0.0`.

Reason: py3d writes a `#Mass#` TAGG whenever any `point.mass` of the LOD is not `None`, even when it is exactly `0.0`. The `.p3d` then carries a spurious `#Mass#` in a LOD that should have none. Addon Builder's binarize bakes the mass of that LOD (sum 0), so the deployed ODOL has a centre of mass of `(0,0,0)` and zero inertia. `ECE_PLACE_ON_SURFACE` then places the vehicle at the height of its centre of mass, 0: it spawns underground and PhysX throws it out while pushing it clear. Measured on a vehicle; bisecting its LODs isolated the bug.

This agrees with `_shared/models/named-properties.md`: physics uses the point masses on the Geometry LOD.

### What produced the bug

```python
# WRONG: writes a #Mass# TAGG in the Fire Geometry LOD, all zeros
for face in firegeo_lod.faces:
    for v in face.vertices:
        v.point.mass = 0.0      # py3d writes #Mass#, binarize uses it, centre of mass = 0
```

### Correct

```python
# RIGHT: no #Mass# TAGG; binarize uses the Geometry LOD's #Mass#
for face in firegeo_lod.faces:
    for v in face.vertices:
        v.point.mass = None     # py3d skips #Mass# for this LOD
```

### Check after assembling

Walk every LOD and make sure that only the Geometry LOD (resolution `1e13`) has mass and a `#Mass#` TAGG:

```python
for lod in model.lods:
    has_mass = any(p.mass is not None for p in (lod.points if hasattr(lod, "points") else []))
    if lod.resolution == 1e13:
        assert has_mass, "Geometry LOD must have #Mass#"
    else:
        assert not has_mass, f"LOD res={lod.resolution:.0e} must NOT have #Mass#"
```

End to end check, after binarizing: run `binarize.exe -always -addon=<dir> <src> <dst> <wildcard>` and read the centre of mass in the ODOL model info. It must not be `(0,0,0)` and must match the centre of mass of the Geometry LOD in the MLOD.

## Section replacement that keeps selections intact (added 2026-08-31)

py3d selection membership follows the identity of the `Point` and `Face` objects. It is not a stored map of integer indices. When replacing a section:

- change `lod.points[:]`, `lod.faces[:]` and `lod.facenormals[:]` in place; do not rebind those lists;
- keep every surviving `Point` and `Face` object, and prune deleted objects from every selection before writing;
- remap the integer fields that really are indices, `Vertex.point_index` and `Vertex.normal_index`;
- append new normals directly to `lod.facenormals` after synchronizing, not to a detached temporary list.

The writer's identity guard should fail loudly on a dead selection key. A successful write still needs a check that every index resolves and that surviving proxies have not moved at all.

## `validate()` ERR_AXIS_SELECTION_MISSING is a heuristic, not an engine rule (added 2026-09-28)

`[EXACT]` `py3d.P3D.validate()` flags every memory selection ending in `_axis` that has no visual selection of the same name (a heuristic carried over from `audit_p3d.py`). Several animations of the same bone with different axes cannot satisfy it: `model.cfg` links `axis=` and `selection=` independently, so there the finding is a false positive, not an engine rule. Measured 2026-09-28: renaming the axes from `clab_*_axis` to `axis_clab_*` took the model from 3 ERROR findings to 0.

`[DESIGN]` Name such axes `axis_<name>` to keep the validator quiet.

`/dayz-p3d-audit` runs the same check and reports CRITICAL for a `<name>_axis` with no `<name>` selection (`_shared/models/memory-points.md`); the same reading applies to its finding.

## Quads are stored as quads

An MLOD face holds up to four vertex slots, and py3d reads and writes faces of 3 or 4 vertices as they are (`Face.read` and `Face.write` accept only those two counts, and pad only the triangles). py3d therefore keeps quads through a round trip, and the quad output of a retopology can be written directly without triangulating it first. Two caveats: the viewer and inspector skills triangulate when they export to glTF, for display only, and whether Addon Builder keeps quads when it binarizes was not tested.

## Vehicle proxy constructor preflight (added 2026-08-31)

The defaults of `LOD.add_proxy(path, index, origin, rotation=None, scale=0.001)` describe a tiny, upright proxy for a worn item. They are not a verified convention for a vehicle proxy. For a scripted vehicle assembly, always pass `rotation` and `scale` explicitly, then measure the triangle that was written with `py3d.derive_proxy_frame()` against a control known to be good. Three measured vehicle controls used the frame rows `((-1,0,0),(0,0,1),(0,1,0))` and triangles at metre scale; the default identity frame differs by 180 degrees of yaw and its triangle is roughly 1000 times smaller. This was tested offline only: it does not replace checking the seat orientation in game. Vehicle proxies are vehicle work; see the vehicles pack (`_shared/vehicles/attachments-and-crew.md`).

## Visual faces carry both a texture and a material (added 2026-08-31)

A py3d builder must fill both `face.material` and `face.texture` on visual faces. A model with materials only can pass every structural offline gate and still render white, especially in models split into proxies, where `hiddenSelections` repaint the host but not its body proxies.

Enforce this per face, as an if and only if, for visual LODs only (`resolution < 1e4`):

```text
material != ""  <=>  texture == derive(material)
material == ""  <=>  texture == ""
derive(M) = replace \\materials\\ with \\textures\\ and .rvmat with _co.paa
```

Proxy triangles naturally fall in the empty and empty case. Penetration materials on non visual LODs may legitimately have an empty texture and stay outside this gate. Keep the casing of paths in the evidence, check that every referenced `.rvmat` and `_co.paa` exists on disk, and keep a negative fixture that renames one referenced texture and must turn the gate red.

The `derive` rule assumes the builder's own folder layout (`materials\` beside `textures\`); adapt it to the mod's layout.

## Budget ratios come from the geometry that ships (added 2026-08-31)

Do not extrapolate a budget of resolved vertices or normal triplets from a decimated mesh to a different source mesh. Edge collapse breaks normal sharing and can inflate the triplets per triangle. Measure the ratio on the exact geometry that will ship. When the source asset contains an authored LOD ladder, prefer that ladder and measure it instead of planning splits from a decimated stand in; this also keeps the rule that visual decimation is the user's call.

## Spawn remains an engine gate (added 2026-08-31)

A clean py3d reload, a digest, an index check, a winding check or a Geometry LOD comparison does not prove that a generated `.p3d` will spawn. Run `binarize` first to sort out capacity and other conversion failures, then require a spawn in game before calling the model ready (`/dayz-build-pbo`, then `/dayz-launch-test`). If conversion passes and the spawn still fails, use the batched LOD variant method (`dayz-p3d-audit/references/winding-diagnostics.md`, "Reusable bisection"): build a batch of variants that each drop or swap one LOD and spawn them all in one session to find the LOD at fault. File patching does not reload binary `.p3d` files.

## Sibling model frame gate (added 2026-08-31)

Before reusing a rotation offset across related models, run the sibling frame check (`dayz-p3d-audit/references/manual-checks.md`, "Sibling-model frame parity"): compare their Memory LOD points, and use the thin axis of the Geometry LOD as the mounting discriminator. A visual bounding box or a shared family name does not establish that two models were built in the same frame. Treat any permutation of axes as a different frame.
