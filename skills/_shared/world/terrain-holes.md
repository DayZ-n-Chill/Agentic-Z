# Terrain holes (DayZ 1.30)

How a 1.30 world removes terrain over a set of height map cells, the one script call that reads it, how a terrain author marks holes, and what is still unproven. Config and script citations are checked on `P:\` (DayZ 1.30). **Nothing here was tested in a running game.** How the format, the cell size and the storage were worked out is in `terrain-holes-evidence.md`.

## The model: three pieces

| Piece | What it is | Where it is defined | Who uses it |
|---|---|---|---|
| Hole | height map cells with no terrain | `CfgWorlds >> <world> >> Holes` (the map's config) | the engine, when it loads the world |
| Geometry | a tunnel or bunker placed below the surface | the `.wrp` (Terrain Builder), Object Spawner, or script | the engine |
| Triggers | boxes that darken the view, change the sound and mark the player "underground" | `cfgundergroundtriggers.json` | the server creates them, the client applies the effects (`underground-triggers.md`) |

A hole only removes terrain; it creates no space. What happens to something that falls through a hole with no geometry under it is not measured, so design as if there were no ground. Without triggers it does not get dark inside.

## Format

Of the vanilla maps readable on `P:\`, only Livonia has holes: seven cells in two groups, beside the two entrances of the Dambog bunker (`class Holes`, `P:\DZ\worlds\enoch\world\config.cpp:303`). Chernarus has none (`P:\DZ\worlds\chernarusplus\world\config.cpp` has neither `Holes` nor `tiles`), and the Sakhal world is in an encrypted `.ebo`.

```cpp
// P:\DZ\worlds\enoch\world\config.cpp:303 (inside CfgWorlds > Enoch)
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
- The engine checks the range. The code that reads `tiles` carries the messages `x (%d) out of range <0, %d)` and `y (%d) ...` (strings in the 1.30 game executable; see `terrain-holes-evidence.md`).
- Each group is a subclass, so a mod could add its own group without overriding the vanilla one. **Not verified:** that a mod's config patch on `CfgWorlds >> ChernarusPlus` opens holes. It is the first thing to measure.

## The unit is a height map cell

In Livonia the grid is 2048 cells of 6.25 m (12,800 m). With that size both groups land on the vanilla underground triggers of Dambog:

- `{118, 195 to 197}`: X 737.5 to 743.75, Z 1218.75 to 1237.5, the main entrance.
- `{94 to 95, 180 to 181}`: a 12.5 m square at X 587.5 to 600, Z 1125 to 1137.5, the second entrance.

This is a cross check by fit, not a value read from the `.wrp` header, and other maps are not measured (the fit is in `terrain-holes-evidence.md`). Always compute `cell = floor(coordinate / cell_size)` with the cell size of your own terrain, which the map specialist takes from the Terrain Builder project, never a guess.

## Script API

```c
// P:\scripts\3_game\global\game.c:1203
	//! Returns whether tile at provided world coordinates is a hole.
	proto native bool		SurfaceIsHole(float x, float z);
```

- It is the only new hole API and it only reads. Script cannot open or close a hole at run time.
- No vanilla script calls it: a search of `P:\scripts` finds only the declaration.
- Use it to keep things off cells with no terrain: custom loot, spawn points, custom holograms. Vanilla kit placement does not look at holes.

## Where the data lives

Holes live in the world config, not in the `.wrp`: both vanilla `.wrp` files changed format in 1.30 by the same amount although only one map has `Holes` (cross checked; the sizes are in `terrain-holes-evidence.md`).

## Authoring workflow

- Buldozer 1.30 has four new inputs: `UABuldLinkCamToTerrain`, `UABuldCopyTileCoord`, `UABuldMarkUnderground` and `UABuldRemoveUnderground` (`P:\bin\constants.xml:282` to `:285`).
- New in Terrain Builder 1.30 (from the 1.30 release notes, not checked on `P:\`): the Buldozer camera can be unlinked from the terrain height to edit below the surface (key 8 by default), the same toggle affects objects, and each object has an "underground" flag that stops a static object below the terrain from being hidden by occlusion when it should be visible.
- That flag belongs to Terrain Builder. There is no script equivalent for objects created by Object Spawner or `CreateObject`, and whether those objects are occluded below the terrain is not measured.
- A stable DayZ Tools from April 2026 has no hole strings and no flag strings (measured on 2026-09-24, not on `P:\`): a later Terrain Builder is needed.
- A third-party terrain tool released on 2026-09-19 (binaries only, not run here) describes this workflow; none of it is verified:
  - it marks cells of the height field grid and writes `holes.cfg` next to `layers.cfg`, one class per group, where Terrain Builder and Buldozer are meant to read it;
  - it adds the `#include` to the terrain's `config.cpp`;
  - Buldozer reads the file again on each alt-tab;
  - a newer Terrain Builder needs an "underground" flag column in object imports.

  This matches the `\holes.cfg` string the engine uses while loading a world (`terrain-holes-evidence.md`), but the exact path and the reload behavior are not verified.

## Verification status

| Claim | Level |
|---|---|
| The `Holes` and `tiles[]` format, `SurfaceIsHole` | read in source on `P:\` |
| One entry of `tiles[]` is a height map cell; 6.25 m in Livonia | cross checked (fits the triggers) |
| Holes live in the config, not in the `.wrp` | cross checked (the `.wrp` grows the same with and without holes) |
| How a hole renders and collides, what happens when something falls through, AI and navmesh | not verified |
| A config only mod opens holes in a vanilla map | not verified (a hypothesis) |
| `holes.cfg` next to `layers.cfg`, and the reload on alt-tab | not verified (third-party tool behaviour) |
| The effect of `ECE_OBJECT_SPAWNER` on an object under a hole | not verified |

## Before designing with holes

Each test moves one row of the table above. Together they fit in one diag session (`/dayz-launch-test`):

1. **Vanilla Livonia.** `g_Game.SurfaceIsHole(740, 1225)` must return `true` (cell `{118,196}`) and `g_Game.SurfaceIsHole(1000, 1000)` `false`. Take one screenshot from outside the hole and one from inside.
2. **Config only mod.** Add a group of your own in `CfgWorlds >> ChernarusPlus >> Holes` and repeat the check on its cell.
3. **Mod geometry.** Place an object with Object Spawner under that hole and check that it is visible from inside and outside, and that it collides.
4. **Falling.** Drop an object, and walk a character, into a hole with no geometry.

## What could not be verified

- Any behavior in game: rendering, collision, occlusion, falling, AI and navmesh.
- The cell size of any map other than Livonia, and Livonia's as read from the header of the `.wrp`.
- Sakhal: its world is in an encrypted `.ebo` and could not be read.
- Exactly where the engine looks for `holes.cfg`, and whether a config only mod opens holes.
- What the engine does with `ECE_OBJECT_SPAWNER`.

## On Linux

The Proton setup and its limits are in `_shared/linux-proton.md`. Two things change here: Terrain Builder was not started under Proton, so treat any `.wrp` step as Windows only until it is measured; and string searches in the game executable work natively with `strings` and `strings -el` (UTF-16).
