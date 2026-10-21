# Attachments, parts and crew

How a vehicle takes doors, wheels and engine parts, how the inventory groups them, and how seats and doors work together.

## The chain for one attachment

A part attaches only when all four links exist:

1. The vehicle lists the slot name in `attachments[]` (`OffroadHatchback`, `P:\DZ\vehicles\wheeled\config.cpp:1255`).
2. `CfgSlots` has a class `Slot_<name>` whose `name=` is that slot name (`Slot_NivaDriverDoors`, `P:\scripts\config.cpp:1077`). Script looks a slot up by the class name `Slot_` plus the slot name, not by `name=` or `displayName=` (`P:\scripts\3_game\systems\inventory\inventoryslots.c:28` to `:42`). A slot that shows a model part gives `selection=` the model selection (`Slot_NivaWheel_1_1` uses `selection="wheel_1_1"`, `P:\scripts\config.cpp:1030`).
3. The part item lists the same slot in `inventorySlot[]` (`HatchbackDoors_Driver`, `P:\DZ\vehicles\wheeled\config.cpp:908` to `:918`).
4. For wheels, the axle's `Wheels` subclass names the slot in `inventorySlot` (`:1452` to `:1463`), so the simulation knows which wheel is which.

A slot name missing from `CfgSlots` fails with no error. Vanilla slot names such as `CarBattery`, `SparkPlug`, `GlowPlug`, `CarRadiator`, `Reflector_1_1` and `Reflector_2_1` already exist (`P:\scripts\config.cpp:852` to `:915`); reuse them so vanilla parts fit. Give every new slot a mod prefix (`MyMod_Door_1_1`).

```cpp
class CfgSlots
{
    class Slot_MyMod_Door_1_1
    {
        name = "MyMod_Door_1_1";
        displayName = "#STR_CfgDoor0";
        ghostIcon = "set:dayz_inventory image:doorfront";
    };
};
```

The `displayName` and `ghostIcon` values above are the ones vanilla uses for a front door (`P:\scripts\config.cpp:1852` to `:1857`). Rear doors use `image:doorrear` (`:1148` to `:1152`).

## Part classes

| Part | Config base | Script base | Notes |
|---|---|---|---|
| Door, hood, trunk | `CarDoor: Inventory_Base` (`P:\DZ\vehicles\wheeled\config.cpp:75`) | `CarDoor` (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:568`) | Base sets `hiddenSelections[]={"dmgZone_doors"}` and `lockType=2`. Each door has its own `DamageSystem` with `Window` and `Doors` zones (`HatchbackDoors_Driver`, `:924` to `:1028`). |
| Wheel | `CarWheel: Inventory_Base` (`:14`) | `CarWheel` (`inventoryitem.c:194`) | One wheel class can list every wheel slot plus the spare (`HatchbackWheel`, `:853` to `:867`). Tyre physics keys: see `simulation.md`. A ruined variant inherits `CarWheel` too (`HatchbackWheel_Ruined`, `:882`). |
| Battery, plugs, radiator | `P:\DZ\vehicles\parts\config.cpp` | `CarBattery` (`P:\scripts\4_world\entities\itembase\vehiclebattery\carbattery.c:1`), `GlowPlug`, `SparkPlug`, `CarRadiator` (`inventoryitem.c:939`, `:952`, `:834`) | Reuse the vanilla parts. |

Vanilla declares an empty script class for every door and wheel it ships (`class HatchbackDoors_Driver extends CarDoor {};`, `inventoryitem.c:695`). Do the same for your parts.

`GlowPlug` declares `inventorySlot` as a string (`P:\DZ\vehicles\parts\config.cpp:831`) while doors and wheels use the array form. When you change a part's slots, follow the string versus array rule in `.claude/skills/_shared/conventions/config.md`.

## Inventory categories

`class GUIInventoryAttachmentsProps` groups slots into the tabs a player sees (`OffroadHatchback`, `P:\DZ\vehicles\wheeled\config.cpp:2307`). Vanilla uses three groups, each with `name`, `description`, `icon` and `attachmentSlots[]`: `Engine` (battery, radiator, plug), `Body` (lights, doors, hood, trunk, spare) and `Chassis` (wheels). Every slot in `attachments[]` belongs in one group.

Script can hide a group or the cargo: vanilla cars hide the `engine` group while the hood is closed and the cargo while the trunk is closed (`CanDisplayAttachmentCategory` and `CanDisplayCargo`, `P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:163`, `:182`).

Cargo space is `class Cargo` with `itemsCargoSize[]`, `allowOwnedCargoManipulation` and `openable` (`P:\DZ\vehicles\wheeled\config.cpp:1501`).

## Rules for taking parts off

- `CarScript.CanReleaseAttachment` refuses any part while the engine runs and the car moves (`P:\scripts\4_world\entities\vehicles\carscript.c:638`).
- Vanilla cars add their own rule: no battery, radiator or plug removal while the hood is closed or the engine runs (`offroadhatchback.c:139`; `offroad_02.c:155`).
- The spare wheel uses `CanManipulateSpareWheel`, which returns `false` in `CarScript` (`carscript.c:670`). Override it, as vanilla does for an open trunk or hood (`offroadhatchback.c:158`), or the spare can never be fitted or removed by hand. The check runs for slots whose selection is `wheel_spare_1` or `wheel_spare_2` (`carscript.c:609` to `:636`).

## Crew and seats

`class Crew` lists the seats. The base is in `CarScript` (`P:\DZ\vehicles\wheeled\config.cpp:265` to `:282`):

| Key | Driver value | Meaning |
|---|---|---|
| `actionSel` | `"seat_driver"` | Model selection the get in action targets. |
| `proxyPos` | `"crewDriver"` | Crew proxy in the model where the player sits. |
| `getInPos`, `getInDir` | `"pos_driver"`, `"pos_driver_dir"` | Memory points for getting in. |
| `isDriver` | `1` | Only on the driver seat. |

A four seat car adds `class Cargo1` and `class Cargo2` with `seat_cargo1`, `crewCargo1`, `pos_cargo1` and `pos_cargo1_dir` (`Offroad_02`, `:20990`). The seat index script sees follows this order: driver `0`, co driver `1`, then cargo seats, which is how `GetSeatAnimationType` maps them (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:138`).

## Doors and seats in script

| Method | Where | What a new car returns |
|---|---|---|
| `int GetCarDoorsState(string slotType)` | `carscript.c:2243`; override `offroad_02.c:218` | `DOORS_MISSING` when no door is attached, otherwise `TranslateAnimationPhaseToCarDoorState("<anim source>")`, which reads open above phase `0.5` (`carscript.c:2248`). |
| `string GetAnimSourceFromSelection(string selection)` | `offroad_02.c:360` | Maps model selections (`doors_driver`, `doors_cargo1`) to animation sources (`DoorsDriver`, `DoorsCargo1`). |
| `bool CrewCanGetThrough(int posIdx)` | `offroad_02.c:253` | `false` when that seat's door is closed. |
| `string GetDoorInvSlotNameFromSeatPos(int posIdx)` | `carscript.c:2167`; override `offroad_02.c:310` | The door slot for each seat. |
| `string GetDoorSelectionNameFromSeatPos(int posIdx)` | `carscript.c:2162` | The door selection for each seat. |
| `string GetDoorConditionPointFromSelection(string selection)` | `carscript.c:2141` | Memory point near the seat (`seat_con_1_1` and so on) that `CanReachSeatFromDoors` measures from (`carscript.c:2177`). |
| `bool CanReachSeatFromSeat(int currentSeat, int nextSeat)` | `offroad_02.c:381` | Which seats a player may switch between. |

`CarDoorState` is `DOORS_MISSING`, `DOORS_OPEN`, `DOORS_CLOSED` (`carscript.c:1`).

Every door needs an `AnimationSources` class with `source="user"`. `CarScript` defines `DoorsDriver`, `DoorsCoDriver`, `DoorsHood` and `DoorsTrunk` (`P:\DZ\vehicles\wheeled\config.cpp:351` to `:366`); a car with rear doors adds `DoorsCargo1` and `DoorsCargo2` itself (`Offroad_02`, `:21143`).

## Actions

`CarScript.SetActions` registers open and close doors, get in, lights, horn and push (`carscript.c:2313`). Override it with `super` and `AddAction` or `RemoveAction` only when the vehicle needs different actions. New action classes belong to dayz-script-specialist.

## What the model must provide

Hand this list to the art lead. Each name comes from a vanilla config key or script call above.

- Selections: one per door (`doors_driver`), seat selections (`seat_driver`, `seat_cargo1`), the `dmgZone_*` selections used in `DamageSystem`, light selections (`light_left`, `light_right`, `light_dashboard`, `P:\DZ\vehicles\wheeled\config.cpp:260` to `:263` in `CarScript`).
- Proxies: `crewDriver`, `crewCoDriver`, `crewCargo1` and so on.
- Memory points: `pos_driver`, `pos_driver_dir` and one pair per seat; `wheel_1_1_damper_land` and the other hubs; `seat_con_1_1` and the other door condition points; `refill` for the fuel cap (`P:\scripts\3_game\vehicles\transport.c:112`).
- Animations: one per door source, the wheel turn, rotation and damper animations named in `simulation.md`.
