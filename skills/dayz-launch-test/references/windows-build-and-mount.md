# Build, file patching and mod mounting on Windows

How a change reaches the engine on Windows: what AddonBuilder keeps or drops for script, asset and mixed mods, what `-filePatching` really serves, what a release build must prove, and why mod paths must be absolute.

AddonBuilder, launcher and engine mount behaviour was measured on one Windows test machine and is not checked on `P:\`; the parameters live in the engine and tools, not in the scripts. The mount probe asks `ConfigIsExisting` with a config path that contains a space, the same form vanilla uses: `g_Game.ConfigIsExisting(CFG_VEHICLESPATH+" "+type_name)` (`P:\scripts\4_world\systems\inventory\attachmentsoutofreach.c:82`). The launch loop itself is in `windows-launch-cycle.md`; `/dayz-build-pbo` is the supported build in this repo.

## Build and deploy

`-Build` runs `AddonBuilder P:\<Mod>` into `P:\Mods\@<Mod>\Addons\<Mod>.pbo`. Build whenever assets (`.p3d`, `.paa`, `.rvmat`) change: file patching does not reliably load binarized models and textures.

| Mod | What AddonBuilder does | What to do |
|---|---|---|
| Scripts only | Its default binarize mode drops `.c` files (they are not in its include list), leaving a config-only PBO that mounts with no script running. | `Invoke-Build` adds `-packonly` when the source has no `.p3d`, `.paa` or `.rvmat` (force it with `-PackOnly`) and warns when a mod with a `scripts\` folder packs suspiciously small. |
| With `.asi` or `.anm` | Binarize mode drops them unless `-include` lists `*.asi;*.anm`. A weapon with its own player animation graph (`AddItemInHandsProfileIK` with its own `.asi` as the second argument) then builds without the graph: the reference points at a missing file and the build still reports success. | Put `*.asi;*.anm` in the include list, and check that the file shows as an entry in the PBO header, not only as a string inside the compiled script. |
| Assets plus scripts | `-packonly` is not added when `.p3d` or `.paa` are present, and `Invoke-Build` never passes `-include` (only `-prefix`, `-temp`, and `-clear` or `-packonly` when they apply). So binarize drops `.c`, `.paa`, `.ogg`, `.rvmat`, `.layout` and `.csv`, and the PBO mounts with no script running. The size warning (under 4096 bytes) misses it, because binarized `.p3d` files keep the PBO large: 170 files and 95.1 MB without an include list against 451 files and 106.8 MB with one. | Build with `AddonBuilder <src> <out> -prefix=<Mod> "-temp=<tmp>" "-include=<lst>" -clear` and the list `*.c;*.asi;*.anm;*.paa;*.rvmat;*.layout;*.ogg;*.ptc;*.csv`, then count the PBO entries or search it for a known `.c`. The list filters what is synced and does not define the PBO, so check the real entries (`build-and-storage-traps.md`, on the mixed build). |

The mixed-mod failure usually arrives when a mod moves from a hand-written AddonBuilder command to the generated scripts. On a mod with three script files the PBO held 22 entries and 401,857 bytes without the include list and 25 entries and 411,786 bytes with it; the gap was exactly the three `.c` files. The hand command passed `-include=...\tools\include.lst`, a list made by hand, but setting up the scripts for a mod copies only `dayz-test.ps1` and the three `.bat` wrappers, never an `include.lst`, and `Invoke-Build` passes no `-include`. Switching to `server.bat` or `dayz-test.ps1 -Build` then drops every script with no visible change: the PBO stays large and the size warning never fires. In game the mod mounts but no action appears, which looks exactly like an unregistered `ActionConstructor` or a bad `ActionCondition`, so the wrong file gets debugged. List the fresh PBO before you spend a test cycle.

A local patch to `Invoke-Build` passes the include list when it exists and the build is not pack-only:

```powershell
$incLst = Join-Path $PSScriptRoot 'include.lst'
if (-not $usePackOnly -and (Test-Path $incLst)) { $abArgs += "-include=$incLst" }
```

It also replaces the size check (a `scripts\` folder and a PBO under 4096 bytes) with a content check: when the source has `scripts\`, list the PBO (for example with `BankRev -lf`) and require the packed `.c` count to equal the source `.c` count. The template in `scripts/` does not carry this patch.

Then launch the diag exe in the chosen mode. Edit a model, run again with `-Build`. Edit a script, rebuild the PBO too, unless the probe below showed that your install serves the source.

## A release build must prove itself

An exit code of 0 is not a successful build (`exit_0_is_not_build_success`). AddonBuilder can leave an old PBO in place after a later copy step fails, so the exit code and `Test-Path` alone do not prove that the requested bytes were built or deployed. A release verdict needs evidence of a fresh PBO, the expected `header_prefix` and file entries, a clean scan of the log for fatal lines, and a valid `.bisign` when signing is expected.

A release workflow should also work like this, though it is not checked in game: build the candidate outside the published path, validate it, and publish only after every check passes. On any failure the previous artifact stays unchanged, and the build manifest and cache do not move. The cache key covers input bytes, build options, prefix, DayZ build, tool versions and hashes, and the signing key identity. The preflight rejects case and path conflicts, files excluded but referenced, absolute packed paths, stale or missing `.paa` dependencies, and ODOL inputs it cannot handle, before binarizing.

The generated dev launcher does none of this. Use its PBO for iteration, and do not call the result ready for release until `/dayz-build-pbo`, `/dayz-gate build` and `/dayz-release-pack` have supplied these guarantees.

## What file patching serves

`-filePatching` is meant to load scripts and configs from raw source, not binarized assets. Model, texture and material changes need `-Build`; never tell the user "just edit and it reloads" for a `.p3d` or `.paa` change, which is the most common false expectation here.

On the measured install even scripts did not load from the work drive. With `-filePatching` on server and client, `allowFilePatching=1`, the work drive mounted and `P:\<prefix>\scripts\...` present, the engine still compiled the scripts from the PBO: probe prints that existed only in the source never appeared over two boots, and appeared at once after a pack-only `dayz-test.ps1 -Build`. So:

1. Treat the PBO as the only source of scripts until the probe below says otherwise on your install. Every Enforce Script change then needs a pack-only rebuild (seconds) and a relaunch.
2. Loose model and texture files on the work drive are just as unproven. Do not blame stale visuals on loose files and do not expect fresh visuals from them; check what the engine runs. A stale model tree on the work drive that was suspected of shadowing the deployed model never did.
3. The source probe settles it in one boot. Change a log string on a line that already prints, in the source only (for example `[TAG]` to `[TAG srcprobe]`), relaunch without rebuilding, and search the script log. The new token means the source was served; the old string still printing means the PBO was. Run it before spending cycles on "why does my script change do nothing".

## Mod paths must be absolute

A bare `-mod=@Name` is resolved relative to the engine's working directory, the game folder, as `<DayZ>\@Name`. Deployed mods live under `<DayZ>\!Workshop\@Name`, so that path does not exist and the engine silently fails to mount the addon: its `CfgPatches` and `CfgVehicles` classes never register, and `CreateObjectEx` later returns null with no RPT error. The server boots, the mission runs, nothing logs an error, and the mod's classes are missing.

A `ConfigIsExisting("CfgPatches <Mod>")` probe in the mission on a headless `-server` showed it:

| `-mod=` | Result |
|---|---|
| `@<Mod>` (relative, working directory the game folder) | `CfgPatches.<Mod> = 0`, absent |
| `<DayZ>\!Workshop\@<Mod>` (absolute) | `CfgPatches.<Mod> = 1`, and the mod's base class exists |

The failure is not always silent:

- A relative path that climbs out of the server folder with `..\` does not mount either, and it is loud. The retail DayZServer 1.30, given one in `-serverMod`, stopped at an error window `Cannot open file '<server>\..\..\...\@Name\addons\<pbo>'`, wrote an `ErrorMessage_DayZServer_x64_<date>.mdmp` into the profile folder and never reached the mods' `PBO Load` lines; its RPT says nothing about it.
- On the native Linux server the rule is reversed: an absolute `-mod=` or `-servermod=` mounts nothing and gives no error, so paths go relative to the server tree (`linux-native-server.md`, on running it headless).

`Get-ModString` rewrites every bare `@Name` to its absolute `!Workshop` path through `Resolve-ModToken`. It handles names with spaces such as `@Dabs Framework` and passes through tokens that are already rooted or not found under `!Workshop`. This applies to server, client and offline.

Not checked:

- The probe confirmed only the mount of the mod under test. Whether base mods mount by relative name in `all` mode (client present) was not isolated; resolving them all to absolute paths makes the question moot.
- Checking a dependency's mount needs its real `CfgPatches` name, not its folder name: `@CF` is `JM_CF_Scripts` (read from `@CF\addons\scripts.pbo`). A probe asking for `"CF"` gives a false negative.
