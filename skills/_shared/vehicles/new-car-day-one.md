# New car, day one

What to measure offline before a new or ported vehicle goes in game for the first time, what each of the three files owns, and the gaps no config review reveals.

> Status: the costs and counts below were measured on mod vehicles (a quad bike, two imported cars, a ported quad), not on vanilla ones. A citation written with its full `P:\` path, and a bare `file.c:N` (the vanilla script of that name under `P:\scripts\`), were opened on the vanilla data on `P:\` (a 1.30 build). "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- The refuel action looks for `FUEL_SELECTION_NAME`, which is `"refill"` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionfillfuel.c:13`), and measures the player against `GetRefillPointPosWS` and `GetActionDistanceFuel` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionfillfuel.c:60-62`).
- `Transport` reads the `refill` memory point in its constructor (`P:\scripts\3_game\vehicles\transport.c:112`) and names the action component in `GetActionCompNameFuel` (`P:\scripts\3_game\vehicles\transport.c:459-461`).

## Run before the first in-game cycle

Across three vehicle builds (a quad bike and two imported cars, about 180 to 220 in-game cycles in
all) the dominant cost was defects of a known class, attacked one per rebuild AFTER the car was
in game. Front-load them on day 1, offline, before any PBO exists. A check applied up front is nearly
free: the spawn-blocker check found on the first car ran before the second car's structural phase
and cost minutes, while the get-in defect that was not written down cost dozens of iterations on
all three:

1. **Parity first**: debinarize `civiliansedan` ONCE and derive the structural gap checklist from it.
   The preflight #1 to #9 items fall out of this diff instead of error by error in game.
2. **Measure, never assume, on the imported model AND on a working control.** Verify the
   origin of the data and every empirical constant, not just API names (one winding investigation ran
   about 15 sessions on an oracle nobody had verified, and a 32768 "ceiling" and an Izz>=300 gate were
   both artifacts): nose=-Z markers in the simulation against the visual (#11), EACH body proxy's anchor
   and content (the #11 trap), the directions of the axis memory points, per-LOD point counts with py3d
   (Blender estimates read about 1.24 times too high), and the imported model's own inventory of authored
   LODs BEFORE building a decimation pipeline (decimation needs the user's approval).
3. **Wrap the day-1 measurements in one preflight script** that takes the car `.p3d` and the proxy
   folder and reports: parse health, simulation against visual orientation, the yaw-180 MIRROR signature
   of wheel proxies, anchor and content of each body proxy, the direction class of the steering axis,
   and LOD point counts. Calibrate it on a broken and a working model: a calibrated run gave three
   FAILs on a car before its fix and none on the vanilla sedan.
   Note from that calibration: the distance from anchor to hub is NOT a discriminator (the correct
   sedan measured 0.20 to 0.22 m, the mirrored car 0.147 m, so the broken car sat closer); the EXACT
   (-X,-Z) mirror signature is.
4. **Write the acceptance spec from the CONSUMER**: list the exact names, frames and values that
   `model.cfg`, `config.cpp` and the engine will read, and assert that each exists in the `.p3d`.
   Producer-side self-consistency passed 58 asserts while the contract with the consumer was broken, and
   offline suites passed while the car could not spawn.
5. **A headless harness with a vanilla control in the same run** (the vanilla sedan, or a working
   quad): the difference from the control does the diagnosis (a bouncing quad logged wheel contact
   `0000` against the control's `1111`, which isolated the bug in one run).
   **The difference is only valid if BOTH cars get the IDENTICAL kit.** Kit the mod car through
   its own `OnDebugSpawn()` (or an explicitly declared superset), never a hand-written partial kit.
   One drive test was spent with the mod car on a hand-written kit (fuel and coolant only, so
   oil and brake fluid were 0) while the control sedan got the full vanilla `OnDebugSpawn`:
   kits that are not equivalent silently poison the comparison and add a confounded state variable to
   every symptom.
6. **Fluids, DamageZones and vitals config from the proven shape** (preflight #8 and #9): copied, never invented.

7. **A reference-frame MARKER pass, before anything is built on top.** Two blind spots compound: a face
   with an empty `texture` renders **WHITE**, and white masks every frame and UV defect underneath it; and
   a mirrored or 180-degree-rotated parametrization is **invisible on any surface without legible
   text**. Together they hid one such defect on an imported car for two months, and it was closed once
   with the wrong diagnosis ("aliasing", measured 172 to 180 texels/m, 4 px per cycle) because no
   surface could show handedness. Inject the markers on the FIRST import and judge them **in the
   engine**, not the viewer and not the modelling tool: the engine defines the convention.
   - **Texture marker**: one image, asymmetric under every symmetry of the square: an `F`, a labelled
     +U arrow, a labelled +V arrow, four distinctly coloured corners, and a grid for scale. Point
     EVERY visual face at it; this is the same single-field pass that repairs an empty `face.texture`,
     so it costs nothing to build once. **Redirect the `hiddenSelectionsTextures` slots too**, or the
     config paints over the marker on the host and you read a false pass. Delivers in one
     look: mirror, rotation, per-island rotation, tiling and scale.
   - **Geometry marker**: a small tri-axis gizmo, three differently SHAPED arms on +X, +Y and +Z, welded at
     the origin. Catches axis permutation and a reflected transform with no textures involved. This is
     the one that flags a frozen `(x, y, -z)` on day 0. Compensating a
     reflection by flipping winding fixes lighting and culling but NOT texture handedness.
   - **Caveat**: the texture marker is USELESS on heavily tiled surfaces. A seat net
     at u in [-14.9, 25.0] repeats about 40 times and shows only fragments of the glyph, which reads as a
     defect and is not one. Measure the per-material UV range first and annotate those surfaces before
     looking.

## The three files and what each owns

| File | Owns | Does NOT own |
|---|---|---|
| `.p3d` | geometry, LODs, named selections, memory points, proxies, **mass + CoM** (Geometry-LOD vertex weights) | physics params, animation values |
| `config.cpp` | the `CarScript` class, drivetrain / engine / suspension, `Crew`, damage, lights, cargo, attachments, sounds, `AnimationSources` | mass, CoM, animation axes |
| `model.cfg` | `CfgSkeletons` (bone hierarchy) + `CfgModels.Animations` (how each bone moves) | physics, which sources are user-driven |

Mass is **not** a config field: it is computed from the vertex weights of the Geometry LOD. `p3d-vehicle-killers.md` covers mass tagged in the wrong LOD, and `vehicle-config-and-modelcfg.md` the config and `model.cfg` blocks.

## Port parity: three gaps no config reveals

A port copies what it sees in the reference `config.cpp`. These three do not live in any config,
so they survive any review that reads configs:

- **The `refill` anchor.** Without a `refill` selection in Memory and in ViewGeometry, the refuel
  action **never appears** (`actionfillfuel.c:13`, `:60-62`; `transport.c:112-115`, `:459-462`).
  Copying the `GetActionDistanceFuel()` override from the reference is not enough: it adjusts the
  distance of an action that, without an anchor, does not exist.
- **Custom `CfgSoundSets`.** Inheriting the base class leaves the vehicle **mute**: zero engine
  sound sets in `soundSetsFilter[]` and none of its own. It emits no error in any log.
- **A `modded class` with no trace in config.** One reference vehicle shipped a modded
  `ActionGetInTransport` (it fixes the turn of more than 180 degrees when mounting from the opposite
  side) and a modded `ModItemRegisterCallbacks` (one-handed wheels). No config mentions them, so they
  only appear when the **script trees** are compared.

The method that found them is the portable part: do not enumerate what to inspect, but **derive the
contract from the running reference** ("every selection family the reference has, the
port has") with a short list of authorized exceptions. One port had 17 gates, 15 of them
green, and failed to spawn; the complementary sweep found 22 gaps in a single pass.
