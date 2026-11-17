# Known issues

Gaps measured against the converter that ships in this directory. They
were first recorded as LL-124 and re-checked in the current sources
(grep, not assumption). They are **not** fixed here; that is a later
task. A clean conversion is not evidence that any of them is gone.

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

`classify_lod` (`p3d_to_gltf.py`) returns `"shadow"` for every
resolution in `[10, 15000)`, which includes ViewPilot at 1100. It
does **not** currently label 1100 as a visual LOD:
`find_best_visual_lod` only accepts types that start with `"visual"`,
so a 1100 LOD is not chosen as the mesh. The pack py3d fork
(`classify_lod_resolution`) returns `None` for 1100.

The original LL-124 wording was "classified as a visual LOD". That
specific label is no longer what the function returns. The
misclassification itself is still present: 1100 is `shadow`, not a
ViewPilot kind.

*Present as a wrong kind. Not treated as the visual mesh.*

## Out of scope here

- PNG → PAA encoding.
- Applying parsed `_nohq` / `_smdi` stages in the Three.js viewer.
- Multiple-LOD switching in the HTML.
- ODOL input (use a debinarizer first).
