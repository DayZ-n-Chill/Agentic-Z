# SIB helicopter

How the SIB helicopter mod (Workshop `3485438937`, internal `ver=8.041`) flies a `CarScript` child: its class layout, the simple `SetVelocity` loop, the JSON coefficient store, inputs and actions, rotor animation, damage zones, and what cannot be read. Open it for a second, simpler kinematic example beside `helicopter-rffs.md`, or for collective, cyclic, anti-torque, rotor animation, engine start and stop, the altitude ceiling or helicopter damage zones.

Everything here describes the SIB mod's scripts, which are not in this repo and not vanilla. The mod ships obfuscated; its server and client script PBOs were de-obfuscated and the readable files read. They carry generated names, and citations are `file:line` into them (`SERVER\unknown_16894.c`, `CLIENT\unknown_15761.c`). Do not build from SIB: its advanced core cannot be read, and the readable model is a homegrown kinematic hack rather than a modelled rotor. Build from RFFS (`helicopter-rffs.md`, kinematic) or MH6 (`helicopter-mh6.md`, force-based), as `helicopters.md` says.

## Class layout

`HeliTest_SIB : Heli_sib_cript : CarScript`, defined in `CLIENT\unknown_15761.c`:

| Layer | Adds | Source |
|---|---|---|
| `CarScript` (vanilla) | Wheels, seats, fuel, damage, sound | |
| `Heli_sib_cript : CarScript` | A full `SimulationModule` with four wheels for taxiing, `Crew` with driver and co-driver, car `AnimationSources` (`DoorsDriver`, `HideDestroyed_*`, `AnimHitWheel_*`), electrical and fuel stubs (`fuelCapacity=50`, `electricConsumptionIgnition=3001`) | `:117` to `:287` |
| `HeliTest_SIB : Heli_sib_cript` | Rotor and flight `AnimationSources` (`hide_rotor`, `hide_start`, `rot_h_start`, `rot_h_blur_end`, `rot2_h_*`, `toplivo`, dial sources), crew of driver, co-driver and two cargo, helicopter `DamageZones`, `Cargo`, `ObstacleGenerator` | `:288` to `:710` |

The config still declares wheels, axles, steering and gearbox (`drive="DRIVE_AWD"`, `class Engine{torqueMax=114;…}`, `:315` to `:420`) as the ground fallback; the helicopter overrides `EOnSimulate` and moves itself. Size variants `HeliSIB_big`, `middle`, `little`, `minimal` and `none` differ only in `Cargo` (`:711` to `:755`).

## The simple model

`SERVER\unknown_16894.c` (the client copy is identical through the class body) is fully readable and has no licence check.

Coefficients, defaults in the class body, overwritten from JSON by `go_conf()`:

| Field | Default | Role | Source |
|---|---|---|---|
| `c_startDurationInv` | `0.05` | Inverse of engine spin-up time | `:26` |
| `c_liftForceCoef` | `3.0` | Lift strength | `:27` |
| `c_altNoForce` | `500.0` (`c_altNoForce=500`) | Altitude where lift reaches 0 | `:28` |
| `c_altFullForce` | `450.0` | Altitude below which lift is full | `:29` |
| `c_cyclicAsideForceCoef` | `1.3` | Sideways strength | `:30` |
| `c_cyclicForwardForceCoef` | `1.0` | Forward strength | `:31` |
| `c_bodyFrictionCoef` | `0.3` | Body friction | `:32` |
| `c_heliMass` | `1500.81` | Mass | `:33` |

Reading `Simulate()` shows that most of these are loaded but not used by the simple model, which runs on literals; they are what the advanced model consumes.

`EOnSimulate` (server only) gates on two animation phases and runs input then integration (`:425` to `:452`):

```c
anim_rotor  = GetAnimationPhase("hide_rotor");
anim_engine = GetAnimationPhase("hide_start");
KeyboardPilot(dt, anim_engine, anim_rotor);   // inputs into m_RollKey, m_PitchKey, m_Yaw, m_rotorTurn
Simulate(dt, anim_engine, anim_rotor);
```

Inputs (`KeyboardPilot`, `:124` to `:201`) come from `playerObj.GetInputInterface().SyncedValue("UASIBHeli<X>")`, each true at 0.5 or more:

| Input | Effect | Meaning |
|---|---|---|
| `UASIBHeliCyclicRight`, `Left` | `m_RollKey ∓ 0.6` | Roll |
| `UASIBHeliBack`, `Forward` | `m_PitchKey ∓ 0.6` | Pitch |
| `UASIBHeliLeft`, `Right` | `m_Yaw ± 0.6` | Yaw |
| `UASIBHeliUp`, `Down` | `m_rotorTurn = ±2.8` | Climb and descend |

`Simulate` (`:298` to `:391`):

1. Height above the surface, `m_height = Distance(GetPosition, SurfaceY-projected pos)` (`:300` to `:303`). Above 1,500 m the rotor and engine are hidden, a kill switch (`:319`). Between 5 and 6 m angular velocity is zeroed with `dBodySetAngularVelocity(this, "0 0 0")` to settle a landing (`:326` to `:329`; `P:\scripts\1_core\proto\enphysics.c:165`).
2. At zero health (`GetHealth("","") <= 0`): hide rotor and engine, set `m_isDead`, `SetSynchDirty()`, freeze the rotors (`:306` to `:315`).
3. Pitch to speed (`HeliPitch`, `:204` to `:221`): nose down past -5 degrees (`< -5`) raises `m_heliSpeed` (cap 60), nose up past 5 lowers it (floor -10). Forward motion is a side effect of attitude, not a thrust vector.
4. Bank to yaw (`HeliRoll`, `:224` to `:258`): roll turns the helicopter; past 59 degrees it forces a descent (`m_rotorTurn = -3.0`). Yaw is written with `SetOrientation`.
5. Levelling (`AutoAlignment`, `:262` to `:292`): without roll or pitch input (`m_RollKey==0`, `m_PitchKey==0`), nudge back toward level by 0.1 per tick outside a 3 degree dead zone. An attitude recentre, not a PID.
6. Attitude: rotate `GetOrientation()` by `Math.RAD2DEG * key * dt` and `SetOrientation` (`:349` to `:353`).
7. Velocity (`:360` to `:387`): forward is heading sine and cosine times `m_heliSpeed` (`:365` to `:371`); vertical is `m_rotorTurn`, and with no collective a constant +0.25 m/s up is applied (`:384`), the passive hover. `SetVelocity(this, m_Velocity)` (`:387`; `P:\scripts\1_core\proto\enphysics.c:111`) sets the velocity, so nothing carries over between ticks: an arcade feel.

There is no lift curve in the simple model: lift is the +0.25 m/s baseline plus `m_rotorTurn`. The 450 and 500 m coefficients are declared, but the clamp is the literal 1,500 m, so the documented ceiling is unused. Whether the advanced model uses the 450 to 500 band cannot be read.

## The advanced model

`SERVER\unknown_16458.c`, `CLIENT\unknown_18705.c` and `SERVER\unknown_10783.c`. Every method is name-mangled and every entry is guarded by `license_active_helisib`, set only after an HTTP GET to the mod's licence server returns a signed config (`unknown_10783.c:319` to `:395`). Drop the whole licence layer from anything you write; it is this mod's DRM, not part of flight.

Readable:

- Forces: the only readable `dBodyApplyForce` and `dBodyApplyTorque` calls are in the helper `qmdkldkpqpmlsib` (`unknown_10783.c:454`, `:455`), which applies a target velocity change times `dBodyGetMass(...)` as a force, plus a torque, using matrix helpers in `Transform_SIB` (`unknown_18705.c:4` to `:28`).
- An autopilot: `AutopilotState_SIB { Far, Brake, Near, Align, Reached }` and `StopMode_SIB { SMNone, SMLand, SMGetIn, SMGetOut }` (`CLIENT\unknown_18705.c:33` to `:51`), with many `get_botmap_*` and `set_botmap_*` accessors (`:232` to `:270`).
- Contact damage: impulses summed per zone into `ProcessDirectDamage(DT_CUSTOM, ...)` with zone coefficients and crew injury (`unknown_16458.c:244` to `:333`, `unknown_18705.c:313` to `:402`).

Not readable: the integrator `hkdxkhzidmpsib(dt,this)`, called from `EOnSimulate` (`unknown_16458.c:216`; client twin `zcggxjtfzrsib`, `unknown_18705.c:285`), has no definition in any readable file. All 23,514 non-junk blocks of both PBOs (9,546 server, 13,968 client) were decompressed and searched; the name appears only as the call. The lift curve, the collective to force mapping and the altitude band all live there.

## Config store

The coefficients are not in `config.cpp`. A JSON file per class, `$profile:\Heli_sib\<classname>_config.json`, created from defaults when missing and loaded with `JsonFileLoaderVert<T>` (`CLIENT\unknown_6344.c:66` to `:97`), fills a global `ref map<string,float> ssaBWDQnlAkkAQpglobal = new map<string,float>;` (`CLIENT\unknown_1929.c:4`), referenced everywhere as `ssaBWDQnlAkkAQp`.

The default struct `class Json_Heli_MH6` (`unknown_6344.c:2` to `:53`) has readable names: `Lift_power=3.3`, `No_power=1200`, `Full_power=1250`, `side_strength=1.3`, `power_before=1.0`, `friction=0.3`, `Mass=1400.81`, `incline` and `front_tilt` 0.9, `m_povorot=0.4`, damage zone switches, `maxFuel=70`, `gasoline_costs=0.0004`, sound volumes, `coef_damage_weapon`, `auto_off_autopilot`, `auto_engine_shutdown`.

The load is positional: `vert_conf_MH6` inserts values under `child_name + "_" + index` (`:105` to `:154`), and the class reads them back in the same order in `go_conf()` (`unknown_16894.c:475` to `:515`) and in the advanced loader `pxmcpzlfyvhxsib()` (`unknown_16458.c:337` to `:393`):

| JSON field | Field in the class |
|---|---|
| `duration` | `c_startDurationInv` |
| `Lift_power` | `c_liftForceCoef` |
| `No_power` | `c_altNoForce` |
| `Full_power` | `c_altFullForce` |
| `side_strength` | `c_cyclicAsideForceCoef` |
| `power_before` | `c_cyclicForwardForceCoef` |
| `friction` | `c_bodyFrictionCoef` |
| `Mass` | `c_heliMass` |
| `incline`, `front_tilt`, `inclineMouse`, `front_tiltMouse`, `m_povorot` | `m_naklon`, `m_nabor`, `m_naklonMouse`, `m_naborMouse`, `m_povorot` |
| `Chassis`, `Body`, `Engine`, `Fuel`, `Rotor1`, `Rotor2` | `b_Chassis`, `b_Body`, `b_Engine`, `b_Fuel`, `b_Rotor1`, `b_Rotor2`, zone switches |

`vert_conf` dispatches on `child_name.Contains("HeliMH6_SIB")` (`unknown_6344.c:57` to `:64`), which suggests each model brings its own `Json_Heli_*` and `vert_conf_*` (inferred).

## Inputs and actions

- Flight inputs are custom `UASIBHeli*` actions declared in `inputs = "HelicopterModScripts/modded_Inputs.xml"` (`unknown_15761.c:21`) and looked up with `GetUApi().GetInputByName("UASIBHeliEngine_new")`, `"UASIBHeliAutopilot"` and `"UASIBHeliHide"` (`CLIENT\unknown_18863.c:121`, `:188`, `:255`). The XML is binary in the PBO and was not read.
- In-vehicle inputs `DefaultActionInputHelicopterEngine` (to `UASIBHeliEngine_new`) and `DefaultActionInputHelicopterHide` (to `UASIBHeliHide`), both `ContinuousDefaultActionInput` with `m_DetectFromTarget=false` (`SERVER\unknown_294.c`, `unknown_286.c`).
- Engine actions `ActionHeliStartEngineSIB` and `ActionHeliStopEngineSIB` (`unknown_16894.c:609`, `:645`), and mouse and keyboard variants `Action_Helicopter_Start_Engine_*` and `Stop_Engine_*` (`unknown_10783.c:39` to `:228`). Start sets `hide_start=1.0` and calls `heli.OnEngineStart()`; stop sets `hide_start=0` and `hide_rotor` to 0, zeroes the wanted rotor speed, stops the blur and calls `heli.OnEngineStop()`.
- Cockpit buttons are memory points the player must be near: `GetMemoryPointPos("avtopilot")` or `("button_beam")`, then `ModelToWorld` and a distance check (`CLIENT\unknown_2491.c`, `unknown_2306.c`).

## Rotors and engine start

Rotors are driven by `SetAnimationPhase` on paired sources, not by RPM. Sources (`unknown_15761.c:455` to `:514`): `hide_rotor`, `hide_start`, `rot_h_start` and `rot_h_blur_end` (rotor 1), `rot2_h_start` and `rot2_h_blur_end` (rotor 2), `toplivo` (fuel), and dial sources (`HorizonBankdetect`, `visotadetect`, `rpmdetect`, `speed`).

The static mesh and the blurred mesh are swapped by `animatezzstart` (spinning: start 1, blur 0) and `animatezzstop` (stopped: start 0, blur 1), only while `GetHealth01("Rotor1"/"Rotor2") > 0.15` (`unknown_16894.c:526` to `:595`); dead rotors freeze through `animatezzerror1/2`. Engine start (`SERVER\unknown_12270.c:7` to `:25`, RPC `HelicopterStartSimulate`): with `hide_start==1.0`, call `SetAnimationPhase("hide_rotor",1)`, `animatezzstart(heli)`, `rot_start(heli)` and `mainRotor(heli)`; `rot_start` (`unknown_5972.c:258`) sets the wanted rotor speed. The rotors are baked geometry with a blur variant, not attachable items. `toplivo` doubles as the fuel gauge; `ConsumeFuel()` lowers it every 5 s by `z_zatrat + (fuel-damage/4)` (`unknown_16894.c:454` to `:472`).

## Damage

- Zones (`unknown_15761.c:580` to `:684`): `Body` (6,000 hitpoints), `Chassis` and `Engine` (3,000), `Rotor1` and `Rotor2` (2,000), `Fuel` and `Proj` (700), each with `memoryPoints[]={"dmgzone_*"}` and `transferToGlobalCoef` near 0 (only `Body` passes 0.001). Global `hitpoints=1000`.
- When all six JSON zone switches are 0, the helicopter calls `SetAllowDamage(false)` (`unknown_16894.c:500` to `:503`).
- Contact (`OnContact`, `:400` to `:421`): damage is impulse times `m_dmgContactCoef`; a hard hit (speed over 10, angular speed over 5 or impulse over 1,000) removes the zone's whole health.
- Weapons (`SERVER\unknown_3380.c`): `EEOnDamageCalculated` returns `false` when `coef_damage_weapon` is 0; `EEHitBy` scales damage by it. Blades (`SIB_blade`) and doors (`Sib_heliDoor`) use their parent's coefficient.
- A destroyed helicopter hitting a player applies `dBodyApplyImpulse` through an override of `DayZPlayerImplement.RegisterTransportHit` (`unknown_10783.c:118` to `:146`).

Both models are `modded class HeliTest_SIB` in the server and the client PBO; physics run on the server, with `EOnSimulate` gated on `GetGame().IsServer()` (`unknown_16894.c:428`) and, for the advanced model, also on the licence (`unknown_16458.c:214`).

## Not read

- `config.bin`: the config used is the script config in `unknown_15761.c`. Check exact numbers against the live mod.
- `model.cfg` (bones and the real animation classes): only the `AnimationSources` names are known.
- The `.p3d` memory points, inferred from script: `dmgzone_body`, `chassis`, `engine`, `fuel`, `rotor1`, `rotor2`, `proj`, `avtopilot`, `button_beam`, crew `pos_*` and `crew*` proxies.
- The advanced integrator and the input bindings.

What SIB confirms: the `CarScript` chain, `AnimationSources`, `DamageZones` and `Crew` config, custom `UA*` inputs, engine start and stop actions and the rotor blur swap, all shared with the other helicopter mods. Its only readable force code, `qmdkldkpqpmlsib` (`unknown_10783.c:454`), applies forces but holds no lift model.
