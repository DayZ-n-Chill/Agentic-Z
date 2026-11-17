# py3d-dayz

Read and write Arma / DayZ `.p3d` models in their unbinarized **MLOD** form,
from Python. No dependencies, pure stdlib.

This is a maintained fork of [KoffeinFlummi/py3d](https://github.com/KoffeinFlummi/py3d)
by Felix "KoffeinFlummi" Wiegand (MIT, last released in 2018). The original is a
compact, correct MLOD codec and it is still the foundation of this code — its
copyright notice is preserved verbatim in [LICENSE](LICENSE).

> **The importable module is still `py3d`.** Only the *distribution* name
> differs, because `py3d` on PyPI is an unrelated 3D library. So `import py3d`
> keeps working, and `py3d.IS_DAYZ_FORK` lets a script assert it got this one.

## Why a fork

Upstream is a minimal codec: it assumes well-formed input and trusts the caller.
That is a reasonable design, but in a modding pipeline the input is frequently
*not* well formed — a half-written export, a mesh straight out of Blender, a
selection rebuilt by hand. This fork adds two things on top:

1. **Guards.** Paths that used to corrupt a `.p3d` silently, or blow up much
   later with an unrelated error, now fail early with a message that names the
   offending selection, property or LOD.
2. **A DayZ model validator.** `P3D.validate()` returns a list of `Finding`s
   about things that are legal MLOD but wrong for DayZ.

## Install

```bash
pip install git+https://github.com/willy92wins/py3d-dayz
```

Verify you imported the right library:

```python
import py3d
assert py3d.IS_DAYZ_FORK
```

## Quick start

```python
import py3d

with open("crate.p3d", "rb") as f:
    model = py3d.P3D(f)

for lod in model.lods:
    print(lod.kind(), lod.resolution, len(lod.points), len(lod.faces))

for finding in model.validate():
    print(finding.severity, finding.code, finding.msg)

model.save("crate_out.p3d")          # atomic write + verify + optional backup
```

Command line:

```bash
python -m py3d info     model.p3d    # LODs, counts, selections, memory points
python -m py3d validate model.p3d    # validator findings; exit 1 if any ERROR
python -m py3d diff     a.p3d b.p3d  # structural comparison
```

## What this fork adds

**Correctness guards**
- Selection weights validated on write, naming the selection that is wrong.
- `#Property#` keys/values over 63 UTF-8 bytes raise instead of being silently
  truncated (a 64-byte value loses its NUL terminator and corrupts the reader).
- Stale selections — bound to lists that were replaced — raise instead of
  silently losing their membership.
- `P3D.save(path, verify=True, backup_dir=...)`: atomic write, reopened and
  re-parsed before replacing the original.

**DayZ knowledge**
- Canonical LOD resolutions and `LOD.kind()` / `P3D.get_lod("geometry")`.
  Note DayZ does **not** use the Arma-3-era `e13` ids for FireGeo/ViewGeo:
  they are `7e15` and `6e15`. Getting this wrong means bullets pass through
  your model.
- `P3D.validate()` reports a Geometry, View or Fire LOD with faces but no
  `ComponentNN` selection (in game a model with no component in any collision
  LOD collides with nothing, and nothing logs it; one LOD missing it alone was
  not measured), a closed part left out of every component of such a LOD (in
  game two such parts took no ray in the LODs they were left out of, also
  beside covered parts: a box left out of all three, a lever left out of
  Geometry and Fire; one LOD alone was not measured), `#Mass#` outside the
  Geometry LOD, non-watertight collision, degenerate faces, memory-point
  structure, winding problems, and more. The case of a component's name is
  not checked: `component01` collided in game exactly like `Component01`.

**Editing helpers**
- `bbox`, `triangulate`, `set_selection`, `set_total_mass`, `set_memory_point`,
  `make_double_sided`, `transform`.
- `blender_to_dayz(model)`: a model authored in Blender, converted to DayZ's
  frame without mirroring it. See [Blender → DayZ](#blender--dayz).
- A full proxy lifecycle: `add_proxy` / `get_proxies(strict=True)` /
  `align_proxy` / `remove_proxy`, with explicit raw↔engine frame conversion.

**Format fidelity**
- Every `#UVSet#` beyond the first is read into `Vertex.uv_sets` and written
  back in id order. Upstream dropped them on save: a skinned body that carried
  two UV sets lost the second one (4,761,261 → 4,409,836 bytes).
- A LOD without faces (Memory, LandContact) gets the empty `#UVSet#` tag that
  Object Builder writes and BI-authored files carry; upstream omitted it.
- The editor's current selection (`#Selected#`) is read into `LOD.selected` and
  written back with its payload intact, in the slot Object Builder writes it in
  (after `#SharpEdges#`, before the named selections). Upstream dropped it:
  re-saving `WeaponSpecialLODs.p3d` lost 202 bytes and `InfectedSpecialLODs.p3d`
  863. It is editor state, not model data -- `binarize.exe` discards it
  (measured; see KNOWN-ISSUES) -- but Object Builder preserves it verbatim, so
  dropping it silently discards the user's selection.
- `save(verify=True)`, `info` and `diff` compare the UV set ids of every LOD and
  the presence and membership of `#Selected#`.

**Write contract.** For valid canonical input the bytes written are identical to
what upstream writes, with two deliberate exceptions: a LOD without faces gets
the empty `#UVSet#` tag (17 bytes) that upstream omits, and `#Selected#` is
written back where upstream dropped it. Where upstream would have corrupted the
file or crashed later, this fork raises instead. A file written by Object
Builder survives a read/write cycle byte for byte; a file written by BI may not,
because tags are written in this library's order -- which is the order Object
Builder itself writes, and not always the source file's.

## Blender → DayZ

```python
import py3d

model = py3d.P3D()
# ... fill model.lods with points, faces and normals exactly as Blender has
# them: Blender coordinates, faces counter-clockwise seen from outside,
# outward normals ...
py3d.blender_to_dayz(model)   # once, before adding anything built in DayZ space
model.save("thing.p3d")
```

Blender is right-handed (Z up, front at −Y) and DayZ left-handed (X east, Y up,
Z north). A conversion that keeps the shape is therefore a reflection in the
numbers, `(x, y, z) → (x, z, y)`, determinant −1. That reflection on its own
already puts the faces in the MLOD order — vertex-order cross product pointing
inward — so `blender_to_dayz` keeps every face's vertex order and only negates
the normals, which MLOD also stores pointing inward. Measured in game on
2026-10-01 (DayZDiag 1.29.163709) with one chiral model, an "F" in relief on a
plate, written three ways and binarized with AddonBuilder:

| how the model was written | in game |
|---|---|
| `py3d.blender_to_dayz(model)` | solid, the F reads correctly |
| `model.transform(py3d.ROT_X_NEG90)`, then every face reversed and every normal negated | solid but **mirrored** |
| `model.transform(py3d.ROT_X_NEG90)` alone — the usage this README gave up to 1.7.0 | inside-out **and** mirrored |

The mirrored model passes the winding checks — vertex order against normals,
inward per component — so only an asymmetric feature shows the mirror.

Measured the same day with the same map:

- **Collision LODs.** Geometry, ViewGeometry and FireGeometry converted with
  `blender_to_dayz` register raycasts in all three modes, from both sides;
  after `transform(ROT_X_NEG90)` alone they register none.
- **Proxies.** `blender_to_dayz` moves proxy triangles like any other face. A
  proxy drawn in Blender as this library's canonical raw triangle — what
  `add_proxy(space="raw")` builds in Blender coordinates — comes out of
  binarize with the same engine frame as `add_proxy(space="engine")` given the
  matching rotation, and renders in the pose it had in Blender (static proxies;
  identity, a yaw and a tilted yaw). The binarized file is byte-identical to
  the one `add_proxy(space="engine")` gives, the path a py3d-built motorbike
  was driven with in game, so a crew or wheel proxy drawn this way with the
  identity frame gets the frame that works there. That is the frame only, not
  the rest of the vehicle, and no vehicle was driven through this conversion
  (KNOWN-ISSUES has the limits). Proxies drawn another way get whatever frame
  their triangle implies: check those in the binarized file against a model
  that works.

**Migrating from `py3d.BLENDER_TO_DAYZ`.** Up to 1.7.0 this README gave
`model.transform(py3d.BLENDER_TO_DAYZ)`, the det=+1 rotation `(x, z, −y)`, as
the Blender → DayZ step. It mirrors the model. From 1.8.0:

- geometry authored in Blender: call `py3d.blender_to_dayz(model)` instead;
- code that needs the rotation itself — for instance to undo a det=+1 export
  `(x, −z, y)` from DayZ to Blender, where the mirror cancels out — uses
  `py3d.ROT_X_NEG90`, the same matrix under a name that says what it is.

`py3d.BLENDER_TO_DAYZ` still holds that same matrix, so no model changes shape
behind your back, and every read of it raises a `FutureWarning` that says the
above.

## Winding: read this before trusting any validator

The single most common way to break a DayZ model is a Blender (Z-up) to DayZ
(Y-up) export whose face order or normal sign does not match its axis map.
Faces in the wrong order make the texture visible only from *inside*, and
raycasts pass through; normals with the wrong sign leave the model solid but
shade it wrong (lit inverted, measured on a character). (The other common way,
a mirrored model, is invisible to every check below; see
[Blender → DayZ](#blender--dayz).)

This fork checks winding two ways:

- **Absolute** (`ERR_WINDING_VS_NORMALS`): does each face's winding agree with
  its own declared normal? Both vectors live in the same space, so this is
  immune to the left-handed/right-handed confusion.
- **Relative** (`ERR_WINDING_INVERTED`): is a collision LOD wound the opposite
  way from the Visual LOD? The reference is the visual LOD of lowest
  resolution, which the message names by index: `get_lod("visual")` returns
  the first in file order, which need not be it. The check compares the share
  of faces wound outward from each LOD's centroid, a test that assumes convex
  geometry, and files the finding on the collision LOD whichever of the two is
  wrong.

The relative check alone **cannot** see a model where *every* LOD is inverted —
everything is consistent with everything else — which is why the absolute
check exists. The absolute check cannot see faces and normals turned
*together*: `transform(ROT_X_NEG90)` alone, which rendered inside-out in game
(the table above), agrees on 100 % of its faces and `validate()` returns `[]`.

`ERR_WINDING_VS_NORMALS` says that winding and normals **disagree**, not which
of the two is wrong, and the two cases need opposite fixes. In a DayZ MLOD the
vertex-order cross product `cross(v1 − v0, v2 − v0)` and the stored normals both
point away from the side meant to be seen: inward on a solid, as
`blender_to_dayz` writes them. So settle the winding first, with the normals
left alone, and only then fix the normals against it:

1. **Winding, visual LOD**, per closed shell: a shell whose every edge is shared
   by exactly two of its faces. An open sheet, or a double-sided part whose
   faces come with reversed twins, has no inside and is left out.
   - Make the shell coherent. Two faces that run a shared edge the same way
     disagree (`WARN_WINDING_EDGE_INCOHERENT`). Flood-fill the shell across its
     shared edges into the groups of faces that agree with each other, and turn
     the vertex order of one group, normally the smaller. Which one does not
     matter, because the next step decides the direction of the whole shell;
     and its normals stay as they are, because the minority can be the side
     that was right.
   - Read its signed volume by winding: the sum of `dot(v0, cross(v1, v2)) / 6`
     over the fan triangles of its faces, in the file's own coordinates.
     Negative on a solid meant to be seen from outside, positive on a room
     meant to be seen from inside. With the other sign,
     `face.vertices.reverse()` on every face of the shell. Never decide on the
     sum over the whole LOD, which can hide an inverted part, nor on a shell
     that is not coherent yet: one reversed face can leave its sum negative.
2. **Winding, collision LODs**, per component: `face.vertices.reverse()` on
   every face whose cross product points outward, against face centroid minus
   component centroid. The test assumes a convex component, which Geometry
   components must be; on a concave one (a ring, an L) it reads faces that are
   right as outward.
3. **Normals**, once the winding is right: part by part, in the parts steps 1
   and 2 read, never a corner on its own sign. Read each face by the average of
   its corner normals against its vector area, the sum of
   `cross(v[j] − v[0], v[j+1] − v[0])` over its fan, both normalized: it reads
   with its winding at `dot ≥ 0.5` and against it at `dot ≤ −0.5`, and has no
   reading in between, or when one of its corner normals is zero or,
   normalized, gives a `dot` of the other sign or within 0.1 of zero. A face
   whose winding you turned reads as before with the sign turned: the vector
   area turns exactly with the face. A part reads cleanly when every face of it
   has a reading and its larger group of faces wound alike, as step 1 or 2
   found them before turning any (the whole part where they found one group;
   two groups of one size leave no larger one), reads all one way. In a part
   that reads cleanly, negate the normals of the faces that read against their
   winding and keep the rest: that negates normals stored the other way or
   turned along with their winding, and keeps those of faces whose winding
   alone was turned. Leave any other part as it is, to inspect.
   Negate in the pool, `lod.facenormals[j] = (-x, -y, -z)` (not through
   `Vertex.normal`, whose setter looks the value up in the pool). An entry that
   a corner you keep also uses stays as it is, and the corners you fix are
   re-pointed to an entry you leave unchanged that already holds the negated
   value or, failing that, to a negated copy; copies count toward the 32768
   entries `validate()` checks (`WARN_NORMALS_BUDGET`).
   A corner normal still against its face at the end is inspected, never
   negated on that alone: a normal smoothed across a sharp fold can point
   against a face wound right. A flat tetrahedron wound right, with one
   area-weighted normal per point, has 6 of its 12 corners against their faces;
   `validate()` reads it at 75 % (`WARN_WINDING_NORMAL_MISMATCH`), and negating
   those corners turns six right normals, through three pool copies, and takes
   it to 100 % with no finding.
   *(Changed 2026-10-03, 1.10.1: this step read "negate each corner normal that
   still points against its face, in the pool, [...] Go corner by corner: the
   check reads each face's first corner only, and negating whole faces turns
   corners that were right. [...] A corner normal close to perpendicular to its
   face gives no clear sign: inspect it rather than flip it." On smoothed
   normals that turns right ones, as on the tetrahedron above.)*

Never reverse faces on this finding alone. Two Blender exports read 0 % and
their winding was right: the build that reversed every face rendered both
inside-out in game, and the one that negated their normals rendered both right
side out. Either fix silences the finding, the wrong one too, so settle the
winding before touching anything else, not after. And never reverse a face by
swapping `vertices[1]` and `vertices[2]`: that inverts a triangle but turns a
quad `[0,1,2,3]` into `[0,2,1,3]`, a crossed face.

`ERR_WINDING_INVERTED` is read the same way: the collision LOD and the Visual
LOD disagree on which way is out, not which one is wrong. A Visual LOD turned
inside-out, faces and normals together, raises it on the healthy collision LODs
and not on itself, and the absolute check passes it. So run step 1 on the
Visual LOD the message names and step 2 on the collision LOD, which leave a
part that reads right as it is, then step 3. A part those steps cannot read (an
open sheet, double-sided twins, a component that is not closed and convex)
leaves the finding unresolved: check in game, or against a model that renders
right, which side it is meant to show before turning it. Only when every part
of both LODs reads right is there nothing to fix: a Visual LOD meant to be seen
from inside reads positive and is right. Reversing the healthy collision LODs
instead, which this finding used to recommend, trades it for
`ERR_WINDING_VS_NORMALS` on each of them; negating their normals as well leaves
`validate()` at `[]` with every LOD wound outward, the collision LODs as
`transform(ROT_X_NEG90)` alone leaves them, which registered no raycast in game.

## Status and known issues

The library is used in a real modding pipeline. On a plain `pytest` run 391
tests pass and 11 skip: the 7 CANON tests, which need a local clone of upstream
(see [Tests](#tests)), and 4 that need the companion scripts. It has also been
through a deliberately adversarial audit, and **not every problem it found is
fixed yet**. Before
relying on this for anything you cannot redo, read
[KNOWN-ISSUES.md](KNOWN-ISSUES.md) — in particular the entries about
`save(verify=True)`, `python -m py3d diff` and the Recipe JSON round-trip, which
are weaker than their names suggest.

## Tests

```bash
python -m pytest -q

# The CANON tests compare byte-for-byte output against upstream and are
# skipped unless you point them at a local clone of it:
PY3D_UPSTREAM_PATH=/path/to/KoffeinFlummi/py3d python -m pytest -q
```

Fixtures are synthetic — no Bohemia Interactive assets are included or required.

## License

MIT, same as upstream. Copyright (c) 2017 Felix Wiegand for the original work;
see [LICENSE](LICENSE). Fork maintained by [@willy92wins](https://github.com/willy92wins).
