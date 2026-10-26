# Script hooks that play an animation

The Enforce Script calls that move a `model.cfg` animation, which side runs them, and the two vanilla patterns to copy. The full script is written by `dayz-script-specialist`; this file says which hook to name in the handoff.

## The calls

All on `Entity`, so every item, building and vehicle has them (`P:\scripts\3_game\entities\entity.c`).

| Call | Line | Use |
|---|---|---|
| `proto native void SetAnimationPhase(string animation, float phase)` | :15 | Move the source to `phase` over its `animPeriod`. |
| `proto native float GetAnimationPhase(string animation)` | :12 | Read the current phase, for example to see if a move finished. |
| `void SetAnimationPhaseNow(string animation, float phase)` | :22 | Jump straight to the phase with no animation time; use after loading a save. |
| `proto native void ResetAnimationPhase(string animation, float phase)` | :28 | Used by `SetAnimationPhaseNow` to skip the timing. |
| `void OnAnimationPhaseStarted(string animSource, float phase)` | :33 | Callback from the engine when a phase change starts. |
| `proto int GetNumUserAnimationSourceNames()`, `proto string GetUserAnimationSourceName(int index)` | :17, :19 | List the user sources an object has. |

`animation` is the source name from `class AnimationSources` (see `animation-sources.md`), and `phase` is a value inside the `model.cfg` animation's `minValue` to `maxValue`.

## Buildings: the door API, no mod script needed

`Building` has the door calls, indexed by door number (`P:\scripts\3_game\entities\building.c`): `GetDoorIndex(int componentIndex)` :28, `GetDoorCount()` :31, `IsDoorOpen(int index)` :34, `OpenDoor(int index)` :61, `CloseDoor(int index)` :64, `LockDoor(int index, bool force = false)` :67, `UnlockDoor(int index, bool animate = true)` :70. `Building` also has override hooks such as `OnDoorOpenStart` :102 and `OnDoorCloseFinish` :127. Mod buildings script against `BuildingBase` (`P:\scripts\4_world\entities\game\super\building.c:8`), which the door action casts to.

`PlayerBase` registers `ActionOpenDoors` for every player (`P:\scripts\4_world\entities\manbase\playerbase.c:1697`). On the server it finds the door from the aimed component and calls `OpenDoor` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:59` to `:75`). So a mod building with a correct `class Doors` and matching `model.cfg` needs no script. Write script only to change behavior, for example a keypad lock that calls `LockDoor`.

## Items: pattern 1, net synced state (barrel lid)

Use this when a moving part shows a state that clients must see and saves must keep. From `Barrel_ColorBase`, `P:\scripts\4_world\entities\itembase\barrel_colorbase.c`:

1. Keep the state in a variable and register it for net sync in `InitItemVariables` (:21, `RegisterNetSyncVariableBool("m_Openable.m_IsOpened")`).
2. Put every `SetAnimationPhase` call in one method that reads the state (:144 to :156, `UpdateVisualState`).
3. Call it after the state changes on the server (`Open` :87, `Close` :106) and in `OnVariablesSynchronized` on clients (:158 to :163).
4. Save the state in `OnStoreSave` and apply it in `OnStoreLoad` (:52 to :80), then call `SetSynchDirty()` (:100).
5. An action changes the state on the server: `ActionOpenBarrel.OnExecuteServer` calls `Open()` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopenbarrel.c:27` to `:33`), and the item registers it in `SetActions` (`barrel_colorbase.c:566`).

## Items: pattern 2, server sets the phase (fence gate)

`Fence.OpenFence` sets the phase only on the server and then syncs its own state (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:488` to `:513`). It polls `GetAnimationPhase("Wall_Gate_Rotate")` with `CallLater` until the gate reaches 100 (:577 to :585) before doing follow up work. Use this when other server logic must wait for the move to end.

## Which side

- Change state on the server. The user action runs `OnExecuteServer` or `OnStartServer`.
- Clients must end with the same phase. Pattern 1 does that by calling the same method in `OnVariablesSynchronized`.
- Sounds tied to the move play on clients only (`fence.c:516`, `if (!g_Game.IsHeadlessOrDedicatedServer())`).

## The player's own animation

An action also plays a player animation through `m_CommandUID`, for example `DayZPlayerConstants.CMD_ACTIONMOD_OPENDOORFW` for doors (`actionopendoors.c:7`) and `CMD_ACTIONMOD_INTERACTONCE` for the barrel (`actionopenbarrel.c:5`). Pick an existing command; new player animations are out of scope (see `rtm-and-character-animation.md`).
