# Rider poses: what places a driver's body and hands

How the vanilla graph poses a player on a vehicle, what that means for a mod vehicle whose shape differs, and the one way to change the pose for a single vehicle class without replacing the player graph. The solver, the tools and every measured result are in `skills/dayz-animation-pipeline/references/vehicle-rider-ik-pose.md`. The vehicle's own config and seats belong to the vehicles pack.

## The pose comes from clips, not from the vehicle model

Each vehicle type is a column of the player template's `Vehicle` groups: `CivilianSedan`, `Hatchback_02`, `Jawa_05`, `Jawa_Bitrak` and the rest (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1114` to `:1127`). The base instance maps every line of a column to a clip, for example `Vehicle.Jawa_Bitrak.DriverSteeringMain` (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:5178`).

The hands are put on the steering by IK nodes in the vehicle sub-graph, and those nodes read a pose, not the vehicle:

- `AnimNodeIK2Target0` takes its child pose and the two chain bindings `LHandIKTarget` and `RHandIKTarget` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:17` to `:30`).
- `AnimNodeIK2hands` solves the two chains again with `SnapRotation 1` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:31` to `:46`).

No IK node in `vehicles.agf` names a vehicle memory point or a config value, and the file has no foot IK. So the hands are wherever the steering pose clip leaves them. Memory points added to a mod vehicle for grips or footpegs are read by nothing in the game; a different grip position needs different clips.

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

The vanilla transition clips hold differences over a base pose. Measured in game on 1.30: a clip made with DayZATool plays as an absolute pose, so a mod's own transitions must be written as absolute whole body poses, or the spine collapses during the transition.

## Changing the pose for one vehicle class

Replacing `vehicles.agf`, the template or the base instance replaces the player graph for everyone (`anim-graphs.md`, "What collides"). The route that avoids it uses the instance switch vanilla added in 1.30 for the surrender pose:

1. A child instance file whose `ParentTemplates` names `player_main.asi`, the shape of `player_main_surrender.asi` (`P:\DZ\anims\workspaces\player\player_main\player_main_surrender.asi:1` to `:5`), holding only the lines of the column the vehicle rides on.
2. The file registered as a profile in the mod callback `RegisterCustom` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:329`), the way vanilla registers `SurrenderDummyItem` and `"Empty"` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1543`, `:1548`).
3. The switch in script while the player rides that class: `EnableAutoAnimInstUpdateOnHandsChange(false)` and `SetAnimationInstanceByName` with the child's path, as surrender does (`P:\scripts\4_world\entities\manbase\playerbase.c:2087`, `:2088`); back to `player_main.asi` with the automatic switch on again when the player gets out (`P:\scripts\4_world\entities\manbase\playerbase.c:2104` to `:2107`). `PlayerBase` has the hooks `OnCommandVehicleStart` and `OnCommandVehicleFinish` (`P:\scripts\4_world\entities\manbase\playerbase.c:4342`, `:4375`).

That the mechanism exists is checked above. That a mod's child instance changes the rider's pose on one class only, on a dedicated server and the owning client, is measured in game on 1.30, not checked on `P:\`; remote observers, late join, a held item, unconsciousness and death were not tested. The native's own comment warns that the switch can desync when misused (`SetAnimationInstanceByName`, `P:\scripts\3_game\human.c:1384`).

## Boarding side and falling off

- The motorbike's get in side is chosen in `ActionGetInTransport` when the transport's `HasDirectionalInOutAction()` is true (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:81` to `:100`), and the graph has a state per side: `GetIn_L` on `GetCommandI(CMD_Vehicle_GetIn) == 0` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1612` to `:1618`), `GetIn_R` on 1. A vehicle with its own boarding clips needs both sides.
- A fallen motorbike ejects its rider: `CrewShouldEject` returns `IsFallen()` (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:464` to `:466`), and the player code then activates `MDF_UNCONSCIOUSNESS` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2458`).

## Reading the real steering angle

To compare the hands with the bars in a test, read the animated part, not the input: `GetBonePivotsForAnimationSource(int level, string animationSource, out TIntArray pivots)` and `GetBoneRotationMS(int pivot, out float quaternion[4])` on `Object` (`P:\scripts\3_game\entities\object.c:233`, `:242`). Vanilla uses the first for its motorbike sounds (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:292`).
