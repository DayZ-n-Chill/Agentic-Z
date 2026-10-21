---
name: dayz-pack-texture
---

## Overview

Converts PNG or TGA images to DayZ .paa textures with ImageToPAA, after checking each filename has a texture-role suffix such as _co, _ca, _nohq or _smdi. Use when a mod's textures need packing for config.cpp, .rvmat or hiddenSelectionsTextures references.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-pack-texture

Convert one or more PNG/TGA images to `.paa` (DayZ's texture format) using DayZ Tools' `ImageToPAA.exe`. Each input file must end in a texture-role suffix. ImageToPAA reads the suffix to pick the compression and color space (its rules are in `<DayZ Tools>\Bin\ImageToPAA\TexConvert.cfg`). The skill accepts every suffix that has a rule there and is used by vanilla textures under `P:\DZ`:

| Suffixes | Role |
|---|---|
| `_co`, `_ca` | Color / diffuse, without and with alpha |
| `_lco`, `_lca` | Terrain layer color (satellite and mask textures), without and with alpha |
| `_nohq`, `_no`, `_non`, `_nopx` | Normal map: high quality, plain, with noise in alpha (vegetation), parallax |
| `_smdi`, `_sm` | Specular (`_smdi` is the higher-bit-depth form vanilla gear uses) |
| `_as`, `_ads`, `_adshq` | Ambient shadow (`_ads`, `_adshq`: ambient, diffuse and shadow) |
| `_mc`, `_mco` | Macro texture, multiply color |
| `_dt`, `_detail`, `_cdt`, `_dtsmdi` | Detail textures |
| `_mask`, `_sky` | Masks, sky |

Most mod gear needs only `_co` (or `_ca`), `_nohq` and `_smdi`.

A file like `vest_camo_co.png` becomes `vest_camo_co.paa` next to it. An existing `.paa` of that name is overwritten without asking.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\pack_texture.py" <input1> [<input2> ...]
```

| Argument | Required? | Notes |
|---|---|---|
| `<input>` | yes (one or more) | Path to a `.png` or `.tga` file with a valid suffix in the basename. Pass each file explicitly; cmd.exe does not expand globs. |

## What it does

1. Preflight gate.
2. Validate every input before converting any: the file exists, the extension is `.png` or `.tga` (any case), and the basename ends with one of the suffixes above (any case) before the extension.
3. Resolve `ImageToPAA.exe` from DayZ Tools (env / registry / Steam paths) via `find_dayz_tools()`.
4. For each input, invoke `ImageToPAA.exe <input> <output.paa>`, overwriting any existing `.paa`. Streams the tool's output live. A conversion counts as failed if the tool exits non-zero, if no `.paa` appears, or if an existing `.paa` was left unchanged (its modification time did not move), so a stale file from an earlier run is never reported as packed.
5. Report a summary of successes and failures. Exit non-zero if any failed.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `ImageToPAA.exe` is not found under DayZ Tools.
- An input file doesn't exist.
- An input doesn't end in `.png` or `.tga`.
- An input's basename doesn't end with one of the suffixes above. ImageToPAA picks the compression from the suffix, and the rest of the pipeline (rvmat stages, reviewers) relies on it to tell what the texture is for.

## Output

```
DayZ preflight
... (preflight output)
Preflight complete.

[OK]   ImageToPAA: C:\...\DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe

[Pack] vest_camo_co.png  ->  vest_camo_co.paa
... (ImageToPAA output) ...
[OK]   Wrote vest_camo_co.paa (123,456 bytes)

[Pack] vest_camo_nohq.png  ->  vest_camo_nohq.paa
... (ImageToPAA output) ...
[OK]   Wrote vest_camo_nohq.paa (98,765 bytes)

[OK]   2 of 2 textures packed.
```

## Do not

- Don't auto-rename inputs. If the user has `vest_camo.png` (no suffix), they rename it themselves so they're explicit about what role it plays.
