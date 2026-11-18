# New car, day one

What to measure offline before a new or ported vehicle goes in game for the first time, what each of the three model and config files owns, and the gaps a port inherits that no config review shows.

## Measure before the first in-game cycle

Most of the cost of a vehicle build is known kinds of defect found one per rebuild after the car is already in game. Check them offline on day one, before any PBO exists; a check run up front costs minutes, while a missed get-in defect cost dozens of cycles on each of three mod vehicles.

1. Compare against vanilla first. Unpack the `CivilianSedan` once and take the list of structural gaps from the diff (`vehicle-structural-parity.md`). The day one checks fall out of this diff rather than appearing one error at a time in game.
2. Measure on the imported model and on a working control, never assume. Check where data came from and every constant you rely on, not only API names: a 32768 "ceiling" and an `Izz>=300` threshold both turned out to be wrong. Measure the nose direction (minus Z) in the simulation against the visual, each body proxy's anchor and content (`invariants-import-mesh-and-winding.md`), the directions of the axis memory points, the point count per LOD with py3d (Blender's estimate reads about 1.24 times too high), and which LODs the imported model already has before building a decimation pipeline. Decimation needs the owner's approval.
3. Put the day one measurements in one script that takes the car `.p3d` and the proxy folder and reports parse health, simulation against visual orientation, the yaw 180 mirror signature of the wheel proxies, anchor and content of each body proxy, the direction of the steering axis, and LOD point counts. Tune it on a broken model and a working one: one run gave three fails on a car before its fix and none on the vanilla sedan. The distance from anchor to hub does not separate them (0.20 to 0.22 m on the correct sedan, 0.147 m on the mirrored car); the exact `(-X, -Z)` mirror signature does.
4. Write the acceptance list from what reads the model: the exact names, frames and values that `model.cfg`, `config.cpp` and the engine read, and check each exists in the `.p3d`. A model that agreed with itself on 58 checks still broke what the config expected, and offline suites passed on a car that could not spawn.
5. Run a headless test with a vanilla control in the same run, the vanilla sedan or a working quad. The difference from the control does the diagnosis: a bouncing quad logged wheel contact `0000` against the control's `1111`. The comparison holds only if both cars get the same kit. Kit the mod car through its own `OnDebugSpawn()`, never a partial kit written by hand; a mod car with only fuel and coolant against a sedan with the full vanilla `OnDebugSpawn` compares two different states.
6. Copy fluids, damage zones and the vital part config from a working car, never invent them (`invariants-engine-fluids-and-handling.md`).
7. Add reference markers on the first import, before building on top, and judge them in the engine, not a viewer or the modelling tool. A face with an empty texture renders white and hides every frame and UV fault under it, and a mirrored or rotated UV layout is invisible on any surface without readable text; together they hid one such fault on an imported car for months.
   - Texture marker: one image that no flip or rotation of the square leaves unchanged, with an `F`, labelled +U and +V arrows, four differently coloured corners and a grid. Point every visual face at it, and redirect the `hiddenSelectionsTextures` slots too, or the config paints over the marker and you read a false pass. One look shows mirror, rotation, rotation per UV island, tiling and scale.
   - Geometry marker: a small gizmo of three differently shaped arms on +X, +Y and +Z, joined at the origin. It catches swapped axes and a reflected transform, such as a frozen `(x, y, -z)`, with no textures involved. Flipping winding to make up for a reflection fixes lighting and culling but not the handedness of the texture.
   - The texture marker is useless on heavily tiled surfaces: a seat net at u from -14.9 to 25.0 repeats about 40 times and shows only bits of the glyph, which looks like a fault and is not. Measure the UV range per material first and note those surfaces.

## What each file owns

| File | Owns | Does not own |
|---|---|---|
| `.p3d` | Geometry, LODs, named selections, memory points, proxies, mass and centre of mass (vertex weights of the Geometry LOD) | Physics values, animation values |
| `config.cpp` | The `CarScript` class, drivetrain, engine, suspension, `Crew`, damage, lights, cargo, attachments, sounds, `AnimationSources` | Mass, centre of mass, animation axes |
| `model.cfg` | `CfgSkeletons` (the bone tree) and `CfgModels` `Animations` (how each bone moves) | Physics, which sources script drives |

Mass is not a config key; it comes from the vertex weights of the Geometry LOD. Mass in the wrong LOD is in `p3d-vehicle-killers.md`; the config and `model.cfg` blocks are in `vehicle-config-and-modelcfg.md`.

## Three gaps a port inherits

A port copies what it sees in the reference `config.cpp`. These three are not in any config, so a config review misses them:

- The `refill` memory point. The refuel action compares each action component name with `GetActionCompNameFuel()`, which returns `"refill"`, and measures the player against `GetRefillPointPosWS()` and `GetActionDistanceFuel()` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionfillfuel.c:58` to `:62`; `P:\scripts\3_game\vehicles\transport.c:462` to `:475`). `Transport` reads the `refill` point in its constructor and falls back to `"0 0 0"` (`transport.c:112` to `:115`). Without a `refill` selection in the Memory and View Geometry LODs the refuel action never appears, and copying the `GetActionDistanceFuel()` override does not help.
- Custom `CfgSoundSets`. Inheriting the base class leaves the vehicle silent, with no engine sound sets in `soundSetsFilter[]` and none of its own, and no error in any log.
- A `modded class` with no trace in config. One reference vehicle shipped a modded `ActionGetInTransport` (it fixes a turn of more than 180 degrees when mounting from the far side) and a modded `ModItemRegisterCallbacks` (one-handed wheels). They show only when the script folders are compared.

Derive the list of what to check from the running reference, with a short list of allowed exceptions: every selection family the reference has, the port has. One port passed 15 of its 17 checks and still failed to spawn; comparing it family by family against the reference found 22 gaps in one pass.
