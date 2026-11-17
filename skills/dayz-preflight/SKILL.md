---
name: dayz-preflight
description: "Checks the DayZ modding environment (P:\\ mounted, DayZ Tools, DayZ Diag and DayZ Server installed, vanilla data unpacked, P:\\Mods junction) and creates the junction if it is missing. Use when starting DayZ work, after a reboot or fresh clone, before a debug session, or when another DayZ skill reports an environment problem. Its references cover the Object Builder (Buldozer) viewer path, the DayZ 1.30 launch options (-cacheP3D, unpacked -mod folder) and the Linux equivalents."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-preflight

Verify the DayZ modding environment before doing any DayZ work. Halts with a clear error if `P:\` is not mounted; warns on the other checks so the user can decide whether to proceed. Follow `skills/_shared/dayz-conventions.md`.

Preflight reports and does not repair, with one exception: when `P:\Mods\` is absent and the game's `!Workshop\` folder is found, it creates the `P:\Mods\` junction. `mklink /J` needs no admin rights, overwrites nothing and has a fixed target. It never mounts `P:\` (use `/dayz-workdrive`) and never changes an existing `P:\Mods\`.

## How to run

```cmd
python "<skill-dir>\preflight.py"
```

Run it before other DayZ skills, after a fresh clone, and after each reboot (`P:\` does not auto-mount). Build and deploy skills run it for you as a gate.

One flow does not need a separate preflight run: the in-game test script `dayz-test.ps1` of the dayz-test-ingame skill starts with its own checks (game exe, work drive, the `P:\Mods` junction, `allowFilePatching` in `serverDZ.cfg`, the Steam session, AddonBuilder for a build) and creates the junction when it is missing. Preflight is the report-and-warn check for everything else.

## What it checks

| # | Check | Severity |
|---|---|---|
| 1 | `P:\` drive is mounted | **hard fail**, exit 1 |
| 2 | DayZ Tools installed (`Bin\AddonBuilder\AddonBuilder.exe` found) | warn |
| 3 | DayZ Diag installed (`DayZDiag_x64.exe` found; `/dayz-launch-test` needs it) | warn |
| 4 | DayZ Server installed (`DayZServer_x64.exe` found; `/dayz-add-server` copies mission templates from it) | warn |
| 5 | Vanilla DayZ data unpacked under `P:\`, and vanilla scripts under `P:\scripts` | warn |
| 6 | `P:\Mods\` is a junction to `<DayZ install>\!Workshop\`. Absent: created. Absent while the game is found but its `!Workshop\` folder is not: reported with the `mkdir` command for that folder, nothing created. Real folder, dangling link, or link to anywhere else: reported, left untouched. | warn here; `/dayz-build-pbo` and `/dayz-deploy-pbo` hard-fail on it |

Exit code 0 = ready (or warnings only). Exit 1 = `P:\` not mounted, named in stderr.

## How paths are resolved

First hit wins. A `*_PATH` env var whose value fails its check is skipped, the next source is tried, and preflight prints `[WARN]  <VAR> ignored: <value>` with what the value must contain, so a setting that had no effect is never silent:

| What | Order |
|---|---|
| **DayZ Tools** | `DAYZ_TOOLS_PATH` env var, then the registry (`Path` under `HKLM\SOFTWARE\WOW6432Node\Bohemia Interactive\DayZ Tools`, its non-WOW6432 and `HKCU` siblings, each tried in turn), then `DayZ Tools` in each Steam library. The first candidate containing `Bin\AddonBuilder\AddonBuilder.exe` wins. |
| **DayZ Diag** | `DAYZ_DIAG_PATH` env var, set to the full exe path (for example `D:\SteamLibrary\steamapps\common\DayZ\DayZDiag_x64.exe`); a folder holding `DayZDiag_x64.exe` also works. Any other value is ignored with a warning. Then `DayZDiag_x64.exe` next to the resolved game, then `DayZ\DayZDiag_x64.exe` in each Steam library. The result is always the exe file. |
| **DayZ Server** | `DAYZ_SERVER_PATH` env var, then `DayZServer` in each Steam library (must contain `DayZServer_x64.exe`). |
| **DayZ game** (for `!Workshop`) | `DAYZ_GAME_PATH` env var, then `DayZ` in each Steam library (must contain `DayZ_x64.exe`). |
| **Vanilla data** | `DAYZ_VANILLA_DATA_PATH` env var, then `P:\dz` (case-insensitive, so `P:\DZ` matches). Must exist and be non-empty. |
| **Vanilla scripts** | `P:\scripts` (vanilla `DZ_Scripts`, unpacked beside `P:\DZ`). Must exist and be non-empty; warns otherwise. |
| **`P:\` and `P:\Mods\`** | Fixed by DayZ convention, not configurable. |

Steam libraries come from the Steam root in the registry (or the default `C:\Program Files (x86)\Steam` and `C:\Program Files\Steam`) plus every library listed in its `steamapps\libraryfolders.vdf`, so installs on other drives are found.

Other skills reuse these resolvers rather than re-implementing discovery: `find_dayz_tools`, `find_dayz_game`, `find_dayz_diag`, `find_dayz_server`, `find_vanilla_data`, `validate_p_mods` and `read_registry_string` (load `preflight.py` through `skills/_shared/skill_helpers.py`).

## Output

```
DayZ preflight

[OK]    P:\ is mounted
[OK]    DayZ Tools found: C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools
[OK]    DayZ Diag found: D:\SteamLibrary\steamapps\common\DayZ\DayZDiag_x64.exe
[OK]    DayZ Server found: D:\SteamLibrary\steamapps\common\DayZServer
[OK]    Vanilla data found: P:\dz
[OK]    Vanilla scripts found: P:\scripts
[OK]    P:\Mods -> D:\SteamLibrary\steamapps\common\DayZ\!Workshop

Preflight complete.
```

On a first run where `P:\Mods\` did not exist, the last check prints `[OK]    Created junction P:\Mods -> ...\DayZ\!Workshop` before the `P:\Mods ->` line.

If `P:\` is not mounted:

```
DayZ preflight

[FAIL]  P:\ is NOT mounted
        Open DayZ Tools and mount the P drive (Tools menu > Mount P drive), or run /dayz-workdrive.
```

Exit 1; downstream DayZ skills refuse to run.

## Before a debug or diagnosis session

A build needs only the checks above. Diagnosing a bug also needs the files to compare against. Before a debug session, confirm these are on `P:\` and ask the user to mount or unpack whatever is missing:

1. The unpacked vanilla scripts under `P:\scripts`. They are the authority on engine, action and vehicle behaviour: `CarScript`, for example, is declared at `P:\scripts\4_world\entities\vehicles\carscript.c:94`. Preflight already warns when this folder is missing or empty.
2. The mod's own tree on `P:\` (`P:\<ModName>\`, the link `/dayz-new-mod` creates to `workspace/<ModName>/`) and, for a packed test, its PBOs under `P:\Mods\@<ModName>\Addons\`, to confirm what is actually in the build under test.
3. The working reference mod the broken one is being compared with, when there is one.

Without them a diagnosis falls back on memory and diffs. Preflight does not check items 2 and 3, because they depend on the mod. This rule comes from a vehicle mod debug session (the LFQuad quad bike, May 2026).

## References

These hold checks and notes that `preflight.py` does not run.

| Question | File |
|---|---|
| Object Builder's Buldozer preview never opens. Is the external viewer path valid? | `references/object-builder-viewer.md` |
| What does DayZ 1.30 change for the environment (`-cacheP3D`, an unpacked `-mod` folder, the new Workbench editors)? | `references/dayz-1-30.md` |
| What replaces each check on Linux? | `references/linux.md` |

When the work has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), follow `/dayz-mod-dev`, the entry point for mod development.

## Do not

- Don't mount `P:\` from here. That is `/dayz-workdrive`'s job; when DayZ Tools cannot mount the drive it falls back to `subst P: "<folder>"` itself.
- Don't "fix" a wrong `P:\Mods\` automatically. A real folder may hold the user's files; the warning gives the manual fix.
- Don't treat the Tools, Diag, Server, vanilla data or junction warnings as fatal in preflight itself. The user may have a custom layout; build skills enforce what they need.
