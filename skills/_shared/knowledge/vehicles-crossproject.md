# DayZ vehicles: cross-project invariants

Covers the seven invariants every DayZ vehicle (car, quad, truck, bike) runs into, which project earned each one, and the process lesson behind recording them.

Status: a durable record from the author's vehicle projects (LFQuad, SUB_BRZ, MercedesAMGLF), translated into English. The vanilla script citations in rows 1 and 7 were opened and confirmed on `P:\` on 2026-11-17 (the source note gave them as bare file names). The other rows are in-game measurements from those projects and are not yet checked on `P:\`. The working detail lives in the vehicles pack, `skills/_shared/vehicles/`, and in the `dayz-vehicles` skill; this note is the summary and the history.

> Domain hub: the invariants that **every** DayZ vehicle (car/quad/truck/bike) will
> encounter, along with which project earned each one. It exists because the actual cost of NOT having this
> was re-deriving crew get-in across dozens of iterations in three projects in a row.
>
> Executable detail lives in the `dayz-vehicles` skill (the "invariants you will hit" checklist at the
> start of its `SKILL.md`) and in `skills/_shared/vehicles/vehicle-structural-parity.md`. This note is the
> cross-project durable record. Promotion rule: promote an invariant across projects the day it is won
> (the author's "evidence-led memory" rule, section "Cross-project promotion").

## Vehicle projects (chronological order)

- **LFQuad** — quad (Banshee + Croco physics). **First** to resolve
  get-in, wheel simulation and structural parity. The source of invariants 1, 3, 4.
- **SUB_BRZ** (rip-to-DayZ pipeline; it lives in the author's vehicle import folder and the
  `rip-vehicle-import` pipeline notes) — suffered get-in, the `componentNN` dual tag and winding again. Proved that invariant 1
  is the SAME in an imported car, not something specific to the quad.
- **MercedesAMGLF** — Mercedes-AMG GT3 via proxies. Closed the
  engine body-proxies convention (invariant 5) and confirmed get-in in game again.

## The invariants (which project earned it · where the detail is)

| # | Invariant | Earned in | Detail |
|---|---|---|---|
| 1 | Radial get-in needs a **script class** that `extends CarScript` and overrides `CrewCanGetThrough`. A bare `class X: CarScript` in config inherits `Transport.CrewCanGetThrough`, which returns `false` (`P:\scripts\3_game\vehicles\transport.c:727`), so the action is filtered out and never appears | LFQuad D34, then suffered again in SUB_BRZ and Mercedes | `skills/_shared/vehicles/vehicle-structural-parity.md`, "Crew get-in" |
| 2 | The script module must **load** (`CfgMods` `files[]` without a backslash, and without a `.p3d` path that yields `*.p3d.p3d`) or the class never binds: a silent failure | SUB_BRZ / Mercedes | `dayz-vehicles` skill, "Script binding" |
| 3 | The Geometry LOD needs the named property **`class=vehicle`** or the wheels do not simulate (`WheelCountPresent()==0`, no RPT error) | LFQuad 2026-05-27 (SP-027) | `skills/_shared/vehicles/vehicle-structural-parity.md` |
| 4 | Seats and hubs must carry **`componentNN` (the dual tag)** or they are invisible collision islands: a spawn blocker, or no seat | SUB_BRZ session 7 | "componentNN dual tag" |
| 5 | Crew and wheel proxies go in **ViewGeo AND FireGeo**; the proxy triangle is the engine identity frame `R=((-1,0,0),(0,0,1),(0,1,0))` in model space (NOT `rotation=None` from py3d) | Mercedes (body proxies) | structural parity, and `rip-import.md` in the `rip-vehicle-import` skill |
| 6 | Wheel `angle1` sign: **measure the axis in the `.p3d` BEFORE** setting it (the offline check predicts inverted rotation without going in game) | LFQuad shipping | `skills/_shared/vehicles/build-packaging-and-debug.md`, sections 2-3 |
| 7 | **One vital plug per car**: vanilla makes SparkPlug AND GlowPlug vital by default. A bare `CarScript` requires both: `IsVitalSparkPlug` is tested at `P:\scripts\4_world\entities\vehicles\carscript.c:1776` and `IsVitalGlowPlug` at `P:\scripts\4_world\entities\vehicles\carscript.c:1783`. Petrol cars override `IsVitalGlowPlug` to return false (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:370`); diesel cars override `IsVitalSparkPlug` to return false (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:415`). Declare only the vital one in `attachments[]` and attach it in `OnDebugSpawn`. "Does not start" with a SparkPlug inserted means GlowPlug was not overridden, NOT a removed requirement | SUB_BRZ 2026-06-28 | `dayz-vehicles` skill invariant 8, and `skills/_shared/vehicles/vehicle-config-and-modelcfg.md` section 15 |

## Why this note exists (the process lesson)

Knowledge of get-in **was captured** in the skill (SP-007 pose, SP-017 wheelPresent), but it
arrived **late**: the LFQuad win was not promoted to a domain invariant when it was won, so each
later project re-derived it. The fix was not "more memory" or "more links". It was **promoting the
invariant the day it is won** and placing it where the next project reads it **at startup** (the preflight
checklist), not as triage after a failure. The rule is the author's "evidence-led memory" rule, section
"Cross-project promotion"; patches waiting for read-only skills sat in the author's pending patch queue.

## 2026-06-29: skills audit against LFQuad, Mercedes and Subaru (consolidation)

Comparison of the knowledge from three cars against the skills. Confirmed: this was not a capture failure but a findability and timing problem, plus a wrong destination (the May promotions went to `dayz-model-pipeline` and were later retired). Actions applied to the `dayz-vehicles` `SKILL.md`: co-driver ViewGeo inward plus flags `0x02000000` became **preflight #4**; a **METHOD** block (parity first, in game is the gate, crew probe FIRST); ownership completed with the `OnInput` actuator; LL-103, LL-104, `OnDebugSpawn` and the fitting editor added to `vehicle-config-and-modelcfg.md`. In the author's notes: LL-166 and LL-175 written; the pending patch queue reconciled (SP-032 and SP-036 applied; SP-041 closed with no issue; SP-040(b) `GetSteering` applied to the `dayz-animation-pipeline` skill). Reaffirmed: **`dayz-vehicles` is an editable skill, NOT a read-only plugin**; SP-032 and SP-036 had been wrongly parked as "read-only plugin". Detail: the author's session notes of 2026-06-29 (not in this repo).

## Related

- `verified-capabilities.md` — DayZ feasibility verdicts plus Enforce Script and config gotchas.
- The `dayz-vehicles` skill — the destination for every new vehicle invariant.
- The model pipeline note (merged by the models workstream) — LOD, proxy and named property assembly, where invariants 3 to 5 originate.
- The author's "evidence-led memory" rule, section "Cross-project promotion" — the process rule this note embodies (not in this repo).
- The author's pending patch queue — patches for read-only skills (SP-017 and SP-027 are vehicle related; not in this repo).
- The author's lessons learned from the LFQuad, SUB_BRZ and Mercedes projects cited above (not in this repo).
- MercedesAMGLF — the project that closed invariant 5 (body proxies).
