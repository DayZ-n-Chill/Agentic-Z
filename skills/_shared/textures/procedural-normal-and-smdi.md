# Procedural normal and `_smdi` maps

How to turn a height map into a DayZ `_nohq` with a Sobel filter, how to get a height map from a color texture, and how to write a flat `_smdi` per material with the right channel packing.

This is **tool knowledge**, not vanilla data. It is the generator side of `normal-maps.md` (the convention and how to check it) and `smdi-and-levels.md` (the channels and how to set levels against vanilla); where they differ, those files win. `fbm` and the color recipes are in `procedural-textures.md` and `procedural-recipes.md`.

## Normal map from a height map

The output follows the DirectX convention DayZ uses: a surface that rises to the right leans its normal to the left (red below 0.5), and a surface that rises down the image leans its normal up the image, which is green below 0.5 because Y points down the rows.

```python
import numpy as np
from PIL import Image

def height_to_normal(height_map, strength=1.0):
    """height_map: 2D array in [0, 1]. Returns (h, w, 3) normals stored in [0, 1]."""
    height = height_map.astype(np.float32)
    h, w = height.shape

    # 3 x 3 Sobel gradients, Y running down the rows; the one pixel border stays flat.
    grad_x = np.zeros((h, w), dtype=np.float32)
    grad_y = np.zeros((h, w), dtype=np.float32)
    p = height
    grad_x[1:-1, 1:-1] = ((p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:])
                          - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2]))
    grad_y[1:-1, 1:-1] = ((p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:])
                          - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:]))
    grad_x *= strength
    grad_y *= strength

    # A normal leans away from a rising slope, so both gradients are negated.
    # DirectX: +Y points down the rows, the direction grad_y is measured in.
    normals = np.stack([-grad_x, -grad_y, np.ones((h, w), dtype=np.float32)], axis=2)
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)

    # From [-1, 1] to [0, 1] for storage in a texture
    return np.clip((normals + 1.0) / 2.0, 0, 1)

def generate_normal_from_texture(diffuse_path, strength=1.0):
    """A normal map from the luminance of an existing color texture."""
    rgb = np.array(Image.open(diffuse_path).convert('RGB'), dtype=np.float32) / 255.0
    height = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    normals = height_to_normal(height, strength)
    return Image.fromarray((normals * 255).astype(np.uint8), mode='RGB')
```

- `strength` 0.5 gives subtle bumps, 1.0 moderate ones and 2.0 pronounced detail. At 0 the map is flat.
- Storing `+grad_x` and `+grad_y` instead leans red toward the slope and gives green the OpenGL sign, a mix of neither convention. The signs above agree with the convention check of `/dayz-pack-texture` (`normal_convention.py`, in `normal-maps.md`).
- A height map taken from luminance only guesses at relief, since it treats bright as high and cannot tell painted dirt from a groove. Check the result in game; bumps that look pushed in mean the green channel is flipped (`checking-the-look.md`).

## A flat `_smdi` per material

The packing is red at about 255, green the specular strength and blue the gloss, which is roughness inverted. The vanilla battery charger decodes that way: red 255 on every pixel, green 0 to 255, blue 90 to 115 (`P:\DZ\gear\camping\data\battery_charger_smdi.paa`). A packing with red as the specular and blue as a "detail index" is wrong.

```python
from opensimplex import OpenSimplex

SMDI_PRESETS = {  # red fixed at 255; green = specular; blue = gloss
    'painted_metal': (255, 85, 130),
    'brushed_steel': (255, 190, 210),
    'raw_steel': (255, 180, 200),
    'polished_aluminum': (255, 220, 230),
    'rubber': (255, 25, 70),
    'plastic': (255, 40, 90),
    'glass': (255, 230, 245),
    'worn_paint': (255, 70, 100),
}

def generate_smdi_map(width, height, material='painted_metal'):
    r, g, b = SMDI_PRESETS.get(material, SMDI_PRESETS['painted_metal'])
    smdi = np.zeros((height, width, 3), dtype=np.uint8)
    smdi[:, :, 0] = r
    smdi[:, :, 1] = g
    smdi[:, :, 2] = b

    # A slight variation of 0 to 15 on the gloss only, never on the specular
    gen = OpenSimplex(seed=99)
    for y in range(height):
        for x in range(width):
            var = int((gen.noise2(x / width * 2, y / height * 2) + 1) / 2 * 15)
            smdi[y, x, 2] = min(255, int(smdi[y, x, 2]) + var)

    return Image.fromarray(smdi, mode='RGB')
```

The presets sit in the middle of these ranges. They are generic starting points, not vanilla measurements; vanilla paint can sit far lower, so set them against a vanilla asset of the same kind (`smdi-and-levels.md`):

| Material | Red | Green (specular) | Blue (gloss) | Notes |
|---|---|---|---|---|
| Painted metal | 255 | 85 to 95 | 120 to 140 | Standard industrial |
| Brushed steel | 255 | 180 to 200 | 200 to 220 | Directional grain |
| Raw steel | 255 | 180 to 200 | 180 to 200 | A little rougher than brushed |
| Polished aluminum | 255 | 220 to 230 | 230 to 245 | Close to a mirror |
| Rubber | 255 | 25 to 35 | 60 to 90 | Very matte |
| Matte plastic | 255 | 40 to 50 | 80 to 110 | Slightly reflective |
| Glass | 255 | 230 to 245 | 240 to 255 | Highly reflective |
| Worn paint | 255 | 70 to 80 | 100 to 120 | Aged and weathered |

The highlight in game also depends on `specular[]`, `specularPower` and the fresnel stage of the `.rvmat`; values per surface copied from vanilla materials are in `surface-recipes.md`.
