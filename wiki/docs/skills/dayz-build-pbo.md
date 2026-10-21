---
name: dayz-build-pbo
---

## Overview

Packs a mod from workspace/&lt;ModName&gt;/ into a binarized .pbo at P:\Mods\@&lt;ModName&gt;\Addons\ with DayZ Tools AddonBuilder. Use when a mod's source changed and you need a fresh PBO before /dayz-launch-test, or a clean rebuild to chase a stale-asset bug.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-build-pbo

Package a mod scaffold into a deployable `.pbo` under `P:\Mods\@<ModName>\Addons\`, where the engine loads it. Path discovery comes from `dayz-preflight/preflight.py`; the preflight gate, project cache and ownership-marker rules come from `.claude/skills/_shared/skill_helpers.py`.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\build.py" <ModName> [--clean]
```

| Argument | Required? | Notes |
|---|---|---|
| `<ModName>` | yes | Must match a scaffold under `workspace/<ModName>/` in the project cached by `/dayz-init`, with the `P:\<ModName>\` junction in place. |
| `--clean` | no | Passes `-clear` to AddonBuilder, wiping `P:\Mods\@<ModName>\Addons\` before building. Use after large refactors or when chasing a stale-asset bug. Refused while `Addons\` holds any PBO other than `<ModName>.pbo` (payload copied in by `/dayz-deploy-pbo`). |

## What it does

1. **Project** - reads the project root cached by `/dayz-init`.
2. **Lint gate**: runs `/dayz-lint <ModName>` and stops with `[FAIL]` and each `file:line` if it finds an error, since the mod would not load. Lint warnings print as `[WARN]` and the build goes on. The `P:\<ModName>\` link is left to step 5, the junction check.
3. **Preflight gate** - runs `/dayz-preflight`; halts on non-zero. Then confirms `P:\Mods\` is a junction to the DayZ `!Workshop` folder.
4. **Workspace check** - `workspace/<ModName>/` exists and contains `config.cpp` and `$PBOPREFIX$`, and `$PBOPREFIX$` holds exactly `<ModName>` (surrounding whitespace and a BOM are ignored; case must match). The build always packs with `-prefix=<ModName>` through the `P:\<ModName>\` junction, so a different prefix means the mod's config paths expect another root; it refuses rather than build a PBO whose paths do not resolve.
5. **Junction check** - `P:\<ModName>\` is a link pointing at `workspace/<ModName>/` (created by `/dayz-new-mod` or `/dayz-import-mod`).
6. **Tools check** - resolves `AddonBuilder.exe` through `find_dayz_tools()` (env var, registry, Steam libraries).
7. **Ownership gate** - if `P:\Mods\@<ModName>\` already exists, it must contain `.agentic-z-scaffold` with content `<ModName>`. An unmarked folder could be a subscribed or hand-placed mod, so the build refuses to write into it or `-clear` it. This is the same rule `/dayz-deploy-pbo` uses.
8. **Clean gate** (`--clean` only) - refuses if `P:\Mods\@<ModName>\Addons\` holds any `.pbo` other than `<ModName>.pbo`, since `-clear` would wipe that deployed payload.
9. **Ownership marker** - when this run creates `P:\Mods\@<ModName>\`, it writes `.agentic-z-scaffold` there before AddonBuilder starts, so a failed first build leaves a marked folder that the next build accepts. The marker sits above `Addons\`, so `-clear` keeps it. `/dayz-clean-workspace` only removes deployed folders that carry it. If the marker cannot be written, the build prints `[FAIL]` and exits 1 without running AddonBuilder.
10. **Build** - runs `AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -include=<skill-dir>\include.lst -exclude=<skill-dir>\exclude.lst [-clear]`. Binarization is on.
11. **Verify output** - `P:\Mods\@<ModName>\Addons\<ModName>.pbo` exists and is newer than the build start. AddonBuilder can exit 0 while leaving an old PBO in place; that case fails as a stale PBO.
12. **Cleanup** - removes `P:\temp\<ModName>\` on success; keeps it on failure for debugging.

## include.lst

`include.lst` (next to `build.py`) is passed to AddonBuilder as `-include=`. It is one line of `;`-separated wildcard patterns naming the file types AddonBuilder copies into the PBO: scripts, configs, layouts, models, textures, materials, sounds, and data files such as `.json`, `.xml`, `.csv` and `.txt`. A file whose extension is not listed is silently left out of the PBO. If your mod ships another file type, add its pattern to that line.

## exclude.lst

`exclude.lst` (next to `build.py`) is passed as `-exclude=`. AddonBuilder leaves files matching its patterns (one per line, `;` starts a comment) out of the final PBO. It drops `.gui-sources\` (the sprite source PNGs for `/dayz-build-imageset`; only the packed atlas and `.imageset` under `gui/imagesets/` ship), version-control folders, binarization logs, archives, signatures and keys, and source, doc and temp folders.

## Refuses to run if

- No project is cached (run `/dayz-init`).
- `/dayz-preflight` fails, or `P:\Mods\` is not a valid junction to `!Workshop`.
- `workspace/<ModName>/`, its `config.cpp`, or its `$PBOPREFIX$` is missing (`/dayz-add-scaffold` adds the files).
- `$PBOPREFIX$` holds anything other than `<ModName>`. Set it to that single line, and make sure `config.cpp` paths use `<ModName>\` as their root.
- `P:\<ModName>\` is missing, is a real folder, or points somewhere other than `workspace/<ModName>/`. The hint points at `/dayz-add-scaffold <ModName> --piece junction`, which creates the link.
- `AddonBuilder.exe` is not found (set `DAYZ_TOOLS_PATH` or install DayZ Tools).
- `P:\Mods\@<ModName>\` exists without a matching ownership marker. If it is yours, remove it: `cmd /c rmdir /s /q P:\Mods\@<ModName>`.
- `--clean` is passed while `Addons\` holds PBOs other than `<ModName>.pbo`.
- AddonBuilder exits non-zero (its exit code propagates), or produces no fresh PBO. The temp dir is kept for inspection.

## Output

```
DayZ preflight

[OK]    P:\ is mounted
...     (rest of the /dayz-preflight report)

Preflight complete.
[OK]    P:\Mods junction valid
[OK]    workspace\MyMod\ found
[OK]    $PBOPREFIX$ matches MyMod
[OK]    P:\MyMod junction valid
[OK]    AddonBuilder: C:\...\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe
[OK]    P:\Mods\@MyMod\ ownership marker valid

[AddonBuilder] C:\...\AddonBuilder.exe P:\MyMod P:\Mods\@MyMod\Addons -prefix=MyMod -temp=P:\temp\MyMod -include=...\include.lst -exclude=...\exclude.lst

... AddonBuilder's own output, streamed live ...

[OK]    Built: P:\Mods\@MyMod\Addons\MyMod.pbo (12,345 bytes)
[OK]    Cleaned temp dir
```

The ownership line appears only when `@MyMod` already exists. Failures print `[FAIL]  <reason>` followed by an indented hint.

## Do not

- Don't write the PBO anywhere except `P:\Mods\@<ModName>\Addons\`; that is where the engine loads in-development mods.
- Don't create or repair the `P:\<ModName>\` junction here; `/dayz-new-mod` and `/dayz-import-mod` create it, and `/dayz-add-scaffold <ModName> --piece junction` repairs it.
