---
name: dayz-launch-objectbuilder
---

# /dayz-launch-objectbuilder

Open Object Builder without leaving the terminal. Optionally pre-loads a `.p3d`, or sets the working folder to a specific mod's `P:\<ModName>\` so the file dialog opens inside it.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## What it does

1. Gates on `/dayz-preflight`.
2. Locates `ObjectBuilder.exe` via DayZ Tools.
3. Verifies the registry has been populated by `/dayz-setup-objectbuilder` — fails with a clear hint if not.
4. Resolves the open target:
   - `--file <path>` → opens that `.p3d` directly.
   - `--mod <ModName>` → sets working dir to `P:\<ModName>\` so the open-dialog lands there.
   - Neither → no argument; Object Builder opens its last-used file.
5. Spawns `ObjectBuilder.exe` with `DETACHED_PROCESS` so the shell returns immediately. The window may take 2-5s to appear.

## How to run

**Just open the editor:**
```cmd
python .claude\skills\dayz-launch-objectbuilder\launch.py
```

**Open a specific .p3d:**
```cmd
python .claude\skills\dayz-launch-objectbuilder\launch.py --file P:\MyMod\data\model.p3d
```

**Open with a mod folder as working directory:**
```cmd
python .claude\skills\dayz-launch-objectbuilder\launch.py --mod MyMod
```
(Requires `P:\MyMod\` to exist — typically created by `/dayz-new-mod`.)

## When to run

- Anytime you need to inspect or edit a `.p3d` model.
- After `/dayz-new-mod` produced a scaffold and you want to drop a model into `data/`.
- Before adding LODs, named selections, or memory points to a custom asset.

## Output

```
DayZ Object Builder launcher

[OK]    P:\ mounted
[OK]    DayZ Tools: ...
[OK]    Vanilla data: P:\dz
[OK]    P:\Mods junction valid

[OK]    ObjectBuilder.exe: ...\Bin\ObjectBuilder\ObjectBuilder.exe
[OK]    Registry configured
[INFO]  Opening: P:\MyMod\data\model.p3d

[OK]    Object Builder launched (PID 12345). The window may take a few seconds to appear.
```

## Flag rules

- `--file` and `--mod` are mutually exclusive — pass one or neither.
- `--file` accepts an absolute path. Warns if the extension isn't `.p3d` (Object Builder may refuse).
- `--mod` is just the mod name; the skill expands to `P:\<ModName>\`. Fails fast if the folder isn't there.

## Why detached

Running Object Builder under the parent shell would block the terminal until you close the editor. We spawn with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` so:

- Closing this terminal doesn't kill Object Builder.
- The skill exits immediately after the spawn.
- The PID is printed so you can find/kill it later if needed.

## Do not

- Don't run before `/dayz-setup-objectbuilder` on a fresh machine — the skill will tell you to run setup first.
- Don't pass relative paths to `--file` unless you're sure of cwd — absolute paths are safer.
- Don't spam-launch — Object Builder isn't designed to run multiple instances against the same file.
