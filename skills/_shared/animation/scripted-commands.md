# Scripted player commands on the vanilla graph

What a `HumanCommandScript` can make the vanilla player graph do: how it is started and ended, report a stance and a movement, bind graph variables, commands and tags by name, start the jump machine, play the walk, run and sprint sources, and what breaks on the way (missing foot events, the raised idle, the weapon lift check, a command class in `4_World`).

The API and graph lines are checked on `P:\`. The behaviour was measured in game on 1.30 with two test mods, a sliding floor and a skateboard, with a server and one client on one machine; treat measured lines as evidence for that setup.

## Starting, running and ending the command

The class takes the `Human` as the first constructor parameter (`P:\scripts\3_game\human.c:1239`). Start it with `StartCommand_ScriptInst(typename)` or `StartCommand_Script(instance)` and read it back with `GetCommand_Script()` (`:1623`, `:1624`, `:1627`). The vanilla comment says the object is not managed: once started the engine owns it, an instance made but never started must be deleted by hand, and deleting one that is running crashes (`:1230` to `:1234`). Prefer `StartCommand_ScriptInst`, which leaves no instance to own.

| Step | Hook | What it may do | Line |
|---|---|---|---|
| Start | `OnActivate()` | Bind names, first `PreAnim_` writes. | `:1243` |
| Before the graph | `PreAnimUpdate(float pDt)` | Write graph variables and commands; `SetHeading` works here and in `PrePhysUpdate` only. | `:1288`, `:1261` |
| After the graph | `PrePhysUpdate(float pDt)` | Read events and tags, change the root motion in local space (`PrePhys_SetTranslation`). | `:1306`, `:1313` |
| After physics | `PostPhysUpdate(float pDt)` | Final world position (`PostPhys_SetPosition`). Return false to end the command. | `:1322`, `:1327` |
| End | `OnDeactivate()` | Clean up. | `:1246` |

`SetFlagFinished(true)` also ends it, and the player's `CommandHandler` then sees `pCurrentCommandFinished` true (`:1253`). While it runs, the current command id is `COMMANDID_SCRIPT` (`P:\scripts\3_game\dayzplayer.c:708`).

Start and stop the command from the player's command handler. `DayZPlayerImplement.CommandHandler` calls three empty hooks meant for mods, `ModCommandHandlerBefore`, `ModCommandHandlerInside` and `ModCommandHandlerAfter` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2266` to `:2279`), at the start, the middle and the end of its work (`:2297`, `:2430`, `:2688`). Returning true from one skips the rest of the vanilla handler for that frame, so return true only while your command owns the player.

## Reporting stance and movement

`HumanCommandScript` (`P:\scripts\3_game\human.c:1236`) has two overrides that no vanilla script calls. The engine reads them, and the graph plays the locomotion they report while the command runs (`:1264` to `:1274`). A third, `GetCurrentLeaning`, returns the lean from -1 to 1 (`:1277`). The first two as vanilla declares them:

```c
//! Override this to return the current stance of the human.
int GetCurrentStance()
{
    return DayZPlayerConstants.STANCEIDX_ERECT;
}

//! Override this to return the current movement state of the human.
int GetCurrentMovement()
{
    return DayZPlayerConstants.MOVEMENT_IDLE;
}
```

The movement values are `MOVEMENT_IDLE`, `MOVEMENT_WALK`, `MOVEMENT_RUN` and `MOVEMENT_SPRINT` (`P:\scripts\3_game\dayzplayer.c:645` to `:648`).

Return the movement and also write `MovementSpeed` every `PreAnimUpdate`. Measured: on the sliding floor, returning `MOVEMENT_RUN` was enough to make the character run, where without it the locomotion of the previous command stayed. On the skateboard the override alone left the graph on the idle clip (the pelvis stayed inside the idle clip's band, 0.894 to 0.927 m, over 994 state lines, 292 of them moving at 1 m/s or more), and with `MovementSpeed` written as well the walk, run and sprint sources played. Those two builds differed in other writes too, so the `MovementSpeed` write is the likely cause, not an isolated one.

## Binding graph variables, commands and tags by name

`PreAnim_SetFloat`, `PreAnim_SetInt` and `PreAnim_CallCommand` take ids from the vanilla graph, and script gets them by name through the interface `Human.GetAnimInterface()` returns, which its source comment calls "usable in HumanCommandScript implementations" (`human.c:1420` and `:1421`):

| Call on `HumanAnimInterface` | Line | Returns |
|---|---|---|
| `BindCommand(string pCommandName)` | `human.c:310` | The command index. |
| `BindVariableFloat(string pVariable)`, `BindVariableInt`, `BindVariableBool` | `:313` to `:315` | The variable index. |
| `BindTag(string pTagName)` | `:318` | The tag handle. |

All return -1 on error (`:307`). Inside `PreAnimUpdate` or `OnActivate` the command then uses `PreAnim_CallCommand(int pCommand, int pParamInt, float pParamFloat)`, `PreAnim_SetFloat`, `PreAnim_SetInt` and `PreAnim_SetBool` (`:1291` to `:1294`), and inside `PrePhysUpdate` reads `PrePhys_IsTag(int pTag)` (`:1310`).

Bind the names the master graph declares: variables such as `MovementSpeed`, `MovementDirection`, `Stance`, `TurnAmount`, `Look`, `LookDirX` and `Lean` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:6`, `:11`, `:16`, `:21`, `:26`, `:34`, `:88`), and commands from the `Commands` block at `:211` (`CMD_Action` at `:218`, `CMD_Jump` at `:245`, `CMD_Land` at `:263`). The same calls work on a custom graph with its own variables; Bohemia's scripted swim sample brings its own.

A shipped third party gunner command does this on the vanilla graph: it binds `Stance` with `BindVariableInt` and forces it with `PreAnim_SetInt` in `OnActivate` (`_shared/vehicles/gunner-shoot-from-vehicle.md`). `PreAnim_CallCommand` has no caller in vanilla script, which only means vanilla shows no example.

Measured with a skateboard ride command: `MovementSpeed`, `MovementDirection` and `LookDirX` as floats, `Stance` as int, `Look` as bool, `CMD_Jump` and `CMD_Land` as commands and `TagFall` as a tag all bound on server and owning client with the same ids and none at -1 (`MovementSpeed` 0, `MovementDirection` 1, `Stance` 2, `Look` 4, `LookDirX` 6, `CMD_Jump` 11, `CMD_Land` 17, `TagFall` 108504). Bind by name every time anyway; nothing says those numbers hold across builds.

## Jumping and moving under the command

`PreAnim_CallCommand(CMD_Jump)` takes the graph into the fall machine. `TagFall` is the tag of the `FallMaster` state machine (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:1065` to `:1067`), which holds the jump, fall and landing states, and the master graph enters it on `IsCommand(CMD_Jump) || IsCommand(CMD_Fall)` (`P:\DZ\anims\workspaces\player\player_main\master.agf:293`, state `Falling` at `:102`). The jump states start on `IsCommand(CMD_Jump)` (`locomotion.agf:1134`, `:1148`, `:1162`); the other entry states on `CMD_Fall` or `CMD_Restrained_Fall` (`:1077`, `:1085`). Measured: polling `PrePhys_IsTag(TagFall)` in the air saw the tag on server and client, also in a flight where the body stayed on the ground, so the tag follows the command, not the physics. Which state played was not read.

The graph chooses idle or movement on `MovementSpeed`: `IdleLow` starts on `!Raised && MovementSpeed == 0` and `MovementLow` on `!Raised && MovementSpeed > 0` (`locomotion.agf:6640` and `:6650`), and the variable runs 0 to 3 (`player_main.agr:6` to `:10`). Write 0 stopped, 1 walking pace, 2 running and 3 sprinting, and return the matching `MOVEMENT_` value.

`MovementDirection` written every `PreAnimUpdate` is not proven: the walk node updates that variable itself with `UpdateOnInit 1` and `UpdateOnMainPath 1` (`AnimSrcNodeVarUpdate`, `locomotion.agf:9481` to `:9488`), and the test never sampled full lean while rolling. A continuous lean blend driven from script is still untested.

## Replacement walk, run and sprint clips need foot events

The erect walk, run and sprint sources are sync sources: `WalkFSrc` plays `Locomotion.WalkF` on `SyncLine "Walk"` (`locomotion.agf:9463` to `:9467`); `RunFSrc` and `SprintFAnim` play `Locomotion.RunF` and `Locomotion.SprintF` on `SyncLine "RunSprint"` (`:5427` to `:5431`, `:6096` to `:6100`). The file holds 115 sync sources, 34 on `Walk` and 15 on `RunSprint`. The idle, `IdleAnim`, is a plain source with no line (`:11977` to `:11981`).

The master graph names its sync table (`AnimSyncTable`, `player_main.agr:3`), which defines each line by foot events at normalised times:

| Line | Events in cyclic order | Where |
|---|---|---|
| `Walk` | `RFootDown` 0.25, `LFootUp` 0.31, `LFootDown` 0.85, `RFootUp` 0.9 | `P:\DZ\anims\workspaces\player\player_synctable.asy:23` to `:42` |
| `RunSprint` | `LFootUp` 0.15, `RFootDown` 0.4, `RFootUp` 0.6, `LFootDown` 0.9 | `player_synctable.asy:43` to `:62` |

Vanilla clips carry these as events inside the `.anm`, in its `EVNT` chunk, where each event's frame and name are readable without a tool. In `P:\DZ\anims\anm\player\moves\unarmed\p_erc_walkf.anm` the first cycle has `RFootDown`, `LFootUp`, `LFootDown` and `RFootUp` at frames 8, 12, 24 and 27; in `p_erc_runf.anm` it has `LFootUp`, `RFootDown`, `RFootUp` and `LFootDown` at frames 5, 9, 15 and 19; each clip holds three cycles, 24 events in all, with `Step` and `SoundAttachment` events between the foot events; `p_erc_idle.anm` has no `EVNT` chunk. The base instance maps them at `Locomotion.Erc.WalkF`, `Locomotion.Erc.RunF` and `Locomotion.Erc.Idle` (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:3333`, `:3273`, `:3237`).

Measured: with replacement clips generated without events, the logged pelvis stayed at the same model space position on 50 of 53 samples while the board rolled, pushed and turned at 0.5 to 6.5 m/s, and the front foot sat 8 to 9 cm under the deck; a clip held still fits those numbers. With the line's four events added, and nothing else changed but a gravity switch for the flight, the pelvis moved between 0.86 and 1.17 m over 153 samples and the front foot sat on the deck. The idle, which has no events, animated in both.

Give a clip that replaces a `Walk` or `RunSprint` source the four foot events of that line, in its cyclic order:

- The table defines 13 lines with other events: `Turn` has four `Turn...` events (`player_synctable.asy:123`), `Transitions` only `TransitionIn` and `TransitionOut` (`:143` to `:154`), `TurnCro` three `TurnCroFoot` events (`:155`). A clip on another line needs that line's events, read from the node's `SyncLine` and the table. None of those is tested.
- The events may sit off the line's phases: a 63 frame push clip with `RFootDown` at 0.54 instead of 0.4 played too. A clip with events out of order is not tested.
- On the SEAnim to DayZATool route write each event as a SEAnim note named `RFootDown||-1`; DayZATool writes it as an event with the three fields vanilla foot events carry (the name, an empty string, -1). The tool in `scripts/tools/dayz-animation-formats/` reads and writes SEAnim notes.
- Before a test, check the built `.anm` holds the event names as plain ASCII in its `EVNT` chunk. Clips with no `EVNT` chunk at all are the ones that stood still.

## Raised stance under a scripted command

A ride command whose child `.asi` has no `ErcRas` or `CroRas` lines sometimes started in the vanilla raised fists idle (measured). The idle for a raised stance is `IdleRas`, which starts on `Raised && MovementSpeed == 0` (`locomotion.agf:6620` to `:6623`); `Raised` is a graph bool with default 0 (`player_main.agr:49` to `:51`). The likely cause is that the move command leaves `Raised` set. The fix, plausible and not confirmed in game: bind `Raised` with `BindVariableBool` in `OnActivate` and write it false with `PreAnim_SetBool` every `PreAnimUpdate` (`human.c:315`, `:1294`). With it no raised fists start was seen over several builds, and the bind returned 9.

A weapon can be raised and fired under a `HumanCommandScript` main command once `GetCurrentStance()` returns `STANCEIDX_RAISEDERECT` (`P:\scripts\3_game\dayzplayer.c:622`; measured). While it is raised, vanilla's lift check throws a NULL exception every time it runs. `LiftWeaponCheckEx` (`P:\scripts\4_world\entities\firearms\weapon_base.c:1651`) takes `player.GetCommand_Move()` (`:1698`) and passes it to `ApproximateWeaponLiftTransform` (`:1750`, declared at `:1564`), which calls `IsChangingStance()` on it with no null check (`:1625`). `GetCommand_Move` is native (`human.c:1481`) and returns the command only while it is the current one, so under any other main command it is null. A test that reads only its own log lines misses these exceptions; read the whole script log.

## A command class in 4_World crashes the exit

Measured, cause unknown: a `HumanCommandScript` subclass declared in `4_World` and started two or more times crashed every orderly exit of client and server, for a real ride command and an empty class alike. The same empty class in `3_Game`, or started only once, exited cleanly. A likely workaround, not verified: a thin class in `3_Game` that forwards to a `Managed` logic object in `4_World`. The measurements are entry E23 of `skills/dayz-launch-test/references/error-catalog.md`.
