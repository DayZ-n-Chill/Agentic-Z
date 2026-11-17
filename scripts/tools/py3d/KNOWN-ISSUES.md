# Known issues

This library was put through a deliberately adversarial audit in August 2026 —
several independent reviewers, each reproducing findings by executing code
rather than reading it. What follows is what that audit found and what is still
open. It is published in full, unflattering parts included, because a modelling
tool that hides its blind spots is worse than one that has none.

Fixed items are listed at the bottom.

---

## Do not use these as approval gates

The three issues below share one shape: **an instrument that cannot fail for the
reason you care about.** A clean result from any of them is not evidence.

### `save(verify=True)` does not verify geometry

`_verify_against` compares LOD counts, point/face counts, selection names and
total mass. It does **not** compare coordinates, UVs, winding, indices, normals,
flags, materials or textures.

Reproduced: two models identical except for one point at `(0,0,0)` vs
`(99,99,99)` — verify passes. It also accepts out-of-range point indices.

*Use it as a "the file is structurally re-readable" check, not as proof that
what you wrote is what you meant.*

### `python -m py3d diff` reports "equal" for materially different models

Same root cause. The same `(0,0,0)` vs `(99,99,99)` pair prints `total: 0` and
exits 0. Since 1.6.0 it does compare the UV set ids of every LOD, and since
1.7.0 the `#Selected#` tag, so neither a dropped UV set nor a dropped editor
selection is invisible to it; coordinates and UV values still are.

*Do not use `diff` to verify that an edit did what you intended.*

### `tools/audit_p3d.py` can print `ALL PASSED` when nothing was checked

The wrapper returns exit 0 and `OVERALL: ALL PASSED` when given no inputs, when
pointed at a directory that does not exist, and even after printing a read error
for a file it could not open. Warnings also end in exit 0.

*Check that the file count in its output is what you expected.*

---

## Data-loss risks

### Recipe JSON (`to_dict` / `from_dict`) is lossy — not a persistence format

- The Recipe classifier disagrees with `LOD.kind()`. A Visual LOD with
  `resolution=16` round-trips into a **ShadowVolume at 10000.0**, losing its
  textures, materials and UVs.
- `from_dict()` writes `#Mass#` into FireGeometry LODs, which `validate()` then
  correctly rejects — and which makes the binarizer bake a wrong centre of mass.
- Visual LOD resolutions are snapped to a canonical table, so two distinct
  visual levels can collapse onto one.
- Selection membership is recorded as indices into the original arrays and
  re-applied to a rebuilt, deduplicated array, so named selections on visual
  LODs can end up pointing at different geometry.
- Additional UV sets (`Vertex.uv_sets`) are not part of the Recipe schema;
  `from_dict()` rebuilds a model with set 0 only.

*Use Recipe for inspection. Use the `.p3d` itself for persistence.*

### `write()` straight to an open file can destroy the previous file

The guards validate **inside** `write()`, by which point `open(path, "wb")` has
already truncated the target. The resulting partial file is unreadable.

`save()` is **not** affected — it writes to a temporary file first and the
original survives intact. Verified both ways.

*Prefer `save()`. Reserve `write()` for streams you own.*

### `transform()` applies the matrix twice to points shared between LODs

It iterates per LOD and mutates `Point` objects in place, so a point present in
two LODs is transformed once per LOD. `(0,1,0)` ends up at `(0,-1,0)` instead of
`(0,0,-1)`, and `save(verify=True)` accepts the result. A `facenormals` list
shared between LODs is mapped once per LOD the same way. `blender_to_dayz()`,
built on `transform()`, refuses both cases with `ValueError` before changing
anything; `transform()` itself still does not.

### `make_double_sided()` breaks proxies

The generated twin face is added to *every* selection that contained the
original, so a proxy selection goes from one face to two and
`get_proxies(strict=True)` / `align_proxy()` then raise.

*Run it before adding proxies, or on LODs that have none.*

---

## Silent wrong answers

- **Selection weights below `w ≈ 0.00196` cannot be written.** Validation accepts
  any float in `(0,1)`, but the encoder computes `round((1-w)*255)+1`, which
  overflows a byte and raises `ValueError` at write time.
- **`set_selection(name, face_idx=0)` silently produces an empty selection**,
  because `face_idx or ()` treats the integer `0` as empty. `face_idx=[0]` works.
- **A selection whose name contains `#` corrupts the file.** Writing is allowed;
  on read, a name like `#EndOfFile#` terminates the tag loop early, leaving the
  LOD with a garbage resolution and no selections.
- **`validate()` raises `IndexError` on out-of-range point indices** instead of
  reporting a finding, so a corrupt file crashes the validator.
- **N-gons (>4 vertices) can be written but not read back.** `save(verify=True)`
  correctly refuses; `verify=False` leaves an unreadable file.
- **`Selection.read` ignores the declared `num_bytes`** and the MLOD version
  field is ignored on read and always written as 257.
- **Watertight only flags edges used once**, so an edge shared by three or more
  faces passes as watertight.
- **All format validation uses bare `assert`**, so running under `python -O`
  disables it — and because the asserts also advance the stream, valid files
  fail to load. The user-facing error is an empty `AssertionError`.
- **Floats are read/written in native byte order** while integers are explicit
  little-endian. Harmless on x86; wrong on a big-endian host.

## Compatibility

- **`Selection(list(lod.points), list(lod.faces))` now raises** where upstream
  accepted it and wrote byte-identical output. The guard tests list *identity*
  when the bug it targets is one of *length*. This is the fork's one true
  behavioural regression against upstream.
- **`py3d.BLENDER_TO_DAYZ` is deprecated (1.8.0).** It keeps its value, the
  det=+1 rotation now also published as `ROT_X_NEG90`, and every read of it
  raises a `FutureWarning`. Because the warning comes from a module
  `__getattr__`, the name is no longer in the module's namespace:
  `from py3d import *` does not bring it in any more. `from py3d import
  BLENDER_TO_DAYZ` still works, and warns. Listing it in an `__all__` would
  bring it back, but then every `from py3d import *` would warn, twice, and
  fail under `-W error`, even in code that never uses the name.

## Blender → DayZ: what was measured

Measured 2026-10-01 on DayZDiag 1.29.163709, so nobody has to re-run it. One
chiral model — an "F" in relief on a plate, authored in Blender space with
outward counter-clockwise faces and outward normals, a single visual LOD of 48
triangles — was written three ways, binarized with AddonBuilder and looked at
in game:

| variant | how it was written | MLOD sha256 | in game |
|---|---|---|---|
| B | `blender_to_dayz()` | `f1be491df6304534...` | solid, the F reads correctly |
| A | `transform(ROT_X_NEG90)`, every face reversed, every normal negated | `b08372a6248d826a...` | solid but mirrored |
| C | `transform(ROT_X_NEG90)` alone | `ac5f0f77f6d93db9...` | inside-out and mirrored |

`tests/test_s7_blender_to_dayz.py` rebuilds that model and asserts all three
digests, so its chirality and winding checks run on the very bytes that were
binarized. A and B differ only in the matrix, and A passes the winding
checks - vertex order against normals, inward per box - on all 48 faces.

A second probe the same day, binarized the same way and read with an ODOL
reader independent of this library, covered what the first left out:

- **Collision.** The F plate with Geometry, ViewGeometry and FireGeometry LODs,
  one convex component per box. In the binarized file every component of the
  B and A variants winds like vanilla `Motorbike_02` (outward, 48 of 48 per
  LOD) and C the other way (0 of 48). In game, `scene_raycast` north to south
  and south to north hit B and A in `geom`, `view` and `fire`, missed C in all
  three, and hit a vanilla container used as control.
- **Proxies.** Three static proxies drawn in Blender as canonical raw
  triangles (identity, yaw +90, yaw +90 after a 30 degree tilt), converted with
  the model: their binarized engine frames equal the ones worked out by hand
  (aside = M x, up = M z, dir = M y, M the swap) and the ones
  `add_proxy(space="engine")` writes for them; the same matrices through
  `add_proxy(space="raw")` in DayZ space do not. In game the proxied F stood
  in the pose drawn in Blender, and read correctly where it faced the camera
  (the identity and the yawed proxy). The two binarized parents, Blender-drawn
  proxies converted and `add_proxy(space="engine")`, are byte-identical files.

Crew and wheel proxies of a driven vehicle: an equivalence of the proxy
frame, not a drive. Drawn as a canonical raw triangle with the identity frame
(the one vanilla `Motorbike_02` gives its crew and wheels, and one of the
three poses above), such a proxy comes out of binarize as
`add_proxy(space="engine")` writes it, and that engine-space path is the one
a py3d-built motorbike was driven with in game (2026-09-23: all three
variants started and drove, one up to 137 km/h). That covers the proxy frame
only: the vehicle's selections, bones, model.cfg bindings and LODs still have
to match a working model. And a frame is not a pose: on the same motorbike a
crew proxy tilted on purpose came out of binarize with exactly the frame asked
for, and in game the rider turned to the left instead of leaning forward, so
for crew only the identity frame is known to work. No vehicle was driven
through `blender_to_dayz` itself.

Not covered, and not claimed: proxies drawn with another convention or as
ambiguous (isosceles) triangles, crew proxies with a frame other than the
identity, proxies as a dedicated server reads them, player collision (only
raycasts), and any model built partly in DayZ space before the conversion.

---

## What `#Selected#` is worth

Measured 2026-09-02, so nobody has to re-run it.

**The game never sees it.** Five variants of `sedanwheel_mlod.p3d` (8 LODs)
differing *only* in the tag were binarized with
`binarize.exe -norecurse -always -silent` and the ODOL hashed:

| variant | change to the MLOD | ODOL sha256 |
|---|---|---|
| `a_none` | none (negative control) | `620d4fec1646fcdb...` |
| `a_none2` | none, second run (determinism control) | `620d4fec1646fcdb...` |
| `a_zero` | `#Selected#` all `0x00`, all 8 LODs (+5,167 B) | `620d4fec1646fcdb...` |
| `a_ones` | `#Selected#` all `0x01`, all 8 LODs (+5,167 B) | `620d4fec1646fcdb...` |
| `a_geo` | one point moved 1 cm (positive control) | `610ae73593eed77a...` |
| `a_tex` | texture cleared on 2,092 faces (positive control) | `ebc0c0dcc4ee18e4...` |

Neither the presence nor the content of the tag reaches the ODOL. The two
positive controls are not optional: three identical hashes are otherwise
indistinguishable from "binarize never read my file".

**Object Builder 2.3.0.159800 does not require it, but does keep it.** A
4-LOD file stripped of every `#Selected#` opens with no error, keeps all four
LODs, and saves back at the same size *without* the tag — Object Builder does
not invent it. The same file with the tag saves it back with the payload
byte-for-byte (1, 2 and 393 non-zero bytes across its three LODs). And
BI-authored files carry it unevenly: `DayzSkeleton.p3d` has none at all, and
the visual LOD of `WeaponSpecialLODs.p3d` has none while its four special
LODs do. It is the selection the author left behind, nothing more.

**Object Builder does not preserve tag order either.** Round-tripping a
BI-authored file through it moves `#UVSet#` from the front to the back — the
same order this library writes. So a file that has been through Object
Builder round-trips here byte for byte; one straight from BI may not, and
that is not a defect this library can fix without also diverging from the
editor.

**`binarize.exe` is not byte-deterministic on every model.** Three runs of an
unmodified `WeaponSpecialLODs.p3d` produced three different ODOL
(`2b4c12ad...`, `b3aa67aa...`, `7113b139...`). The files were the same size
with the same multiset of strings; only the material table order differed
(`ak12.rvmat` and `ris.rvmat` swapped). That model references assets which do
not resolve (`Material not loaded: dz\data\data\penetration\metalplate.rvmat`),
and the order they are resolved in leaks into the output. **Any ODOL A/B test
needs a same-input repeat run as its control**, per model — without it, this
noise reads as signal.

## Fixed

- **`validate()` flagged a component name that works and missed lost
  collision in View and Fire.** Up to 1.8.0 `ERR_COMPONENT_NAMING` ran on the
  Geometry LOD alone and fired on a lowercase `component01` ("Engine requires
  'Component01' (uppercase C); collision silently fails"). In game (DayZDiag
  1.29.163709, 2026-10-02) `component01` collided exactly like `Component01`
  in `geom`, `view` and `fire` rays, the physics ray and a walking player,
  packed unbinarized and binarized, and binarize writes both names as
  `component01`; a box with no component in its Geometry, View and Fire LODs
  took no ray in any of them, let the player through, and no log line said
  so. From 1.9.0 the error flags any of those three LODs that has faces
  outside its proxy triangles and no selection whose name starts with
  `component`, and ignores the case of the name. A LOD missing a component while the others have one was
  not measured.
- **The documented Blender → DayZ path mirrored the model.** Up to 1.7.0,
  `BLENDER_TO_DAYZ` was the det=+1 rotation `(x,y,z) -> (x,z,-y)` and
  `p3d.transform(py3d.BLENDER_TO_DAYZ)` was the documented usage. Blender is
  right-handed and DayZ left-handed, so every det=+1 map between the two
  mirrors the model, and that call alone also leaves it inside-out (variant C
  above). Symmetric test models hide a mirror, which is how it lasted. Now
  `blender_to_dayz()` applies the det=-1 reflection `(x,y,z) -> (x,z,y)`,
  keeps the face order and negates the normals; the old constant is
  deprecated with its value unchanged (see Compatibility).
- **Additional UV sets were dropped on save, and point-only LODs lost their
  `#UVSet#` tag.** `LOD.read` discarded every `#UVSet#`, and `LOD.write`
  emitted set 0 only, and only when the LOD had faces. Measured on a skinned
  body with two UV sets: 4,761,261 → 4,409,836 bytes and the second set gone;
  the Memory LOD of a BI-authored file lost its 4-byte `#UVSet#`. Sets beyond
  the first now live in `Vertex.uv_sets` and are written back in id order; a
  LOD without faces gets the empty tag Object Builder writes; a payload whose
  length does not match the faces, or a set id declared twice, raises on
  read. Still not preserved: the source file's tag order — which Object
  Builder does not preserve either (see below).
- **`#Selected#` was dropped on save.** The tag holds the editor's current
  selection — one byte per point followed by one per face, a named
  selection's layout — and `LOD.read` fell through to the tag loop's
  default, which reads the payload and throws it away. Re-saving a
  BI-authored file lost it: `InfectedSpecialLODs.p3d` −863 B (LOD1 −45,
  LOD2 −409, LOD3 −409) and `WeaponSpecialLODs.p3d` −202 B (LOD1 −30,
  LOD2 −48, LOD3 −60, LOD4 −64), which was the whole remaining delta. It
  now lives in `LOD.selected` as a `Selection` and is written back with its
  payload intact, in the slot Object Builder writes it in (after
  `#SharpEdges#`, before the named selections). A payload whose length does
  not match the LOD's counts, or a second `#Selected#` in one LOD, raises
  on read. See *What `#Selected#` is worth* for what that fidelity buys.
- **Infinite hang on an unterminated string.** `_read_asciiz` looped forever
  when a file reached EOF without a NUL byte — the process hung with no
  traceback, which no caller could catch. Inherited from upstream; a truncated
  `.p3d` is the normal way to hit it. Now raises, naming the offset.
- **The validator recommended a fix that corrupts quads.** `ERR_WINDING_INVERTED`
  advised swapping `vertices[1]` and `vertices[2]`, which inverts a triangle but
  turns a quad `[0,1,2,3]` into `[0,2,1,3]` — a crossed face. It now recommends
  `face.vertices.reverse()` and warns against the swap.
- **`ERR_WINDING_INVERTED` told the reader to reverse healthy LODs.** The
  relative check compares the share of faces wound outward from each LOD's
  centroid and files the finding on the collision LOD, and its message told the
  reader to reverse every face of that LOD. With the Visual LOD turned
  inside-out, faces and normals together, it fired on the three healthy
  collision LODs of a clean multi-LOD model and nowhere else; reversing them
  traded it for `ERR_WINDING_VS_NORMALS`, and negating their normals too left
  `validate()` at `[]` with every LOD wound outward. The message now names the
  Visual LOD it compares against (the one of lowest resolution, by index), says
  the two LODs disagree on which way is out, not which one is wrong, and gives
  for both the winding-first steps of `ERR_WINDING_VS_NORMALS`, which leave a
  part that reads right as it is; a part those steps cannot read leaves the
  finding unresolved.
- **Globally inverted winding was invisible.** The only winding check was
  relative to the Visual LOD, so inverting *every* LOD — precisely what a Z-up to
  Y-up export does — left the model self-consistent and `validate()` returned
  `[]`. Two order-independent signals were added: agreement between winding and
  each face's own declared normal, and edge-traversal coherence between
  neighbouring faces. Neither assumes convexity nor a handedness convention.
  Measured at 100% on 15 vanilla LODs (1274/1274 faces), where the old
  centroid-based measure ranged from 0% to 31.8% without meaning anything.
- **The relative check used the wrong reference LOD** — the first visual LOD in
  file order rather than the one with the lowest resolution, so LOD ordering on
  disk changed the verdict.
