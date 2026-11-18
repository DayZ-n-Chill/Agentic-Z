# DayZ 1.30 on a running server: what was measured, not only read

`dayz-1-30-mod-workflow.md` and the other `dayz-1-30-*.md` references come from reading vanilla scripts. This file holds what was observed by booting test mods on a dedicated server: things a source file cannot show (a function that silently does the wrong thing, a path rule, a crash), plus the Community Framework and Expansion facts a 1.30 server needs.

**Where the measurements were taken.** On the native **Linux** `DayZServer`. 1.30 is the stable release; the whole set was measured again on DayZ 1.30 stable (2026-11-13; build not recorded). An entry's build says where it was first measured: the 1.30.164014 pre-release (`1.30.164014.27`, 2026-10-02, then on Experimental) unless it names 1.30.164200 (`1.30.164200.56`, build 25963285, 2026-10-23), 1.30.164078.38 or 1.30.164289. Windows servers were not tested; where a Windows rule differs, `skills/dayz-launch-test/references/windows-launch-cycle.md` says so. The rig to repeat any of it is in `skills/dayz-launch-test/references/linux-native-server.md`.

**What was checked on `P:\`.** Measured behaviour cannot be read from a file, so it stays marked as measured and is not yet checked on `P:\`. Wherever a statement is about a declaration, the vanilla file on `P:\` was opened and is cited. The data on `P:\` at the time was a 1.30 build from before 1.30.164200 (game storage version 144), so the "now" side of section 6 could not be checked there.

## 1. The version define

- The engine defines only the current version. Vanilla documents the define as "filled in with the current Major and Minor version" (`DAYZ_X_XX`, `P:\scripts\1_core\defines.c:12-14`). Measured: the `defines:` of a 1.30 server's `Module:` lines contain `DAYZ_1_30`, and 1.30 does **not** define `DAYZ_1_29` (1.29 did not define `DAYZ_1_28`).
- So write plain current code without a version `#ifdef`; `#ifdef DAYZ_1_30` would drop the code again on the next release. Only if the user asks for a mod that must still load on an older server: put the **old** code under that version's define and the current code in `#else`, so the current code stays the default.
- `string v; g_Game.GetVersion(v);` gives the full run-time build, for example `"1.30.164014.27"`; use it for logging (`GetVersion` is declared at `P:\scripts\3_game\global\game.c:942`). It cannot select code that would not compile; only a define can.
- A mod's own `defines[] = {"MYMOD"};` in `CfgMods` works with `#ifdef MYMOD`. The mod name of a loaded mod is a define too (`#ifdef AutoTest`; `skills/dayz-launch-test/references/linux-headless-client.md`).
- `BUILD_EXPERIMENTAL` and `DIAG_DEVELOPER` exist only on diag and experimental builds; never use them to mean "1.30".

## 2. `FindFile` and file paths

**Current state: fixed in 1.30.164200.** Measured on build 25963285: `FindFile` resolves `$profile:`, `$mission:`, `$saves:` and `$storage:` again, and backslash patterns work too. The script declarations did not change: `FindFile`, `FindNextFile`, `CloseFindFile`, `FindFileHandle`, `FileAttr` and `FindFileFlags` in `1_Core/proto/EnSystem.c` are byte for byte the same as in 1.29, so Bohemia fixed the native binding only and nothing needs a new signature. On `P:\` the three functions are at `P:\scripts\1_core\proto\ensystem.c:520-522` (`FindFile`, `FindNextFile`, `CloseFindFile`) and the `FindFileFlags` enum at `P:\scripts\1_core\proto\ensystem.c:513-518`. The measured matrix on 25963285, with `-profiles=profiles` inside the server folder and with an absolute `-profiles=/var/tmp/<dir>` outside it, both the same:

| Pattern | Result |
|---|---|
| `$profile:*`, `$profile:fftest/*.json` (also with `\`), with `FindFileFlags.DIRECTORIES` | the profile folder's entries; files and the `sub` dir |
| `$mission:fftest/*.json`, `$mission:*` | `m.json`; the mission's `cfg*.xml` |
| `$saves:*` | `DayZ.cfg` |
| `$storage:*` | `data`, `backup`, `players.db`, `spawnpoints.bin` once the mission runs; nothing in `main()` or on a first boot |
| relative `profiles/fftest/*.json` (either slash) | found |
| `FindFile(..., -1)` | same as `ALL` |
| `CF.FindFileEx` (Workshop CF 1.5.9 of 2026-10-12) | passes through to `FindFile` |

**Removing the workarounds** (measured on 1.30.164200; this does not by itself prove the behaviour of every later 1.30 build):

- `CF.FindFileEx(...)` becomes `FindFile(...)` with the same arguments. Leaving it costs only a test file `$profile:cf_findfile_dz130_test`, so it is cleanup, not a fix; a mod that needed CF only for it can drop CF.
- A copied `YOURMOD_FindFilePath(p)` wrapper becomes plain `p`; then delete the helper and the leftover `$profile:yourmod_findfile_dz130_test` and `cf_findfile_dz130_test` files. (The helper is not shipped here: it only served 1.30 builds before 164200.)
- The profile folder no longer has to sit inside the server executable's folder; an absolute `-profiles=` works with plain `FindFile` and with `CF.FindFileEx`. A mission folder or `-storage=` outside it was not tested.
- Keep the loop shape: the first match arrives in `fileName`, then `FindNextFile`, then `CloseFindFile`. Results are bare names, so open each by the placeholder path (`"$profile:MyMod/" + fileName`). Enforce Script has no `do { } while` (`Can't find variable 'do'`), so loop with `bool found = fileName != ""; while (found) { ...; found = FindNextFile(h, fileName, attr); }`.
- Before removing anything on an unknown server, check `g_Game.GetVersion(v)`: there is no define for the point release.

**History, 1.30.164014 and the 1.30 release (build 25956772).** `FindFile` ignored the placeholders and, with no error, listed the server's working directory instead (`FindFile("$profile:*")` returned `DayZServer`, `addons`, `keys`, ...); backslash paths found nothing. The reported cause, not yet checked on `P:\`: the binding passed the `FindFileFlags` value where the reworked native expects a file system index. The workarounds were `CF.FindFileEx` (CF 1.5.9 or newer), or a port of it for mods without CF, and both reduced an absolute `-profiles=` to its last component, which is where the announced "profile folder must be inside the server folder" rule came from. Every other file function worked with the placeholders on those builds.

**Still true on 25963285**:

- **`$storage:` is not available during mission start.** `FileExist`, `MakeDirectory` and `OpenFile` on it returned false in the `MissionServer` constructor, in `OnInit()` and on both sides of `OnMissionStart()`, and true from the first `MissionServer.OnUpdate()` or `CallLater` tick, 7 to 10 s later. On the very first boot of an instance (no `storage_1` yet) it stayed unavailable for the whole 60 s run: fall back to `<mission folder>/storage_<instanceId>/`. The 1.30 build ignored a relative `-storage=<dir>`; do not combine `-storage` with `$storage:`.
- **`g_Game.GetMissionFolderPath()` returns `""` on 1.30 Linux servers**, while `GetMissionPath()` is `mpmissions/dayzOffline.chernarusplus/mission.c`. The cause is visible in vanilla: `SetMissionPath` looks only for `"\\"` when it cuts the folder out of the path (`P:\scripts\3_game\dayzgame.c:1207-1221`), and `GetMissionFolderPath` returns what that left (`P:\scripts\3_game\dayzgame.c:1228-1231`). Derive the folder from `GetMissionPath()`.
- Write forward slashes in every path you build (`dir + "/" + name`); they work everywhere.

## 3. Script module paths in `CfgMods` need forward slashes

With `files[] = {"MyMod\scripts\4_World"};` a 1.30.164014 server loads the mod's config and shows its `CfgMods` defines, but compiles **none** of its scripts and prints no error: the World module count stays at vanilla (2321). `files[] = {"MyMod/scripts/4_World"};` fixes it. The case of the folder name made no difference. Found in a Workshop mod whose five PBOs all used backslashes. Check every `worldScriptModule`, `gameScriptModule` and `missionScriptModule`, also in a debinarized `config.bin`. Not tested again on 25963285 and not tested on Windows.

In this repo `/dayz-new-mod` writes these paths with forward slashes, and `/dayz-lint` checks that each listed folder exists (`script-module-path`). Lint does not yet flag a backslash in `files[]`.

## 4. Compile failures, measured

- On the 1.30 pre-release a script compile failure was followed by a **segfault** of the server, right after `Can't compile "World" script module!`. A crash at boot is often a compile error: read `script_*.log` first.
- Override signatures confirmed by a failing boot ("marked as override, but there is no function with this name"). Adding a parameter, even with a default, changes the signature.
  - `EntityAI.ProcessVariables()` and the `ItemBase` override are now `ProcessVariables(float elapsedTime)` (`P:\scripts\3_game\entities\entityai.c:3913`; the `ItemBase` override at `P:\scripts\4_world\entities\itembase.c:4659`).
  - `Construction.SetParent(BaseBuildingBase)` is now `SetParent(EntityAI parent)` (`P:\scripts\4_world\classes\basebuilding\construction.c:44`); `Construction` now extends `ConstructionBase` (`P:\scripts\4_world\classes\basebuilding\construction.c:2`), which extends `ConstructionBasic` (`P:\scripts\4_world\classes\constructionbase.c:30`).
  - `CarScript.ToggleHeadlights()` is gone (no declaration anywhere under `P:\scripts\`); use `LightToggle()` on `Transport` (`P:\scripts\3_game\vehicles\transport.c:236`).
- Historical, not corroborated: an earlier note said `Settings`, `GameSettings` and `SettingsMenu` (2_GameLib) were always under `#ifdef GAME_TEMPLATE`. Do not use that sentence as a current rule.
  The vanilla file now holds one line only, `// removed due to mod conflicts` (`P:\scripts\2_gamelib\settings.c:1`).
- A `modded class` must live in the **same script module as the class it modifies**. `Transport` is a `3_Game` class (`P:\scripts\3_game\vehicles\transport.c:68`), so `modded class Transport` in `4_World` fails with `Unknown type 'Transport'`; hook `CarScript`, `BoatScript` or `MotorbikeScript` instead.

## 5. Silent breakers, measured

- **`OnCEUpdate()` is never called on 1.30.** It is still declared, with `[Obsolete("1.30: Use OnCEIterate(float currentTime, float elapsedTime) instead")]` and no body (`OnCEUpdate`, `P:\scripts\3_game\entities\entityai.c:4924-4925`), so an override compiles with a warning and never runs. Measured over 2 minutes with 20 spawned items: `OnCEUpdate` 0 calls, `OnCEIterate` 446k. Port to `OnCEIterate(float currentTime, float elapsedTime)` (`P:\scripts\3_game\entities\entityai.c:3904`) and call `super` first, as its comment asks.
- Obsolete members compile with `SCRIPT (W): '...' is obsolete`.
- **`ERPCs` values shifted.** `RPC_SYMPTOM_PARAM_SYNC` (`P:\scripts\3_game\enums\erpcs.c:23`) and others were inserted near the top, so every vanilla id after `RPC_PLAYER_SYMPTOM_OFF` (`P:\scripts\3_game\enums\erpcs.c:22`) changed. Mods that send or store vanilla RPC ids as raw integers, or count from one, break. Use the enum names and keep mod ids in your own range (our notes on id ranges are in `skills/_shared/enscript/references/erpc_defines.md`).
- `GAME_STORAGE_VERSION` went from 142 to 144 (`P:\scripts\3_game\global\game.c:5` holds 144): back up `storage_1` before the first 1.30 boot; older servers cannot read it back (the stream itself is in `skills/_shared/persistence/save-load-contract.md` and `dayz-1-30-persistence.md`).

## 6. The 1.30.164200 update (build 25956772 to 25963285)

From comparing the API index of both builds; only the Workbench row was run on a server. The "before" column was checked on `P:\`, which still holds the earlier build, and cites it. The "now" column names the 1.30.164200 file and line; it is not yet checked on `P:\`.

Two changes sometimes listed for 164200 are false: `FilterObstructedObjectsByGrouping` is present in both builds (on `P:\` at `P:\scripts\4_world\static\miscgameplayfunctions.c:1436`), and `IsLockTargetOnUse` is already present in 164078 (on `P:\` at `P:\scripts\4_world\classes\useractionscomponent\actionbase.c:102`). Neither was removed or added in 164200.

| Before (on `P:\`) | Now (1.30.164200, not yet checked on `P:\`) | Effect |
|---|---|---|
| `int GetSupportProvided(int category)` and `int GetSupportRequirement(int category)` on `ConstructionPart` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:371-376`) | `bool GetSupportProvided(int category, out int providedStrength)` and `bool GetSupportRequirement(int category, out int requiredStrength)` (`constructionpart.c:371-378`) | The same change on `ConstructionPartStaticsSupportData` (before: `P:\scripts\4_world\classes\rebuilding\constructionstatics.c:71-79`, `GetSupportProvided`; now `constructionstatics.c:80-89`) and on `ConstructionPartTypeData.GetPartTypeSupport*` (now `constructionparttyped.c:633-641`). Callers and overrides break. |
| `ConstructionPart.TryHandleUtilityParts(EntityAI parent)` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:485`) | `TryQueueUtilityPartsUpdate(ConstructionBase)` (`constructionpart.c:491`, `:885`) | Utility parts update through a queue (`QueueUpdateUtilityParts`, `UpdateUtilityParts`, `constructionbase.c:626-640`). |
| `ConstructionPartTypeData.m_UtilityAutomaticBuild` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:40`) and `GetPartTypeUtilityAutobuildPartsList()` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:674`) | removed | `TriggersUtilityPartsUpdate()` instead (`constructionparttyped.c:478`). |
| (none) | `InvertSupportBehavior()` (`constructionpart.c:387`), `ConstructionPartRebuildInvertedSupport` (`constructionpartrebuildinvertedsupport.c:7`), `ConstructionBase.IgnoreHouseCollisions()` (`constructionbase.c:1521`) | New. None of the three names exists under `P:\scripts\`. |
| `CarScript.IsMoving()` (`P:\scripts\4_world\entities\vehicles\carscript.c:2221`) | declared on `Transport` (`3_game/vehicles/transport.c:819`); new `Transport.HasCrew()` (`transport.c:175`) | Calls keep working. |
| `NavmeshTest` and `NavmeshTest_A` to `_F` (`P:\scripts\4_world\entities\navmeshtest\navmeshtest.c:2`) | `Land_NavmeshTest*` (`navmeshtest.c:2`, `:118`) | Renamed. |
| `Workbench`, `WorldEditor`, `WBModuleDef` and the rest callable from game scripts: on `P:\` the file opens with the `WBModuleDef` typedefs and `class Workbench` with no `#ifdef` around them (`P:\scripts\1_core\workbenchapi.c:1-6`) | the Workbench API classes are guarded (`1_core/workbenchapi/workbench.c:1`), except `WorkbenchPlugin` and `ResourceName`; `ResourceBrowser` and `WorldEditor*` are gone | **Measured on one run only**: DabsFramework 1.51 (`SampleMVC.c:33`, `Workbench.Dialog(...)`) fails with `Can't find variable 'Workbench'`, then `Can't compile "Mission" script module!` and a crash at boot. Wrap such calls in `#ifdef WORKBENCH`. An API index that ignores `#ifdef` still lists the classes. |

The guard itself is mapped in `skills/_shared/enscript/references/workbench_api.md`, "The guard (newer shape)".

## 7. Mod load order is not the `-mod` order

`modded class` blocks from several addons stack in addon **compile** order, and that order follows `requiredAddons` resolution, not the `-mod=` or `-servermod=` string. Measured: a servermod whose `requiredAddons` names `DayZExpansion_Vehicles_Scripts` compiled right after that addon, at a position unrelated to its place in the `-servermod` string. A `-servermod` addon does not compile after every `-mod` addon. So no position in the chain can be relied on; never build a fix on being first or "outermost". Make it independent of order:

- hook an event that provably runs **after** the behaviour you counteract: `EEInit()` runs after the constructor chain, so re-enabling damage there beats a constructor-time `SetAllowDamage(false)` from any position;
- identify targets by data (a class-name prefix, config flags), not by which mod you assume ran first.

## 8. Community Framework and Expansion on 1.30

Third-party mod behaviour, not vanilla: Community Framework (CF), Community Online Tools (COT), Dabs Framework and DayZ Expansion. Our own checked notes on CF and Dabs are `skills/_shared/enscript/integrations/community_framework.md` and `dabs_framework.md` in the same folder.

**CF**:

- Use the regular Workshop **CF 1.5.9 or newer** (1559212036). CF-Test (1625463737) is obsolete: the 1.5.9 PBOs are byte-identical to its last build (checked 2026-10-14). Load only one of them (both declare `JM_CF_Scripts`). The current COT (1564026768) needs no COT-Test either. CF's `config.cpp` still says `version = "1.5.8"`; do not test for the string.
- CF 1.5.9 compiled unmodified on 1.30.164014 with no `SCRIPT (E)` of its own; its 1.30-only code is behind `#ifndef DAYZ_1_29`. Against 1.5.8 (19 files): `CF.ResolvePath` and `CF.FindFileEx`; ModStorage on `MotorbikeScript`; `AdvancedCommunication`, `AnimalBase`, `BuildingBase` and `ZombieBase` create their `CF_ModStorageObject` lazily; a corrupt header (CF too new, or more than 256 mods) is rejected with `Corrupt modstorage header, unsupported CF version ... or too many mods` and `false` from the load; input bindings keep a persistent `UAIDWrapper` (`CF_InputBinding.m_InputID` is gone, use `m_InputWrapper`); `JMAnimRegister.Register(pType)` is deprecated and empty; `CF_String.LastIndexOf` is `[Obsolete]`. Storage written by CF 1.5.9 on 1.30 cannot be loaded by older servers. Hooks and layout: `skills/_shared/persistence/cf-modstorage.md`.
- Start a CF server with `-profiles=<dir>` **and** `-mission=mpmissions/<mission>`. CF resolves paths from both; without `-mission` it falls back to the `serverDZ.cfg` template, which is only the folder name, so `$mission:` and `$storage:` pointed nowhere and the diag build printed a `Virtual Machine Exception`. On the native Linux server the mission path must be relative anyway (`skills/dayz-launch-test/references/linux-native-server.md`). CF needs a writable `$profile:`.
- On diag and experimental builds any `Error()` inside CF ("Could not determine mission folder") shows as a `Virtual Machine Exception`.
- A CF module only receives the events it enables: call `EnableUpdate()`, `EnableMissionStart()`, `EnableClientReady()` and so on in `OnInit()`; an override without its `Enable...` call is never invoked. Networked module variables: at most 256 per module, synced through RPC id 435022, and only the dedicated server sends.
- Removing CF from a server whose storage was written with CF is an observed breakage (`Scripted variables corrupted` while loading that storage). Whether adding CF needs a wipe is a hypothesis that was not isolated (the trees were rebuilt at the same time). Isolate first, before wiping: `skills/dayz-launch-test/references/linux-native-server.md`, "Storage and CF".

**Expansion**:

- DayZ-Expansion-Bundle does not run on its own. Load, in this order: CF (1559212036), **Dabs Framework** (2545327648; not pulled in by the Bundle or CF and not in Expansion's own mod list), **DayZ-Expansion-Licensed** (2116157322), the Bundle (2572331007), then your mod. The Bundle contains every module, so do not add single-module items such as Spawn-Selection. DayZ-Expansion-Animations (2918418331) is needed to drive Expansion cars and helicopters.
- **Without Dabs** the Game module fails with `Undefined function 'Math.Exp'`, followed by hundreds of `Bad type 'JsonFileLoader'` and `'array'` cascade errors: fix the first error, not the cascade.
- Measured on 1.30.164078.38 with CF, Dabs, Licensed and Bundle: 1081 Game-module files, no `SCRIPT (E)`, and a headless client joined into the world. On 1.30 stable the Workshop Dabs build runs unpatched, and no `-newErrorsAreWarnings=1` is needed; the patched Dabs fork and the `-experimental` items were workarounds for the 1.30.164014 pre-release only.
- `#ifdef EXPANSIONMODNAVIGATION` and `#ifdef EXPANSIONMODVEHICLE` detect the modules whatever the mod order (the preload scripts define them).

In this repo, pass the dependency mods to `/dayz-launch-test` and `/dayz-gate --deps` in that load order.

## 9. Read from the sources, not measured

Read in the CF 1.5.8 and 1.5.9 scripts and the vanilla 1.30 scripts; no boot behind them. The CF items are third-party mod behaviour, not vanilla; the last two were checked on `P:\`.

- **CF RPCs.** `GetRPCManager().AddRPC(mod, func, this, SingleplayerExecutionType.Server|Client|Both)` (the default is `Server`; the old misspelling `SingeplayerExecutionType` is still declared). The handler is a method of `this` named exactly like the RPC, and `AddRPC` returns `bool`. `SendRPC(string modName, string funcName, Param params = NULL, bool guaranteed = false, PlayerIdentity sendToIdentity = NULL, Object sendToTarget = NULL)`; a `null` identity from the server broadcasts. `SendRPCs(..., array<ref Param> params, ...)` sends several params at once (no `Both`). There is no `VSendRPC` in CF 1.5.8.
- **CF modules.** `CF_Modules<MyModule>.Get()`; `CF_ModuleGame` (3_Game: RPCs, input bindings, networked variables; `CF_Module` is a typedef of it), `CF_ModuleWorld` (4_World, client lifecycle events), `CF_ModuleCore`. Remember the `Enable...()` calls from section 8.
- **CF notifications.** `NotificationSystem.Create(StringLocaliser title, StringLocaliser text, string icon, int color, float time = 3, PlayerIdentity sendTo = NULL)` (`CreateNotification` is the same); on the server a null `sendTo` means everyone, on the client it shows locally. `CF_TypeConverter.Get(typename)` returns the converter CF's config and XML code uses; there are no `IntToString` or `StringToInt` helpers, use `ToString()` and `ToInt()`.
- **Detecting CF without a dependency.** Its `CfgMods` exports `CF_MODULES`, `CF_MODSTORAGE`, `CF_SURFACES`, `CF_EXPRESSION` and more; test with `#ifdef CF_MODULES`.
- **`EntityAI.SetRequiredSimulation(bool)` and `IsRequiredSimulation()`** (`P:\scripts\3_game\entities\entityai.c:2887-2888`) control the active state of a custom `Transport`; a sleeping body no longer ticks `EOnSimulate` or `EOnPostSimulate`.
- **`InventoryLocationType.TEMP`** (`P:\scripts\3_game\systems\inventory\inventorylocation.c:12`) is a client-side limbo location during an inventory desync. The values come from C++, so use the names, and a `switch` over the type should tolerate `TEMP`.
