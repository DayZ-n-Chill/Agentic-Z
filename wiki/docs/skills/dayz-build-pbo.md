---
name: dayz-build-pbo
---

## Overview

Pack a scaffolded mod from workspace/&lt;ModName&gt;/ into a .pbo at P:\Mods\@&lt;ModName&gt;\Addons\ via DayZ Tools AddonBuilder. Gates on /dayz-preflight, verifies the P:\&lt;ModName&gt;\ junction created by /dayz-new-mod, surfaces AddonBuilder output live. Default is binarized output; --clean wipes the target dir first.

# /dayz-build-pbo

Package a DayZ mod scaffold into a deployable `.pbo` and place it under `P:\Mods\@<ModName>\Addons\` so the engine can load it. Gates on `/dayz-preflight` and the `P:\<ModName>\` junction created by `/dayz-new-mod`. Reuses `find_dayz_tools()` from preflight per the L2 rule — no copy-paste path discovery.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-build-pbo\build.py <ModName> [--clean]
```

| Argument | Required? | Notes |
|---|---|---|
| `<ModName>` | yes | Must match an existing scaffold under `workspace/<ModName>/` with the `P:\<ModName>\` junction in place. |
| `--clean` | no | Passes `-clear` to AddonBuilder, wiping `P:\Mods\@<ModName>\Addons\` before building. Use after large refactors or when chasing a stale-asset bug. |

## What it does

1. **Preflight gate** — runs `/dayz-preflight`; halts on non-zero.
2. **Workspace check** — verifies `workspace/<ModName>/` exists and contains `config.cpp` + `$PBOPREFIX$`.
3. **Junction check** — verifies `P:\<ModName>\` is a link pointing at `workspace/<ModName>/` (created by `/dayz-new-mod`). If the link is missing or points elsewhere, halts with a clear message.
4. **Tools check** — resolves `AddonBuilder.exe` via `find_dayz_tools()` (env var → registry → Steam paths). Halts if not found.
5. **Prepare paths** — ensures `P:\Mods\@<ModName>\Addons\` and `P:\temp\<ModName>\` exist.
6. **Build** — invokes `AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> [-clear]`. AddonBuilder's stdout/stderr stream live so you see binarization progress and config errors as they happen.
7. **Verify output** — confirms `P:\Mods\@<ModName>\Addons\<ModName>.pbo` exists and is newer than the build start.
8. **Cleanup** — removes `P:\temp\<ModName>\` on success (kept on failure for debugging).

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `workspace/<ModName>/` is missing.
- `workspace/<ModName>/config.cpp` or `$PBOPREFIX$` is missing.
- `P:\<ModName>\` doesn't exist, isn't a link, or points somewhere other than `workspace/<ModName>/`. (Run `/dayz-new-mod <ModName>` to scaffold and create the junction.)
- `AddonBuilder.exe` isn't found (set `DAYZ_TOOLS_PATH` or install via Steam).
- AddonBuilder exits non-zero — exit code propagates and the temp dir is preserved for inspection.

## Output

Success:

```
DayZ preflight
[OK]    P:\ is mounted
[OK]    DayZ Tools found: C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools
[OK]    Vanilla data found: P:\dz
[OK]    Workshop deploy folder exists: P:\Mods

Preflight complete.
[OK]    workspace\MyMod\ found
[OK]    P:\MyMod junction valid
[OK]    AddonBuilder: C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe

[AddonBuilder] ... live output ...

[OK]    Built: P:\Mods\@MyMod\Addons\MyMod.pbo (12,345 bytes)
[OK]    Cleaned temp dir
```

Failure (any step):

```
[FAIL] <reason>
       <hint or next step>
```

## Do not

- Don't try to write the PBO outside `P:\Mods\@<ModName>\Addons\`. The engine only loads from `P:\Mods\` for in-development mods.
- Don't manage the `P:\<ModName>\` junction here — that's `/dayz-new-mod`'s job. If the junction is missing or wrong, fail and direct the user to scaffold first.
- Don't re-implement Tools path discovery — import `find_dayz_tools` from `dayz-preflight/preflight.py`.
- Don't auto-binarize off — keep binarization on by default. (A `--no-binarize` flag can be added later if iteration speed becomes a problem.)
