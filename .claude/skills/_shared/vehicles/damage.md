# Vehicle damage

How a vehicle's `DamageSystem` is laid out, which zone names script depends on, and how crashes hurt the vehicle and the people inside.

## Layout

Reference: `OffroadHatchback` (`P:\DZ\vehicles\wheeled\config.cpp:1540` to `:2282`).

- `class GlobalHealth` then `class Health`: `hitpoints` (`1000` on `OffroadHatchback`) and `healthLevels[]` with five steps at `1`, `0.7`, `0.5`, `0.3` and `0`, each with the materials to show at that step (`:1544`).
- `class DamageZones`: one class per zone. Keys used by vanilla (`Front`, `:1594` to `:1669`):

| Key | Meaning |
|---|---|
| `displayName` | Name shown to players. |
| `fatalInjuryCoef` | `-1` on car zones. |
| `componentNames[]` | Components in the model's fire geometry that belong to the zone (`"dmgZone_front"`). |
| `memoryPoints[]` | Memory points for the zone. |
| `class Health` | `hitpoints`, `transferToGlobalCoef`, optional `healthLevels[]` with per zone materials. |
| `transferToZonesNames[]`, `transferToZonesCoefs[]` | Share of damage passed to other zones (`Front` passes to both front fenders and `Engine`, `:1654` to `:1660`). |
| `inventorySlots[]`, `inventorySlotsCoefs[]` | Share of damage passed to attached parts (`Front` damages the hood, radiator and front wheels). |

`OffroadHatchback` zones: `Chassis`, `Front`, `Reflector_1_1`, `Reflector_2_1`, `Back`, `Roof`, `Fender_1_1`, `Fender_2_1`, `Fender_1_2`, `Fender_2_2`, `WindowFront`, `WindowLR`, `WindowRR`, `Engine`, `FuelTank` (`:1579` to `:2237`). The `Engine` zone has `transferToGlobalCoef=1` and passes damage to `CarBattery` and `SparkPlug` (`:2170` to `:2236`).

Paint and damage textures are swapped through `hiddenSelections[]` named after the zones (`dmgZone_chassis`, `dmgZone_front`, `:1283` to `:1290`).

Doors carry their own `DamageSystem` with `Window` and `Doors` zones (`HatchbackDoors_Driver`, `:924`).

The boat uses `Chassis`, `Engine`, `LeftFloat`, `RightFloat` and `FrontFloat` (`P:\DZ\vehicles\water\config.cpp:218` to `:494`).

## Zone names script depends on

Keep these names exactly; script reads them by string.

| Zone | Read by |
|---|---|
| `Engine` | `CheckOperationalRequirements` (a ruined engine will not start, `P:\scripts\4_world\entities\vehicles\carscript.c:1758`); `PartsHealthCheck` (`:2134`); overrev, coolant and drowning damage (`:878`, `:921`, `:1240`); destroyed effect (`EEHealthLevelChanged`, `:2401`); `Transport.EEHitBy` flags an engine hit (`P:\scripts\3_game\vehicles\transport.c:148`). |
| `FuelTank` | `PartsHealthCheck` (`carscript.c:2137`); a ruined tank ruins the engine (`:863`) and a damaged one leaks fuel. |
| `Reflector_1_1`, `Reflector_2_1` | Health copied from the attached headlight bulb (`EEItemAttached`, `carscript.c:488` to `:495`). |
| `WindowLR`, `WindowRR`, `WindowFront`, `WindowBack`, `WindowFrontLeft`, `WindowFrontRight` | Breaking glass sounds (`carscript.c:2381` to `:2394`). |

A car with a `Motor` zone instead of `Engine` would never lose engine health to overrevving or low coolant, and a ruined engine would not stop it starting.

## Damage while driving

- Overrev: at or above `EngineGetRPMRedline()` the engine zone takes damage every tick; above `EngineGetRPMMax()` it also loses 5 percent of its maximum health (`carscript.c:875` to `:882`). The redline is `rpmRedline` in the `Engine` simulation class.
- Low coolant: see `fluids-and-engine.md`.
- Drowning: when the `drown_engine` memory point is under water for more than `DROWN_ENGINE_THRESHOLD = 0.5` seconds, the engine loses `DROWN_ENGINE_DAMAGE = 350.0` health per second (`carscript.c:102`, `:103`, `:368`, `:1234` to `:1242`).

## Crash damage

`Transport.OnContact` collects contacts per zone (`transport.c:315`) and `CarScript.CheckContactCache` applies them on the server (`carscript.c:1279`):

- Zone damage is the contact impulse times `m_dmgContactCoef`, `0.023` by default (`transport.c:91`). Vanilla cars leave it at the default; a commented line in each constructor shows a tuned value (`offroad_02.c:9`).
- Below `CARS_CONTACT_DMG_MIN = 150` nothing happens; below `CARS_CONTACT_DMG_THRESHOLD = 750` the hit is light and does not transfer to other zones; above it the crew is hurt too (`P:\scripts\3_game\constants.c:888`, `:889`; `carscript.c:1329` to `:1355`).
- Crew damage is worked out as if the car weighed 1000 kg, so heavy and light cars hurt their crew the same (`carscript.c:1292`). Above `CARS_CONTACT_DMG_KILLCREW = 1200` everyone inside dies; below it each crew member loses 2 to 100 health and 50 to 150 shock (`DamageCrew`, `carscript.c:1374`; `constants.c:890`).

Test crash damage in game; P:\ gives the formula but not the impulse a given collision produces.
