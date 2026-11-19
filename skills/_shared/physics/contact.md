# Contact

Covers what happens when bodies touch: the contact event and its data, item impact sounds, how players, animals and vehicles react to being hit, collisions with characters, and pushing.

## The contact event

- The event is `EOnContact(IEntity other, Contact extra)` (`P:\scripts\1_core\proto\enentity.c:213`), raised for `EntityEvent.CONTACT` (`:97`).
- Turn it on with `SetEventMask(EntityEvent.CONTACT)` (`P:\scripts\1_core\proto\enentity.c:701`). Vanilla does this in the constructor of `DayZAnimal` (`P:\scripts\3_game\entities\dayzanimal.c:692`), `ZombieBase` (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:50`), `DayZPlayerImplement` (`P:\scripts\4_world\entities\dayzplayerimplement.c:174`) and items with their own contact logic such as `EasterEgg` (`P:\scripts\4_world\entities\itembase\gear\consumables\easteregg.c:40`).
- `ItemBase` overrides `EOnContact` (`P:\scripts\4_world\entities\itembase.c:1119`) while its constructor sets only `EntityEvent.INIT` (`:127`). An item class that needs its own contact logic sets `EntityEvent.CONTACT` itself, as `EasterEgg` does, and calls `super.EOnContact` so the impact sound still plays.
- Contact needs a physics body. When no event arrives, check `dBodyIsSet` and the Geometry LOD first (`drop-and-throw.md`, `collision-lods.md`).

## What a contact carries

The `Contact` class (`P:\scripts\1_core\physics\contact.c:9`) has, among others:

| Field | Meaning | Line |
|---|---|---|
| `Physics1`, `Physics2` | The two bodies | `:14` |
| `Material1`, `Material2` | Surface properties of each | `:17` |
| `Impulse` | Impulse applied to resolve the collision | `:21` |
| `Normal` | Collision axis at the contact point | `:27` |
| `Position` | Contact point in world space | `:29` |
| `PenetrationDepth` | How far object 1 went in | `:31` |
| `RelativeVelocityBefore` | Relative velocity before the hit | `:35` |
| `VelocityBefore1` | Object 1 velocity before the hit, world space | `:39` |
| `ShapeIndex1`, `ShapeIndex2` | Which geometry of each body touched | `:23`, `:25` |
| `RelativeNormalVelocityBefore`, `RelativeNormalVelocityAfter`, `RelativeVelocityAfter`, `VelocityAfter1`, `VelocityAfter2` | The same values along the normal, and after the hit | `:33` to `:45` |
| `GetNormalImpulse()`, `GetRelativeVelocityBefore(vel)`, `GetRelativeVelocityAfter(vel)` | Native helpers | `:47` to `:49` |

Use `Impulse` for "how hard" and `RelativeVelocityBefore.Length()` for "how fast". A `Contact` can only be received: its constructor and destructor are private (`P:\scripts\1_core\physics\contact.c:11`, `:12`).

## Handling a contact once per tick

`EOnContact` can fire several times in one tick. Two vanilla shapes keep the work to one pass:

- **The fireplace** registers `CONTACT | TOUCH` (`P:\scripts\4_world\entities\itembase\fireplacebase\fireplace.c:17`), sets a flag in its contact handler only on the server, while its body is active and it is not being deleted (`dBodyIsActive(this)`, `:62`), and does the work in `EOnPostSimulate` (`:66`).
- **Vehicles** keep the first contact of a tick in a cache and process it in `EOnPostSimulate` (below).

## Item impact sounds

- `InventoryItem` picks a sound table from the `soundImpactType` config key, default `"default"` (`P:\scripts\3_game\entities\inventoryitem.c:118` to `:122`).
- `ProcessImpactSoundEx` plays nothing below 0.3 m/s relative speed (`P:\scripts\3_game\entities\inventoryitem.c:203`) and finds the surface with `DayZPhysics.GetHitSurfaceAndLiquid` (`P:\scripts\3_game\global\dayzphysics.c:206`).
- `ItemBase.EOnContact` feeds it the config `weight` (`P:\scripts\4_world\entities\itembase.c:1125`). On a liquid surface the sound plays once and then stops (`:1137`).
- Vanilla sizes an impact by speed, `extra.RelativeVelocityBefore.Length()` (`P:\scripts\3_game\entities\inventoryitem.c:202`), and skips a repeat inside `SOUND_CONTACT_SKIP`, 0.33 s (`:3`, checked at `:207`).

## Players, animals and vehicles

- Players, infected (`ZombieBase.EOnContact`, `P:\scripts\4_world\entities\creatures\infected\zombiebase.c:1030` to `:1043`) and animals react to being hit by a vehicle in `EOnContact`: on the server they call `RegisterTransportHit(transport)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3958`, `P:\scripts\3_game\entities\dayzanimal.c:942`). `EntityAI.RegisterTransportHit` (`P:\scripts\3_game\entities\entityai.c:4134`) works out the damage from the vehicle's velocity, and pushes the body with `dBodyApplyImpulse` only when the hit kills it (`:4158` to `:4163`).
- A vehicle gets `OnContact(string zoneName, vector localPos, IEntity other, Contact data)` per damage zone hit (`P:\scripts\3_game\vehicles\transport.c:318`). `CarScript` turns the contact impulse into damage with `m_dmgContactCoef`, `0.058` by default (`P:\scripts\4_world\entities\vehicles\carscript.c:224`, used at `:1291`).
- The "impulse" a vehicle stores is its own change of momentum, `GetMomentum() - m_MomentumPrevTick` (`P:\scripts\3_game\vehicles\transport.c:334`), not `Contact.Impulse`, which vanilla only logs in a diag build (`:326`). When the direction of travel reversed in the hit (the dot product of the old and new velocity directions is below 0), the whole previous momentum is used instead (`:335` to `:339`). Only the first contact of a tick is kept (`m_ContactCache.Count() == 0`, `:330`), and only on the server (`:320`); `CheckContactCache` (`P:\scripts\4_world\entities\vehicles\carscript.c:1279`) works it out later, from `EOnPostSimulate` (`:807`, called at `:826`). Copy that shape for your own contact logic: vanilla warns that a vehicle's `OnContact` "Can be called very frequently in one frame" (`P:\scripts\4_world\entities\vehicles\boatscript.c:425`).

## Vehicle hits on players, step by step

- **Only a `Transport` triggers it.** The player's `EOnContact` casts `Transport.Cast(other)` and does nothing for any other entity (`P:\scripts\4_world\entities\dayzplayerimplement.c:3966`). An item or object that should hurt players on contact must detect the contact in its own `EOnContact` and call `ProcessDirectDamage` on the target itself.
- **Thresholds by vehicle kind**, all in `RegisterTransportHit`: a `Car` above 2.0 on `GetSpeedometerAbsolute()` (`carSpeed > 2.0`, `P:\scripts\3_game\entities\entityai.c:4150`); a `Motorbike`, new in 1.30, the same (`motorbikeSpeed > 2.0`, `:4169`); a `Boat` above 5 m/s (`m_TransportHitVelocity.Normalize() > 5`, `:4194`) for a flat 0.5 damage whatever the speed, because `Normalize()` turns the vector into a unit vector in place (`P:\scripts\1_core\proto\enconvert.c:141` to `:154`), so `m_TransportHitVelocity.Length() * 0.5` at `:4196` is always 0.5; and never when the player stands on that boat (`PhysicsGetLinkedEntity() == boat`, `:4188`); any other `Transport` above 0.1 m/s (`:4205`).
- **For a car, the damage is the speed.** `ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage)` passes the vehicle's speed in m/s as the damage coefficient (`P:\scripts\3_game\entities\entityai.c:4152`, `:4153`). The ammo `TransportHit` has `Health` `damage=1`, no blood or shock damage, and `hitAnimation=1` (`P:\DZ\weapons\melee\config.cpp:52` to `:72`), so a hit at 10 m/s deals 10 health before armor and plays the full body hit animation.
- **One hit per contact episode.** `m_TransportHitRegistered` blocks further hits until the victim's `EEHitBy` resets it (`P:\scripts\4_world\entities\dayzplayerimplement.c:1567`). Contact damage you write yourself has no such guard; add a flag or a cooldown, since `EOnContact` can fire several times in one tick.
- **The corpse is thrown, the living are not.** The impulse is `40 * m_TransportHitVelocity` with 60 upward for a car (`P:\scripts\3_game\entities\entityai.c:4159` to `:4164`) and `5.0 * m_TransportHitVelocity` with 5 upward for a motorbike (`:4180`, `:4181`), both only behind `IsDamageDestroyed()` and above 3 on the speedometer (`:4159`, `:4178`). Any other `Transport` throws the corpse like a car above 0.3 m/s (`:4216` to `:4220`). A hit below the speed threshold clears `m_TransportHitRegistered` again (`:4156`), so the next contact is tested afresh.

The whole damage pipeline (`EEHitBy` chain, hit zones, bleeding, shock, the hit animation) is in `damage-pipeline.md`.

## Contact damage from your own object

The player reacts only to a `Transport`, so an item or object that should hurt on contact deals the damage itself. The same shape as the vehicle hit, from the striker's side:

```c
void MyItem() { SetEventMask(EntityEvent.CONTACT); }
override void EOnContact(IEntity other, Contact extra)
{
    super.EOnContact(other, extra);              // keep the impact sound
    if (!g_Game.IsServer()) return;
    EntityAI target = EntityAI.Cast(other);
    if (target && target.IsAlive() && m_CanHit)
    {
        float speed = GetVelocity(this).Length(); // m/s
        if (speed > 0.5)
        {
            m_CanHit = false;                     // reset by a timer, or in the target's EEHitBy
            target.ProcessDirectDamage(DamageType.CUSTOM, this, "", "TransportHit", "0 0 0", speed);
        }
    }
}
```

With `TransportHit` the health damage is the speed in m/s and the target plays the full body hit animation. Do not push a living player with `dBodyApplyImpulse`; vanilla never does, and the measured result is in `ragdoll-and-fall-damage.md`. The threshold of 0.5 m/s is a starting value, not a vanilla one.

## Collisions with characters

- `InventoryItem.EnableCollisionsWithCharacter(bool state)` and `HasCollisionsWithCharacter()` (`P:\scripts\3_game\entities\inventoryitem.c:21`, `:22`) switch item to player collision.
- `ThrowPhysically` takes `collideWithCharacters`, default `true` (`P:\scripts\3_game\entities\inventoryitem.c:26`).
- The layer `PhxInteractionLayers.DYNAMICITEM_NOCHAR` exists next to `DYNAMICITEM` (`P:\scripts\3_game\global\dayzphysics.c:9`, `:10`).
- `dBodyCollisionBlock(ent1, ent2)` stops two bodies colliding and returns a block that `dBodyRemoveBlock` lifts (`P:\scripts\1_core\proto\enphysics.c:116`, `:117`).

## Pushing

The push action is the vanilla reference for moving a body from script: it reads `dBodyGetMass(entity)`, scales a force of `PUSH_FORCE_INCREMENT = 3000.0` by it, multiplies by the inverse mass again, so the impulse does not depend on the object's mass, and applies the result with `dBodyApplyImpulseAt(entity, impulse, entity.ModelToWorld(vector.Zero))` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushobject.c:49`, `:100` to `:109`). The car push does the same at the engine position, scaled by `GetPushForceCoefficientMultiplier()` and a random sideways and vertical factor (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushcar.c:35` to `:48`, `:52`). Both take stamina with `EStaminaModifiers.PUSH_CAR` (`actionpushobject.c:107`; `P:\scripts\3_game\enums\estaminamodifiers.c:13`). The other impulse and force calls are listed in `rigid-body-api.md` ("Moving a body"). Check that the body is dynamic before you push it (`drop-and-throw.md`).
