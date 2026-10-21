# Color variants

Covers how one set of models carries every color through hidden selections, how vanilla names them, and how script changes them at run time.

## The vanilla pattern

A wearable has three models: one on the ground and one worn by each gender (see `models-and-proxies.md`). Vanilla gives each model its own hidden selection.

| Selection | Model it lives in | Checked in |
|---|---|---|
| `camoGround` | The ground model (`model=`) | `P:\DZ\characters\vests\plate_carrier_g.p3d` |
| `camoMale` | The male worn model (`ClothingTypes` `male=`) | `P:\DZ\characters\vests\plate_carrier_m.p3d` |
| `camoFemale` | The female worn model (`ClothingTypes` `female=`) | `P:\DZ\characters\vests\plate_carrier_f.p3d` |

The selection names were read from the vanilla models with a byte scan, since the models on `P:\` are binarized.

In config, the color base lists the selections once and each color lists one texture per selection, in the same order:

- `PlateCarrierVest_Black` sets `hiddenSelections[]` at `P:\DZ\characters\vests\config.cpp:197` and three copies of `BallisticVest_black_co.paa` at `:203` to `:207`.
- `UKAssVest_ColorBase` sets `hiddenSelections[]` once (`P:\DZ\characters\vests\config.cpp:896`), and each color such as `UKAssVest_Black` sets only `scope=2` and `hiddenSelectionsTextures[]` (`:1011` to `:1019`).
- The ground texture may differ from the worn one. `SmershVest` uses `smersh_g_co.paa` for `camoGround` and `smersh_co.paa` for the two worn selections (`P:\DZ\characters\vests\config.cpp:578` to `:582`).

`hiddenSelectionsMaterials[]` swaps the `.rvmat` the same way, one entry per selection. Vanilla uses it on body parts, for example `MaleAdamTorso` at `P:\DZ\characters\tops\config.cpp:52`.

## Skin showing through: `personality`

`TShirt_ColorBase` lists a fourth selection, `personality`, after the three camo selections (`P:\DZ\characters\tops\config.cpp:2269`), while each color lists only three textures (`TShirt_Beige` at `:2360`). The script fills `personality` with the wearer's skin: `Clothing.SwitchItemSelectionTextureEx` finds the selection (`P:\scripts\4_world\entities\itembase\clothing_base.c:140`) and copies the material and texture of the player's empty hands into it. A worn model with bare skin (arms on a T-shirt) names that area `personality` so it matches every character.

## Checks before you hand back

1. Every name in `hiddenSelections[]` is a named selection in the model it belongs to. Ask the Object Builder specialist to confirm the names in the mod's own models.
2. `hiddenSelectionsTextures[]` has one entry per camo selection, in the same order, and each path exists under the mod's `$PBOPREFIX$` or under `P:\DZ\`.
3. Color textures end in `_co` and are packed with `/dayz-pack-texture`.
4. Only the color classes have `scope=2`; the color base stays at `scope=0` so it never spawns.
5. **Engine:** a hidden selection must be present in every visual LOD of a model, or that LOD keeps its original texture. Say so in the notes for Object Builder.

## Changing a color from script

| Call | What it does | Where |
|---|---|---|
| `GetHiddenSelectionIndex(string selection)` | Index of a name in `hiddenSelections[]`, or -1. | `P:\scripts\3_game\entities\entityai.c:2778` |
| `SetObjectTexture(int index, string texture_name)` | Changes the texture of one hidden selection. | `:2881` |
| `SetObjectMaterial(int index, string mat_name)` | Changes the material of one hidden selection. | `:2884` |
| `HiddenSelectionsData` | Reads `hiddenSelections`, `hiddenSelectionsTextures` and `hiddenSelectionsMaterials` from config for a type. | `P:\scripts\3_game\hiddenselectionsdata.c:1` |

Prefer config colors. Script color changes are for items that change at run time, and that code belongs to the script team.
