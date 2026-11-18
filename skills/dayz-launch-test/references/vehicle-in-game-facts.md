# Vehicles in a scripted test

How a car behaves when a test spawns, seats, conditions, drives and deletes it: which peer owns the drive, how throttle reaches the car, how to give a spawned car wheels and fluids, how to read gears, and the traps of a driving bench. The checks to run, in order, with the fix for each failure, are in `vehicle-acceptance-checks.md`.

Vanilla facts cite the file on `P:\`. The rest was measured in game on DayZ 1.29 and 1.30 with test cars and vanilla cars and is not checked on `P:\`. A scripted test cell that seats a player with `StartCommand_Vehicle` is in `test-cell-vehicles.md`.

## Who owns the drive

Under `FEATURE_NETWORK_RECONCILIATION` the driver's client takes possession of the car when it enters the driver seat: `PlayerBase.OnVehicleSeatDriverEnter` calls `identity.Possess(pawn)` (`P:\scripts\4_world\entities\manbase\playerbase.c:4561` to `:4576`). So the client is the owner and simulates the drive.

- Throttle and steering are applied in `CarScript.OnInput` (`P:\scripts\4_world\entities\vehicles\carscript.c:1041`), which ends with `SetThrottle` and `SetSteering` from the driver's input (`:1202` and `:1203`). A `Car.SetThrottle` call from mission script is overwritten there by the driver's input of 0. To drive a car from a test, apply the values in a `modded class CarScript` override of `OnInput` after `super`, on the owner.
- A get-in that seats the player only on the client leaves the server's crew empty. An action the server checks then fails: `ActionSwitchLights` needs the player at `VEHICLESEAT_DRIVER` on the server (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c:34`), so it kept starting while nothing lit until the player was also seated on the server.
- The client stays bound to the first car it entered. After getting out and into a second car on the server only, the light switch failed there twice. Plan one car per run.
- A server-side seat that times out at 15 s can still have seated the player; with a 30 s timeout it answered in 1.3 s. Read the player's state before you call it a failure.

## Giving a spawned car wheels and fluids

A spawned `CarScript` has no attachments: no wheels, no fluids. A vanilla car's `OnDebugSpawn` attaches the wheels and parts and fills the fluids, for example `Hatchback_02` (`P:\scripts\4_world\entities\vehicles\inheritedcars\hatchback_02.c:393`). Call it on the server; on the client it does nothing under server authority. A car conditioned only on the client reads zero wheels and an empty tank on the server.

- Reading the tank in the same tick as `OnDebugSpawn` can return 0 although it fills the tank; read again a tick later before you call it a failure. Seen in four runs on two machines.
- Parts `OnDebugSpawn` mounts are not separate world objects, so a search at their position finds nothing. To remove a part during a test, mount it yourself, keep its object and delete that; the detach path then runs (the headlights went from the two bulb to the one bulb state).
- No reader of vehicle state shows the lights. Log them from the mod under `#ifdef DIAG_DEVELOPER`, or compare captures.

## A bare spawn shows the undercarriage

With no wheels, only the hub or disc shows, and the brakes (rotor and caliper), suspension and hubs sit bare in the wheel arch as if floating in a gap. That is correct base geometry, not misalignment. A smoke test of a bare spawn checks materials only: paint, textures, winding. Fit the wheels and capture again to judge alignment. When a part "looks displaced", measure before you decide (bounding box, centroid, left and right symmetry, containment in the wheel volume): one scare was bare brakes symmetric within 0.003 m.

## Gears and gearboxes

- The gear index follows the vanilla `CarGear` enum: 0 reverse, 1 neutral, 2 first and so on, up to `TENTH` (`P:\scripts\3_game\vehicles\car.c:32` to `:45`). Sixth gear reads 7.
- `CarScript` treats an automatic and a manual gearbox differently (`GearboxGetType() == CarGearboxType.MANUAL`, `carscript.c:1159`; the getter at `car.c:266`). A test drive that only opens the throttle can leave an automatic car in neutral. To drive one, test a copy whose `Gearbox.type` is `GEARBOX_MANUAL` with every other entry byte identical, and say so in the verdict.
- `ShiftUp()` (`car.c:257`) called on every tick with rpm above 0.8 of the redline skipped gears: first to fourth within 100 ms at about 33 km/h, and no downshift. Leave about 0.3 s between automatic upshifts in a test driver.
- A search by type returns the config class as the type and the script class as the class name. A mod wheel with no script class of its own reads `CarWheel`; its `_Ruined` twin, which has one, reads its own name. That is a cheap check that a mod's script class binds.

## Deleting a car

- Deleting a car with a player in a crew seat brings the game down on the first 1.30 patch: `ObjectDelete` on an occupied car crashed the server, and on the client `CarHud.RefreshVehicleHud` hit a NULL in `EngineGetRPM` (`P:\scripts\5_mission\gui\vehicles\carhud.c:104`). LBmaster's admin tool works around the same bug. Eject every occupant, on every crew position, before you delete; if a seat cannot be emptied, do not delete.
- The server only sees its own crew. A player seated only on the client is not in the server's crew, so the eject finds nobody, the car goes, and the client's `HumanCommandVehicle` points at a deleted car: a native `ACCESS_VIOLATION` on the client. Get the player out on the client first.
- Seven cars in a row in one run, each deleted after a clean eject, worked.

## Health and grenades

No vanilla action sets an item's health, so a health level transition (such as the 1.30 ruined wheel swap) needs damage. An RGD5 dropped unpinned 1.5 m from a loose wheel took it only to 0.971. A grenade unpinned in the hands arms only when it leaves them (`EEItemLocationChanged`, `P:\scripts\4_world\entities\itembase\grenade_base.c:273` to `:281`); drop it to arm it.

## A driving bench

- Use a site with at least 150 m clear in every direction the car might face, checked in the same session with a terrain height read and a search for objects; a View Geometry ray does not see the statics that stop a car. The north-west airfield on Chernarus near `[4200, 0, 10650]` has a flat concrete corridor about 160 m long to the north (measured).
- Measure the drive's distance on clear ground: an obstacle in front gave 0.15 to 0.25 m at full throttle, and the same car 40 m away on clear ground drove 29 m. With the engine revving or the gear shifting up and no distance, suspect an obstacle before the drivetrain.
- Create bench cars with 8389668 (`spawning-and-placement.md`), check that no other vehicle is within 30 m before the first run, check that the seated car is the class you created, and check each recorded trace's car class before you analyse it.
- A seat that keeps failing for every car, on a clean site and after a respawn, needed a fresh client.
- Thresholds on drive telemetry follow `telemetry-thresholds.md`.
