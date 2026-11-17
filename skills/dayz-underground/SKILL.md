---
name: dayz-underground
description: "Reference for underground areas in DayZ 1.30: terrain holes (CfgWorlds Holes, tiles[], holes.cfg, SurfaceIsHole), underground triggers (cfgundergroundtriggers.json, UndergroundTrigger, breadcrumbs, EyeAccommodation), the player's underground state (EUndergroundPresence, INPUT_UDT_UNDERGROUND_SYNC, disallowedTypesInUnderground), the in-game trigger editor, the Buldozer underground inputs, the Badlands bunkers (cfgbunkerbroadcast.json) and notes on the .wrp world file. Use when a mod or map needs a hole in the terrain, a bunker, tunnel, trench or cave, or a dark underground zone. Spanish phrases a user may type: agujero o hueco en el terreno, zona subterránea, búnker, túnel, trinchera. Not for base building parts and code locks (dayz-basebuilding) or sandstorm and heat (dayz-environment-hazards)."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ underground (1.30)

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts, so there is no preflight gate. The reference files are in `<skill-dir>\references\`.

It covers the hole in the terrain (new in 1.30), the underground triggers that darken the view and change the sound, the player's "underground" state, and what the Badlands DLC builds on top (bunkers announced by radio, an irrigation tunnel entrance).

Script and config citations were checked on `P:\` (DayZ 1.30). **Nothing in this skill was tested in a running game.** "Verification status" below gives the level of each claim, and "Before designing with holes" says how to raise it.

## What to read

| Question | File |
|---|---|
| What is the evidence for the hole format, the cell size and where holes are stored? What do Terrain Builder 1.30 and the FTT tool add? | `references/terrain-holes-evidence.md` |
| What are all the fields of `cfgundergroundtriggers.json`, how is it loaded and synced, how do I tie a trigger to my bunker? | `references/underground-triggers.md` |
| How is a `.wrp` world file laid out, and how is a road graph pulled out of one? | `references/wrp-format-and-road-graph.md` |

Work that belongs elsewhere:

| Topic | Go to |
|---|---|
| Base building parts, rebuilding, locks | `_shared/persistence/base-building.md` and the `dayz-basebuilding` skill |
| The state file of the bunker broadcast | `_shared/persistence/save-load-contract.md` |
| Trigger volumes in general (`ScriptedEntity`, `TriggerEvents`) | `_shared/physics/scripted-triggers.md` |
| Sandstorm and heat on Nasdara | `dayz-environment-hazards` |
| Starting the game and checking a result | `/dayz-launch-test` |

## The model: three pieces

| Piece | What it is | Where it is defined | Who uses it |
|---|---|---|---|
| Hole | height map cells with no terrain | `CfgWorlds >> <world> >> Holes` (the map's config) | the engine, when it loads the world |
| Geometry | a tunnel or bunker placed below the surface | the `.wrp` (Terrain Builder), Object Spawner, or script | the engine |
| Triggers | boxes that darken the view, change the sound and mark the player "underground" | `cfgundergroundtriggers.json` | the server creates them, the client applies the effects |

A hole only removes terrain; it creates no space. What happens to something that falls through a hole with no geometry under it is not measured, so design as if there were no ground. Without triggers it does not get dark inside.

## Terrain holes

### Format

Of the vanilla maps readable on `P:\`, only Livonia has holes: seven cells in two groups, beside the two entrances of the Dambog bunker (`class Holes`, `P:\DZ\worlds\enoch\world\config.cpp:303`). Chernarus has none, and Sakhal is encrypted.

```cpp
class Holes
{
	class Dambog            // one group is one subclass; the name is free
	{
		tiles[]=
		{
			{118,195},{118,196},{118,197},
			{94,180},{95,180},{94,181},{95,181}
		};
	};
};
```

- Each entry of `tiles[]` is `{x, z}`: cell indexes of the height map, not meters.
- The engine checks the range. The code that reads `tiles` carries the messages `x (%d) out of range <0, %d)` and `y (%d) ...` (strings found in the 1.30 game executable; see the evidence file).
- Each group is a subclass, so a mod could add its own group without overriding the vanilla one. **Not verified:** that a mod's config patch on `CfgWorlds >> ChernarusPlus` opens holes. It is the first thing to measure.

### The unit is a height map cell

In Livonia the grid is 2048 cells of 6.25 m (12,800 m). With that size both groups land on the vanilla underground triggers of Dambog; with 5 m or 10 m neither does (the numbers are in the evidence file):

- `{118, 195 to 197}`: X 737.5 to 743.75, Z 1218.75 to 1237.5, the main entrance.
- `{94 to 95, 180 to 181}`: a 12.5 m square at X 587.5 to 600, Z 1125 to 1137.5, the second entrance.

This is a cross check by fit: the cell size was not read from the header of the `.wrp`, and other maps are not measured. Always compute `cell = floor(coordinate / cell_size)` with the cell size of your own terrain.

### Script API

```c
// P:\scripts\3_game\global\game.c:1203
	//! Returns whether tile at provided world coordinates is a hole.
	proto native bool		SurfaceIsHole(float x, float z);
```

- It is the only new hole API and it only reads. Script cannot open or close a hole at run time.
- No vanilla script calls it: a search of `P:\scripts` finds only the declaration.
- Use it to keep things off cells with no terrain: custom loot, spawn points, custom holograms. Vanilla kit placement does not look at holes.

### Where the data lives

- Both vanilla `.wrp` files on `P:\` are OPRW version 32. In 1.29 both were version 29 (not on `P:\`), and both grew by the same 5 % although only one has `Holes`. That change is a format change; holes live in the world config (cross checked, see the evidence file).

## Authoring workflow

- Buldozer 1.30 has four new inputs: `UABuldLinkCamToTerrain`, `UABuldCopyTileCoord`, `UABuldMarkUnderground` and `UABuldRemoveUnderground` (`P:\bin\constants.xml:282` to `:285`).
- New in Terrain Builder 1.30 (not checked on `P:\`): the Buldozer camera can be unlinked from the terrain height to edit below the surface (key 8 by default), and each object has an "underground" flag that stops a static object below the terrain from being hidden by occlusion when it should be visible.
- That flag belongs to Terrain Builder. There is no script equivalent for objects created by Object Spawner or `CreateObject`, and whether those objects are occluded below the terrain is not measured.
- A stable DayZ Tools from April 2026 has no hole strings and no flag strings (measured on 2026-09-24, not on `P:\`): a later Terrain Builder is needed.
- Third party tool: FTT, a terrain tool released 2026-09-19. Third-party tool behaviour, not checked here:
  - it marks cells and writes `holes.cfg` next to `layers.cfg`, where Terrain Builder and Buldozer are meant to read it;
  - it adds the `#include` to the terrain's `config.cpp`;
  - Buldozer reads the file again on each alt-tab;
  - this matches the `\holes.cfg` string the engine uses while loading a world, but the exact path and the reload behavior are not verified.

## Underground triggers

- File: `$mission:cfgundergroundtriggers.json`; when that is missing, `dz/worlds/<world>/ce/cfgundergroundtriggers.json` (`GetData`, `P:\scripts\3_game\undergroundarealoader.c:105` to `:125`).
- The server creates the boxes (`UndergroundTriggerCarrier`) when the mission starts (`SpawnAllTriggerCarriers`, `P:\scripts\5_mission\mission\missionserver.c:91`) and sends the whole JSON to each client that connects (`SyncDataSend`, `P:\scripts\3_game\undergroundarealoader.c:174` to `:177`). A custom mission JSON works without the client having the file.
- Trigger type (`P:\scripts\4_world\entities\scriptedentities\triggers\undergroundtrigger.c:100` to `:118`): with `Breadcrumbs` it is `TRANSITIONING` (at most 32); without them, `EyeAccommodation == 1.0` gives `OUTER`; any other value gives `INNER`.
- Limit of 4096 triggers per JSON: `m_TriggerIndex` is synchronized in -1 to 4095 (`P:\scripts\4_world\entities\scriptedentities\triggers\undergroundtrigger.c:10`). In 1.29 the range was -1 to 255 (not on `P:\`).
- A trigger can be tied to an object (`CustomSpawn`), through `ParentNetworkId` for a map object or through `Tag` for an object placed by Object Spawner. The vanilla pattern, the schema and a mod recipe are in `references/underground-triggers.md`.
- In-game editor, new in 1.30: `LCTRL+/` (`KC_SLASH`, `P:\scripts\4_world\plugins\pluginbase\pluginkeybinding.c:55`). It exists only in the diag build (`P:\scripts\4_world\plugins\pluginbase\pluginundergroundtriggermanager.c:1` is `#ifdef DIAG_DEVELOPER`) and `EditorToggle` returns at once in multiplayer (`pluginundergroundtriggermanager.c:358` to `:360`).
  - A double click creates a trigger (`Event_OnDoubleClick`, `pluginundergroundtriggermanager.c:305`); boxes and breadcrumbs can be edited.
  - It exports to `$mission:cfgundergroundtriggers.json` (`pluginundergroundtriggermanager.c:821`) and first keeps a copy named `cfgundergroundtriggers.json.backup-<date>` (`pluginundergroundtriggermanager.c:922` to `:923`).

## Underground presence

- `EUndergroundPresence` has `NONE`, `OUTER`, `TRANSITIONING` and `FULL` (`P:\scripts\4_world\classes\undergroundhandlerclient.c:1` to `:7`). The client works it out from the trigger it is in (`SetUndergroundPresence`, `undergroundhandlerclient.c:464` to `:476`).
- In 1.30 the client sends it to the server: `SetUnderground` writes `INPUT_UDT_UNDERGROUND_SYNC` (`P:\scripts\4_world\entities\manbase\playerbase.c:2853` to `:2865`), and the server takes it in `OnInputUserDataProcess` with only a range check (`P:\scripts\4_world\entities\manbase\playerbase.c:6557` to `:6564`). In 1.29 the value existed only on the client (not on `P:\`).
- Consequence: the server now knows the presence. Before, a server side check that read it saw `NONE`.
- One such check is `CanPlaceItem` (`P:\scripts\4_world\entities\manbase\playerbase.c:2834` to `:2846`, called from `P:\scripts\4_world\classes\hologram.c:438`): inside a trigger it refuses the types in `disallowedTypesInUnderground`.
  - The defaults are `FenceKit`, `TerritoryFlagKit` and `WatchtowerKit` (`P:\scripts\3_game\cfggameplaydatajson.c:229` to `:232`).
  - The setting is in `cfggameplay.json` under `BaseBuildingData` > `HologramData` (`GetDisallowedTypesInUnderground`, `P:\scripts\3_game\cfggameplayhandler.c:372` to `:374`).
- The client decides the value; the server does not work it out again. Do not use it alone for anything a cheating client should not control.

## Badlands in the 1.30 scripts

- **Bunkers announced by radio.**
  - The classes are `Land_Bunker_Basement_Civilian`, `Land_Bunker_Basement_Storage`, `Land_Bunker_Basement_Medical` and the three `Land_Bunker_Shelter_*` ones (`P:\scripts\4_world\entities\building\bunker.c:331` to `:336`), each with a code lock.
  - The radio broadcasts coordinates and the code in Morse (not on `P:\`; the broadcast was not heard in game).
  - It is configured in `cfgbunkerbroadcast.json`, in `$mission:` or in `dz/worlds/<world>/ce/` (`m_ConfigFilePath`, `P:\scripts\3_game\cfgbunkerbroadcasthandler.c:5`, `:26` to `:27`), plus `bunkerBroadcastEnabled` in `cfggameplay.json` (`P:\scripts\3_game\cfggameplaydatajson.c:193`).
- **Irrigation tunnel.** `Land_IrrigationTunnel_Entrance_01` sits in the `rebuildable` script folder (`P:\scripts\4_world\entities\building\rebuildable\irrigationtunnel_entrance.c:1`): the entrance can be rebuilt, and its debug spawn fills it with sticks and rope.
- Not on `P:\`: the first 1.30 build shipped only Nasdara's scripts. Stable 1.30.164200 installs `nasdara\addons\` with 24 PBOs (structures, Central Economy, navmesh, world data) and the world in the encrypted `worlds_nasdara.ebo`; what they hold underground was not read.
- Announced for Badlands on 2026-09-22, not checked on `P:\`: the Badlands underground facilities use the terrain holes system, which will be available for other maps and for mods.

## Verification status

| Claim | Level |
|---|---|
| The `Holes` and `tiles[]` format, `SurfaceIsHole`, presence synchronization, the trigger limit, the JSON schema | read in source on `P:\` |
| One entry of `tiles[]` is a height map cell; 6.25 m in Livonia | cross checked (fits the triggers) |
| Holes live in the config, not in the `.wrp` | cross checked (the `.wrp` grows the same with and without holes) |
| How a hole renders and collides, what happens when something falls through, AI and navmesh | not verified |
| A config only mod opens holes in a vanilla map | not verified (a hypothesis) |
| `holes.cfg` next to `layers.cfg`, and the reload on alt-tab | not verified (third-party tool behaviour, FTT) |
| The effect of `ECE_OBJECT_SPAWNER` on an object under a hole | not verified |

## Before designing with holes

Each test moves one row of "Verification status". Together they fit in one diag session (`/dayz-launch-test`):

1. **Vanilla Livonia.** `g_Game.SurfaceIsHole(740, 1225)` must return `true` (cell `{118,196}`) and `g_Game.SurfaceIsHole(1000, 1000)` `false`. Take one screenshot from outside the hole and one from inside.
2. **Config only mod.** Add a group of your own in `CfgWorlds >> ChernarusPlus >> Holes` and repeat the check on its cell.
3. **Mod geometry.** Place an object with Object Spawner under that hole and check that it is visible from inside and outside, and that it collides.
4. **Falling.** Drop an object, and walk a character, into a hole with no geometry.

## What this skill could not verify

- Any behavior in game: rendering, collision, occlusion, falling, AI and navmesh.
- The cell size of any map other than Livonia, and Livonia's as read from the header of the `.wrp`.
- Sakhal: its world is in an encrypted `.ebo` and could not be read.
- Exactly where the engine looks for `holes.cfg`, and whether a config only mod opens holes.
- What the engine does with `ECE_OBJECT_SPAWNER`.

## On Linux

Everything above is the Windows workflow. The Proton setup and its limits are in the shared Linux notes (`_shared/linux-proton.md`). For this skill only two things change: Terrain Builder was not started under Proton, so treat any `.wrp` step as Windows only until it is measured; and string searches in the game executable work natively with `strings` and `strings -el` (UTF-16).

## Building and testing the mod

When the work has to end in a mod that builds, loads and ships, use this repo's own chain: `/dayz-lint`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-gate`.
