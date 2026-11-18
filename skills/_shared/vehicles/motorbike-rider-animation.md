# Motorbike rider animation and camera

How the motorbike rider is animated: the human vehicle command, the `vehicles.agf` animation graph, the vanilla rider clips, the third-person camera, and which vanilla rider set a new bike should use. The rider's pose and how a mod changes it belong to the animation pack (see the last section).

## The vehicle command

`HumanCommandVehicle.IsTransitioning()` returns `IsGettingIn() || IsGettingOut() || IsSwitchSeat()` (`P:\scripts\3_game\human.c:735`), so it blocks other actions while the rider gets on, off or changes seat.

`JumpOutVehicle()` is native (`human.c:725`). `ActionGetOutTransport` treats the exit as a jump-out when `m_Speed` is above the jump-out threshold (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:164`), then calls `JumpOutVehicle()` (`:185`). On a motorbike the threshold is `MOTO_JUMPOUT_THRESHOLD = 10.0` km/h (`:36`, set at `:157`) and the speed comes from `GetSpeedometerAbsolute()` (`:158`).

## Third-person camera

The bike has its own camera, `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32`, registered to `DayZPlayerCamera3rdPersonVehicleMotorbike` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20` and `:63`). The class is in `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:239` to `:470`.

Like the car camera, which smooths every axis with a fixed time of `0.3` (`dayzplayercameravehicles.c:142` to `:148`), it uses `Math.SmoothCD` and `Math.SmoothCDPI2PI` (`:369` to `:375`), but with its own constants per axis (`:256` to `:265`):

| Constant | Value |
|---|---|
| `CONST_YAW_LAG_REVERSE` | `0.3` |
| `CONST_SPRING_SMOOTHTIME_YAW` | `0.5` |
| `CONST_SPRING_SMOOTHTIME_PITCH`, `_ROLL` | `0.3` |
| `CONST_SPRING_SMOOTHTIME_POS_X`, `_POS_Y`, `_POS_Z` | `0.4` |

The yaw swing in a turn is reversed and damped (`:387` to `:390`), with the vanilla comment "reverse + dampen the yaw lag swing":

```c
float lagYaw = tempRot[0];
if (lagYaw > 180.0)
    lagYaw -= 360.0;
rot[0] = -lagYaw * CONST_YAW_LAG_REVERSE;
```

## The `vehicles.agf` graph

The vehicle graph ships as text in `P:\DZ\anims\workspaces\player\player_main\vehicles.agf` (3,655 lines). The DayZ 1.29 data had no `.agf`; its graphs were text `.agr` files in the older `$AnimGraph 7` format, declared `VehicleType` with a range up to 10 and had no `Jawa_*` column, so the motorbike rider is new in 1.30. The 1.29 files are not on `P:\`, so that comparison is not checked there.

The node that picks the bike branch (`vehicles.agf:1564` to `:1576`):

```text
AnimSrcNodeBlendT MotorBikeB {
 BlendTime "0.3"
 BlendFn S
 Condition "VehicleType == 10 || VehicleType == 11"
 Child0 "VehicleSTM"
 Child1 "MotorBikeSTM"
}
```

`VehicleType` 10 is `VehicleAnimInstances.MOTO1` (`Motorbike_01`) and 11 is `MOTO2` (`Motorbike_02`).

The state machine `MotorBikeSTM` (`vehicles.agf:1582` to `:1751`) has these states:

| State | What it plays |
|---|---|
| `Idle` | Riding or resting, with hand IK on (`Child "AnimNodeIK2hands"`) |
| `GetIn_L`, `GetIn_R` | Get on from the left or right, tagged `TagVehicleGetIn` |
| `GetOut_L`, `GetOut_R` | Get off at a full stop (`IsExit 1`) |
| `JumpOut_L`, `JumpOut_R` | Jump off at speed, with the landing |
| `Death` | Death on the seat (`IsCommand(CMD_Death) && !IsTag("TagVehicleGetIn")`) |
| `GettingInDeath` | Death while getting on |

## Rider clips

The `.anm` clips are binary. `P:\DZ\anims\workspaces\player\player_main\player_main.asi` (not the one of `player_inventory`) points at them under `P:\DZ\anims\anm\player\vehicles\jawa_05\` and `jawa_bitrak\`. The columns `"Jawa_05"` and `"Jawa_Bitrak"` are in `player_main.ast:1119` and `:1120`; the `Jawa_05` instances fill `player_main.asi:5088` to `:5144`, and the `Jawa_Bitrak` ones start at `:5145`.

The `Vehicle.Jawa_05.*` instances used by `Motorbike_01`:

- Riding: `DriverIdle`, `DriverSteeringMain`, `DriverSteeringExtreme`, `DriverWobble`, `DriverCollision`, `DriverAimIdle`, `AccelerationSpine`, `AccelerationSpineUD`, `IdleToDrive`, `DriveToIdle`.
- Getting on and off: `DriverGetIn_L` and `_R`, `DriverGetOut_L` and `_R`, `DriverJumpOut_L` and `_R`.
- Death and unconsciousness: `DriverDeath`, `DriverUnconsciousIdle`, `DriverUnconsciousDeath`.

## Which rider set to use

Both sets work without touching the graph. Return the one that fits from `GetAnimInstance()`:

- `VehicleAnimInstances.MOTO1` for a bike shaped like an enduro or light moped: seat height, bar reach and footpegs.
- `VehicleAnimInstances.MOTO2` for a heavier or wider bike, or an upright cruiser posture.

## Rider pose, boarding side and falling off

These are animation subjects, kept in the animation pack:

- `_shared/animation/rider-poses.md`: where the driver's body and hands come from (clips, not the bike model; no IK node reads a vehicle memory point), the steering pose over 45 degrees of wheel angle, the four pieces of the motorbike pose, the child `.asi` route that changes the pose for one bike class without replacing the graph, the boarding side (`HasDirectionalInOutAction`, `GetSeatAnimationTypeDirectional`) and ejection.
- `_shared/animation/rider-pose-solver.md`: solving a pose from anchors on the model; `_shared/animation/rider-pose-measured.md`: what was measured in game with the child `.asi` route and with generated clips.
- `_shared/animation/anim-graphs.md`, on which changes collide: why replacing `player_main` is something only one mod can do.
