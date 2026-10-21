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

`dBodyActive(ent, ActiveState)` wakes or sleeps a body: `INACTIVE`, `ACTIVE` or `ALWAYS_ACTIVE` (`P:\scripts\1_core\proto\enphysics.c:64`; enum at `P:\scripts\1_core\physics\activestate.c:9`). Vanilla wakes a vehicle this way when a base building part next to it changes (`P:\scripts\4_world\classes\constructionbase.c:284`).

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

## How vanilla drops and throws

- **Player throw.** Holding the throw button winds up a force from 0 to 1; on release the player calls `GetHumanInventory().ThrowEntity(item, direction, force)` with a force between `c_fThrowingForceMin = 20.0` and `c_fThrowingForceMax = 90.0` (`P:\scripts\4_world\entities\dayzplayerimplementthrowing.c:62`, `:261`, `:262`). The hand action then calls `item.ThrowPhysically(player, throwEvent.GetForce())` (`P:\scripts\3_game\systems\inventory\hand_actions.c:81`).
- **When a throw is refused.** No throw with the weapon raised, with no free space 0.7 m in front (`CheckFreeSpace(vector.Forward, 0.7, false)`), or with an item that uses the heavy hand profile (`P:\scripts\4_world\entities\dayzplayerimplementthrowing.c:187`, `:231`, `:252`). The heavy profile is `SetHeavyItems()` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:275`), registered per class name with `AddItemInHandsProfileIK`, for example `WoodenCrate` (`:854`). `Inventory_Base` gets a one handed default (`:373`). A mod class that inherits from a heavy vanilla class is expected to use that heavy profile; confirm it in game.
- **Making a resting item fall.** Vanilla calls `ThrowPhysically(null, vector.Zero)` on items and kits that must drop to the ground: items left floating when a base part is removed (`P:\scripts\4_world\classes\constructionbase.c:300`) and the shelter kit, which is spawned with `ECE_PLACE_ON_SURFACE` and then made to fall (`P:\scripts\4_world\entities\itembase\tentbase\shelter.c:61`, `:65`). The signature is `ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true)` (`P:\scripts\3_game\entities\inventoryitem.c:26`).
- **Snapping to the ground instead.** `PlaceOnSurface()` (`P:\scripts\3_game\entities\object.c:299`) moves the object onto the surface below it without simulating a fall. Vanilla uses it for locks and traps (`P:\scripts\4_world\entities\itembase\codelock.c:304`, `P:\scripts\4_world\entities\itembase\trapbase.c:551`).
- **Stopping a dropped item.** `ItemBase.StopItemDynamicPhysics()` sets `SetDynamicPhysicsLifeTime(0.01)` so the body settles at once (`P:\scripts\4_world\entities\itembase.c:4530`).

The native calls `CreateDynamicPhysics(int interactionLayers)`, `EnableDynamicCCD(bool state)` and `SetDynamicPhysicsLifeTime(float lifeTime)` are on `Object` (`P:\scripts\3_game\entities\object.c:456` to `:458`). No vanilla script calls the first two; prefer `ThrowPhysically`. The manual pattern, when you need it, is in `_shared/enscript/patterns/physics_items.md`.

## Fast bodies

A body that moves further in one simulation step than a wall or floor is thick can pass through it. Continuous collision detection catches this: `dBodyEnableCCD(body, maxMotion, sphereCastRadius)` turns it on when both values are 0 or more and off with `-1`; `maxMotion` should be a little less than the size of the geometry, and `sphereCastRadius` is the largest sphere that fits inside the body (`P:\scripts\1_core\proto\enphysics.c:76` to `:83`). For items there is `EnableDynamicCCD(true)` (`P:\scripts\3_game\entities\object.c:457`). Thicker Geometry is the better fix for a slow item; CCD is for small or fast ones.

## Falling through the floor: check in this order

1. The floor. If it is the mod's own model, run `/dayz-p3d-audit` on it: Geometry LOD present, components named and closed, faces have penetration materials (`collision-lods.md`). If it is vanilla, the floor is fine; look at the item.
2. The item's Geometry LOD and mass: `/dayz-p3d-audit` on the item's MLOD model (`mass-and-weight.md`).
3. The spawn: was it created with `ECE_CREATEPHYSICS` or `ECE_PLACE_ON_SURFACE`, or with `ECE_KEEPHEIGHT` inside the floor?
4. The body state: `dBodyIsSet`, `dBodyIsDynamic` and `GetSimulationState()` on a diag session.
5. Speed: a small item thrown hard at a thin floor needs thicker Geometry or CCD.
