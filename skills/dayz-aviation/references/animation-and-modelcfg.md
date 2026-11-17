# Control surfaces, model.cfg and damage zones

`AnimationSources` for control surfaces, dials and dampers, the `model.cfg` animation classes behind them (dial source scheme, `sourceAddress`, the propeller spin hack, surface angles), aircraft damage zones, and which vanilla seat animation set each aircraft reuses.

Third-party material: patterns read from the LM_Planes mod (Workshop `3730564764`, by Llama and Itspete-Here), whose files are not in this repo. Not yet checked on `P:\` except where a `P:\` path is cited. Use it to learn the pattern and write the mod's own code. The general `model.cfg` and `AnimationSources` rules are in `skills/_shared/animation/model-cfg-animations.md` and `skills/_shared/animation/animation-sources.md`.

## AnimationSources (in CfgVehicles.<Aircraft>)

```cpp
class AnimationSources {
    // Flight controls — all script-driven
    class elevator_1_1 { source = "user"; initPhase = 0.5; animPeriod = 0.5; };  // initPhase=0.5 = neutral
    class elevator_2_1: elevator_1_1 {};
    class aileron_1_1:  elevator_1_1 {};
    class aileron_2_1:  elevator_1_1 {};
    class rudder_1_1:   elevator_1_1 {};
    class gear_1_1 { source = "user"; initPhase = 0; animPeriod = 2.5; };  // 2.5s retract
    
    // Dashboard instruments — short animPeriod for responsive needles
    class dial_compass { source = "user"; initPhase = 0; animPeriod = 0.05; };
    class dial_horizon_pitch { source = "user"; initPhase = 0; animPeriod = 0.05; };
    class dial_horizon_bank  { source = "user"; initPhase = 0; animPeriod = 0.05; };
    class dial_volt          { source = "user"; initPhase = 0; animPeriod = 0.05; };
    class dial_altitude      { source = "user"; initPhase = 0; animPeriod = 0.05; };
    
    // Dampers (suspension) — translation animations
    class damper_1_1 { source = "user"; initPhase = 0.5; animPeriod = 1; };
};
```

Every flight-control source is `"user"` (script-driven). The script then calls `SetAnimationPhase("elevator_1_1", value)` from `UpdateControlSurfaceAnimations(dt)`.

## Model.cfg Animation classes (per-aircraft .cfg)

Animations live in `CfgModels.<Aircraft>.class Animations`:

```c
class dial_horizon_bank
{
    type = "rotation";
    source = "dial_horizon_bank";  // CUSTOM source string
    selection = "dial_horizon_bank";
    axis = "dial_horizon_bank_axis";
    sourceAddress = clamp;          // Critical for dials: don't loop past min/max
    minValue = -1;
    maxValue = 1;
    angle0 = 3.14;
    angle1 = -3.14;
    memory = true;
};

class wheel_1_1
{
    type = "rotation";
    source = "wheelfrontleft";      // VANILLA engine source
    selection = "wheel_1_1";
    axis = "wheel_1_1_axis";
    sourceAddress = loop;           // Wheels rotate continuously
    minValue = 0.0;
    maxValue = 6.2831855;           // 2π
    angle0 = 0.0;
    angle1 = -6.2831855;
    memory = 1;
};

class damper_1_1
{
    type = "translation";           // Suspension: linear motion
    offset0 = 0.0;
    offset1 = 0.35;
    // ...
};
```

### Dial source-string scheme

**Vanilla engine sources** (read directly from simulation):
- `source = "rpm"` (engine RPM, for `dial_rpm`)
- `source = "fuel"` (for `dial_fuel`)
- `source = "coolant"` (for `dial_temp`)
- `source = "speed"` (for `dial_speed`)

**Custom script-driven sources** (script writes via SetAnimationPhase):
- `source = "dial_altitude"` (matches the bone name when custom)
- `source = "dial_volt"`, `dial_compass`, `dial_horizon_bank`, `dial_horizon_pitch`

**Pattern**: when source is custom, source string equals bone name (`dial_altitude` → `dial_altitude`). When source is vanilla, source differs (`dial_rpm` → `rpm`).

### sourceAddress patterns

| sourceAddress | Use case |
|---|---|
| `clamp` | Dials — don't loop past min/max, needle stops at range edges |
| `loop` | Wheels, compass — continuous rotation |
| `mirror` | Ping-pong oscillation (Catalina + Patty_Wagon use heavily — wipers, dial wobble) |

### Propeller spin hack

```c
class rotor_1_1
{
    type = "rotation";
    source = "wheelfrontright";  // !!! Tied to right-front wheel RPM, not engine !!!
    ...
};
```

Because the aircraft uses `CarScript`, vanilla wheel-RPM sources are easier than custom. Visual prop spin is tied to right-front wheel rotation. **Scripts override this during flight** by manipulating wheel state OR by using `dBodySetAngularVelocity` directly. `rotor_1_1_blur` bone is for the blurred-prop visual effect, controlled by script (no animation in cfg).

### Multi-engine bone naming inconsistency

- DC-3 uses: `rotor_1_2`, `rotor_center2`
- Catalina uses: `rotor_2_1`, `rotor_center_2`

Pick one convention for new mods; don't mix.

### Flight surface realistic angles

- Elevator: ±0.40 rad (~23°)
- Aileron: ±0.40 rad (note: angle0/angle1 swap signs vs elevator)
- Rudder: ±0.27 rad (~15°)
- minValue/maxValue: -1 to 1 (script writes normalized)

### Damper translation

```c
class damper_1_1 {
    type = "translation";
    source = "damper_1_1";
    axis = "damper_1_1_axis";
    offset0 = 0.0;
    offset1 = 0.35;   // Up movement (suspension travel)
    memory = 1;
};
class damper_2_2 { ...; offset0 = -0.2; offset1 = -0.40; };  // Tail wheel: different range
```

Pair this with `damper_susp_X_Y` rotation animations for the spring-mount visual swing.

### isDiscrete flag

- `isDiscrete = 1` for vehicles (respects `sourceAddress` strictly)
- `isDiscrete = 0` for static props (Hangar) with simple continuous animation

## Aviation Damage Zones

```c
sections[] = {
    "camo1",
    "dmgzone_body", "dmgzone_back", "dmgzone_chassis", "dmgzone_front",
    "dmgzone_flaps_backleft", "dmgzone_flaps_backright",
    "dmgzone_flaps_frontleft", "dmgzone_flaps_frontright",
    "dmgzone_wings_backleft", "dmgzone_wings_backright",
    "dmgzone_wings_frontleft", "dmgzone_wings_frontright",
    "dmgzone_wings_rudder", "dmgzone_window_back",
    "dmgzone_window_front", "dmgzone_window_left", "dmgzone_window_right",
    "dmgzone_lights"
};
```

Aircraft-specific zones beyond standard car damage:
- 4 wing parts (front/back × left/right) — granular cosmetic damage
- 4 flap parts (matching wing layout)
- `wings_rudder` (rudder counts as wing for damage)
- 4 windows (cockpit canopy damage)

### VehicleAnimInstances catalog (per-aircraft player anim)

`override int GetAnimInstance() { return VehicleAnimInstances.XXX; }` — pick based on cockpit size/shape:

| Aircraft | AnimInstance | Vanilla DayZ vehicle template |
|---|---|---|
| Cessna180 | `GOLF` | Compact car cockpit (small piston single) |
| Catalina | `SEDAN` | Standard car cockpit (medium plane) |
| Spitfire | `GOLF` | Fighter cockpit fits GOLF shape |
| StuntPlane | `SEDAN` | |
| Tigermoth (all variants) | `SEDAN` (default) | |
| Z37_Bumblebee | `SEDAN` | |
| DC-3 | `V3S` | Truck cockpit (large transport) |
| Patty_Wagon | `V3S` | Truck cockpit |

Vanilla DayZ has these animation instances reusable without authoring custom anims: the `VehicleAnimInstances` enum at `P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1` lists `CIVVAN`, `V3S`, `SEDAN`, `HATCHBACK`, `BUS`, `S120`, `MULTICAR`, `GOLF`, `HMMWV`, `ZODIAC`, `MOTO1` and `MOTO2`, and none is made for an aircraft. Pick by character: small + tight = GOLF, standard cockpit = SEDAN, large/truck cabin = V3S.
