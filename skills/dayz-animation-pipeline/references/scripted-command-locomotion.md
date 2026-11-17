# Driving the vanilla player graph from a scripted command

What a `HumanCommandScript` can make the vanilla player graph do: report a stance and a movement, bind graph variables, commands and tags by name, start the jump machine, play the walk, run and sprint sources, and what breaks on the way (missing foot events, the raised idle, the weapon lift check, a command class in `4_World`).

The API and graph lines are checked on `P:\` (1.30). The behaviour was measured in game by the source pack's LFSlidingFloor and LFSkateboard projects on DayZDiag 1.30 Experimental (1.30.164014 unless a line says otherwise), with a server and one client on one machine. Treat measured lines as evidence for that setup.

## The command reports its own stance and movement

`HumanCommandScript` (`P:\scripts\3_game\human.c:1236`) has two overrides that no vanilla script calls; the engine reads them, and the graph plays the locomotion they report while the scripted command is running:

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

(`P:\scripts\3_game\human.c:1264` to `:1274`.) The movement values are `MOVEMENT_IDLE`, `MOVEMENT_WALK`, `MOVEMENT_RUN` and `MOVEMENT_SPRINT` (`P:\scripts\3_game\dayzplayer.c:645` to `:648`).

Measured (LFSlidingFloor, 2026-06-10): returning `MOVEMENT_RUN` from `GetCurrentMovement()` made the character run while the scripted command moved it; without the override it kept the locomotion left by the previous command.

Qualified later (LFSkateboard, 2026-10-06): with this override alone a ride command left the graph on the idle clip. With the override plus `MovementSpeed` written every `PreAnimUpdate`, the walk, run and sprint sources played. The two builds differed in other writes too, so the comparison points at the `MovementSpeed` write without isolating it. Write both.

## Graph variables, commands and tags are bound by name

An earlier version of the source pack discarded `PreAnim_SetFloat`, `PreAnim_SetInt` and `PreAnim_CallCommand` on the belief that script cannot get the vanilla graph's ids. It can, by name, through the interface `Human.GetAnimInterface()` returns, which its source comment calls "usable in HumanCommandScript implementations" (`P:\scripts\3_game\human.c:1420`, `:1421`):

| Call on `HumanAnimInterface` | Line | Returns |
|---|---|---|
| `BindCommand(string pCommandName)` | `P:\scripts\3_game\human.c:310` | The command index. |
| `BindVariableFloat(string pVariable)`, `BindVariableInt`, `BindVariableBool` | `P:\scripts\3_game\human.c:313` to `:315` | The variable index. |
| `BindTag(string pTagName)` | `P:\scripts\3_game\human.c:318` | The tag handle. |

All return −1 on error (source comment at `human.c:307`). The command then uses, inside `PreAnimUpdate` or `OnActivate`, `PreAnim_CallCommand(int pCommand, int pParamInt, float pParamFloat)`, `PreAnim_SetFloat`, `PreAnim_SetInt` and `PreAnim_SetBool` (`P:\scripts\3_game\human.c:1291` to `:1294`), and inside `PrePhysUpdate` reads `PrePhys_IsTag(int pTag)` (`:1310`).

The names to bind are the ones the master graph declares: variables such as `MovementSpeed`, `MovementDirection`, `Stance`, `TurnAmount`, `Look`, `LookDirX` and `Lean` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:6`, `:11`, `:16`, `:21`, `:26`, `:34`, `:88`), and commands from the `Commands` block that starts at `:211` (`CMD_Action` at `:218`, `CMD_Jump` at `:245`, `CMD_Land` at `:263`).

A shipped third party command does this on the vanilla graph: the SIBNIC gunner binds `Stance` with `BindVariableInt` and forces it with `PreAnim_SetInt` in `OnActivate` (described in `skills/_shared/vehicles/gunner-shoot-from-vehicle.md`). `PreAnim_CallCommand` has no caller in vanilla script, which only means vanilla shows no example.

These APIs also work with a custom graph that defines its own variables; Bohemia's scripted swim sample brings its own.

## Measured: a skateboard ride command on the vanilla graph

LFSkateboard, 2026-10-06. A ride `HumanCommandScript` on the vanilla graph, with a child `.asi` swapping the locomotion and jump clips.

**The binds hold on both sides.** `OnActivate` bound `MovementSpeed`, `MovementDirection` and `LookDirX` as floats, `Stance` as int, `Look` as bool, `CMD_Jump` and `CMD_Land` as commands and `TagFall` as a tag. All twelve bind lines of six rides, server and owning client, returned the same ids and none returned −1: `MovementSpeed` 0, `MovementDirection` 1, `Stance` 2, `Look` 4, `LookDirX` 6, `CMD_Jump` 11, `CMD_Land` 17, `TagFall` 108504. Bind by name every time anyway; nothing says those numbers hold across builds.

**`PreAnim_CallCommand(CMD_Jump)` takes the graph into the fall machine.** The command called it once when the jump started and polled `PrePhys_IsTag(TagFall)` on every tick in the air. `TagFall` is the tag of the `FallMaster` state machine (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:1065` to `:1067`), which holds the jump states and the fall and landing states. The master graph enters it on `IsCommand(CMD_Jump) || IsCommand(CMD_Fall)` (`P:\DZ\anims\workspaces\player\player_main\master.agf:293`; the state `Falling` at `:102`). The tag was seen in both landed flights on the server and on the client, and also in a flight where the body stayed on the ground, so it followed the command, not the physics. The probe read only the tag. That the machine started in a jump state comes from the graph, not from the measurement: the jump states start on `IsCommand(CMD_Jump)` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:1134`, `:1148`, `:1162`) and the other entry states on `CMD_Fall` or `CMD_Restrained_Fall` (`:1077`, `:1085`), which this command never called. Which state played was not read.

**`MovementSpeed` written every `PreAnimUpdate`, with a matching `GetCurrentMovement()`, gets the walk, run and sprint sources.** The graph chooses idle or movement on `MovementSpeed`: the stance machine's `IdleLow` starts on `!Raised && MovementSpeed == 0` and `MovementLow` on `!Raised && MovementSpeed > 0` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:6640`, `:6650`), and the variable runs 0 to 3 (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:6` to `:10`). The command wrote 0 stopped, 1 rolling, 2 pushing and 3 pushing with Shift, and returned the matching `MOVEMENT_` value. With both, the three sources played once their clips carried the events described below.

The build tested the night before had the same override, the same locomotion clips byte for byte and the same lines in its `.asi`, and wrote no `MovementSpeed`. The owner's pelvis stayed inside the idle clip's band, 0.894 to 0.927 m over 994 state lines, 292 of them moving at 1 m/s or more (217 sprinting), where those clips, which had no events, would have frozen in the walk, run or sprint sources. So the override alone left that graph on idle. The two builds also differ in other writes (`Stance`, `Look`, `LookDirX`, the jump and land commands).

**Not isolated.** `MovementDirection` was bound and written (the lean times 85), but the test lap leaned only while pushing, so there were no rolling samples at full lean. Whether a `MovementDirection` written every `PreAnimUpdate` survives the graph's own update of that variable is still open: the walk node updates it with `UpdateOnInit 1` and `UpdateOnMainPath 1` (`AnimSrcNodeVarUpdate`, `P:\DZ\anims\workspaces\player\player_main\locomotion.agf:9481` to `:9488`). A continuous lean blend driven from script is still a design, not a result.

## A clip that replaces a walk, run or sprint source needs the foot events of its sync line

The erect walk, run and sprint sources are sync sources: `WalkFSrc` plays `Locomotion.WalkF` on `SyncLine "Walk"` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:9463` to `:9467`), and `RunFSrc` and `SprintFAnim` play `Locomotion.RunF` and `Locomotion.SprintF` on `SyncLine "RunSprint"` (`:5427` to `:5431`, `:6096` to `:6100`). The file holds 115 sync sources, 34 on `Walk` and 15 on `RunSprint`. The idle is a plain source, `IdleAnim`, with no line (`:11977` to `:11981`).

The master graph names its sync table (`AnimSyncTable`, `P:\DZ\anims\workspaces\player\player_main\player_main.agr:3`), and the table defines each line by foot events at normalised times:

| Line | Events in cyclic order | Where |
|---|---|---|
| `Walk` | `RFootDown` 0.25, `LFootUp` 0.31, `LFootDown` 0.85, `RFootUp` 0.9 | `P:\DZ\anims\workspaces\player\player_synctable.asy:23` to `:42` |
| `RunSprint` | `LFootUp` 0.15, `RFootDown` 0.4, `RFootUp` 0.6, `LFootDown` 0.9 | `P:\DZ\anims\workspaces\player\player_synctable.asy:43` to `:62` |

The vanilla clips carry these as events inside the `.anm`. As the source pack read them from a 1.29 unpack: `p_erc_walkF.anm` has `RFootDown`, `LFootUp`, `LFootDown` and `RFootUp` at frames 8, 12, 24 and 27; `p_erc_runF.anm` has `LFootUp`, `RFootDown`, `RFootUp` and `LFootDown` at frames 5, 9, 15 and 19; both have `Step` and `SoundAttachment` events beside them; `p_erc_idle.anm` has none. The base instance maps them at `Locomotion.Erc.WalkF`, `Locomotion.Erc.RunF` and `Locomotion.Erc.Idle` (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:3333`, `:3273`, `:3237`).

**Without the events the logged pose stopped moving.** A child `.asi` mapped `Locomotion.Erc.WalkF`, `WalkFL` and `WalkFR` to three rolling clips and the erect `RunF` and `SprintF` lines to one push clip, all generated without events, while the command drove locomotion through `MovementSpeed`. The owner's pelvis read the same (x, y) = (−0.0569, 0.9386) m on 50 of 53 state lines, rolling, pushing and turning at 0.5 to 6.5 m/s with the lean going from −1 to +1. The head's (x, y) did not change either, and the front foot stayed 8 to 9 cm under the deck. The other three lines fell in the jump's flight and the 0.6 s after landing. The log carried only the model space x and y of pelvis and head and the toe to deck distances; nobody looked at the pose. A locomotion clip held still is the reading those numbers fit, not an observation of the whole skeleton.

**With the four events of the line the pose moved.** The next build added the line's four events to those four clips and to the charge clip of the crouched lines, and changed nothing else but a gravity switch for the flight. The pelvis moved between 0.86 and 1.17 m over 153 lines with 152 distinct values, and the front foot sat on the deck (median 0 mm). The idle clip has no events either, and it animated in both runs.

**The fix, measured for `Walk` and `RunSprint` only.** Give a clip that replaces a `Walk` or `RunSprint` source the four foot events of that line, in the line's cyclic order.

- The table defines 13 lines. The others carry other events or orders: `Turn` has four `Turn...` events (`P:\DZ\anims\workspaces\player\player_synctable.asy:123`), `Transitions` only `TransitionIn` and `TransitionOut` (`:143` to `:154`), `TurnCro` three `TurnCroFoot` events (`:155`). A clip that replaces a source on another line needs that line's events, read from the node's `SyncLine` and the table. None of those was tested.
- The 28 frame rolling clips carried their events at the line's phases (frames 7, 9, 24, 25). The 63 frame push clip carried `RFootDown` and `RFootUp` around the pushing foot's contact as the project measured it (down at frame 34, up at 39), which puts `RFootDown` at 0.54 instead of the line's 0.4, and it played too. A clip with the events out of order was not tested.
- On the SEAnim to DayZATool route, write each event as a SEAnim note named `RFootDown||-1`. DayZATool wrote each such note into the `.anm` as an event with the three fields the vanilla foot events carry: the name, an empty string and −1. The tool in `scripts/tools/dayz-animation-formats/` reads and writes SEAnim notes.
- Before a test, check that the built `.anm` holds the event names (plain ASCII inside its `EVNT` chunk). The clips of the build that stopped moving had no `EVNT` chunk at all.

## `Raised` under a scripted command

### The raised fists idle

Measured (LFSkateboard, 2026-10-06 and 07): a ride command whose child `.asi` has no `ErcRas` or `CroRas` lines sometimes started in the vanilla raised fists idle. The graph's idle for a raised stance is the state `IdleRas`, which starts on `Raised && MovementSpeed == 0` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:6620` to `:6623`); `IdleLow` and `MovementLow` after it start on `!Raised`. `Raised` is a graph bool with default 0 (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:49` to `:51`).

The cause and the fix are the project's, plausible and not verified in game. Its reading: the move command leaves `Raised` set, and the stance machine then enters `IdleRas`. Its fix: bind `Raised` with `BindVariableBool` in `OnActivate` and write it false with `PreAnim_SetBool` on every `PreAnimUpdate` (`P:\scripts\3_game\human.c:315`, `:1294`). The owner played several builds with the fix and saw no raised fists start, but did not confirm that case explicitly. The automated check verified only the bind (it returned 9, not −1): the test bridge could not raise unarmed fists.

### A weapon raised under a scripted command

Measured (LFSkateboard, reported 2026-10-09): a weapon can be raised and fired under a `HumanCommandScript` main command once the command's `GetCurrentStance()` returns `STANCEIDX_RAISEDERECT` (`P:\scripts\3_game\dayzplayer.c:622`).

While the weapon is raised, though, vanilla's lift check throws a NULL exception each time it runs. `LiftWeaponCheckEx` (`P:\scripts\4_world\entities\firearms\weapon_base.c:1651`) takes the move command from `player.GetCommand_Move()` (`:1698`) and passes it to `ApproximateWeaponLiftTransform` (`:1750`, declared at `:1564`), which calls `IsChangingStance()` on it with no null check (`:1625`). `GetCommand_Move` is native (`P:\scripts\3_game\human.c:1481`) and, like the other command getters, returns the command only while it is the current one, so under any other main command it returns null.

A test verdict that reads only its own log lines misses these exceptions: 241 of them went unnoticed in one probe. Read the whole script log.

## A command class in `4_World`, started twice, crashed the exit

Measured (LFSkateboard, 2026-10-07, DayZDiag 1.30.164014 Experimental), cause unknown and still open: a `HumanCommandScript` subclass declared in `4_World` and started two or more times crashed every orderly exit of client and server. This held for the project's ride command and for an empty class alike. The same empty class declared in `3_Game`, or started only once, exited cleanly.

The workaround the project adopted, still being verified when reported: a thin class in `3_Game` that forwards to a `Managed` logic object in `4_World`. The measurements are recorded in the source pack's error catalogue as entry E23 (`skills/dayz-mod-workflow/references/error-catalog.md`).
