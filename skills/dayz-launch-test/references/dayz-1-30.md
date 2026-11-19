# DayZ 1.30 launch changes

What DayZ 1.30 changes for starting and driving a test session: unpacked `-mod` folders, two new launch flags, headless clients, pending actions in single player and Script Console tabs. The rules in `README.md` ("Rules that hold on every route") still apply: absolute `-mod` paths on Windows, the `-mod=` line as the measure of a run, and the file patching caveats.

Script lines cite the vanilla 1.30 scripts on `P:\scripts\`. Quoted lines come from the DayZ 1.30 Experimental modding changelog; how the new flags behave was read there, not measured with a 1.30 DayZ Tools binary. Nothing from 1.29 is unpacked on `P:\`, so a 1.29 comparison is reported, not checked there.

Related files: `diag-direct-launch.md` (starting the 1.30 DayZDiag by hand), `server-load-and-dummy-bots.md` (load tests with server side bots), `vehicle-in-game-facts.md` (cars in a scripted test on 1.30) and `dayz-1-30-server-measured.md` (what a running 1.30 server showed).

## An unpacked `-mod` folder

Until 1.29 the loop was: repack the PBO, deploy it where the engine reads mods, launch DayZDiag. The 1.30 changelog says:

```text
Changed: Mods now have their own named filesystem
Changed: Improved unpacked mod workflow; -mod can now point to a physical folder
Changed: RV configs can now be read when loaded as an unpacked mod
```

What a dedicated 1.30 server actually does with one, measured in game:

- The folder mounts as a relative directory: the RPT logs `Adding relative directory ...` where a PBO logs `Adding package ... (pbo count: N)`.
- With a `CfgMods` block it injects the mod's define into the script modules and loads its scripts.
- It does not merge the folder's `config.cpp` into the runtime config tree: `ConfigIsExisting("CfgPatches <mod>")` stays false.
- So world configs need a packed PBO. Unpacked, terrain `Holes` in `CfgWorlds` are not read: `SurfaceIsHole` stays false and the RPT logs `No entry 'config.bin/CfgWorlds/<world>.Holes'`. The same content packed as a PBO measured true, and the PBO may carry `config.cpp` as text with no binarize.

Use an unpacked folder for script iteration, still with an absolute path; a bare `@Name` still mounts nothing with no error. `.p3d` and `.paa` files still follow the rule that file patching does not reload binaries, and a test of what you ship still packs.

## New launch flags

From the 1.30 changelog:

```text
Added: '-resolveFilePatchingUsingEnfusion=0/1' for file patching to prioritize looking through named enfusion filesystems before checking launched directory (requires -filepatching, always enabled in Workbench)
Added: '-cacheP3D=0/1' command line launch option, creates .p3dcache files next to .p3d files to allow for quicker subsequent launches of the Game/Buldozer when working with unbinarized assets
```

When iterating on unpacked or MLOD assets, add them to the diag command line, for example `-filePatching -resolveFilePatchingUsingEnfusion=1 -cacheP3D=1`. Not tested in game. The `.p3dcache` files beside the models are local caches; never commit them.

## Headless clients

1.30 adds `CGame.IsHeadless()` and `IsHeadlessOrDedicatedServer()` (`P:\scripts\3_game\global\game.c:1130` and `:1136`; reported absent from the 1.29 `Game.c`). The script side is in `_shared/enscript/depth/dayz-1-30-enforce-script.md`.

- A headless client has no window to capture, so a capture run still needs a rendered client; never treat a headless client as the capture peer.
- Script that skips visual effects should test `IsHeadlessOrDedicatedServer()`, so headless clients behave like the dedicated server.
- On 1.30 Experimental the headless client (`-headlessMode=1`) crashes before loading `World`, so it cannot carry a load test there. Server side dummy players do the job instead (`server-load-and-dummy-bots.md`).

## Pending actions in single player

`PerformActionStart` moved from `:762` in 1.29 to `:804` in 1.30, and single player no longer overwrites an action that is already pending or running. From `P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804` to `:828`:

```c
void PerformActionStart(ActionBase action, ActionTarget target, ItemBase item, Param extra_data = NULL)
{
	if (!g_Game.IsMultiplayer())
	{
		if (!m_PendingActionData && !m_CurrentActionData)
		{
			m_PendingActionData = new ActionData;

			if (!action.SetupAction(m_Player, target, item, m_PendingActionData, extra_data))
				m_PendingActionData = null;
		}
	}
	else
	{
		ActionStart(action, target, item, extra_data);
	}
}

override int GetActionState()
{
	if (m_PendingActionData)
		return UA_AM_INIT;

	return super.GetActionState();
}
```

`UA_AM_INIT = 14` was inserted, so the later `UA_AM_*` values moved (`P:\scripts\3_game\constants.c:506` to `:511`):

| Constant | Value |
|---|---|
| `UA_INITIALIZE` | 12 |
| `UA_CHECK_CON` | 13 |
| `UA_AM_INIT` | 14 |
| `UA_AM_PENDING` | 15 |
| `UA_AM_ACCEPTED` | 16 |
| `UA_AM_REJECTED` | 17 |

A test that injects a second `PerformActionStart` in single player before the first has finished does nothing, with no error (not tested in game). Wait until `GetActionState()` is no longer `UA_AM_INIT`, and use the constant, never the number 14. Multiplayer is unchanged: `PerformActionStart` still calls `ActionStart` directly (`:816` to `:819`).

A scripted action start in single player does nothing the same way while an action is pending or running. Continuous actions need held input a script does not give (`actions-doors-and-inventory.md`). For an instant action, if a second start does nothing, wait for `GetActionState()` to leave `UA_AM_INIT`.

## Script Console tabs

Until 1.29 adding a Script Console tab meant replacing `ScriptConsole.c`. In 1.30 tabs register through `ScriptConsoleTabRegistry.Register` (`P:\scripts\5_mission\gui\scriptconsole.c:33` to `:43`):

```c
class ScriptConsoleTabRegistry
{
	protected static ref array<ref ScriptConsoleTabRegistryEntry> s_Entries;

	static void Register(int id, string displayName, string widgetName, typename tabClass)
	{
		if (!s_Entries)
			s_Entries = new array<ref ScriptConsoleTabRegistryEntry>();

		s_Entries.Insert(new ScriptConsoleTabRegistryEntry(id, displayName, widgetName, tabClass));
	}
```

- Vanilla `InitializeRegistry` (`scriptconsole.c:50` to `:66`) first clears the array (`:52` and `:53`), then registers the tabs from GENERAL to WEATHER.
- `ScriptConsole.BuildContextMenu()` (`:279`) calls `InitializeRegistry()` and then walks `GetAll()` (`:293` to `:296`). `Init()` calls `BuildContextMenu()` at `:227`, and on console builds `OnInputDeviceChanged` calls it again at `:249`.

For a mod's debug tab, mod the registry initializer or register from a mission module after vanilla has registered, with a new `ScriptConsoleTabID` below `COUNT`; never replace the whole `ScriptConsole.c`. Because `InitializeRegistry` clears the array, a `Register` call from `4_World` that runs before it is lost; registering inside a `modded` `InitializeRegistry` after `super` avoids that. Neither order is tested in game. Console tabs are diag UI for a person; a scripted test still needs its own spawning and raycasts.

## Navmesh

Custom terrains need their `.nm` navmesh regenerated for 1.30; the changelog says there is no backwards compatibility. Workbench 1.30 was not available to test, so the Tools side rests on the changelog.
