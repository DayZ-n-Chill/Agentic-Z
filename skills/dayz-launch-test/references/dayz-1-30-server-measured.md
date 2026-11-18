# DayZ 1.30 on a running server

What booting test mods on a 1.30 dedicated server shows that a source file cannot: a function that silently does the wrong thing, a path rule, a crash, the real load order, and the Community Framework and Expansion facts a 1.30 server needs. The `dayz-1-30-*.md` files of the packs cover what reading the vanilla scripts shows.

Measured on the native Linux `DayZServer`, and measured again in full on DayZ 1.30 stable. Where an entry names a build it was first measured there: 1.30 Experimental unless it says the 1.30 release, the first 1.30 patch or the second 1.30 patch (`_shared/enscript/references/game_builds.md` maps these names to builds). Windows servers were not tested; where a Windows rule differs, `windows-launch-cycle.md` or `windows-build-and-mount.md` says so. The setup to repeat any of it is `linux-native-server.md`.

Measured behaviour cannot be read from a file and is not checked on `P:\`. Every statement about a declaration was opened on `P:\` and is cited. This file was checked against a 1.30 build from before the first 1.30 patch (game storage version 144). `P:\` now holds a patched 1.30 build (`_shared/enscript/references/game_builds.md`), so the "before" side of "The first 1.30 patch" is no longer on `P:\` and its citations name the file without `P:\`.

## The version define

- The engine defines only the current version. Vanilla documents the define as "filled in with the current Major and Minor version" (`DAYZ_X_XX`, `P:\scripts\1_core\defines.c:12` to `:14`). The `defines:` of a 1.30 server's `Module:` lines hold `DAYZ_1_30`; 1.30 does not define `DAYZ_1_29`, as 1.29 did not define `DAYZ_1_28`.
- So write plain current code with no version `#ifdef`: `#ifdef DAYZ_1_30` would drop the code again on the next release. Only when the user asks for a mod that must still load on an older server, put the old code under that version's define and the current code in `#else`, so the current code stays the default.
- `string v; g_Game.GetVersion(v);` gives the full build, a dotted string of four numbers that starts with `1.30.` on 1.30 (`GetVersion`, `P:\scripts\3_game\global\game.c:941`). Use it for logging; it cannot select code that would not compile, only a define can.
- A mod's own `defines[] = {"MYMOD"};` in `CfgMods` works with `#ifdef MYMOD`. A loaded mod's name is a define too (`#ifdef AutoTest`; `linux-headless-client.md`).
- `BUILD_EXPERIMENTAL` and `DIAG_DEVELOPER` exist only on diag and Experimental builds; never use them to mean "1.30".

## `FindFile` and file paths

On the first 1.30 patch and later, `FindFile` resolves `$profile:`, `$mission:`, `$saves:` and `$storage:`, and backslash patterns work. The script declarations did not change from 1.29: `FindFile`, `FindNextFile` and `CloseFindFile` (`P:\scripts\1_core\proto\ensystem.c:520` to `:522`) and the `FindFileFlags` enum (`ensystem.c:513` to `:518`), so the fix was in the native binding and no signature changes. Measured with `-profiles=profiles` inside the server folder and with an absolute `-profiles=/var/tmp/<dir>` outside it, with the same results:

| Pattern | Result |
|---|---|
| `$profile:*`, `$profile:fftest/*.json` (also with `\`), with `FindFileFlags.DIRECTORIES` | the profile folder's entries; files and the `sub` folder |
| `$mission:fftest/*.json`, `$mission:*` | `m.json`; the mission's `cfg*.xml` |
| `$saves:*` | `DayZ.cfg` |
| `$storage:*` | `data`, `backup`, `players.db`, `spawnpoints.bin` once the mission runs; nothing in `main()` or on a first boot |
| relative `profiles/fftest/*.json` (either slash) | found |
| `FindFile(..., -1)` | same as `ALL` |
| `CF.FindFileEx` (Workshop Community Framework 1.5.9) | passes through to `FindFile` |

On 1.30 Experimental and the 1.30 release, `FindFile` ignored the placeholders and listed the server's working folder instead (`FindFile("$profile:*")` returned `DayZServer`, `addons`, `keys`, ...), and backslash paths found nothing. The reported cause, not checked on `P:\`: the binding passed the `FindFileFlags` value where the reworked native expects a file system index. The workarounds were `CF.FindFileEx` (CF 1.5.9 or newer) or a port of it for mods without CF; both cut an absolute `-profiles=` to its last part, which is where the announced rule "the profile folder must be inside the server folder" came from. Every other file function worked with the placeholders on those builds.

Removing the workarounds on the first 1.30 patch or later:

- `CF.FindFileEx(...)` becomes `FindFile(...)` with the same arguments. Leaving it only costs a test file `$profile:cf_findfile_dz130_test`, so this is cleanup, not a fix; a mod that needed CF only for it can drop CF.
- A copied `YOURMOD_FindFilePath(p)` wrapper becomes plain `p`; delete the helper and the leftover `$profile:yourmod_findfile_dz130_test` and `cf_findfile_dz130_test` files. (The helper is not shipped here; it only served earlier 1.30 builds.)
- The profile folder no longer has to sit inside the server folder; an absolute `-profiles=` works with plain `FindFile` and with `CF.FindFileEx`. A mission folder or `-storage=` outside it was not tested.
- Keep the loop shape: the first match arrives in `fileName`, then `FindNextFile`, then `CloseFindFile`. Results are bare names, so open each by its placeholder path (`"$profile:MyMod/" + fileName`). Enforce Script has no `do { } while` (`Can't find variable 'do'`), so loop with `bool found = fileName != ""; while (found) { ...; found = FindNextFile(h, fileName, attr); }`.
- On an unknown server check `g_Game.GetVersion(v)` first; there is no define for the point release.

Still true on the first 1.30 patch:

- `$storage:` is not available while the mission starts. `FileExist`, `MakeDirectory` and `OpenFile` on it returned false in the `MissionServer` constructor, in `OnInit()` and on both sides of `OnMissionStart()`, and true from the first `MissionServer.OnUpdate()` or `CallLater` tick, 7 to 10 seconds later. On the first boot of an instance (no `storage_1` yet) it stayed unavailable for the whole 60 second run, so fall back to `<mission folder>/storage_<instanceId>/`. The 1.30 build ignored a relative `-storage=<dir>`; do not combine `-storage` with `$storage:`.
- `g_Game.GetMissionFolderPath()` returns `""` on 1.30 Linux servers, while `GetMissionPath()` is `mpmissions/dayzOffline.chernarusplus/mission.c`. The cause shows in vanilla: `SetMissionPath` looks only for `"\\"` when it cuts the folder out of the path (`P:\scripts\3_game\dayzgame.c:1207` to `:1221`), and `GetMissionFolderPath` returns what that left (`dayzgame.c:1228` to `:1231`). Derive the folder from `GetMissionPath()`.
- Write forward slashes in every path you build (`dir + "/" + name`); they work everywhere.

## Script module paths need forward slashes

With `files[] = {"MyMod\scripts\4_World"};` a 1.30 Experimental server loads the mod's config and shows its `CfgMods` defines, but compiles none of its scripts and prints no error: the World module count stays at vanilla (2321). `files[] = {"MyMod/scripts/4_World"};` fixes it; the case of the folder name made no difference. A Workshop mod had all five PBOs written with backslashes. Check every `worldScriptModule`, `gameScriptModule` and `missionScriptModule`, also in a debinarized `config.bin`. Not tested again on the first 1.30 patch, nor on Windows.

In this repo `/dayz-new-mod` writes these paths with forward slashes, and `/dayz-lint` checks that each listed folder exists (`script-module-path`). Lint does not yet flag a backslash in `files[]`.

## Compile failures

- On the 1.30 pre-release a script compile failure was followed by a segfault of the server, right after `Can't compile "World" script module!`. A crash at boot is often a compile error, so read `script_*.log` first.
- Override signatures confirmed by a failing boot ("marked as override, but there is no function with this name"). Adding a parameter, even with a default, changes the signature:
  - `EntityAI.ProcessVariables()` and the `ItemBase` override are now `ProcessVariables(float elapsedTime)` (`P:\scripts\3_game\entities\entityai.c:3913`; the `ItemBase` override at `P:\scripts\4_world\entities\itembase.c:4663`).
  - `Construction.SetParent(BaseBuildingBase)` is now `SetParent(EntityAI parent)` (`P:\scripts\4_world\classes\basebuilding\construction.c:44`). `Construction` now extends `ConstructionBase` (`construction.c:2`), which extends `ConstructionBasic` (`P:\scripts\4_world\classes\constructionbase.c:30`).
  - `CarScript.ToggleHeadlights()` is gone (no declaration under `P:\scripts\`); use `LightToggle()` on `Transport` (`P:\scripts\3_game\vehicles\transport.c:239`).
- `P:\scripts\2_gamelib\settings.c` holds one line, `// removed due to mod conflicts` (`:1`), so the `Settings`, `GameSettings` and `SettingsMenu` classes are not there to call.
- A `modded class` must live in the same script module as the class it changes. `Transport` is a `3_Game` class (`P:\scripts\3_game\vehicles\transport.c:66` and `:68`; it extends `Pawn` when `FEATURE_NETWORK_RECONCILIATION` is defined and `EntityAI` otherwise), so `modded class Transport` in `4_World` fails with `Unknown type 'Transport'`; hook `CarScript`, `BoatScript` or `MotorbikeScript` instead.

## Silent breakers

- `OnCEUpdate()` is never called on 1.30. It is still declared with `[Obsolete("1.30: Use OnCEIterate(float currentTime, float elapsedTime) instead")]` and no body (`P:\scripts\3_game\entities\entityai.c:4924` and `:4925`), so an override compiles with a warning and never runs. Over 2 minutes with 20 spawned items: `OnCEUpdate` 0 calls, `OnCEIterate` 446,000. Port to `OnCEIterate(float currentTime, float elapsedTime)` (`entityai.c:3904`) and call `super` first, as its comment asks.
- Obsolete members compile with `SCRIPT (W): '...' is obsolete`.
- `ERPCs` values moved. `RPC_SYMPTOM_PARAM_SYNC` (`P:\scripts\3_game\enums\erpcs.c:23`) and others were inserted near the top, so every vanilla id after `RPC_PLAYER_SYMPTOM_OFF` (`erpcs.c:22`) changed. Mods that send or store vanilla RPC ids as raw integers, or count from one, break. Use the enum names and keep mod ids in a range of your own (`_shared/enscript/references/erpc_defines.md`).
- `GAME_STORAGE_VERSION` went from 142 to 144 (`P:\scripts\3_game\global\game.c:5` holds 144). Back up `storage_1` before the first 1.30 boot; older servers cannot read it back (the stream is in `_shared/persistence/save-load-contract.md` and `_shared/persistence/dayz-1-30-persistence.md`).

## The first 1.30 patch

From comparing the API index of the two builds; only the Workbench row was run on a server. The "before" column cites the lines of the earlier build, which `P:\` held until it was extracted again from a patched build. The "now" column cites the patched build now on `P:\`.

Two changes sometimes listed for the first 1.30 patch are not real: `FilterObstructedObjectsByGrouping` is in both builds (`P:\scripts\4_world\static\miscgameplayfunctions.c:1444`), and `IsLockTargetOnUse` was already in the 1.30 release (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:102`).

| Before (the earlier build) | Now (the first 1.30 patch) | Effect |
|---|---|---|
| `int GetSupportProvided(int category)` and `int GetSupportRequirement(int category)` on `ConstructionPart` (`scripts\4_world\classes\basebuilding\constructionpart.c:371` to `:376`) | `bool GetSupportProvided(int category, out int providedStrength)` and `bool GetSupportRequirement(int category, out int requiredStrength)` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:365` and `:370`) | The same change on `ConstructionPartStaticsSupportData` (before: `scripts\4_world\classes\rebuilding\constructionstatics.c:71` to `:79`; now `P:\scripts\4_world\classes\rebuilding\constructionstatics.c:80` and `:89`) and on `ConstructionPartTypeData.GetPartTypeSupportProvided` and `GetPartTypeSupportRequirement` (now `P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:625` and `:630`). Callers and overrides break. |
| `ConstructionPart.TryHandleUtilityParts(EntityAI parent)` (`constructionpart.c:485`) | `TryQueueUtilityPartsUpdate(ConstructionBase con)` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:485`, overridden at `:879`) | Utility parts update through a queue: `QueueUpdateUtilityParts` adds `UpdateUtilityParts` to the post update queue once (`P:\scripts\4_world\classes\constructionbase.c:683` to `:693`). |
| `ConstructionPartTypeData.m_UtilityAutomaticBuild` and `GetPartTypeUtilityAutobuildPartsList()` (`scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:40` and `:674`) | removed | `TriggersUtilityPartsUpdate()` instead (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:481`). |
| (none) | `InvertSupportBehavior()` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:381`), `ConstructionPartRebuildInvertedSupport` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionpartrebuildinvertedsupport.c:7`), `ConstructionBase.IgnoreHouseCollisions()` (`P:\scripts\4_world\classes\constructionbase.c:1585`) | New; none of the three names existed in the earlier build. |
| `CarScript.IsMoving()` (`scripts\4_world\entities\vehicles\carscript.c:2221`) | declared on `Transport` (`P:\scripts\3_game\vehicles\transport.c:819`, overridden by `CarScript` at `P:\scripts\4_world\entities\vehicles\carscript.c:2221`); new `Transport.HasCrew()` (`transport.c:175`) | Calls keep working. |
| `NavmeshTest` and `NavmeshTest_A` to `_F` (`scripts\4_world\entities\navmeshtest\navmeshtest.c:2`) | `Land_NavmeshTest*` (`P:\scripts\4_world\entities\navmeshtest\navmeshtest.c:2` and `:118`) | Renamed. |
| `Workbench`, `WorldEditor`, `WBModuleDef` and the rest callable from game scripts: the file opens with the `WBModuleDef` typedefs and `class Workbench` with no `#ifdef` around them (`scripts\1_core\workbenchapi.c:1` to `:6`) | the Workbench API classes sit inside `#ifdef WORKBENCH` (`P:\scripts\1_core\workbenchapi\workbench.c:1` to `:63`), except `WorkbenchPlugin` (`P:\scripts\1_core\workbenchapi\plugins\workbenchplugin.c:2`) and `ResourceName` (`P:\scripts\1_core\workbenchapi.c:1`); `ResourceBrowser` and the Workbench `WorldEditor` classes are gone (`WorldEditorIngame` in `P:\scripts\2_gamelib\menumanager.c:87` is a game menu, not the Workbench API) | Measured on one run: Dabs Framework 1.51 (`SampleMVC.c:33`, `Workbench.Dialog(...)`) fails with `Can't find variable 'Workbench'`, then `Can't compile "Mission" script module!` and a crash at boot. Wrap such calls in `#ifdef WORKBENCH`. An API index that ignores `#ifdef` still lists the classes. |

The guard itself is mapped in `_shared/enscript/references/workbench_api.md`, "The guard".

## Mod load order is not the `-mod` order

`modded class` blocks from several addons stack in addon compile order, and that order follows `requiredAddons` resolution, not the `-mod=` or `-servermod=` string. A server mod whose `requiredAddons` names `DayZExpansion_Vehicles_Scripts` compiled right after that addon, at a place unrelated to its position in the `-servermod` string, and a `-servermod` addon does not compile after every `-mod` addon. No position in the chain can be relied on, so never build a fix on being first or "outermost". Make it independent of order:

- Hook an event that provably runs after the behaviour you counter: `EEInit()` runs after the constructor chain, so turning damage back on there beats a constructor time `SetAllowDamage(false)` from any position.
- Pick targets by data (a class name prefix, config flags), not by which mod you assume ran first.

## Community Framework and Expansion

Third-party mod behaviour, not vanilla: Community Framework (CF), Community Online Tools (COT), Dabs Framework and DayZ Expansion. Our checked notes on CF and Dabs are `_shared/enscript/integrations/community_framework.md` and `dabs_framework.md` beside it.

Community Framework:

- Use the regular Workshop CF 1.5.9 or newer (1559212036). CF-Test (1625463737) is obsolete: the 1.5.9 PBOs are byte identical to its last build. Load only one of them, since both declare `JM_CF_Scripts`. The current COT (1564026768) needs no COT-Test either. CF's `config.cpp` still says `version = "1.5.8"`, so never test that string.
- CF 1.5.9 compiles unchanged on 1.30 Experimental with no `SCRIPT (E)` of its own; its 1.30 only code sits behind `#ifndef DAYZ_1_29`. Against 1.5.8 (19 files): `CF.ResolvePath` and `CF.FindFileEx`; ModStorage on `MotorbikeScript`; `AdvancedCommunication`, `AnimalBase`, `BuildingBase` and `ZombieBase` create their `CF_ModStorageObject` lazily; a corrupt header (CF too new, or more than 256 mods) is refused with `Corrupt modstorage header, unsupported CF version ... or too many mods` and `false` from the load; input bindings keep a persistent `UAIDWrapper` (`CF_InputBinding.m_InputID` is gone, use `m_InputWrapper`); `JMAnimRegister.Register(pType)` is deprecated and empty; `CF_String.LastIndexOf` is `[Obsolete]`. Storage written by CF 1.5.9 on 1.30 cannot be loaded by older servers. Hooks and layout: `_shared/persistence/cf-modstorage.md`.
- Start a CF server with `-profiles=<dir>` and `-mission=mpmissions/<mission>`. CF resolves paths from both; without `-mission` it falls back to the `serverDZ.cfg` template, which is only the folder name, so `$mission:` and `$storage:` pointed nowhere and the diag build printed a `Virtual Machine Exception`. On the native Linux server the mission path must be relative anyway (`linux-native-server.md`). CF needs a writable `$profile:`.
- On diag and Experimental builds any `Error()` inside CF ("Could not determine mission folder") shows as a `Virtual Machine Exception`.
- A CF module only receives the events it enables: call `EnableUpdate()`, `EnableMissionStart()`, `EnableClientReady()` and the rest in `OnInit()`; an override without its `Enable...` call never runs. Networked module variables: at most 256 per module, synced through RPC id 435022, and only the dedicated server sends.
- Removing CF from a server whose storage was written with CF breaks the load (`Scripted variables corrupted`). Whether adding CF needs a wipe was not isolated on Linux (the trees were rebuilt at the same time), so isolate before wiping: `linux-native-server.md`, "Storage and Community Framework".

Expansion:

- DayZ-Expansion-Bundle does not run alone. Load, in this order: CF (1559212036), Dabs Framework (2545327648; not pulled in by the Bundle or CF and not in Expansion's own mod list), DayZ-Expansion-Licensed (2116157322), the Bundle (2572331007), then your mod. The Bundle holds every module, so do not add single module items such as Spawn-Selection. DayZ-Expansion-Animations (2918418331) is needed to drive Expansion cars and helicopters.
- Without Dabs the Game module fails with `Undefined function 'Math.Exp'`, followed by hundreds of `Bad type 'JsonFileLoader'` and `'array'` errors in a cascade: fix the first error, not the cascade.
- On the 1.30 release with CF, Dabs, Licensed and Bundle: 1081 Game module files, no `SCRIPT (E)`, and a headless client joined into the world. On 1.30 stable the Workshop Dabs build runs unpatched and no `-newErrorsAreWarnings=1` is needed; a patched Dabs and the `-experimental` items were needed only on 1.30 Experimental.
- `#ifdef EXPANSIONMODNAVIGATION` and `#ifdef EXPANSIONMODVEHICLE` detect the modules whatever the mod order; the preload scripts define them.

In this repo, pass the dependency mods to `/dayz-launch-test` and `/dayz-gate --deps` in that load order.

## Read in the sources, not measured

Read in the CF 1.5.8 and 1.5.9 scripts and the vanilla 1.30 scripts, with no boot behind them. The CF items are third-party behaviour; the last two are vanilla and cited.

- CF RPCs: `GetRPCManager().AddRPC(mod, func, this, SingleplayerExecutionType.Server|Client|Both)` (the default is `Server`; the old misspelling `SingeplayerExecutionType` is still declared). The handler is a method of `this` named exactly like the RPC, and `AddRPC` returns `bool`. `SendRPC(string modName, string funcName, Param params = NULL, bool guaranteed = false, PlayerIdentity sendToIdentity = NULL, Object sendToTarget = NULL)`; a `null` identity from the server broadcasts. `SendRPCs(..., array<ref Param> params, ...)` sends several params at once (no `Both`). There is no `VSendRPC` in CF 1.5.8.
- CF modules: `CF_Modules<MyModule>.Get()`; `CF_ModuleGame` (3_Game: RPCs, input bindings, networked variables; `CF_Module` is a typedef of it), `CF_ModuleWorld` (4_World, client lifecycle events), `CF_ModuleCore`. Remember the `Enable...()` calls above.
- CF notifications: `NotificationSystem.Create(StringLocaliser title, StringLocaliser text, string icon, int color, float time = 3, PlayerIdentity sendTo = NULL)` (`CreateNotification` is the same); on the server a null `sendTo` means everyone, on the client it shows locally. `CF_TypeConverter.Get(typename)` returns the converter CF's config and XML code uses; there are no `IntToString` or `StringToInt` helpers, so use `ToString()` and `ToInt()`.
- Detecting CF without depending on it: its `CfgMods` exports `CF_MODULES`, `CF_MODSTORAGE`, `CF_SURFACES`, `CF_EXPRESSION` and more; test with `#ifdef CF_MODULES`.
- `EntityAI.SetRequiredSimulation(bool)` and `IsRequiredSimulation()` (`P:\scripts\3_game\entities\entityai.c:2887` and `:2888`) control the active state of a custom `Transport`; a sleeping body no longer ticks `EOnSimulate` or `EOnPostSimulate` (the tick is native, so that part is not checked on `P:\`).
- `InventoryLocationType.TEMP` (`P:\scripts\3_game\systems\inventory\inventorylocation.c:12`) is a client side holding location during an inventory desync. The values come from C++ ("DO NOT EDIT! enum values are overwritten from c++", `inventorylocation.c:1`), so use the names, and a `switch` over the type should accept `TEMP`.
