# Baking a normal map: high poly to low poly

The checks a high to low normal bake in Blender must pass before the first pass, so the bake is not repeated once per mistake. It ends with the conversion to a DayZ `_nohq` and the render that proves the bake.

How to read it: this is Blender and bake practice measured on one custom infected model (2026-06-24: five bake rounds hit four separate traps), not a vanilla game fact. The DayZ side of the result, the Y- convention and how a packed `_nohq` reads, is in `normal-maps.md`, and the vanilla texture sizes per folder are in `suffixes-and-sizes.md`.

## Before the bake: geometry

- [ ] **Triangulate the low poly mesh before baking.** Otherwise the bake computes tangents on quads while the engine renders triangles, and the normals are misaligned in game.
- [ ] **The bounding box of the low and the high source match** within 1 mm. If they differ (typical after the low mesh was re-posed or conformed), bake in a pose where they match: a bake proxy with the final low mesh's topology and UVs and the positions it had before the conform or the rig. A tangent space normal map does not depend on the pose when topology and UVs are the same.
- [ ] **Only the high mesh is visible besides the low.** Hide every other object in the scene (other passes, inner bones, proxies). Otherwise the AO and the normal pick up occlusion and surfaces that do not belong.
- [ ] **Low mesh:** clear custom split normals (`customdata_custom_splitnormals_clear`), make the normals consistent pointing out (`normals_make_consistent(inside=False)`) and shade smooth. Without this, normals inherited from a retopology or a voxel remesh stay inconsistent and the AO comes out dark in random places.
- [ ] **High mesh:** do not run `normals_make_consistent` on it. On a mesh that is not watertight (a generated mesh, a voxel retopology) it flips whole shells inward. Keep the high mesh's own normals and shade smooth.

## Before the bake: the target image

- [ ] **Fill the target image with the neutral value first.** A tangent space normal map: RGB (128, 128, 255), the vector (0, 0, 1). An AO map: white (255, 255, 255), or grey (192, 192, 192) if that is your convention.
- [ ] **`use_clear=False`** in the bake settings. Otherwise the texels the bake misses stay black (0, 0, 0), a Normal Map node reads them as a normal pointing inward, and they render black under any light.
- [ ] Image size by the mod's texel target: 1024, 2048 or 4096. 2048 is the usual size for a humanoid.

## Bake settings

- [ ] **Cage 0.025 m and max ray distance 0.05 m** as the default for a humanoid. Raise them for a thick mesh (inner parts close to the torso, a vehicle with separate panels). Lower them if the low mesh intersects itself, which is rare.
- [ ] Bake in Blender's default OpenGL convention and convert to DirectX (Y-) at the end.
- [ ] At least 16 samples for AO; 1 for the normal, which gains nothing from more.

## After the bake: DayZ format

- [ ] `_nohq` is the normal with the **green channel inverted**:

  ```python
  from PIL import Image
  im = Image.open("normal_ogl.png").convert("RGB")
  r, g, b = im.split()
  g = g.point(lambda v: 255 - v)
  Image.merge("RGB", (r, g, b)).save("zombie_body_nohq.png")
  ```

- [ ] `_co` is the base color. If only a generator's placeholder color exists, treat it as a placeholder and texture again on the new UVs.
- [ ] `_smdi` is the specular map, when the material uses one (`smdi-and-levels.md`).
- [ ] Convert the PNG files with `/dayz-pack-texture`. A PNG saved straight from Blender can be refused; the cause and the fix are in `suffixes-and-sizes.md`.

## Data maps in Blender

For any data map (normal, AO, curvature, displacement, ID, masks):

- Set `colorspace_settings.name = 'Non-Color'` on the image.
- Save with the `Standard` view transform, look `None`, exposure 0 and gamma 1.
- Read the written file back and compare it with the buffer you meant to write. The largest error must be within one quantization step. Without that round trip a wrong map ships unnoticed.
- `img.filepath_raw = "folder\file.png"` resolves against the open `.blend` file, not against the working folder, and `save()` raises nothing. A whole bake can be reported as written and be nowhere to be found. Use an absolute path and check `os.path.isfile()` before reporting a file as written.

## Looking at materials in Blender

For previewing a DayZ material before the game:

- In Blender 5.1, use the `RENDERED` shading mode with EEVEE and a light, and capture the 3D view area, not the whole window.
- For a Multi material, keep the second UV set (`tex1`) and reproduce the blend by the mask (`multi-materials.md`).
- On Windows without `python-lzo`, a `.paa` can be decoded with `lzokay` through the 3D viewer tool's shim (`scripts/tools/dayz-3d-viewer/`).

## Proof renders

Before packing, render three views for comparison:

- A: the low mesh with the normal map applied.
- B: the low mesh flat, with no normal map.
- C: the high mesh.

The bake passes when A is clearly closer to C than to B: the normal map adds the high mesh's detail. It fails on blemishes, local rainbows, or a normal that does not show at all (a wrong transform).
