# Vehicle structural parity

How to compare a new or imported car with a working vanilla car before the first in-game test, and what each LOD, selection, memory point and proxy of a drivable car holds.

The reference is the vanilla sedan, `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` (ODOL version 56 on `P:\`). It is binarized and py3d cannot read it, so figures read from it, and from a working third-party quadbike used as a second reference, came from converted copies (**model knowledge**). Facts documented by Bohemia Interactive are marked "per the Bohemia docs". The rest of this topic is split by subject:

| Question | File |
|---|---|
| Geometry LOD, mass, centre of mass, wheel wells, suspension, wheel `.p3d` colliders, spawn launches | `vehicle-geometry-and-mass.md` |
| Proxy paths, body chunk frames, bone selections, `componentNN` tags, axis convention, imported bodies | `vehicle-proxies.md` |
| Seat components, crew proxy triangles, the script class get-in needs, the seat probe | `crew-get-in-geometry.md` |

## Compare first, then build

Building a car from scratch shows its missing structure one in-game error at a time. Convert the sedan once and compare against it before baking:

1. Convert the sedan with an outside ODOL to MLOD converter whose reader handles version 56.
2. List every LOD: resolution, named selections and proxies.
3. Compare with your model read back through py3d, and with your `config.cpp`.
4. Build every missing piece in one pass.

After deploying, judge by the RPT, not by the offline comparison.

## What each LOD holds

The sedan ships 10 LODs: 6 visual plus the special LODs. A car needs at least Geometry and Memory, View Geometry if it has crew, and Fire Geometry if it takes localized damage.

| LOD | Resolution | Holds on a car | Notes |
|---|---|---|---|
| Visual | 0, 1, 4, 8 and so on | Visual mesh, with wheel, crew and door proxies in every visual LOD they should show in | A visual LOD must not hold an empty named selection that an animation or the engine uses; that can crash the game (per the Bohemia docs). |
| Geometry | 1e13 | Closed convex `componentNN`, hubs `wheel_X_Y_damper_land` as their own components, mass per vertex | Total mass and centre of mass come from the vertex weights (`vehicle-geometry-and-mass.md`). |
| Memory | 1e15 | Every memory point (catalogue below) | Lights, entry points and animation control points. |
| LandContact | 2e15 | Nothing on a modern `Car` | The sedan has none. Ground contact comes from the tyre collider and the small `damper_land` component in Geometry; do not add this LOD. |
| Roadway | 3e15 | Surfaces a player can stand on (roof, hood) | Optional. Must not overlap Geometry, or the player wobbles. |
| Hitpoints | 5e15 | One `dmgZone_*` selection per config damage zone | Unconnected named vertices. |
| View Geometry | 6e15 | Crew proxies (`crewdriver`, `crewcodriver`, `crewcargoN`), seat components, occluders | With no component here the cursor cannot open the action menu (`crew-get-in-geometry.md`). |
| Fire Geometry | 7e15 | Damage zone components, wheel proxies identical to the visual ones, crew proxies | Must hold a proxy named after each wheel slot, so the simulation can fit a wheel and suspension there. |
| Shadow Volume | 1e4 or 1.1e4 | Closed, triangulated shadow, slightly smaller than the visual mesh | If it is not smaller, the model looks partly or fully shaded. |

## Memory points of a car

Read from the working quadbike; the wheel pattern is `wheel_<side>_<axle>` with axle 1 at the front, as vanilla names its slots (the truck's front axle holds `Truck_01_Wheel_1_1` and `Truck_01_Wheel_2_1`, `P:\DZ\vehicles\wheeled\config.cpp:18589` and `:18594`). Side 1 is +x, side 2 is -x (`vehicle-proxies.md`).

| Group | Points |
|---|---|
| Crew and seats | `pos_driver`, `pos_codriver`, `pos_cargo`, each with `_dir`; door condition points `seat_con_1_1`, `seat_con_2_1` |
| Wheels, each of four | `wheel_X_Y_axis` (2 points, spin axis), `wheel_X_Y_damper_land` (contact, the config `wheelHub`); on imported models also `wheel_X_Y_damper` with `_damper_axis`, and on the front `wheel_X_1_steering` with `_steering_axis` and `steering_hub_X_1` |
| Steering and dashboard | `steeringwheel`, `drivewheel`, `mph`, `rpm`, `fuel_1`, `dial_temp` (each dial with `_axis`), `light_dashboard` |
| Lights | Beams `light_left`, `light_right` (each with `_dir`), `light_reverse`, `reflector_1_1`, `reflector_2_1` |
| Engine | `engine` with `_axis`, `enginerun`, `engineshake`, `drown_engine` |
| Other | `pos center` (with a space), `ce_center`, `ce_radius`, and the fuel point `refill` |

The sedan has no `wheel_X_Y_damper` or steering axis points in Memory: it uses a `susp_arm_*` linkage with `susp_arm_steering_X_1_axis`. Damper and steering names belong to each car's skeleton, so a check should require only `wheel_X_Y_axis` in Memory and `wheel_X_Y_damper_land` in Geometry.

Two points carry hidden defaults. Without `drown_engine` the engine drowns at the model origin (per the Bohemia docs). The fuel position loads only when `MemoryPointExists("refill")` and `GetActionCompNameFuel()` returns `"refill"` (`P:\scripts\3_game\vehicles\transport.c:112` and `:113`, `:459` to `:461`); a model with `fuelpoint` instead leaves the fuel action at 0,0,0.

## Named selections per LOD

- Visual: wheels `wheel_X_Y`, suspension `wheel_X_Y_damper`, steering `wheel_X_1_steering`, `steeringwheel` and `drivewheel`, doors `doors_*`, seats `seat_*`, lights `light_*`, paint `color`, `base`, `special`, and a catch-all for the rest of the chassis (`zbytek`).
- Geometry: lower case `componentNN`; the quadbike has 27, and 30 to 50 suffice for a sedan or hatchback. Hubs `wheel_X_Y_damper_land` as their own components.
- Hitpoints: one `dmgZone_*` per config zone (`dmgZone_chassis`, `front`, `back`, `fender_*`, `engine`, `fuelTank`, `lights_*`).

## Lights, damage and animation sources

Lights need all three parts, or the headlights fit but never light:

- Visual selections `light_1_1`, `light_1_2`, `light_2_1`, `light_2_2`, `light_brake`, `light_brake_1_2`, `light_brake_2_2`, `light_reverse_1_2`, `light_reverse_2_2`, `light_dashboard`, `light_rear`.
- Memory points `light_left`, `light_left_dir`, `light_right`, `light_right_dir`, `light_reverse`, `reflector_1_1`, `reflector_2_1`.
- Config `hiddenSelections[]` with the light selections at fixed indices, as on the sedan: front 0 and 1, brake 2 and 3, reverse 4 and 5, tail 6 and 7, dashboard 8 (`P:\DZ\vehicles\wheeled\config.cpp:5138` to `:5148`); `hiddenSelectionsMaterials[]` pointing at a lights `.rvmat`; and the switches `frontReflectorMatOn` and `Off`, `brakeReflectorMatOn` and `Off`, `ReverseReflectorMatOn` and `Off`, `TailReflectorMatOn` and `Off`, `dashboardMatOn` and `Off`. A config that puts `color`, `glass` or `interior` at 0 to 2 and the lights after them risks broken lights.

Damage needs `class DamageSystem` with `GlobalHealth` and `DamageZones` in config, and on the model a Fire Geometry component plus `dmgzone_*` selections per zone (`damage.md`). The sedan ships three directional wreck models (`P:\DZ\vehicles\wheeled\civiliansedan\wreck\civiliansedan_wreckedfront.p3d`, `_wreckedback`, `_wreckedboth`), but no vanilla script or vehicle config references them, so there is no vanilla wreck spawn to copy. An empty `healthLevels {}` is valid.

Dampers need user animation sources: `class AnimationSources` with `damper_1_1`, `damper_2_1`, `damper_1_2`, `damper_2_2` as `source="user"` with `initPhase` and `animPeriod`. Without them the RPT reports `unknown animation source damper`. Wheel spin (`source "wheel"`) and steering (`source "direction"`) are driven by the simulation once the `Axles` wheels (`animRotation`, `animTurn`, `wheelHub`) are right and the hubs exist as Geometry faces. The `model.cfg` pattern is in `vehicle-geometry-and-mass.md`; the full config in `vehicle-config-and-modelcfg.md`.

## Auditing a car you received

When you take over a finished car (config, `model.cfg` and `.p3d`) or import one from another game, audit it before planning:

- Parse the MLOD and print each LOD's resolution, point and face counts and named selections. A correct parse ends exactly at the file size, and the resolutions match the values above. A model that looks complete may really be complete; fix only its specific gaps.
- Count the source vertices per mesh (glTF accessor `POSITION` counts or FBX meshes). Splitting into proxies is a matter of grouping meshes under each model's vertex ceiling, judged by binarize (`binarize-vertex-budget.md`), not of decimating. One received car had 166 meshes and 236k vertices: no single mesh over the ceiling, the total seven times over it.
- Check what each inherited selection means to the engine, not only that it exists: the light indices and the fuel point above are the usual traps.

## Checking the checker

A verifier whose expected values are hard-coded only proves the builder agrees with itself. Run its universal checks on the converted sedan and require a pass; if the sedan fails, the check is wrong. Split the checks: universal checks are the engine contract any car meets, and car checks (damage zone list, body proxy names) are policy for one mod. Before closing a step, require:

- a self test where a synthetic good model passes and a broken one fails exactly the expected checks;
- the sedan passing the universal checks;
- the target passing its hard checks;
- a py3d read, save and read round trip that changes nothing.

A result of exactly 0.000 or 100% by construction proves nothing. The checks as applied to an imported car are in `rip-structural-lods.md`.

## Comparing LODs of one model

A decimator keeps surface while changing vertex density, so a raw vertex centroid and principal axes can report a frame change on a correct LOD (about 0.035 m and 18 degrees, measured offline). Compare each LOD with LOD 0 by area-weighted centroid and covariance, orient each principal axis by the area-weighted third moment, and report inconclusive when an axis or its sign is degenerate. Calibrate tolerances on a working pair from the same model; 2 degrees and 0.02 m worked once and are not defaults. Take the list of LOD files from the host's `proxy:` selections, not a hand list.

## Tools

Converting the reference needs an outside ODOL to MLOD converter, which this repo does not ship. Config blocks are in `_shared/enscript/depth/`, `model.cfg` and animation sources in `dayz-animation-pipeline`, damage effects in `/dayz-particles`. `/dayz-p3d-audit` runs the vehicle checks offline.
