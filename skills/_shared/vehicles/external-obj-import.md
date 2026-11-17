# Importing external OBJ models into DayZ

OBJ to game-ready `.p3d`, end to end: parse, transform, decimate, normals, LOD assembly, PNG to PAA, config wiring and validation, with the winding and normal corrections that later vehicle imports forced.

> Status: the workflow was measured on third-party mod content, not vanilla (a wall lamp of a power-grid mod; the winding corrections on a sports coupe import), and is not yet checked on `P:\`. The mod-side hooks the steps describe (placement modes, wall yaw offset, port registration, device registries) belong to that kind of mod, not to vanilla. A citation written with its full `P:\` path was opened on the vanilla data. The Python libraries named are optional third-party packages that this repo does not install. `py3d-direct-generation.md` and `memory-and-selections.md` are in `skills/dayz-model-pipeline/references/`, not files of this pack. The fixed "32k" ceiling in step 5 is a planning figure: `binarize-vertex-budget.md` holds the measured rule.

## Vanilla anchors checked on `P:\`

- `units[]` is the `CfgPatches` array step 8 says not to forget: `P:\DZ\vehicles\wheeled\config.cpp:5`.
- The vanilla models an import is compared against are binarized: `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` opens with the `ODOL` signature, version 56, so the vanilla winding and normal percentages quoted below were measured on debinarized copies and cannot be read from the file on `P:\` directly.

## When to use this

This reference covers the workflow for turning an artist-authored OBJ
(Maya/ZBrush/Blender export) into a ready-to-implement DayZ `.p3d`. It's
an end-to-end walkthrough, grounded in a real case (a wall lamp for a
power-grid mod: 94k-face high-poly lamp with PBR textures → game-ready mod object in one
pipeline run).

Use this when:

- The user delivers an `.obj` file (often with `.mtl` + PNG textures)
- No procedural generation is needed — the geometry already exists
- You need the object to slot into an existing mod (shared config/scripts
  with sibling items)

Related references:

- Decimation mechanics → `decimation-libraries.md`
- PNG → PAA encoding (no external tools needed) → `png-to-paa-encoding.md`
- P3D assembly API → `py3d-direct-generation.md` (dayz-model-pipeline skill)
- Memory points / port naming → `memory-and-selections.md` (dayz-model-pipeline skill)

## Quick workflow (annotated)

```
Step 1: Explore reference object in the mod (sibling item with same role)
Step 2: Parse OBJ → (verts, uvs, faces_by_material)
Step 3: Pick transform (centering, scaling, orientation)
Step 4: Decimate per-material group with pymeshlab
Step 5: Build smooth normals from the FINAL winding (no auto-orient)
Step 6: Assemble P3D — visual LOD(s), convex Geom/Fire/View, Memory
Step 7: Encode color PNG → PAA (DXT1, pure Python)
Step 8: Write rvmat(s), model.cfg entry, config.cpp classes, scripts
Step 9: Open in the inspector + the textured viewer to validate
```

Each step below elaborates with the patterns that proved necessary.

---

## Step 1: Use a sibling as reference

For an electrical device of a power-grid mod, find the closest analogue
already in the mod (the ceiling light for a lamp, an existing switch for a
switch, and so on) and read:

- Its block in `config.cpp` (kit class + placed-entity class)
- Its entry in `model.cfg` (sections, animations)
- Its script files in `scripts/4_World/` (the device class and its effect)
- Its `.rvmat` files (OFF + emissive ON variants)
- Its memory LOD (ports, light positions, bbox)

This answers the most important modelling questions before any geometry
is touched: which material swaps, which animations, which named
selections, how ports are wired. **The user saying "same as ceiling
light but wall-mounted" shortcuts 80% of decision-making** — read the
sibling, clone structurally, adapt placement.

## Step 2: Parse the OBJ with material-based selection splits

OBJs carry material assignments through `usemtl` lines. Use them to split
faces into named selections. Typical Maya pattern:

- `usemtl lamp_electric_HP:initialShadingGroup` → body faces
- `usemtl aiStandardSurface1SG` → bulb / accent part
- Other Maya defaults: `lambert*SG`, `blinn*SG`

In the wall-lamp case the bulb's material (`aiStandardSurface1SG`) was
assigned by the artist specifically to isolate glass-like surfaces — this
became the `light_emit` named selection that the engine swaps to the
emissive `_on.rvmat` when the device is powered.

### Minimal OBJ parser

```python
def parse_obj(path, emissive_material_names):
    verts, uvs = [], []
    faces_by_group = {"body": [], "emit": []}
    current_mat = None
    with open(path, "r") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.split()
                verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith("vt "):
                parts = line.split()
                uvs.append((float(parts[1]), float(parts[2])))
            elif line.startswith("usemtl "):
                current_mat = line[7:].strip()
            elif line.startswith("f "):
                toks = line.split()[1:]
                tri_verts = []
                for t in toks:
                    parts = t.split("/")
                    vi = int(parts[0]) - 1
                    ti = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else -1
                    tri_verts.append((vi, ti))
                group = "emit" if current_mat in emissive_material_names else "body"
                # fan-triangulate any n-gons
                for i in range(1, len(tri_verts) - 1):
                    faces_by_group[group].append(
                        [tri_verts[0], tri_verts[i], tri_verts[i + 1]]
                    )
    return verts, uvs, faces_by_group
```

### Flipping V for DayZ texture convention

OBJ texture coordinates put V=0 at the bottom of the image. DayZ
(and Object Builder) put V=0 at the top. Flip once at parse time:

```python
# When you emit UVs per face-vertex:
uv_flipped = (u, 1.0 - v)
```

Skipping this flip is a silent visual bug — textures render upside-down.

## Step 3: Transform — centering, scaling, orientation

Artist OBJs often ship at arbitrary scale and with the model centered on
some local origin rather than the DayZ ground-origin convention. Do all
of these at once:

```python
V = np.array(verts, dtype=np.float64)
lo, hi = V.min(axis=0), V.max(axis=0)

# DayZ convention: model sits above Y=0 (Y is up).
# Center X/Z on bbox center, shift Y so the floor of the bbox is at 0.
center = np.array([(lo[0]+hi[0])/2.0, lo[1], (lo[2]+hi[2])/2.0])

# Target a reasonable real-world size.
TARGET_MAX_DIM = 0.40   # meters — tweak per object type
scale = TARGET_MAX_DIM / float((hi - lo).max())

def xform(v):
    return (
        (v[0] - center[0]) * scale,
        (v[1] - center[1]) * scale,
        (v[2] - center[2]) * scale,
    )
```

### Orientation — when (not) to flip axes

- **OBJ Y-up == DayZ Y-up.** If the OBJ was exported from Maya or a
  modern Blender OBJ exporter with Y-up preset, no axis rotation is
  needed. Unlike Blender's native Z-up exports (covered in
  `py3d-direct-generation.md`), OBJs are almost universally Y-up.
- **Don't flip Z speculatively — and "flip ⇒ reverse every face" is NOT the invariant.** A reflection (det=-1) does invert face orientation, but what matters is (a) the NET
  determinant of the full multi-stage transform chain and (b) the side-convention gap between source and
  target: glTF/OBJ/OpenGL render the +cross side, DayZ renders the ANTI-cross side. One net reflection with
  winding kept VERBATIM is exactly the OpenGL→DayZ conversion (measured: Blender→DayZ `(x, z+Y0, y)`
  det=-1, no reversal, correct in game on a sports coupe import); reversing there bakes the inside-out result. A spurious
  EXTRA flip (an early draft of the wall lamp: interior lit, exterior black) changes the net chain — remove the
  flip rather than "fixing" winding. Inverted-normals symptoms (surface visible but black) are a NORMALS
  problem, not winding: recompute stored normals as smooth(+cross) of the FINAL winding.
- **Front-facing direction is a config concern, not a mesh concern.**
  If the model faces `+Z` but DayZ expects it to face the wall (`-Z`
  after hologram yaw), fix it where the mod's placement code takes its
  wall yaw offset (return `180.0` from the kit subclass) — not by rotating
  the mesh.

### Quick sanity check — winding

Centroid-outwardness of the winding cross product is NOT a correctness gate for DayZ: the engine renders
the ANTI-cross side, and correct content measures inward-dominant (vanilla civiliansedan LOD1 37.1%
cross-outward, its roof 1.6%; a deployed-approved car shell 14-19%; an in-game-OK interior 67%). Never
"repair" a mesh to raise this number. Sanity-check instead:

- (a) per-piece topological winding uniformity — every shared edge traversed in opposite directions by
  its two faces (count, for every edge shared by two faces, the pairs that
  traverse it in the same direction; this repo ships no script for it);
- (b) stored normals consistent with the final winding: stored·cross>0 ≈ 96-99% as in vanilla
  (see the import orientation rule in `visual-gates-and-winding.md`).

## Step 4: Decimate per material group

See `decimation-libraries.md` for the full comparison. In short:

```python
# Decimate body and emit separately so each gets its own face budget.
Vb_d, UVwedge_b, Fb_d = decimate_meshlab(V_body, UV_body, F_body, 15000)
Vbl_d, UVwedge_bl, Fbl_d = decimate_meshlab(V_bulb, UV_bulb, F_bulb, 2800)
```

Use a ladder of targets for 4 LODs (e.g. `[15000, 7500, 3000, 1200]` for
body, `[2800, 1400, 600, 300]` for emissive). Keep the emissive part
relatively dense at LOD0 — spherical bulbs need segments to look round.

## Step 5: Smooth normals from the FINAL winding

Flat normals (one per face, repeated across the face's 3 vertices) hit
the engine's 32k normal pool ceiling fast. Smooth normals (one averaged
normal per unique vertex) are roughly 3× more efficient and look better
on curved surfaces.

Derive them from the FINAL winding: area-weighted smooth of `+cross` per
vertex — do NOT auto-orient normals outward from the model centroid
(vanilla MLOD stored·cross>0 = 96.2% and an
in-game-OK interior 99.5%, while a centroid-oriented car shell measured
0.5% — anomalous, candidate root of bright-triangle artifacts). If the
source winding is inconsistent, fix the WINDING first by
per-connected-component MAJORITY flood-fill, then derive normals from it:

```python
def compute_smooth_normals(V, F):
    V = np.asarray(V, dtype=np.float64)
    F = np.asarray(F, dtype=np.int64)
    p0, p1, p2 = V[F[:,0]], V[F[:,1]], V[F[:,2]]
    fn = np.cross(p1 - p0, p2 - p0)
    a = np.linalg.norm(fn, axis=1, keepdims=True)
    a[a < 1e-12] = 1e-12
    fn_unit = fn / a
    vn = np.zeros_like(V)
    for i in range(3):
        np.add.at(vn, F[:, i], fn_unit * a)   # area-weighted
    lens = np.linalg.norm(vn, axis=1, keepdims=True)
    lens[lens < 1e-9] = 1.0
    vn /= lens
    return vn.astype(np.float32)
```

(A centroid auto-orient step does not belong here — it is
the same oracle class that inverted imported-car normals; see the
import orientation rule in `visual-gates-and-winding.md`. The wall-lamp "lit-from-inside" case was a
spurious extra axis flip, fixed by removing the flip, not by re-orienting
normals.)

## Step 6: Assemble P3D

Standard py3d assembly (see `py3d-direct-generation.md`), but with two
considerations specific to imported meshes:

1. **Store the smooth normals in the `facenormals` pool once per vertex**,
   not per face. Each `Vertex.normal_index` points into this shared pool.
2. **Per-face UVs come from wedge UVs out of pymeshlab**, indexed as
   `wedge[face_idx*3 + vertex_in_face]`. See
   `decimation-libraries.md` for the reshape pattern.

For the collision LOD family (Geometry / Fire Geometry / View Geometry),
a single convex box covering the bounding volume is usually enough for
an item-sized object. Only break into components if the item has
distinct physical parts that need separate collision (articulated
lights, moving panels).

### Choose modern LOD resolution values

Use the DayZ resolution constants:

| LOD | Resolution |
|-----|------------|
| Geometry | `1.0e13` |
| Fire Geometry | `7.0e15` |
| View Geometry | `6.0e15` |
| Memory | `1.0e15` |

Do not use the Arma values `2.0e13` for Fire Geometry and `3.0e13` for
View Geometry: the P3D inspector of the dayz-p3d-inspector skill labels
them "unknown" (`skills/dayz-p3d-inspector/references/recipe-format.md`).

## Step 7: PNG → PAA without external tools

TexView or Pal2PacE is not needed after generation — see `png-to-paa-encoding.md`
for a pure-Python DXT1 encoder that produces valid PAAs the engine
accepts. Typical usage:

```python
from paa_encoder import write_paa_dxt1
write_paa_dxt1(src_png_path="lamp_diffuse.png",
               out_paa_path=f"{DATA_DIR}/wall_lamp.paa",
               max_size=1024)
```

Source PNGs larger than ~1024 on either axis aren't valuable for in-game
textures and balloon the PAA. Resize to 512 or 1024 depending on the
object's size in the player's view.

## Step 8: Write the mod wiring (config, model.cfg, scripts)

Pattern: clone the sibling reference identified in Step 1, rename classes,
adjust model paths, override only what differs.

For the wall lamp, "differs from ceiling light" meant:

- The kit's placement-modes hook returned `1` (floor + wall) instead of `2`
  (floor + wall + ceiling)
- The light effect had slightly smaller radius / brightness (wall sconces
  are usually less powerful than overhead lights)
- A new section in `model.cfg` (class name matches p3d filename)
- A new block in `config.cpp` and a new entry in `CfgPatches.units[]`

Everything else — port wiring, RPC sync vars, the rvmat swap in the
device's variable-sync handler, consumption/capacity, the kit's
registration as furnace fuel — was identical.

### Register the new entity everywhere

`CfgPatches.units[]` in `config.cpp` is the most commonly-missed spot.
Miss it and the class loads but the engine won't create instances for
mission placement. In a mod with its own registries, also check:

- The check list of any action that accepts the sibling kits (for
  example a furnace-fuel action), if the new kit should be accepted too
- Spawn-list registries, if they exist
- The device registry, if the device has a special gameplay role

Grep for the sibling class name across the whole mod — every hit is a
candidate for wall-lamp-specific registration.

## Step 9: Validate with both viewers

- **Textured viewer** (`scripts/tools/dayz-3d-viewer/`) — shows PBR-rendered result
  with the baked PAA/RVMAT, best for spotting UV seam artifacts, inverted
  normals, missing geometry.
- **Inspector** (dayz-p3d-inspector skill) — shows LODs, memory points,
  axes, bounding boxes, named selections. Best for verifying electrical
  ports are at the right place, ce_center is sensible, LODs have the
  expected resolutions.

Run both after generation. If the textured viewer looks fine but the
inspector flags LOD types as "unknown", you used the wrong resolution
constants — regenerate with the values of Step 6.

## Pitfalls to expect on first import

- **"Inverted normals" look** — almost always a spurious extra axis flip
  changing the NET transform chain. Remove the flip. If still wrong,
  recompute stored normals as smooth(+cross) of the FINAL winding
  (Step 5) — never centroid-auto-orient them.
- **UV seam smearing on spheres / bulbs** — you're using nearest-neighbor
  UV transfer instead of MeshLab's wedge-aware decimation. Switch to
  `meshing_decimation_quadric_edge_collapse_with_texture`.
- **Holes and floating slices after decimation** — you're using
  `fast_simplification`. Switch to `pymeshlab`.
- **"Gray/muddy" texture** — usually just the source PNG's average being
  dark, not a bug. Sample a few pixels of the source to confirm. The
  engine renders PBR with metalness/roughness, so matte painted sources
  often look darker than the user expects.
- **Cable won't attach to the device** — Memory LOD is missing
  `port_input_N` / `port_output_N` points, or their names don't match
  the port names the device script registers. See
  `memory-and-selections.md`.
- **P3D is enormous (20MB+)** — you skipped decimation. Real items
  should be 0.5–5 MB. Decimate with pymeshlab.

---

## Blender 5.x — OBJ import/export API

In Blender 4.x+/5.x, `bpy.ops.import_scene.obj` / `export_scene.obj` **no longer
exist** — they moved to `bpy.ops.wm.obj_import` / `bpy.ops.wm.obj_export`,
with different parameters (`forward_axis`/`up_axis` in uppercase like
`"NEGATIVE_Z"`/`"Y"`, `use_split_objects`, `export_selected_objects`, etc.).
**FBX and glTF REMAIN** in `bpy.ops.import_scene.fbx` / `.gltf` (those addons did not
migrate to `wm.`). Checked in Blender 5.1.1. A Blender script written with
the older OBJ operators has to be translated to
`wm.obj_import`/`wm.obj_export`.
