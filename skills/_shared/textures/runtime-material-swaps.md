# Material and texture swaps at run time

What changes an item's material or texture while the game runs: the engine's health levels, the script calls, and what was measured when a script repaints worn clothing. Read it before writing thermal vision, camouflage, team marking or any effect that calls `SetObjectMaterial`.

How to read it: a line with a `P:\` citation was checked on the vanilla files. A block marked **measured in game** records a test run in the DayZ client that has no vanilla file behind it; it is not yet checked on `P:\`, so treat it as a lead and repeat the test before a design depends on it. The clothing runs are dated 2026-08-31.

## Contents

- [The calls and their two index spaces](#the-calls-and-their-two-index-spaces)
- [Health levels swap materials in the engine](#health-levels-swap-materials-in-the-engine)
- [Wetness does not repaint clothing](#wetness-does-not-repaint-clothing)
- [A script material on worn clothing: what was measured](#a-script-material-on-worn-clothing-what-was-measured)
- [The getter is not proof of what renders](#the-getter-is-not-proof-of-what-renders)
- [An empty texture hides the selection](#an-empty-texture-hides-the-selection)
- [A material cannot move a texture that a script assigns](#a-material-cannot-move-a-texture-that-a-script-assigns)

## The calls and their two index spaces

Two families of calls exist, and each indexes a different config array.

| Call | Indexes | Vanilla declaration |
|---|---|---|
| `SetObjectTexture`, `GetObjectTexture` | `hiddenSelections[]` | `P:\scripts\3_game\entities\entityai.c:2881` ("Change texture in hiddenSelections") |
| `SetObjectMaterial`, `GetObjectMaterial` | `hiddenSelections[]` | `P:\scripts\3_game\entities\entityai.c:2884` ("Change material in hiddenSelections") |
| `SetSimpleHiddenSelectionState`, `IsSimpleHiddenSelectionVisible` | `simpleHiddenSelections[]` | `P:\scripts\3_game\entities\entityai.c:2877` ("Simple hidden selection state; 0 == hidden") |

- `GetHiddenSelectionIndex` returns an index into `hiddenSelections[]` only; its own comment says so (`P:\scripts\3_game\entities\entityai.c:2778`). Use it for the texture and material calls.
- For the simple calls, read the other array and search it by name. Vanilla does both steps, the guard and the lookup, with `ConfigIsExisting("simpleHiddenSelections")` and `ConfigGetTextArray` in `P:\scripts\4_world\entities\firearms\weapon_base.c:94-99`. The member it fills is declared with the comment "index in simpleHiddenSelections cfg array" beside `m_weaponHideBarrelIdx` (`P:\scripts\4_world\entities\firearms\weapon_base.c:62`).
- The same lookup with `ConfigGetTextArray` sits in the head class (`P:\scripts\4_world\entities\manbase\bodyparts\head.c:20`), and the guard alone in the binoculars action, `ConfigIsExisting("simpleHiddenSelections")` at `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionviewbinoculars.c:35`.
- Vanilla never feeds one space into the other. Of the 32 lines in `P:\scripts` that call the simple pair (two more are commented out), none passes `GetHiddenSelectionIndex`: they use fixed numbers such as `SIMPLE_SELECTION_MELEE_RIFLE` (`P:\scripts\3_game\dayzplayer.c:1173`), stored members such as `m_magazineSimpleSelectionIndex` (`P:\scripts\4_world\entities\firearms\weapon_base.c:2136`), or a getter such as `GetHairIndex` (`P:\scripts\4_world\entities\manbase\playerbase.c:9407`).
- **Measured in game** (2026-08-31): passing a `GetHiddenSelectionIndex` result to `SetSimpleHiddenSelectionState` crashed the client natively, with a minidump and no script trace.

Body clothing has no simple selections to index. Under `P:\DZ\characters`, only four `config.cpp` files declare `simpleHiddenSelections`: `heads` (3 times), `headgear` (2), `data` (2) and `glasses` (1). The tops, pants, vests, gloves, shoes, belts, backpacks and masks configs declare none, so the simple calls cannot hide part of a shirt. They still work for headgear and glasses, with the guard above.

A scan of the `proto native` lines of `entityai.c` and `object.c` finds only these calls for textures, materials and simple selections. There is no general "refresh the visuals" call.

`SetObjectTexture` changes the texture on the machine that calls it only. To show a skin to every player, ship the textures in the PBO through `hiddenSelectionsTextures[]`, sync only the chosen index (net sync or RPC), and let each client call `SetObjectTexture(i, textures[index])` itself (measured in a mod).

What a mod cannot do with images at run time (checked across `P:\scripts`, Community Framework and Dabs Framework, none of which has a capture or readback call): read the screen or a render back into script; call a native DLL (`CallExtension` is an Arma 3 call and occurs nowhere in `P:\scripts`); save a screenshot through `Workspace.SaveScreenshot`, which does not exist. `MakeScreenshot` is still declared (`P:\scripts\1_core\proto\proto.c:142`) but was measured broken since 1.19. Render-to-texture (`r2t`) surfaces are declared in config and tied to memory points, not created from script. An image a mod must show has to reach the client as a file, loaded into an `ImageWidget` with `LoadImageFile` (`P:\scripts\1_core\proto\enwidgets.c:257`).

## Health levels swap materials in the engine

`healthLevels[]` in an item's `DamageSystem` maps health thresholds to materials. For `TShirt_ColorBase` it is at `P:\DZ\characters\tops\config.cpp:2283-2330`: `1` and `0.7` give `tshirt.rvmat`, `0.5` and `0.3` give `tshirt_damage.rvmat`, and `0` gives `tshirt_destruct.rvmat`.

- The engine applies the swap, not script. `GetHealthLevel` is `proto native` (`P:\scripts\3_game\entities\object.c:1171`), and the only lines in `P:\scripts` that name the config array are three comments in that file. A search of the scripts for a material writer therefore finds nothing, and that does not mean nothing writes the material.
- `EEHealthLevelChanged` runs on the client: the vanilla body in `Clothing_Base` is guarded by `IsHeadlessOrDedicatedServer` and does only client work (`P:\scripts\4_world\entities\itembase\clothing_base.c:111-125`).
- **Measured in game** (2026-08-31): crossing a health threshold wiped a script material override on the next frame, and the engine wrote its material after `EEHealthLevelChanged` had run. Inside the hook the getter still returned the script's material; one tick later it was empty. Re-applying the override inside the hook is therefore lost.

Leave the `personality` selection alone when you repaint clothing. Vanilla already writes a material and a texture there with `SetObjectMaterial` and `SetObjectTexture` (`P:\scripts\4_world\entities\itembase\clothing_base.c:155-156`).

## Wetness does not repaint clothing

The four wetness thresholds are the constants `STATE_DRENCHED`, `STATE_SOAKING_WET`, `STATE_WET` and `STATE_DAMP` (`P:\scripts\3_game\constants.c:933-936`). No vanilla clothing material follows them:

- The one vanilla material swap by wetness is the garden plot, and it is done in script with `SetObjectMaterial` (`P:\scripts\4_world\entities\gardenbase.c:605-610`).
- Under `P:\DZ\characters` no file has `wet` in its name, against 353 `*damage*.rvmat` files.
- **Measured in game** (2026-08-31): a script override stayed in place while a worn item crossed all four wetness thresholds.

## A script material on worn clothing: what was measured

All of this section is **measured in game** (DayZ client, 2026-08-31). The override was `dz\data\data\mirror.rvmat` on the camo selections, because it reads as binary to the eye: `specular[]={2,2,2,0}` on a dark diffuse (`P:\DZ\data\data\mirror.rvmat:5`).

What a first run saw:

| Writes of `SetObjectMaterial` | Result |
|---|---|
| 1, right after a health level change | rendered (not reproduced later, see below) |
| 1, about 50 s after the last state change | did not render, though the call was made with valid indexes |
| about 19 per second, sustained | rendered at health levels 0, 2 and 4, stable |
| writing stopped | the material stayed |

That table suggests frequency is the cause. A second run the same day showed it is not. Each arm used a new garment made with `CreateAttachment`, with no health level change:

| Treatment | Writes | Render |
|---|---|---|
| none (control) | 0 | vanilla |
| burst of 0.1 s | about 6 | vanilla |
| burst of 5 s | 291 | vanilla |
| continuous for 43 s | 2,478 | vanilla |
| continuous for 128 s, with a wetness threshold crossed on purpose | 6,648 | vanilla |

What follows from the two runs:

- Writing more often does not make the material stick. 6,648 continuous writes on a garment that never changed health level rendered nothing.
- The one event seen to install the override was a real health threshold crossing while the writes were running. The same crossing is also what clears an override that is already there.
- Once an override sticks it is sticky: it survived at least 97 s with no writes and one health step. A test that reuses one garment across arms therefore measures its own history. Start each arm with a new garment, and check the starting wetness and health level in the log.
- A write on the first tick after an observed health change rendered in the first run and did not in the second. Both are single samples and both stand as recorded.
- So worn clothing cannot be repainted on demand by writing a material. An effect that must appear when the player switches it on needs another route to rebuild the visual.

Routes that were ruled out, with the reason:

- `SwitchItemSelectionTextureEx` is a script hook with an empty body in `EntityAI`, not a native call (`P:\scripts\3_game\entities\entityai.c:1196`). Calling it rebuilds nothing. Vanilla calls it from the player's `EEItemAttached` (`P:\scripts\4_world\entities\manbase\playerbase.c:1507-1509`), so the rebuild that happens there is the attach itself.
- `SetSimpleHiddenSelectionState` cannot do it for body clothing, because those configs have no `simpleHiddenSelections` (see the first section).

When you measure this yourself, two failures give the same vanilla frame: "nothing refreshed" and "it refreshed, and the refresh wiped the override". Tell them apart by writing again after the cycle. The pass condition is a pair of frames, not one: the same entity and camera with the override kept, then cleared by a health step.

## The getter is not proof of what renders

**Measured in game** (2026-08-31), wrong in both directions within one run:

| `GetObjectMaterial` returned | The frame showed |
|---|---|
| `dz\data\data\mirror.rvmat` | a black vanilla shirt: the getter said the override was applied and it was not visible |
| an empty string | a shirt with the mirror material: the getter said it was absent and it was visible |

- To prove a material is applied, look at the frame. The getter reports the script's slot, which is a different thing from what renders. A check that reads the getter can pass on clothing that looks vanilla and fail on clothing that looks painted.
- The getter returned an empty string while the engine held its own material, not a vanilla path, and on the server it always returned empty: clothing material is client side.
- This does not weaken a result that was judged by pixels with a control pair.

## An empty texture hides the selection

`hiddenSelectionsTextures[]` with an empty string for a selection hides it. A script material applied to that selection then succeeds and still nothing renders.

- Vanilla uses the empty string to hide on purpose: `HideOnItem` clears the materials and textures of the light selections with `""` (`P:\scripts\4_world\entities\itembase\xmaslights.c:94-103`), and the blowtorch hides its flame with `SetObjectTexture(0, "")` (`P:\scripts\4_world\entities\itembase\blowtorch.c:50`).
- A selection whose material a script swaps must name its real texture in config. `BatteryCharger` does: every entry of its `hiddenSelectionsTextures[]` is `battery_charger_co.paa` (`P:\DZ\gear\camping\config.cpp:11118-11126`).
- Not verified in game: switching the selection to a bright procedural color, `#(argb,8,8,3)color(r,g,b,1,CO)`, to keep a glowing part visible over a dark area of the `_co`.

## A material cannot move a texture that a script assigns

**Measured in game** (DayZ 1.29, 2026-09-10), one variable changed on one selection. Two materials were identical except that one had a root level `uvSource="tex"` and a `uvTransform` with `pos[]={0.5,0.5,0}`. The same texture was applied with `SetObjectTexture` under both, and it rendered in the same place.

- The materials declared no `Stage0`, so the color texture was the face texture: the one from the `hiddenSelectionsTextures[]` slot or from `SetObjectTexture`. A root level `uvTransform` governs the stages the material declares, and the face texture does not pass through it.
- A design that pans or crops one large texture by swapping materials with different transforms does not work in this form.
- Not tested: whether the transform takes effect when the material carries the texture in its own `Stage0` and no script assigns one.
