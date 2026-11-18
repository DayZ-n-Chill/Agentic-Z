# Rider animation, the `vehicles.agf` graph and the camera

How the motorbike rider is animated: the human vehicle command, the text animation graph `vehicles.agf`, the vanilla `.anm` clips, the third-person camera, and which vanilla rider set a new bike should use. The rider's pose and how a mod changes it live in the animation pack (section 5). Short citations: `config.cpp:N` is `P:\DZ\vehicles\singletrack\config.cpp`, and a bare script file name is the file of that name under `P:\scripts\` (`motorbike_01.c` and `motorbike_02.c` are the ones in `4_world\entities\vehicles\inheritedmotorbikes\`). Line numbers match the 1.30 data on `P:\` at the time of writing; when a line has moved, Grep for the symbol. Results marked as measured were measured in game on DayZDiag 1.30.164014 with sport bike mods; they cannot be checked on `P:\`.

---

## 1. Human Control Methods and Interaction

### `HumanCommandVehicle`
- `bool IsTransitioning()` (`P:\scripts\3_game\human.c:735`):
  ```c
  bool IsTransitioning()
  {
      return IsGettingIn() || IsGettingOut() || IsSwitchSeat();
  }
  ```
  Unifies kinematic checks and blocks concurrent actions while the character enters, exits, or switches seats.
- `JumpOutVehicle()` (`proto native`, `human.c:725`): `ActionGetOutTransport` jumps out while moving when `m_Speed > m_JumpingOutThreshold` (`actiongetouttransport.c:164`) and then calls `JumpOutVehicle()` (`:185`). On motorbikes the threshold is `MOTO_JUMPOUT_THRESHOLD = 10.0` km/h (`:36`, assigned at `:157`) and speed comes from `GetSpeedometerAbsolute()` (`:158`).

---

## 2. Third-Person Camera: `DayZPlayerCamera3rdPersonVehicleMotorbike`

- **Registration**: `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32;` in `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20, 63`.
- **Implementation**: `DayZPlayerCamera3rdPersonVehicleMotorbike` in `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:239-470`.
- **Spring Damping (Spring Smooth Time)**:
  Like the car camera (`dayzplayercameravehicles.c:142-148`, with fixed time `0.3`), uses `Math.SmoothCD` and `Math.SmoothCDPI2PI` (`:369-375`), but with dedicated per-axis constants (`:256-265`):
  - `CONST_SPRING_SMOOTHTIME_YAW = 0.5;`
  - `CONST_SPRING_SMOOTHTIME_PITCH = 0.3;`
  - `CONST_SPRING_SMOOTHTIME_ROLL = 0.3;`
  - `CONST_SPRING_SMOOTHTIME_POS_X/Y/Z = 0.4;`
- **Yaw lag reverse and damping**:
  ```c
  // P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:387-390
  float lagYaw = tempRot[0];
  if (lagYaw > 180.0)
      lagYaw -= 360.0;
  rot[0] = -lagYaw * CONST_YAW_LAG_REVERSE; // CONST_YAW_LAG_REVERSE = 0.3
  ```
  Reverses and dampens the camera yaw swing when turning (vanilla comment: "reverse + dampen the yaw lag swing").

---

## 3. Enfusion Animation Graph: `vehicles.agf`

In 1.30 the vehicle graph ships as structured text: `P:\DZ\anims\workspaces\player\player_main\vehicles.agf` (3655 lines). The 1.29 data has no `.agf`, but its graphs are not binary: they are text `.agr` files in the old `$AnimGraph 7` format (line 1 of the 1.29 `player_main.agr`, and of the 1.29 `Vehicles.agr` for the vehicle sub-graph). That graph declares `#Var VehicleType int -1 -1 10 ""` (line 99 of the 1.29 `player_main.agr`) and has no `Jawa_*` column, so the motorbike rider is new in 1.30. The 1.29 files are not part of the 1.30 data, so these 1.29 facts are not yet checked on `P:\`.

### Vehicle Type Selector (`MotorBikeB`)
```enfusion
// [EXACT] P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1564-1576
    AnimSrcNodeBlendT MotorBikeB {
     EditorPos 4 -18.3
     BlendTime "0.3"
     BlendFn S
     TriggerOn ""
     TriggerOff ""
     Condition "VehicleType == 10 || VehicleType == 11"
     Child0 "VehicleSTM"
     Child1 "MotorBikeSTM"
     OptimizeMin 1
     OptimizeMax 1
     SelectMainPath 0
    }
```
- `VehicleType == 10`: `VehicleAnimInstances.MOTO1` (`Motorbike_01`).
- `VehicleType == 11`: `VehicleAnimInstances.MOTO2` (`Motorbike_02`).

### State Machine `MotorBikeSTM` (`vehicles.agf:1582-1751`)
1. `Idle`: Stretched-out riding or rest with hand IK active (`Child "AnimNodeIK2hands"`).
2. `GetIn_L` / `GetIn_R`: Directional get-in from left or right with `"TagVehicleGetIn"` tag.
3. `GetOut_L` / `GetOut_R`: Get-out at a complete stop (`IsExit 1`).
4. `JumpOut_L` / `JumpOut_R`: Running jump-out at speed with ground impact animation.
5. `Death`: Death on the seat (`IsCommand(CMD_Death) && !IsTag("TagVehicleGetIn")`).
6. `GettingInDeath`: Death while mounting the motorbike.

---

## 4. Animation Clips (.anm) of Jawa_05 and Jawa_Bitrak

The `.anm` clips are binary. `P:\DZ\anims\workspaces\player\player_main\player_main.asi` (not to be confused with that of `player_inventory`) references them as `DZ/anims/anm/player/vehicles/Jawa_05/…` and `DZ/anims/anm/player/vehicles/Jawa_Bitrak/…`, which on `P:\` are the folders `P:\DZ\anims\anm\player\vehicles\jawa_05\` and `jawa_bitrak\`. Columns `"Jawa_05"` and `"Jawa_Bitrak"` are in `player_main.ast:1119-1120`; `Jawa_05` instances occupy `player_main.asi:5088-5144` and `Jawa_Bitrak` instances start at line `5145`.

### `Motorbike_01` (`Jawa_05`) Mapping
Instances `Vehicle.Jawa_05.*` present in `player_main.asi:5088-5144`:
- Riding: `DriverIdle`, `DriverSteeringMain`, `DriverSteeringExtreme`, `DriverWobble`, `DriverCollision`, `DriverAimIdle`, `AccelerationSpine`, `AccelerationSpineUD`, `IdleToDrive`, and `DriveToIdle`.
- Entry, exit, and jump-out: `DriverGetIn_L`/`_R`, `DriverGetOut_L`/`_R`, and `DriverJumpOut_L`/`_R`.
- Death and unconsciousness: `DriverDeath`, `DriverUnconsciousIdle`, and `DriverUnconsciousDeath`.

### Implications for a New Motorbike Modder
- If ergonomics of your motorbike (seat height, handlebar reach, footpegs) resemble an enduro or light moped, **use `VehicleAnimInstances.MOTO1`**.
- If your motorbike is heavier, wider, or upright / cruiser posture, **use `VehicleAnimInstances.MOTO2`**.
- Both instances are free and work out-of-the-box without touching the graph.

---

## 5. Rider pose, boarding side and falling off

The rider's pose, the hand IK on the bars, the left and right boarding states, ejection when the bike falls and the fall when a rider dies are animation subjects, and their one home is the animation pack:

- `skills/_shared/animation/rider-poses.md`: where the driver's body and hands come from (clips, not the bike model; no IK node reads a vehicle memory point), the steering pose read over 45 degrees of wheel angle, the four pieces of the motorbike pose, the child `.asi` route that changes the pose for one bike class without replacing the graph, the boarding side (`HasDirectionalInOutAction`, `GetSeatAnimationTypeDirectional`) and ejection.
- `skills/_shared/animation/rider-pose-solver.md`: solving a pose from anchors on the model, and everything measured in game with the child `.asi` route and with generated clips.
- `skills/_shared/animation/anim-graphs.md`, "Which changes collide": why replacing `player_main` is a wall that only one mod can cross.
