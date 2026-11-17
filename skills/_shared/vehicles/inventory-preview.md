# Inventory preview of vehicle parts

Two ways the inventory preview of a door, hood or other part renders empty: the wrong `rotationFlags` for its side, and an `invview` point at the bounding box centre.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- Preview view 0 is documented as `boundingbox_min + boundingbox_max + invView` (`P:\scripts\3_game\gameplay.c:293`).
- The inventory icon calls `SetModelOrientation("0 0 0")` and then `SetView` with `GetViewIndex` (`P:\scripts\5_mission\gui\inventorynew\containeditems\icon.c:1385-1386`), and `GetViewIndex` looks for an `invView2` memory point (`P:\scripts\3_game\entities\entityai.c:3769-3771`).
- `Hatchback_02_Door_1_1` sets `rotationFlags=8` (`P:\DZ\vehicles\wheeled\config.cpp:9029`), `Hatchback_02_Door_2_1` sets `rotationFlags=4` (`P:\DZ\vehicles\wheeled\config.cpp:9153`), `Hatchback_02_Door_1_2` sets `rotationFlags=8` (`P:\DZ\vehicles\wheeled\config.cpp:9164`) and `Hatchback_02_Door_2_2` sets `rotationFlags=4` (`P:\DZ\vehicles\wheeled\config.cpp:9288`). `Truck_01_Door_2_1` overrides its left-hand parent only to set `rotationFlags=4` (`P:\DZ\vehicles\wheeled\config.cpp:18348`).

## Two ways a part preview renders empty (split from the lights notes 2026-10-01)

### 1. `rotationFlags` is per SIDE, and the wrong one renders an empty preview

Left-hand doors take `8`, right-hand doors take `4`. Vanilla applies this in every family —
`Hatchback_02_Door_1_1`/`1_2` use 8 while `2_1`/`2_2` use 4 (`P:\DZ\vehicles\wheeled\config.cpp:9029`,
`:9153`, `:9164`, `:9288`), and `Truck_01_Door_2_1` overrides its left-hand parent purely to set 4
(`:18348`). A mirrored door that inherits the left-hand value shows a **blank item-inspect preview**
while its opposite renders normally, with everything else identical: same LOD table, same named
properties, same bounding box, same distance to origin, same selections, same winding. Symmetric
config plus symmetric geometry plus one side blank means look at `rotationFlags` before the model.

### 2. An inventory preview goes BLANK when `invview` sits at the bounding-box centre (SP-415, added 2026-10-01, SUB_BRZ s98)

A part mounts, renders in the world and keeps its tooltip, and its inventory preview is still empty.
`ItemPreviewWidget` view 0 is `boundingbox_min + boundingbox_max + invView`
[EXACT][CLAIM-INVVIEW-VIEW0-DEF] (`scripts/3_game/gameplay.c:293`, DayZ 1.30.164014 Exp), and the
icon forces `SetModelOrientation("0 0 0")` + `SetView(GetViewIndex())`
(`containeditems/Icon.c:1385-1386`): with `invview` at the box centre the eye-to-centre direction is
null and the render comes out empty. Measured on the two SUB_BRZ doors (s98, in game, DayZ
1.30.164014 Exp): both had `invview` within 3e-8 m of the bbox centre (and of `ce_center` / `pos
center`); vanilla puts it ~1.07 m from the centre, OUTSIDE the box, on the side to show, and reuses
the same point on both mirrored doors. Never write `invview = (min+max)/2`; offline gate:
|invview - bbox centre| > 0.3 m for every part with a preview. With `invview2` present,
ATTACHMENT/GROUND render view 1 and CARGO/HANDS view 0 (`scripts/3_game/entities/entityai.c:3769-3811`) -
design both point sets together or not at all.
