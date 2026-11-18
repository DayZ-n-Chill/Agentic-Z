# Cockpit screens and map tiles

Showing a map on a dashboard screen: the render target bridge and its limit, satellite tiles on hidden selections, tile overlap, and sizing a sliding tile window.

> Status: field notes measured in game on a mod test car (TestCoupe, a sedan with a dashboard map screen), on 1.29 unless an entry names another build. They are mod behaviour, not vanilla, and were not repeated for this file. A citation written with its full `P:\` path was opened on the vanilla data of this repo (a 1.30 build).

## Vanilla anchors checked on `P:\`

- `RTTextureWidgetTypeID` is documented as a texture used as render target for children widgets (`P:\scripts\1_core\proto\enwidgets.c:28-29`).
- `SetGUIWidget` binds an `RTTextureWidget` to a hidden selection index of an entity, referenced in the shader as `$rendertarget` (`P:\scripts\1_core\proto\enwidgets.c:634-637`).
- No vanilla script calls `SetGUIWidget`: its declaration is the only occurrence under `P:\scripts` (Grep, 2026-11-17).
- Both tile folders named below exist in the vanilla data: `P:\DZ\gear\navigation\data\usermap\` (1,024 `s_XXX_YYY_lco.paa` files) and `P:\DZ\worlds\chernarusplus\data\layers\` (1,849 of them), counted 2026-11-17.

## Cockpit screen to live engine map: the RTTextureWidget bridge (added 2026-08-19, TestCoupe)

**Cockpit screen → live engine map (RTTextureWidget bridge) (added 2026-08-19, TestCoupe):**
Any hiddenSelections screen can display the ENGINE's map renderer (the one the in-game map uses) instead
of baked tiles: create the RT via `CreateWidget(RTTextureWidgetTypeID, …)` (children render INTO its
texture, `RTTextureWidgetTypeID` at `P:\scripts\1_core\proto\enwidgets.c:28-29` — they never paint to the viewport, so no HUD witness), hang a `MapWidget`
under it with `CreateWidgets(layout, rt)`, then hook the entity **in this exact order**:
`SetObjectMaterial(idx, "Mod\data\x.rvmat")` FIRST (no leading backslash), `SetObjectTexture(idx,
"$rendertarget")` second, `proto native void SetGUIWidget(IEntity, int idx, RTTextureWidget)`
(`P:\scripts\1_core\proto\enwidgets.c:637`) LAST. A later SetObjectMaterial rebinds the base texture slot and silently undoes
the hook — a uniform light-grey screen means `$rendertarget` resolved to the white fallback texture.
Vanilla script has no call site to copy (anchors above); the order was verified in-game on 1.29 diag.
MapWidget `GetScale()` defaults to 0.85; at 0.05–0.6 it draws line-work only (contours + roads, no
urban/forest fill) — pick the zoom with the user's eye gate. If the hooked vehicle leaves the client
streaming bubble its `GetPosition()` reads `<0,0,0>` and the map recenters to the map corner:
production code must re-resolve the vehicle every tick, never cache the entity reference. MCP test
flow that actually seats and starts: `vehicle_get_in_client` (ownership get-in; `vehicle_enter`
answers seated:1 without sticking) → `engine_set`; the tools are those of the DayZ-MCP notes in `skills/dayz-launch-test/references/mcp/`.
**Closed 2026-08-19b — RT unusable for a live GPS:** the RT freezes the FIRST composed frame
(later `SetScale`/`SetMapPos`/vehicle movement never recompose it), and a MapWidget child only ever
contributes the vector layers (roads + contours) — the raster fill (land, forest, buildings) never
reaches the RT, even with a 24 s warm-up between widget creation and the entity hook. The bridge
recipe above remains valid for STATIC screen content only. Live vehicle GPS goes through baked
tiles on hiddenSelections instead (next section).

## Screen tiles: terrain satmap, not the navigation usermap, re-asserted client-side (added 2026-08-19, TestCoupe)

**Vehicle screen tiles: terrain satmap, not navigation usermap — and re-assert client-side (added 2026-08-19, TestCoupe):**
Two tile sources share the same `s_XXX_YYY_lco.paa` naming on chernarusplus but look completely
different, and their grids are not the same size: on this repo's `P:\` the usermap folder holds
32×32 tiles (`s_000_000` to `s_031_031`) and the layers folder 43×43 (`s_000_000` to `s_042_042`),
so read the grid size from the folder and do not assume 32. The notes below were written against a
32×32 grid of 480 m tiles, which is not what `P:\` holds for the layers folder. `dz\gear\navigation\data\usermap\` is the PAPER
map art (light background, red roads, contour lines — what the ItemMap shows), while
`dz\worlds\chernarusplus\data\layers\` is the colored aerial satmap (the real "GPS look").
A GPS screen wants the layers path; world name must be parameterized per terrain. Second half of
the rule: `SetObjectTexture`/`SetObjectMaterial` called ONLY client-side is silently reverted
to the config `hiddenSelectionsTextures[]` whenever the server pushes a visual-state resync —
observed reproducibly on GEAR CHANGE. **Applying on the dedicated server does NOT fix it
(refuted in-game 2026-08-19 afternoon): scripted SetObject* state does not replicate
server→client.** The working pattern is the skin-mod one: re-assert the full scripted visual
state client-side on EVERY `OnVariablesSynchronized` (no packed==applied early-out; gate only
the diagnostics). Also force-hide every bank window on the first apply
(`SetAnimationPhaseNow(name, 1.0)` loop): windows spawn with the config-default texture and
their initial hide phase is not guaranteed applied. The force-hide only exists at runtime if
the hide animations actually BAKED — see "Animations only bake for selections that are skeleton
bones" in `animation-bake-and-odol-sections.md`. Satmap-in-bank
verified in-game 2026-08-19 (TestCoupe, 1.29 diag, human driver gate).

## Neighbouring satmap tiles share 32 px (added 2026-09-14, TestCoupe)

**Tile overlap: neighboring satmap layer tiles share 32 px — sample only the tile core (added 2026-09-14, TestCoupe).** In `dz\worlds\chernarusplus\data\layers\`, column 480 of a tile is column 0 of its east neighbor and row 480 is row 0 of its south neighbor: a per-tile screen map must sample only the core `16/512..496/512` of each tile. Without the crop the measured seam ratio was ~1.9-2.1 and roads jumped ~30 m; with it, 0.90-1.12 (measured offline on the 1.30.164014 Exp satmap tiles). Name index of `s_AAA_BBB_lco.paa`: AAA is the tile column tx, BBB encodes the row as 31 - tz on a 32-row grid (last row index minus tz; not yet checked on the 43-row layers folder of `P:\`), and UV (0,0) is the northwest corner.

## Sliding-plate tile window: border row and bezel size

**Sliding-plate tile window: fix the border row and size the bezel with `wy + COVER + T` (added 2026-10-01, TestCoupe).** Design rule, worked out offline: on a sliding-plate tile map with the marker centred, the hidden margin under the window must reach one full tile past the lowest window corner: with a free bottom row it is 1.5 tiles deep (97.5 mm under the centre on a 7x5 grid of 32 mm tiles, window +/-88.63 x +/-52.92 mm, bezel 99 mm). Pinning the bottom row with `minValue`/`offset0` in its `_y` class (same slope), whenever its top edge stays COVER below the lowest projected window corner, cuts the requirement to 88.68 mm and the bezel to 90 mm. Under the window the requirement is always `wy + COVER + T`; with a centred marker nothing below one full tile reduces it. If a smaller bezel is wanted, the lever is tile size (zoom), not the window - say so with a preview.
