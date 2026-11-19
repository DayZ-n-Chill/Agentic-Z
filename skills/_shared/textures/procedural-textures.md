# Procedural textures

How to generate the `_co`, `_nohq` and `_smdi` maps of a generated model in Python with coherent noise: the maps to target, OpenSimplex noise and FBM, building a surface in layers with blend modes, and the mistakes that make a texture look procedural.

This is **tool knowledge** (Pillow, numpy, OpenSimplex); a pixel recipe has no vanilla file behind it. Where it touches the game it follows this pack, and where the two differ the pack wins. Material recipes and a full script are in `procedural-recipes.md`; the normal map from a height map and the `_smdi` generator are in `procedural-normal-and-smdi.md`.

Generate each map as `.png` and convert it with `/dayz-pack-texture`. Faces in the `.p3d` name the `.paa`, never the `.png` (`_shared/models/generated-model-rules.md`, "Visual LODs, memory and selections").

## The maps to generate

| Map | Mode | What it holds |
|---|---|---|
| `_co.png` | RGB | The base color, what you see before lighting. No alpha; a surface that needs transparency is a `_ca`, which keeps its alpha (`suffixes-and-sizes.md`). |
| `_nohq.png` | RGB | The normal: red X, green Y, blue Z, DirectX convention with green pointing down (`normal-maps.md`). Built from a height map (`procedural-normal-and-smdi.md`). |
| `_smdi.png` | RGB | Red kept at 255, green the specular strength, blue the gloss (`smdi-and-levels.md`). |

The vanilla battery charger shows the `_smdi` layout: `P:\DZ\gear\camping\data\battery_charger_smdi.paa` decodes with red at 255 on every pixel and its data in green and blue. Never treat blue as a "detail index"; that packing is wrong for a DayZ `_smdi`.

Sizes: 512 x 512 for small objects (switches, adapters, knobs, small boxes) and 1024 x 1024 for medium and large ones (electrical boxes, panels, barrels, machinery). Every side is a power of two, and the `_nohq` and `_smdi` match their `_co`; what vanilla picks per folder is in `suffixes-and-sizes.md`.

## OpenSimplex noise

OpenSimplex is a gradient noise that suits textures better than Perlin noise: smooth, natural variation with no visible tiling.

```cmd
python -m pip install opensimplex pillow numpy
```

```python
from opensimplex import OpenSimplex

gen = OpenSimplex(seed=42)                        # a fixed seed reproduces the pattern
value = gen.noise2(x * frequency, y * frequency)  # in [-1, 1]
normalized = (value + 1.0) / 2.0                  # in [0, 1]
```

- The same input always gives the same output, and nearby inputs give nearby values.
- The output is always in [-1, 1]; normalize it yourself.
- A different seed gives an entirely different pattern. Use `seed=np.random.randint(0, 1000000)` for variety, and write down the seeds you keep.

Frequency sets the size of the features:

| Frequency | Gives |
|---|---|
| 0.01 to 0.05 | Large, slow variation: the overall color |
| 0.05 to 0.2 | Mid scale detail: paint streaks, patches |
| 0.2 to 1.0 | Fine texture: grain, micro roughness |
| 1.0 and up | Detail below a pixel |

## Fractional Brownian motion

FBM sums several octaves of noise at rising frequency and falling amplitude, which gives natural looking complexity. The recipes in the other two files call this function:

```python
def fbm(gen, x, y, octaves=6, lacunarity=2.0, gain=0.5):
    """Sums octaves of OpenSimplex noise. Returns a value in about [-1, 1]."""
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_amplitude = 0.0
    for _ in range(octaves):
        value += amplitude * gen.noise2(x * frequency, y * frequency)
        max_amplitude += amplitude
        frequency *= lacunarity
        amplitude *= gain
    return value / max_amplitude if max_amplitude > 0 else 0.0
```

| Parameter | Typical | Effect |
|---|---|---|
| `octaves` | 4 to 8 | 4 is smooth and large scale, 6 a good balance, 8 or more intricate and slow |
| `lacunarity` | 2.0 to 2.5 | How fast frequency rises per octave: 2.0 standard, 1.5 smoother, 2.5 more varied detail |
| `gain` | 0.4 to 0.6 | How fast amplitude falls per octave: 0.5 standard, 0.6 more visible fine detail, 0.4 smoother |

Typical settings: `octaves=4, gain=0.5` for flowing paint variation, `octaves=7, lacunarity=2.2, gain=0.6` for grainy rust and corrosion, `octaves=5, gain=0.4` for subtle worn metal.

## Building a surface in layers

What separates a generic texture from a convincing one is layering, each layer with one job and its own blend mode:

| Layer | Job | Frequency and octaves | Blend |
|---|---|---|---|
| Base color | Overall color and large variation, such as dark grey (60, 60, 70) within 10 % | 0.02 to 0.05, 3 to 4 octaves | sets the canvas |
| Flow or streaks | Directional wear from paint application | Y squeezed to 0.1, X stretched to 0.02, 4 octaves | overlay or multiply |
| Grain | Micro texture of the material, brushed metal or molded plastic | 0.3 to 0.5, 5 octaves | overlay at 0.2 to 0.4 |
| Micro variation | Dust and fingerprints, almost invisible | 1.0 to 2.0, 3 octaves, amplitude 0.02 to 0.05 | soft light or overlay, very low |
| Edge wear | Lighter edges where the coating wore away | a position mask times noise | additive or overlay |
| Sparse details | Rust spots, dirt, scratches | 0.1 to 0.2 with a threshold | multiply for dark, screen for light |

The blend functions take `base` and `layer` as numpy arrays of one shape in [0, 1], and an `opacity` where 1.0 applies the blend fully and 0.0 leaves `base` unchanged:

```python
import numpy as np

def blend_lerp(base, layer, alpha):
    return base * (1.0 - alpha) + layer * alpha

def blend_multiply(base, layer, opacity=1.0):
    return blend_lerp(base, base * layer, opacity)

def blend_screen(base, layer, opacity=1.0):
    return blend_lerp(base, 1.0 - (1.0 - base) * (1.0 - layer), opacity)

def blend_overlay(base, layer, opacity=1.0):
    result = np.where(base < 0.5, 2.0 * base * layer, 1.0 - 2.0 * (1.0 - base) * (1.0 - layer))
    return blend_lerp(base, result, opacity)

def blend_soft_light(base, layer, opacity=1.0):
    lifted = np.where(base <= 0.25, ((16.0 * base - 12.0) * base + 4.0) * base, np.sqrt(base))
    result = np.where(layer <= 0.5,
                      base - (1.0 - 2.0 * layer) * base * (1.0 - base),
                      base + (2.0 * layer - 1.0) * (lifted - base))
    return blend_lerp(base, result, opacity)
```

Multiply darkens, screen lightens, overlay multiplies below 0.5 and screens above, and soft light is a gentler overlay that suits grain.

## Mistakes that look procedural

| Mistake | What it looks like | Fix |
|---|---|---|
| `random.random()` per pixel | TV static | Coherent noise, `(gen.noise2(x * f, y * f) + 1.0) / 2.0` |
| Noise used without normalizing | Mostly black or barely visible, since half the values are negative | Map [-1, 1] to [0, 1] before scaling to 255 |
| One layer of noise | Obviously generated, too uniform | FBM with several octaves, `fbm(gen, x, y, octaves=6)` |
| One frequency for every layer | No range of scale | Different frequencies per job: about 0.02 for large features, 0.3 for texture, 2.0 for detail |
| An RGBA image saved as `_co` | An alpha channel that is thrown away | `Image.new('RGB', ...)` for `_co`, `_nohq` and `_smdi`; only a `_ca` keeps alpha |
| Values outside [0, 1] | Blown out white or crushed black patches | `np.clip(canvas, 0.0, 1.0)` before saving |
| `height_to_normal(..., strength=0)` | A completely flat normal map | Strength 0.5 to 2.0 |

## Habits that pay off

- Study real objects: photograph electrical boxes, metal surfaces and worn paint, and copy how they vary.
- Give every layer a purpose; random stacking looks chaotic.
- Match frequency to real size: paint streaks are larger than metal grain.
- Put wear and weathering at edges and corners with position masks.
- Add imperfections; perfect surfaces look fake.
- Keep it reproducible with fixed seeds.
- High frequency noise is slow to compute. Work at a small size while iterating, then generate once at full size and scale down if needed.
- Try multiply, screen and overlay before settling on a blend.
- Keep `_smdi` red near 255 and match green and blue to the material.
- Look at it in the engine early; DayZ lighting changes how a texture reads (`checking-the-look.md`).
