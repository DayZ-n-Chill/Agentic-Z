# DayZ vehicles: cross-project invariants

Covers the seven invariants every DayZ vehicle (car, quad, truck, bike) runs into, which vehicle mod each one was first measured on, and the process lesson behind recording them.

Status: the vanilla script citations in rows 1 and 7 were opened and confirmed on `P:\` on 2026-11-17. The other rows are in-game measurements on three vehicle mods (LFQuad, SUB_BRZ, MercedesAMGLF; their source is not in this repo) and are not yet checked on `P:\`. The working detail lives in the vehicles pack, `skills/_shared/vehicles/`, and in the `dayz-vehicles` skill; this note is the summary and the history.

This summary exists because the cost of not having it was re-deriving crew get-in across dozens of iterations on three vehicles in a row. The numbered checks in the `dayz-vehicles` skill ("Numbered invariants" in its `SKILL.md`) and `skills/_shared/vehicles/vehicle-structural-parity.md` hold the executable detail. Promotion rule: an invariant found on one vehicle is written into the vehicles pack the day it is confirmed.

## The three vehicles (chronological order)

- **LFQuad**: a quad. The first to resolve get-in, wheel simulation and structural parity. Invariants 1, 3 and 6 were first measured on it.
- **SUB_BRZ**: a car imported from another game's model (the `rip-vehicle-import` route). It hit get-in, the `componentNN` dual tag and winding again, and showed that invariant 1 is the same on an imported car, not something specific to the quad.
- **MercedesAMGLF**: a car whose body is built from proxies. It settled the body-proxy frame (invariant 5) and confirmed get-in in game again.

## The invariants (where each was first measured, and where the detail is)

| # | Invariant | First measured on | Detail |
|---|---|---|---|
| 1 | Radial get-in needs a **script class** that `extends CarScript` and overrides `CrewCanGetThrough`. A bare `class X: CarScript` in config inherits `Transport.CrewCanGetThrough`, which returns `false` (`P:\scripts\3_game\vehicles\transport.c:727`), so the action is filtered out and never appears | LFQuad, then again on SUB_BRZ and MercedesAMGLF | `skills/_shared/vehicles/invariants-get-in-and-seats.md`, "Invariant 1" |
| 2 | The script module must **load** (`CfgMods` `files[]` without a backslash, and without a `.p3d` path that yields `*.p3d.p3d`) or the class never binds: a silent failure | SUB_BRZ and MercedesAMGLF | `skills/_shared/vehicles/invariants-get-in-and-seats.md`, "Invariant 2" |
| 3 | The Geometry LOD needs the named property **`class=vehicle`** or the wheels do not simulate (`WheelCountPresent()==0`, no RPT error) | LFQuad, 2026-05-27 | `skills/_shared/vehicles/vehicle-structural-parity.md` |
| 4 | Seats and hubs must carry **`componentNN` (the dual tag)** or they are invisible collision islands: a spawn blocker, or no seat | SUB_BRZ | `skills/_shared/vehicles/invariants-get-in-and-seats.md`, "Invariant 4" |
| 5 | Crew and wheel proxies go in **ViewGeo AND FireGeo**; the proxy triangle is the engine identity frame `R=((-1,0,0),(0,0,1),(0,1,0))` in model space (NOT `rotation=None` from py3d) | MercedesAMGLF (body proxies) | `skills/_shared/vehicles/vehicle-structural-parity.md` and `skills/_shared/vehicles/rip-import.md` |
| 6 | Wheel `angle1` sign: **measure the axis in the `.p3d` BEFORE** setting it (the offline check predicts inverted rotation without going in game) | LFQuad | `skills/_shared/vehicles/build-packaging-and-debug.md`, sections 2-3 |
| 7 | **One vital plug per car**: vanilla makes SparkPlug AND GlowPlug vital by default. A bare `CarScript` requires both: `IsVitalSparkPlug` is tested at `P:\scripts\4_world\entities\vehicles\carscript.c:1776` and `IsVitalGlowPlug` at `P:\scripts\4_world\entities\vehicles\carscript.c:1783`. Petrol cars override `IsVitalGlowPlug` to return false (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:370`); diesel cars override `IsVitalSparkPlug` to return false (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:415`). Declare only the vital one in `attachments[]` and attach it in `OnDebugSpawn`. "Does not start" with a SparkPlug inserted means GlowPlug was not overridden, NOT a removed requirement | SUB_BRZ, 2026-06-28 | `skills/_shared/vehicles/invariants-engine-fluids-and-handling.md`, "Invariant 8", and `skills/_shared/vehicles/vehicle-config-and-modelcfg.md` section 15 |

## Why this note exists (the process lesson)

Knowledge of get-in **was written down** after the first vehicle, but it arrived **late**: the LFQuad result was not promoted to a general invariant when it was confirmed, so each later vehicle re-derived it. The fix was not "more memory" or "more links". It was **promoting the invariant the day it is confirmed** and placing it where the next vehicle reads it **at startup** (the numbered checks), not as triage after a failure.

## 2026-06-29: what a comparison of the three vehicles changed

Comparing what the three vehicles had taught against the written vehicle guidance confirmed that the gap was findability and timing, plus a wrong destination: the first promotions had gone to `dayz-model-pipeline` instead of the vehicle guidance. What changed as a result, all now in the vehicles pack:

- Co-driver get-in: the seat component in ViewGeo is wound inward and carries the point flags of a working vanilla car (`0x0000003F`; see "Crew get-in" in `skills/_shared/vehicles/vehicle-structural-parity.md`). This became one of the up-front checks.
- A method block: parity first, the in-game run is the gate, and the crew probe runs FIRST (`skills/_shared/vehicles/method-and-gate-calibration.md`).
- Network ownership of driver input, including the `OnInput` actuator (`skills/_shared/vehicles/network-physics-ownership.md`).
- `OnDebugSpawn` traps, added to `skills/_shared/vehicles/vehicle-config-and-modelcfg.md` section 15.
- `GetSteering` returning 0 on a dedicated server, recorded in `skills/dayz-animation-pipeline/references/handlebar-and-steering-config.md`.

## Related

- `verified-capabilities.md` — DayZ feasibility verdicts plus Enforce Script and config gotchas.
- The `dayz-vehicles` skill — the destination for every new vehicle invariant.
- `skills/dayz-model-pipeline/references/critical-rules.md` and `skills/_shared/models/proxies.md` — LOD, proxy and named property assembly, where invariants 3 to 5 originate.
