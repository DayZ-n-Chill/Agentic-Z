# Procedural texture generation for DayZ models

How to generate the `_co`, `_nohq` and `_smdi` maps of a generated model in Python with coherent noise: the map formats, OpenSimplex and FBM, compositing in layers, material recipes, the normal map from a height map, specular values per material, and the mistakes that make a texture look procedural.

What is checked and what is not: this is tool knowledge (Pillow, numpy, OpenSimplex) and the source author's recipes for the LF_PowerGrid mod's electrical objects; a pixel recipe cannot be checked on `P:\`. The map formats were compared with the textures pack, which is read from the vanilla TexConvert settings and vanilla files: suffixes, channel packing and sizes are in `_shared/textures/suffixes-and-sizes.md`, the `.rvmat` stages the maps go into are in `_shared/textures/rvmat-stages.md`, and values per surface are in `_shared/textures/surface-recipes.md`. Where this file and that pack differ, the pack wins. The code blocks were run once with numpy 2.4 and Pillow 12, at a small image size and with a stand-in for the OpenSimplex noise function, to confirm that they execute and that the normal map signs are as described.

The textures are generated as `.png` and converted to `.paa` with `/dayz-pack-texture`. Faces in the `.p3d` name the `.paa` (`critical-rules.md`, rule 8).

## Contents

1. [DayZ texture map types](#1-dayz-texture-map-types)
2. [OpenSimplex noise fundamentals](#2-opensimplex-noise-fundamentals)
3. [Fractional Brownian motion (FBM)](#3-fractional-brownian-motion-fbm)
4. [Compositing in layers](#4-compositing-in-layers-the-key-to-realism)
5. [Material recipes](#5-material-recipes)
6. [Normal map generation](#6-normal-map-generation)
7. [SMDI map generation and values](#7-smdi-map-generation-and-values)
8. [Ambient occlusion](#8-ambient-occlusion)
9. [Complete example: an industrial electrical box](#9-complete-example-an-industrial-electrical-box)
10. [Common mistakes](#10-common-mistakes-and-solutions)
11. [Tips for industrial quality](#11-tips-for-industrial-quality)

## 1. DayZ texture map types

All procedural generation targets these maps.

### Color map (`_co.png`)

- **Purpose:** the RGB diffuse color that sets the base appearance.
- **Resolution:** 512x512 for small objects (switches, boxes), 1024x1024 for large objects.
- **Format:** PNG in RGB mode. A `_co` has no alpha; a surface that needs transparency is a `_ca` instead, which keeps its alpha channel (`_shared/textures/suffixes-and-sizes.md`). The source's wording, "DayZ tools ignore alpha", holds for `_co` only.
- **Value range:** 0 to 255 per channel.
- **Use:** what you see in game, before lighting.

### Normal map (`_nohq.png`)

- **Purpose:** encodes surface detail without adding geometry.
- **Format:** PNG, RGB (red is X, green is Y, blue is Z).
- **Convention:** DirectX, with Y pointing down the image (green down), the same as 3ds Max and the Unreal default. A normal map from an OpenGL tool (Y up) needs its green channel inverted before packing. This is tool knowledge from the source's texture pipeline, which measures it; the source's own text in this file said "OpenGL standard (Y+ is up)", and its other files and its test say DirectX. In game, bumps that look pushed in mean the green channel is flipped (`_shared/textures/checking-the-look.md`).
- **Strength:** typical range 0.5 to 2.0.
- **Generation:** derived from a height map with Sobel filtering (section 6).
- **Key fact:** it removes the need for high polygon detail.

### Specular map (`_smdi.png`)

- **Purpose:** controls the highlight in the Super shader.
- **Format:** PNG in RGB mode.
- **Packing:** red is unused and kept at 255, green is the specular strength, blue is the gloss. Vanilla's TexConvert settings force red to 1 for this suffix and keep green and blue (`_shared/textures/suffixes-and-sizes.md`), and the source measured red at 255 on four LF_PowerGrid `_smdi` textures. The channel meanings in full are in `skills/dayz-texture-pipeline/references/map-conventions.md`; this file keeps its generator presets aligned to that packing.
- **R channel (about 255, fixed):** keep it near white unless cloning a vanilla exception.
- **G channel (specular strength):** 0 is matte, 255 is mirror like.
  - Painted metal: about 80 to 100
  - Raw steel: about 180 to 200
  - Rubber: about 20 to 40
  - Glass or clear plastic: about 220 to 240
- **B channel (gloss, roughness inverted):** 0 is extremely rough, 255 is perfectly smooth.
  - Weathered paint: about 100 to 140
  - Fresh paint: about 150 to 180
  - Polished metal: about 200 to 240
  - Rough rubber: about 60 to 100
- **Note:** do **not** treat B as a "detail index". That packing is wrong for a DayZ `_smdi`; leave R near white and put the gloss in B.

### Resolution guidelines

- **Small objects** (switches, adapters, knobs): 512x512
- **Medium objects** (electrical boxes, panels): 1024x1024
- **Large objects** (barrels, machinery): 1024x1024 or higher
- **Performance:** 512x512 is enough for most small objects. Every side is a power of two, and `_nohq` and `_smdi` are the size of their `_co`; what vanilla picks per folder is in `_shared/textures/suffixes-and-sizes.md`.

---

## 2. OpenSimplex noise fundamentals

OpenSimplex is a gradient based coherent noise function, better suited to textures than Perlin noise. It gives smooth, natural looking variation.

### Installation

```cmd
python -m pip install opensimplex pillow numpy
```

### Basic usage

```python
from opensimplex import OpenSimplex

# Create a generator with a seed so the result can be reproduced
gen = OpenSimplex(seed=42)

# Sample noise at 2D coordinates
value = gen.noise2(x * frequency, y * frequency)

# Output range: [-1.0, 1.0]
# Normalize to [0, 1]: normalized = (value + 1.0) / 2.0
```

### Key parameters

**Frequency** controls the scale of the noise features:

- Low (0.01 to 0.05): large, slowly varying features (overall color)
- Medium (0.05 to 0.2): mid scale detail (paint streaks, patches)
- High (0.2 to 1.0): fine texture (grain, micro roughness)
- Very high (1.0 and up): detail below a pixel

**Seed** decides the pattern:

- Different seeds give entirely different patterns.
- The same seed always gives the same pattern.
- Use `seed=np.random.randint(0, 1000000)` for variety.

### Important properties

- **Continuous:** slightly different input coordinates give slightly different values (smooth gradients).
- **Deterministic:** the same input always gives the same output.
- **Non repeating:** the effective period is very large; no visible tiling artifacts.
- **Range:** always [-1, 1]; normalize by hand.

---

## 3. Fractional Brownian motion (FBM)

FBM layers several octaves of noise at rising frequencies and falling amplitudes, which creates natural looking complexity.

### Complete working function

```python
def fbm(gen, x, y, octaves=6, lacunarity=2.0, gain=0.5):
    """
    Fractional Brownian motion: several layers of noise summed.

    Args:
        gen: OpenSimplex generator instance
        x, y: coordinates to sample
        octaves: number of noise layers (more = more detail)
        lacunarity: frequency multiplier per octave (2.0 is standard)
        gain: amplitude decay per octave (persistence; 0.5 is standard)

    Returns:
        float: FBM value, normalized to about [-1, 1]
    """
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_amplitude = 0.0

    for _ in range(octaves):
        value += amplitude * gen.noise2(x * frequency, y * frequency)
        max_amplitude += amplitude
        frequency *= lacunarity
        amplitude *= gain

    # Normalize to approximately [-1, 1]
    return value / max_amplitude if max_amplitude > 0 else 0.0
```

### Parameter effects

**octaves** (typical: 4 to 8)

- 4 octaves: smooth, large scale variation
- 6 octaves: a good balance for most objects
- 8 or more: intricate detail, expensive to compute

**lacunarity** (typical: 2.0 to 2.5)

- Controls how fast the frequency rises per octave
- 2.0: standard; each octave is twice as fine
- 1.5: slower rise; a smoother result
- 2.5: faster rise; more variety of detail

**gain, or persistence** (typical: 0.4 to 0.6)

- Controls how fast the amplitude falls per octave
- 0.5: standard; each octave contributes half of the one before
- 0.6: more amplitude at high frequencies; more visible detail
- 0.4: less amplitude; a smoother overall look

### Typical combinations

```python
# Smooth, flowing textures (paint variation)
fbm(gen, x, y, octaves=4, lacunarity=2.0, gain=0.5)

# Detailed, grainy textures (rust, corrosion)
fbm(gen, x, y, octaves=7, lacunarity=2.2, gain=0.6)

# Subtle variation (worn metal)
fbm(gen, x, y, octaves=5, lacunarity=2.0, gain=0.4)
```

---

## 4. Compositing in layers: the key to realism

The difference between a generic texture and an industrial quality one is **layering**. Each layer has one purpose and is composed with a blend mode.

### Layering strategy

**Layer 1: base color**

- Purpose: overall color and large scale variation
- Frequency: 0.02 to 0.05 (low)
- Octaves: 3 to 4
- Effect: the foundation; sets the dominant color
- Example: dark gray (RGB 60, 60, 70) with ±10 % variation

**Layer 2: flow or streak pattern**

- Purpose: directional wear (paint flow, application marks)
- Frequency: Y axis compressed to 0.1, X axis stretched to 0.02
- Octaves: 4
- Effect: a streaky, directional pattern
- Blend: overlay or multiply
- Example: the patterns of factory paint application

**Layer 3: grain**

- Purpose: the surface's micro texture (metal grain, plastic texture)
- Frequency: 0.3 to 0.5 (medium to high)
- Octaves: 5
- Effect: visible but subtle grain
- Blend: overlay, low opacity (0.2 to 0.4)
- Example: brushed metal or molded plastic

**Layer 4: micro variation**

- Purpose: detail below a pixel (dust, fingerprints)
- Frequency: 1.0 to 2.0 (very high)
- Octaves: 3
- Effect: almost invisible; adds realism
- Amplitude: 0.02 to 0.05 (very low)
- Blend: soft light or overlay, minimal opacity

**Layer 5: wear and edge damage**

- Purpose: lighter areas at edges where paint or coating wore away
- Based on: a position mask (edges) plus noise
- Effect: reveals the material underneath at edges
- Blend: additive or overlay
- Example: light gray where dark paint is worn

**Layer 6: sparse details**

- Purpose: random imperfections (rust spots, dirt, scratches)
- Frequency: 0.1 to 0.2 with a threshold
- Effect: discrete spots and marks
- Blend: multiply (for dark spots) or screen (for light marks)
- Example: orange brown rust over the base color

### Blend mode functions

Every blend takes an optional `opacity` (1.0 applies the blend fully, 0.0 leaves `base` unchanged), which the recipes below use. `base` and `layer` are numpy arrays of the same shape with values in [0, 1].

```python
import numpy as np

def blend_lerp(base, layer, alpha):
    """Linear interpolation: result = base * (1 - alpha) + layer * alpha"""
    return base * (1.0 - alpha) + layer * alpha

def blend_multiply(base, layer, opacity=1.0):
    """Darkens: result = base * layer"""
    return blend_lerp(base, base * layer, opacity)

def blend_screen(base, layer, opacity=1.0):
    """Lightens: result = 1 - (1 - base) * (1 - layer)"""
    return blend_lerp(base, 1.0 - (1.0 - base) * (1.0 - layer), opacity)

def blend_overlay(base, layer, opacity=1.0):
    """Conditional: multiply if base < 0.5, screen otherwise"""
    result = np.where(
        base < 0.5,
        2.0 * base * layer,
        1.0 - 2.0 * (1.0 - base) * (1.0 - layer)
    )
    return blend_lerp(base, result, opacity)

def blend_soft_light(base, layer, opacity=1.0):
    """Subtle overlay: useful for grain"""
    lifted = np.where(
        base <= 0.25,
        ((16.0 * base - 12.0) * base + 4.0) * base,
        np.sqrt(base)
    )
    result = np.where(
        layer <= 0.5,
        base - (1.0 - 2.0 * layer) * base * (1.0 - base),
        base + (2.0 * layer - 1.0) * (lifted - base)
    )
    return blend_lerp(base, result, opacity)
```

### Complete composition example

```python
import numpy as np
from PIL import Image
from opensimplex import OpenSimplex

def composite_texture(width, height, seed=42):
    """Generate a complete texture from several layers."""
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32) * 0.5

    # Layer 1: base color (dark gray with variation)
    base_layer = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 2, y / height * 2, octaves=3, gain=0.5)
            base_layer[y, x] = (val + 1.0) / 2.0

    base_color = np.array([0.25, 0.25, 0.27], dtype=np.float32)  # Dark gray
    canvas *= base_color
    canvas *= blend_lerp(np.ones_like(base_layer), base_layer, 0.3)[:, :, None]

    # Layer 2: directional streaks
    streak_layer = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 0.05, y / height * 0.3, octaves=4)
            streak_layer[y, x] = (val + 1.0) / 2.0

    for c in range(3):
        canvas[:, :, c] = blend_overlay(canvas[:, :, c], streak_layer, 0.4)

    # Layer 3: grain
    grain_layer = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 5, y / height * 5, octaves=5, gain=0.5)
            grain_layer[y, x] = (val + 1.0) / 2.0

    for c in range(3):
        canvas[:, :, c] = blend_lerp(canvas[:, :, c], grain_layer, 0.15)

    # Layer 4: edge wear (lighter at edges)
    edge_mask = np.ones((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            dist_from_edge = min(x, y, width - x, height - y) / min(width, height)
            edge_mask[y, x] = dist_from_edge

    wear_amount = 0.05
    for c in range(3):
        canvas[:, :, c] = blend_lerp(canvas[:, :, c], edge_mask, wear_amount)

    # Clamp to [0, 1]
    canvas = np.clip(canvas, 0.0, 1.0)

    return canvas
```

The loops call the noise function once per pixel and octave, which takes a while at 1024x1024 in plain Python. That is acceptable for a texture generated once; compute at a smaller size while iterating.

---

## 5. Material recipes

Complete recipes for the surfaces of common electrical objects.

### Recipe 1: painted metal (industrial gray or green)

Common for electrical boxes, cabinets and control panels.

```python
def generate_painted_metal(width=512, height=512, seed=42):
    """Industrial painted metal with edge wear."""
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32)

    # Base: dark gray (0.28, 0.28, 0.30)
    base_color = np.array([0.28, 0.28, 0.30], dtype=np.float32)
    canvas *= base_color

    # Large scale color variation (±0.08)
    variation = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 2, y / height * 2, octaves=3, gain=0.5)
            variation[y, x] = (val + 1.0) / 2.0
    variation = variation * 0.16 - 0.08  # Scale to [-0.08, 0.08]
    for c in range(3):
        canvas[:, :, c] = np.clip(canvas[:, :, c] + variation, 0, 1)

    # Paint streak direction (top to bottom, factory application)
    streaks = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 0.08, y / height * 0.2, octaves=4)
            streaks[y, x] = (val + 1.0) / 2.0
    streak_amount = 0.12
    for c in range(3):
        canvas[:, :, c] = blend_lerp(canvas[:, :, c], streaks * 0.95, streak_amount)

    # Grain (the metal underneath showing through)
    grain = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 2.0, y / height * 2.0, octaves=5, gain=0.6)
            grain[y, x] = (val + 1.0) / 2.0
    for c in range(3):
        canvas[:, :, c] = blend_overlay(canvas[:, :, c], grain, 0.08)

    # Edge wear (light gray where paint is worn, revealing metal)
    edge_mask = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            dist = min(x, y, width - x, height - y) / max(width, height)
            edge_mask[y, x] = 1.0 - (dist * 0.3)  # Wear extends 30% inward
    edge_color = 0.40  # Lighter gray
    for c in range(3):
        canvas[:, :, c] = blend_lerp(canvas[:, :, c], edge_color, edge_mask * 0.08)

    canvas = np.clip(canvas, 0, 1)
    return canvas
```

**SMDI for painted metal:**

- R: 255
- G (specular): 85 to 95 (slightly reflective)
- B (gloss): 120 to 140 (a semi matte factory finish)

### Recipe 2: brushed steel or aluminum

Directional grain for metal surfaces, high reflectivity.

```python
def generate_brushed_steel(width=512, height=512, direction='horizontal', seed=42):
    """Brushed metal with strong directional grain."""
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32)

    # Base: medium gray (0.50, 0.50, 0.52)
    base_color = np.array([0.50, 0.50, 0.52], dtype=np.float32)
    canvas *= base_color

    # Strong directional grain (compressed on one axis)
    grain = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            if direction == 'horizontal':
                val = fbm(gen, x / width * 0.1, y / height * 8.0, octaves=6, gain=0.5)
            else:  # vertical
                val = fbm(gen, x / width * 8.0, y / height * 0.1, octaves=6, gain=0.5)
            grain[y, x] = (val + 1.0) / 2.0
    for c in range(3):
        canvas[:, :, c] = blend_overlay(canvas[:, :, c], grain, 0.25)

    # Micro variation (subtle scratches)
    micro = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 3.0, y / height * 3.0, octaves=4, gain=0.6)
            micro[y, x] = (val + 1.0) / 2.0
    for c in range(3):
        canvas[:, :, c] = blend_soft_light(canvas[:, :, c], micro, 0.05)

    canvas = np.clip(canvas, 0, 1)
    return canvas
```

**SMDI for brushed steel:**

- R: 255
- G (specular): 180 to 200 (highly reflective)
- B (gloss): 200 to 220 (very smooth)

### Recipe 3: rubber or plastic (cable insulation)

Matte, smooth, hardly any metallic look.

```python
def generate_rubber(width=512, height=512, color=(0.15, 0.15, 0.18), seed=42):
    """Matte rubber or plastic insulation."""
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32)

    # Base: dark matte color (black rubber by default)
    base_color = np.array(color, dtype=np.float32)
    canvas *= base_color

    # Smooth, low frequency variation (molding patterns)
    smooth_var = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 0.5, y / height * 0.5, octaves=2, gain=0.4)
            smooth_var[y, x] = (val + 1.0) / 2.0
    smooth_var = smooth_var * 0.08 - 0.04
    for c in range(3):
        canvas[:, :, c] = np.clip(canvas[:, :, c] + smooth_var, 0, 1)

    # Very subtle grain (not metallic)
    grain = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 1.0, y / height * 1.0, octaves=3, gain=0.5)
            grain[y, x] = (val + 1.0) / 2.0
    for c in range(3):
        canvas[:, :, c] = blend_lerp(canvas[:, :, c], grain, 0.03)

    canvas = np.clip(canvas, 0, 1)
    return canvas
```

**SMDI for rubber:**

- R: 255
- G (specular): 20 to 40 (not reflective)
- B (gloss): 60 to 100 (a rough surface)

### Recipe 4: rust and corrosion overlay

Apply over the base paint for realistic weathering.

```python
def generate_rust_overlay(width=512, height=512, density=0.15, seed=42):
    """Rust patches to overlay on painted metal."""
    gen = OpenSimplex(seed=seed)
    rust = np.zeros((height, width, 3), dtype=np.float32)

    # Rust distribution from noise with a threshold
    rust_mask = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 1.5, y / height * 1.5, octaves=5, gain=0.6)
            noise_val = (val + 1.0) / 2.0
            rust_mask[y, x] = max(0, noise_val - (1.0 - density)) / density

    # Orange brown rust color: (0.65, 0.35, 0.10)
    rust_color = np.array([0.65, 0.35, 0.10])

    # Variation within the rust patches
    rust_var = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 4.0, y / height * 4.0, octaves=4, gain=0.5)
            rust_var[y, x] = (val + 1.0) / 2.0
    rust_var = rust_var * 0.3 + 0.7  # Range [0.7, 1.0]

    for c in range(3):
        rust[:, :, c] = rust_color[c] * rust_mask * rust_var

    return rust, rust_mask
```

**Usage:** composite the rust overlay onto the base texture.

```python
base = generate_painted_metal()
rust, rust_mask = generate_rust_overlay()
result = blend_multiply(base, rust + (1.0 - rust_mask)[:, :, None])
```

---

## 6. Normal map generation

Convert a height map to surface normals with Sobel filtering. The output is in the DirectX convention DayZ uses: a surface that rises to the right leans its normal to the left (red below 0.5), and a surface that rises down the image leans its normal up the image, which in a map whose Y axis points down the image is green below 0.5.

```python
def height_to_normal(height_map, strength=1.0):
    """
    Convert a height map to a DirectX convention normal map with Sobel filtering.

    Args:
        height_map: 2D numpy array [0, 1], the surface height
        strength: bump intensity (0.5 to 2.0 typical)

    Returns:
        3D numpy array [height, width, 3], normals stored as [0, 1]
    """
    height = height_map.astype(np.float32)
    h, w = height.shape

    # Sobel kernels for the X and Y gradients (Y runs down the image rows)
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)

    # Gradients by convolution
    grad_x = np.zeros((h, w), dtype=np.float32)
    grad_y = np.zeros((h, w), dtype=np.float32)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            patch = height[y-1:y+2, x-1:x+2]
            grad_x[y, x] = np.sum(patch * sobel_x)
            grad_y[y, x] = np.sum(patch * sobel_y)

    # Apply the strength
    grad_x *= strength
    grad_y *= strength

    # A normal leans away from the rising slope, so both gradients are negated.
    # DirectX: +Y points down the rows, the direction grad_y is measured in.
    # For an OpenGL (Y up) map the Y line would be +grad_y.
    normals = np.zeros((h, w, 3), dtype=np.float32)
    normals[:, :, 0] = -grad_x  # X component (red)
    normals[:, :, 1] = -grad_y  # Y component (green, Y down)
    normals[:, :, 2] = 1.0      # Z component (blue, out of the surface)

    # Normalize to unit vectors
    lengths = np.sqrt(
        normals[:, :, 0]**2 + normals[:, :, 1]**2 + normals[:, :, 2]**2
    )
    lengths[lengths == 0] = 1.0  # Avoid division by zero

    normals[:, :, 0] /= lengths
    normals[:, :, 1] /= lengths
    normals[:, :, 2] /= lengths

    # Convert from [-1, 1] to [0, 1] for storage in a texture
    normals = (normals + 1.0) / 2.0
    normals = np.clip(normals, 0, 1)

    return normals

def generate_normal_from_texture(diffuse_path, strength=1.0):
    """Generate a normal map from an existing diffuse texture."""
    img = Image.open(diffuse_path).convert('RGB')
    rgb = np.array(img, dtype=np.float32) / 255.0

    # Height map from luminance
    height = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

    normals = height_to_normal(height, strength)
    normals_uint8 = (normals * 255).astype(np.uint8)

    return Image.fromarray(normals_uint8, mode='RGB')
```

**Key parameters:**

- **strength:** 0.5 gives subtle bumps, 1.0 moderate, 2.0 pronounced detail.
- **DayZ convention:** the green channel encodes Y pointing down the image (DirectX).

The source's function stored `+grad_x` and `+grad_y`. That leaned red toward the rising slope and gave green the OpenGL sign, a mix of neither convention; the signs above follow the texture pipeline's convention test. A height map taken from luminance is a guess at relief anyway (bright is treated as high), so check the result in game.

---

## 7. SMDI map generation and values

The `_smdi` map controls the highlight. The packing is R about 255, G specular, B gloss (section 1). Generate values per material with that packing. The presets below were rebuilt by the source from an older, wrong packing (R as specular, B as "detail index") by moving the old R to G and the old G to B, after it measured vanilla style `_smdi` textures.

```python
def generate_smdi_map(width, height, material='painted_metal'):
    """Generate an SMDI map for the given material.

    Packing: R about 255 (keep near white), G = specular, B = gloss
    (roughness inverted).
    """

    # Material presets (R fixed at 255; G = specular; B = gloss)
    materials = {
        'painted_metal': {'r': 255, 'g': 85, 'b': 130},
        'brushed_steel': {'r': 255, 'g': 190, 'b': 210},
        'raw_steel': {'r': 255, 'g': 180, 'b': 200},
        'polished_aluminum': {'r': 255, 'g': 220, 'b': 230},
        'rubber': {'r': 255, 'g': 25, 'b': 70},
        'plastic': {'r': 255, 'g': 40, 'b': 90},
        'glass': {'r': 255, 'g': 230, 'b': 245},
        'worn_paint': {'r': 255, 'g': 70, 'b': 100},
    }

    props = materials.get(material, materials['painted_metal'])

    # A solid SMDI map with slight variation on the gloss (B)
    smdi = np.zeros((height, width, 3), dtype=np.uint8)
    smdi[:, :, 0] = props['r']  # R about 255 (fixed, near white)
    smdi[:, :, 1] = props['g']  # Specular
    smdi[:, :, 2] = props['b']  # Gloss

    # Optional: subtle variation on the gloss (channel 2), not on the specular
    gen = OpenSimplex(seed=99)
    for y in range(height):
        for x in range(width):
            var = gen.noise2(x / width * 2, y / height * 2)
            var = int((var + 1) / 2 * 15)  # 0 to 15 added
            smdi[y, x, 2] = min(255, int(smdi[y, x, 2]) + var)

    return Image.fromarray(smdi, mode='RGB')
```

**SMDI values per material** (the generator's bases use midpoints):

| Material | R | G (specular) | B (gloss) | Notes |
|---|---|---|---|---|
| Painted metal | 255 | 85 to 95 | 120 to 140 | Standard industrial; measured |
| Brushed steel | 255 | 180 to 200 | 200 to 220 | Directional grain |
| Raw steel | 255 | 180 to 200 | 180 to 200 | Slightly rougher than brushed |
| Polished aluminum | 255 | 220 to 230 | 230 to 245 | Mirror like |
| Rubber | 255 | 25 to 35 | 60 to 90 | Very matte |
| Plastic (matte) | 255 | 40 to 50 | 80 to 110 | Slightly reflective |
| Glass | 255 | 230 to 245 | 240 to 255 | Highly reflective |
| Worn paint | 255 | 70 to 80 | 100 to 120 | Aged, weathered |

The highlight in game also depends on `specular[]`, `specularPower` and the fresnel stage of the `.rvmat`; values per surface copied from vanilla materials are in `_shared/textures/surface-recipes.md`.

---

## 8. Ambient occlusion

If AO was baked in Blender, multiply it in to add depth at no cost in geometry:

```python
def integrate_ao(diffuse_path, ao_path):
    """Multiply AO into the diffuse to darken recessed areas."""
    diffuse = Image.open(diffuse_path).convert('RGB')
    ao = Image.open(ao_path).convert('L')

    # Make sure both are the same size
    ao = ao.resize(diffuse.size, Image.Resampling.LANCZOS)

    diffuse_array = np.array(diffuse, dtype=np.float32) / 255.0
    ao_array = np.array(ao, dtype=np.float32) / 255.0

    # AO as RGB for the multiplication
    ao_rgb = np.stack([ao_array, ao_array, ao_array], axis=2)

    # Blend: darken by AO
    result = diffuse_array * ao_rgb
    result = (result * 255).astype(np.uint8)

    return Image.fromarray(result, mode='RGB')
```

The Super shader also has its own stage for a baked ambient shadow, `Stage4` with an `_as` texture (`_shared/textures/rvmat-stages.md`); multiplying AO into the `_co` is the simple route for a small prop.

---

## 9. Complete example: an industrial electrical box

A full script that generates all three maps (512x512) for a typical electrical enclosure. It uses `fbm`, the blend functions, `generate_painted_metal`, `generate_rust_overlay`, `height_to_normal` and `generate_smdi_map` from the sections above.

```python
import os
import numpy as np
from PIL import Image
from opensimplex import OpenSimplex

def generate_electrical_box_textures(output_dir='textures', seed=42):
    """Generate the complete texture set for an electrical box."""

    width, height = 512, 512
    gen = OpenSimplex(seed=seed)
    os.makedirs(output_dir, exist_ok=True)

    # ===== COLOR MAP =====
    diffuse = generate_painted_metal(width, height, seed)

    # Rust overlay (small patches)
    rust, rust_mask = generate_rust_overlay(width, height, density=0.08, seed=seed+1)
    for c in range(3):
        diffuse[:, :, c] = blend_multiply(diffuse[:, :, c],
                                          rust[:, :, c] + (1 - rust_mask))

    # Small scuffed and worn areas
    scuffs = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 3, y / height * 3, octaves=4, gain=0.6)
            if (val + 1) / 2 > 0.85:  # Only the highest noise values
                scuffs[y, x] = 1.0

    scuff_color = 0.45  # Light gray
    for c in range(3):
        diffuse[:, :, c] = blend_lerp(diffuse[:, :, c], scuff_color, scuffs * 0.06)

    diffuse = np.clip(diffuse, 0, 1)
    diffuse_uint8 = (diffuse * 255).astype(np.uint8)
    Image.fromarray(diffuse_uint8, mode='RGB').save(f'{output_dir}/box_co.png')

    # ===== NORMAL MAP =====
    # Height map from the luminance of the diffuse
    height_map = (0.299 * diffuse[:, :, 0] +
                  0.587 * diffuse[:, :, 1] +
                  0.114 * diffuse[:, :, 2])

    normals = height_to_normal(height_map, strength=1.2)
    normals_uint8 = (normals * 255).astype(np.uint8)
    Image.fromarray(normals_uint8, mode='RGB').save(f'{output_dir}/box_nohq.png')

    # ===== SMDI MAP =====
    smdi = generate_smdi_map(width, height, material='painted_metal')
    smdi.save(f'{output_dir}/box_smdi.png')

    print("Generated textures:")
    print(f"  {output_dir}/box_co.png (color)")
    print(f"  {output_dir}/box_nohq.png (normal)")
    print(f"  {output_dir}/box_smdi.png (specular and gloss)")

# Run: generate_electrical_box_textures()
```

---

## 10. Common mistakes and solutions

### Mistake 1: using random() instead of coherent noise

```python
# WRONG: looks like TV static
for y in range(height):
    for x in range(width):
        canvas[y, x] = random.random()

# CORRECT: smooth, natural variation
for y in range(height):
    for x in range(width):
        val = gen.noise2(x * frequency, y * frequency)
        canvas[y, x] = (val + 1.0) / 2.0
```

### Mistake 2: forgetting to normalize the output

```python
# WRONG: the range [-1, 1] comes out black or barely visible
noise_val = gen.noise2(x, y)  # Range [-1, 1]
pixel = int(noise_val * 255)  # Mostly negative or below 128

# CORRECT: normalize to [0, 1]
noise_val = gen.noise2(x, y)
normalized = (noise_val + 1.0) / 2.0  # Range [0, 1]
pixel = int(normalized * 255)  # Full range [0, 255]
```

### Mistake 3: using a single layer of noise

```python
# WRONG: looks obviously procedural, too uniform
val = gen.noise2(x * 0.1, y * 0.1)

# CORRECT: several octaves add realism
val = fbm(gen, x, y, octaves=6, lacunarity=2.0, gain=0.5)
```

### Mistake 4: the same frequency for all details

```python
# WRONG: no variety of scale, boring
noise1 = fbm(gen, x * 0.1, y * 0.1, octaves=6)
noise2 = fbm(gen, x * 0.1, y * 0.1, octaves=6)

# CORRECT: different frequencies for different purposes
base = fbm(gen, x * 0.02, y * 0.02, octaves=3)  # Large features
grain = fbm(gen, x * 0.3, y * 0.3, octaves=5)   # Texture
micro = fbm(gen, x * 2.0, y * 2.0, octaves=3)   # Detail
```

### Mistake 5: an alpha channel on a `_co`

```python
# WRONG: a _co has no alpha, so an RGBA image carries a channel that is thrown away
img = Image.new('RGBA', (512, 512))

# CORRECT: RGB mode for _co, _nohq and _smdi
img = Image.new('RGB', (512, 512))
img.save('texture_co.png')  # No alpha channel
```

Only a surface that needs transparency keeps an alpha channel, and it is then saved as `_ca`.

### Mistake 6: blown out or invisible textures

```python
# WRONG: values outside [0, 1] get clipped
canvas[y, x] = 2.5  # Clipped to 1.0 (white)
canvas[y, x] = -0.5  # Clipped to 0.0 (black)

# CORRECT: clamp explicitly
canvas = np.clip(canvas, 0.0, 1.0)
```

### Mistake 7: a normal map with no strength

```python
# WRONG: the normal map is completely flat (strength 0)
normals = height_to_normal(height_map, strength=0)

# CORRECT: strength 0.5 to 2.0 for visible bumps
normals = height_to_normal(height_map, strength=1.2)
```

---

## 11. Tips for industrial quality

1. **Reference real objects.** Photograph actual electrical boxes, metal surfaces, worn paint. Study the patterns of variation.
2. **Layer on purpose.** Each layer should serve a purpose (base color, wear, grain, details). Random layering looks chaotic.
3. **Respect scale.** Frequency should reflect real world size. Paint streaks are larger than metal grain.
4. **Use edge masks.** Wear and weathering concentrate at edges and corners. Use masks based on position.
5. **Add imperfections.** Perfect surfaces look fake. Include dust, scratches, fingerprints, corrosion.
6. **Test in the engine.** Textures look different under DayZ lighting. Preview early and adjust the strength values (`_shared/textures/checking-the-look.md`).
7. **Keep it reproducible.** Use fixed seeds for consistent iteration. Write the seed values down.
8. **Mind the cost of frequency.** High frequency noise is expensive to compute. Compute once at the largest resolution and downscale if needed.
9. **Composite carefully.** Blend modes matter. Try multiply, screen and overlay to find the right look.
10. **Get the SMDI right.** Match the specular (G) and the gloss (B) to the material; keep R near white (about 255).

---

## Quick reference: standard texture settings

```python
# Small electrical object (512x512)
gen = OpenSimplex(seed=42)
width, height = 512, 512

# Painted metal box
diffuse = generate_painted_metal(512, 512, seed=42)
height_map = (0.299 * diffuse[:, :, 0] +
              0.587 * diffuse[:, :, 1] +
              0.114 * diffuse[:, :, 2])
normals = height_to_normal(height_map, strength=1.2)
smdi = generate_smdi_map(512, 512, material='painted_metal')

# Save
Image.fromarray((diffuse * 255).astype(np.uint8), 'RGB').save('box_co.png')
Image.fromarray((normals * 255).astype(np.uint8), 'RGB').save('box_nohq.png')
smdi.save('box_smdi.png')
```

Start with the basic recipes and add layers according to what the result looks like in the engine.
