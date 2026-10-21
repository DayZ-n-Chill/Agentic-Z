# Vehicle pack

Reference for building cars, boats and helicopters: the class tree, simulation config, attachment slots, crew seats, fluids and damage. Every fact cites the vanilla file on `P:\` it came from. Line numbers match the vanilla data at the time of writing; when a line has moved, Grep for the class or key name.

Open only the file the current step needs.

| Question | File |
|---|---|
| Which parent class, which addon to require, which script class to write, which overrides are mandatory | `class-hierarchy.md` |
| `SimulationModule` keys: engine, clutch, gearbox, axles, suspension, wheels, boat propeller | `simulation.md` |
| `attachments[]`, `CfgSlots`, door and wheel part classes, inventory categories, crew seats, door states | `attachments-and-crew.md` |
| Fuel, oil, coolant and brake fluid, engine start rules, battery and plugs | `fluids-and-engine.md` |
| `DamageSystem` zones, zone names script depends on, crash damage to the vehicle and crew | `damage.md` |
| Helicopters on the native helicopter base classes | `helicopters.md` |

## Where vanilla keeps vehicle data

| What | Path on `P:\` |
|---|---|
| Native config parents (`Transport`, `Car`, `Boat`, `Helicopter`) | `P:\bin\config.cpp:1404` to `:1563` |
| Cars, their doors and wheels | `P:\DZ\vehicles\wheeled\config.cpp` (addon `DZ_Vehicles_Wheeled`) |
| Boats | `P:\DZ\vehicles\water\config.cpp` (addon `DZ_Vehicles_Water`) |
| Batteries, plugs, radiators and other shared parts | `P:\DZ\vehicles\parts\config.cpp` (addon `DZ_Vehicles_Parts`) |
| Inventory slot definitions (`CfgSlots`) | `P:\scripts\config.cpp:11` (addon `DZ_Scripts`) |
| Native script classes | `P:\scripts\3_game\vehicles\` (`transport.c`, `car.c`, `boat.c`, `helicopter.c`) |
| Script classes | `P:\scripts\4_world\entities\vehicles\` (`carscript.c`, `boatscript.c`, `helicopterscript.c`, `inheritedcars\`, `inheritedboats\`) |
| Door, wheel and plug item scripts | `P:\scripts\4_world\entities\core\inherited\inventoryitem.c` |
