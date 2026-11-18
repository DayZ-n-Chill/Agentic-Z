# Cockpit screens and map tiles

How to show a map on a dashboard screen: the render target route and why it cannot show a live map, satellite tiles on hidden selections, the overlap between tiles, and sizing a sliding tile window.

The results were measured in game on a test car with a dashboard map screen; they are mod behaviour, not vanilla.

## What vanilla shows

- `RTTextureWidgetTypeID` is a "Texture used as render target for children widgets" (`P:\scripts\1_core\proto\enwidgets.c:28` and `:29`).
- `SetGUIWidget(IEntity ent, int index, RTTextureWidget w)` binds a render target widget to a hidden selection of an entity, which the shader reads as `$rendertarget` (`enwidgets.c:634` to `:637`).
- No vanilla script calls `SetGUIWidget`; its declaration is the only place it appears under `P:\scripts`.
- Both tile folders below exist: `P:\DZ\gear\navigation\data\usermap\` holds 1,024 `s_XXX_YYY_lco.paa` files (a 32 by 32 grid) and `P:\DZ\worlds\chernarusplus\data\layers\` holds 1,849 (43 by 43).

## The render target route: static content only

A hidden selection screen can show the engine's own map renderer, the one the in-game map uses, instead of baked tiles:

1. Create the render target with `CreateWidget(RTTextureWidgetTypeID, ...)`. Its children draw into its texture, never onto the screen.
2. Hang a `MapWidget` under it with `CreateWidgets(layout, rt)`.
3. Hook the entity in this order: `SetObjectMaterial(idx, "MyMod\data\screen.rvmat")` first (no leading backslash), then `SetObjectTexture(idx, "$rendertarget")`, then `SetGUIWidget(entity, idx, rt)` last.

A later `SetObjectMaterial` rebinds the base texture and silently undoes the hook. A flat light grey screen means `$rendertarget` fell back to the white texture. Vanilla has no call to copy, so this order comes from the in-game test.

`MapWidget.GetScale()` defaults to 0.85. Between 0.05 and 0.6 it draws lines only, contours and roads with no town or forest fill; choose the zoom by eye with the user. If the vehicle leaves the client's streaming range its `GetPosition()` reads `<0,0,0>` and the map jumps to the corner, so look the vehicle up again every tick instead of keeping the reference.

The route cannot show a live GPS. The render target keeps the first frame it draws: later `SetScale`, `SetMapPos` or vehicle movement never redraw it. A `MapWidget` child also gives only the vector layers (roads and contours); the raster fill of land, forest and buildings never reaches the render target, even 24 s after creating the widget. Use it for static screen content only, and build a live GPS from baked tiles (next section).

To seat a driver and start the engine from a test script, the client must own the vehicle: a seat forced on the server reports the player seated without the client taking ownership, and the engine does not start. Seat the player on the client as well, then start the engine; `scripted-vehicle-tests.md` has the details.

## Screen tiles: the satellite layers, reapplied on the client

Both folders name their tiles `s_XXX_YYY_lco.paa` but look nothing alike, and their grids differ in size, so read the grid size from the folder rather than assuming 32:

| Folder | Look | Grid on `P:\` |
|---|---|---|
| `dz\gear\navigation\data\usermap\` | The paper map: light background, red roads, contour lines, as the map item shows | 32 by 32, `s_000_000` to `s_031_031` |
| `dz\worlds\chernarusplus\data\layers\` | The coloured aerial image, the real GPS look | 43 by 43, `s_000_000` to `s_042_042` |

A GPS screen wants the layers folder, with the world name as a parameter for other terrains. The figures in the rest of this file were worked out on a 32 by 32 grid of 480 m tiles, not the 43 by 43 layers folder on `P:\`; check them against it.

`SetObjectTexture` and `SetObjectMaterial` called only on the client are silently reset to the config `hiddenSelectionsTextures[]` whenever the server pushes a visual state resync; a gear change triggers it every time. Applying them on the dedicated server does not help, because scripted `SetObject*` state does not travel from server to client. Do what skin mods do: on the client, reapply the whole scripted visual state in every `OnVariablesSynchronized`, with no "already applied" shortcut (gate only the diagnostics). On the first apply, also force every tile window hidden with a `SetAnimationPhaseNow(name, 1.0)` loop: windows spawn with the config texture, and their starting hide phase is not guaranteed. That works only if the hide animations baked, which needs every window to be a skeleton bone (`animation-bake-and-odol-sections.md`).

## Neighbouring tiles share 32 px

In `dz\worlds\chernarusplus\data\layers\`, column 480 of a tile is column 0 of its east neighbour, and row 480 is row 0 of its south neighbour. A screen map built per tile must sample only the core of each tile, `16/512` to `496/512`. Without that crop the seam ratio measured about 1.9 to 2.1 and roads jumped about 30 m; with it, 0.90 to 1.12 (measured offline on DayZ 1.30 tiles).

In `s_AAA_BBB_lco.paa`, `AAA` is the tile column `tx` and `BBB` is the row written as `31 - tz` on a 32 row grid, that is the last row index minus `tz`. This is not yet checked on the 43 row layers folder on `P:\`. UV `(0,0)` is the north west corner.

## Sizing a sliding tile window

With a sliding plate of tiles and the position marker centred, the hidden margin under the window must reach one full tile past the lowest corner of the window. Worked out offline on a 7 by 5 grid of 32 mm tiles, with the window at plus or minus 88.63 by 52.92 mm:

- With a free bottom row, the margin is 1.5 tiles deep: 97.5 mm under the centre, and a 99 mm bezel.
- Pinning the bottom row with `minValue` and `offset0` in its `_y` class (same slope), as long as its top edge stays `COVER` below the lowest projected window corner, cuts it to 88.68 mm and a 90 mm bezel.

Under the window the need is always `wy + COVER + T`; with a centred marker, nothing below one full tile reduces it. For a smaller bezel the lever is tile size, that is the zoom, not the window; show the user a preview when you suggest it.
