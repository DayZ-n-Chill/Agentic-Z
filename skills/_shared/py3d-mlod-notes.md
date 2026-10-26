# py3d MLOD reader: `lod.facenormals` is a pool, not per-face

Tier 3 pack for anyone reading `.p3d` files with py3d (used by `/dayz-p3d-audit`). Tier 2 rules in `dayz-conventions.md` still apply.

When using KoffeinFlummi's `py3d` library (or any MLOD reader), a critical
detail to know:

`lod.facenormals` is a global pool of normal vectors for the LOD, indexed
by `vertex.normal_index`. It is not a per-face array.

```python
# WRONG mental model — face.facenormals[i] is NOT the normal of face[i]
for i, face in enumerate(lod.faces):
    n = lod.facenormals[i]   # ← WRONG, indexes pool not face

# CORRECT — each Vertex has point_index AND normal_index pointing into pools
for face in lod.faces:
    for v in face.vertices:
        point  = lod.points[v.point_index].coords      # (x, y, z)
        normal = lod.facenormals[v.normal_index]       # (x, y, z)
        uv     = v.uv                                   # (u, v)
```

`face.vertices[i].normal` is a property that resolves to
`lod.facenormals[v.normal_index]` for you. It returns a tuple `(x, y, z)`
directly, not a Vec3 object — so don't write `.coords` on it (compare with
`lod.points[i].coords` which does require `.coords` because points are Vec3
objects).

### Pool size is independent of face count

`len(lod.facenormals)` equals `num_facenormals` from the MLOD header. It is
independent of `len(lod.faces)`. Smoothing-group merges multiple faces
sharing a vertex normal; flat shading allocates one entry per face corner.
Audit code that asserts `len(lod.facenormals) == len(lod.faces)` will fire
spurious errors on most non-trivial models.

### Why this matters for winding / handedness checks

A common audit anti-pattern: compare `lod.facenormals[i]` to
`cross(face.vertices[1].point - face.vertices[0].point, face.vertices[2].point - face.vertices[0].point)`
to detect "winding mismatch". This breaks because:
- `facenormals[i]` is not per-face,
- and even if it were, smoothed-shaded faces have averaged corner normals
  that won't match the flat winding cross product.

The right approach is to average the per-corner normals of one face and
compare to the winding cross product. See
`skills/dayz-p3d-audit/references/winding-methodology.md`.
