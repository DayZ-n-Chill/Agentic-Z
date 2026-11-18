# OBJ import: LODs, textures and wiring

How to finish an OBJ import once it is parsed and in DayZ coordinates: decimate each material group, build smooth normals, assemble the `.p3d`, encode the PAA, wire config and scripts into the mod, and check the result.

Parsing, the UV flip, the transform and winding checks come first, in `external-obj-import.md`. The method was worked out on a third-party wall lamp and is not checked on `P:\`, except where a `P:\` path is cited.

## Decimate each material group

Decimate the body and the emissive part separately so each gets its own face budget (`decimation-libraries.md`):

```python
Vb_d, UVwedge_b, Fb_d = decimate_meshlab(V_body, UV_body, F_body, 15000)
Vbl_d, UVwedge_bl, Fbl_d = decimate_meshlab(V_bulb, UV_bulb, F_bulb, 2800)
```

For four LODs use targets such as `[15000, 7500, 3000, 1200]` for the body and `[2800, 1400, 600, 300]` for the emissive part. Keep a round bulb fairly dense in LOD 0 so it still looks round. The 32k normal figure below is a planning number; whether a model packs is decided by `binarize` (`binarize-vertex-budget.md`).

## Smooth normals from the final winding

Flat normals, one per face repeated on its three corners, fill the 32k normal pool fast. Smooth normals, one averaged normal per vertex, take about a third as many and look better on curves.

Derive them from the final winding, area weighted along the cross product of each face. Do not orient normals away from the model centroid: stored normals agree with the cross product on 96.2 percent of faces in a vanilla MLOD and 99.5 percent on an interior that is correct in game, while a centroid-oriented car shell measured 0.5 percent and showed bright triangles. If the source winding is inconsistent, fix the winding first by flipping each connected piece to its majority direction, then compute normals.

```python
def compute_smooth_normals(V, F):
    V = np.asarray(V, dtype=np.float64)
    F = np.asarray(F, dtype=np.int64)
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    fn = np.cross(p1 - p0, p2 - p0)
    a = np.linalg.norm(fn, axis=1, keepdims=True)
    a[a < 1e-12] = 1e-12
    vn = np.zeros_like(V)
    for i in range(3):
        np.add.at(vn, F[:, i], fn)   # fn is unit normal times area
    lens = np.linalg.norm(vn, axis=1, keepdims=True)
    lens[lens < 1e-9] = 1.0
    return (vn / lens).astype(np.float32)
```

## Assemble the model

Assemble with py3d as in `_shared/models/py3d-generation.md`, with two points for imported meshes:

- Store each smooth normal once in the `facenormals` pool and point each `Vertex.normal_index` at it.
- Take each corner's UV from the wedge UVs, `wedge[face_idx * 3 + corner]` (`decimation-libraries.md`).

For an item-sized object one convex box over the bounding volume is enough for Geometry, Fire Geometry and View Geometry. Split into components only for parts that need their own collision, such as an arm that moves or a panel that opens.

Use the DayZ resolution values:

| LOD | Resolution |
|---|---|
| Geometry | `1.0e13` |
| Fire Geometry | `7.0e15` |
| View Geometry | `6.0e15` |
| Memory | `1.0e15` |

Do not use `2.0e13` for Fire Geometry or `3.0e13` for View Geometry, values from Arma-era guides; the P3D inspector labels them "unknown" (`_shared/models/tools-p3d-inspector-recipe.md`).

## Encode the texture

TexView and Pal2PacE are not needed: `_shared/textures/png-to-paa-encoding.md` has a pure-Python DXT1 encoder whose PAA files the engine accepts.

```python
from paa_encoder import write_paa_dxt1
write_paa_dxt1(src_png_path="lamp_diffuse.png", out_paa_path=f"{DATA_DIR}/wall_lamp.paa", max_size=1024)
```

A source over about 1024 on either side adds size without visible gain. Resize to 512 or 1024 by how large the object appears on screen.

## Wire it into the mod

Clone the item you read first, rename the classes, change the model paths and override only what differs. For the wall lamp against the ceiling light that meant:

- The kit's placement modes hook returns `1` (floor and wall) instead of `2` (floor, wall and ceiling).
- The light has a smaller radius and brightness.
- A new `model.cfg` class named after the `.p3d` file.
- A new `config.cpp` block.

Port wiring, synced variables, the `.rvmat` swap on sync, power use and the kit's use as furnace fuel stay the same.

Listing the class in `CfgPatches` `units[]` is tidy but not required: the addon that holds every vanilla car leaves `units[]` empty (`P:\DZ\vehicles\wheeled\config.cpp:5`) and those cars spawn. In a mod with its own registries, Grep the copied item's class name across the mod; every hit, such as an action's list of accepted kits, a spawn list or a device registry, may need the new class.

## Check with both viewers

- The textured viewer (`scripts/tools/dayz-3d-viewer/`) renders the PAA and `.rvmat`; use it for UV seams, inverted normals and missing geometry.
- The P3D inspector (`_shared/models/tools-p3d-inspector.md`) shows LODs, memory points, axes, bounding boxes and named selections; use it to check port positions, `ce_center` and LOD resolutions.

If the viewer looks right but the inspector calls a LOD "unknown", the resolution values are wrong; rebuild with the table above.

## Problems to expect on a first import

| Symptom | Cause | Fix |
|---|---|---|
| Looks like inverted normals | An extra axis flip changed the net transform | Remove the flip; if still wrong, recompute normals from the final winding, never from the centroid |
| UV smear on round parts | Nearest-neighbour UV copy instead of wedge-aware decimation | Use `meshing_decimation_quadric_edge_collapse_with_texture` |
| Holes and floating slices | `fast_simplification` | Use `pymeshlab` |
| Grey, muddy texture | Usually a dark source PNG; matte painted sources look darker under PBR | Sample source pixels before calling it a bug |
| A cable will not attach | Memory LOD lacks `port_input_N` or `port_output_N`, or names differ from what the device script registers | `_shared/models/memory-and-selections-authoring.md` |
| `.p3d` over 20 MB | Decimation skipped | Decimate; real items are 0.5 to 5 MB |

## OBJ in Blender 4 and 5

`bpy.ops.import_scene.obj` and `export_scene.obj` no longer exist. They are `bpy.ops.wm.obj_import` and `bpy.ops.wm.obj_export`, with different parameters: `forward_axis` and `up_axis` in upper case (`"NEGATIVE_Z"`, `"Y"`), `use_split_objects`, `export_selected_objects`. FBX and glTF stay under `bpy.ops.import_scene.fbx` and `.gltf`. Checked in Blender 5.1 (**tool knowledge**). Translate any script written for the old OBJ operators.
