# Decimation libraries

Which Python library to use to cut a dense imported mesh down to a face count each LOD can carry, a `pymeshlab` recipe that keeps UV seams, and face targets for each LOD.

These are third-party Python packages that this repo does not install. Their behaviour below was measured on a 94k-face OBJ of a wall lamp from a third-party mod (**tool knowledge**), not on a vanilla file. The vanilla car to compare LODs against is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`; it is binarized (ODOL version 56), so py3d cannot read it and no vanilla face count is given here. The vertex ceiling that decides whether a model packs lives in `binarize-vertex-budget.md`, and the vehicle LOD rules in `invariants-lods-and-vertex-budget.md`.

## Which library to pick

Use `pymeshlab` with the `meshing_decimation_quadric_edge_collapse_with_texture` filter for any real mesh with UVs. Use Blender headless when it is installed and you build the object from scratch. Avoid `fast_simplification` on artist meshes.

| Library | Keeps UVs | Keeps topology | Reaches any target | Install | Speed |
|---|---|---|---|---|---|
| `fast_simplification` | No | Poor, tears holes | No, stalls | `pip` | Fastest |
| `pymeshlab` (quadric edge collapse with texture) | Yes, as wedge UVs | Good | Yes | `pip` | Fast |
| Blender `--background` with the Decimate modifier | Yes, after a new unwrap | Good | Yes | Needs Blender | Slow to launch |
| `trimesh.simplify_quadric_decimation` | No | Fair | Needs a backend such as `open3d`, missing on most systems | `pip` plus backend | Not measured |

## Why `fast_simplification` fails on artist meshes

- It stops collapsing at a floor that depends on the mesh. On the 94k-face lamp it never went below about 22k faces, whatever `target_count` or `agg` was set. Clean synthetic meshes reduce fine, so the cause is the non-manifold edges, duplicate vertices and degenerate triangles that Maya and ZBrush OBJ exports carry.
- It merges surfaces that should stay apart, such as the inside and outside of a lamp shade, which leaves holes, loose face islands and floating slices.
- It returns only positions and faces, so UVs are lost. Copying them back from the original smears seams on round parts; a bulb with a polar seam shows a striped band.

When the output shows holes, floating shards, smeared texture around UV poles, or LODs with different silhouettes, switch library instead of tuning `agg`.

## The `pymeshlab` recipe

The `_with_texture` variant treats UV seams as hard edges that cannot collapse, so round UV islands stay whole. Install with `pip install pymeshlab`, plus `trimesh scipy numpy` for welding.

Write the mesh to an OBJ with duplicate positions merged but the original UV indices kept per face corner, then decimate:

```python
import os, tempfile
import numpy as np
import pymeshlab

def decimate_meshlab(V, UV, F, target_face_count, preserve_boundary=True):
    # V: (Nv, 3) positions, UV: (Nv, 2) one UV per row of V, F: (Nf, 3) indices into both.
    # Returns positions, wedge UVs (Nf*3, 2) and faces.
    if target_face_count >= len(F):
        return V, UV[F.reshape(-1)].astype(np.float32), F
    with tempfile.TemporaryDirectory() as td:
        in_obj = os.path.join(td, "in.obj")
        # Merge seam vertices into one position with several vt entries,
        # which is what lets the solver collapse edges.
        V_uniq, inv = np.unique(V, axis=0, return_inverse=True)
        F_pos = inv[F.reshape(-1)].reshape(-1, 3)
        with open(in_obj, "w") as f:
            for v in V_uniq:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for uv in UV:
                f.write(f"vt {uv[0]:.6f} {uv[1]:.6f}\n")
            for old, new in zip(F, F_pos):
                f.write("f " + " ".join(f"{int(new[k])+1}/{int(old[k])+1}" for k in range(3)) + "\n")
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
        if wuv.ndim == 3:  # some builds return (Nf, 3, 2), others (Nf*3, 2)
            wuv = wuv.reshape(-1, 2)
    return V_out, wuv, F_out
```

Right after the decimation filter, call `ms.apply_filter("compute_normal_per_vertex")` (wrap it in `try`, the name varies between versions) and read `m.vertex_normal_matrix()`. These smooth normals follow the real topology, so they beat a "flip if it points toward the centroid" rule on uneven shapes such as a lamp with a long arm. Switch to them when specular looks rippled without a normal map, or a curved panel looks lit from behind. Store each normal once in `lod.facenormals` and point each `Vertex.normal_index` at it, which gives smooth shading at the smallest normal pool.

## Wedge UVs

Wedge UVs belong to a face corner, not a vertex: a position on a seam has two. Assign them per corner when building py3d faces, never by vertex index:

```python
wedge_uvs = wuv.reshape(-1, 3, 2)
for tri, uvs in zip(F_out, wedge_uvs):
    face = py3d.Face(lod.points, lod.facenormals)
    for k in range(3):
        v = py3d.Vertex(lod.points, lod.facenormals)
        v.point_index = int(tri[k])
        v.uv = (float(uvs[k, 0]), float(uvs[k, 1]))
        face.vertices.append(v)
```

## `pymeshlab` traps

- The filter name is exact: `meshing_decimation_quadric_edge_collapse_with_texture`. It does not accept `preservetopology`; passing it fails with `Parameter preservetopology not found`.
- `save_current_mesh()` can raise `MemoryError` when `save_textures=True` (the default) and the OBJ points at a 4k or larger PNG. Pass `save_textures=False`, or read `vertex_matrix()`, `face_matrix()` and `wedge_tex_coord_matrix()` directly.
- The module has no `__version__`, so do not use it for feature checks.
- `MeshSet.filter_list()` does not exist; call `pymeshlab.filter_list()` or `dir(ms)`.

## Blender instead

When Blender is installed it gives the best LODs, because it can unwrap again after Decimate, shade smooth and bake AO. The steps are in `_shared/models/blender-headless.md`. Prefer Blender for an object built from scratch, and `pymeshlab` for adapting a delivered mesh.

## Face targets per LOD

The old DX9 limit of 32,768 vertex normals per LOD is a useful aim for LOD 0 even though DayZ runs on DX11, because it forces real reduction between LODs. For a 90k-face artist mesh:

| LOD | Face target | Vertices with smooth normals, about |
|---|---|---|
| 0 | 15,000 | 8,000 |
| 1 | 7,500 | 4,500 |
| 2 | 3,000 | 1,900 |
| 3 | 1,200 | 800 |

A searchlight from a third-party mod has 7,007 vertices and 12,430 faces in LOD 0, a fair size for a complex placed item.

## Clean the input first

When `pymeshlab` still misbehaves, check the source mesh:

- Duplicate positions: if `trimesh` `merge_vertices()` reports far fewer vertices than the raw `v` lines, merge them as the recipe does before decimating.
- Non-manifold edges: `trimesh.is_winding_consistent` reports winding; `trimesh.fill_holes()` closes small gaps.
- Loose parts: `trimesh.split(only_watertight=False)` counts islands. Three is normal for a lamp with shade, arm and mount; fifty or more usually means errors.

When a mesh holds named parts (bulb, housing), decimate each part on its own with its own target, split by the OBJ's `usemtl` lines (`external-obj-import.md`).
