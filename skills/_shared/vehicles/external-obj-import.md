# OBJ import: parsing and transform

How to turn an artist's OBJ export (Maya, ZBrush, Blender) into DayZ coordinates: which existing item to copy, how to split faces by material, the UV flip, the transform, and how to tell a winding problem from a normals problem.

The later steps (decimation, normals, LOD assembly, textures, config wiring and checks) are in `obj-import-assembly.md`. The method was worked out on a third-party wall lamp (a 94k-face high-poly mesh with PBR textures) and checked on a sports coupe import; it is not checked on `P:\`. The Python libraries named are optional packages this repo does not install.

Use this route when the user delivers an `.obj` (usually with a `.mtl` and PNG textures), the geometry already exists, and the object must fit into an existing mod beside similar items.

## The steps

1. Read the closest existing item in the mod.
2. Parse the OBJ into vertices, UVs and faces grouped by material.
3. Centre, scale and orient.
4. Decimate each material group (`obj-import-assembly.md`).
5. Build smooth normals from the final winding.
6. Assemble the `.p3d`: visual LODs, convex Geometry, Fire Geometry and View Geometry, Memory.
7. Encode the colour PNG to PAA.
8. Write the `.rvmat`, `model.cfg`, `config.cpp` and scripts.
9. Check in the inspector and the textured viewer.

## Copy the closest item

Find the item in the mod that plays the same role (a ceiling light for a wall lamp, an existing switch for a switch) and read its `config.cpp` block, its `model.cfg` entry, its scripts, its `.rvmat` files (off and emissive on) and its Memory LOD (ports, light positions, bounding box). That answers which material swaps, which animations, which named selections and how ports are wired before any geometry is touched. When the user says "same as the ceiling light but on the wall", clone the structure and change only the placement.

## Split faces by material

OBJ files assign materials with `usemtl` lines; use them to make named selections. Typical Maya names: `lamp_electric_HP:initialShadingGroup` for the body, `aiStandardSurface1SG` for a bulb or accent, and the defaults `lambert*SG` and `blinn*SG`. On the wall lamp the artist gave the bulb its own material to isolate the glass, and that group became the `light_emit` selection the mod swaps to the emissive `_on.rvmat` when the device has power.

```python
def parse_obj(path, emissive_material_names):
    verts, uvs = [], []
    faces_by_group = {"body": [], "emit": []}
    current_mat = None
    with open(path, "r") as f:
        for line in f:
            if line.startswith("v "):
                p = line.split()
                verts.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("vt "):
                p = line.split()
                uvs.append((float(p[1]), float(p[2])))
            elif line.startswith("usemtl "):
                current_mat = line[7:].strip()
            elif line.startswith("f "):
                corners = []
                for t in line.split()[1:]:
                    p = t.split("/")
                    vi = int(p[0]) - 1
                    ti = int(p[1]) - 1 if len(p) > 1 and p[1] else -1
                    corners.append((vi, ti))
                group = "emit" if current_mat in emissive_material_names else "body"
                for i in range(1, len(corners) - 1):  # fan-triangulate n-gons
                    faces_by_group[group].append([corners[0], corners[i], corners[i + 1]])
    return verts, uvs, faces_by_group
```

OBJ puts V=0 at the bottom of the image; DayZ and Object Builder put it at the top. Flip once while parsing, `uv = (u, 1.0 - v)`, or every texture renders upside down with no error.

## Centre, scale and orient

Artist OBJs come at any scale and around any origin. DayZ models stand on Y=0 with Y up, so centre X and Z on the bounding box and put the bottom of the box at 0:

```python
V = np.array(verts, dtype=np.float64)
lo, hi = V.min(axis=0), V.max(axis=0)
center = np.array([(lo[0] + hi[0]) / 2.0, lo[1], (lo[2] + hi[2]) / 2.0])
TARGET_MAX_DIM = 0.40   # metres; set per object
scale = TARGET_MAX_DIM / float((hi - lo).max())

def xform(v):
    return tuple((v[k] - center[k]) * scale for k in range(3))
```

- OBJ from Maya, or from Blender with the Y-up preset, is already Y-up like DayZ, so no rotation is needed. Blender's own Z-up data is covered in `_shared/models/py3d-axis-map.md`.
- Do not flip an axis on a guess, and do not reverse every face because of a flip. A reflection (determinant -1) does reverse face orientation, but what counts is the net determinant of the whole transform chain and the side each format draws: glTF, OBJ and OpenGL draw the side the cross product points to, DayZ draws the other side. One net reflection with the winding kept as is converts OpenGL to DayZ: Blender to DayZ as `(x, z + Y0, y)` has determinant -1, needs no reversal, and was correct in game on the coupe. Reversing there bakes the model inside out.
- An extra flip changes the net chain. An early wall lamp had one and showed a lit inside and a black outside; the fix was removing the flip, not changing the winding.
- A surface that is visible but black is a normals problem, not winding: recompute the stored normals from the final winding (`obj-import-assembly.md`).
- Which way the object faces is placement, not mesh. If it faces `+Z` and the mod's placement expects it to face the wall, return a yaw offset of `180.0` from the kit class where the mod takes its wall yaw; do not rotate the mesh.

## Checking winding

Whether the cross product points away from the centroid is not a correctness check for DayZ, because the engine draws the side opposite the cross product and correct models read mostly inward. Measured on debinarized copies: the vanilla sedan LOD 1 (`P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`, binarized ODOL version 56 on `P:\`) has 37.1 percent of faces pointing outward by that measure and its roof 1.6 percent; an approved deployed car shell 14 to 19 percent; an interior that is correct in game 67 percent. Never "repair" a mesh to raise that number. Check instead:

- Each piece winds the same way throughout: every edge shared by two faces is walked in opposite directions by them. Count the shared edges walked the same way; this repo ships no script for it.
- Stored normals agree with the final winding: the dot product of stored normal and cross product is positive on about 96 to 99 percent of faces, as on vanilla (`visual-gates-and-winding.md`).
