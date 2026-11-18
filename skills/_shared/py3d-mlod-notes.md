# py3d MLOD reader: `lod.facenormals` is a pool, not per-face

Tier 3 pack for anyone reading `.p3d` files with py3d (used by `/dayz-p3d-audit`). Tier 2 rules in `dayz-conventions.md` still apply.

When using the `py3d` library (or any MLOD reader), a critical
detail to know:

`lod.facenormals` is a global pool of normal vectors for the LOD, indexed
by `vertex.normal_index`. It is not a per-face array.

```python
# WRONG mental model — lod.facenormals[i] is NOT the normal of face[i]
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
directly, not an object — so don't write `.coords` on it (compare with
`lod.points[i].coords` which does require `.coords` because `lod.points` holds
`py3d.Point` objects whose `.coords` attribute is the `(x, y, z)` tuple).

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

To negate a normal, write the pool entry (`lod.facenormals[j] = (-x, -y, -z)`), never
the `Vertex.normal` setter, which looks the new value up in the pool and re-indexes the
corner. An entry shared with a corner whose normal must stay gets a negated copy
appended to the pool, and only the corners to change are pointed at the copy
(`skills/dayz-p3d-audit/references/winding-diagnostics.md`, "From Check B to fix").

### Selections are dictionaries

`lod.selections` is an ordered dictionary keyed by selection name. Looping over it
gives the names, not objects. Each selection's `points` and `faces` are dictionaries
keyed by the point or face object, with the weight as the value, so they cannot be
indexed by number:

```python
for name, sel in lod.selections.items():
    members = len(sel.points), len(sel.faces)

# positions of a selection's points in lod.points
position = {id(pt): n for n, pt in enumerate(lod.points)}
indices = sorted(position[id(pt)] for pt in sel.points)
```

Code that reads `sel.name`, indexes `sel.points[0]`, or indexes the selection
itself (`sel[0]`) was written for another library version and fails with
`'str' object has no attribute 'name'`, `KeyError: 0`, or
`'Selection' object is not subscriptable` respectively.

### Two libraries share the name

The `py3d` these notes describe is the DayZ build kept in the repo under
`scripts/tools/py3d/`, the copy `/dayz-p3d-audit` and the other skills load. It has `P3D.validate()`, proxy helpers and
guards against writing a corrupt file, and sets `py3d.IS_DAYZ_FORK = True`, so a script
can assert it imported this copy. The package called `py3d` on PyPI is a different
thing: it is an unrelated point cloud library, so never `pip install py3d`.

## Writing a `.p3d` from a script

Notes on tool behaviour seen on one vehicle mod. None of it is a game fact. The fork in `scripts/tools/py3d/` (1.6.0 or later) guards every old py3d 1.0.0 write trap below; they matter only when you read or run an older script, or one that uses its own wrapper functions (`set_face_weight`, `add_memory_point`, `lod.materials`), which is where several of them came from.

| Old trap | What went wrong | In the fork |
|---|---|---|
| 1. `py3d.Selection()` with no arguments | An empty selection with no error; later adds wrote nothing, so the selection reached the file with its name and no members. The old fix was `py3d.Selection(lod.points, lod.faces)`. | A clear `TypeError`. Use `lod.new_selection(name)` or `lod.set_selection(name, ...)`. |
| 2. A weight given as a float (`1.0`) | The weight slot is one byte; a float wrote four, shifted the rest of the file by three, and Object Builder could not read the LOD. Same for point weights. | Whole numbers are converted on write; anything else raises `ValueError` naming the selection. |
| 3. Material names compared with case | Exporters and their JSON often use upper or mixed case while vanilla derived models use lower case, so an exact match found nothing and the face set ended up empty. | `lod.faces_by_material()` and `faces_for_material()` ignore case. |
| 4. Appending a memory point that already exists | A model extended from a vanilla one already has points such as `crewdriver`; a second point of the same name was ignored because the engine was seen to use the first, so the edit did nothing. This breaks the seat test in `animation/get-in-sides.md`. | `lod.set_memory_point(name, xyz)` inserts or overwrites and never duplicates. |
| 5. References taken before the LOD grew | A reference to the points or faces taken before more were added went stale; selections then listed garbled indices that covered random faces. | Membership is checked on write, and `P3D.save(verify=True)` reads the file back and checks it. |

Whole file check: `python -m py3d validate model.p3d`, or `P3D.validate()`.

### Frame check when a script writes points into a production model

A rebake script takes selections and memory points described in one frame (a viewer's, or a JSON file's) and writes them into the production `.p3d`. When the two frames disagree on which way is forward, a hard coded flip mirrors the output for one of them with no error. In one case the authoring viewer had the front at +Z and the production model at -Z. So give the script an explicit frame argument and let it detect the frame from the model:

```python
def detect_frame(p3d) -> str:
    # Count faces in a 0.5 m band at each end of the long axis; the fuller end is the front.
    bbox = p3d.lod0.bbox()
    front_pos = count_faces_in_band(p3d.lod0, axis="z", band=(bbox.z_max - 0.5, bbox.z_max))
    front_neg = count_faces_in_band(p3d.lod0, axis="z", band=(bbox.z_min, bbox.z_min + 0.5))
    return "plusZ" if front_pos > front_neg else "minusZ"

parser.add_argument("--frame", choices=["plusZ", "minusZ", "auto"], default="auto")
frame = detect_frame(p3d) if args.frame == "auto" else args.frame
flip_z = frame == "minusZ"
```

The pose solver asks the same question from the other side (`animation/rider-pose-solver.md`, its frame of reference section). Both must agree.

### Check the output before calling it done

After any script writes a `.p3d`:

1. Open the output again with `py3d.P3D(open(path, "rb"))`. There is no `py3d.read_p3d`.
2. For each selection written, the face count is above zero and close to the source's. Zero means the write did not take.
3. For each memory point written, the position equals the source within 0.0001 m and the name occurs once. A duplicate with the old value in front means the overwrite was skipped.
4. The material count is unchanged, and `/dayz-p3d-audit` still passes (winding, `Component01` naming).

If any check fails, restore the backup and fix the script; a file corrupted this way cannot be nudged back into shape. A plan that includes a script writing a `.p3d` names these checks as its acceptance criteria.
