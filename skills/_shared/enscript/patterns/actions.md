# Pattern: actions (`ActionBase`)

Custom actions: the "Hold F to do something" UI elements players see when looking at an item. Four traps regularly produce *"my action doesn't show"* or *"my action shows but the server rejects it"* symptoms.

`ActionBase` is in `P:\scripts\4_world\classes\useractionscomponent\actionbase.c` (class at :51). The item condition classes are in `P:\scripts\4_world\classes\useractionscomponent\itemconditioncomponents\`, the target ones in `...\targetconditionscomponents\`.

See also: `examples/02_custom_action_singleuse.c` and `examples/03_continuous_action.c` for full action implementations.

---

## ⚠️ Register the action class

A new action class must be inserted once in a modded `ActionConstructor.RegisterActions`. Adding it to an item in `SetActions` is not enough.

```c
modded class ActionConstructor
{
    override void RegisterActions(TTypenameArray actions)
    {
        super.RegisterActions(actions);
        actions.Insert(ActionMyMod_DrinkContaminate);
    }
}
```

`ActionConstructor.ConstructActions` builds an action object only for the classes that `RegisterActions` inserts (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:3-27`; `RegisterActions` is at `:27`). `ActionManagerBase.GetAction` looks an action up in that map (`actionmanagerbase.c:214`). `ItemBase.AddAction` calls it, and for a class that was never registered it logs an error and returns, so the action never appears (`P:\scripts\4_world\entities\itembase.c:255-262`).

The error goes through `Debug.LogError`, which writes only when the game runs with `-doLogs` and one of `-logToScript` (`script.log`), `-logToFile` (`$profile:scriptExt.log`) or `-logToRpt` (`P:\scripts\3_game\tools\debug.c:594-596`, `646-663`, `719-723`; `constants.c:256`). On a normal launch nothing is logged and the action silently never appears. With logging on, the line ends in:

```
Action ActionMyMod_DrinkContaminate dosn't exist!
```

(`dosn't` is vanilla's spelling, `itembase.c:261`.)

---

## ⚠️ `CCINonRuined` vs `CCINone` for tool-in-hand actions

Use `CCINonRuined` (an item in hand that is not ruined) **not** `CCINone` when the action needs a specific tool in hand. `CCINone.Can` returns `true` for anything, including no item and a ruined one (`ccinone.c:3`), so the action shows with a broken tool. `CCINonRuined.Can` returns `item && !item.IsDamageDestroyed()` (`ccinonruined.c:3`).

```c
// CORRECT for tool-in-hand actions
override void CreateConditionComponents()
{
    m_ConditionItem = new CCINonRuined;     // tool must be present, non-ruined
    m_ConditionTarget = new CCTNone;
}

// AVOID for tool actions: accepts no item and a ruined item
m_ConditionItem = new CCINone;
```

`CreateConditionComponents` runs once when the action manager builds the action (`actionbase.c:245`). The item condition is checked again on the server: `ActionManagerServer` calls `pickedAction.Can(m_Player, target, item)` before it accepts a client's action (`actionmanagerserver.c:168`), and `ActionBase.Can` checks `m_ConditionItem.Can` and then `ActionCondition` (`actionbase.c:951` and `:954`).

Condition-component picker (the `m_ConditionItem` half). Each row was read from its file in `itemconditioncomponents\`:

| Component | `Can` returns | File |
|---|---|---|
| `CCINone` | always true | `ccinone.c` |
| `CCIBase` | always true (the parent class) | `ccibase.c` |
| `CCIPresent` | an item is in hand | `ccipresent.c` |
| `CCINotPresent` | no item in hand | `ccinotpresent.c` |
| `CCINonRuined` | an item in hand, not ruined (tool-in-hand actions) | `ccinonruined.c` |
| `CCINotRuinedAndEmpty` | an item in hand, not ruined, with quantity above 0 (despite the name) | `ccinotruinedandempty.c` |
| `CCINotRuinedAndDry` | an item in hand, not ruined, not wet | `ccinotruinedanddry.c` |
| `CCINotEmpty` | an item in hand with quantity | `ccinotempty.c` |

While the action runs, `CCIBase.CanContinue` also needs the item to still be the one in hands (`ccibase.c:8`).

---

## ⚠️ Stopping a placed item from being picked up

Both take actions already check `IsTakeable()`: `ActionTakeItem.ActionCondition` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakeitem.c:36`) and `ActionTakeItemToHands.ActionCondition` (`actiontakeitemtohands.c:38`). The inventory screen does not go through those actions, so also refuse cargo and hands. Vanilla `PowerGeneratorStatic` does exactly this (`P:\scripts\4_world\entities\building\underground\powergeneratorstatic.c:143`, `:149` and `:219`):

```c
override bool IsTakeable() { return false; }                          // the take actions
override bool CanPutInCargo(EntityAI parent) { return false; }        // drag into a container
override bool CanPutIntoHands(EntityAI parent) { return false; }      // drag into hands
```

To hide an action from the wheel for another reason, `ItemBase.RemoveAction(typename)` removes one that a parent class added (`P:\scripts\4_world\entities\itembase.c:295`); call it in `SetActions()` after `super.SetActions()`.

---

## ⚠️ Base the condition on synced state only

`ActionCondition` runs on the client to show the action and again on the server before it runs (`actionmanagerserver.c:168`, `actionbase.c:954`). If it reads client-only or unsynced state (a local variable, a value never net-synced, a `GetGame().IsClient()` branch), the client shows the action and the server rejects it. Base conditions on synced state only.

A separate tip on inheritance: prefer `IsKindOf()` to `GetType()`. `GetType() == "MyMod_FancyKnife"` won't match subclasses of `MyMod_FancyKnife`, while `IsKindOf("MyMod_FancyKnife")` will.

```c
// CORRECT: one condition on synced state, on the item in hand and the target
override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
{
    if (!item || !item.IsKindOf("MyMod_FancyKnife"))
        return false;
    Object obj = target.GetObject();
    return obj && obj.IsKindOf("MyMod_Crate");
}
```

The vanilla signature is `protected bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)` (`actionbase.c:441`).

Symptom of a condition that differs between client and server: the action renders for the player but fails silently on execute. Look in `script.log` for the action's `OnExecuteServer` not firing.

---

## Action lifecycle (one-shot vs continuous)

| Type | Base class | Used for | Source |
|---|---|---|---|
| Single-use | `ActionSingleUseBase` | Tap-to-do (take pills with `ActionConsumeSingle`, open with `ActionOpen`, drop with `ActionDropItem`, all under `actions\singleuse\`) | `actions\actionsingleusebase.c:29` |
| Continuous | `ActionContinuousBase` | Hold-to-complete with progress bar (bandage, build, repair) | `actions\actioncontinuousbase.c:120` |
| Interactive | `ActionInteractBase` | Target-driven actions (interact with another entity) | `actions\actioninteractbase.c:38` |

All three are under `P:\scripts\4_world\classes\useractionscomponent\`. Drinking is continuous, not single-use (`actions\continuous\actiondrink.c:9`, `ActionDrink: ActionConsume`). Pick the base that matches your interaction model: wrong base = wrong UI affordance.
