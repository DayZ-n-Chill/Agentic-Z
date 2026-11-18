# Dropping and throwing

Covers how an object gets a physics body, how the player and vanilla scripts drop and throw items, and why an item floats, freezes or falls through a floor.

## Static or dynamic

A body can exist in the collision world without being simulated. Check its state before you blame the model.

| Query | Answers | Source |
|---|---|---|
| `dBodyIsSet(ent)` | Has the entity a physics body at all | `P:\scripts\1_core\proto\enphysics.c:57` |
| `dBodyIsDynamic(ent)` | Is the body simulated (dynamic) or static | `P:\scripts\1_core\proto\enphysics.c:66` |
| `obj.GetPhysics().GetSimulationState()` | `NONE` (in neither world), `COLLISION` (collides but is not simulated) or `SIMULATION` | `P:\scripts\1_core\physics\physics.c:53`; enum at `P:\scripts\1_core\physics\simulationstate.c:12` |
| `dBodyIsActive(ent)` | Is a dynamic body awake | `P:\scripts\1_core\proto\enphysics.c:68` |

`dBodyActive(ent, ActiveState)` wakes or sleeps a body: `INACTIVE`, `ACTIVE` or `ALWAYS_ACTIVE` (`P:\scripts\1_core\proto\enphysics.c:64`; enum at `P:\scripts\1_core\physics\activestate.c:9`). Vanilla wakes a vehicle this way when a base building part next to it changes (`P:\scripts\4_world\classes\constructionbase.c:342`).

## Spawn flags

`CreateObjectEx` flags decide whether a new object gets collision at all (`P:\scripts\3_game\ce\centraleconomy.c`):

| Flag | Value | Meaning |
|---|---|---|
| `ECE_TRACE` | 4 | Trace down from the spawn point when placing (`:10`) |
| `ECE_CREATEPHYSICS` | 1024 | "create collision envelope and related physics data (if object has them)" (`:17`) |
| `ECE_KEEPHEIGHT` | 524288 | Keep the given height, no trace or surface placement (`:28`) |
| `ECE_IN_INVENTORY` | 787456 | `ECE_CREATEPHYSICS`, `ECE_KEEPHEIGHT` and `ECE_NOSURFACEALIGN` (`:37`) |
| `ECE_PLACE_ON_SURFACE` | 1060 | `ECE_CREATEPHYSICS`, `ECE_UPDATEPATHGRAPH` and `ECE_TRACE` (`:38`) |

An object spawned without `ECE_CREATEPHYSICS` has no collision envelope, so nothing rests on it and it rests on nothing. An item spawned with it can still be static and hang where it was created; make it fall as below.

Map objects are static too. The train wagon wrecks such as `StaticObj_Wreck_Train_Wagon_Flat` and `StaticObj_Wreck_Train_Wagon_Tanker` inherit `HouseNoDestruct` (`P:\DZ\structures\wrecks\config.cpp:1588`, `:1593`), and an impulse on them was discarded in a mod test (measured, not checkable on `P:\`). To knock one over, catch the hit in `OnContact` on your own moving entity and replace the wreck with a dynamic entity of your own. Removing a map object has to reach every client as well as the server, so prove the swap in the in game test.

## How vanilla drops and throws

- **Player throw.** Holding the throw button winds up a force from 0 to 1; on release the player calls `GetHumanInventory().ThrowEntity(item, direction, force)` with a force between `c_fThrowingForceMin = 20.0` and `c_fThrowingForceMax = 90.0` (`P:\scripts\4_world\entities\dayzplayerimplementthrowing.c:62`, `:261`, `:262`). The hand action then calls `item.ThrowPhysically(player, throwEvent.GetForce())` (`P:\scripts\3_game\systems\inventory\hand_actions.c:81`).
- **When a throw is refused.** No throw with the weapon raised, with no free space 0.7 m in front (`CheckFreeSpace(vector.Forward, 0.7, false)`), or with an item that uses the heavy hand profile (`P:\scripts\4_world\entities\dayzplayerimplementthrowing.c:187`, `:214`, `:231`, `:252`). The heavy profile is `SetHeavyItems()` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:275`), registered per class name with `AddItemInHandsProfileIK`, for example `WoodenCrate` (`:854`). `Inventory_Base` gets a one handed default (`:373`). A mod class that inherits from a heavy vanilla class is expected to use that heavy profile; confirm it in game.
- **Making a resting item fall.** Vanilla calls `ThrowPhysically(null, vector.Zero)` on items and kits that must drop to the ground: items left floating when a base part is removed (`P:\scripts\4_world\classes\constructionbase.c:358`) and the shelter kit, which is spawned with `ECE_PLACE_ON_SURFACE` and then made to fall (`P:\scripts\4_world\entities\itembase\tentbase\shelter.c:61`, `:65`). The admin tools spawn items with gravity the same way, `item.ThrowPhysically(null, "0 0 0")` on the server (`P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:430`, `:553`). The signature is `ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true)` (`P:\scripts\3_game\entities\inventoryitem.c:26`).
- **Snapping to the ground instead.** `PlaceOnSurface()` (`P:\scripts\3_game\entities\object.c:299`) moves the object onto the surface below it without simulating a fall. Vanilla uses it for locks and traps (`P:\scripts\4_world\entities\itembase\codelock.c:325`, `P:\scripts\4_world\entities\itembase\trapbase.c:551`).
- **Stopping a dropped item.** `ItemBase.StopItemDynamicPhysics()` sets `SetDynamicPhysicsLifeTime(0.01)` so the body settles at once and clears the flag `m_ItemBeingDroppedPhys` (`P:\scripts\4_world\entities\itembase.c:4534` to `:4538`; the flag at `:59`).
- **Where the throw is simulated.** `HandActionThrow` calls `ThrowPhysically` only when the player's instance type is not `INSTANCETYPE_REMOTE` (`P:\scripts\3_game\systems\inventory\hand_actions.c:77`), so the body exists on the server and on the thrower's own client. That is why a thrown item collides for the thrower. A mod that throws an item itself and needs the owner to collide with it copies that guard. What other clients simulate is not visible in script.
- **Emptying an inventory.** `ThrowEntityFromInventory` calls `ThrowPhysically(null, force, false)`, so the items do not collide with characters (`P:\scripts\4_world\static\miscgameplayfunctions.c:1329`, `:1345`, `:1353`); an entity that is not an `ItemBase` gets `dBodyApplyImpulse(entity, force)` instead (`:1359`).
- **Drop physics has a lifetime.** The dynamic body made by a drop or throw is temporary; `SetDynamicPhysicsLifeTime` sets how long it lasts. Measured in game; not checkable on `P:\`: the default is 15 s, after which `dBodyIsDynamic` turns false, and `SetDynamicPhysicsLifeTime(3600)` was honored. An item that must keep rolling longer has to extend it.
- **Setting the body up again.** `ItemBase.OnCreatePhysics()` calls `RefreshPhysics()` (`P:\scripts\4_world\entities\itembase.c:1150` to `:1155`), which tents, fireplaces, kits, the Hesco box and the battery charger override (`P:\scripts\4_world\entities\itembase\tentbase.c:162`; `P:\scripts\4_world\entities\itembase\fireplacebase\fireplace.c:479`; `P:\scripts\4_world\entities\itembase\kitbase.c:96`; `P:\scripts\4_world\entities\itembase\hescobox.c:124`; `P:\scripts\4_world\entities\itembase\batterycharger.c:365`).

The native calls `CreateDynamicPhysics(int interactionLayers)`, `EnableDynamicCCD(bool state)` and `SetDynamicPhysicsLifeTime(float lifeTime)` are on `Object` (`P:\scripts\3_game\entities\object.c:456` to `:458`). No vanilla script calls the first two; prefer `ThrowPhysically`. The manual pattern, when you need it, is in `_shared/enscript/patterns/physics_items.md`. `InventoryItem.ForceFarBubble(bool state)` makes the item use the server's `networkRangeFar` instead of `networkRangeNear`, which matters for an item thrown far; it has no effect when the config `forceFarBubble` is already set (`P:\scripts\3_game\entities\inventoryitem.c:28` to `:31`).

For an item that must block or hit players and keep rolling, the native path in one place (run it where vanilla runs a throw, on the server and the owner client; confirm the lifetime in game):

```c
item.ThrowPhysically(null, impulse, true);   // true: collides with characters
item.EnableDynamicCCD(true);
item.SetDynamicPhysicsLifeTime(3600);
```

The model still needs a Geometry LOD for collision, a View Geometry LOD for the action cursor and a Fire Geometry LOD for bullets (`collision-lods.md`).

## Fast bodies

A body that moves further in one simulation step than a wall or floor is thick can pass through it. Continuous collision detection catches this: `dBodyEnableCCD(body, maxMotion, sphereCastRadius)` turns it on when both values are 0 or more and off with `-1`; `maxMotion` should be a little less than the size of the geometry, and `sphereCastRadius` is the largest sphere that fits inside the body (`P:\scripts\1_core\proto\enphysics.c:76` to `:83`). For items there is `EnableDynamicCCD(true)` (`P:\scripts\3_game\entities\object.c:457`). Thicker Geometry is the better fix for a slow item; CCD is for small or fast ones.

## Falling through the floor: check in this order

1. The floor. If it is the mod's own model, run `/dayz-p3d-audit` on it: Geometry LOD present, components named and closed, faces have penetration materials (`collision-lods.md`). If it is vanilla, the floor is fine; look at the item.
2. The item's Geometry LOD and mass: `/dayz-p3d-audit` on the item's MLOD model (`mass-and-weight.md`).
3. The spawn: was it created with `ECE_CREATEPHYSICS` or `ECE_PLACE_ON_SURFACE`, or with `ECE_KEEPHEIGHT` inside the floor?
4. The body state: `dBodyIsSet`, `dBodyIsDynamic` and `GetSimulationState()` on a diag session.
5. Speed: a small item thrown hard at a thin floor needs thicker Geometry or CCD.
