# Terrain holes: the evidence (DayZ 1.30)

What is known about 1.30 terrain holes and how it was found: the Livonia config, the cell size, the new engine strings, the `.wrp` version change, and what Terrain Builder 1.30 and the FTT tool add. The config, the trigger file and the `.wrp` files are on `P:\` and were checked there. The engine string search and the comparison with 1.29 were measured on 2026-09-24 (install 1.30.164014 against 1.29 stable) and are not checkable on `P:\`. Nothing here was tested in a running game.

## The Livonia config

`P:\DZ\worlds\enoch\world\config.cpp:303` has `class Holes` inside `CfgWorlds` `Enoch`, between `OutsideTerrain` and `Grid`, with one group, `Dambog`, of seven cells:

```cpp
// P:\DZ\worlds\enoch\world\config.cpp:303
		class Holes
		{
			class Dambog
			{
				tiles[]=
				{
					{118,195},
					{118,196},
					{118,197},
					{94,180},
					{95,180},
					{94,181},
					{95,181}
				};
			};
		};
```

The same world class gained `hasOcean=0` (`P:\DZ\worlds\enoch\world\config.cpp:409`).

The Chernarus world config on `P:\` (file `P:\DZ\worlds\chernarusplus\world\config.cpp`) has neither `Holes` nor `tiles`. The Sakhal world is in an encrypted `.ebo` and is not unpacked.

From the comparison with 1.29, not on `P:\`: the 1.29 config of Livonia has no `Holes` class, and `cfgundergroundtriggers.json` of Livonia is byte for byte the same in 1.29 and 1.30, so holes did not arrive with new triggers.

## Cell size in Livonia: 6.25 m

Livonia is 12,800 m wide. With 2048 cells, a cell is 6.25 m. The table places the `Dambog` cells for three assumed sizes, against the eight vanilla underground triggers of the Dambog bunker (file `P:\DZ\worlds\enoch\ce\cfgundergroundtriggers.json`, at X 584.6 to 749.7 and Z 1131.0 to 1229.1):

| Cell group | With 5 m | With 6.25 m | With 10 m |
|---|---|---|---|
| `{118, 195 to 197}` | X 590 to 595, Z 975 to 990 | X 737.5 to 743.75, Z 1218.75 to 1237.5 | X 1180 to 1190, Z 1950 to 1980 |
| `{94 to 95, 180 to 181}` | X 470 to 480, Z 900 to 910 | X 587.5 to 600, Z 1125 to 1137.5 | X 940 to 960, Z 1800 to 1820 |

Triggers that the 6.25 m column lands on:

- Main entrance: the triggers at (749.7; 533.5; 1228.5) and (735.0; 533.7; 1229.1), each 15 by 5.6 by 10.8 m.
- Second entrance: the trigger at (593.7; 588.75; 1131.8), 11 by 22.3 by 11.6 m.

With 5 m and with 10 m neither group falls inside the range of the triggers. Two independent groups fitting is what supports the 6.25 m reading. It is a cross check, not a read value: the cell size was not read from the header of the `.wrp`, and the cell size of other maps is not measured.

## New engine strings

Measured in `DayZDiag_x64.exe` 1.30.164014; not on `P:\`. Four related strings appear that the 1.29 executable does not have (other occurrences of "hole" belong to Recast, the navmesh generator, and were already there):

| String | Where used (reference address in that build) | Nearby strings in that function |
|---|---|---|
| `\holes.cfg` | 0x792cb4 | `CfgWorlds` (+1429), `DefaultWorld` (+1474): world loading |
| `tiles` | 0x6655e3 | `Holes` (+1308) |
| `Holes` | 0x665aff | `tiles` (-1308), `y (%d) out of range <0, %d)` (+1349), `x (%d) out of range <0, %d)` (+1374) |
| `Holes` | 0x71b1f2 | `minTreesInForestSquare` (-1358), `minRocksInRockSquare` (-1203): `CfgWorlds` parameters |
| `SurfaceIsHole` | 0xc20528 | the native table of `CGame` (`SurfaceY`, `SurfaceRoadY`, `GetSurfaceInfoOn` and others) |

In the read only data, `\holes.cfg` sits right before the loading screen messages ("Preparing surface materials", "Extruding hills and valleys") and right after the Buldozer actions `UABuldMarkUnderground` and `UABuldRemoveUnderground`.

Reading of this, marked as inference: code walks `Holes`, reads `tiles`, and checks each `x` and `z` against the grid size; `Holes` is also read as a world parameter in `CfgWorlds`; and a path exists that loads a `holes.cfg` file while loading the world. The code was not disassembled to see how that path is built.

The script side is on `P:\`: `SurfaceIsHole` is declared at `P:\scripts\3_game\global\game.c:1204`.

### How to repeat the measurement

1. Extract `dta\scripts.pbo`, `Addons\worlds_enoch.pbo` and `Addons\worlds_chernarusplus.pbo` from both game versions. Any PBO extractor works; the entries are not compressed.
2. Turn each `config.bin` into text with `CfgConvert.exe -txt` from DayZ Tools and compare them.
3. Search the strings of `DayZDiag_x64.exe` in both versions, ASCII and UTF-16, and compare the lists.
4. To see which code uses a string, search the `.text` section for `lea` or `mov r64, [rip+disp32]` instructions that point at its address, and list the other strings referenced within about 0x600 bytes. The addresses belong to one build and change with every build.

## The `.wrp` changes the same way with and without holes

| Map | 1.29 (not on `P:\`) | 1.30 (on `P:\`) | Difference | Has `Holes`? |
|---|---|---|---|---|
| ChernarusPlus | OPRW v29, 223,653,986 bytes | OPRW v32, 235,121,528 bytes (`P:\DZ\worlds\chernarusplus\world\chernarusplus.wrp`) | plus 5.1 % | no |
| Enoch (Livonia) | OPRW v29, 226,053,187 bytes | OPRW v32, 237,263,513 bytes (`P:\DZ\worlds\enoch\world\enoch.wrp`) | plus 5.0 % | yes |

Both files move to v32 and grow by the same share although only one map has holes, so the `.wrp` change is a format change. This supports holes living in the config. It does not rule out the `.wrp` also storing something related, for example the per object "underground" flag.

## Not on `P:\`: the 1.30 release and the FTT tool

- **DayZ 1.30.164014.**
  - The release adds terrain holes for modding, with no further detail published.
  - Terrain Builder gains a Buldozer camera that can be unlinked from the terrain to edit below the surface (key 8), an input to link and unlink it, the same toggle affecting objects, and an "underground" flag per object against occlusion.
- **Badlands (announced 2026-09-22).** Among what arrives with it: underground facilities and infrastructure built on the new terrain holes system, which will also be available for other maps and for mods, and Morse radio signals that lead to underground shelters.
- **FTT (third-party terrain tool, 2026-09-19 and 20).** Binaries only, no source. Third-party tool behaviour, as its documentation describes it:
  - its "Hole Generator" marks cells of the height field grid;
  - it writes `holes.cfg` next to `layers.cfg`, one class per group;
  - it adds the `#include` to the terrain's `config.cpp`;
  - Buldozer reads the file again on each alt-tab;
  - a newer Terrain Builder needs an "underground" flag column in object imports.

  None of this was verified. Its binary was not run.
