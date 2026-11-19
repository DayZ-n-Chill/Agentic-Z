# Ripped racing game cars

How to turn a car ripped from a racing game into a drivable `CarScript` vehicle: what a per-car rip folder holds, which parts to include, how to read dimensions and the transform from the locators, and where the car's physics data comes from.

Everything here was measured on cars built from rips, with the vanilla sedan, other test cars and two shipped third-party car mods as references; none of it is vanilla behaviour unless it cites `P:\`. The vanilla sedan model is binarized, so figures read from it came from a converted copy (**model knowledge**). Read with `ripped-car-proxy-split.md` (the route for a car split into proxies), `gta-rip-intake.md` (the other rip source), `rip-geometry-and-winding.md` and `vehicle-structural-parity.md`.

| Step | File |
|---|---|
| Folder, parts, dimensions, transform, physics data | `rip-import.md` |
| Structural LODs, body build, decimation, render crashes, first spawn faults, offline checks | `rip-structural-lods.md` |
| Textures, paint colour, materials by type, glass, interior, one-sided faces | `rip-textures-and-materials.md` |
| Wheels, rims, track width, doors, deploy transplant, interior in first person | `rip-wheels-and-doors.md` |

## What the rip folder holds

The rip comes as a game container with mesh files, swatch textures and a car definition, read in Blender with community import scripts. Run them headless: `blender --background --factory-startup --python <script> -- <args>`. The mesh importer reads one mesh (geometry only with `use_materials=False`, one try per piece); the car importer assembles the whole car by its skeleton but needs the game database for physics and dimensions.

| File | Holds | Use |
|---|---|---|
| `Manifest.xml` | Every part: `<Model path>` grouped by `PartEnum` under `NonUpgradeablePart` or `UpgradeablePart` | Include and exclude list |
| `Locators.xml` | Named locators with a 4 by 4 `SceneTransform` (`_41`, `_42`, `_43` are the x, y, z translation) | Memory points, wheel positions, seats, dimensions |
| `physicsdefinition.bin` | The collision hull only: definition type, `Mass=0.0`, empty inertia, then a point cloud | Not used. A float scan finds no value in the curb weight range; mass is not in this file. |
| The car definition and its debug copy | The active part set | Assembled by the car importer |
| `IKAnchorBones.xml` | Steering and pedal IK | Steering wheel pivot and axis only |
| The build report HTML | A render report | A reference for winding, not a parts list |
| `ManufacturerColors.bin` | Factory paint colours | `rip-textures-and-materials.md` |
| The shared library (not in a one-car archive) | Materials, tyres, wheels | Textures |

Identify the source game from the build report, not from the material library name, which is shared across a game generation.

A media tree may hold several cars. Before packaging, take three to five part names from your include list and require them in the `Manifest.xml` under that exact car's folder; a work folder's name is not proof. Missing names stop the handoff.

## Which parts to include

Each `<Model path="game:\...\X.modelbin" LODs="N">` sits under an element with a `PartEnum`. Resolve `game:\` to your game root and check that each file exists.

- A `__slod` suffix marks a shadow-only part (one LOD). It feeds the shadow LOD, not the visual include list.
- The car definition can name a custom part, such as a custom front bumper, that ships only as its `__slod` shadow. The visible part is then the standard one. Check the visible file exists before using a custom part.
- A widebody rip ships both stock (`body_a`, `fenders_a`) and wide parts (`bodywide_a`, `fenderswide_a`). The wide parts are flares bolted on top of the stock shell, not replacements: include the wide parts and keep `body_a`, which is the central roof and cabin shell. Leaving out `body_a` deletes the roof. A matching LOD count does not prove a replacement; check for z-fighting in the assembled view (`_shared/models/blender-visual-review.md`).
- Exclude the source rim when the vanilla sedan wheel is used; the original rim can follow later (`rip-wheels-and-doors.md`).
- Include the suspension and axles. Leaving them out for a later re-pose that never happens removes the visible parts the wheels sit on; include them posed at ride height.
- Route each source primitive by the part that owns it, keyed by node instance and primitive index (a mesh index alone is not unique with instancing). Every included primitive appears exactly once. Material names a surface, not its owner: a steering wheel decal stays with the steering wheel even when it shares a material with the dashboard, and door fasteners and decals go with the door. Test the router with movable-part primitives that a material-only router would get wrong.

## The right side

A left-hand drive rip ships the driver side and mirrors the passenger side in the game. On disk:

- Missing on the right, so build them by mirroring X and fixing winding on the mirrored faces: doors, door cards, handles, jambs, door speakers, seats, seatbelts, skirts.
- Shipped on both sides: glass, head and tail lights, wing mirrors, brake calipers and rotors.

The car definition names right-side parts that are not on disk, so check each right-side file to sort shipped from mirrored. One car had 14 parts shipped on both sides and 8 to mirror.

## Dimensions from the locators

The wheel locators give the car's geometry, with x lateral, y up and z along the car:

- Wheelbase is `wheelLF.z - wheelLR.z`. On one car 1.286372 - (-1.288897) = 2.575 m, matching the real car's 2575 mm exactly, which confirms the axes were read right. Always compare with the real car; a mismatch means the wrong axis.
- Track is `wheelRF.x - wheelLF.x`, at the wheel centres; a widebody reads wide.
- The tyre contact plane is `wheel.y - wheel_radius`, not the lowest point of the body, which includes the splitter. It sets the new origin so the car sits on the ground.

`IKAnchorBones.xml` holds `SteeringWheelMaxDegrees` (270 on one car) and IK rotations of about ±1.94. Do not copy them: vanilla `maxSteeringAngle` is 30 or 35 (`P:\DZ\vehicles\wheeled\config.cpp:1375` and `:5240`). Use the file only for the steering wheel's pivot and axis.

## The transform

The locators are in source space (Fx, Fy, Fz), and memory points must sit with the deployed geometry, so find the map by matching centroids: take identifiable parts such as headlights and taillights, compute their centroid in the deployed geometry, compare with the matching locator, and solve each axis's sign and offset.

The result on the reference car was `DayZ = (-Fx, Fy + Y0, -Fz)` with `Y0 = (wheel_radius - rip_wheel_center_y) + lift`, here `(0.3587 - 0.19464) + 0.18 = 0.34406`. The `(-x, -z)` part is a 180 degree turn about the vertical, a proper rotation with determinant +1, not a mirror. A DayZ car faces -z with the driver on +x and the source game faces +z, so a correct import flips z (`vehicle-proxies.md`, section "Which way a car faces").

Wheels are named `wheel_<side>_<axle>` as on the sedan: side 1 is +x, axle 1 is the front, so the steered wheels are `wheel_1_1` and `wheel_2_1`. The config `Axles`, the `model.cfg` steering and any checker must agree.

## Drivetrain and mass

Drivetrain, torque, differential, tyre sizes and ride height live in the game database, which the per-car rip usually does not include, and which ships encrypted. Do not guess values out of the binary files: a number from guessed offsets is worse than an honest unchecked value with a real-world target. DayZ mass is not a config key anyway; it is baked from the Geometry LOD's `#Mass#` weights, so the real car's curb weight is only the authoring target.

Get the data, in this order:

1. Public stat sites for the retail game, which list curb weight, drivetrain, power and front weight share per car. For one 2022 coupe two sites agree: rear wheel drive, 2,835 lb (1286 kg), 228 hp, 53% front. Mass and drivetrain do not change between builds of a game.
2. A decrypted database or a CSV of two tables from whoever supplied the rip: `model` (`DrivetrainTypeID` for rear, all or front wheel drive, `EnginePlacementID`, `Name`, `Year`) and `gamecars` (`CurbWeight`, `WeightDistribution`, `SimPeakPower`, `SimPeakTorque`, `NumGears`, `RideHeight`, tyre widths, ratios and `WheelDiameter`), keyed by `carid`. Calibrate power and weight distribution units against one known car first.

Never upload a database from a non-public build to a third-party decryption service: it is a privacy and security problem, and the service may not hold keys for it anyway.
