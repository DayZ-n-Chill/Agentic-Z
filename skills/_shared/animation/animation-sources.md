# Animation sources in config.cpp

The `config.cpp` side of an animation: what a `model.cfg` `source` points at, for items and for buildings. The class itself is written by `dayz-config-specialist`; this file says which entries the animation needs so you can hand them over.

## Items and placed objects: `class AnimationSources`

An item drives its animations through user sources declared in its `CfgVehicles` class. Script then sets their phase.

```cpp
class AnimationSources
{
    class Lid
    {
        source = "user";
        initPhase = 0;
        animPeriod = 0.01;
    };
};
```

| Key | Meaning | Vanilla values |
|---|---|---|
| `source` | `"user"` means script sets the phase. | `"user"` in every vanilla source below |
| `initPhase` | Phase when the object spawns. | `Lid` 0 and `Lid2` 1 (`P:\DZ\gear\containers\config.cpp:104`, `:110`); `AnimSourceHidden` 1 (`P:\DZ\gear\camping\config.cpp:4440`) |
| `animPeriod` | How long the move takes. | 0.01 for the barrel lids (near instant); 0.018 for the fence gate (`P:\DZ\gear\camping\config.cpp:4445`) |

The class name is the source name: the `model.cfg` animation uses it as `source`, or as the animation's own name when the model source is `user` (fence), and script passes it to `SetAnimationPhase` (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:148` uses `"Lid"`, declared at `P:\DZ\gear\containers\config.cpp:101`).

`animPeriod` is time per unit of phase. The fence gate runs 0 to 100 with `animPeriod = 0.018`, so a full swing takes about 1.8 seconds, and script expects it to finish in about 2000 ms (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:13`, `GATE_ROTATION_TIME_APPROX`). With a 0 to 1 range, `animPeriod` is simply the duration in seconds.

Sources can inherit to share settings: fence declares `class AnimRotate` once and every gate part inherits it (`P:\DZ\gear\camping\config.cpp:4442` to `:4480`).

`animPeriod` is one value for both directions. A part that must go out and come back at different speeds cannot do it through `animPeriod` alone.

A hide source that should start hidden uses `initPhase = 1`: the flag declares `folded` with `initPhase=0` and `unfolded` with `initPhase=1` (`P:\DZ\gear\camping\config.cpp:13062` to `:13076`), and its script swaps the two when it is attached (see `attach-state-parts.md`).

## Vehicles: which sources are declared and which the engine supplies

A car declares its doors, seats and suspension as `user` sources. `CarScript` also declares the `user` sources `HideDestroyed_1_1` to `HideDestroyed_2_2`, and damage sources with `source="Hit"` plus a `hitpoint` key: `AnimHitWheel_1_1` to `AnimHitWheel_2_2` and `HitDoorsHood`, `HitDoorsTrunk`, `HitDoorsDrivers`, `HitDoorsCoDrivers`, `HitDoorsCargo` (`P:\DZ\vehicles\wheeled\config.cpp:368` to `:429`). The motorbike's `AnimHitWheel_1` adds `raw=1` to its `Hit` source (`P:\DZ\vehicles\singletrack\config.cpp:137` to `:142`), the only vanilla use of that key; what it changes is not visible on `P:\`. A `Hit` source follows the named hit point's damage, not script:

| Declared in `AnimationSources` | Where | Driven by |
|---|---|---|
| `DoorsDriver`, `DoorsCoDriver`, `DoorsHood`, `DoorsTrunk` | `P:\DZ\vehicles\wheeled\config.cpp:353` to `:365` | Script. |
| `SeatDriver`, `SeatCoDriver` | `P:\DZ\vehicles\wheeled\config.cpp:1509`, `:1515` | Script. |
| `damper_1_1` and the other dampers | `P:\DZ\vehicles\wheeled\config.cpp:1521`; the wheel names its damper with `animDamper="damper_1_1"` (`:1456`) | The simulation, through that key. |

The sources for steering (`steeringwheel`), wheel spin (`wheelfrontleft` and its siblings), steered hubs (`turnfrontleft`, `turnfrontright`) and gauges (`speed`, `rpm`, `fuel`, `coolant`) are used by the hatchback's model (`P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d`) and are not declared in `AnimationSources`. The engine supplies them. Steering and gauges are named only in `model.cfg`. The wheel and hub sources are also named by the `SimulationModule` wheel classes, the same way as `animDamper`: `animTurn="turnfrontleft"` and `animRotation="wheelfrontleft"` (`P:\DZ\vehicles\wheeled\config.cpp:294` to `:295`), or `animTurn="turnfront"` and `animRotation="wheelfront"` on a single track vehicle (`P:\DZ\vehicles\singletrack\config.cpp:78` to `:79`). A mod vehicle inherits these keys or writes its own, and uses the same names in `model.cfg`. Older Bohemia documentation lists many more engine sources (aircraft, turrets, clocks); before using one, find it in a shipped DayZ model.

## Diagnosing a `user` source: a read phase does not prove movement

`GetAnimationPhase(src) == 1.0` before the first `SetAnimationPhase(src, 1)` does not prove the part is at phase 1. A source that is not registered on that object can read the same way. Before blaming the phase:

1. List the sources with `GetNumUserAnimationSourceNames()` and `GetUserAnimationSourceName(int index)` (`P:\scripts\3_game\entities\entity.c:17`, `:19`) and confirm `src` is among them.
2. Compare on the same model with a source that does move something, for example a rotor proxy. A selection made of the model's own faces on a bone can fail to move where a proxy on that bone does; for doors, consider making the door a proxied sub-model.

Keep the probe read only. Do not call `SetAnimationPhase(door, 0)` to see whether a source exists: it changes live state. If the door was open, a cached open state in the mod's own script may not restore it, leaving it shown closed while the logic says open until the next toggle. Test writing through the real open and close action with logging added.

The second point and the cache trap were seen in game on one vehicle mod; they are not checked on `P:\`.

## Buildings: `class Doors`

A building opens its doors with no mod script. The class inherits from a house base such as `HouseNoDestruct` (`P:\DZ\data\config.cpp:3119`), lists each door in `class Doors`, and the player's built in `ActionOpenDoors` does the rest (`P:\scripts\4_world\entities\manbase\playerbase.c:1697`).

```cpp
class Doors
{
    class Doors5
    {
        displayName = "door 5";
        component = "Doors5";
        soundPos = "doors5_action";
        animPeriod = 1;
        initPhase = 0;
        initOpened = 0.7;
        soundOpen = "doorWoodSmallOpen";
        soundClose = "doorWoodSmallClose";
        soundLocked = "doorWoodSmallRattle";
        soundOpenABit = "doorWoodSmallOpenABit";
    };
};
```

Taken from `Land_HouseBlock_3F_Corner1` (`P:\DZ\structures\residential\config.cpp:7341`), entry at `:7385`.

| Key | Must match |
|---|---|
| Class name (`Doors5`) | The `source` of the door's `model.cfg` animation. The shipped house model uses source `doors5` for it. |
| `component` | The door's named component in the View Geometry LOD, so the player can aim at it (`Building.GetDoorIndex(componentIndex)` works from the view geometry component index, `P:\scripts\3_game\entities\building.c:27` to `:28`). |
| `soundPos` | A Memory LOD point; the shipped model has `doors5_action`. |
| `animPeriod` | Seconds to open, with the usual 0 to 1 range. |
| `initOpened` | The common vanilla values are 0.3 (1,051 entries) and 0.7 (935); the Badlands houses that can be rebuilt use 2 (566, `P:\DZ\structures_takistan\Residential\config.cpp:32`), and 0.5, 0, 1 and 0.1 also occur (`P:\DZ\structures_sakhal\config.cpp:3088`, `:3702`, `P:\DZ\structures\wrecks\config.cpp:95`). The name suggests the chance the door spawns open; no script reads the key, so treat that as unconfirmed. |

Reuse the vanilla sound names until the mod has its own sounds; new sounds are audio work, not animation work.

## Hand over to the config specialist

Send `dayz-config-specialist` the exact class names, `source`, `initPhase` and `animPeriod` for every source, or the full `Doors` entries for a building, plus the `model` path. Names must match the `model.cfg` sources letter for letter.
