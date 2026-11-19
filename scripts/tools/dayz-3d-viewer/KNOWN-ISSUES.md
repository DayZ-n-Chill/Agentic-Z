# Known issues

Gaps in the converter that ships in this directory, each checked against
the current sources. They are **not** fixed here; that is a later task.
A clean conversion is not evidence that any of them is gone.

## Present

### SWIZ is stored and never applied

`PAAFile._read_tags` records a `SWIZ` tag when the file has one
(`paa_to_png.py`, `_read_tags`). `decode_mipmap` never reads
`self.tags["SWIZ"]` and never swizzles channels. Normal maps that
rely on the BI swizzle therefore leave the converter with the stored
channel order.

*Present. Do not treat a decoded `_nohq` PNG as engine-correct until
the swizzle is applied.*

### Proxy triangles export as visible geometry

`extract_lod_geometry` walks every face in the chosen LOD
(`p3d_to_gltf.py`). It does not skip selections whose name matches
`proxy:…`. A proxy triangle therefore becomes a primitive in the
`.glb` and a mesh in the embedded viewer.

*Present. Hide or strip proxies before conversion if the viewer must
match the in-game mesh.*

### Resolution 1100 (ViewPilot) is not a view-pilot kind

`classify_lod` (`p3d_to_gltf.py`) follows the kinds of
`classify_lod_resolution` in `scripts/tools/py3d`: visual below 1000,
`shadowvolume` in `[10000, 20000)`, and the special LODs from geometry
to fire geometry. ViewPilot at 1100 is none of these, so it is
reported as `unknown_1100.0`, as py3d returns `None` for it.
`find_best_visual_lod` only accepts types that start with `"visual"`,
so a 1100 LOD is not chosen as the mesh.

*Present as an unknown kind. Not treated as the visual mesh.*

## Out of scope here

- PNG → PAA encoding.
- Applying parsed `_nohq` / `_smdi` stages in the Three.js viewer.
- Multiple-LOD switching in the HTML.
- ODOL input (use a debinarizer first).
