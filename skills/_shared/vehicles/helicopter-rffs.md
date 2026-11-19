# RFFS helicopter

How the RFFS helicopter framework (`RFFSHeli_Core` 1.0) flies a `CarScript` child with `SetVelocity` and `SetOrientation`: the class layout, the `FlightSimulation()` integrator, the typed JSON config, rotors, memory points, crew, damage zones, actions, aviation parts, HUD and sync. Open it when building or debugging a kinematic helicopter.

Everything here was read in the RFFS mod's own de-rapified `config.cpp` files and scripts (`Core_config.cpp`, `S76_config.cpp`, `Core_scripts\{3_Game,4_World,5_Mission}\...`, `S76_scripts\4_world\RFFSHeli_S76.c`), which are not in this repo and not vanilla. Citations are `file:line` into those files, with `Core.c` short for `Core_scripts\4_World\RFFSHeli_Core.c`. The mod is not obfuscated. Learn the pattern and write your own code; which model to build from is in `helicopters.md`.

RFFS is the kinematic reference. Nothing is locked or missing, unlike SIB (`helicopter-sib.md`), and the model is far more grounded than SIB's: lift rotated with attitude, ground effect, translational lift, speed and climb governors, drag and weathervaning. It still sets velocity directly with `SetVelocity` (`P:\scripts\1_core\proto\enphysics.c:111`) instead of applying forces.

## Class layout

| Layer | Adds | Source |
|---|---|---|
| `CarScript` (vanilla) | Wheels, seats, fuel, damage, sound | |
| `RFFSHeli_base : CarScript` | The whole flight model, all tuning values, sync variables, the ground fallback (four `NivaWheel` wheels, axles, steering, gearbox), aviation slots, rotor and gauge `AnimationSources` | `Core.c:2`; `Core_config.cpp:517` to `:873` |
| `RFFSHeli_S76 : RFFSHeli_base` | Per-model values (fuel, airspeed, altitude), doors, seats and crew, the model's gauge needle logic, wreck class | `RFFSHeli_S76.c:1`; `S76_config.cpp:116` to `:734` |

The base is declared `class RFFSHeli_base: CarScript` (`Core.c:2`). It declares a full ground `SimulationModule` (`drive="DRIVE_AWD"`, torque curve, gearbox, four axles and wheels, `Core_config.cpp:525` to `:664`) used only for taxiing, and sets `vehicleClass = "Expansion_Helicopter"` (`:523`). Vanilla `CarScript` registers only `POSTSIMULATE` and `POSTFRAME` (`P:\scripts\4_world\entities\vehicles\carscript.c:207`, `:208`), so the helicopter adds `SetEventMask(EntityEvent.SIMULATE)` and `SetEventMask(EntityEvent.FRAME)` (`Core.c:180`, `:181`) and flies itself from `EOnSimulate` (`Core.c:1027`).

## Controls

`FlightSimulation()` (`Core.c:1767` to `:2129`) runs from `EOnSimulate` on the server only, with the engine running and `m_heli_state == 2` (`:1149` to `:1156`). The client re-enters `EOnSimulate` from `EOnFrame` every 5 ms or more (`:1008` to `:1016`), but that only runs `ExecuteAnimations()` and `KeyboardInputClient()` (`:1143` to `:1145`); it does not smooth the pose, which comes from native `CarScript` replication.

The server reads inputs in `KeyboardInput()` (`:510` to `:544`) from `CrewMember(0)` or `CrewMember(1)` with `GetInputInterface().SyncedValue("UARFFS...")`. The client reads the same values in `KeyboardInputClient()` (`:475` to `:507`) only to keep them synced. The inputs are declared in `inputs="RFFSHeli_Core/modded_Inputs.xml"` (`Core_config.cpp:30`):

| Input | Writes | Meaning | Source |
|---|---|---|---|
| `UARFFSCyclicForward`, `Back` | `r_cyclic_ForwardBack` by `v * c_tilt_rate` | Cyclic pitch | `Core.c:549`, `:550` |
| `UARFFSCyclicLeft`, `Right` | `r_cyclic_LeftRight ∓= v * c_lateral_tilt_rate` | Cyclic roll | `:551`, `:552` |
| `UARFFSPedalLeft`, `Right` | `r_pedal_LeftRight ∓= v * c_rotation_rate` | Tail rotor yaw | `:553`, `:554` |
| `UARFFSCollectiveUp`, `Down` | `m_collective_level = Clamp(±1, 0, 20)` | Collective in 20 steps | `:563` to `:583` |
| `UARFFSToggleHUD` | `m_show_hud_*`, 3-tick debounce | HUD on and off | `:661` to `:668` |
| `UARFFSToggleCommand` | `m_pilot_in_command` | Hand control between pilot and co-pilot | `:683` to `:690` |
| `UARFFSRecover` | `m_flight_recovery_*` | Recovery mode | `:637` to `:657` |

The collective is a lever of 20 steps of 5 percent each (`:105`), stepped with a 5-frame repeat gate (`:565` to `:583`); thrust is `r_collective_power = (m_collective_level / 20) * c_thrust_rate` (`:543`). Two arcade options, `c_simple_collective` (server-wide) and `c_heli_simple_collective` (per model), replace the steps with `r_collective_power = ±(0.85 * c_thrust_rate)` while a key is held (`:585` to `:592`).

## The integrator

The normal branch (`Core.c:1895` to `:2126`), in order:

1. Ceiling: when `GetPosition()[1] > c_max_altitude_m`, clamp Y with `SetPosition` (`:1774` to `:1780`). Default 1,219.2 m (`:38`); the S76 uses 1,250 m (`RFFSHeli_S76.c:45`).
2. Damage: a damaged or ruined `TailRotor` adds growing uncommanded pedal (`:1783` to `:1801`); a damaged `Engine` or `MainRotor` multiplies collective power by 0.85 (`:1804` to `:1817`).
3. Angular momentum: cyclic and pedal feed `m_angular_moment`, which decays each tick by `c_tilt_drag_rate * m_cyclic_modifier`, is clamped to `c_angular_moment_limit` and snaps to 0 near zero (`:1898` to `:1931`). Orientation is composed with `YawPitchRollMatrix` and `Math3D.MatrixMultiply3` (`:1954` to `:1961`), a real 3D compose. Cyclic recentres through `c_cyclic_retard` when released (`:1947` to `:1952`).
4. Lift vector: the scalar collective is rotated into world space by pitch, roll and yaw (`:1993` to `:1996`), so tilting the disc turns lift into travel:

   ```c
   vector_x = r_collective_power * (-sin(roll) * cos(yaw) - cos(roll) * sin(pitch) * sin(yaw));
   vector_y = r_collective_power * ( sin(roll) * sin(yaw) - cos(roll) * sin(pitch) * cos(yaw));
   vector_z = r_collective_power * ( cos(roll) * cos(pitch));
   ```

5. Ground effect: near the ground while descending, `vector_z` gets a term scaled by `c_rotor_diameter_m` (`:1998` to `:2000`).
6. Translational lift: about `(translational_speed * 0.00007)² * c_thrust_rate` is added to `vector_z` (`:2002` to `:2004`).
7. Speed governor: near `c_max_airspeed_kph`, a term `speed⁴ / ((max + 40) * 0.277778)⁴` is taken off the horizontal thrust, only when thrust would add speed (`:2006` to `:2027`).
8. Climb governor: near `c_max_climb_rate`, `vector_z` is scaled down by a fifth-power term (`:2029`, `:2030`).
9. Thrust is added to the velocity (`:2032` to `:2035`), and `c_aero_drag_rate` is split across X and Z and subtracted (`:2037` to `:2048`).
10. Weathervaning: the nose turns toward the velocity by `(angle_diff / 360) * log2(speed * 0.1) * c_bank_turn_coeff` (`:2069` to `:2087`), so banked turns change heading. Wind terms are commented out (`:2050` to `:2067`).
11. Trainer mode: optional clamp of pitch and roll to 35 degrees and descent to -7.5 m/s (`:2089` to `:2106`).
12. `AdditionalThrustVectors(velocity, orient, out, out)` (`:2132` to `:2136`) is an empty hook a model can override to add thrust, for a tilt-rotor say.
13. Apply: `SetOrientation(heli_orient)`, then `SetVelocityAdjusted(heli_velocity)` (`:2116` to `:2119`); reset the four input sums (`:2122` to `:2125`); `ConsumeFuel()` (`:2128`).

`SetVelocityAdjusted` and `GetVelocityAdjusted` (`:2465` to `:2487`) wrap `SetVelocity` and `GetVelocity(this)` with a horizontal scale per model (`c_speed_adjustement_factor`, `c_speed_factor`), a speed fudge from DayZ 1.21 and 1.28 (`:82` to `:84`; the S76 sets `SpeedFactor=195`, `RFFSHeli_S76.c:49`). `dBodyApplyImpulse` appears only commented out (`Core.c:272`).

Recovery mode: with `UARFFSRecover` held and `c_allow_recovery` set, the branch at `:1819` to `:1894` zeroes the inputs, sets `m_collective_level = 10` (50 percent), counters gravity (`heli_velocity[1] += 0.245`), bleeds speed and eases the attitude level relative to the velocity. It is not a PID, and there is no auto hover.

## Config

Two JSON files under `$profile:\RFFSHeli\`, loaded with `JsonFileLoader<T>`, created from defaults and migrated by version:

- `MasterConfig.json`, class `RFFSHeli_MasterConfig` (`RFFSHeli_MasterConfig.c:193` to `:268`, `ConfigVersion=12`): server policy. HUD units, first and third person, helmet; `AllowTakeCommand`, `SimpleCollective`, `AllowRecoveryMode`, `Grounded`; sound volume; damage toggles and collision coefficient; storage; and a crash site model (create on ruin, scatter and damage cargo, spawn infected from a class list, counts, distances, loot damage). Read once in `EEInit()` on the server (`Core.c:287` to `:352`).
- `<classname>_Config.json`, class `RFFSHeli_HeliConfig` (`RFFSHeli_HeliConfig.c:136` to `:188`, `ConfigVersion=7`): per-model tuning. Fuel capacity and rate, trainer mode, hydraulics, simple collective, maximum airspeed, altitude and climb, drag, bank turn, speed factor, and the anti-torque, cyclic, collective and cyclic damping rates. The model seeds the defaults in its `EEInit()` and calls `ApplyHeliConfig()` (`RFFSHeli_S76.c:38` to `:62`).

`RFFSHeli_HeliConfigData` has named fields with `get*` accessors (`RFFSHeli_HeliConfig.c:3` to `:133`), read by name in `ApplyHeliConfig()` (`Core.c:232` to `:265`), for example `c_thrust_rate = getControlsCollectiveThrustRate() * 0.01 * 0.47`. That is safer than SIB's positional map. Values are percentages (100.0 is baseline) that scale a fixed constant, so server owners tune by percent without knowing the coefficient.

About 12 config booleans are packed into one `RegisterNetSyncVariableInt("c_encoded_config_bool")` (`Core.c:334` to `:345`) and unpacked on the client in `EOnSimulate` (`:1030` to `:1081`), one sync variable instead of twelve. SIB does the same.

## Animation, state, memory points, crew and damage

`AnimationSources` (`Core_config.cpp:665` to `:838`, extended for the S76 at `S76_config.cpp:318` to `:545`) are all `source="user"`, driven by `SetAnimationPhase`:

- Rotors, main and tail, four sources each: `rotorN_speed`, `rotorN_blur_hide` (static to blur swap), `rotorN_blades_hide`, `rotorN_bent_hide` (damage states). Rotors are baked geometry with a blur variant, gated by health.
- Engine state: `engine_rpm`, `engine_running`, `engine_running_fast`, `rotor_spinning`.
- Gauges: `airspeed_kts`, `altitude_ft`, `agl_ft` with needle bands (`_sm_hide`, `_lg_hide`, or per model `_low`, `_med`, `_high_hide`), `compass`, `pitch_orientation`, `roll_orientation`, `vs_ft`. Driven from `UpdateCockpitGauges()` (`Core.c:428` to `:441`); the S76 adds four airspeed bands, three AGL bands and three vertical speed needles (`RFFSHeli_S76.c:85` to `:158`).
- Wheels and doors: vanilla `damper_*` and `AnimHitWheel_*`, plus `DoorsDriver`, `DoorsCoDriver`, `DoorsCargo1`, `DoorsCargo2` (`S76_config.cpp:347` to `:370`).

`m_heli_state` is 0 off, 1 starting, 2 running, 3 shutting down, with 11 and 13 between (`Core.c:100`). `ExecuteAnimations()` dispatches by state (`:1323` to `:1368`); `StartUpAnimation()` ramps `rotor1_speed` and fades to blur at 80 percent of `c_startup_sound_length` (`:1481` to `:1502`). `EvaluateDamageStates()` (`:1371` to `:1468`) forces shutdown for a missing or ruined wiring harness, a ruined engine or main rotor, empty fuel, or, with `c_has_hydraulics`, low hydraulic fluid; low hydraulics also weaken cyclic through `m_cyclic_modifier` (`:1407` to `:1414`).

Memory points from config and script: `dmgZone_chassis`, `avionics`, `engine`, `hydraulics`, `fuelTank`, `rotor1`, `rotor2`, `lights_1_1` (`S76_config.cpp:561` to `:665`); `ptcExhaust_start` for engine smoke (`Core.c:1332`, `:1343`); `crewDriver`, `crewCoDriver`, `crewCargo1` to `4` with `pos_*` and `pos_*_dir` (`S76_config.cpp:125` to `:171`). The `.p3d` was not read, so these are names, not checked model data.

Crew (`S76_config.cpp:125` to `:171`): driver, co-driver and four cargo seats, each with `actionSel`, `proxyPos`, `getInPos`, `getInDir`. Both front seats have `isDriver=0`; script decides who flies through `m_pilot_in_command`, which is how pilot and co-pilot both get control with a hand-off.

Damage zones (`S76_config.cpp:546` to `:677`): `Chassis`, `Avionics`, `Engine`, `Hydraulics`, `FuelTank`, `MainRotor`, `TailRotor`, `Reflector_1_1` (landing light), each with hitpoints, transfers (engine to hydraulics 0.5; tail rotor to chassis 0.75 and engine 0.2) and `inventorySlots` tying part health to attachment health. Global `hitpoints=8000`. Collisions go through `m_ContactCache` and `ChassisImpactDamage()`: a skid landing harder than 1,500 ft/min calls `DecreaseHealth("Chassis")` (`Core.c:752` to `:768`).

## Actions, parts and HUD

- `ActionStartHelicopter` (`ActionStartHelicopter.c:9` to `:205`): in vehicle, pilot or co-pilot in command only, blocked when `c_grounded` or the engine is ruined. It checks battery (energy over 5), igniter, hydraulic hoses if fitted, wiring and fuel, sets `m_heli_state = 1` and calls `OnBeforeEngineStart`. `ActionStopHelicopter` (`ActionStopHelicopter.c:1` to `:101`) needs airspeed under 8 km/h and sets `m_heli_state=3`. Vanilla `ActionStartEngine` and `ActionStopEngine` are modded to return `false` on `RFFSHeli_base` (`ActionStartHelicopter.c:209` to `:232`, `ActionStopHelicopter.c:104` to `:127`), and `SetActions()` removes the horn and engine start (`Core.c:2456` to `:2463`).
- Repair actions `ActionRepairHelicopterMainRotor`, `TailRotor`, `Engine`, `Chassis`, `Hydraulics`, `Avionics`, `FuelTank` and `ActionReplaceHelicopterAvionics` each raise one zone one health level with a repair item, chosen through a per-player `RepairHelicopterActionData`.
- Aviation parts replace the car parts: `AviationBattery`, `AviationIgniterPlug`, `AviationHydraulicHoses`, `AviationWiringHarness`, with their own `CfgSlots` and items (`Core_config.cpp:159` to `:505`, `:875` to `:908`). The helicopter overrides the vanilla checks such as `IsVitalCarBattery` (`P:\scripts\4_world\entities\vehicles\carscript.c:2812`) to return `false`, although in 1.30 that method is marked obsolete and no vanilla script calls it; the start check reads `NeedElectricitySourceDevice()` (`P:\scripts\3_game\vehicles\transport.c:830`), so a port to 1.30 overrides that instead. The mod sets its own `IsVitalAviationBattery` to return `true` (`Core.c:2227` to `:2260`); `GetBattery()` returns the aviation battery (`:2268` to `:2271`). Fuel is `CarFluid.FUEL` and hydraulic fluid `CarFluid.OIL` (`:1135`, `:1136`).
- HUD: a `modded class IngameHud` (`headsUpDisplay.c:1`) creates `RFFSHeli_Core/GUI/RFFSHelicopterGUI.layout` under the vanilla `LeftHUDPanel` (`:66` to `:71`). Each frame it casts `GetCommand_Vehicle().GetTransport()` to `RFFSHeli_base` and shows the panel only for the pilot in command with the HUD on and, optionally, a pilot helmet (`:150` to `:165`). It reads the synced fields (`m_airspeed_kph`, `m_altitude_m`, `m_fuel_level`, `m_hydraulic_level`, `m_collective_level`) and `GetHealthLevel(...)` for warning lights (`:202` to `:490`). A badly damaged or ruined `Avionics` zone distorts or blanks the HUD (`:167` to `:187`). Metric and imperial units are honoured.

## Sync

The server owns the flight (`Core.c:1151`). The constructor registers sync variables (`:189` to `:208`): altitude, height above ground and airspeed, `m_heli_state`, `m_collective_level`, `m_rotor_spin`, fuel and hydraulic levels, alarm, engine damage and bullet hit sound flags, `m_pilot_in_command` and `c_encoded_config_bool`. Every change calls `SetSynchDirty()`. The client never owns the velocity.

## Not read

- `modded_Inputs.xml` ships in `RFFSHeli_Core.pbo` and holds only `<actions>`, `<sorting>` and `<preset>`, with no input `<context>`; the key bindings are not recorded. The input names are confirmed from script (`Core.c:491` to `:501`, `:549` to `:554`, `:563` to `:583`).
- The `.p3d` models, `model.cfg`, `RFFSHelicopterGUI.layout` and the sound assets.
- The files read are de-rapified `config.cpp`; check exact numbers against the live PBO before relying on them.
