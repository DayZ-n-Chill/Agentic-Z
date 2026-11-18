# py3d assembly rules

What to watch when you write or edit a `.p3d` with py3d beyond the basic API: which py3d to install, where mass may sit, how to replace part of a LOD without breaking its selections, what the validator's axis finding means, and which checks only Binarize and a spawn in game can make. The API itself is in `py3d-generation.md`; notes on reading an MLOD are in `_shared/py3d-mlod-notes.md`.

These are measurements of the py3d library and of the Binarize and spawn steps on mod models. Vanilla models on `P:\` are binarized (`P:\DZ\gear\camping\wooden_case.p3d` starts with the bytes `ODOL`), so none of it is checked there.

## Which py3d

Use the py3d that ships in this repo at `scripts/tools/py3d`, version 1.6.0 or later. It is an MLOD reader and writer with guards against writing a broken file, the DayZ LOD values, `validate()`, proxies, the recipe helpers and the command line `python -m py3d`.

```cmd
python -m pip install -e scripts\tools\py3d
python -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,6,0), (py3d.__version__, py3d.__file__)"
```

- Never run `pip install py3d`: the PyPI package of that name is an unrelated point cloud library.
- Do not install any other MLOD library that imports as `py3d`. It has none of these guards or helpers, and one environment holds only one package of that name, so uninstall such a copy first; the assert above names the one in use. `/dayz-p3d-audit` uses this same py3d (its `requirements.txt` names `scripts/tools/py3d`).

## Mass only on the Geometry LOD

On every LOD that is not the Geometry LOD (Fire Geometry `7e15`, View Geometry `6e15`, LandContact `2e15`, Memory `1e15`, shadow, or a visual LOD below 1000), set `point.mass = None` on every point. Never set `point.mass = 0.0`.

py3d writes a `#Mass#` TAGG whenever any point of a LOD has a mass that is not `None`, `0.0` included. Binarize then bakes that LOD's mass (a sum of 0), so the binarized model has its centre of mass at `(0,0,0)` and no inertia. `ECE_PLACE_ON_SURFACE` puts a vehicle at the height of its centre of mass, so it spawns underground and the physics throws it out while pushing it clear. Measured on a mod vehicle; removing LODs one at a time isolated the fault. This matches `named-properties.md`: physics uses the point masses of the Geometry LOD.

```python
# Wrong: writes a #Mass# TAGG of zeros into Fire Geometry, and the centre of mass bakes to 0
for face in firegeo_lod.faces:
    for v in face.vertices:
        v.point.mass = 0.0

# Right: no #Mass# TAGG; Binarize uses the Geometry LOD's
for face in firegeo_lod.faces:
    for v in face.vertices:
        v.point.mass = None
```

After assembling, make sure only the Geometry LOD (`1e13`) has mass:

```python
for lod in model.lods:
    has_mass = any(p.mass is not None for p in lod.points)
    if abs(lod.resolution - 1e13) < 1e11:      # resolutions read back as float32
        assert has_mass, "the Geometry LOD needs #Mass#"
    else:
        assert not has_mass, f"LOD {lod.resolution:.0e} must not have #Mass#"
```

Then binarize (`binarize.exe -always -addon=<dir> <src> <dst> <wildcard>`) and read the centre of mass in the binarized model info: it must not be `(0,0,0)` and must match the Geometry LOD's centre of mass in the MLOD (`py3d-collision-and-mass.md`).

## Replacing part of a LOD without losing selections

py3d ties selection membership to the `Point` and `Face` objects themselves, not to a stored list of indices. When you replace part of a LOD:

- change `lod.points[:]`, `lod.faces[:]` and `lod.facenormals[:]` in place; never bind those names to new lists;
- keep every surviving `Point` and `Face` object, and remove deleted ones from every selection before writing;
- remap the fields that really are indices, `Vertex.point_index` and `Vertex.normal_index`;
- append new normals straight to `lod.facenormals` after syncing, not to a separate temporary list.

The writer fails loudly on a selection that holds a dead object. A clean write still needs a check that every index resolves and that surviving proxies have not moved at all.

## The validator's axis finding is a guess

`py3d.P3D.validate()` reports `ERR_AXIS_SELECTION_MISSING` for every memory selection ending in `_axis` that has no visual selection of the same name without `_axis`. That is a naming guess carried over from `audit_p3d.py`, not an engine rule: `model.cfg` names `axis=` and `selection=` separately, so several animations of one bone on different axes can never satisfy it. On one mod model, renaming the axes from `clab_*_axis` to `axis_clab_*` took it from 3 ERROR findings to none; name such axes `axis_<name>` to keep the validator quiet.

`/dayz-p3d-audit` passes this finding on as a WARNING when it runs without a `model.cfg`, marked as guessed from the axis name. With `--model-cfg` it drops the guess and checks the selection and axis each animation names instead (`fork_findings` in `skills/dayz-p3d-audit/scripts/audit_p3d.py`; `memory-points.md`).

## Quads stay quads

An MLOD face holds up to four vertices, and py3d reads and writes faces of 3 or 4 vertices as they are: `Face.read` accepts only those two counts, and `Face.write` pads triangles without checking the count, so a builder must keep every face at 3 or 4. Quads survive a round trip, and the quad output of a retopology can be written without triangulating it first. The viewer and inspector tools triangulate when they export to glTF, for display only. Whether Addon Builder keeps quads when it binarizes was not tested.

## Vehicle proxies need their frame and scale set

The defaults of `LOD.add_proxy(path, index, origin, rotation=None, scale=0.001)` describe a tiny, upright proxy for a worn item, not a checked setting for a vehicle. In a scripted vehicle build, always pass `rotation` and `scale`, then measure the written triangle with `py3d.derive_proxy_frame()` against a proxy known to work. Three working vehicle proxies used the frame rows `((-1,0,0),(0,0,1),(0,1,0))` with triangles at metre scale. Those rows are the engine's identity frame written as a raw frame (`py3d.proxy_frame_to_engine` maps them to the identity, so `add_proxy(..., space="engine")` with the identity rotation builds the same triangle). The default raw identity frame differs from them by a half turn about the (0,1,1) diagonal, not by a turn about the up axis, and its triangle is about 1000 times smaller. This was checked offline only and does not replace checking the seat in game; vehicle proxies are vehicle work (`_shared/vehicles/attachments-and-crew.md`, `proxy-frames.md`).

## Visual faces carry both a texture and a material

A py3d builder must fill both `face.material` and `face.texture` on visual faces. A model with materials only can pass every offline structure check and still render white, above all a model split into proxies, where `hiddenSelections` repaint the host but not its body proxies.

Check it per face on the visual LODs only (`resolution < 1e4`), both ways:

```text
material != ""  if and only if  texture == derive(material)
material == ""  if and only if  texture == ""
derive(M) = M with \materials\ replaced by \textures\ and .rvmat by _co.paa
```

Proxy triangles fall in the empty and empty case. Penetration materials on collision LODs may rightly have no texture and stay outside the check. Keep path casing as written, check that every `.rvmat` and `_co.paa` exists on disk, and keep a test model with one texture renamed that must make the check fail. `derive` assumes a `materials\` folder beside a `textures\` folder; adapt it to the mod's layout.

## Budgets come from the geometry that ships

Do not carry a budget of resolved vertices or normal triples from a decimated mesh over to a different source mesh. Edge collapse breaks normal sharing and can raise the triples per triangle. Measure the ratio on the exact geometry that will ship. When the source asset has its own LODs, use and measure those instead of planning splits from a decimated stand in; that also keeps visual decimation the user's call.

## A spawn in game is still required

A clean py3d reload, a hash, an index check, a winding check or a Geometry LOD comparison does not prove a generated `.p3d` will spawn. Run Binarize first to rule out capacity and other conversion failures, then require a spawn in game before calling the model ready (`/dayz-build-pbo`, then `/dayz-launch-test`). If conversion passes and the spawn still fails, build a batch of variants that each drop or swap one LOD and spawn them all in one session to find the LOD at fault (`dayz-p3d-audit/references/winding-diagnostics.md`, "Reusable bisection"). File patching does not reload binary `.p3d` files.

## Models of one family may not share a frame

Before reusing a rotation offset across related models, compare them (`dayz-p3d-audit/references/manual-checks.md`, "Sibling-model frame parity"): compare their Memory LOD points, and use the thin axis of the Geometry LOD to tell how each is mounted. A visual bounding box or a shared family name does not show that two models were built in the same frame, and any swap of axes is a different frame.
