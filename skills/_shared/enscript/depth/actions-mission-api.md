# Action classes and server connect hooks

Which base classes, condition components, overrides and registration calls an action uses, and which `MissionServer` events run when a player connects, respawns or leaves. The action pattern is in `../patterns/actions.md`; the mission order is in `../references/mission_lifecycle.md`.

## Action base classes

`ActionSingleUseBase` (`P:\scripts\4_world\classes\useractionscomponent\actions\actionsingleusebase.c:29`), `ActionContinuousBase` (`P:\scripts\4_world\classes\useractionscomponent\actions\actioncontinuousbase.c:120`) and `ActionInteractBase` (`P:\scripts\4_world\classes\useractionscomponent\actions\actioninteractbase.c:38`) all derive from `AnimatedActionBase`. `FirearmActionBase` derives from `ActionBase` directly (`P:\scripts\4_world\classes\useractionscomponent\actions\weapons\firearmactionbase.c:1`).

`ActionData` carries `m_Player`, `m_MainItem`, `m_Target` (an `ActionTarget`) and `m_ActionComponent` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:21` to `:49`).

## Condition components

`CreateConditionComponents()` sets `m_ConditionItem` and `m_ConditionTarget` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:63` and `:64`, `:245` to `:248`).

- Item conditions, in `ItemConditionComponents/`: `CCINone`, `CCIDummy`, `CCIPresent`, `CCINotPresent`, `CCINonRuined`, `CCINotEmpty`, `CCINotRuinedAndEmpty`, `CCINotRuinedAndDry`.
- Target conditions, in `TargetConditionsComponents/`: `CCTNone`, `CCTDummy`, `CCTSelf`, `CCTMan`, `CCTObject(dist)`, `CCTParent`, `CCTCursor(dist)` and its `NoRuinCheck`, `Inherited`, `Parent` and `NoObject` forms, `CCTNonRuined`, `CCTSurface`, `CCTTree`, `CCTWaterSurface`, `CCTWaterSurfaceEx` and `CCTLiquid`.
- `CCTWaterSurface` is `[Obsolete("1.30: replaced by CCTLiquid")]` (`P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctwatersurface.c:2`); use `CCTLiquid`.

Distances come from `UAMaxDistances` (`P:\scripts\4_world\classes\useractionscomponent\actions\actionconstants.c:111` to `:122`): `SMALL` 1.3, `DEFAULT` 2.0, `REPAIR` 3.0, `LARGE` 8.0, and more.

## Methods to override

| Method | Source |
|---|---|
| `GetText()`, which returns `m_Text` | `P:\scripts\4_world\classes\useractionscomponent\actionbase.c:330` to `:333` |
| `ActionCondition(PlayerBase, ActionTarget, ItemBase)` | `actionbase.c:441` |
| `OnStartServer`, `OnStartClient`, `OnEndServer`, `OnEndClient` | `actionbase.c:1388` to `:1409` |
| `CanBeUsedInVehicle()` | `actionbase.c:361` |
| `OnExecuteServer`, `OnExecuteClient` | `P:\scripts\4_world\classes\useractionscomponent\animatedactionbase.c:179` and `:183` |
| `OnFinishProgressServer`, `OnFinishProgressClient`, for continuous actions | `P:\scripts\4_world\classes\useractionscomponent\actions\actioncontinuousbase.c:289` and `:293` |

## Input type and behaviour flags

`GetInputType()` decides which key and press style starts the action, and each base class picks a different one. An action that overrides it with the wrong input class is filed under another input and does not show where you expect.

| Base or override | Default | Source |
|---|---|---|
| `ActionBase.GetInputType()` | `DefaultActionInput` | `actionbase.c:230` |
| `ActionSingleUseBase` | `DefaultActionInput` | `actionsingleusebase.c:37` |
| `ActionContinuousBase` | `ContinuousDefaultActionInput` (hold) | `actioncontinuousbase.c:179` |
| `ActionInteractBase` | `InteractActionInput` | `actioninteractbase.c:61` |
| `HasTarget()` | `true`: the target is synced to the server and the cursor shows the floating widget | `actionbase.c:259` |
| `HasProgress()` | `true`: shows the progress bar | `actionbase.c:265` |
| `IsLocal()` | `false`: when true the action is not synchronised to the server | `actionbase.c:271` |
| `IsInstant()` | `false`: when true the action runs at once in `OnStart`, with no animation or callback | `actionbase.c:294` |

The input classes are declared in `P:\scripts\4_world\classes\useractionscomponent\actioninput.c` (`InteractActionInput` at `:558`, `ContinuousDefaultActionInput` at `:627`, `DefaultActionInput` at `:654`).

## A continuous action needs a callback class

The callback class sets the progress component. Vanilla does it in `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionactivatetrap.c:1` to `:34`: a `class MyMod_ActionCB : ActionContinuousBaseCB` overrides `CreateActionComponent()` with `m_ActionData.m_ActionComponent = new CAContinuousTime(seconds);`, and the action's constructor sets `m_CallbackClass = MyMod_ActionCB;`. The base default is the plain `ActionContinuousBaseCB` (`actioncontinuousbase.c:126`).

## Registering an action

- On an item: `override void SetActions()` with `super.SetActions(); AddAction(MyMod_Action);` (`SetActions` and `AddAction` at `P:\scripts\4_world\entities\itembase.c:246` and `:255`).
- On the player: `SetActions(out TInputActionMap InputActionMap)` with `AddAction(MyMod_Action, InputActionMap)` (`P:\scripts\4_world\entities\manbase\playerbase.c:1695` and `:1817`). The forms without the map are kept only for older mods (`:1747`, `:1838`).

## `MissionServer` connect hooks

The server creates `MissionServer` from `P:\scripts\5_mission\somemission.c:1` to `:9`; the class is declared at `P:\scripts\5_mission\mission\missionserver.c:5`.

`OnEvent` (`missionserver.c:309`) dispatches the client events:

| Event | What it does | Line |
|---|---|---|
| `OnClientPrepareEvent` | The prepare step of a connecting client | `:449` |
| `OnClientNewEvent` | Calls `CreateCharacter(PlayerIdentity, vector pos, ParamsReadContext, string characterName)` (`:499`), which returns the new `PlayerBase`, then `InvokeOnConnect` | `:549` |
| `OnClientReadyEvent(PlayerIdentity, PlayerBase)` | A character loaded from the database, then `InvokeOnConnect(PlayerBase, PlayerIdentity)` (`:435`) | `:599` |
| `OnClientRespawnEvent` | Respawn | `:611` |
| `OnClientReconnectEvent` | Reconnect | `:633` |
| `OnClientDisconnectedEvent(identity, player, int logoutTime, bool authFailed)` | Starts the logout timer, or for an instant logout calls `PlayerDisconnected` | `:641` |

`PlayerDisconnected(PlayerBase, PlayerIdentity, string uid)` (`:690`) runs `InvokeOnDisconnect` and handles the body by its alive state (`HandleBody`, `missionserver.c:748` to `:763`); a corpse is not removed that way. `uid` is `identity.GetId()`, and the source warns that `identity` may already be deleted there (`:692`), so key any save on `uid`.
