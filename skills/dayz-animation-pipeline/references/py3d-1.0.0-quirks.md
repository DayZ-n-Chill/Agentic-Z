# py3d 1.0.0 write quirks (historical) and the frame check for a rebake script

Notes on tool behaviour from the LFQuad project of the source pack, kept for anyone reading an older script. Nothing here is a vanilla fact and none of it was checked on `P:\`. The DayZ fork of py3d in `scripts/tools/py3d/` (1.6.0 or later) removes or guards every quirk below; the frame check at the end still applies to any script that writes memory points.

## Status

A later check by the source pack found that several of these "quirks" described the project's own wrapper functions (`set_face_weight`, `add_memory_point`, `lod.materials`), not the real surface of upstream py3d 1.0.0. What the fork does for each case:

| Old quirk | In the fork |
|---|---|
| 1. `Selection()` with no arguments | A clear `TypeError`. Use `lod.new_selection(name)` or `lod.set_selection(name, ...)`. |
| 2. Weights given as float | Checked on write: whole numbers are converted, anything else raises `ValueError` naming the selection. |
| 3. Material names in another case | `lod.faces_by_material()` and `faces_for_material()` ignore case. |
| 4. Duplicate memory points | `lod.set_memory_point(name, xyz)` inserts or overwrites and never duplicates. |
| 5. Stale references after the LOD grows | Membership is checked on write (stale or foreign references raise), and `P3D.save(verify=True)` reads the file back and checks it. |

Whole file check: `python -m py3d validate model.p3d`, or `P3D.validate()`.

## The five quirks as first recorded

If a script writes selections or memory points with an old py3d, or with wrappers like the project's, walk this list before trusting its output.

### 1. `Selection()` needs the LOD's points and faces

```python
sel = py3d.Selection()                         # wrong: an empty selection, with no error
sel = py3d.Selection(lod.points, lod.faces)    # right
```

With the no argument form, later calls that add faces appeared to work and wrote nothing. The selection reached the output file with its name and no members, the same symptom as a converter that keeps selection names and loses membership. Do it once per LOD per selection; if the LOD grows afterwards, see quirk 5.

### 2. Weights are integers

```python
sel.set_face_weight(face_idx, 1.0)   # wrong: corrupts the file
sel.set_face_weight(face_idx, 1)     # right
```

The weight goes into a one byte slot. A float wrote four bytes there and shifted everything after it by three; the file kept a plausible size and Object Builder reported that it could not read the LOD. The same holds for point weights. Use integer 1 unless the script is really skinning.

### 3. Material names: compare without case

```python
target = next(m for m in lod.materials if m.name == mat_name)                    # wrong
target = next(m for m in lod.materials if m.name.lower() == mat_name.lower())    # right
```

The library returns material names as the file stores them. The project's vanilla derived models used lower case names, while exporters, material libraries and the JSON written from them often use upper or mixed case. An exact match then finds nothing and the selection's face set ends up empty. Normalise when comparing, not in the JSON.

### 4. Overwrite a memory point that already exists

```python
mem_lod.add_memory_point("crewdriver", pos)          # wrong when the point exists: two entries

existing = next((p for p in mem_lod.points if p.name == "crewdriver"), None)
if existing:
    existing.set_position(pos)                        # overwrite in place
else:
    mem_lod.add_memory_point("crewdriver", pos)
```

A model extended from a vanilla one already has points such as `crewdriver` and `crewcodriver`. Appending a second point with the same name leaves two; the project saw the engine use the first, the old one, so the edit silently did nothing. This is what breaks the seat test in `dual-entry-action-pattern.md`.

### 5. Take references after the last growth

```python
mem_lod.add_memory_point("pos_driver_L", pos_L)
# ... every other add ...
sel = py3d.Selection(mem_lod.points, mem_lod.faces)   # after the adds, never before
```

A reference to the LOD's points or faces taken before more were added went stale. The output read fine for the new points, but its selections listed garbled indices, and Object Builder showed them covering random faces. Take the reference after the last add, and build again any selection made earlier.

## Frame check when a script writes points into a production model

A rebake script takes selections and memory points described in one frame (a viewer's, or a JSON file's) and writes them into the production `.p3d`. When the two frames differ in which way is forward, a hard coded flip mirrors the output for one of them, with no error. The project's authoring viewer had the front at +Z and its production model at −Z.

So the script takes an explicit frame argument and can detect the frame from the model:

```python
def detect_frame(p3d) -> str:
    # Count faces in a 0.5 m band at each end of the long axis; the fuller end is the front.
    bbox = p3d.lod0.bbox()
    front_pos = count_faces_in_band(p3d.lod0, axis="z", band=(bbox.z_max - 0.5, bbox.z_max))
    front_neg = count_faces_in_band(p3d.lod0, axis="z", band=(bbox.z_min, bbox.z_min + 0.5))
    if front_pos > front_neg:
        return "plusZ"
    return "minusZ"

parser.add_argument("--frame", choices=["plusZ", "minusZ", "auto"], default="auto")
frame = args.frame
if frame == "auto":
    frame = detect_frame(p3d)
flip_z = frame == "minusZ"

for name, src_pos in canonical_points.items():
    pos = list(src_pos)
    if flip_z:
        pos[2] = -pos[2]
    # then write it, overwriting an existing point of the same name
```

The pose solver has the same question from the other side (`vehicle-rider-ik-pose.md`, its frame of reference section). Both must agree on the frame.

## Check the output before calling it done

After any script writes a `.p3d`:

1. Open the output again with `py3d.P3D(open(path, "rb"))`. There is no `py3d.read_p3d`.
2. For each selection written, the face count is above zero and close to the source's. Zero means the write did not take.
3. For each memory point written, the position equals the source within 0.0001 m, and the name occurs once. A duplicate with the old value in front means the overwrite was skipped.
4. The material count is unchanged, and `/dayz-p3d-audit` still passes (winding, `Component01` naming).

If any check fails, restore the backup and fix the script. A file corrupted this way cannot be nudged back into shape.

A plan that includes a script writing a `.p3d` names these checks as acceptance criteria for it.
