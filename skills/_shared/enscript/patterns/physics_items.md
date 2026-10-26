# Pattern: dynamic items (physics)

For items with `simulation = "inventoryItem"` and `physLayer = "item"`, the `ECE_CREATEPHYSICS` flag of `CreateObjectEx` creates the **collision shape** but leaves the rigid body **static / kinematic**. Calling `dBodyApplyImpulse` on a static body silently no-ops — common symptom is *"item appears frozen in air after spawn."*

Two ways to get an item physics-active after spawn: the vanilla helper, or the manual API.

---

## Preferred — `ThrowPhysically`

The vanilla helper at `P:\scripts\3_game\entities\inventoryitem.c:26`:

```c
proto native void ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true);
```

It is native, so what it does inside can't be read in script. It is the call vanilla itself uses: the player's throw (`P:\scripts\3_game\systems\inventory\hand_actions.c:81`) and items or kits that must fall (`P:\scripts\4_world\classes\constructionbase.c:300`, `P:\scripts\4_world\entities\itembase\tentbase\shelter.c:65`).

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
| `CreateDynamicPhysics`, `EnableDynamicCCD`, `SetDynamicPhysicsLifeTime` | `P:\scripts\3_game\entities\object.c:456-458` |
| `PhxInteractionLayers` enum (`DYNAMICITEM`, `DYNAMICITEM_NOCHAR`, ...) | `P:\scripts\3_game\global\dayzphysics.c:1-43` |
| `dBodyDynamic`, `dBodyEnableGravity`, `dBodyApplyImpulse` | `P:\scripts\1_core\proto\enphysics.c:64-69, 141` |
| `StopItemDynamicPhysics` (sets lifetime to 0.01 to "park" the body) | `P:\scripts\4_world\entities\itembase.c:4530` |
