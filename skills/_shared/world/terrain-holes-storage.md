# Where terrain holes are stored

Which file holds a world's holes, why one cell is 6.25 m in Livonia, which engine strings load holes, and how the `.wrp` format changed in 1.30. The world config, the trigger file and the `.wrp` files are on `P:\`. The engine strings and the 1.29 files are not on `P:\`; each line says so. How to use holes is in `terrain-holes.md`.

## The Livonia config

`class Holes` sits inside `CfgWorlds` `Enoch`, between `OutsideTerrain` and `Grid` (`P:\DZ\worlds\enoch\world\config.cpp:303`); the block itself is quoted in `terrain-holes.md`. The same world class also has `hasOcean=0` (`P:\DZ\worlds\enoch\world\config.cpp:409`).

The 1.29 config of Livonia has no `Holes` class, and Livonia's `cfgundergroundtriggers.json` is byte for byte the same in 1.29 and 1.30 (not on `P:\`). Holes therefore did not come with new triggers; they open ground over triggers that already existed.

## Why a Livonia cell is 6.25 m

Livonia is 12,800 m wide; with 2048 cells, a cell is 6.25 m. The table places the `Dambog` cells for three possible cell sizes, against the eight vanilla underground triggers of the Dambog bunker (`P:\DZ\worlds\enoch\ce\cfgundergroundtriggers.json`, at X 584.6 to 749.7 and Z 1131.0 to 1229.1):

| Cell group | With 5 m | With 6.25 m | With 10 m |
|---|---|---|---|
| `{118, 195 to 197}` | X 590 to 595, Z 975 to 990 | X 737.5 to 743.75, Z 1218.75 to 1237.5 | X 1180 to 1190, Z 1950 to 1980 |
| `{94 to 95, 180 to 181}` | X 470 to 480, Z 900 to 910 | X 587.5 to 600, Z 1125 to 1137.5 | X 940 to 960, Z 1800 to 1820 |

The triggers the 6.25 m column lands on:

- Main entrance: the triggers at (749.7; 533.5; 1228.5) and (735.0; 533.7; 1229.1), each 15 by 5.6 by 10.8 m.
- Second entrance: in X and Z the cells overlap five triggers. Three form the entrance stack: the transition trigger at (592.0; 606.5; 1131.0), 8.7 by 16 by 7.8 m with 12 breadcrumbs; the trigger below it at (593.7; 588.75; 1131.8), 11 by 22.3 by 11.6 m; and the outer trigger (`EyeAccommodation` 1) at (584.65; 611; 1131.1), 6 by 8 by 7.6 m, which reaches only 0.15 m into the cells. The other two are the large interior boxes at (605.05; 562.5; 1143.45) and (626.15; 504.95; 1143.3), which cover this ground deeper down.

With 5 m or 10 m, neither group falls inside the triggers. Two independent groups fitting is what supports 6.25 m. It is a fit, not a value read from the `.wrp` header, and the cell size of other maps is unknown.

## Engine strings that load holes

The 1.30 diag executable has four related strings that the 1.29 executable lacks (not on `P:\`). Other occurrences of "hole" belong to the navmesh generator and are older.

| String | Strings referenced from the same function |
|---|---|
| `\holes.cfg` | `CfgWorlds`, `DefaultWorld`: world loading |
| `tiles` | `Holes` |
| `Holes` | `tiles`, `y (%d) out of range <0, %d)`, `x (%d) out of range <0, %d)` |
| `Holes` | `minTreesInForestSquare`, `minRocksInRockSquare`: `CfgWorlds` parameters |
| `SurfaceIsHole` | the native table of `CGame` (`SurfaceY`, `SurfaceRoadY`, `GetSurfaceInfoOn` and others) |

In the read only data, `\holes.cfg` sits right before the loading screen messages ("Preparing surface materials", "Extruding hills and valleys") and right after the Buldozer actions `UABuldMarkUnderground` and `UABuldRemoveUnderground`.

What the strings suggest, unverified because the code has not been disassembled: the engine walks `Holes`, reads `tiles` and checks each `x` and `z` against the grid size; it also reads `Holes` as a `CfgWorlds` world parameter; and a path exists that loads a `holes.cfg` file while the world loads. How that path is built is unknown.

The script side is on `P:\`: `SurfaceIsHole` is declared at `P:\scripts\3_game\global\game.c:1204`.

## Checking a new game build

Repeat this whenever a game update may have changed holes:

1. Extract `dta\scripts.pbo`, `Addons\worlds_enoch.pbo` and `Addons\worlds_chernarusplus.pbo` from the old and the new game version. Any PBO extractor works; the entries are not compressed.
2. Turn each `config.bin` into text with `CfgConvert.exe -txt` from DayZ Tools and compare them.
3. List the strings of `DayZDiag_x64.exe` in both versions, ASCII and UTF-16, and compare the lists.
4. To see which code uses a string, search the `.text` section for `lea` or `mov r64, [rip+disp32]` instructions that point at its address, and list the other strings referenced within about 0x600 bytes. Addresses change with every build, so never reuse them from an older one.

## The `.wrp` format changed on every map

| Map | 1.29 (not on `P:\`) | 1.30 | Growth | Has `Holes` |
|---|---|---|---|---|
| ChernarusPlus | OPRW v29 | OPRW v32 (`P:\DZ\worlds\chernarusplus\world\chernarusplus.wrp`) | 5.1 % | no |
| Enoch (Livonia) | OPRW v29 | OPRW v32 (`P:\DZ\worlds\enoch\world\enoch.wrp`) | 5.0 % | yes |

Both files move to v32 and grow by the same share although only one map has holes, so the change is a format change. That supports holes living in the config. It does not rule out the `.wrp` also storing something related, for example the per object "underground" flag. The file layout itself is in `wrp-format-and-road-graph.md`.
