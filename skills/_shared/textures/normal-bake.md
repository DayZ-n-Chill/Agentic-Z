# Normal bake in Blender

What a high poly to low poly normal bake in Blender must get right before the first run, so it is not redone once per mistake, then the conversion to a DayZ `_nohq` and the renders that prove the bake.

This is Blender and baking practice learned on a custom infected model, not a vanilla game fact. The DayZ side of the result, the Y- convention and how a packed `_nohq` reads, is in `normal-maps.md`; the vanilla texture sizes per folder are in `suffixes-and-sizes.md`.

## Geometry before the bake

- **Triangulate the low poly mesh first.** Otherwise the bake works out tangents on quads while the engine draws triangles, and the normals are off in game.
- **Match the bounding boxes** of the low and the high mesh to within 1 mm. If they differ, as they do after the low mesh was posed again or conformed, bake in a pose where they match: a bake copy with the final low mesh's topology and UVs at the positions it had before the conform or the rig. A tangent space normal map does not depend on the pose when topology and UVs are the same.
- **Show only the high mesh besides the low.** Hide everything else in the scene (other passes, inner bones, proxies), or the AO and the normal pick up surfaces that do not belong.
- **Clean the low mesh:** clear custom split normals (`customdata_custom_splitnormals_clear`), make the normals point out consistently (`normals_make_consistent(inside=False)`) and shade smooth. Normals left over from a retopology or a voxel remesh otherwise stay mixed and the AO goes dark in random places.
- **Leave the high mesh's normals alone.** Never run `normals_make_consistent` on it: on a mesh that is not watertight, such as a generated mesh or a voxel retopology, it flips whole shells inward. Shade it smooth and keep its own normals.

## The target image

- **Fill it with the neutral value first.** For a tangent space normal map that is RGB (128, 128, 255), the vector (0, 0, 1); for an AO map white (255, 255, 255), or grey (192, 192, 192) if that is your convention.
- **Set `use_clear=False`** in the bake settings. Otherwise texels the bake misses stay black (0, 0, 0), a Normal Map node reads them as a normal pointing inward, and they render black under any light.
- Size the image by the mod's texel target: 1024, 2048 or 4096. 2048 is the usual size for a humanoid.

## Bake settings

- **Cage 0.025 m and max ray distance 0.05 m** suit a humanoid. Raise both for a thick mesh (inner parts close to the torso, a vehicle with separate panels); lower them if the low mesh crosses itself, which is rare.
- Bake in Blender's default OpenGL convention and convert to DirectX (Y-) at the end.
- Use at least 16 samples for AO; the normal gains nothing from more than 1.

## Into DayZ format

A `_nohq` is the baked normal with its green channel inverted:

```python
from PIL import Image
im = Image.open("normal_ogl.png").convert("RGB")
r, g, b = im.split()
g = g.point(lambda v: 255 - v)
Image.merge("RGB", (r, g, b)).save("zombie_body_nohq.png")
```

- `_co` is the base color. If all you have is a generator's placeholder color, treat it as a placeholder and texture again on the new UVs.
- `_smdi` is the specular map, when the material uses one (`smdi-and-levels.md`).
- Convert the PNG files with `/dayz-pack-texture`. A PNG saved straight from Blender can be refused; cause and fix are in `suffixes-and-sizes.md`.

## Saving data maps from Blender

For every data map (normal, AO, curvature, displacement, ID, masks):

- Set `colorspace_settings.name = 'Non-Color'` on the image.
- Save with the `Standard` view transform, look `None`, exposure 0 and gamma 1.
- Read the written file back and compare it with the buffer you meant to write; the largest error must be one quantization step or less. Without that round trip a wrong map ships unnoticed.
- `img.filepath_raw = "folder\file.png"` resolves against the open `.blend` file, not the working folder, and `save()` raises nothing, so a bake can be reported as written and be nowhere. Use an absolute path and check `os.path.isfile()` before you say a file was written.

## Previewing in Blender

- In Blender 5.1, preview with the `RENDERED` shading mode in EEVEE with a light, and capture the 3D view area, not the whole window.
- For a Multi material, keep the second UV set (`tex1`) and reproduce the blend through the mask (`multi-materials.md`).
- On Windows without `python-lzo`, the 3D viewer tool (`scripts/tools/dayz-3d-viewer/`) decodes a `.paa` with `lzokay` through its shim.

## Proving the bake

Before packing, render three views side by side:

1. The low mesh with the normal map.
2. The low mesh flat, with no normal map.
3. The high mesh.

The bake passes when the first is clearly closer to the third than to the second, because the normal map carries the high mesh's detail. It fails on blotches, local rainbows, or a normal that does not show at all, which points to a wrong transform.
