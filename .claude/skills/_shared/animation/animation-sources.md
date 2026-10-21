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
| `initPhase` | Phase when the object spawns. | `Lid` 0 and `Lid2` 1 (`P:\DZ\gear\containers\config.cpp:104`, `:110`); `AnimSourceHidden` 1 (`P:\DZ\gear\camping\config.cpp:4430`) |
| `animPeriod` | How long the move takes. | 0.01 for the barrel lids (near instant); 0.018 for the fence gate (`P:\DZ\gear\camping\config.cpp:4435`) |

The class name is the source name: the `model.cfg` animation uses it as `source`, and script passes it to `SetAnimationPhase` (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:148` uses `"Lid"`, declared at `P:\DZ\gear\containers\config.cpp:101`).

`animPeriod` is time per unit of phase. The fence gate runs 0 to 100 with `animPeriod = 0.018`, so a full swing takes about 1.8 seconds, and script expects it to finish in about 2000 ms (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:13`, `GATE_ROTATION_TIME_APPROX`). With a 0 to 1 range, `animPeriod` is simply the duration in seconds.

Sources can inherit to share settings: fence declares `class AnimRotate` once and every gate part inherits it (`P:\DZ\gear\camping\config.cpp:4432` to `:4452`).

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

Taken from `Land_HouseBlock_3F_Corner1`, `P:\DZ\structures\residential\config.cpp:7385`.

| Key | Must match |
|---|---|
| Class name (`Doors5`) | The `source` of the door's `model.cfg` animation. The shipped house model uses source `doors5` for it. |
| `component` | The door's named component in the Geometry LOD, so the player can aim at it (`Building.GetDoorIndex(componentIndex)`, `P:\scripts\3_game\entities\building.c:28`). |
| `soundPos` | A Memory LOD point; the shipped model has `doors5_action`. |
| `animPeriod` | Seconds to open, with the usual 0 to 1 range. |
| `initOpened` | Vanilla uses 0.3 and 0.7. The name suggests the chance the door spawns open; script does not show it, so treat that as unconfirmed. |

Reuse the vanilla sound names until the mod has its own sounds; new sounds are audio work, not animation work.

## Hand over to the config specialist

Send `dayz-config-specialist` the exact class names, `source`, `initPhase` and `animPeriod` for every source, or the full `Doors` entries for a building, plus the `model` path. Names must match the `model.cfg` sources letter for letter.
