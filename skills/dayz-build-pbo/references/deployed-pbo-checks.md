# Checking the deployed PBO

How to make sure the PBO the game loads is the one you built, from the sources you meant, and why a mod that mounts can still run nothing. The gates on a fresh build are in `post-build-gates.md`.

This is measured behaviour of AddonBuilder and the game's loader, not vanilla data on `P:\`. Only the trailer check below was measured on vanilla PBOs, the ones the game ships.

## A mod can have two PBOs

The game loads the PBO in `P:\Mods\@<Mod>\Addons\`, whatever else exists. On one vehicle mod a freshness gate pointed at a second PBO in the source tree:

| Path | Size | Model inside |
|---|---:|---|
| `<Mod>\<Mod>.pbo` in the source tree | 5.92 MB | Binarized `.p3d` (ODOL) |
| `P:\Mods\@<Mod>\Addons\<Mod>.pbo`, the deployed one | 17.22 MB | Unbinarized MLOD |

Both were complete, with 73 entries, 5 `.c`, 36 `.paa` and 23 `.rvmat` each, and the size gap came from binarizing, not from anything missing. The deployed one was the older of the two.

- Check every PBO that exists for the mod, not one chosen by hand. If any of them lacks what the model needs, or is older than the sources, the verdict is red. A gate that looks only at the source tree's PBO can pass on a deployment that never got the work.
- Check that a `.p3d` is present by name, never by size: one route binarizes it and the other does not, and the same model was 5.4 times larger in one package.
- A freshness gate that walks the source tree must skip `*.pbo`, `*.bisign`, `*.bak*` and temp files. A backup is written after the file it copies, so counting it as source keeps the gate red for ever.

## A surviving `-temp` tree packs old sources

"Build Successful" does not mean your sources were packed. A wrapper that cleans AddonBuilder's `-temp` with `shutil.rmtree(temp, ignore_errors=True)` hides the failure when something locks the folder (Explorer, an antivirus, a running game), and the old tree survives. AddonBuilder then regenerates only what it writes itself, `config.bin` from your `config.cpp` and `texHeaders.bin`, packs the old `gui/`, `scripts/` and `data/`, and reports `Build Successful` with code 0. Each rebuild moves the `.pbo` timestamp and not its content.

The sign inside the `-temp` tree: `config.bin` and `texHeaders.bin` are minutes old, while `gui/`, `scripts/` and `data/` are days or weeks old. In the measured case the deployed package was a week behind the source tree: 14 files differed, a whole `.layout` was missing, and `config.cpp` was not copied.

Two traps when checking for it:

- **Counting loose version strings does not discriminate.** The old package held 80 matches of `"1.2.3"` and 1 of `"1.2.4"`, mixing comments, changelogs and old migrations. Search for the exact literal of the constant: `grep -c -a -F 'MYMOD_VERSION_STR = "1.2.4"'` gives one against zero.
- **Larger is not more complete.** The right package was 8.4 MB smaller than the stale one (99.6 MB against 108.0 MB), because the uncleaned temp tree had collected leftovers from earlier builds. A gate that blocks a shrinking PBO would have blocked the good one.

The check that catches it carries a positive control: one marker that exists only in the new sources, and one that must exist in both. If the second is missing too, the grep is broken and the first result means nothing.

```bash
grep -c -a -F "<new marker>"     <path>/Addons/<Mod>.pbo   # must be 1 or more
grep -c -a -F "<control marker>" <path>/Addons/<Mod>.pbo   # must always be 1 or more
```

The fix is a removal that fails closed. `build.py` removes `P:\temp\<ModName>\` before every build and stops when the folder survives (step 11 in `SKILL.md`). A wrapper of your own needs the same check after its `rmtree`: stop when the temp folder still exists, and never let `ignore_errors=True` decide what gets packed.

## Moving a project to another machine

A copy of the sources does not bring Steam's `!Workshop` folder or the server profiles. Before the first in-game test on the new machine, list those outside dependencies and profiles, list the deployed PBO's entries, and compare each expected entry with the current tree by content hash. Equal whole-PBO bytes are no substitute for comparing per entry; rebuild and deploy on any difference you cannot explain. Run source sync steps only in a mode that cannot overwrite restored sources with stale build output.

In PowerShell, `powershell -File x.ps1 -Array a,b` passes one string, so a gate fed that way fails without deploying; call the script with `&`.

## Two causes of a mod that mounts and runs nothing

Both look like the dropped `.c` case in `post-build-gates.md`: the mod mounts, nothing runs, the log is empty. Both can be decided offline in seconds, so rule them out before you spend a game session reading silence.

**The script module name picks the compile layer.** `CfgMods.<Mod>.defs` must map each source folder to its own module: `3_Game` to `gameScriptModule`, `4_World` to `worldScriptModule`, `5_Mission` to `missionScriptModule`. `4_World` files declared under `gameScriptModule` pack with no warning, but the code never reaches the layer where its base classes exist. A test mod that declared `files[]={"<Mod>/scripts/4_world"}` under `gameScriptModule` ran nothing at all, while two working mods on the same machine use `worldScriptModule` for `4_World`. `/dayz-lint` reports the mismatch as `script-module-layer`.

Match the case of the folder too, on disk and in `config.cpp`. Working mods ship `4_World` and `5_Mission` capitalised; a lower-case tree packs lower-case paths while `config.cpp` asks for the capitalised ones, and Windows does not tell you.

```powershell
# Declared modules against what is on disk
$cfg = Get-Content "$mod\config.cpp" -Raw
[regex]::Matches($cfg,'class\s+(\w+ScriptModule)') | % { $_.Groups[1].Value }
[regex]::Matches($cfg,'"([^"]*scripts/[^"]+)"') | % {
  $p = Join-Path $mod ($_.Groups[1].Value -replace '^[^/]+/','' -replace '/','\')
  "{0} -> on disk: {1}" -f $_.Groups[1].Value, (Test-Path $p) }
```

**Every vanilla PBO ends in a 21-byte trailer that home-made packers leave out.** The trailer is one `0x00` byte followed by the SHA-1 of everything before it, `trailer == b"\x00" + sha1(data[:-21]).digest()`. Six vanilla PBOs from 10 KB to 350 MB all match (`ai.pbo`, `ai_bliss.pbo`, `animals.pbo`, `animals_bliss.pbo`, `anims_anm_infected.pbo` and `anims_anm_player.pbo` in the game's `Addons` folder). AddonBuilder writes it, and `pbo_entries.py` checks it on every `/dayz-build-pbo` build. A custom packer usually does not, because a PBO without it still parses with any reader you write yourself, and a round-trip test compares the packer only with its own output.

Whether the engine rejects a PBO without the trailer is not established, and in the measured case it was not the cause. Write it anyway; the append is idempotent and removes one variable:

```python
data = open(pbo, "rb").read()
if not (len(data) > 21 and data[-21] == 0
        and hashlib.sha1(data[:-21]).digest() == data[-20:]):
    open(pbo, "ab").write(b"\x00" + hashlib.sha1(data).digest())
```

## Gate order in a build script

A build step that reports success without checking `$LASTEXITCODE` after each AddonBuilder call, and a deploy step that accepts a PBO on `Test-Path` alone, both hand you a stale file and call it fresh. Check the result after every call; for AddonBuilder, whose exit code is 0 even on failure, read the rpt's `[ResultCode]` and check that the PBO exists and was rebuilt (`addonbuilder-rules.md`). Print a SHA-256 build id at pack time that a boot marker inside the mod can be checked against; otherwise an old PBO looks the same as a new one that does nothing.

## Two more rules

- **A compile error in a vanilla file may be a cascade.** Facing `quoted string not closed`, an unexpected end of file or a line in a vanilla script, look for a BOM or a truncated file earlier in the same module first. Diagnose and fix at byte level on the machine that holds the real files, not on a stale mount.
- **Load order follows `requiredAddons[]`.** The dependency graph orders the compile across mods within each script layer (`skills/dayz-launch-test/references/dayz-1-30-server-measured.md`, "Mod load order is not the `-mod` order"). Avoid putting code in `1_Core` or `2_GameLib` unless you need that layer; shared data belongs in `3_Game`.
