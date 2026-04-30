---
name: dayz-pack-texture
description: >-
  Convert PNG/TGA images to DayZ-format `.paa` textures via DayZ Tools' ImageToPAA.exe.
  Validates the required suffix (`_co`, `_nohq`, `_smdi`) on each input filename so
  the engine assigns the correct texture role. One-to-one: every input produces a `.paa`
  next to itself.
---

# /dayz-pack-texture

Convert one or more PNG/TGA images to `.paa` (DayZ's texture format) using DayZ Tools' `ImageToPAA.exe`. Each input file is required to follow the DayZ suffix convention so the engine knows what kind of texture it is:

| Suffix | Meaning |
|---|---|
| `_co` | Color / diffuse |
| `_nohq` | Normal map |
| `_smdi` | Specular / mask |

A file like `vest_camo_co.png` becomes `vest_camo_co.paa` next to it.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-pack-texture\pack_texture.py &lt;input1&gt; [&lt;input2&gt; ...]
```

| Argument | Required? | Notes |
|---|---|---|
| `&lt;input&gt;` | yes (one or more) | Path to a `.png` or `.tga` file with a valid suffix in the basename. Globs work via your shell. |

## What it does

1. Preflight gate.
2. Resolve `ImageToPAA.exe` from DayZ Tools (env / registry / Steam paths) via `find_dayz_tools()`.
3. For each input:
   - Validate extension is `.png` or `.tga`.
   - Validate basename ends with one of `_co`, `_nohq`, `_smdi` (before the extension).
   - Invoke `ImageToPAA.exe &lt;input&gt; &lt;output.paa&gt;`. Streams the tool's output live.
4. Report a summary of successes and failures. Exit non-zero if any failed.

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `ImageToPAA.exe` is not found under DayZ Tools.
- An input file doesn't exist.
- An input doesn't end in `.png` or `.tga`.
- An input's basename doesn't end with a recognized DayZ suffix (`_co` / `_nohq` / `_smdi`). The engine relies on the suffix to assign the texture role; without it the texture won't apply correctly.

## Output

```
DayZ preflight
... (preflight output)
Preflight complete.

[OK]    ImageToPAA: C:\...\DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe

[Pack] vest_camo_co.png  ->  vest_camo_co.paa
... (ImageToPAA output) ...
[OK]    Wrote vest_camo_co.paa (123,456 bytes)

[Pack] vest_camo_nohq.png  ->  vest_camo_nohq.paa
... (ImageToPAA output) ...
[OK]    Wrote vest_camo_nohq.paa (98,765 bytes)

[OK]    2 of 2 textures packed.
```

## Do not

- Don't accept inputs without a recognized suffix. Silently producing a wrongly-named `.paa` masks an engine-side bug that's painful to diagnose later.
- Don't auto-rename inputs. If the user has `vest_camo.png` (no suffix), they need to rename it themselves so they're explicit about what role it plays.
- Don't re-implement DayZ Tools path discovery — import `find_dayz_tools` from `dayz-preflight/preflight.py`.
