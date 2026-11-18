# Mesh decimation for DayZ models: library comparison and decision guide

Which Python library to reduce a high-poly import with (`pymeshlab`, `fast_simplification`, Blender headless, `trimesh`), a working `pymeshlab` recipe that keeps UV seams, and face targets for a LOD ladder.

> Status: tool behaviour measured on a 94k-face OBJ of a wall lamp (third-party mod content, not vanilla), and not yet checked on `P:\`. The libraries are optional third-party Python packages and are not installed by this repo. The fixed vertex ceilings under "Choosing LOD targets" are planning figures: `binarize-vertex-budget.md` holds the measured rule (the ceiling is per model, and the verdict of `binarize` decides), and `invariants-lods-and-vertex-budget.md` holds the vehicle LOD invariants.

## Vanilla anchors checked on `P:\`

- The vanilla control for LOD ladders in this pack is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`. It is a binarized ODOL (version 56), which py3d cannot read, so no vanilla face count was measured for this file.

## What decimation is for

Decimation is how you drop a dense artist-authored mesh (say 90k triangles from
Maya) down to a LOD-appropriate count (under the engine's vertex-normal limits,
and useful visual LOD tiers at LOD1/LOD2/LOD3). **The choice of decimation
library matters a lot.** This page compares the options and says
which to reach for.

## TL;DR

- **Use `pymeshlab`** with `meshing_decimation_quadric_edge_collapse_with_texture`
  for any real-world mesh with UVs. It preserves UV seams, respects topology,
  and reaches arbitrary face targets.
- **Avoid `fast_simplification`** for artist meshes with UVs. It hits a hard
  floor (refuses to collapse below some mesh-dependent count, e.g. ~22k faces
  on a 94k-face lamp), destroys topology (holes, floating islands), and drops
  per-vertex attributes like UVs silently.
- **Blender headless** is best when available (proper Decimate modifier +
  Smart UV re-project + AO bake), but most non-workstation environments don't
  have Blender installed. `pymeshlab` covers ~90% of that ground from `pip`.

## Capability Matrix

| Library | Preserves UVs | Preserves topology | Hits arbitrary targets | Install cost | Speed |
|---|---|---|---|---|---|
| `fast_simplification` | No | Poor (tears holes) | No (stalls) | `pip`, instant | Fastest |
| `pymeshlab` (QEC-with-texture) | Yes (wedge UVs) | Good | Yes | `pip`, one-shot | Fast |
| Blender `--background` + Decimate | Yes (after re-UV) | Good | Yes | Needs Blender install | Slow (launch cost) |
| `trimesh.simplify_quadric_decimation` | No | OK | N/A | Needs `open3d` or similar backend | N/A — backend missing on most systems |

## The `fast_simplification` trap

`pip install fast_simplification` is tempting: one dependency, the API is
trivial, it's written in C and runs fast. But on real artist meshes it fails
hard in ways that are easy to miss until you render the output.

**What goes wrong:**

1. **Hard floor on collapse count.** On a 94k-triangle input it refused
   to reduce below ~22k regardless of `target_count=1000` or `agg=15`. The
   same `agg` values work fine on clean synthetic meshes, so the bug is
   topology-dependent (non-manifold edges, duplicated vertices, degenerate
   triangles — all common in Maya/ZBrush OBJ exports).
2. **Topology destruction.** When it does collapse, it can merge across
   surfaces that shouldn't merge (e.g. a lamp shade's inside and outside
   surfaces get stitched), leaving visible holes, disconnected face islands,
   and "floating slice" artifacts. Users notice immediately.
3. **UVs are dropped.** The function returns `(V_out, F_out)` — no attribute
   transfer. You have to re-project or nearest-neighbor UV-copy from the
   original, and both approaches create seam artifacts on spheres/curves
   (the bulb of a lamp is a textbook case — a sphere with a polar UV seam
   shows as a smeared stripe).

**Symptoms in the rendered output:**
- Visible holes in what should be a closed mesh
- Small disconnected shards floating near the model
- Smeared/striped texture regions around UV poles (bulbs, spherical parts)
- Different LODs have totally different silhouettes even with "similar" targets

If you see any of these after decimation, don't try to tune `agg` further —
switch library.

## The `pymeshlab` recipe (recommended)

`pymeshlab` wraps MeshLab's proven Quadric Edge Collapse. The
`_with_texture` filter variant is wedge-UV aware: it models UV seams as
hard edges that cannot collapse across, so spherical UV islands stay
intact.

### Install

```bash
pip install pymeshlab
# Also useful for the position-welding step:
pip install trimesh scipy numpy
```

### The full pattern (Python)

```python
import os, tempfile
import numpy as np
import pymeshlab

def decimate_meshlab(V, UV, F, target_face_count, preserve_boundary=True):
    """
    Decimate with MeshLab's texture-aware Quadric Edge Collapse.

    Inputs:
      V: (Nv, 3) vertex positions — may have duplicates if you deduped by (vi, ti)
      UV: (Nv, 2) UV coords — row i is the UV of V row i
      F: (Nf, 3) int32 — face indices; every index addresses both V and UV

    Returns:
      V_out: (Nv', 3) decimated positions
      UVwedge_out: (Nf'*3, 2) wedge UVs, one per face-vertex
      F_out: (Nf', 3) decimated face indices into V_out
    """
    if target_face_count >= len(F):
        wedge = UV[F.reshape(-1)]
        return V, wedge.astype(np.float32), F

    with tempfile.TemporaryDirectory() as td:
        in_obj = os.path.join(td, "in.obj")

        # Collapse duplicate positions (seam vertices with different UVs become one
        # position with multiple vt references). This is what lets the solver
        # actually collapse edges.
        V_uniq, inv = np.unique(V, axis=0, return_inverse=True)
        F_pos = inv[F.reshape(-1)].reshape(-1, 3)

        with open(in_obj, "w") as f:
            for v in V_uniq:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for uv in UV:
                f.write(f"vt {uv[0]:.6f} {uv[1]:.6f}\n")
            for tri_old, tri_new in zip(F, F_pos):
                # Each face-vertex gets its wedge UV via the ORIGINAL vt index.
                f.write(
                    "f "
                    f"{int(tri_new[0])+1}/{int(tri_old[0])+1} "
                    f"{int(tri_new[1])+1}/{int(tri_old[1])+1} "
                    f"{int(tri_new[2])+1}/{int(tri_old[2])+1}\n"
                )

        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(in_obj)
        ms.apply_filter(
            "meshing_decimation_quadric_edge_collapse_with_texture",
            targetfacenum=int(max(12, target_face_count)),
            preserveboundary=preserve_boundary,
            preservenormal=True,
            planarquadric=True,
        )
        m = ms.current_mesh()
        V_out = m.vertex_matrix().astype(np.float32)
        F_out = m.face_matrix().astype(np.int32)

        wuv = np.asarray(m.wedge_tex_coord_matrix(), dtype=np.float32)
        # Some pymeshlab builds return (Nf, 3, 2), others (Nf*3, 2).
        if wuv.ndim == 3:
            wuv = wuv.reshape(-1, 2)

    return V_out, wuv, F_out
```

### Also grab MeshLab's winding-aware vertex normals

After decimating, ask MeshLab to compute per-vertex smooth normals and
pull them out alongside wedge UVs. These are **strictly better than a
hand-rolled centroid-based auto-orient**: MeshLab follows the mesh's
actual topology and handles asymmetric geometry (arm + shade + mount)
where a simple "flip if dot(normal, vertex - centroid) < 0" rule
misfires.

```python
# Immediately after apply_filter(...decimation...)
try:
    ms.apply_filter("compute_normal_per_vertex")
except Exception:
    pass  # filter name varies slightly across pymeshlab versions

m = ms.current_mesh()
V_out = m.vertex_matrix().astype(np.float32)
F_out = m.face_matrix().astype(np.int32)
N_out = np.asarray(m.vertex_normal_matrix(), dtype=np.float32)  # (Nv, 3)
wuv   = np.asarray(m.wedge_tex_coord_matrix(), dtype=np.float32)
if wuv.ndim == 3:
    wuv = wuv.reshape(-1, 2)
```

Store `N_out[k]` once per unique vertex in `lod.facenormals` and have
each `Vertex.normal_index` point to it — this is smooth shading at the
minimum normal-pool cost.

**Signs you should switch to MeshLab normals over the centroid
auto-orient:**
- Model is asymmetric (wall lamp with a long arm, not a symmetric
  device like a button or a switch panel)
- Render shows wavy / rippled specular that doesn't correspond to a
  normal map
- Certain panels or curved surfaces look "lit from behind" — the shade
  of a lamp is the classic case, its centroid-relative normals can end
  up pointing into the interior

### Wedge UVs vs per-vertex UVs

Wedge UVs are **per-face-vertex**, not per-vertex. A mesh where one position
has two different UVs across a seam has two wedge UVs stored at that
position. When you build a py3d face you assign the wedge UV directly to
each `Vertex`:

```python
# wedge_uvs: (Nf*3, 2), flat — reshape once for iteration
wedge_uvs = wuv.reshape(-1, 3, 2)

for tri, uvs in zip(F_out, wedge_uvs):
    face = py3d.Face(lod.points, lod.facenormals)
    for k in range(3):
        v = py3d.Vertex(lod.points, lod.facenormals)
        v.point_index = int(tri[k])
        v.uv = (float(uvs[k, 0]), float(uvs[k, 1]))
        # ...
        face.vertices.append(v)
```

Trying to use wedge UVs as per-vertex UVs (indexing by vertex index) is
wrong — two face-vertices that share a position may need different UVs.

### Common pymeshlab gotchas

- **Filter name is exact.** `meshing_decimation_quadric_edge_collapse_with_texture`
  exists; `_decimation_with_texture` does not. Same parameters mostly as the
  plain variant, but **`preservetopology` is not accepted on the `_with_texture`
  variant** (different filter signature) — remove it or you get
  `Parameter preservetopology not found`.
- **`save_current_mesh()` can MemoryError** when `save_textures=True` is on
  (the default) and the input OBJ references a huge source PNG (4k × 4k+).
  Either pass `save_textures=False`, or skip saving entirely and extract data
  directly via `vertex_matrix()` / `face_matrix()` / `wedge_tex_coord_matrix()`.
- **No `__version__` attribute** on the top-level module. Don't rely on it
  for feature detection.
- **`MeshSet.filter_list()` does not exist** — use `dir(ms)` to find filters
  or call `pymeshlab.filter_list()`.

## The Blender path (for reference)

When `blender` is installed, it produces the highest-quality LODs because it
can re-UV-unwrap after Decimate, Shade Smooth cleanly, and bake AO. The
pipeline is covered in `skills/_shared/models/blender-headless.md`
(`skills/_shared/models/blender-headless.md`). Prefer Blender when building
a full object from scratch; prefer pymeshlab when adapting a delivered mesh
and Blender isn't available.

## Choosing LOD targets

The engine's legacy DX9 spec names 32,768 as the vertex-normal ceiling per
LOD. Modern DayZ SA runs on DX11+ and tolerates more in practice, but it's
still a good target for LOD0 — and it forces meaningful reduction between
LOD tiers.

For a typical 90k-face artist mesh, these targets give a clean LOD ladder:

| LOD | Face target | Expected verts (smooth normals) |
|-----|------------|---------------------------------|
| 0 | 15 000 | ~8 000 |
| 1 | 7 500 | ~4 500 |
| 2 | 3 000 | ~1 900 |
| 3 | 1 200 | ~800 |

Reference (a searchlight model of a third-party mod, not vanilla): LOD0 = 7007 verts / 12430
faces. That's a good anchor for "complex placed item."

## Pre-processing input meshes

If decimation still behaves weirdly after switching to pymeshlab, the input
mesh itself may be the issue. Worth checking:

- **Duplicated vertex positions** (per-face-vertex OBJ exports). `trimesh`
  after `merge_vertices()` reports the unique count — if it's drastically
  lower than the raw `v` count, the OBJ has massive duplication and you
  should dedupe (as in the recipe above) before decimating.
- **Non-manifold edges.** `trimesh.is_winding_consistent` tells you if
  winding is OK; `trimesh.fill_holes()` can patch small open areas.
- **Disconnected components.** `trimesh.split(only_watertight=False)` shows
  how many islands the mesh has. A pendant lamp with a shade + arm + mount
  is legitimately 3 components; a mesh with 50+ components often has errors.

For devices where a mesh contains multiple named parts
(e.g. bulb vs housing), decimate each part separately so the solver can
apply different targets. Split by material name from the
OBJ's `usemtl` lines — see `external-obj-import.md`.
