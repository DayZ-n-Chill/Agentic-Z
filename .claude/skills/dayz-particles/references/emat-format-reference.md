# .emat Material Format Reference

Verified from 8 vanilla particle material files. Plain text format.

---

## TWO SHADER TYPES

### `Particle` — Most common (fire, sparks, water, smoke with blending)

Used when particles need additive blending, transparency sorting, or emissive glow.
Supports sprite sheet animation (TileU/TileV).

### `ParticleSprite` — Simpler (steam, flares, opaque billboards)

Used for simpler particles that just need diffuse+ambient lighting.
No BlendMode property available.

---

## COMPLETE PROPERTY TABLE

| Property | Available in | Type | Description |
|---|---|---|---|
| `AlbedoMap` | Both | string | Texture: `"{GUID}path.edds"` optionally with `alpha` channel ref |
| `Color` | Both | RGBA float | Base tint color (0-1 per channel) |
| `Diffuse` | Both | RGBA float | Diffuse lighting response |
| `Ambient` | Both | RGBA float | Ambient lighting response |
| `Emissive` | Both | RGBA float | Self-illumination / glow intensity |
| `BlendMode` | Particle only | string/int | Blending: `Additive_AlphaModulate`, `2`, or omit |
| `Sort` | Both | string/int | Render sorting: `translucent`, `overlay`, `0` |
| `Softness` | Both | float | Soft-particle edge blending (0=hard, 2=very soft) |
| `TileU` | Particle only | int | Sprite sheet columns (for animated textures) |
| `TileV` | Particle only | int | Sprite sheet rows |
| `CameraBlendFar` | Particle only | float | Distance fade threshold |
| `BidirLightScale` | Particle only | float | Bidirectional light scaling (0=disable) |

---

## BlendMode VALUES

| Value | Visual effect | Use case |
|---|---|---|
| `Additive_AlphaModulate` | Adds light, modulated by alpha | Sparks, fire, water splash |
| `2` | Numeric equivalent (legacy) | Same as additive |
| (omitted) | Standard alpha blending | Steam, soft smoke |

---

## Sort VALUES

| Value | Render order | Use case |
|---|---|---|
| `translucent` | Sorted back-to-front with scene | Water, smoke near objects |
| `overlay` | Always on top of geometry | Flares, HUD-like effects |
| `0` | Default engine sorting | Most particles |

---

## VANILLA EXAMPLES (annotated)

### Glow dot (simplest material — ParticleSprite-like but Particle shader)

```
material "Graphics/Particles/materials/glow/glow1.emat": Particle
{
	AlbedoMap "{B6C9A3D2263E9667}Graphics/Particles/sprites/glow.edds","{69E030A5603F544C}alpha"
	Color "0 0 0 1"           ← black base (emissive does the visual)
	Ambient "0 0 0 1"
	Emissive "1 1 1 0"        ← full white glow
	Sort 0
	BlendMode 2               ← additive
	Softness 2                ← very soft edges
}
```
Note: legacy format with `material "path": Shader { ... }` and quoted values.
Both legacy and modern formats work.

### Spark point (Particle shader, additive)

```
Particle {
 AlbedoMap "{016B7879D4775122}Graphics/Particles/sprites/spark.edds" alpha
 Color 0 0 0 1
 Ambient 0 0 0 1
 Emissive 1 1 1 0             ← full emissive glow
 Sort translucent
 BlendMode Additive_AlphaModulate
 Softness 1
 CameraBlendFar 0.001         ← fade very close to camera
}
```

### Animated spark strip (8-tile sprite sheet)

```
Particle {
 AlbedoMap "{0B829A150C6A13E5}Graphics/Particles/sprites/sparks_06.edds"
 Emissive 1 1 1 0
 BlendMode Additive_AlphaModulate
 TileU 8                       ← 8 frames horizontal
 CameraBlendFar 0.001
 BidirLightScale 0
}
```

### Steam/vapor (ParticleSprite shader)

```
ParticleSprite {
 AlbedoMap "{00DB5AFE43BFC32C}Graphics/Particles/sprites/steam_cloud.edds"
 Color 0.9451 0.9451 0.9451 1  ← slightly gray
 Diffuse 0.949 0.949 0.949 1   ← high diffuse (lit by scene)
 Ambient 0.5882 0.5882 0.5882 1
 Softness 2                     ← very soft edges
}
```

### Water splash (Particle shader, translucent)

```
Particle {
 AlbedoMap "{612031817F136DE0}Graphics/Particles/sprites/water_splash_01.edds"
 Color 0.5098 0.5098 0.5098 0   ← gray tint, transparent base
 Diffuse 0.4745 0.4745 0.4745 1
 Emissive 0.0392 0.0392 0.0392 0.0392  ← very slight glow
 Sort translucent
 BlendMode Additive_AlphaModulate
 TileU 4                        ← 4x2 sprite sheet
 TileV 2
 Softness 2
}
```

### Flare (ParticleSprite shader, overlay sorting)

```
ParticleSprite {
 AlbedoMap "{856E111BF3EA99A3}Graphics/Particles/sprites/flare_light_ca.edds"
 Color 1 1 1 0
 Diffuse 1 1 1 0
 Ambient 1 1 1 0
 Emissive 1 1 1 1              ← full emissive in all channels
 Sort overlay                   ← renders on top of everything
}
```

---

## CREATING CUSTOM MATERIALS

### Approach 1: Reference vanilla .edds textures (safest)

Create a new .emat that points to an existing vanilla sprite texture by GUID:

```
Particle {
 AlbedoMap "{016B7879D4775122}Graphics/Particles/sprites/spark.edds"
 Emissive 0.2 0.5 1.0 0       ← blue-tinted sparks!
 BlendMode Additive_AlphaModulate
 Softness 1
}
```

This creates blue electric sparks using vanilla spark texture.

### Approach 2: Custom .edds texture (full custom)

1. Create a DDS texture (DXT5 for alpha, DXT1 for opaque)
2. Rename `.dds` → `.edds`
3. Place in mod: `MyMod/data/particles/sprites/my_texture.edds`
4. Reference in .emat by path only (no GUID for mod files — needs testing):
   `AlbedoMap "MyMod/data/particles/sprites/my_texture.edds"`

### Vanilla sprite texture GUIDs (extracted from .emat files)

| GUID | Path | Description |
|---|---|---|
| `{B6C9A3D2263E9667}` | Graphics/Particles/sprites/glow.edds | Soft circular glow |
| `{016B7879D4775122}` | Graphics/Particles/sprites/spark.edds | Single spark point |
| `{0B829A150C6A13E5}` | Graphics/Particles/sprites/sparks_06.edds | Spark strip (8 frames) |
| `{00DB5AFE43BFC32C}` | Graphics/Particles/sprites/steam_cloud.edds | Steam/cloud puff |
| `{612031817F136DE0}` | Graphics/Particles/sprites/water_splash_01.edds | Water splash (4x2 sheet) |
| `{856E111BF3EA99A3}` | Graphics/Particles/sprites/flare_light_ca.edds | Light flare |

---

## .meta FILES (for reference only — not needed for mods)

```
MetaFileClass {
 Name "{GUID}relative/path.emat"
 Author "username"
 ChangeDate 1234567890
 Configurations {
  EMATResourceClass PC { }
  EMATResourceClass XBOX_ONE : PC { }
  EMATResourceClass PS4 : PC { }
  EMATResourceClass LINUX : PC { }
 }
}
```

GUIDs are assigned by Workbench. Mod runtime loading uses PBO paths,
not GUIDs, for mod-owned resources.
