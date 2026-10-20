---
name: dayz-build-pbo
description: Packs a scaffolded mod from workspace/<ModName>/ into a binarized .pbo at P:\Mods\@<ModName>\Addons\ with DayZ Tools AddonBuilder, streaming its output live. Gates on /dayz-preflight, the P:\<ModName>\ junction and the deploy-dir ownership marker. Use when a mod's source changed and you need a fresh PBO before /dayz-launch-test, or with --clean to chase a stale-asset bug.
argument-hint: "<ModName> [--clean]"
---

<!-- skill-dir-note -->
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
| `--clean` | no | Passes `-clear` to AddonBuilder, wiping `P:\Mods\@<ModName>\Addons\` before building. Use after large refactors or when chasing a stale-asset bug. |

## What it does

1. **Project** - reads the project root cached by `/dayz-init`.
2. **Preflight gate** - runs `/dayz-preflight`; halts on non-zero. Then confirms `P:\Mods\` is a junction to the DayZ `!Workshop` folder.
3. **Workspace check** - `workspace/<ModName>/` exists and contains `config.cpp` and `$PBOPREFIX$`.
4. **Junction check** - `P:\<ModName>\` is a link pointing at `workspace/<ModName>/` (created by `/dayz-new-mod` or `/dayz-import-mod`).
5. **Tools check** - resolves `AddonBuilder.exe` through `find_dayz_tools()` (env var, registry, Steam libraries).
6. **Ownership gate** - if `P:\Mods\@<ModName>\` already exists, it must contain `.agentic-z-scaffold` with content `<ModName>`. An unmarked folder could be a subscribed or hand-placed mod, so the build refuses to write into it or `-clear` it. This is the same rule `/dayz-deploy-pbo` uses.
7. **Build** - runs `AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -include=<skill-dir>\include.lst [-clear]`. Binarization is on.
8. **Verify output** - `P:\Mods\@<ModName>\Addons\<ModName>.pbo` exists and is newer than the build start. AddonBuilder can exit 0 while leaving an old PBO in place; that case fails as a stale PBO.
9. **Ownership marker** - writes `P:\Mods\@<ModName>\.agentic-z-scaffold`. It sits above `Addons\`, so `-clear` keeps it. `/dayz-clean-workspace` only removes deployed folders that carry it.
10. **Cleanup** - removes `P:\temp\<ModName>\` on success; keeps it on failure for debugging.

## include.lst

`include.lst` (next to `build.py`) is passed to AddonBuilder as `-include=`. It is one line of `;`-separated wildcard patterns naming the file types AddonBuilder copies into the PBO: scripts, configs, layouts, models, textures, materials, sounds, and data files such as `.json`, `.xml`, `.csv` and `.txt`. A file whose extension is not listed is silently left out of the PBO. If your mod ships another file type, add its pattern to that line.

## Refuses to run if

- No project is cached (run `/dayz-init`).
- `/dayz-preflight` fails, or `P:\Mods\` is not a valid junction to `!Workshop`.
- `workspace/<ModName>/`, its `config.cpp`, or its `$PBOPREFIX$` is missing (`/dayz-add-scaffold` adds the files).
- `P:\<ModName>\` is missing, is a real folder, or points somewhere other than `workspace/<ModName>/`.
- `AddonBuilder.exe` is not found (set `DAYZ_TOOLS_PATH` or install DayZ Tools).
- `P:\Mods\@<ModName>\` exists without a matching ownership marker. If it is yours, remove it: `cmd /c rmdir /s /q P:\Mods\@<ModName>`.
- AddonBuilder exits non-zero (its exit code propagates), or produces no fresh PBO. The temp dir is kept for inspection.

## Output

```
DayZ preflight
[OK]    P:\ is mounted
...
Preflight complete.
[OK]    P:\Mods junction valid
[OK]    workspace\MyMod\ found
[OK]    P:\MyMod junction valid
[OK]    AddonBuilder: C:\...\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe
[OK]    P:\Mods\@MyMod\ ownership marker valid

[AddonBuilder] ... live output ...

[OK]    Built: P:\Mods\@MyMod\Addons\MyMod.pbo (12,345 bytes)
[OK]    Cleaned temp dir
```

The ownership line appears only when `@MyMod` already exists. Failures print `[FAIL] <reason>` followed by an indented hint.

## Do not

- Don't write the PBO anywhere except `P:\Mods\@<ModName>\Addons\`; that is where the engine loads in-development mods.
- Don't create or repair the `P:\<ModName>\` junction here; that is `/dayz-new-mod` and `/dayz-import-mod`'s job.
- Don't pass `--clean` to a build that runs after `/dayz-deploy-pbo` into the same `@<ModName>`; `-clear` wipes the deployed payload PBOs too.
