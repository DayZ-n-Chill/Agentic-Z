# The Blender to DayZ axis map in py3d

How to map geometry made with Z up (Blender, or code written that way) into a DayZ `.p3d`, which has Y up, without mirroring it or turning it inside out, and when a py3d script may reverse faces. The full account of axes and winding for every source, glTF and GLB included, is `axes-and-winding.md`.

Tool knowledge about the py3d in `scripts/tools/py3d`, measured in game on mod models; MLOD files are not on `P:\`, where every model is binarized (`P:\DZ\gear\camping\wooden_case.p3d` starts with the bytes `ODOL`).

## The map

Blender is right handed and DayZ left handed, so the map that keeps the shape is a reflection: `x' = x`, `y' = z`, `z' = y` (determinant -1). Map the positions, map the normals the same way and negate them (MLOD stores normals pointing inward), and keep the vertex order of every face. Apply it to every LOD: visual, Geometry, Fire Geometry, View Geometry, shadow and Memory.

```python
def map_point(c):
    return (c[0], c[2], c[1])

def map_normal(n):
    return (-n[0], -n[2], -n[1])    # mapped like the points, then negated: MLOD normals point inward

for lod in model.lods:
    for pt in lod.points:
        pt.coords = map_point(pt.coords)
    lod.facenormals[:] = [map_normal(n) for n in lod.facenormals]   # in place: Vertex.normal reads this list
```

One asymmetric model exported three ways and spawned in game showed the difference:

| Map | In game |
|---|---|
| The reflection above | Solid and the right way round |
| A rotation of -90 degrees about X (`z' = -y`), faces reversed and normals negated | Solid, but mirrored |
| `P3D.transform(py3d.BLENDER_TO_DAYZ)` alone | Inside out and mirrored |

The winding checks pass on a mirrored export, and a symmetric model looks right either way, so check the result on an asymmetric feature.

## The same map with py3d's own calls

- `model.transform(((1, 0, 0), (0, 0, 1), (0, 1, 0)))` maps points and normals and, because the determinant is negative, reverses every face. Reverse them back and negate the normals, and the result equals the loop above.
- From py3d 1.8.0, `py3d.blender_to_dayz(model)` does the whole conversion in one call and keeps the vertex order of every face, proxy triangles included. Measured in game: its collision LODs take ray casts in `geom`, `view` and `fire`, and static proxies drawn in Blender as py3d canonical raw triangles come out with the same binarized frames as `add_proxy(space="engine")` (the binarized files are byte for byte the same) and render in the pose drawn. A crew or wheel proxy drawn that way with the identity frame gets the frame a working driven motorbike was built with; that settles the frame only, and the rest of a vehicle must still match a working model (`proxy-frames.md`).
- `py3d.BLENDER_TO_DAYZ` is the rotation with determinant +1 from the table above and is deprecated; the same value is `py3d.ROT_X_NEG90`. Do not use it as the map.

## When to reverse faces

Geometry mapped with the reflection keeps its vertex order: no reversal. Reverse faces only to repair a mesh whose cross product points outward, such as after `P3D.transform()` with a negative determinant, which reverses everything on its own.

Never reverse proxy triangles on their own account; they carry the attachment frame. The one case where they are reversed is undoing a whole model reversal by `P3D.transform()`, which hit them too: reversing everything back leaves them in their authored order, as the reflection and `py3d.blender_to_dayz()` do. py3d canonical triangles then render in the pose drawn in Blender; for proxies made another way, compare the binarized file with a working model.

This loop undoes a whole model reversal and nothing else. It reverses every face of every LOD, proxy triangles included:

```python
# Only to undo a whole model P3D.transform() reversal
for lod in model.lods:
    for face in lod.faces:
        face.vertices.reverse()
```

Do not use it to repair a collision LOD wound outward. Repair that face by face: reverse only the faces that are not proxy triangles and that the per component check reads as outward, set their stored normals as `dayz-p3d-audit/references/p3d-killers.md` section 1 says, and leave every other face and LOD alone (`generated-model-rules.md`, "The per component winding check"). Run as a collision repair, the loop also turns a healthy visual LOD inside out and changes every proxy's frame.

Faces wound the wrong way show as:

- textures visible only from inside the object;
- the object transparent or missing from outside;
- the object solid black from outside.
