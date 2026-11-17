# New car, day one

What to measure offline before a new or ported vehicle goes in game for the first time, what each of the three files owns, and the gaps no config review reveals.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- The refuel action looks for `FUEL_SELECTION_NAME`, which is `"refill"` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionfillfuel.c:13`), and measures the player against `GetRefillPointPosWS` and `GetActionDistanceFuel` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionfillfuel.c:60-62`).
- `Transport` reads the `refill` memory point in its constructor (`P:\scripts\3_game\vehicles\transport.c:112`) and names the action component in `GetActionCompNameFuel` (`P:\scripts\3_game\vehicles\transport.c:459-461`).

## New car, day one: run before the first in-game cycle (retro 2026-07-03)

Retro of LFQuad→SUB_BRZ→MercedesAMGLF (~90-110 session-equivalents, ~180-220 in-game cycles across
the three): the dominant cost was known-CLASS defects attacked one-per-rebuild AFTER the car was
in-game. Front-load them on day 1, offline, before any PBO exists — promoted knowledge applied up
front is nearly free (the SUB_BRZ spawn-blocker check ran before Mercedes Phase 3 and cost minutes;
the un-promoted get-in cost "dozens of iterations" on three cars):

1. **Parity-first** (METHOD #1): debinarize `civiliansedan` ONCE → structural gap checklist.
   Preflight #1-#9 items fall out of this diff instead of error-by-error in-game.
2. **Measure, never assume — on the rip AND on a working control.** Cite-then-verify extends to
   DATA PROVENANCE and empirical constants, not just API names (the BRZ winding saga ran ~15
   sessions on an oracle nobody had verified; the 32768 "ceiling" and the Izz>=300 gate were both
   artifacts): nose=-Z markers sim vs visual (#11), EACH body proxy's anchor + content (#11 trap),
   axis memory-point directions, per-LOD point counts via py3d (Blender estimates read ~x1.24
   optimistic), the rip's own authored-LOD inventory BEFORE building a decimation pipeline
   (decimation is user-gated).
3. **One command wraps the day-1 measurements**: `python <vehicle-import>\tools\import_preflight.py
   --car <p3d> [--proxy-dir <dir>]` — parse-health, sim/visual orientation, wheel-proxy yaw-180
   MIRROR signature, body-proxy anchor+content report, steering-axis direction class, LOD point
   counts; prints the follow-up gate-ladder commands (rungs 1/2/4 stay in their dedicated tools).
   CALIBRATED 2026-07-04: FAILs x3 on the pre-fix Mercedes (B1/B2/B3), 0 FAIL on the vanilla sedan.
   Note from that calibration: anchor→hub PROXIMITY is NOT a discriminator (correct sedan = 0.20-0.22 m,
   mirrored Mercedes = 0.147 m — the broken car sat closer); the EXACT (-X,-Z) mirror signature is.
4. **Acceptance spec from the CONSUMER** (R8-extended): list the exact names/frames/values that
   model.cfg + config.cpp + the engine will read and assert each exists in the `.p3d` — producer-side
   self-consistency passed 58 asserts while the forward contract was broken (LL-025), and offline
   suites passed while the car could not spawn.
5. **Headless harness with a vanilla control in the same run** (sedan/Croco): "the control delta does
   the diagnosis" (LFQuad bounce: wc=0000 vs control wc=1111 isolated the bug in one run).
   **The control delta is only valid if BOTH cars get the IDENTICAL kit flow** — kit the mod car via
   its own `OnDebugSpawn()` (or an explicitly declared superset), never a hand-rolled partial kit.
   MercedesAMGLF s16 spent a user drive-test with the mod car on a hand-written `KitManual`
   (FUEL+COOLANT only → OIL=0/BRAKE=0) while the control sedan got full vanilla `OnDebugSpawn`
   (init.c:145-146, found 2026-07-07 AFTER the cycle was spent): non-equivalent kits silently
   poison the mod-vs-control discriminator and add a confounded state variable to every symptom.
6. **Fluids / DamageZones / vitals config from the proven shape** (preflight #8/#9) — copied, never invented.

7. **Reference-frame MARKER pass, before anything is built on top** (SP-368, added 2026-08-15,
   MercedesAMGLF G1). Two blind spots compound: a face with an empty `texture` renders **WHITE**, and
   white masks every frame/UV defect underneath it; and a mirrored or 180-rotated parametrization is
   **invisible on any surface without legible text**. Together they hid the same defect here from June
   to August, and it was CLOSED ONCE with the wrong diagnosis ("aliasing", measured 172-180 texels/m,
   4 px/cycle) because no one had a surface that could show handedness. Inject the markers on the
   FIRST import and judge them **in the engine** - not the viewer, not the DCC: the engine defines the
   convention.
   - **Texture marker**: one image, asymmetric under every symmetry of the square - an `F`, a labelled
     +U arrow, a labelled +V arrow, four distinctly coloured corners, and a grid for scale. Point
     EVERY visual face at it; this is the same single-field pass that repairs an empty `face.texture`,
     so it costs nothing to build once. **Redirect the `hiddenSelectionsTextures` slots too**, or the
     config stamping paints over the marker on the host and you read a false pass. Delivers in one
     look: mirror, rotation, per-island rotation, tiling and scale.
   - **Geometry marker**: a small tri-axis gizmo, three differently-SHAPED arms on +X/+Y/+Z, welded at
     the origin. Catches axis permutation and a reflected transform with no textures involved. This is
     the one that would have flagged a frozen `(x, y, -z)` on day 0 - and note that compensating a
     reflection by flipping winding fixes lighting and culling but NOT texture handedness.
   - **Caveat that cost a cycle**: the texture marker is USELESS on heavily tiled surfaces. A seat net
     at u in [-14.9, 25.0] repeats ~40x and shows only fragments of the glyph, which reads as a defect
     and is not one. Measure the per-material UV range first and annotate those surfaces before
     looking, or you will chase your own marker.

## The three files and what each owns

| File | Owns | Does NOT own |
|---|---|---|
| `.p3d` | geometry, LODs, named selections, memory points, proxies, **mass + CoM** (Geometry-LOD vertex weights) | physics params, animation values |
| `config.cpp` | the `CarScript` class, drivetrain / engine / suspension, `Crew`, damage, lights, cargo, attachments, sounds, `AnimationSources` | mass, CoM, animation axes |
| `model.cfg` | `CfgSkeletons` (bone hierarchy) + `CfgModels.Animations` (how each bone moves) | physics, which sources are user-driven |

Mass is **not** a config field — it is computed from Geometry-LOD vertex weights. Full detail in the
references.

## Port parity: three gaps no config reveals (added 2026-08-29, LFQuad2)

A port copies what it sees in reference `config.cpp`. These three do not live in any config,
so they survive intact through any review reading configs:

- **The `refill` anchor.** Without a `refill` selection in Memory and in ViewGeometry, the refuel
  action **never appears** (`actionfillfuel.c:13,60-62`; `transport.c:112-115,459-462`).
  Copying the `GetActionDistanceFuel()` override from the reference is not enough: it adjusts the distance of
  an action that, without an anchor, does not exist.
- **Custom `CfgSoundSets`.** Inheriting the base class leaves the vehicle **mute**: zero engine
  soundsets in `soundSetsFilter[]` and none of its own. It emits no error in any log.
- **`modded class` with no trace in config.** The reference had `ActionGetInTransport` (fixes the
  turn of more than 180 degrees when mounting from the opposite side) and `ModItemRegisterCallbacks` (one-handed
  wheels). No config mentions them, so they only appear by comparing **script trees**.

Method that found them, which is the portable part: do not enumerate what to inspect, but **derive the
contract from running reference** --"every selection family reference has, the
port has"-- with a short list of authorized exceptions. Port had 17 gates, 15
green, and failed to spawn; complementary sweep extracted 22 gaps in a single pass.
