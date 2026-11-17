# Vehicle scripting traps

Script side traps on vehicles: the seated pose, a soft dependency on another mod's animations, get in, vital parts and engine start, networking on vehicles with physics, cloning a binarized reference vehicle, wheels that never join the simulation, and state that is only true on the owner's client. A line cited as `P:\...:N` was opened on `P:\`; results marked as measured were measured in game and were not re-run here; 1.29 line numbers are for a build that is not on `P:\`. The vehicle config and model rules are in the vehicles pack (`skills/_shared/vehicles/README.md`).

## The driver's seated pose is the `int` from `GetAnimInstance()`

The seated driver pose is chosen by `Transport.GetAnimInstance()`, which returns a `VehicleAnimInstances` value (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1`). The base method calls `Error("GetAnimInstance() not implemented")` (`P:\scripts\3_game\vehicles\transport.c:662-670`), so every drivable vehicle must override it. Vanilla has no quad pose: the values are `CIVVAN` = 0, `V3S` = 1, `SEDAN` = 2, `HATCHBACK` = 3, `BUS` = 4, `S120` = 5, `MULTICAR` = 6, `GOLF` = 7, `HMMWV` = 8, `ZODIAC` = 9, and in 1.30 also `MOTO1` = 10 and `MOTO2` = 11. A quad can reuse `V3S`.

## Soft dependency on another mod's animation pack (decided at run time, with a fallback)

To prefer another mod's pose (for example an animation pack whose own enum defines `QUADBIKE = 22`) but fall back when that mod is absent: do not name the other mod's enum (a hard compile dependency), and do not use `#ifdef` (decided at compile time, so one behaviour is baked in and there is no fallback at run time). Check at run time and return the raw number:

```c
override int GetAnimInstance()
{
    if (GetGame().ConfigIsExisting("CfgPatches <Mod>"))
        return <raw_int>;
    return VehicleAnimInstances.<vanilla>;
}
```

This compiles without the mod and picks the pose from the server's mod set. The cost: the raw number is tied to the other mod's enum value, so document the literal with the file and line that defines it. (It is an `if` because Enforce has no ternary operator, rule 1 in `hard-rules.md`.)

## Get in: one mount point per seat; both sides through two entry components

The seat is decided by the component the player looks at (`Transport.CrewPositionIndex(componentIndex)`, `P:\scripts\3_game\vehicles\transport.c:179`). The action is allowed by `CanReachSeatFromDoors(selection, fromPos)`, tried over several door selections (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:45-68`). The mount uses a single get in position per seat (`pos_driver`) and a one-sided get in animation. To enter from either side, give the seat two entry components or door selections that map to the same crew index: the action is then reachable from both sides. A truly mirrored mount still needs a mirrored get in animation.

Before changing a value that native code consumes, list which arguments you have seen and which you have assumed: a default in a signature is not the value the caller passes. Instrument first (an override that logs), or state the assumption and test it alone. For each field of an engine result used in a condition, list the kinds of input and measure its size, sign and range with a live probe before choosing a threshold: without a measured sign, write a condition that does not depend on the sign. A type definition plus a precedent is not verification.

## Vital parts decide engine start: override `IsVital*` when you clone a reference vehicle

A drivable vehicle decides which parts it needs to run through its `IsVital*()` methods, which all return `true` in the base classes: `IsVitalSparkPlug`, `IsVitalGlowPlug` and `IsVitalFuelTank` on `Transport` (`P:\scripts\3_game\vehicles\transport.c:404-416`), `IsVitalEngineBelt` and `IsVitalRadiator` (`P:\scripts\4_world\entities\vehicles\carscript.c:2201`, `:2206`). The battery is not an `IsVital*` check on 1.30: `IsVitalCarBattery` and `IsVitalTruckBattery` are `[Obsolete("1.30: use Transport.NeedElectricitySourceDevice")]` and no vanilla code calls them (`P:\scripts\4_world\entities\vehicles\carscript.c:2811-2821`), so overriding them does nothing. The start check sets `NO_BATTERY` when `NeedElectricitySourceDevice()` returns true (default `true`, `P:\scripts\3_game\vehicles\transport.c:821`) and `GetBattery()`, which casts `GetElectricitySourceDevice()` (default `null`, `transport.c:826`), finds no charged battery (`P:\scripts\4_world\entities\vehicles\carscript.c:1768-1774`, `:2437-2440`). Override `NeedElectricitySourceDevice()` and `GetElectricitySourceDevice()` (and `GetElectricitySourceDeviceType()`) for the battery your vehicle uses, as `offroadhatchback.c:61-76` does with `CarBattery`. The start check sets `NO_IGNITER` when a vital igniter part is missing or ruined (`P:\scripts\4_world\entities\vehicles\carscript.c:1776-1788`; about `:2011-2015` in 1.29): with `IsVitalGlowPlug()` true and no glow plug attached, the engine does not start. A radiator that is vital but absent makes the running engine damage itself every tick (no coolant). So a vehicle that uses a car battery and a spark plug (the common case) must override the checks for the parts it does not have, or it never starts. Vanilla shows the pattern: `OffroadHatchback` overrides `IsVitalGlowPlug()` to return `false` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:394`; it is the only `IsVital*` override in that file). A quad with no radiator or belt also overrides `IsVitalRadiator()` and `IsVitalEngineBelt()` to return `false`.

## Networking traps on vehicles with physics (measured 2026-08-17)

Five facts measured in game on 1.29, on a helicopter whose parts are created by script:

1. **`CheckVitalItem` stops a healthy engine on the owner.** `CarScript.EOnPostSimulate` (1.29 `carscript.c:986-997`) calls `CheckVitalItem` (1.29 `:2513-2524`) when `IsServerOrOwner()`, every `CARS_FLUIDS_TICK` = 1 s. On the owner it reads the local copy of the inventory and calls `EngineStop()` if the vital item is absent. With parts created by script after the spawn, a late copy stops a healthy engine about 1 s after sitting down (measured, with the stack). Remedy: `override protected void CheckVitalItem(bool,int)` that does nothing outside the server. On 1.30 the tick calls `CheckVitalItemCallback(..., this, "EngineStop")` on `Transport` instead (`P:\scripts\4_world\entities\vehicles\carscript.c:839-854`, `P:\scripts\3_game\vehicles\transport.c:420-438`), and `CheckVitalItem` is `[Obsolete]` and never called (`P:\scripts\4_world\entities\vehicles\carscript.c:2951-2974`), so that override does nothing there: override `CheckVitalItemCallback` the same way (read in the source, not measured on 1.30).

2. **`SetPosition` on a client proxy of a pawn with physics is not applied, not even for one frame.** The former owner's proxy stays at the last snapshot from before possession and never receives the transform (a 10 cm move on the server had not arrived after 25 s). Fix it on the server with an empty crew: `GetGame().RemoteObjectTreeDelete(obj)` then `GetGame().RemoteObjectTreeCreate(obj)` (`P:\scripts\3_game\global\game.c:708` and `:710`; vanilla does it in `P:\scripts\3_game\systems\inventory\replaceitemwithnewlambdabase.c:117-123`). Every client rebuilds its copy in the server's pose; the client's script instance is destroyed, and its `CallLater` calls die with it.

3. **`GetHealth01(zone, type)` on `Object` (`P:\scripts\3_game\entities\object.c:1001`) cannot be called on a client.** It throws `Virtual Machine Exception ... cannot be called on client` (not fatal; it returns 0).

4. **The script log cuts every `Print` line at 255 characters**, not only `DumpStackString(out string)` (`P:\scripts\1_core\proto\endebug.c:50`): measured 2026-09-09, 172 of 193 diagnostic lines of one mod were cut at exactly 255, losing the fields that mattered. Write diagnostics as several short lines that share an event tag (`Hologram#12 wall …`, `Hologram#12 ground …`), clip fields of variable length, and print stacks line by line.

5. **With physics, `ActionStopEngine.OnExecute` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\vehicles\actionstopengine.c:35-59`) runs the stop only on the client.** The server sees it through replication (its stack shows only `OnEngineStop`).

## Cloning a binarized reference vehicle: the config is not the whole contract

When a vehicle is built by copying the `config.cpp` of a binarized Workshop vehicle, the overrides that make it work live in its script, which is binarized and not visible: `IsVital*`, `GetSeatAnimationType`, `CrewCanGetThrough`, the get in mapping. Cloning only the config compiles and looks complete, yet the vehicle will not start or will not let you in. Check the script side against an open vanilla equivalent under `P:\scripts\` (for example `offroadhatchback.c`), not against the binarized reference. Two checks that catch people:

- **`IsVital*`**: match the overrides to the real set of attachments (previous section).
- **The get in action selection must exist in the `.p3d` geometry.** The config's `actionSel="seat_driver"` or `"seat_codriver"` and the chain from `GetActionComponentNameList` to `CanReachSeatFromDoors` (`GetDoorConditionPointFromSelection` at `P:\scripts\4_world\entities\vehicles\carscript.c:2141` maps `seat_driver` to `seat_con_1_1`) need a named selection `seat_driver` or `seat_codriver` painted on faces of the Geometry LOD. The `seat_con_*` memory point is only the destination of the mapping; the override maps the name, it does not create it. Read the `.p3d` back with py3d and confirm the action selection exists in the geometry: a vehicle can pass every internal model check and still have get in fail silently. `/dayz-p3d-audit` reads the geometry side back.

## Wheels and the simulation: `CfgSlots` `selection` must match the Fire Geometry proxy selection

For PhysX to simulate a wheel (`WheelCountPresent() > 0`, not just `WheelCount() = N`; both are declared at `P:\scripts\3_game\vehicles\car.c:345-348`), the selection that the wheel slot's `selection` entry in `CfgSlots` names must exist in the Fire Geometry LOD of the body and must contain the faces of a wheel proxy (`proxy:\…`). The simulation attaches a wheel and its suspension at the proxy placed in the Fire Geometry LOD under the wheel slot's name (engine behaviour, not checkable on `P:\`).

**The vanilla pattern** (the sedan and others): one name, typically `wheel_X_X`, used for all three roles: the slot's `selection` in `CfgSlots`, the wheel proxy's selection in the visual LODs (hidden when the wheel is detached), and the wheel proxy's selection in the Fire Geometry LOD. What must hold is that the name is the same across LODs; the name itself is free.

**The mistake that fails silently:** mixed naming. The visual proxy is in selection `A` (so `selection = "A"` in `CfgSlots` makes the wheel hide work), but the Fire Geometry proxy face lives in another selection `B`. The slot then points at a selection that exists only in the visual LODs, the simulation LOD has no proxy in that selection, and the wheel never joins the PhysX simulation. It compiles cleanly, with no warning and no RPT error.

**Symptoms (with no RPT error):**

- `WheelCountPresent() = 0` while `WheelCount() = 4` (the config is fine).
- The wheels mount as inventory but never spin or give traction; engine RPM rises with throttle but the speed stays near 0.
- The vehicle sinks a little into the terrain and bounces on its hull (hull collision still works).
- Steering animates the wheels (the input comes from the animation graph, apart from the simulation) although they do not simulate.

**How to detect it offline with py3d:**

1. From the `Slot_*` classes in `CfgSlots` that `SimulationModule` `Axles` `Wheels` `Left` or `Right` `inventorySlot` refer to, read each slot's `selection = "<name>"`.
2. In the body `.p3d`, check that the Fire Geometry LOD has a selection named `<name>` and that it contains the faces of a `proxy:\…` proxy.
3. If it is missing, this is the first thing to fix: the vehicle will not drive, it fails silently, and every later analysis will point you at suspension, mass or geometry instead.

**The fix (it only adds, and keeps the visual hide):** put the Fire Geometry proxy face into a new selection named `<name>` (the slot's `selection`) as well, without removing the original selection. With py3d: read the existing Fire Geometry selection that contains the proxy face, build a new `Selection(lod.points, lod.faces)` with `points` and `faces` dictionaries copied from it, and insert it into `lod.selections` under the slot's `selection` name. Read the file back and check that everything else is byte identical (mass, properties, other selections).

**Measured in game on a quad (2026-05-27).** `wheelPresent=0` cost about 12 failed attempts over a month, all aimed at suspension, mass, hub geometry or `class=vehicle`, none of which was the cause. The cause was `selection = "wheelfrontleft"` in `CfgSlots`, a selection that existed only in the visual LODs 0 and 1 where the visual proxy was made for the wheel hide, while the Fire Geometry proxy face lived in the `wheel_X_X` selection. Adding the Fire Geometry proxy face to `wheelfrontleft` as well (one py3d session) took `wheelPresent` from 0 to 4 on the next deploy. A parity audit must include whether the wiring is consistent across LODs, not only the geometry.

## `EngineIsOn()` is always false on a client that is not the owner: replicate the state

`EngineIsOn()` on `Car` (`P:\scripts\3_game\vehicles\car.c:230`), called on a client that does not own the pawn, returns false even when the server has the engine running, with no exception and no warning. Measured on the occupant of seat 1 with a probe that read both sources in the same frame (`natEng=false syncEng=true`) while the server log showed no stop. Consequence: any client subsystem that depends on `EngineIsOn()` switches itself off (here the thermal camera died at once).

Remedy: replicate the state (a `RegisterNetSyncVariableBool` written in `OnEngineStart` and `OnEngineStop`) and make every client path read "native or replicated". A snapshot kept in the owner's state (`m_EngineOnAuthority`) does not serve passengers; it exists only for the owner.

**Probe both sources.** When a client check decides to switch something off, print both sources (native and replicated) in the same frame. That turns "it switches off by itself" into one line of data and proves the fix in the same run.

**Autotests: close the transition.** An autotest that covers only the entry of a transition does not test the exit, where the bug usually lives. Close the cycle with a hook the project already has (a watcher that forces the cancel) instead of synthetic input. (Measured in a helicopter's thermal camera autotests.)

## `HumanCommandVehicle` is local to the client: the get in action creates it, crew replication does not

`PlayerBase.GetCommand_Vehicle()` returns the local `HumanCommandVehicle`. In the whole of `P:\scripts\` there are exactly four `StartCommand_Vehicle` sites: the proto (`P:\scripts\3_game\human.c:1526`), the get in action (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:104`), the recovery from unconsciousness, which uses a local cache (`P:\scripts\4_world\entities\dayzplayerimplement.c:2395`, with `fromUnconscious` true), and a path under `#ifdef DEVELOPER` (`P:\scripts\4_world\entities\manbase\playerbase.c:3541`). No path creates the command from replicated crew. `CommandHandler` only uses an existing command (`P:\scripts\4_world\entities\dayzplayerimplement.c:2369-2384`); it does not create one.

On the owner the creator is `ActionGetInTransport.Start()` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:71-111`), which is not under `#ifdef SERVER` and calls `GetDayZGame().GetBacklit().OnEnterCar()` (`:109`), presentation code, so it runs on the client. The client's action manager calls it when the server accepts the action (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:86`, the `UA_AM_ACCEPTED` branch).

**What it means for mod code:** any client action that requires "I am seated" (the vanilla pattern is `GetCommand_Vehicle()` then `GetTransport()`, as in `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:28`) behaves differently depending on how the player got into the seat. A human who used the normal get in action passes; an occupant placed by server script has the crew replicated (`CrewMember(n) == player` is true on the client) and yet `GetCommand_Vehicle()` is null, so the action is never offered.

**What it means for in game autotests (the `dayz-test-ingame` material):** an autotest that seats the player from the server and then sends the subsystem's RPC skips the real condition and reports green on a human path that may be broken. Measured: a helicopter's FLIR could not be opened by hand for months while the autotest passed, because the test sent the RPC directly. Remedy: the client half of the autotest calls its own `StartCommand_Vehicle` even when the seat already looks occupied, and does not probe until `GetCommand_Vehicle().GetTransport() == <vehicle>`. The probe must evaluate the public `Can(player, target, item)` of `ActionBase` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:968`), never `ActionCondition`, which is `protected`: calling it from outside breaks the compile of the world module (the client does not start; the server stays up because it does not compile client only classes). Until 1.29 the public `ActionBase.Can` was at `actionbase.c:912`. Since 1.30 the three argument `Can(PlayerBase, ActionTarget, ItemBase)` is at `:968` and the four argument overload (with `condition_mask`) is above it at `:929`; the rule "probe `Can`, never `ActionCondition`" is unchanged. `UA_AM_INIT = 14` moved the later `UA_AM_*` values, so do not hard-code those numbers.

Measured: the probe line `[FLIR] action gate can=false cond=false vehCmd=false natEng=false syncEng=true` with `seat fixed (client) crew=1` and no `seat commanded (client)` in the same log.
