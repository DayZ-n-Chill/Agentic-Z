# Inventory preview of vehicle parts

Why the inventory preview of a door, hood or other part can render empty, and the two config and model settings that cause it: `rotationFlags` on the wrong side, and an `invview` point at the bounding box centre.

## How the preview is drawn

View 0 of the item preview (`GetView()`) is documented as `boundingbox_min + boundingbox_max + invView` (`P:\scripts\3_game\gameplay.c:293`). The inventory icon sets `SetModelOrientation("0 0 0")` and then `SetView(m_Obj.GetViewIndex())` (`P:\scripts\5_mission\gui\inventorynew\containeditems\icon.c:1385` and `:1386`).

`GetViewIndex` returns 0 unless the model has an `invView2` memory point (`P:\scripts\3_game\entities\entityai.c:3769` to `:3771`). With `invView2` present on Windows, a part in `ATTACHMENT` or `GROUND` uses view 1, and one in `CARGO`, `HANDS` or `PROXYCARGO` uses view 0 (`entityai.c:3778` to `:3797`). Design both point sets together or leave `invView2` out.

## `rotationFlags` is set per side

Left-hand doors take `rotationFlags=8` and right-hand doors take `4` (`P:\DZ\vehicles\wheeled\config.cpp`):

| Door classes | Value | Line |
|---|---|---|
| `HatchbackDoors_Driver` against `HatchbackDoors_CoDriver` | `8` and `4` | `:919`, `:1039` |
| `CivSedanDoors_Driver` against `CivSedanDoors_CoDriver` and `CivSedanDoors_BackRight` | `8` and `4` | `:4813`, `:4936`, `:4957` |
| `Hatchback_02_Door_1_1` and `_1_2` against `_2_1` and `_2_2` | `8` and `4` | `:9029`, `:9164`, `:9153`, `:9288` |
| `Truck_01_Door_2_1`, which inherits the left-hand `Truck_01_Door_1_1` and overrides the value | `4` | `:18348` |

Two families do not override it. `Sedan_02_Door_2_1` and `Sedan_02_Door_2_2` set no `rotationFlags` and inherit `8` from `Sedan_02_Door_1_1` (`:13566`, `:13695`, `:13455`). `Offroad_02_Door_2_1` and `Offroad_02_Door_2_2` inherit `8` from `Offroad_02_Door_1_1` (`:20723`, `:20743`, `:20586`).

A mirrored door that inherits the left-hand value can show a blank inspect preview while its opposite renders normally, with the LOD table, named properties, bounding box, selections and winding all the same (measured in game on a test car; not checked on `P:\`). When the config and geometry are symmetric and only one side is blank, check `rotationFlags` before the model.

## `invview` at the bounding box centre

A part can mount, render in the world and keep its tooltip while its inventory preview stays empty. With `invview` at the centre of the bounding box, the direction from the eye to the centre is zero and the render comes out empty. Measured in game on two doors of a test car, both with `invview` within 3e-8 m of the box centre.

Vanilla puts the point about 1.07 m from the centre, outside the box, on the side to show, and reuses the same point on both mirrored doors. This is not checked on `P:\`, because the vanilla door models there are binarized.

Never write `invview = (min + max) / 2`. Check offline that `invview` sits more than 0.3 m from the bounding box centre on every part that has a preview.

Related: door classes and their slots are in `attachments-and-crew.md`.
