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

Related calls on other classes:

| Call | Where | Use |
|---|---|---|
| `GetSelectionPositionLS(string name)`, `GetSelectionPositionMS`, `GetSelectionPositionWS` | `Object`, `P:\scripts\3_game\entities\object.c:863` to `:865` | Where a selection is now, with animations applied, in local, model or world space. |
| `GetSelectionBasePositionLS(string name)` | `Object`, `P:\scripts\3_game\entities\object.c:871` | Where it was modelled, with no animation applied. The difference from the call above is how far the part has moved. |
| `HideSelection(string selection_name)`, `ShowSelection` | `EntityAI`, `P:\scripts\3_game\entities\entityai.c:3355`, `:3364` | Shortcuts for a hide source named after the selection: phase 1 hides, 0 shows (`:3359`). |

A phase that reads back as expected does not prove the part moved or that the source exists on that object; list the sources first (`animation-sources.md`, "Checking that a source exists").

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
- Two writers of one source, the owning client locally and the server through sync, only coexist when they write the same target. For a part that follows a long action, let the server write the start and the end and the owning client the states between (measured by the source knowledge pack on 1.30; method in `skills/dayz-animation-pipeline/references/item-ik-and-hide.md`).
- A steering part is not a script job at all: use the engine's `steeringwheel` source in `model.cfg`. The source knowledge pack reports that a steering visual set from the client through a `user` source snapped back to 0 in multiplayer.

## The player's own animation

An action also plays a player animation through `m_CommandUID`, for example `DayZPlayerConstants.CMD_ACTIONMOD_OPENDOORFW` for doors (`actionopendoors.c:7`) and `CMD_ACTIONMOD_INTERACTONCE` for the barrel (`actionopenbarrel.c:5`). Pick an existing command; new player animations are out of scope (see `rtm-and-character-animation.md`).

The command constants are in `DayZPlayerConstants` (`P:\scripts\3_game\dayzplayer.c`): the `CMD_ACTIONMOD_` group plays over the player's movement and the `CMD_ACTIONFB_` group takes the full body. 1.30 added, among others, `CMD_ACTIONMOD_COMBINATIONLOCK` (:766), `CMD_ACTIONFB_BRICKSTACK` (:892), `CMD_ACTIONFB_MIX_MORTAR` (:894) and `CMD_ACTIONFB_SHARPEN` (:896); the full list of additions is in `skills/dayz-animation-pipeline/references/anim-graph.md`.

Since 1.30 script can also switch the player's whole animation instance without an item in the hands, with `SetAnimationInstanceByName` (`P:\scripts\3_game\human.c:1384`); see `items-in-hands.md`.

## Reading a pose back from script

For a test that has to measure what the game really shows, not what was sent:

| Call | Where | Use |
|---|---|---|
| `GetBoneIndexByName(string pBoneName)` | `Human`, `P:\scripts\3_game\human.c:1417` | A skeleton bone's id. Vanilla uses it for `RightHand_Dummy` (`P:\scripts\4_world\entities\dayzplayerimplement.c:628`). The source pack measured on 1.30 that valid ids can be negative (`RightHand` among them); only −1 means the bone is missing. |
| `GetBonePositionMS(int pivot)`, `GetBoneRotationMS(int pivot, out float quaternion[4])` | `Object`, `P:\scripts\3_game\entities\object.c:237`, `:242` | A bone's position and rotation in model space, which does not depend on where the entity stands or faces. |
| `GetBonePivotsForAnimationSource(int level, string animationSource, out TIntArray pivots)` | `Object`, `P:\scripts\3_game\entities\object.c:233` | The bones a `model.cfg` animation source moves, so the part's real angle can be read with `GetBoneRotationMS`. Vanilla uses it for the motorbike's sounds (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:292`). |
| `OverrideRaise(HumanInputControllerOverrideType overrideType, bool value)` | `HumanInputController`, `P:\scripts\3_game\human.c:268` | Holds the weapon raised for a capture. `ENABLED` stays until `DISABLED` is passed (`P:\scripts\3_game\human.c:10`). |

Two results from the source pack's in-game tests on 1.30: a raise forced only on the server does not change the pose the owning client renders, so force it on the client; and a dedicated server placed a rider's hand 0.35 m from where the client did while pelvis and head agreed, so measure hand placement on the client. Methods: `skills/dayz-animation-pipeline/references/weapon-in-hands.md` and `skills/dayz-animation-pipeline/references/vehicle-rider-ik-pose.md`.
