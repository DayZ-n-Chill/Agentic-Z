# Rider animation, the `vehicles.agf` graph and the camera

How the motorbike rider is animated: the human vehicle command, the text animation graph `vehicles.agf`, the vanilla `.anm` clips, the third-person camera, and how far a mod can change the pose in DayZ 1.30. Short citations: `config.cpp:N` is `P:\DZ\vehicles\singletrack\config.cpp`, and a bare script file name is the file of that name under `P:\scripts\` (`motorbike_01.c` and `motorbike_02.c` are the ones in `4_world\entities\vehicles\inheritedmotorbikes\`). Line numbers match the 1.30 data on `P:\` at the time of writing; when a line has moved, Grep for the symbol. Measured results name the project they come from (LFDucati and LFRider, the knowledge pack author's unpublished mods; LL-nnn are that project's lesson numbers); they have not been repeated here.

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

### Directional Entry and Exit (Left / Right)
In `actiongetintransport.c:81-100`, vector math determines whether the rider gets on from the left or right side of the motorbike:
```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:81-100
		if (transport.HasDirectionalInOutAction())
		{
			vector fwd = transport.GetDirection();
			fwd[1] = 0;
			fwd.Normalize();
	
			vector playerPosition = action_data.m_Player.GetPosition();
			vector toTarget = transport.GetPosition() - playerPosition;
			toTarget[1] = 0;
			toTarget.Normalize();
	
			vector right = Vector(fwd[2], 0.0, -fwd[0]);
	
			float side = vector.Dot(toTarget, right);
	
			if (side < 0.0)
			    direction = 1;
		
			seat = transport.GetSeatAnimationTypeDirectional(crewIndex, direction);
		}
```
In `motorbike_01.c:58-69` and `motorbike_02.c:59-70`, `GetSeatAnimationTypeDirectional` returns animation indices associated with `GetIn_L` (0) and `GetIn_R` (1).

### Ejection on Tipover and Collapse on Death
- **Ejection**: In `dayzplayerimplement.c:2452-2459`, if `transport.CrewShouldEject(seatPos)` returns `true` (on motorbikes `IsFallen()`), the server provisionally activates `eModifiers.MDF_UNCONSCIOUSNESS` to force the rider's ejection from the seat while the native ragdoll command is unavailable.
- **Collapse**: In `dayzplayerimplement.c:728-732`, when the rider dies aboard the motorbike, `motorbike.FallOver()` is invoked, ensuring the motorbike loses gyroscopic balance and collapses onto the terrain.

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

In 1.30 the vehicle graph ships as structured text: `P:\DZ\anims\workspaces\player\player_main\vehicles.agf` (3655 lines). (corrected 2026-09-28) The knowledge pack's 1.29 data has no `.agf`, but its graphs are not binary, as this line used to say: they are text `.agr` files in the old `$AnimGraph 7` format (line 1 of the 1.29 `player_main.agr`, and of the 1.29 `Vehicles.agr` for the vehicle sub-graph). That graph declares `#Var VehicleType int -1 -1 10 ""` (line 99 of the 1.29 `player_main.agr`) and has no `Jawa_*` column, so the motorbike rider is new in 1.30. The 1.29 files are not part of the 1.30 data, so these 1.29 facts are not yet checked on `P:\`.

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

### Hand Fixing to Handlebars via IK
In `vehicles.agf:17-46`, two inverse kinematics chains are configured (`AnimSrcNodeIK2` and `AnimSrcNodeIK2Target`):
- `LHandIKTarget` (left hand) and `RHandIKTarget` (right hand).
- Attached to bone/node with weight `1.0` and forced rotation (`SnapRotation 1`).
- Ensures hands remain clamped to handlebar grips regardless of bumps and torso sway.

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

## 5. The "Graph Wall"

To create entirely custom poses (for example, a chopper with ape hangers or a sport bike with a forward tuck), compiling a new animation graph is required.

> [!WARNING] Graph conflict is global
> Only **one mod that replaces the player animation graph** (`player_main`) can be loaded; with two at once, client or server crashes. This is doctrine from the `dayz-animation-pipeline` skill (`references/tooling-and-walls.md`, wall 1) and cannot be verified in the vanilla files [UNVERIFIED here].
>
> For the `.txa` curve export pipeline to `.anm` clips, use the `dayz-animation-pipeline` skill.

### Per-bike pose without replacing the graph (added 2026-09-28, LFDucati rider research; child `.asi` measured the same day, LFDucati B1)

- **The hands come from the clip, not from the bike.** [EXACT] No IK node in `vehicles.agf` reads a vehicle memory point, bone or config value. `AnimNodeIK2Target0` sits over `SteeringBlend` (`vehicles.agf:17-30`), which plays `Vehicle.DriverSteeringExtreme` or `Vehicle.DriverSteeringMain` (`:2614-2626`), and `AnimNodeIK2hands` re-solves the arm chains toward `LHandIKTarget`/`RHandIKTarget` (`:31-46`). There is no foot IK. [INFERRED] The targets are where the steering pose leaves the hands, so another bar or footpeg position needs new clips; neither the P3D nor the config can move the hands.
- **A child `.asi` swapped in on one bike works while it stands, for the player tested (measured 2026-09-28, LFDucati B1, LL-530).** [EXACT, run on DayZDiag 1.30.164014: dedicated server and the owning client] LFDucati's test addon put the rider of one bike class on its own child `.asi` and left every graph file alone. The recipe, as run (`LFD_RiderAsi.c` in that addon):
  1. *The file.* A text `.asi` in the vanilla 1.30 format, header copied from `player_main_surrender.asi:1-6` (`AnimSetInstanceSource`, `Template` = `player_main.ast`, `ParentTemplates` = `player_main.asi`, both with their `{GUID}` prefixes), holding only the lines it overrides, such as `AnimSetInstanceSource_Line "Vehicle.Jawa_Bitrak.DriverSteeringMain" { Resource "{GUID}DZ/anims/anm/....anm" }` (the MOTO2 lines begin at `player_main.asi:5145`). Vanilla ships its own `.asi` files the same way in `anims_workspaces.pbo`: uncompressed text, LF, no final newline, no `.meta`. Packed as a plain file of the mod PBO (AddonBuilder `-packonly` keeps it), ours loaded with no Workbench step.
  2. *Registration*, which has to happen before the preload at `dayzplayercfgbase.c:1653`: `modded class ModItemRegisterCallbacks` → `override void RegisterCustom(DayZPlayerType pType)` calls `super`, builds a `DayzPlayerItemBehaviorCfg` with `SetEmptyHanded()` (`:199`) and calls `pType.AddItemInHandsProfileIK("<no such item>", "<pboprefix>/anims/<name>.asi", cfg, "")` (`P:\scripts\3_game\dayzplayer.c:243`). The item class need not exist, as with vanilla's `"Empty"` (`dayzplayercfgbase.c:1548`); the call returned 913 on both machines. `DayZPlayerTypeRegisterItems` runs twice per machine (`dayzplayercfgbase.c:12`, `:21`), and the client runs it again for the main-menu character.
  3. *The swap*, run on the dedicated server and on the owning client (the two machines tested). On: `GetItemAccessor().EnableAutoAnimInstUpdateOnHandsChange(false)`, then `SetAnimationInstanceByName("<pboprefix>/anims/<name>.asi", 0.5)`. Off: `EnableAutoAnimInstUpdateOnHandsChange(true)`, `SetAnimationInstanceByName("dz/anims/workspaces/player/player_main/player_main.asi", 0.5)`, then `GetItemAccessor().OnItemInHandsChanged(true)` (surrender's calls: `playerbase.c:2087-2088`, `:2104-2107`; `RefreshHandAnimationState`: `:4910`). Switch on in `PlayerBase.OnCommandVehicleStart` (`:4342`) when `GetCommand_Vehicle().GetTransport().IsKindOf("<bike class>")`; off as soon as `HumanCommandVehicle.IsGettingOut()` is true (`human.c:728`) and in `OnCommandVehicleFinish` before `super` (`playerbase.c:4375`), whose `RefreshHandAnimationState` (`:4384`) runs after it.

  Measured (LFDucati LOG T100): both machines received `OnCommandVehicleStart`/`OnCommandVehicleFinish` and ran `CommandHandler`; their switch-on calls were logged 24 ms apart, and their switch-off calls at the start of the get-out 5 ms apart. Stopped on the probe bike, with the sedan's steering poses in the two `DriverSteering*` lines, the owning client's samples put the left hand 0.84 m, the pelvis 1.01 m and the head 1.01 m from the same player on the same model without the swap (the server logged too few control samples for its own comparison), and the owner saw a seated car driver sunk into the bike. The same player stayed unswapped on the other bikes of the row. On exit both machines logged the switch back with `auto=1`; the instance itself was not read back (the debug instance fields came out empty), but the same player's stopped pose on three MOTO2 variants ridden afterwards matched the control's on both machines (pelvis 1.098 m high in the bike's model space, against 0.093 m with the swap), so the override was gone. Other riders, restoring a held item, remote observers and late join were not tested.

  Traps: (a) after the get-out clip ended, the command read as seated, not getting out, until `OnCommandVehicleFinish`, and a per-frame check switched the rider back on for 32 ms on the server and 28 ms on the client; latch it off from the start of the get-out until the vehicle command is gone. (b) (corrected 2026-09-28, LL-535) `Human.GetBoneIndexByName` returns hash-like ids, and several are negative (`RightHand` -1405358722, `RightFoot`, `RightToeBase`, `LeftForeArm`, `RightHandRing1`); the B1 probe treated every negative id as missing and this line used to say they returned -1. Only -1 means missing: tested that way, all of them resolved. (c) The server's hands are not the client's: for the same stopped pose the dedicated server put the left hand 0.35 m (vanilla pose) and 0.55 m (swapped pose) from where the client did, while pelvis and head agreed within a few millimetres; measure hand placement on the client.

  Not verified yet: the riding pose (the probe bike was not ridden), other riders, remote observers and late join, a weapon in hand, the delayed hand refresh (`playerbase.c:6197-6200`), unconsciousness, ejection and death. Survivor Animations' current graph has no `Jawa_*` lines for the child to override (below); whether another graph replacement keeps the `Vehicle.Jawa_Bitrak.*` bindings has to be checked per mod. Open gates: skill `dayz-animation-pipeline`, `references/vehicle-rider-ik-pose.md` §Per-vehicle pose without a graph change.
- **A custom pose comes in four pieces, because the graph already splits standing from riding.** [EXACT] `SteeringBlend` (`vehicles.agf:2614-2626`) blends `MotoIdleSteeringP` (`Vehicle.DriverSteeringExtreme`) and `AnimNodePose` (`Vehicle.DriverSteeringMain`) on `!VehicleWalking && VehicleSpeed >= 0.5`, and `Idle_MotorBikeSTM` plays `Vehicle.IdleToDrive` when that turns true (`:1248-1251`; source `:1169-1171`) and `Vehicle.DriveToIdle` when it turns false (`:1267-1270`; source `:610-612`). [INFERRED from the clip names] `DriverSteeringExtreme` is the stopped pose: its MOTO2 clip is `p_motorbike_02_driver_idle_steering_pose.anm` (`player_main.asi:5175-5177`), and the vanilla rider stands while stopped. [DESIGN] For a sport bike, as the LFDucati owner put it on 2026-09-28: stopped, stand with the feet down and just lean further to reach the clip-ons; `IdleToDrive` lifts the feet onto the pegs and tucks; riding, the full tuck in `DriverSteeringMain`; `DriveToIdle` puts the feet down.
- **Own clips on this route, measured end to end (added 2026-09-28, LFRider on the Kawasaki H2R; DayZDiag 1.30.164014, dedicated server and the owning client, one player; LL-533 to LL-535).** The shared optional mod `LFRider` (not published) generalizes the B1 swap: a config table `CfgLFRider >> Poses` (one class per pose: `vehicle` = bike class, matched with `IsKindOf`, an exact class wins; `asi` = the child `.asi`), every `.asi` registered in `RegisterCustom`, the switch in `OnCommandVehicleStart`, `CommandHandler` and a per-frame poll on clients (for riders a client only watches), latched off from the start of the get-out. What it measured:
  - Clips generated with `DayZATool --generate-anim <f>.seanim 100` (`ANIMSET5`) play: stopped, per-bone medians 0.1-0.5 mm from the clip's FK (single samples up to 37 cm in the blend after getting on); riding, pelvis 1.1-1.7 cm and head 2.1-2.6 cm medians (the graph's lean and acceleration layers). `Resource` works as a bare path. (Stopped medians from the 2026-09-28 runs; in later first-person probe runs, with the same clips in every run and the pelvis fixed, the stopped head moved by several cm between runs and looks: the in-game test session findings brought over with the same knowledge pack, "H2R import (2026-10)".)
  - The steering poses are read over +/-45 degrees of real wheel angle on every bike: `Time = clamp((VehicleSteering + 0.785) * 0.63694, 0, 1)` (`vehicles.agf:50` for `DriverSteeringMain`, `:1466` for `DriverSteeringExtreme`). Author frame `i` of `N` at `(2i/(N-1) - 1) * 45` degrees, clamped to the bike's lock; with the frames spread over the lock (20 degrees on the H2R) the hands stayed 44 mm behind the grips at full lock. With the 45-degree scale, the frame that best explains the measured hands (fit residual 0.3 mm per hand) sat at the bars' measured angle: 20.0 degrees stopped at full lock, and riding at 11-27 km/h (bars -16.0 to +17.4 degrees) within 1.2 degrees, 0.1 or less in 29 of 39 samples. That is the hands following the clip frame of the bars' angle; the grip contact comes from the solver (LL-531), not measured in game. The frame count is free (normalized time): 37 frames put a 20-degree lock on a frame.
  - Transitions (`IdleToDrive`, `DriveToIdle`) must be written as absolute, whole-body poses: the vanilla ones hold differences (pose = base * add per bone; `IdleToDrive` over the riding pose, `DriveToIdle` over the stopped one), but a DayZATool clip plays as an absolute pose, and difference data collapsed the rider's pelvis, spine, neck and head onto one point during the transitions (8 of 209 client and 9 of 218 server samples). Whole-body absolute clips: no collapse (210 client and 218 server samples).
  - The bars' real angle for a probe: `GetBonePivotsForAnimationSource(GetViewGeometryLevel(), "turnfront", pivots)` + `GetBoneRotationMS(pivots[0], q)` (`object.c:233`, `:242`; as `motorbikescript.c:287-292`). A scripted get-out: `ActionGetOutTransport` has no target and its `OnStart` calls `GetOutVehicle` (`actiongetouttransport.c:183`, `:220`); the switch back fired at the start of the get-out on both machines.
  - Getting on and off still play the vanilla clips (the leg over the tail) and blend into the new pose in ~0.3 s. Still open: remote observers and late join, a held item, unconsciousness, ejection, death, own get-in/get-out clips. Detail and numbers: `dayz-animation-pipeline`, `references/vehicle-rider-ik-pose.md` §Own clips on the rider.
- **Survivor Animations takes the other road: it replaces the graph.** [EXACT] Its `MOTORCYCLE = 16` (Workshop 2918418331, build of 15 Jul 2026: `SurvivorAnims.pbo` → `Scripts\4_World\CustomVehicleAnimInstances.c:8`) takes its body from the vanilla Offroad Hatchback **car** driver idle (`Vehicle.Motorcycle.DriverIdle`, `player_main.pbo` of that mod → `player_main.asi:2026`) and its hand IK targets from its own steering poses (`:2029-2030`; `Vehicles.agr:1976-1989`). [INFERRED] An upright car-driver body with the arms re-aimed, not a sport tuck; not seen in game. [EXACT] Its graph is in the 1.29 format (line 1 of the mod's `player_main.agr` = `$AnimGraph 7 {`) and has no `Jawa_*` lines, so on a server that loads it the child `.asi` route has nothing to override.
