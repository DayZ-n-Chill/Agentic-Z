# Rider poses: what places a driver's body and hands

How the vanilla graph poses a player on a vehicle, what that means for a mod vehicle whose shape differs, and the one way to change the pose for a single vehicle class without replacing the player graph. Solving a pose from anchors on the model, the tools and every measured result are in `rider-pose-solver.md`. The vehicle's own config and seats belong to the vehicles pack.

## The pose comes from clips, not from the vehicle model

Each vehicle type is a column of the player template's `Vehicle` groups: `CivilianSedan`, `Hatchback_02`, `Jawa_05`, `Jawa_Bitrak` and the rest (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1114` to `:1127`). The base instance maps every line of a column to a clip, for example `Vehicle.Jawa_Bitrak.DriverSteeringMain` (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:5178`).

The hands are put on the steering by IK nodes in the vehicle sub-graph, and those nodes read a pose, not the vehicle:

- `AnimNodeIK2Target0` takes its child pose and the two chain bindings `LHandIKTarget` and `RHandIKTarget` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:17` to `:30`).
- `AnimNodeIK2hands` solves the two chains again with `SnapRotation 1` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:31` to `:46`).

None of the ten IK nodes in `vehicles.agf` reads a vehicle memory point, a bone of the vehicle or a config value. Most bind both hand chains; the engine start pair binds the left hand only (`MotoEngineIKTarget`, `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1436`, and `MotoEngineVehicleIK`, `:1446`). The file has no foot IK at all: the text `FootIK` does not occur in it. So the hands are wherever the steering pose clip leaves them. Memory points added to a mod vehicle for grips or footpegs are read by nothing in the game; a different grip position needs different clips.

## The steering pose is read by wheel angle

A steering pose is one clip read at a time worked out from the steering variable:

```
AnimSrcNodePose AnimNodePose {
 Source "Vehicle.DriverSteeringMain"
 Time "clamp((VehicleSteering + 0.785) * 0.63694267515923566878980891719745, 0.0, 1.0)"
}
```

(`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:47` to `:51`; the motorbike's stopped pose `MotoIdleSteeringP` uses the same `Time` expression at `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1466`.) The clip therefore spans −0.785 to +0.785 of `VehicleSteering`. Measured in game on 1.30, `VehicleSteering` on the motorbike is the wheel angle in radians, so the clip covers 45 degrees each way whatever the vehicle's steering lock: a clip authored over the lock instead put the hands 44 mm off at full lock.

## The motorbike pose has four pieces

The 1.30 motorbike graph separates standing from riding:

| Piece | Line of the column | When |
|---|---|---|
| Stopped pose | `DriverSteeringExtreme` | `SteeringBlend` picks it while the condition `(!VehicleWalking && VehicleSpeed >= 0.5)` is false (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:2614` to `:2626`). |
| Riding pose | `DriverSteeringMain` | The same node, condition true. |
| Pulling away | `IdleToDrive` | The state machine `Idle_MotorBikeSTM` enters `IdleToDrive` on `VehicleSpeed >= 0.5 && !VehicleWalking` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1248` to `:1251`). |
| Stopping | `DriveToIdle` | It enters `DriveToIdle` on `VehicleSpeed < 0.5 \|\| VehicleWalking` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1267` to `:1270`). |

The clip nodes are `IdleToDriveAnim` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1169` to `:1171`) and `DriveToIdleAnim` (`:610` to `:612`). By its clip name `DriverSteeringExtreme` is the stopped pose: for the `Jawa_Bitrak` column it is `p_motorbike_02_driver_idle_steering_pose.anm` (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:5175` to `:5177`). A design for a sport bike: stopped, the feet are down and the rider leans further to the low bars; `IdleToDrive` lifts the feet onto the pegs and tucks; riding is the full tuck; `DriveToIdle` puts the feet down.

The vanilla transition clips hold differences over a base pose. Measured in game on 1.30: a clip made with DayZATool plays as an absolute pose, so a mod's own transitions must be written as absolute whole body poses, or the spine collapses during the transition.

## Changing the pose for one vehicle class

Replacing `vehicles.agf`, the template or the base instance replaces the player graph for everyone (`anim-graphs.md`, "Which changes collide"). The route that avoids it uses the instance switch vanilla added in 1.30 for the surrender pose:

1. A child instance file whose `ParentTemplates` names `player_main.asi`, the shape of `player_main_surrender.asi` (`P:\DZ\anims\workspaces\player\player_main\player_main_surrender.asi:1` to `:5`), holding only the lines of the column the vehicle rides on.
2. The file registered as a profile in the mod callback `RegisterCustom` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:329`, class at `:305`, called by vanilla at `:1570`), the way vanilla registers `SurrenderDummyItem` and `"Empty"` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1543`, `:1548`; the comment at `:1546` says `Empty` exists so the character can switch back with `SetAnimationInstanceByName`).
3. The switch in script while the player rides that class: `EnableAutoAnimInstUpdateOnHandsChange(false)` and `SetAnimationInstanceByName` with the child's path, as surrender does (`P:\scripts\4_world\entities\manbase\playerbase.c:2087`, `:2088`); back to `player_main.asi` with the automatic switch on again when the player gets out (`P:\scripts\4_world\entities\manbase\playerbase.c:2104` to `:2107`). `PlayerBase` has the hooks `OnCommandVehicleStart` and `OnCommandVehicleFinish` (`P:\scripts\4_world\entities\manbase\playerbase.c:4342`, `:4375`).

That the mechanism exists is checked above. That a mod's child instance changes the rider's pose on one class only, on a dedicated server and the owning client, is measured in game on 1.30, not checked on `P:\` (`rider-pose-solver.md`); remote observers, late join, a held item, unconsciousness and death were not tested. The native's own comment warns that the switch can desync when misused (`SetAnimationInstanceByName`, `P:\scripts\3_game\human.c:1383` to `:1384`).

## Boarding side and falling off

- The motorbike's get in side is chosen in `ActionGetInTransport` when the transport's `HasDirectionalInOutAction()` is true (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:81` to `:100`; the method on `Transport` is at `P:\scripts\3_game\vehicles\transport.c:677`). The seat animation type it passes on comes from `GetSeatAnimationTypeDirectional`, which on the vanilla bikes returns 0 for the left and 1 for the right side of the driver seat (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:58` to `:69`). The graph has a state per side: `GetIn_L` on `GetCommandI(CMD_Vehicle_GetIn) == 0` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1612` to `:1618`), `GetIn_R` on 1, and `GetOut_L`, `GetOut_R`, `JumpOut_L` and `JumpOut_R` as well. A vehicle with its own boarding clips needs a left and a right version of each. The scripted alternative used before 1.30 is in `get-in-sides.md`.
- A fallen motorbike ejects its rider: `CrewShouldEject` returns `IsFallen()` (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:464` to `:466`), and the player code then activates `MDF_UNCONSCIOUSNESS` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2458`); Bohemia's own comment just above calls this temporary until a ragdoll command exists.
- When any rider dies on the bike, driver or passenger, `motorbike.FallOver()` tips it; the call sits after the driver only seat check (`VEHICLESEAT_DRIVER`), not inside it (`P:\scripts\4_world\entities\dayzplayerimplement.c:713` and `:728` to `:731`).
- The clip list per column (`Jawa_05` is `Motorbike_01`, `Jawa_Bitrak` is `Motorbike_02`) and the vehicle config are in `skills/_shared/vehicles/motorbike-rider-animation.md`.

## Reading the real steering angle

To compare the hands with the bars in a test, read the animated part, not the input: find the bones the steering source moves and read their rotation. The calls and their vanilla use are in `script-hooks.md`, "Reading a pose back from script"; the motorbike recipe is in `rider-pose-solver.md`.
