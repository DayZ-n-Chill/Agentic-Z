# Mount probe and test helpers for a new mod

How to check that a new mod mounts before any model or physics exists, and what to change when you copy a test launcher, spawn mission and verdict parser from one mod to another.

The probe and the traps were measured on test servers with per-mod helper scripts; they are not checked on `P:\`. Those helpers (a physics test launcher, a mount probe launcher, a mission `init.c` that spawns the subject, a verdict parser) are not part of this repo: the notes describe traps to avoid when you write or copy them.

## A mount probe before a physics test

For the first build, deploy and mount check of a new mod, before a model or physics exists, do not use a physics test that spawns and measures. Use a minimal mount probe:

1. A stub with only `CfgPatches`: a `config.cpp` with `class CfgPatches { class <Mod> { requiredAddons[]={"DZ_Data"}; }; }` plus `$PBOPREFIX$`, built with `-packonly`.
2. Build the stub with `/dayz-build-pbo` and start only a server with no other mods, since the stub needs only vanilla.
3. A mission whose `init.c` is a minimal `MissionServer` that on its first `OnUpdate` (once, behind a flag) runs `GetGame().ConfigIsExisting("CfgPatches <Mod>")` and prints `[<MOD>-MOUNT] CfgPatches.<Mod>=0|1`. Vanilla calls it the same way, with a config path that contains a space: `g_Game.ConfigIsExisting(CFG_VEHICLESPATH+" "+type_name)` (`P:\scripts\4_world\systems\inventory\attachmentsoutofreach.c:82`).
4. Poll `script*.log` for `[<MOD>-MOUNT]`, and run `BankRev -lf` on the deployed PBO to list what it holds.

It is fast because an empty `void main()` in `init.c`, replacing the vanilla one, skips `CreateHive()` and the Central Economy, so the mission loop starts in seconds rather than minutes (about 20,000 loot items are never loaded). It needs no client, unlike spawning a `CarScript`. The result arrives about 50 s after launch, server only, headless.

## Copying a vehicle physics test to another mod

A physics test written for one vehicle (a launcher, an `init.c` that spawns the vehicle and a control, a verdict parser) carries ties to that vehicle that break silently when copied. Review all four before you trust the copy:

- It never spawns in a server-only run. The spawn `init.c` waits for `players >= 1`, because a `CarScript` simulates only with a player present, so a server-only run never spawns and times out with no samples. Make the client required for a physics run, or fail early when there is none.
- The dev build check demands a debug token that does not exist. A check that requires a `<MOD>-DBG` token in the PBO depends on debug code inside the first mod's vehicle. A clean mod has none, and debug code does not ship, so the check rejects a valid build. Check the product instead: the expected `.c` and config files listed by `BankRev -lf`.
- An inline PowerShell verdict that ignores the control vehicle. If the launcher computes PASS from the subject alone while the Python parser requires the control to settle (INVALID-RUN otherwise), and the launcher never calls the parser, a run passes with a missing or broken control and the negative control is worthless. Have the launcher call the parser and honour its exit code, or port the control check to PowerShell.
- PowerShell `-replace` ignores case by default. Retargeting `'OldMod'` to `'<Mod>'` also rewrites `OLDMOD-DBG` to `<Mod>-DBG` and `[OLDMOD-DBG]` to `[<Mod>-DBG]`. Check the tokens after the swap, or use `-creplace` where case matters.

## Moving the test scripts to a new mod

Only the per-mod helpers carry the old mod name and need a case-sensitive swap: the physics test launcher, the mount probe and its `init.c` (including the bracketed `MOD-MOUNT` print token), the spawn `init.c` (class name and wheel attachments), the verdict parser, and any `.bat` wrappers (`set MOD=`). Generic p3d utilities copy unchanged.

Do the swap on the host with PowerShell `-creplace` and `[System.IO.File]::WriteAllText` as UTF-8 without BOM, not through a sandboxed shell whose view of the files can be cached, and not with an editing tool on a `.py` inside a OneDrive folder, which risks null bytes. Afterwards, search the new folder for leftover old-mod tokens (there must be none) and confirm the new ones landed: wheel attachment, class name, probe token, `set MOD=`. The control vehicle, `CivilianSedan`, is shared across mods and never changes.
