# Collision LODs

Covers which model LOD does which physical job, the rules each collision LOD must follow, and how to probe each one from script to prove where a fault is.

The LOD resolution values are in the table in `_shared/conventions/assets.md` (Tier 2). Do not use Arma 3 values. The silent model faults behind most collision bugs are in `dayz-p3d-audit/references/p3d-killers.md`; this file points to its sections rather than repeating them.

## Which LOD does what

| LOD | Physical job | When it is missing or broken |
|---|---|---|
| Geometry | The physics body: what items rest on, what players and vehicles bump into, and where the mass lives | Items fall through it, players walk through it, the body has no mass |
| Fire Geometry | What bullets and other projectiles hit | Bullets pass through; damage zones get no hits |
| View Geometry | What the action cursor and view checks hit | No action prompt on the object |
| Memory | Points such as `pos center`; not a collision LOD | Placed objects sit at the wrong height |

The jobs in this table are **model knowledge**. The script side confirms the split: raycasts and box checks choose a LOD with `ObjIntersectFire` (0), `ObjIntersectView` (1) or `ObjIntersectGeom` (2) (`P:\scripts\3_game\global\dayzphysics.c:67` to `:69`).

## Rules for the collision LODs

These come from the model pack (`skills/_shared/models/`) and the audit references. Check them on the mod's MLOD model with `/dayz-p3d-audit`; never on a vanilla ODOL model.

- The Geometry LOD exists and carries the mass (`p3d-killers.md` section 4; the audit prints the mass, see `mass-and-weight.md`).
- Each component in Geometry, Fire Geometry and View Geometry is closed and convex, named `Component01`, `Component02` and so on with a capital C (`p3d-killers.md` sections 2, 8 and 9).
- Every face in a collision LOD has a penetration material, or bullets and footsteps find no surface (`p3d-killers.md` section 10).
- `autocenter = 0` is for placed objects only, never kits or handheld items, which then float when dropped (`p3d-killers.md` section 3 and the autocenter rule in `skills/_shared/models/named-properties.md`).
- A thin wall or floor needs real thickness in the Geometry LOD. A body that moves further in one step than the wall is thick can pass through it; see "Fast bodies" in `drop-and-throw.md`.

## Fire Geometry and damage zones

- The audit reports a missing Fire Geometry LOD as `NOTE: Missing FireGeo LOD (res ~7e15). No ballistic damage zones.` (`skills/dayz-p3d-audit/scripts/audit_p3d.py`, `check_required_lods`).
- In config, each damage zone lists the model selections it covers in `componentNames[]`, for example `MediumTent` zone `Body` with `componentNames[]={"body"}` (`P:\DZ\gear\camping\config.cpp:242`). These names must match the selection names in the model exactly. The audit prints each LOD's selections (`sels=[...]`), so compare that list with the config.
- The Fire Geometry is not the Geometry LOD. A model can stop players and still let bullets through, or the other way round, so test both.

## Probing a LOD from script

Use these on a diag session to prove which LOD is hit before you hand a fix on.

- `DayZPhysics.RaycastRV(begPos, endPos, out contactPos, out contactDir, out contactComponent, results, with, ignore, sorted, ground_only, iType, radius, flags)` (`P:\scripts\3_game\global\dayzphysics.c:199`). Pass `ObjIntersectFire` as `iType` to test the Fire Geometry, `ObjIntersectGeom` for the Geometry LOD. Vanilla placement probes the ground this way with `ObjIntersectFire` (`P:\scripts\4_world\classes\hologram.c:683`).
- `GetGame().IsBoxCollidingGeometry(center, orientation, edgeLength, ObjIntersectFire, ObjIntersectGeom, excluded, collided)` tests a box against two LOD kinds at once (`P:\scripts\4_world\classes\hologram.c:566`).
- `DayZPhysics.RayCastBullet(begPos, endPos, layerMask, ignoreObj, out hitObject, out hitPosition, out hitNormal, out hitFraction)` casts against physics layers instead of LODs (`P:\scripts\3_game\global\dayzphysics.c:211`). Layer names are in the `PhxInteractionLayers` enum (`:1`), including `FIREGEOM` (`:17`).
- Bounds: `GetCollisionBox(out vector minMax[2])` (`P:\scripts\3_game\entities\object.c:370`) and `GetBounds(out vector mins, out vector maxs)` (`P:\scripts\1_core\proto\enentity.c:595`). A collision box of zero size or one far from the visual model points at a missing or misplaced Geometry LOD.

## Placement checks are not physics

When a player places an object, `Hologram` decides if the spot is valid. It reads `slopeTolerance` and `yawPitchRollLimit` from the class (`P:\scripts\4_world\classes\hologram.c:139`, `:151`; `WoodenCrate` sets them at `P:\DZ\gear\camping\config.cpp:10165`, `:10166`) and tests a box against the Fire and Geometry LODs of nearby objects (`hologram.c:566`). Server owners can switch these checks off in cfggameplay, for example `disableIsCollidingBBoxCheck` (`P:\scripts\3_game\cfggameplaydatajson.c:242`). A red hologram is a placement question for dayz-config-specialist; a placed object that then falls or sinks is a physics question.
