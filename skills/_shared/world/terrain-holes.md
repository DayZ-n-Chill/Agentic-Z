# Terrain holes

How a world removes terrain over a set of height map cells, the one script call that reads holes, how a terrain author marks them, and what is still unproven. Nothing here has been tested in a running game. Where holes are stored, how the cell size follows from the Livonia data, and the engine strings behind loading are in `terrain-holes-storage.md`.

## Three pieces make an underground space

| Piece | What it is | Where it is defined | Who uses it |
|---|---|---|---|
| Hole | height map cells with no terrain | `CfgWorlds >> <world> >> Holes` (the map's config) | the engine, when it loads the world |
| Geometry | a tunnel or bunker placed below the surface | the `.wrp` (Terrain Builder), Object Spawner, or script | the engine |
| Triggers | boxes that darken the view, change the sound and mark the player "underground" | `cfgundergroundtriggers.json` | the server creates them, the client applies the effects (`underground-triggers.md`) |

A hole only removes terrain; it creates no space. What happens to something that falls through a hole with no geometry under it is unverified, so design as if there were no ground. Without triggers it does not get dark inside.

## The `Holes` class

Of the vanilla world configs on `P:\`, only Livonia has holes: seven cells in two groups, beside the two entrances of the Dambog bunker. Chernarus has none (`P:\DZ\worlds\chernarusplus\world\config.cpp` has neither `Holes` nor `tiles`). Sakhal and Nasdara have only their `ce`, `data` and `navmesh` folders on `P:\`, with no world config. The game ships their worlds in encrypted `.ebo` files (not checked on `P:\`).

```cpp
// P:\DZ\worlds\enoch\world\config.cpp:303 (inside CfgWorlds > class Enoch: CAWorld, which opens at :115)
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
- The engine checks the range: the code that reads `tiles` carries the messages `x (%d) out of range <0, %d)` and `y (%d) ...` (strings in the game executable, not checked on `P:\`; see `terrain-holes-storage.md`).
- Each group is a subclass, so a mod could add its own group without overriding the vanilla one. Unverified: whether a mod's config patch on `CfgWorlds >> ChernarusPlus` opens holes. Measure that first.

## The unit is a height map cell

Livonia's grid is 2048 cells of 6.25 m (12,800 m). With that size both groups land on the vanilla Dambog underground triggers:

- `{118, 195 to 197}`: X 737.5 to 743.75, Z 1218.75 to 1237.5, the main entrance.
- `{94 to 95, 180 to 181}`: a 12.5 m square at X 587.5 to 600, Z 1125 to 1137.5, the second entrance.

The 6.25 m size comes from that fit, not from the `.wrp` header, and the cell size of other maps is unknown (the fit is in `terrain-holes-storage.md`). Always compute `cell = floor(coordinate / cell_size)` with the cell size of your own terrain, which the map specialist takes from the Terrain Builder project. Never guess it.

## Reading holes from script

```c
// P:\scripts\3_game\global\game.c:1203 and :1204
	//! Returns whether tile at provided world coordinates is a hole.
	proto native bool		SurfaceIsHole(float x, float z);
```

- It is the only hole API, and it only reads. Script cannot open or close a hole at run time.
- No vanilla script calls it: a search of `P:\scripts` finds only the declaration.
- Use it to keep things off cells with no terrain: custom loot, spawn points, custom holograms. Vanilla kit placement does not check for holes.

Holes live in the world config, not in the `.wrp` (`terrain-holes-storage.md`).

## Marking holes as a terrain author

- Buldozer has four inputs for this: `UABuldLinkCamToTerrain`, `UABuldCopyTileCoord`, `UABuldMarkUnderground` and `UABuldRemoveUnderground` (`P:\bin\constants.xml:282` to `:285`).
- From the 1.30 release notes, not checked on `P:\`: Terrain Builder can unlink the Buldozer camera from the terrain height to edit below the surface (key 8 by default), the same toggle affects objects, and each object has an "underground" flag that stops a static object below the terrain from being hidden by occlusion when it should be visible.
- That flag belongs to Terrain Builder. Script has nothing like it for objects created by Object Spawner or `CreateObject`, and whether those objects are occluded below the terrain is unverified.
- The stable DayZ Tools release that shipped alongside 1.30 has none of the hole or flag strings (not checked on `P:\`), so a later Terrain Builder is needed.
- A third party terrain tool describes this workflow; it ships as binaries only and has not been run, so none of it is verified:
  - it marks cells of the height field grid and writes `holes.cfg` next to `layers.cfg`, one class per group, for Terrain Builder and Buldozer to read;
  - it adds the `#include` to the terrain's `config.cpp`;
  - Buldozer reads the file again on each alt-tab;
  - a newer Terrain Builder needs an "underground" flag column in object imports.

  This matches the `\holes.cfg` string the engine uses while loading a world (`terrain-holes-storage.md`), but the exact path and the reload are unverified.

## What is not yet proven

| Claim | Status |
|---|---|
| The `Holes` and `tiles[]` format, `SurfaceIsHole` | read on `P:\` |
| One entry of `tiles[]` is a height map cell, 6.25 m in Livonia | fits the vanilla triggers; not read from the `.wrp` header |
| Holes live in the config, not in the `.wrp` | the `.wrp` grows the same with and without holes |
| How a hole renders and collides, what falls through, AI and navmesh | unverified |
| A config only mod opens holes in a vanilla map | unverified |
| `holes.cfg` next to `layers.cfg`, and the reload on alt-tab | unverified (third party tool behaviour) |
| What `ECE_OBJECT_SPAWNER` does to an object under a hole | unverified |

The cell size of any map other than Livonia is unknown, and the Sakhal and Nasdara world configs are not on `P:\`.

## Checks to run before designing with holes

Each check settles one unverified row above. All four fit in one diag session (`/dayz-launch-test`):

1. Vanilla Livonia: `g_Game.SurfaceIsHole(740, 1225)` returns `true` (cell `{118,196}`) and `g_Game.SurfaceIsHole(1000, 1000)` returns `false`. Take one screenshot from outside the hole and one from inside.
2. Config only mod: add a group of your own in `CfgWorlds >> ChernarusPlus >> Holes` and repeat the check on its cell.
3. Mod geometry: place an object with Object Spawner under that hole and check that it is visible from inside and outside, and that it collides.
4. Falling: drop an object, and walk a character, into a hole with no geometry.

## On Linux

The Proton setup and its limits are in `_shared/linux-proton.md`. Terrain Builder has not been run under Proton, so treat any `.wrp` step as Windows only. String searches in the game executable work natively with `strings` and `strings -el` (UTF-16).
