# Vehicle scripting traps

Which script overrides a drivable vehicle needs and which traps hit it at run time: the seated pose, a soft link to another mod's animations, getting in, vital parts and engine start, networking with physics, copying a binarized reference vehicle, wheels that never join the simulation, and state that is only true on the owner's client. Lines labelled `1.29` belong to a build that is not on `P:\`. The vehicle config and model rules are in the vehicles pack (`_shared/vehicles/README.md`).

## The driver's seated pose

`Transport.GetAnimInstance()` picks the seated driver pose and returns a `VehicleAnimInstances` value (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1`). The base method calls `Error("GetAnimInstance() not implemented")` (`P:\scripts\3_game\vehicles\transport.c:662` to `:670`), so every drivable vehicle must override it.

The values are `CIVVAN` 0, `V3S` 1, `SEDAN` 2, `HATCHBACK` 3, `BUS` 4, `S120` 5, `MULTICAR` 6, `GOLF` 7, `HMMWV` 8, `ZODIAC` 9, and in 1.30 also `MOTO1` 10 and `MOTO2` 11. Vanilla has no quad pose; a quad can reuse `V3S`.

## Using another mod's pose when it is loaded

To prefer another mod's pose (for example an animation pack whose own enum defines `QUADBIKE = 22`) and fall back when that mod is absent, don't name the other mod's enum, which is a hard compile dependency, and don't use `#ifdef`, which is decided at compile time and leaves no fallback. Check at run time and return the raw number:

```c
override int GetAnimInstance()
{
    if (GetGame().ConfigIsExisting("CfgPatches MyMod_OtherAnimPack"))
        return 22;  // QUADBIKE in the other mod's enum
    return VehicleAnimInstances.V3S;
}
```

This compiles without the other mod and picks the pose from the server's mod set. The raw number is tied to the other mod's enum value, so note the file and line that defines it next to the literal. It is an `if` because Enforce Script has no ternary operator.

## Getting in from both sides

The seat comes from the component the player looks at (`Transport.CrewPositionIndex(componentIndex)`, `P:\scripts\3_game\vehicles\transport.c:179`). The action is allowed by `CanReachSeatFromDoors(selection, fromPos)`, tried over several door selections (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:45` to `:68`). Each seat has one get in position (`pos_driver`) and a one sided get in animation.

To enter from either side, give the seat two entry components or door selections that map to the same crew index; the action is then reachable from both sides. A truly mirrored mount still needs a mirrored get in animation.

Before you change a value that native code reads, list which arguments you have seen and which you have assumed: a default in a signature is not the value the caller passes. Log it from an override first, or state the assumption and test it alone. For each field of an engine result used in a condition, measure its size, sign and range in game before choosing a threshold; without a measured sign, write a condition that doesn't depend on the sign.

## Vital parts decide engine start

A drivable vehicle decides which parts it needs through its `IsVital*()` methods, which all return `true` in the base classes: `IsVitalSparkPlug`, `IsVitalGlowPlug` and `IsVitalFuelTank` on `Transport` (`P:\scripts\3_game\vehicles\transport.c:404` to `:416`), and `IsVitalRadiator` on `CarScript` (`P:\scripts\4_world\entities\vehicles\carscript.c:2206`).

| Check | What happens | Source |
|---|---|---|
| `IsVitalGlowPlug()` true with no glow plug | The start check sets `NO_IGNITER` and the engine doesn't start | `carscript.c:1776` to `:1788` (about `:2011` to `:2015` in 1.29) |
| `IsVitalRadiator()` true with no radiator | The running engine damages itself every tick, with no coolant | `carscript.c:2206` |
| `IsVitalEngineBelt` | Declared and overridden by the trucks, but no vanilla script calls it in 1.30, so overriding it changes nothing | `carscript.c:2201` |
| `IsVitalCarBattery`, `IsVitalTruckBattery` | `[Obsolete("1.30: use Transport.NeedElectricitySourceDevice")]` and never called, so overriding them does nothing | `carscript.c:2811` to `:2821` |
| Battery | `NO_BATTERY` is set when `NeedElectricitySourceDevice()` returns true (default `true`) and `GetBattery()`, which casts `GetElectricitySourceDevice()` (default `null`), finds no charged battery | `P:\scripts\3_game\vehicles\transport.c:830` and `:826`; `carscript.c:1768` to `:1774`, `:2437` to `:2440` |

For the battery, override `NeedElectricitySourceDevice()`, `GetElectricitySourceDevice()` and `GetElectricitySourceDeviceType()`, as `offroadhatchback.c:61` to `:76` does with `CarBattery`.

A vehicle with a car battery and a spark plug, the common case, must override the checks for the parts it doesn't have, or it never starts. `OffroadHatchback` overrides `IsVitalGlowPlug()` to return `false` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:394`), its only `IsVital*` override. A quad with no radiator also overrides `IsVitalRadiator()` to return `false`.

## Networking on vehicles with physics

Measured in game on 1.29, on a helicopter whose parts are created by script:

- `CheckVitalItem` stops a healthy engine on the owner. In 1.29, `CarScript.EOnPostSimulate` (1.29 `carscript.c:986` to `:997`) calls `CheckVitalItem` (1.29 `:2513` to `:2524`) when `IsServerOrOwner()`, every `CARS_FLUIDS_TICK` of 1 s. On the owner it reads the local copy of the inventory and calls `EngineStop()` if the vital item is missing. With parts created by script after the spawn, a late copy stops a healthy engine about 1 s after the driver sits down. Override it as `override protected void CheckVitalItem(bool isVital, int slotId)` and do nothing outside the server. In 1.30 the tick calls `CheckVitalItemCallback(..., this, "EngineStop")` on `Transport` instead (`P:\scripts\4_world\entities\vehicles\carscript.c:839` to `:854`; `P:\scripts\3_game\vehicles\transport.c:420` to `:438`), and `CheckVitalItem` is `[Obsolete]` and never called (`carscript.c:2951` to `:2974`). Override `CheckVitalItemCallback` the same way; it is `protected void CheckVitalItemCallback(bool isVital, int slotId, Object caller = null, string callbackMethodName = "", Param params = null)` (`transport.c:420`); this is read in the 1.30 source and not yet measured in game.
- `SetPosition` on a client copy of a pawn with physics is not applied, not even for one frame. The former owner's copy stays at the last snapshot from before possession; a 10 cm move on the server had still not arrived after 25 s. Fix it on the server with an empty crew: `GetGame().RemoteObjectTreeDelete(obj)`, then `GetGame().RemoteObjectTreeCreate(obj)` (`P:\scripts\3_game\global\game.c:708` and `:710`; vanilla does it in `P:\scripts\3_game\systems\inventory\replaceitemwithnewlambdabase.c:117` to `:123`). Every client rebuilds its copy in the server's pose. The client's script instance is destroyed, and its `CallLater` calls die with it.
- `GetHealth01(zone, type)` on `Object` (`P:\scripts\3_game\entities\object.c:1001`) can't be called on a client. It throws `Virtual Machine Exception ... cannot be called on client`, which isn't fatal, and returns 0.
- The script log cuts every `Print` line at 255 characters, not only `DumpStackString(out string)` (`P:\scripts\1_core\proto\endebug.c:50`). Write diagnostics as several short lines that share an event tag, clip fields of variable length, and print stacks line by line.
- With physics, `ActionStopEngine.OnExecute` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\vehicles\actionstopengine.c:35` to `:59`) runs the stop only on the client. The server sees it through replication; its stack shows only `OnEngineStop`.

## Copying a binarized reference vehicle

When a vehicle is built by copying the `config.cpp` of a binarized Workshop vehicle, the overrides that make it work live in its script, which is binarized and unreadable: `IsVital*`, `GetSeatAnimationType`, `CrewCanGetThrough`, the get in mapping. Copying only the config compiles and looks complete, yet the vehicle won't start or won't let anyone in. Check the script side against an open vanilla car under `P:\scripts\`, such as `offroadhatchback.c`, not against the binarized reference.

- Match the `IsVital*` overrides to the real set of attachments (see "Vital parts decide engine start").
- The get in selection must exist in the `.p3d` geometry. The config's `actionSel="seat_driver"` or `"seat_codriver"` and the chain from `GetActionComponentNameList` to `CanReachSeatFromDoors` (`GetDoorConditionPointFromSelection` at `P:\scripts\4_world\entities\vehicles\carscript.c:2141` maps `seat_driver` to `seat_con_1_1`) need a named selection `seat_driver` or `seat_codriver` on faces of the Geometry LOD. The `seat_con_*` memory point is only where the mapping points; the override maps the name, it doesn't create it. Read the model back with `/dayz-p3d-audit` and confirm the selection is in the geometry, because a vehicle can pass every other model check and still fail to let anyone in, with no error.

## Wheels that never join the simulation

For PhysX to simulate a wheel, so that `WheelCountPresent()` is above 0 and not only `WheelCount()` (both at `P:\scripts\3_game\vehicles\car.c:345` to `:348`), the selection named by the wheel slot's `selection` entry in `CfgSlots` must exist in the body's Fire Geometry LOD and contain the faces of a wheel proxy (`proxy:\...`). The simulation attaches the wheel and its suspension at the proxy placed in the Fire Geometry LOD under the slot's name; this is engine behaviour, not checkable on `P:\`.

Vanilla cars, the sedan among them, use one name, typically `wheel_X_X`, for all three roles: the slot's `selection` in `CfgSlots`, the wheel proxy's selection in the visual LODs (hidden when the wheel is off), and the wheel proxy's selection in the Fire Geometry LOD. The name itself is free; it must be the same across the LODs.

The silent failure is mixed naming. The visual proxy sits in selection `A`, so `selection = "A"` in `CfgSlots` makes the wheel hide work, but the Fire Geometry proxy face sits in another selection `B`. The slot then names a selection that exists only in the visual LODs, and the wheel never joins the simulation. It compiles with no warning and no RPT error. Measured in game on a quad: `selection = "wheelfrontleft"` existed only in visual LODs 0 and 1, while the Fire Geometry proxy face was in `wheel_X_X`; adding the face to `wheelfrontleft` took `WheelCountPresent()` from 0 to 4.

Symptoms, all with no RPT error:

- `WheelCountPresent()` is 0 while `WheelCount()` is 4, so the config is fine.
- The wheels mount as inventory but never spin or grip; engine RPM rises with throttle while the speed stays near 0.
- The vehicle sinks a little into the terrain and bounces on its hull, because hull collision still works.
- Steering still turns the wheels, because that input comes from the animation, not the simulation.

To find it before testing in game:

1. From the `Slot_*` classes in `CfgSlots` that the `SimulationModule` `Axles` `Wheels` `Left` and `Right` `inventorySlot` entries name, read each slot's `selection = "<name>"`.
2. In the body `.p3d`, check that the Fire Geometry LOD has a selection named `<name>` holding the faces of a `proxy:\...` proxy.
3. If it is missing, fix it first. Every other symptom will point at suspension, mass or geometry instead.

The fix only adds: put the Fire Geometry proxy face into a new selection named after the slot's `selection` as well, without removing the original selection, so the visual hide keeps working. With py3d, copy the `points` and `faces` of the existing Fire Geometry selection that holds the proxy face into a new `Selection(lod.points, lod.faces)` and insert it into `lod.selections` under the slot's name. Read the file back and check that everything else is unchanged: mass, properties, other selections.

## `EngineIsOn()` is false on clients that don't own the vehicle

`EngineIsOn()` on `Car` (`P:\scripts\3_game\vehicles\car.c:230`), called on a client that doesn't own the pawn, returns false even while the server runs the engine, with no exception and no warning. Measured in game on a passenger: the native call read false while a replicated flag read true in the same frame, and the server log showed no stop. Any client feature that depends on `EngineIsOn()` switches itself off.

Replicate the state with a `RegisterNetSyncVariableBool` written in `OnEngineStart` and `OnEngineStop`, and make every client path read "native or replicated". A copy kept in the owner's own state doesn't help passengers.

When a client check decides to switch something off, print both sources in the same frame. That turns "it switches off by itself" into one line of data. A test that covers only the start of a state change misses the end, where the bug usually is; close the cycle with a hook the mod already has rather than with fake input.

## `HumanCommandVehicle` exists only where the get in action ran

`PlayerBase.GetCommand_Vehicle()` returns the local `HumanCommandVehicle`. In all of `P:\scripts\` there are exactly four `StartCommand_Vehicle` sites:

| Site | Source |
|---|---|
| The declaration | `P:\scripts\3_game\human.c:1526` |
| The get in action | `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:104` |
| Recovery from unconsciousness, from a local cache: `StartCommand_Vehicle` with `fromUnconscious` true | `P:\scripts\4_world\entities\dayzplayerimplement.c:2395` |
| A debug `StartCommand_Vehicle` path under `#ifdef DEVELOPER` | `P:\scripts\4_world\entities\manbase\playerbase.c:3541` |

No path creates the command from replicated crew. `CommandHandler` only uses an existing command and never creates one (`dayzplayerimplement.c:2369` to `:2384`).

On the owner, `ActionGetInTransport.Start()` creates it (`actiongetintransport.c:71` to `:111`). It is not under `#ifdef SERVER` and calls `GetDayZGame().GetBacklit().OnEnterCar()` (`:109`), which is client presentation code. The client's action manager calls it when the server accepts the action (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:86`, the `UA_AM_ACCEPTED` branch).

So any client action that requires "I am seated" behaves differently depending on how the player got into the seat. The vanilla test is `GetCommand_Vehicle()`, then `GetTransport()`, as in `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:28`. A player who used the get in action passes. A player seated by server script has the crew replicated, so `CrewMember(n) == player` is true on the client, yet `GetCommand_Vehicle()` is null and the action is never offered.

An in game test that seats the player from the server and then sends the feature's RPC skips that condition and passes while the human path is broken (`skills/dayz-launch-test/references/test-cell-vehicles.md`). Have the test's client half call its own `StartCommand_Vehicle` even when the seat already looks taken, and wait until `GetCommand_Vehicle().GetTransport()` is the vehicle before testing.

Test the action with the public `Can(PlayerBase, ActionTarget, ItemBase)` of `ActionBase` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:968`), never with `ActionCondition`, which is `protected`. Calling it from outside breaks the compile of the World module: the client doesn't start, while the server stays up because it doesn't compile client only classes. In 1.29 the public `Can` was at `actionbase.c:912`; in 1.30 the four argument overload with `condition_mask` sits above it at `:929`. 1.30 also added `UA_AM_INIT = 14`, which moved the later `UA_AM_*` values, so never hard code those numbers.
