# Placement, hologram and material slots

Which facts decide whether a kit can be placed and whether its recipe can ever be built: how much material a slot holds, how the hologram gets its green and red tint, what picks the carry pose and what a custom wall placement needs. Open it when a build action never appears, the hologram is not tinted, or an item is carried in the wrong pose.

## The slot decides how much material fits

For an item that can be split, `GetTargetQuantityMax` asks the slot first, through `InventorySlots.GetStackMaxForSlotId`, and only then falls back to the item's `varStackMax` and then to `varQuantityMax` (`P:\scripts\4_world\entities\itembase.c:3453` to `:3472`). An item that cannot be split skips the slot and uses `varQuantityMax`.

Vanilla sets the cap per slot in `CfgSlots`:

| Slot | `stackMax` | Source |
|---|---|---|
| `Material_WoodenPlanks` | 20 | `P:\scripts\config.cpp:2285` to `:2300` |
| `Material_MetalSheets` | 20 | `config.cpp:2285` to `:2300` |
| `Material_Nails` | 99 | `config.cpp:2277` to `:2284` |
| `Material_MetalWire` (fence) | none | `config.cpp:2309` to `:2315`, used at `P:\DZ\gear\camping\config.cpp:4373` |
| `Material_FPole_MetalWire` (flag pole) | none | `P:\scripts\config.cpp:2508` to `:2514`, used at `P:\DZ\gear\camping\config.cpp:12504` and `:12762` |

`MetalWire` can be split (`canBeSplit=1`, `varQuantityMax=50`, `varStackMax=1`, `P:\DZ\gear\crafting\config.cpp:376` to `:381`). Its two slots set no `stackMax`, so the cap falls back to `varStackMax=1` (`itembase.c:3464` and `:3465`): one wire per slot, not 50.

Read the cap from `CfgSlots`, not from the item. The item's class overstates plank capacity five times (100 against 20). A recipe that asks for more than the slot holds can never be built: the player fills the slot, never reaches the amount, and the build action never appears. Work out how many slots a material needs as the amount divided by the slot's `stackMax`, rounded up. A design that promises the same configurable range for every material, such as 1 to 100 of each, cannot work.

## The same fallback sets a crop's harvest

`PlantBase.Harvest` creates each crop with `SetQuantity(GetQuantityMax())` (`P:\scripts\4_world\entities\gardenbase\plantbase.c:574` and `:575`). For an item that can be split, `GetQuantityMax` resolves to `varStackMax` when the slot sets no cap (`itembase.c:3439` to `:3472`), so raising a crop's `varStackMax` changes the vanilla yield. `SetQuantity` clamps to the item's range (`itembase.c:3356`), so a scripted yield above the stack size is cut without a message unless the mod sets the harvest quantity itself.

## A tinted hologram needs two declarations

`Hologram.RefreshVisual` tints by calling `SetObjectTexture` and `SetObjectMaterial` on a hidden selection index (`P:\scripts\4_world\classes\hologram.c:1546` to `:1565`). `GetHiddenSelection` returns 0 when the name is missing (`:1523` to `:1531`), so a model with no `hiddenSelections[]` shows the ghost in its normal material, with no error.

The hologram looks for a hidden selection named `placing` when the model has a `Placing` animation, otherwise `inventory` (`hologram.c:40` to `:43` and `:178` to `:194`), and tints that selection's index when the config declares it. Vanilla traps declare `hiddenSelections[]={"placing"}` for this (`P:\DZ\gear\traps\config.cpp:106` to `:109`). Index 0, the first entry, is used only when neither name exists.

To get the tint:

- Declare `hiddenSelections[]`, `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` with the values the model already uses, so normal rendering does not change.
- Put the same selection in `sections[]` in `model.cfg`, or the swap has nothing to bind to.
- Declare `hologramMaterial` and `hologramMaterialPath`. `RefreshVisual` reads both keys and appends `_deployable.rvmat` or `_undeployable.rvmat` through `CorrectMaterialPathName` (`hologram.c:14` and `:15`, `:1554` to `:1557`, `:1570`); without them the hologram has no texture.

## The carry pose comes from the animation graph

`itemBehaviour` (`m_ItemBehaviour`, `P:\scripts\4_world\entities\itembasetype.c:33`: 0 heavy, 1 one handed, 2 two handed) drives behaviour rules and the deploy command, not the pose in hands. The pose comes from registering the class in the player's animation setup. Vanilla registers each heavy object with `pType.AddItemInHandsProfileIK(...)`, using `player_main_heavy.asi` and the `heavyItemBehaviour`: `Barrel_ColorBase` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:841`, `WoodenCrate` at `:854`.

A mod makes the same call in `ModItemRegisterCallbacks.RegisterHeavy`, an empty hook declared at `dayzplayercfgbase.c:317` and called after the vanilla list at `:1567`. With no registration the item falls back to the one handed `Inventory_Base` default whatever `itemBehaviour` says. The `.anm` file is an IK pose, not tied to a class, so reusing a vanilla one needs no new animation. Pick the value from the vanilla object you imitate: a cabinet is `0` like the barrel, not `2` like a small kit box.

## Placement actions come from the deployable subclass

`Container_Base` adds `ActionTogglePlaceObject` and `ActionPlaceObject` only in its deployable subclass `DeployableContainer_Base` (`P:\scripts\4_world\entities\itembase\container_base.c:32` and `:48` to `:54`), which `Barrel_ColorBase` inherits (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:1`). A storage object that extends `Container_Base` directly gets no placement, and `IsDeployable()` is `false` by default (`itembase.c:4352` to `:4355`). Add the two actions to the one class that needs them rather than changing a shared parent, which could change its siblings.

## Each placeable config class needs a script class

Give each placeable config class a script class of the same name that inherits from the kit or static base providing `SetActions`, `IsDeployable` and the link between kit and placed object. Check both halves before you look at the hologram or textures.

## A custom wall placement hologram

This is for a modded `Hologram.UpdateHologram`. It is mod code, not vanilla behaviour; only the cited vanilla lines are checked on `P:\`.

1. The wall normal. For an object hit, neither `RaycastRVProxy.dir` nor `RaycastRV.contactDir` is a face normal; both are the ray direction, so a yaw taken from them faces the camera and the ghost's box hits the wall at any angle. Take the normal from `DayZPhysics.RayCastBullet` on `PhxInteractionLayers.BUILDING`, and keep the fire geometry ray to identify the object (`_shared/enscript/depth/` covers raycasts). Not tested in game.
2. The ground. Take the nearest support at or below the aimed point, no more than 2 mm above it. A ray started 2 m above the point lands on sills, ledges and the floor above.
3. The collision box. Lift its bottom 5 cm as `IsCollidingBBox` does (`hologram.c:547` and `:556`), or every building floor blocks placement, and trim the back so the wall the object hangs on does not count.
4. Logging. Write one line per failure cause (wall, ground, spacing, player, water, box) when it changes, rate limited and under 255 characters, and query the unlifted box only while logging. That turns "the hologram is grey" into a named cause.

Points 2 to 4 were measured in game on a test object.
