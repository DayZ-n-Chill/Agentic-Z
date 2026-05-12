# Pattern: dynamic items (physics)

For items with `simulation = "inventoryItem"` and `physLayer = "item"`, the `ECE_CREATEPHYSICS` flag of `CreateObjectEx` creates the **collision shape** but leaves the rigid body **static / kinematic**. Calling `dBodyApplyImpulse` on a static body silently no-ops — common symptom is *"item appears frozen in air after spawn."*

Two ways to get an item physics-active after spawn: the vanilla helper, or the manual API.

---

## Preferred — `ThrowPhysically`

The vanilla helper at `P:\scripts\3_game\entities\inventoryitem.c:26`:

```c
proto native void ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true);
```

Internally calls `CreateDynamicPhysics(ITEM_LARGE)`, `SetDynamicPhysicsLifeTime(...)`, and applies `force` as an impulse. This is the pattern vanilla itself uses — see `P:\scripts\4_world\static\miscgameplayfunctions.c` lines 1188 / 1204 / 1212 for examples.

```c
EntityAI spawned = GetGame().CreateObjectEx("MyMod_Item", pos, ECE_CREATEPHYSICS|ECE_UPDATEPATHGRAPH);
ItemBase ib = ItemBase.Cast(spawned);
if (ib)
    ib.ThrowPhysically(null, impulse, false);
```

---

## Manual — when you need finer control

If you need to drive lifetime, gravity, or interaction layer explicitly:

```c
obj.CreateDynamicPhysics(PhxInteractionLayers.DYNAMICITEM);
obj.EnableDynamicCCD(true);
obj.SetDynamicPhysicsLifeTime(20.0);     // without this, engine sleeps the body
dBodyEnableGravity(obj, true);
dBodyApplyImpulse(obj, impulse);
```

The `SetDynamicPhysicsLifeTime` call is **mandatory** — without it the engine sleeps the body within a few ticks and the impulse is lost mid-flight.

---

## Verified APIs

| API | Location |
|---|---|
| `CreateDynamicPhysics`, `EnableDynamicCCD`, `SetDynamicPhysicsLifeTime` | `P:\scripts\3_game\entities\object.c:462-464` |
| `PhxInteractionLayers` enum (`DYNAMICITEM`, `DYNAMICITEM_NOCHAR`, ...) | `P:\scripts\3_game\global\dayzphysics.c:1-29` |
| `dBodyDynamic`, `dBodyEnableGravity`, `dBodyApplyImpulse` | `P:\scripts\1_core\proto\enphysics.c:64-69, 141` |
| `StopItemDynamicPhysics` (sets lifetime to 0.01 to "park" the body) | `P:\scripts\4_world\entities\itembase.c:4530` |
