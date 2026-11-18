# Procedural material recipes

Covers ready recipes for the surfaces of electrical and industrial props: painted metal, brushed steel, rubber, a rust overlay, baked AO multiplied into the color, and a full script that writes all three maps for an electrical box.

This is **tool knowledge**, not vanilla data. It uses `fbm` and the blend functions from `procedural-textures.md`, and `height_to_normal` and `generate_smdi_map` from `procedural-normal-and-smdi.md`. The `_smdi` values given per recipe are generic starting points; set them against a vanilla asset of the same kind (`smdi-and-levels.md`).

## Two helpers

Every recipe samples FBM over the image and works with distance to the border:

```python
import numpy as np
from PIL import Image
from opensimplex import OpenSimplex

def noise_field(gen, width, height, sx, sy, **fbm_args):
    """FBM sampled at (x / width * sx, y / height * sy), normalized to [0, 1]."""
    field = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            field[y, x] = (fbm(gen, x / width * sx, y / height * sy, **fbm_args) + 1.0) / 2.0
    return field

def edge_distance(width, height):
    """Pixels from each pixel to the nearest border of the image."""
    ys, xs = np.mgrid[0:height, 0:width]
    return np.minimum.reduce([xs, ys, width - xs, height - ys]).astype(np.float32)
```

`noise_field` calls the noise once per pixel and octave, which takes a while at 1024 x 1024 in plain Python. That is fine for a texture made once; work at a smaller size while iterating.

## Painted metal

Industrial grey or green paint for electrical boxes, cabinets and control panels, with factory streaks and worn edges:

```python
def generate_painted_metal(width=512, height=512, seed=42):
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32) * np.array([0.28, 0.28, 0.30], dtype=np.float32)

    # Large color variation of plus or minus 0.08
    variation = noise_field(gen, width, height, 2, 2, octaves=3, gain=0.5) * 0.16 - 0.08
    canvas = np.clip(canvas + variation[:, :, None], 0, 1)

    # Streaks running top to bottom, as paint is applied
    streaks = noise_field(gen, width, height, 0.08, 0.2, octaves=4)
    canvas = blend_lerp(canvas, (streaks * 0.95)[:, :, None], 0.12)

    # Grain of the metal showing through
    grain = noise_field(gen, width, height, 2.0, 2.0, octaves=5, gain=0.6)
    canvas = blend_overlay(canvas, grain[:, :, None], 0.08)

    # Lighter worn edges: full at the border, none from 30 % inward
    edge_mask = np.maximum(0.0, 1.0 - edge_distance(width, height) / max(width, height) / 0.3)
    canvas = blend_lerp(canvas, 0.40, (edge_mask * 0.08)[:, :, None])

    return np.clip(canvas, 0, 1)
```

`_smdi`: red 255, green 85 to 95 (slightly reflective), blue 120 to 140 (a semi matte factory finish).

## Brushed steel or aluminum

Strong grain in one direction and a high reflection:

```python
def generate_brushed_steel(width=512, height=512, direction='horizontal', seed=42):
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32) * np.array([0.50, 0.50, 0.52], dtype=np.float32)

    # Grain squeezed along one axis
    if direction == 'horizontal':
        grain = noise_field(gen, width, height, 0.1, 8.0, octaves=6, gain=0.5)
    else:
        grain = noise_field(gen, width, height, 8.0, 0.1, octaves=6, gain=0.5)
    canvas = blend_overlay(canvas, grain[:, :, None], 0.25)

    # Faint scratches
    micro = noise_field(gen, width, height, 3.0, 3.0, octaves=4, gain=0.6)
    canvas = blend_soft_light(canvas, micro[:, :, None], 0.05)

    return np.clip(canvas, 0, 1)
```

`_smdi`: red 255, green 180 to 200 (highly reflective), blue 200 to 220 (very smooth).

## Rubber or plastic

Matte and smooth, for cable insulation and similar parts, with almost no metallic look:

```python
def generate_rubber(width=512, height=512, color=(0.15, 0.15, 0.18), seed=42):
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32) * np.array(color, dtype=np.float32)

    # Smooth molding variation of plus or minus 0.04
    smooth = noise_field(gen, width, height, 0.5, 0.5, octaves=2, gain=0.4) * 0.08 - 0.04
    canvas = np.clip(canvas + smooth[:, :, None], 0, 1)

    # A very faint, non metallic grain
    grain = noise_field(gen, width, height, 1.0, 1.0, octaves=3, gain=0.5)
    canvas = blend_lerp(canvas, grain[:, :, None], 0.03)

    return np.clip(canvas, 0, 1)
```

`_smdi`: red 255, green 20 to 40 (not reflective), blue 60 to 100 (rough).

## Rust overlay

Rust patches to lay over the base paint. `density` sets how much of the surface rusts:

```python
def generate_rust_overlay(width=512, height=512, density=0.15, seed=42):
    gen = OpenSimplex(seed=seed)

    # Where rust appears: noise above a threshold
    noise = noise_field(gen, width, height, 1.5, 1.5, octaves=5, gain=0.6)
    rust_mask = np.maximum(0, noise - (1.0 - density)) / density

    # Orange brown, varying between 0.7 and 1.0 inside the patches
    rust_var = noise_field(gen, width, height, 4.0, 4.0, octaves=4, gain=0.5) * 0.3 + 0.7
    rust_color = np.array([0.65, 0.35, 0.10])
    rust = rust_color[None, None, :] * (rust_mask * rust_var)[:, :, None]

    return rust, rust_mask
```

Multiply it into the base, keeping the base where there is no rust:

```python
base = generate_painted_metal()
rust, rust_mask = generate_rust_overlay()
result = blend_multiply(base, rust + (1.0 - rust_mask)[:, :, None])
```

## Baked AO in the color map

If you baked AO in Blender, multiply it into the color map to darken recesses at no geometry cost:

```python
def integrate_ao(diffuse_path, ao_path):
    diffuse = Image.open(diffuse_path).convert('RGB')
    ao = Image.open(ao_path).convert('L').resize(diffuse.size, Image.Resampling.LANCZOS)
    diffuse_array = np.array(diffuse, dtype=np.float32) / 255.0
    ao_array = np.array(ao, dtype=np.float32) / 255.0
    result = diffuse_array * ao_array[:, :, None]
    return Image.fromarray((result * 255).astype(np.uint8), mode='RGB')
```

Super also has its own stage for a baked ambient shadow, an `_as` texture in `Stage4`, as the vanilla wooden case does (`P:\DZ\gear\camping\data\wooden_case.rvmat:47`; stage roles in `rvmat-stages.md`). Multiplying AO into the `_co` is the simpler route for a small prop.

## An electrical box, start to finish

A full script that writes all three maps at 512 x 512 for a typical electrical enclosure:

```python
import os

def generate_electrical_box_textures(output_dir='textures', seed=42):
    width, height = 512, 512
    gen = OpenSimplex(seed=seed)
    os.makedirs(output_dir, exist_ok=True)

    # Color: painted metal, small rust patches, light scuffs
    diffuse = generate_painted_metal(width, height, seed)
    rust, rust_mask = generate_rust_overlay(width, height, density=0.08, seed=seed + 1)
    diffuse = blend_multiply(diffuse, rust + (1.0 - rust_mask)[:, :, None])
    scuffs = (noise_field(gen, width, height, 3, 3, octaves=4, gain=0.6) > 0.85).astype(np.float32)
    diffuse = np.clip(blend_lerp(diffuse, 0.45, (scuffs * 0.06)[:, :, None]), 0, 1)
    Image.fromarray((diffuse * 255).astype(np.uint8), mode='RGB').save(f'{output_dir}/box_co.png')

    # Normal: height from the luminance of the color
    height_map = 0.299 * diffuse[:, :, 0] + 0.587 * diffuse[:, :, 1] + 0.114 * diffuse[:, :, 2]
    normals = height_to_normal(height_map, strength=1.2)
    Image.fromarray((normals * 255).astype(np.uint8), mode='RGB').save(f'{output_dir}/box_nohq.png')

    # Specular and gloss
    generate_smdi_map(width, height, material='painted_metal').save(f'{output_dir}/box_smdi.png')
```

Convert the three PNG files with `/dayz-pack-texture`, then build on the result according to how it looks in the engine (`checking-the-look.md`).
