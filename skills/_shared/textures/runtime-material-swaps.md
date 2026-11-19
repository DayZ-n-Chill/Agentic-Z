# Material and texture swaps at run time

What changes an item's material or texture while the game runs: the engine's health levels, the script calls, and what happens when a script repaints worn clothing. Read it before writing thermal vision, camouflage, team marking or any effect that calls `SetObjectMaterial`.

## Contents

- [The calls and their two index spaces](#the-calls-and-their-two-index-spaces)
- [Health levels swap materials in the engine](#health-levels-swap-materials-in-the-engine)
- [Wetness does not repaint clothing](#wetness-does-not-repaint-clothing)
- [A script material on worn clothing](#a-script-material-on-worn-clothing)
- [The getter is not proof of what renders](#the-getter-is-not-proof-of-what-renders)
- [An empty texture hides the selection](#an-empty-texture-hides-the-selection)
- [A material cannot move a texture that a script assigns](#a-material-cannot-move-a-texture-that-a-script-assigns)

## The calls and their two index spaces

Two families of calls exist, and each indexes a different config array.

| Call | Indexes | Vanilla declaration |
|---|---|---|
| `SetObjectTexture`, `GetObjectTexture` | `hiddenSelections[]` | `P:\scripts\3_game\entities\entityai.c:2881` ("Change texture in hiddenSelections") |
| `SetObjectMaterial`, `GetObjectMaterial` | `hiddenSelections[]` | `entityai.c:2884` ("Change material in hiddenSelections") |
| `SetSimpleHiddenSelectionState`, `IsSimpleHiddenSelectionVisible` | `simpleHiddenSelections[]` | `entityai.c:2877` ("Simple hidden selection state; 0 == hidden") |

- `GetHiddenSelectionIndex` returns an index into `hiddenSelections[]` only; its own comment says so (`P:\scripts\3_game\entities\entityai.c:2778`). Use it for the texture and material calls.
- `GetHiddenSelectionIndex`, `GetHiddenSelectionsTextures` and `GetHiddenSelectionsMaterials` read a copy of the config arrays that the `EntityAI` constructor builds once (`P:\scripts\3_game\entities\entityai.c:238`), and only from `CfgVehicles <type>` (`P:\scripts\3_game\hiddenselectionsdata.c:11` to `:13`). They return the config values, never what a script set since. A class under `CfgWeapons` or `CfgMagazines` finds nothing under that path, so the index is -1; read its arrays with `ConfigGetTextArray` on the entity, as `Weapon_Base` does below.
- For the simple calls, read the other array and search it by name. Vanilla does both steps, the guard and the lookup, with `ConfigIsExisting("simpleHiddenSelections")` and `ConfigGetTextArray` (`P:\scripts\4_world\entities\firearms\weapon_base.c:94` to `:99`). The member it fills carries the comment "index in simpleHiddenSelections cfg array" beside `m_weaponHideBarrelIdx` (`weapon_base.c:62`).
- The head class does the same lookup with `ConfigGetTextArray` (`P:\scripts\4_world\entities\manbase\bodyparts\head.c:20`), and the binoculars action has the guard alone, `ConfigIsExisting("simpleHiddenSelections")` in `EnterOptics` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionviewbinoculars.c:35`).
- Vanilla never feeds one space into the other. Of the 32 lines in `P:\scripts` that call the simple pair (two more are commented out), none passes `GetHiddenSelectionIndex`. They use fixed numbers such as `SIMPLE_SELECTION_MELEE_RIFLE` (`P:\scripts\3_game\dayzplayer.c:1173`), stored members such as `m_magazineSimpleSelectionIndex` (`P:\scripts\4_world\entities\firearms\weapon_base.c:2136`), or a getter such as `GetHairIndex` (`P:\scripts\4_world\entities\manbase\playerbase.c:9407`).
- Passing a `GetHiddenSelectionIndex` result to `SetSimpleHiddenSelectionState` crashes the client natively, with a minidump and no script trace (**measured in game**).

Body clothing has no simple selections. Under `P:\DZ\characters` only four `config.cpp` files declare `simpleHiddenSelections`: `heads` (3 times), `headgear` (2), `data` (2) and `glasses` (1). The tops, pants, vests, gloves, shoes, belts, backpacks and masks configs declare none, so the simple calls cannot hide part of a shirt. They still work on headgear and glasses, with the guard above.

The `proto native` lines of `entityai.c` and `object.c` hold no other calls for textures, materials or simple selections. There is no general "refresh the visuals" call.

`SetObjectTexture` changes the texture only on the machine that calls it. To show a skin to every player, ship the textures in the PBO through `hiddenSelectionsTextures[]`, sync only the chosen index (net sync or RPC), and let each client call `SetObjectTexture(i, textures[index])` itself (measured in a mod).

What a mod cannot do with images at run time, checked across `P:\scripts`, Community Framework and Dabs Framework, none of which has a capture or readback call:

- Read the screen or a render back into script.
- Call a native DLL. `CallExtension` is an Arma 3 call and appears nowhere in `P:\scripts`.
- Save a screenshot through `Workspace.SaveScreenshot`, which does not exist. `MakeScreenshot` is still declared (`P:\scripts\1_core\proto\proto.c:142`) but has not worked since DayZ 1.19 (**measured in game**).
- Create a render to texture (`r2t`) surface from script. Those are declared in config and tied to memory points.

An image a mod must show reaches the client as a file and is loaded into an `ImageWidget` with `LoadImageFile` (`P:\scripts\1_core\proto\enwidgets.c:257`).

## Health levels swap materials in the engine

`healthLevels[]` in an item's `DamageSystem` maps health thresholds to materials. For `TShirt_ColorBase` it sits at `P:\DZ\characters\tops\config.cpp:2283` to `:2330`, with two materials per level, one for the worn model and one for the ground model: `1` and `0.7` give `tshirt.rvmat` and `tshirt_ground.rvmat`, `0.5` and `0.3` their `_damage` files, and `0` their `_destruct` files.

- The engine applies the swap, not script. `GetHealthLevel` is `proto native` (`P:\scripts\3_game\entities\object.c:1171`), and the only lines in `P:\scripts` that name the config array are three comments in that file. Searching the scripts for whatever writes the material finds nothing, and that does not mean nothing writes it.
- `EEHealthLevelChanged` runs on the client: the vanilla body in `Clothing_Base` is guarded by `IsHeadlessOrDedicatedServer` and does only client work (`P:\scripts\4_world\entities\itembase\clothing_base.c:111` to `:125`).
- Crossing a health threshold wipes a script material override on the next frame, because the engine writes its own material after `EEHealthLevelChanged` has run. Inside the hook the getter still returns the script's material; one tick later it is empty. Applying the override again inside the hook is therefore lost (**measured in game**).

Leave the `personality` selection alone when you repaint clothing. Vanilla already writes a material and a texture there with `SetObjectMaterial` and `SetObjectTexture` (`P:\scripts\4_world\entities\itembase\clothing_base.c:155` and `:156`).

## Wetness does not repaint clothing

The four wetness thresholds are `STATE_DRENCHED`, `STATE_SOAKING_WET`, `STATE_WET` and `STATE_DAMP` (`P:\scripts\3_game\constants.c:933` to `:936`). No vanilla clothing material follows them:

- The one vanilla material swap by wetness is the garden plot, and it is done in script with `SetObjectMaterial` (`P:\scripts\4_world\entities\gardenbase.c:605` to `:610`).
- Under `P:\DZ\characters` no file has `wet` in its name, against 353 `*damage*.rvmat` files.
- A script override stays in place while a worn item crosses all four wetness thresholds (**measured in game**).

## A script material on worn clothing

All of this section is **measured in game** in the DayZ client. The test override was `dz\data\data\mirror.rvmat` on the camo selections, because it reads as on or off to the eye: `specular[]={2,2,2,0}` on a dark diffuse (`P:\DZ\data\data\mirror.rvmat:5`).

A first run on one garment suggested write frequency matters:

| Writes of `SetObjectMaterial` | Result |
|---|---|
| 1, right after a health level change | rendered (not reproduced in the second run) |
| 1, about 50 s after the last state change | did not render, with valid indexes |
| about 19 per second, sustained | rendered at health levels 0, 2 and 4, stable |
| writing stopped | the material stayed |

A second run, each arm on a new garment made with `CreateAttachment` and with no health level change, shows it does not:

| Treatment | Writes | Render |
|---|---|---|
| none (control) | 0 | vanilla |
| burst of 0.1 s | about 6 | vanilla |
| burst of 5 s | 291 | vanilla |
| continuous for 43 s | 2,478 | vanilla |
| continuous for 128 s, crossing a wetness threshold on purpose | 6,648 | vanilla |

What follows:

- Writing more often does not make the material stick; 6,648 writes on a garment that never changed health level rendered nothing.
- The one event seen to install the override is a real health threshold crossing while the writes are running. The same crossing also clears an override that is already there.
- Once an override sticks, it stays: it survived at least 97 s with no writes and one health step. A test that reuses one garment across arms measures its own history, so start each arm with a new garment and log its starting wetness and health level.
- A write on the first tick after a health change rendered in one run and not in the other. Both are single samples.
- So worn clothing cannot be repainted on demand by writing a material. An effect the player switches on needs another way to rebuild the visual.

Two routes do not help:

- `SwitchItemSelectionTextureEx` is a script hook with an empty body in `EntityAI`, not a native call (`P:\scripts\3_game\entities\entityai.c:1196`), so calling it rebuilds nothing. Vanilla calls it from the player's `EEItemAttached` (`P:\scripts\4_world\entities\manbase\playerbase.c:1507` to `:1509`); the rebuild there comes from the attach itself.
- `SetSimpleHiddenSelectionState` cannot do it on body clothing, whose configs have no `simpleHiddenSelections` (first section).

When you test this yourself, two failures give the same vanilla frame: nothing refreshed, or it refreshed and the refresh wiped the override. Tell them apart by writing again after the cycle. A pass is a pair of frames, not one: the same entity and camera with the override kept, then cleared by a health step.

## The getter is not proof of what renders

Within one run the getter was wrong in both directions (**measured in game**):

| `GetObjectMaterial` returned | The frame showed |
|---|---|
| `dz\data\data\mirror.rvmat` | a black vanilla shirt: applied by the getter, not visible |
| an empty string | a shirt with the mirror material: absent by the getter, visible |

- To prove a material is applied, look at the frame. The getter reports the script's slot, which is not what renders, so a check that reads it can pass on clothing that looks vanilla and fail on clothing that looks painted.
- The getter returns an empty string while the engine holds its own material, not a vanilla path, and on the server it always returns empty: clothing material is client side.
- A result judged by pixels against a control pair stands regardless.

## An empty texture hides the selection

An empty string in `hiddenSelectionsTextures[]` hides that selection. A script material applied to it then succeeds and still nothing renders.

- Vanilla uses the empty string to hide on purpose: `HideOnItem` clears the materials and textures of the light selections with `""` (`P:\scripts\4_world\entities\itembase\xmaslights.c:94` to `:103`), and the blowtorch hides its flame with `SetObjectTexture(0, "")` (`P:\scripts\4_world\entities\itembase\blowtorch.c:50`). The armband shows one set of camo selections by writing back its config texture and hides the other with `""` (`P:\scripts\4_world\entities\itembase\clothing\armband_colorbase.c:81` and `:87`).
- A selection whose material a script swaps must name its real texture in config. `BatteryCharger` does: every entry of its `hiddenSelectionsTextures[]` is `battery_charger_co.paa` (`P:\DZ\gear\camping\config.cpp:11128` to `:11136`).
- A procedural color is a valid `SetObjectTexture` argument: vanilla dyes an item by writing `#(argb,8,8,3)color(r,g,b,a,CO)` to its `personality` selection (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:603`; the string is built at `P:\scripts\4_world\static\miscgameplayfunctions.c:245`). Unverified (not tested in game): that a bright one keeps a glowing part visible over a dark area of the `_co`.

## A material cannot move a texture that a script assigns

Two materials identical except that one has a root level `uvSource="tex"` and a `uvTransform` with `pos[]={0.5,0.5,0}` show the same texture, applied with `SetObjectTexture`, in the same place (**measured in game**, DayZ 1.29, one variable changed on one selection).

- The materials declare no `Stage0`, so the color is the face texture: the one from the `hiddenSelectionsTextures[]` slot or from `SetObjectTexture`. A root level `uvTransform` governs the stages a material declares, and the face texture does not pass through it.
- A design that pans or crops one large texture by swapping between materials with different transforms does not work this way.
- Not tested: whether the transform applies when the material carries the texture in its own `Stage0` and no script assigns one.
