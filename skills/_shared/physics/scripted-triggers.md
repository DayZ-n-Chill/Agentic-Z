# Scripted trigger volumes

The script API under every scripted trigger: `ScriptedEntity` and its collision shapes, who is told when something enters or leaves, and the server and client hooks of `TriggerEvents`. Read from source on `P:\` (DayZ 1.30); nothing here was measured in a running game. Underground areas built on this are in `skills/dayz-underground/SKILL.md`, and hazard areas with a synced trigger in `skills/dayz-environment-hazards/SKILL.md`.

## The class

`ScriptedEntityType : EntityAIType` is declared at `P:\scripts\3_game\entities\scriptedentity.c:8` and `ScriptedEntity : EntityAI` at `P:\scripts\3_game\entities\scriptedentity.c:12`. A scripted entity is therefore an `EntityAI`: it has the inventory, network and persistence machinery whether a given use wants it or not. It is not a bare engine trigger volume, and spawning one means spawning a full entity.

## Collision and trigger shapes

The shape enum is `TriggerShape` with `BOX`, `SPHERE` and `CYLINDER` (`P:\scripts\3_game\entities\scriptedentity.c:1` to `:6`). The shape is chosen explicitly; nothing in the class works it out from a model.

| Method | Kind | What the source shows |
|---|---|---|
| `SetClippingInfo(vector mins, vector maxs, float radius)` (`scriptedentity.c:21`) | `proto native` | Its comment calls it obsolete (`:19`); use `SetCollisionBox`. |
| `SetCollisionBox(vector mins, vector maxs)` (`scriptedentity.c:35`) | `proto native` | Sets `TriggerShape.BOX` by itself (`:27`). |
| `SetCollisionSphere(float radius)` (`scriptedentity.c:46`) | `proto native` | Sets `TriggerShape.SPHERE` by itself (`:40`). |
| `SetCollisionCylinder(float radius, float height)` (`scriptedentity.c:58`) | `proto native` | A cylinder from the origin up to a positive height (`:49`); sets `TriggerShape.CYLINDER`. |
| `SetCollisionCylinderTwoWay(float radius, float negativeHeight, float positiveHeight)` (`scriptedentity.c:84`) | script wrapper | Checks its input, then calls the private native. |
| `SetTriggerShape(TriggerShape shape)` (`scriptedentity.c:102`) | `proto native` | The default shape is `TriggerShape.BOX` (`:101`). |
| `GetTriggerShape()` (`scriptedentity.c:105`) | `proto native` | Returns the current `TriggerShape`. |

`SetCollisionCylinderTwoWay` is the only setter with a check in script: the wrapper at `P:\scripts\3_game\entities\scriptedentity.c:84` to `:99` rejects a `radius` of 0 or less and a `negativeHeight` above `positiveHeight` with `ErrorEx` and returns, and only then calls the private `SetCollisionCylinderTwoWayNative` (`scriptedentity.c:71`). The other setters go straight to native code, so script shows no such guard for them.

`ScriptedEntity` overrides `IsInventoryVisible()` to return `false` (`P:\scripts\3_game\entities\scriptedentity.c:107` to `:110`): it shows no inventory in the UI by default, although it inherits the inventory machinery.

## Who hears about entry and exit: the object that entered

The enter and leave callbacks are on `Object`, not on the trigger: `OnEnterTrigger(ScriptedEntity trigger)` at `P:\scripts\3_game\entities\object.c:92` and `OnLeaveTrigger(ScriptedEntity trigger)` at `P:\scripts\3_game\entities\object.c:95`. Both are empty in the base class, and the parameter is the trigger that was entered or left. So the direction is "the object that moved is told which trigger it crossed", the reverse of the `TriggerEvents` hooks below, which fire on the trigger. A mod that overrides these two on its trigger class is never called this way.

The one vanilla override is for diagnostics only. `PlayerBase` declares `m_IsInsideTrigger` inside `#ifdef DIAG_DEVELOPER` (`P:\scripts\4_world\entities\manbase\playerbase.c:224` to `:225`), and its `OnEnterTrigger` and `OnLeaveTrigger` overrides only call `super` and count that member up and down (`P:\scripts\4_world\entities\manbase\playerbase.c:4772` to `:4784`). The counter only feeds a debug drawing of the player's collision box (`m_IsInsideTrigger` read at `P:\scripts\4_world\entities\manbase\playerbase.c:4739`). None of this exists in a retail build: do not read `m_IsInsideTrigger`, and do not treat the `PlayerBase` overrides as a gameplay hook to copy.

## `TriggerEvents`: events on the trigger

`TriggerEvents : ScriptedEntity` is declared at `P:\scripts\4_world\entities\scriptedentities\triggers\triggerevents.c:3`. Where `Object.OnEnterTrigger` tells the object that entered, `TriggerEvents` gives the trigger its own protected event methods and two invokers that other code can subscribe to.

The invokers are `m_OnEnterInvoker` and `m_OnLeaveInvoker` (`triggerevents.c:5` to `:6`), created on first use by `GetOnEnterInvoker()` and `GetOnLeaveInvoker()` (`triggerevents.c:8` to `:20`). There is no invoker for staying; that phase has hooks only.

The dispatchers are `Enter` (`triggerevents.c:26`), `StayStart` (`:54`), `Stay` (`:79`), `StayFinish` (`:104`) and `Leave` (`:129`). Each runs the same steps in the same order:

1. the `Begin` hook, for example `OnEnterBeginEvent`;
2. for enter and leave only, the matching invoker when it exists;
3. exactly one side hook chosen by `g_Game.IsServer()`: `OnEnterServerEvent` on the server, `OnEnterClientEvent` otherwise (`triggerevents.c:37` to `:40`);
4. the `End` hook.

`Leave` also guards the side test with `g_Game &&` (`triggerevents.c:140`); the others test `g_Game.IsServer()` directly.

| Phase | Hook arguments | Declared at |
|---|---|---|
| Enter, Leave | the `TriggerInsider` | `OnEnterBeginEvent`, `triggerevents.c:44`; `OnLeaveBeginEvent`, `:147` |
| Stay | the `TriggerInsider` and a `float deltaTime` | `OnStayBeginEvent`, `triggerevents.c:94` |
| StayStart | an `int nrOfInsiders` | `OnStayStartBeginEvent`, `triggerevents.c:69` |
| StayFinish | none | `OnStayFinishBeginEvent`, `triggerevents.c:119` |

All hooks are empty `protected` methods in the base class, so a subclass overrides only the phases and sides it needs. Because the side is chosen on each call, one trigger runs its server hooks on the server and its client hooks on each client; this class does not send a hook to the other side.

## Vanilla subclasses as patterns

Four shipped subclasses show what the base is used for:

- `UndergroundTriggerCarrierBase : ScriptedEntity` (`P:\scripts\3_game\triggercarrierbase.c:1`) is the carrier the underground system moves trigger data with.
- `DynamicArea_Flare : ScriptedEntity` (`P:\scripts\4_world\classes\contaminatedarea\dynamicarea_flare.c:2`) is a falling dummy entity that announces a contaminated area: an effect carrier, not a volume.
- `SpookyPlayerStalker : ScriptedEntity` (`P:\scripts\4_world\classes\contaminatedarea\spookyareamisc.c:324`) is attached to each player inside its area and carries a temperature source.
- `TestFramework : ScriptedEntity` (`P:\scripts\3_game\systems\testframework.c:212`) uses the base as a plain scripted world object with init and frame event masks, with no trigger shape at all.

Together: the base serves as a trigger volume, an effect carrier and a general scripted object, and only the first of those uses the shape API.

## Traps

- `ScriptedEntity` is an `EntityAI`, not a light trigger volume; spawning one costs a full entity.
- The shape is explicit: each `SetCollision*` setter sets the `TriggerShape` as a side effect, and the default is `BOX`. The wrong setter changes the volume itself, not only its numbers.
- Only `SetCollisionCylinderTwoWay` checks its input in script. Pass the native setters values you have checked yourself.
- `OnEnterTrigger` and `OnLeaveTrigger` fire on the object that entered; the `TriggerEvents` hooks fire on the trigger. Overriding the first pair on a trigger class does nothing.
- The `PlayerBase` trigger overrides are debug counters under `DIAG_DEVELOPER` and are absent in retail.
- Server and client hooks are separate methods picked on each call by `g_Game.IsServer()`. Writing only the server hook leaves clients silent, and the other way round.

## Limits

Script shows the declarations, the order of the dispatch and the one check in script. It does not show how the engine detects an overlap, how often insiders are evaluated, or whether a `proto native` shape setter is linked in a given build. Those are engine behavior and are not claimed here.
