# Rules that break a motorbike

Which ten config, model and script rules break a motorbike when ignored, the tuning lessons measured on a real import, and what vanilla left unfinished in 1.30. Read `motorbikes.md` first for the class tree. In this file `config.cpp` alone means `P:\DZ\vehicles\singletrack\config.cpp`, and `motorbikescript.c` means `P:\scripts\4_world\entities\vehicles\motorbikescript.c`.

## Config and model rules

| Rule | Symptom when broken | Source |
|---|---|---|
| `class Wheels` holds `Front` and `Rear` directly; there is no `Axles` block | The simulation does not start when the bike spawns. The exact failure (an RPT error, an inert entity or a crash) is not measured. | `config.cpp:73` to `:91` (base), `:340` to `:377` (`Motorbike_01_ColorBase`) |
| Front brake on `input = 1`, rear on `input = 0` | The front lever does nothing, or the rear pedal locks the front wheel | `config.cpp:292`, `:301` |
| A `drivewheel` bone in the model | The headlight stays fixed to the frame instead of turning with the bars | `motorbikescript.c:1107` to `:1109` |
| `SeatDriver` at phase `0.0`, or no `SeatDriver` check | No prompt to get on | `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:92` to `:98` |
| `speedGeomActivation` and `speedGeoms[] = {"geotohide"}` | The bike catches on small bumps or is thrown at speed | `config.cpp:258` to `:262`, `:1448` to `:1452` |

### Wheels

`simulation = "motorbike"` reads `class Wheels { class Front; class Rear; }`; `class Axles` belongs to the car simulation. Remove any `Axles` block from `SimulationModule`:

```cpp
class Wheels: Wheels
{
    class Front: Front { inventorySlot = "MyMod_Bike_Wheel_1"; animDamper = "damperfront"; };
    class Rear: Rear   { inventorySlot = "MyMod_Bike_Wheel_2"; animDamper = "damperback"; };
};
```

### Brakes

`SetBrake` is the rear brake and `SetHandbrake` the front brake (`P:\scripts\3_game\vehicles\motorbike.c:129` to `:139`), so the front brake sits on the handbrake channel:

```cpp
class Brakes
{
    class Front { input = 1; pressureBySpeed[] = {0,0.85,10,0.7,40,0.6,60,0.5,80,0.5}; };
    class Rear  { input = 0; pressureBySpeed[] = {0,0.95,10,0.1,20,0.1,40,0.1,50,0.1}; };
};
```

The rear curve drops from `0.95` at a standstill to `0.1` from `10` on (`config.cpp:302`); that this is meant to stop rear wheel skids is a guess.

### Headlight bone

The script attaches the front light to the bone found by name, `GetBoneIndex("drivewheel")`. Name the fork and handlebar selection `drivewheel` in the model and list it in `skeletonBones[]` of `model.cfg`.

### Seat

`Motorbike_01_ColorBase` lets the rider on only when `GetAnimationPhase("SeatDriver") == 0.0`, so a model without that animation never gets the prompt. For a bike without a flip-up seat, inherit `MotorbikeScript` directly or override `CanGetIn()` without the check. To keep the seat, declare the source:

```cpp
class AnimationSources: AnimationSources
{
    class SeatDriver { source = "user"; initPhase = 0.0; animPeriod = 1.0; };
};
```

### Lean and tip-over

`class Steering` sets `tipoverAngle = 50.0` and the lean curves (`config.cpp:266` to `:278`). The native simulation reads them, so their exact effect, and whether a wrong table makes the bike fall when accelerating or refuse to lean, is not visible on `P:\`. Start from the `Motorbike_01` values: `maxLeanAngle[] = {1,0,5,8,15,10,30,17,40,22,80,30}`, `maxSteeringAngle[] = {1,40,5,40,15,20,30,5,40,3,80,1}`, `directControl[] = {0.0,1.0,5.0,1.0,30.0,0.6,60.0,0.2,80.0,0.0}`.

### Geometry hidden at speed

The kickstand collision hits uneven ground unless it is switched off while moving. `speedGeomActivation` is `0.29` on `Motorbike_01` and `0.27` on `Motorbike_02`. Put the kickstand collision in its own Geometry LOD component named `geotohide`.

## Script rules

### Kickstand

The constructor deploys it with `SetKickstand(1)` (`motorbikescript.c:141`); keep that line, or the bike may fall on its side when it spawns (not measured). No release script retracts it: the only `SetKickstand(0.0)` sits in `OnInput` under `#ifdef DIAG_DEVELOPER` with a debug mode set (`motorbikescript.c:841` to `:843`, `:915`). If it retracts while riding, the native simulation does it.

### Lights, horn and particles

In 1.30 each has its own component, created in the `MotorbikeScript` constructor: `m_LightsComponent` (`motorbikescript.c:113`), `m_HornComponent` (`:127`) and `m_VFXComponent` through `InitializeParticles()` (`:139`). A class on `MotorbikeScript` gets them from the base constructor; register the bike's own light profiles and sound sets on them. The base constructor lines:

```c
m_LightsComponent = VehicleLightsComponent(this);
m_HornComponent = VehicleHornComponent(this);
InitializeParticles(); // creates m_VFXComponent
```

Without them, the light code reaches a component that does not exist, or the horn has no sound and no noise for infected (not measured).

### Light input

Vehicle lights switch with `UAToggleVehicleLights` through `ToggleVehicleLightsActionInput` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:849` to `:855`); `UAToggleHeadlight` is the head torch (`actioninput.c:776` to `:782`). Both names are in `P:\bin\constants.xml:90` and `:91`. An `inputs.xml` that binds only `UAToggleHeadlight` does not switch the bike's headlight. Details in `motorbike-actions-hud-lights-sounds.md`.

### Repair only with the blowtorch

The motorbike repair actions are added only to the blowtorch: `ActionRepairMotorbikeEngineWithBlowtorch`, `ActionRepairMotorbikeChassisWithBlowtorch` and `ActionRepairMotorbikePartWithBlowTorch` (`P:\scripts\4_world\entities\itembase\blowtorch.c:109`, `:111`, `:113`). `ActionRepairMotorbikeEngine` is also missing from the action list that registers the others (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:252` to `:260`). To repair with hand tools, add the actions to the items in a `modded class` and register the missing one:

```c
modded class ActionConstructor
{
    override void RegisterActions(TTypenameArray actions)
    {
        super.RegisterActions(actions);
        actions.Insert(ActionRepairMotorbikeEngine);
    }
}
```

## Contact damage and instant death

A rider who dies when the bike grazes a small obstacle at low speed has contact coefficients that are too high. Each contact gives two values on the server (`CheckContactCache`, `motorbikescript.c:1252` to `:1357`, called inside `if (g_Game.IsServer())` at `:743` to `:758`):

- Vehicle damage `dmg = Math.AbsInt(data[0].m_Impulse * m_VehicleContactDamageCoef)` (`:1263`).
- Crew damage base `crewDmgBase = Math.AbsInt((data[0].m_Impulse / dBodyGetMass(this)) * 500 * m_CrewContactDamageCoef)` (`:1264`). The vanilla comment says it "calculates damage as if the object's weight was 500kg instead of its actual weight".

`dmg` picks the tier, with the constants at `P:\scripts\3_game\constants.c:898` to `:901`:

| `dmg` | Result | Lines |
|---|---|---|
| Below 10 (`MOTORBIKES_CONTACT_DMG_MIN`) | Ignored | `:1301`, `:1302` |
| 10 to below 25 (`MOTORBIKES_CONTACT_DMG_THRESHOLD_SMALL`) | Zone damage without transfer, light crash sound | `:1310` to `:1320` |
| 25 to below 40 (`MOTORBIKES_CONTACT_DMG_THRESHOLD_MID`) | `FallOver()`, light sound, no crew damage | `:1321` to `:1331` |
| 40 and above | `DamageCrew(crewDmgBase)`, `FallOver()`, heavy sound | `:1332` to `:1344` |

From 10 up, `ProcessDirectDamage` applies `dmg` to the zone hit (`:1350`). Inside `DamageCrew` (`:1360` to `:1412`), a `crewDmgBase` above 80 (`MOTORBIKES_CONTACT_DMG_KILLCREW`, strictly greater) runs `crew.SetHealth(0.0)` (`:1369`, `:1383`); otherwise the rider takes 50 to 150 shock and 2 to 100 health, scaled between 25 and 80 (`:1387` to `:1409`).

So `m_VehicleContactDamageCoef` decides when the bike falls (25) and when the rider is hurt (40), and `m_CrewContactDamageCoef` decides whether that kills (above 80). Vanilla values are `0.03` and `0.018` on `Motorbike_01` (`motorbike_01.c:5` and `:6`) and `0.035` and `0.012` on `Motorbike_02` (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_02.c:5` and `:6`).

## Tuning lessons from an imported bike

Measured in game on a 157 kg racing motorbike mod that inherits `Motorbike_02_ColorBase`, on a dedicated server and client. Mod behaviour on one bike, not vanilla.

1. First gear overall must be short. With the automatic clutch, first gear times `driveRatio` between 20 and 26 pulls away (`Motorbike_02` is 25.7; the test bike settled on 20). A real racing bike's 6.77 barely moves it, 0.05 to 0.1 km/h at full throttle with the rpm stuck. Compare in one session against the vanilla drivetrain, and measure the ratio the engine applies (rpm times pi over 30, divided by the drive wheel's angular speed) to confirm the config loaded. On 1.30 bikes wheel 0 is the front; tell the wheels apart by rolling radius (angular speed times radius equals speed), not by `WheelGetPositionLS`.
2. Size the suspension to the load on each wheel. The model that fits the measurements, a guess from them, is F = k (u + travelMaxDown), with u linear in the damper phase (phase 0 is -travelMaxDown, phase 1 is +travelMaxUp). With the bike resting only on its springs, the sum of spring forces over g gave 157.1 kg for a 157.0 kg bike; in another setup the springs carried only 132.7 kg and the engine collision box rested on the ground. To rest on the axle, set travelMaxDown to F / k per wheel, or raise k and scale damping with the square root of k times m. A bike that inherits a lighter bike's suspension inherits its sag; when the sum does not match the mass, look for what else touches the ground.
3. No Geometry box may touch the ground at full compression. Every touch is a contact: `dmg` picks the tier (`motorbikescript.c:1263`), and from 25 up the branches call `FallOver()` (`:1310` to `:1342`), which throws the rider off. Before testing, check that the lowest point of each component, minus the compression left from rest, clears the ground by at least 5 mm, and scale `m_VehicleContactDamageCoef` by vanilla mass over your mass so the same hit counts the same. When a `..._damper_land` box is lowered to seat the physical wheel, shrink it around the same centre, because the physical wheel does not move. Log contacts on the server (`Transport.OnContact`: zone, point, impulse change) before tuning the coefficients.
4. The rider proxy only places the rider and turns them about the vertical. The engine applies the crew proxy frame but keeps the player upright: a proxy tilted 20 degrees forward gave about 17 degrees of yaw and no lean, and a rolled proxy left the player standing 30 cm off the bike. A crouched or leaning rider needs animation (`motorbike-rider-animation.md`).
5. A hidden selection changes material only when `model.cfg` lists it in `sections[]`. Config alone is not enough and the failure is silent, so check the binarized model, where the selection must be a section. The base paints lights by index: headlight 0, brake 1, tail 2, dashboard 3 (`motorbikescript.c:114` to `:122`), and both vanilla bikes then register their brake on index 2, the tail light's index (`motorbike_01.c:19` and `:20`; `motorbike_02.c:20` and `:21`). On a custom model those positions may land on livery selections. A later 1.30 stable build registers each bike's own front and brake indices (`Motorbike_01` front 3 and brake 2, `Motorbike_02` front 4 and brake 6); not yet checked on `P:\`.

## Unfinished in 1.30

Work in progress visible in the vanilla scripts and config on `P:\`. Where a later 1.30 stable build differs, the item says so; those differences are not checked on `P:\`.

- A fallen bike ejects its rider by giving the player `eModifiers.MDF_UNCONSCIOUSNESS` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2452` to `:2458`). The vanilla comment calls it temporary code until a ragdoll command exists.
- `ActionRepairMotorbikeEngine` exists (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikeengine.c:1`) but is not registered and no tool adds it; only the blowtorch version works.
- The base registers light selections whose material is read with `ConfigGetString` (`P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c:77`) from keys such as `frontReflectorMatOn` (`motorbikescript.c:114` to `:122`). `config.cpp` declares none of those keys, while cars do, for example `frontReflectorMatOn` at `P:\DZ\vehicles\wheeled\config.cpp:1338`. The light entries of `hiddenSelections[]` are `lights_brake`, `lights_front` and `lights_rear` on `Motorbike_01_ColorBase` (`config.cpp:232` to `:239`) and `light_1_1`, `light_1_2` and `light_brake_1_2` on `Motorbike_02_ColorBase` (`config.cpp:1416` to `:1425`). A later 1.30 stable build declares the front and brake materials on both bikes, still none for tail or dashboard, and renames the `Motorbike_02_ColorBase` entries `lights_front`, `lights_rear` and `lights_brake`.
- The vehicle sound addon `P:\DZ\sounds\vehicles\config.cpp` holds only `CfgPatches` (`:1` to `:10`). The motorbike sound sets and shaders are in `P:\DZ\sounds\hpp\config.cpp`: the `Motorbike_0*` sound sets at lines 383946 to 385036, the shaders at 316513 to 318260.
- Many vehicle guides written for 1.29 use `CreateFrontLight`, `CarPartsHealthCheck` or `data[0].impulse`; 1.30 replaced or wrapped them (`dayz-1-30-vehicles.md`).
