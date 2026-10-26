# Fluids and engine start

Fuel, oil, coolant and brake fluid on cars and boats, the config keys that size them, and the rules that decide whether the engine starts and keeps running.

## Fluid types

`ETransportFluid` is `FUEL`, `OIL`, `BRAKE`, `COOLANT`, then `USER1` to `USER4` reserved for mods (`P:\scripts\3_game\vehicles\transport.c:52`). Cars use it as `CarFluid` (`P:\scripts\3_game\vehicles\car.c:17`), boats as `BoatFluid` (`P:\scripts\3_game\vehicles\boat.c:13`).

## Config keys

| Key | `CarScript` value (`P:\DZ\vehicles\wheeled\config.cpp`) | Notes |
|---|---|---|
| `fuelCapacity` | `50` (`:243`) | Cars override it: `OffroadHatchback` `42` (`:1346`), `Offroad_02` `115` (`:20980`). Boat: `25` (`P:\DZ\vehicles\water\config.cpp:53`). |
| `fuelConsumption` | not set | Set per car: `OffroadHatchback` `11` (`:1347`), `Offroad_02` `30` (`:20981`). |
| `brakeFluidCapacity` | `1` (`:244`) | |
| `oilCapacity` | `4` (`:245`) | |
| `coolantCapacity` | `6` (`:246`) | |
| `brakeFluidLeakDebit[]`, `oilLeakDebit[]`, `coolantLeakDebit[]` | `{0,0}` (`:247` to `:249`) | |
| `brakeFluidForceCoef[]`, `damageFromOil[]`, `damageFromCoolant[]` | (`:250` to `:252`) | |
| `engineBeltSlot`, `batterySlot` | `"EngineBelt"`, `"CarBattery"` (`:253`, `:254`) | |
| `electricConsumptionIgnition`, `electricConsumptionEngine`, `electricConsumptionLights`, `electricOutputEngine` | `3001`, `0`, `0`, `5` (`:256` to `:259`) | |

The native `Transport` class sets fallback capacities (`fuelCapacity=100` and so on, `P:\bin\config.cpp:1410`), but every vanilla car sets its own through `CarScript`. P:\ does not document the units; treat the vanilla numbers as the scale.

A "bigger fuel tank" is one key on a class that inherits the car: `fuelCapacity = 160;` on `MyMod_Offroad_02_Long: Offroad_02`.

## Fluids from script

Native on `Car` (`P:\scripts\3_game\vehicles\car.c`) and, with `BoatFluid`, on `Boat` (`boat.c:135` to `:152`):

| Call | Line in `car.c` |
|---|---|
| `float GetFluidCapacity(CarFluid fluid)` | `:355` |
| `float GetFluidFraction(CarFluid fluid)` (0 to 1) | `:363` |
| `void Leak(CarFluid fluid, float amount)` | `:366` |
| `void LeakAll(CarFluid fluid)` | `:369` |
| `void Fill(CarFluid fluid, float amount)` | `:372` |
| `void OnFluidChanged(CarFluid fluid, float newValue, float oldValue)`, called on the owner only | `:413` |

When the economy creates a car, `CarScript.EEOnCECreate` fills a random amount up to 35 percent of fuel capacity (`P:\scripts\4_world\entities\vehicles\carscript.c:2412`). Debug spawns call `FillUpCarFluids`, which fills fuel, coolant and oil (`carscript.c:2561`), from `OnDebugSpawn` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:425`).

## Will the engine start

`CarScript.OnBeforeEngineStart` returns `true` only when `CheckOperationalRequirements` reports `ECarOperationalState.OK` (`carscript.c:1713`, `:1752`). It fails for:

| Flag | Condition (`carscript.c:1752` to `:1790`) |
|---|---|
| `RUINED` | The car is destroyed or the `Engine` damage zone is ruined. |
| `NO_FUEL` | Fuel fraction is `0`. |
| `NO_BATTERY` | `NeedElectricitySourceDevice()` is true and the battery is missing, ruined, or has less energy than `GetBatteryConsumption()`. |
| `NO_IGNITER` | `IsVitalSparkPlug()` is true and the `SparkPlug` slot is empty or ruined; or `IsVitalGlowPlug()` is true and the `GlowPlug` slot is empty or ruined. |

The defaults all return `true` (`P:\scripts\3_game\vehicles\transport.c:404` spark plug, `:409` glow plug, `:414` fuel tank, `:821` electricity source). Each vanilla car switches off what it lacks:

| Car | Override | Result |
|---|---|---|
| `OffroadHatchback`, `CivilianSedan`, `Hatchback_02`, `Sedan_02` | `IsVitalGlowPlug()` returns `false` (`offroadhatchback.c:394`) | Petrol: needs a spark plug. |
| `Offroad_02` | `IsVitalSparkPlug()` and `IsVitalRadiator()` return `false` (`offroad_02.c:415`, `:420`) | Diesel: needs a glow plug, no radiator. |
| `Truck_01_Base` | Spark plug, glow plug, engine belt and radiator all `false` (`truck_01_base.c:364` to `:382`) | Needs only fuel and a battery. |

So a car that inherits `Offroad_02` and lists a `SparkPlug` slot still needs a glow plug, unless its script class overrides both methods. Every plug or battery slot the car lists must match the `IsVital*` overrides.

The battery comes from `GetElectricitySourceDevice()` and its class name from `GetElectricitySourceDeviceType()` (`offroadhatchback.c:66`, `:73`).

`OnIgnition` picks the failure sound for each flag (`carscript.c:1721`). The sound set names are member strings set in the car's constructor (`m_EngineStartOK`, `m_EngineStartBattery`, `m_EngineStartPlug`, `m_EngineStartFuel`, `m_EngineStop`, `m_EngineStopFuel`, `offroad_02.c:11` to `:16`).

Boats check only ruin, fuel and the spark plug; there is no battery (`EBoatOperationalState`, `P:\scripts\4_world\entities\vehicles\boatscript.c:9`; `CheckOperationalRequirements`, `:262`).

## While the engine runs

`CarScript.EOnPostSimulate` runs a check every `CARS_FLUIDS_TICK` seconds, which is `VEHICLE_FLUIDS_TICK = 1` (`P:\scripts\3_game\constants.c:866`, `:877`; `carscript.c:807` to `:928`):

- Stops the engine when the car is destroyed, fuel is empty, engine health is `0`, or a vital plug is removed.
- Ruins the `Engine` zone when the `FuelTank` zone is ruined and `IsVitalFuelTank()` is true.
- Leaks coolant when the radiator is below half health, fuel when the `FuelTank` zone is damaged, and oil when the `Engine` zone is damaged or below a quarter health (`carscript.c:893` to `:910`).
- Calls `LeakFluid(CarFluid.BRAKE)` when the `Engine` zone is damaged (`carscript.c:904`), but `LeakFluid` only handles `COOLANT`, `OIL` and `FUEL` (`carscript.c:2098` to `:2119`), so the brake call does nothing and vanilla never leaks brake fluid. Override `LeakFluid` if your car should.
- Damages the engine when coolant is below half and `IsVitalRadiator()` is true.

Every vanilla car overrides `EOnPostSimulate` for its engine heat source without calling `super` (`civiliansedan.c:98`, `offroad_02.c:112`). Read your parent's version before overriding it, and test fuel use and leaks in game after any change.
