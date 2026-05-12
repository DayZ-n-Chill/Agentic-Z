# Pattern: actions (`ActionBase`)

Custom actions — the "Hold F to do something" UI elements players see when looking at an item. Three traps regularly produce *"my action doesn't show"* or *"my action shows but the server rejects it"* symptoms.

See also: `examples/02_custom_action_singleuse.c` and `examples/03_continuous_action.c` for full action implementations.

---

## ⚠️ `CCINonRuined` vs `CCINone` for tool-in-hand actions

Use `CCINonRuined` (item-in-hand, must not be ruined) **not** `CCINone` (no item needed) when the action requires holding a specific tool. With `CCINone` the engine may skip the action entirely when an item IS in hand, even if your condition would have passed.

```c
// CORRECT for tool-in-hand actions
override void CreateConditionComponents()
{
    m_ConditionItem = new CCINonRuined;     // tool must be present, non-ruined
    m_ConditionTarget = new CCTNone;
}

// AVOID — engine may skip when item-in-hand
m_ConditionItem = new CCINone;
```

Condition-component picker (the `m_ConditionItem` half):

| Component | Meaning |
|---|---|
| `CCINone` | No item in hand required |
| `CCIBase` | Some item in hand, any kind |
| `CCINonRuined` | Item in hand, non-ruined (tool-in-hand actions) |
| `CCINonRuinedAndEmpty` | Item in hand, non-ruined, empty quantity (e.g. empty bottle) |

---

## ⚠️ `RemoveAction` — full pickup-prevention pattern

Overriding `IsTakeable()` alone is **not enough** to prevent a placed item from being picked up by drag — the player can still grab it. Full prevention is a 4-step pattern:

```c
override bool IsTakeable() { return false; }

override void SetActions()
{
    super.SetActions();
    RemoveAction(ActionTakeItem);
    RemoveAction(ActionTakeItemToHands);
}

override bool CanPutInCargo(EntityAI parent) { return false; }
```

Without `RemoveAction` for both `ActionTakeItem` and `ActionTakeItemToHands`, the "Pick up" + "Take to hands" actions still render in the action wheel even though `IsTakeable()` returns false — and the inventory drag path is unaffected by either.

---

## ⚠️ Client/server check style must match

If the client uses `IsKindOf()` to decide an action shows up but the server uses `GetType() == "..."` to validate, the action may render but be rejected on execute (or vice versa). Use the **same** check style on both sides.

`IsKindOf()` is preferred because it respects inheritance — `GetType() == "MyMod_FancyKnife"` won't match subclasses of `MyMod_FancyKnife`, while `IsKindOf("MyMod_FancyKnife")` will.

```c
// CORRECT — same style both sides
override bool CanBeUsedForCrafting()
{
    return GetType() && IsKindOf("MyMod_FancyKnife");
}

override bool ActionCondition(...)
{
    return target.GetObject().IsKindOf("MyMod_FancyKnife");
}
```

Symptom of mismatch: action renders for the player but fails silently on execute. Look in `script.log` for the action's `OnExecuteServer` not firing.

---

## Action lifecycle (one-shot vs continuous)

| Type | Base class | Used for |
|---|---|---|
| Single-use | `ActionSingleUseBase` | Tap-to-do (drink, eat one bite, throw) |
| Continuous | `ActionContinuousBase` | Hold-to-complete with progress bar (bandage, build, repair) |
| Interactive | `ActionInteractBase` | Target-driven actions (interact with another entity) |

Pick the base that matches your interaction model — wrong base = wrong UI affordance.
