# Actions, doors and inventory in a scripted test

Which player actions, doors and inventory moves a scripted test can drive and read back, which need held input it cannot give, and the two ways round the rest: a key driven test addon and a mission driver.

Vanilla facts cite the file on `P:\`. The behaviour around them was measured in game on DayZDiag 1.29 and 1.30 and is not checked on `P:\`.

## Continuous actions need held input

An action with a progress bar finishes on the server in `OnFinishProgressServer` (`P:\scripts\4_world\classes\useractionscomponent\actions\actioncontinuousbase.c:289`), which fires only while the input is held for the whole duration. A test that starts the action without holding input sees it start and never finish: the target stayed in the world after waits of 60 and 45 s. That rules out dismantling, deploying and crafting, which is how a mod usually moves money and persistent objects.

- What a started action still proves: the condition was evaluated, so a start shows the mod offers the action on that target in that state. Pair it with a negative control that must be refused (an excluded target), or the start proves nothing.
- Name the action by its class (`class X : ActionInteractBase` in the mod), never by its visible text, which `m_Text` resolves from the stringtable in the client's language.
- An action class missing from the player's action list and an action that is there but refused by its `ActionCondition` are different failures. Test an invented action name on the same object as the negative control, so you know the two are really told apart.
- A server that is stopped without a graceful shutdown prints `... was not closed. Always shut down the server gracefully` on the next boot, and what was not saved is gone. No test of `OnStoreSave` and `OnStoreLoad` across a restart is conclusive unless the server was shut down gracefully and the object was created through the action that persists it; "did not persist" is then the test setup, not the mod.

## Instant actions finish before you look

`PerformActionStart` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804`) can complete an instant action before the caller's next line, so a check of `GetRunningAction()==null` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerbase.c:91`) right after it reads "nothing running" for an action that already worked. The vanilla test for such an action is `(IsLocal() || !UseAcknowledgment()) && IsInstant()` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:1064`). `ActionTogglePlaceObject` overrides both `IsLocal()` and `IsInstant()` to true (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actiontoggleplaceobject.c:19` and `:24`); `ActionDropItemSimple` overrides only `IsInstant()` (`actiondropitemsimple.c:5`) and inherits `UseAcknowledgment()` returning false from `ActionDropItem` (`actiondropitem.c:74`). Check the effect (the hologram, the dropped object) instead. On 1.30 in single player, a second action while one is pending does nothing; wait for `GetActionState()` to leave `UA_AM_INIT` (`dayz-1-30.md`).

## Doors

- A building resolves a door from the View Geometry component index: `GetDoorIndex(int componentIndex)` (`P:\scripts\3_game\entities\building.c:28`), and `ActionOpenDoors` passes the target's component (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:40`). An `ActionTarget` built with component -1 resolves no door, so the action is refused even with the player 1.4 m away. Pass the door's component or door index.
- `SetAnimationPhaseNow` (`P:\scripts\3_game\entities\entity.c:22`) on a door's animation source does not hold the door: the engine's door controller returns it to its wanted phase, and `IsDoorOpen(index)` (`building.c:34`) stays false, so every action that needs an open door is refused. A door set to phase 1 settled ajar at phase 0.07. Drive doors through the door actions, and read the result from `IsDoorOpen` and rays.
- A phase read back right after a write can lag one tick: phase 0, write 1.0, read 0.0, next read 0.599. Read again later.

## Real inventory moves

Measured on DayZ 1.30:

- Taking an item from the cargo of a world container (`WoodenCrate`, `Barrel_Blue`, open, player 1.5 m away) or from a building's attachment slot (`RB_LvL1_Plank` on `Land_House_1M1`) with a server-side take failed as not reachable. Taking an attachment of an item lying on the ground (`SparkPlug` in a `PowerGenerator`) and a container on the ground worked.
- `ActionAttach` with a plank in the hands was refused on a `Land_House_1M1` and worked on a `PowerGenerator` (spark plug). To fill a building's slot, use `PredictiveTakeEntityToTargetAttachment` from the table below.
- What worked every time: a test only addon whose `modded class MissionGameplay` (inside `#ifndef SERVER`) maps keys in `OnKeyPress` (`P:\scripts\5_mission\mission\missiongameplay.c:742`) to the client's own inventory calls, on objects found with `g_Game.GetObjectsAtPosition` (`P:\scripts\3_game\global\game.c:923`). Each reached the server as a real inventory command:

| Move | Call | Source |
|---|---|---|
| Cargo or building slot to hands | `PredictiveTakeEntityToHands` | `P:\scripts\3_game\entities\man.c:178` |
| Hands to cargo, crate to crate | `PredictiveTakeEntityToTargetCargo` | `P:\scripts\4_world\entities\manbase\playerbase.c:9072` |
| Hands to an empty building slot | `PredictiveTakeEntityToTargetAttachment` | `playerbase.c:9044` |
| Hands onto a stack | `CombineItemsClient` | `P:\scripts\4_world\entities\itembase.c:786` |
| Split a stack in half | `OnRightClick` | `itembase.c:2059` |

- Read the hands on the server. A client side "nothing in hands" is only the client's prediction.
- With Community Framework, Dabs Framework and VPPAdminTools loaded, a mod's `MissionGameplay.OnKeyPress` did not receive keys injected from a script; without that stack it did. Run such a driver without that stack, ship it as its own PBO and keep it out of the release.
- `OnKeyPress` is a mission callback, not system input: a key code delivered there does not open the vanilla menu, has no key up and no hold, and so cannot finish a continuous action.
- In-vehicle actions check the seat on the server (`vehicle-in-game-facts.md`).
- A server started without `-adminlog` writes no `.ADM` file, so lines written with `AdminLog` (`P:\scripts\3_game\global\game.c:669`) are lost. Start the server with `-adminlog`, or have the test build copy them to `Print` and read `script_*.log`.
- The player keeps what it carried between runs (`spawning-and-placement.md`). A plank left in the hands turned the next take from a slot into a swap.

## Opening a mod's UI

A Dabs Framework `ScriptView` panel is a host created up front, not a `UIScriptedMenu`, so looking for the current menu finds none while the panel is open. Find the panel by the root widget name of its `.layout`, the first `FrameWidgetClass <name>` in the file. An edit box bound to an int getter turns `"0.001"` into 0; type integers. A response marker printed about 200 ms after its trigger is missed by a log wait that starts "from now"; read back over the last 200 lines and match the marker to the request.

## A mission driver for logic no input reaches

When a test needs mod APIs the player cannot reach, put an Enforce Script driver in the test mission's `init.c`. Keep that mission with the mod's own test files and boot the test server on it instead of the template mission. `/dayz-gate behavior` injects a driver of the same kind (`AZ_BehaviorTest`) into a copy of the instance's mission; for its built in actions use the gate.

1. A server only driver class, started with `CallLater` at 250 ms.
2. A file protocol written once per sequence number: `$profile:<case>\cmd_<seq>.json` in, `res_<seq>.json` out, read and written with `JsonFileLoader`. Never rewrite a `seq`.
3. One boot per run: the sequence lives in memory and resets to 1 on restart.
4. A `MARK` line in the script log marks each window. Every failed operation is written into its `res_<seq>.json`; the poll loop does not die on a failed case.
5. Mission scripts see the classes of every loaded mod and compile on the server with `#ifdef SERVER` visible. The host side only writes commands, reads results and cuts the log between marks.
6. Archive the case folder (rename the folder, do not move its contents with a wildcard) when a run finishes, and never run a command that already has its `res_<seq>.json`. A driver whose sequence reset to 1 on a stale `cmd_1.json` re-ran a mounting command about every 1.5 s; half an hour later the world held thousands of duplicate objects.
