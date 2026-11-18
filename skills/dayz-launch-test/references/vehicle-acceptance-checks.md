# Vehicle acceptance checks

Which checks take an imported car from "it spawns" to "it drives and turns the right way", where the car must stand for each, which failures end a pass, and which fix in the vehicles pack each failure points to.

Vanilla facts cite the file on `P:\`. The order of checks and the failure signatures were measured in game on test cars and are not checked on `P:\`. How each step is driven (who owns the car, conditioning, gears) is in `vehicle-in-game-facts.md`. Fix files named without a path are in the vehicles pack, `skills/_shared/vehicles/`, which `dayz-vehicle-specialist` reads.

## The checks in order

| Check | How | Pass | Failure points to |
|---|---|---|---|
| Spawns | Create the class at the player's position on clear ground | An entity of the mod's class exists where asked, a few seconds later too | The class does not resolve: the mod is not mounted or `CfgPatches` does not register it (`/dayz-lint` finds the second kind before a boot). Spawns but is invisible, or "action selection not found in geometry": `componentNN` on loose islands. |
| Solid and oriented | Rays at several points (`raycasts-and-collision.md`) and captures from several angles with a camera that leaves the simulation on (`screenshots-and-cameras.md`) | Rays hit where they should; no holes or inverted faces; the right orientation and a plausible scale | Per part winding, the orient transform, scale or the proxy frame (table below) |
| Get-in offered | The checks of `ActionGetInTransport.ActionCondition` for the driver seat's component | The driver seat passes. A car only a passenger can enter cannot be driven by a person. | The first check that fails (table below). Does not block the later checks. |
| The player's own get-in | Aim at the top of the seat from beside its door and run `ActionGetInTransport` on that component, from both sides and for each seat | The cursor offers the action on the seat's component, then the player sits | The cursor on another component, or a door condition point on one side only |
| Conditioned on the server | Seat on the server and run `OnDebugSpawn` there (`vehicle-in-game-facts.md`) | The wheel count equals the car's wheels and the fuel is above 0 | No wheels attached, or an `Axles` override that lists one axle. Blocks the drive checks. |
| Seated as owner | Seat the client as driver | Seated, the client owns the car | Reach, the seat animation or the crew bone. Blocks the drive checks. |
| Drives | Engine on, full throttle for about 12 s on clear ground | Moves more than 1 m, the speedometer above 0, engine on, client is owner. Rolling from gravity does not count. | Near 0 with the engine on: test again on clear ground first, then the wheel simulation or the drivetrain |
| Turns the right way | Full steer one way while driving | The car curves to the commanded side. The sign is not calibrated, so compare against a vanilla car. | The sign of the wheel `angle` in `model.cfg`, or the `wheel_X_Y` naming |

### Which failures end a pass

- No entity ends the pass: there is nothing to test.
- A car not conditioned or not seated ends the pass for the drive checks.
- The geometry checks and the get-in checks do not end the pass. A forced seat (`StartCommand_Vehicle`) skips the get-in action's checks, so a car a person could not get into can still be driven: that pair of signals says the car drives and the get-in fix is still needed.

Collect every failure the reachable checks show, apply the fixes together at the end of the pass, rebuild once and run the checks again, so each boot counts for every change. Give each car an iteration budget (6 passes is a sane default) and a journal per pass: the check reached, the first failing condition, the drive distance, the telemetry read and the mapped fix. A failure outside the table below means stop and understand it, not iterate blindly. The verdict comes from the game; an offline audit (`skills/dayz-p3d-audit/scripts/audit_getin_wheels.py`) only filters before a rebuild, and offline checks have given a false green on two test cars.

### Where the car stands

The get-in checks need the car next to the player, because the last check measures player to door distance. The drive needs a clear track ahead. Spawn the car at the player's position on open ground with at least 150 m clear in every direction it might face; no spawn flag sets a heading (`spawning-and-placement.md`), so choose the site, not the direction.

## What the vanilla get-in checks

`ActionGetInTransport.ActionCondition` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:26`) checks, among others, `CanGetIn()` (`:36`), `CrewCanGetThrough` and `IsAreaAtDoorFreeDiag` for the crew index of the component under the cursor (`:54`), and `CanReachSeatFromDoors` (`:64`). A check that evaluates these for a given component, not the one under the cursor, or that calls `IsAreaAtDoorFree` in place of `IsAreaAtDoorFreeDiag`, is only partial: a test quad passed every forced seat test while its right side offered no get-in for either seat (`dayz-1-30-vehicles.md`, the one sided get-in finding).

- Find the seat component with a View Geometry ray straight down onto the top of the seat. A level ray at seat height hit the rear fender first.
- Aiming the player converged up to about 42 degrees off the body heading; targets at 60 and 76 degrees did not converge. Place the player so the seat lies within about 40 degrees of the current heading, behind left or behind right of a car facing the same way.
- On screen the hold prompt sits under the vehicle's name, in the client's language.

## Failure to fix table

| Symptom | Check | Fix (where to read it) |
|---|---|---|
| The class does not resolve | Spawns | The mod is not mounted (`windows-build-and-mount.md`, absolute mod paths) or `CfgPatches` does not register it. Not a model fault. |
| Spawns but is invisible, or "action selection X not found in view/fire geometry" | Spawns | The `componentNN` double tag: `vehicle-structural-parity.md` and `rip-import.md`. Hubs and seats are islands with no overlap, so each also carries a `componentNN` selection on the same faces. |
| A hole from one angle, solid from the other | Solid | Per part winding, not a global flip (a global flip gave a false green): `rip-import.md`. |
| The car is rotated or mirrored, or a part floats or is turned about 90 degrees | Solid | The body's orient transform, or the proxy frame `R=((-1,0,0),(0,0,1),(0,1,0))`: `proxies-and-detachable-parts.md`. |
| The seat component has no crew index | Get-in offered | `componentNN` on the seats, as for the invisible case. |
| `CrewCanGetThrough` false | Get-in offered | A bare `class X: CarScript` inherits `Transport.CrewCanGetThrough()=false`: `rip-import.md`. Override `CrewCanGetThrough`, `GetSeatAnimationType` and `GetAnimInstance`, and add `worldScriptModule` in `CfgMods`. |
| The door area is not free | Get-in offered | Something blocks the door area, or the door selection is wrong. |
| `CanReachSeatFromDoors` false | Get-in offered | Seat and door geometry, or the car is too far from the player. Move the player next to the car first. |
| The cursor does not offer the get-in while the component checks pass | The player's own get-in | `CanGetIn()` refuses (for example a fallen motorbike, `P:\scripts\4_world\entities\vehicles\motorbikescript.c:225`), or the cursor is on another component. Aim at the top of the seat and compare the components. |
| Get-in works from one side only | The player's own get-in | Likely the door condition points sit on one side: `dayz-1-30-vehicles.md`. |
| The car reads as `CarScript`, not the mod's class, and `CrewCanGetThrough` is false | Get-in offered | The mod's scripts did not load. Compare `Module: World; loaded N files` with a run without the mod; on 1.30 backslashes in `files[]` load nothing (`dayz-1-30-vehicles.md`). |
| The seat is occupied, the hands hold a heavy item, or the player is already in a vehicle | Get-in offered | The test's own state: spawn a clean car, drop the item, or get out first. |
| Wheel count short or fuel 0 after conditioning | Conditioned | `OnDebugSpawn` attaches no wheels, or an `Axles` override lists one axle (`invariants-wheels-and-hubs.md`, "List every axle in an `Axles` override"). For fuel, read again a tick later first. |
| The client is not seated | Seated as owner | Get-in latency, the crew bone or selection, or the seat animation type: `vehicle-config-crew-lights-sounds.md`. The crew proxy needs a selection in the geometry and a bone in `CfgSkeletons`. |
| No distance with an obstacle ruled out | Drives | Wheel simulation (Fire Geometry): `rip-import.md` (each wheel proxy's face also in the visual `wheel_X_Y`, `wheel_X_Y_damper` and, at the front, `wheel_X_1_steering`) and `vehicle-structural-parity.md` (hubs as faces and `componentNN` in the Geometry LOD); or the drivetrain in `config.cpp`. A free camera that stopped the player's simulation also leaves the car inert (`screenshots-and-cameras.md`). |
| Curves opposite to the commanded steer, or the wheels are mirrored | Turns | The sign of the wheel `angle` in `model.cfg` (`vehicle-config-and-modelcfg.md`) and the `wheel_X_Y` naming (`rip-import.md`: the first index is the side, 1 = +x and 2 = -x; the second is the axle, 1 = front). |
