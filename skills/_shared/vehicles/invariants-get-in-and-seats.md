# Get-in, seats, doors and crew: invariants

Why a get-in, seat or door action does not appear on a new or imported car, and the model, config and script contract that makes it appear.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

Related file in this pack: `get-in-actions-and-proxy-pose.md` (the get-in condition chain link by link, and which anchor places the occupant).

## Vanilla anchors checked on `P:\`

- `CrewCanGetThrough` returns `false` in `Transport` (`P:\scripts\3_game\vehicles\transport.c:724`), so a car with no script class of its own can never be entered.
- The get-in action checks `CanGetIn` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:36`), then `CrewCanGetThrough` and `IsAreaAtDoorFreeDiag` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:54`), then `CanReachSeatFromDoors` with a distance of `1.0` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:64`).
- `CrewPositionIndex` maps a hit component to a crew seat (`P:\scripts\3_game\vehicles\transport.c:179`).
- The base `GetDoorConditionPointFromSelection` pairs `seat_driver` with `seat_con_1_1`, `seat_codriver` with `seat_con_2_1`, `seat_cargo1` with `seat_con_1_2` and `seat_cargo2` with `seat_con_2_2` (`P:\scripts\4_world\entities\vehicles\carscript.c:2141`). Vanilla overrides `GetDoorConditionPointFromSelection` for `OffroadHatchback` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:364`) and `Van_01` (`P:\scripts\4_world\entities\vehicles\inheritedcars\van_01.c:269`).
- `Sedan_02` keeps `CarBattery` and `SparkPlug` behind `Sedan_02_Trunk` (`P:\scripts\4_world\entities\vehicles\inheritedcars\sedan_02.c:142`) and `CarRadiator` behind `Sedan_02_Hood` (`P:\scripts\4_world\entities\vehicles\inheritedcars\sedan_02.c:156`), and its `CanDisplayCargo` tests the hood (`P:\scripts\4_world\entities\vehicles\inheritedcars\sedan_02.c:203`).
- `CivilianSedan` overrides `GetSeatAnimationType` for four seats (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:119`) and `CrewCanGetThrough`, comparing each door against `DOORS_CLOSED` (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:226`).
- The outside door action casts its target to `CarDoor` and reads `GetActionComponentNameList` from that door item (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoorsoutside.c:34`), then asks the car for `GetAnimSourceFromSelection` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoorsoutside.c:43`).
- `CivilianSedan` declares `Cargo1` and `Cargo2` crew seats with `proxyPos` `crewCargo1` and `crewCargo2` (`P:\DZ\vehicles\wheeled\config.cpp:5221-5234`). The only crew proxy models vanilla ships are `P:\DZ\vehicles\wheeled\proxies\crew_cargo.p3d` and `P:\DZ\vehicles\wheeled\proxies\crew_driver.p3d`.
- `CivSedanDoors_BackLeft` declares no `rotationFlags` of its own (`P:\DZ\vehicles\wheeled\config.cpp:4938-4947`) and inherits `rotationFlags=8` from `CivSedanDoors_Driver` (`P:\DZ\vehicles\wheeled\config.cpp:4813`).

## Before copying a donor: check where the engine is (SP-205)

**BEFORE copying a donor — verify WHERE the engine is, not how many seats it has (SP-205, origin 2026-08-08, SUB_WRXSTI T8).**
`sedan_02.c` looks like the vanilla 4-seat sedan control and is **rear-engine**: it closes `CarBattery`
and `SparkPlug` behind the **trunk** and the `CarRadiator` behind the **hood**
(`scripts\4_world\entities\vehicles\inheritedcars\sedan_02.c:142-160`), and gates `CanDisplayCargo`
on the hood (`sedan_02.c:203`). Porting that to a front-engine car leaves the engine parts behind
the wrong lid — a bug that only shows in-game. The correct control for front-engine + 4 seats is
**`civiliansedan.c`**. Rule: before copying a donor, verify WHERE the engine lives, not only how
many seats it has. Rear seat on that 4-seater (measured vs `civiliansedan_mlod.p3d`; in-game
confirmation pending WRX live test #1): Memory `pos_cargo1(_dir)`, `pos_cargo2(_dir)`,
`seat_con_1_2`, `seat_con_2_2`; `GetSeatAnimationType` cases 2/3 → `VEHICLESEAT_PASSENGER_L` /
`VEHICLESEAT_PASSENGER_R` and **`CrewCanGetThrough` cases 2/3** (`civiliansedan.c:119-131`,
`:226-256`) — the base returns `false` (`transport.c:724-727`). Distinct `crew_cargo` proxy index
and seat-box lead: invariants 28 and 30.

## Four-seat completion (SP-205 rider)

**Four-seat completion rider (SP-205, added 2026-08-31).** Rear seats also need
`seat_cargo1/2` boxes dual-tagged to their exact `componentNN` in Geometry and
ViewGeometry; `crewcargo1/2` proxies in ViewGeometry and FireGeometry using one
`crew_cargo` path with distinct instance indexes; `Crew.Cargo1/2` entries with
`actionSel`, `proxyPos`, `getInPos`, and `getInDir`; and the two passenger cases
in both `GetSeatAnimationType` and `CrewCanGetThrough`. `CarScript` already maps
all four `seat_*` selections to `seat_con_1_1`, `seat_con_2_1`,
`seat_con_1_2`, and `seat_con_2_2` (`carscript.c:2141-2156`), so an override of
`GetDoorConditionPointFromSelection` that only repeats that table is dead code.

## The base door condition table is the left-hand-drive mapping (SP-426)

**That base table is the LEFT-HAND-DRIVE mapping (SP-426, added 2026-10-01, WRX STI B-01).**
[EXACT][CLAIM-GETIN-LHD-BASE-TABLE] On a right-hand-drive car whose memory points are named by
physical side (driver door = `seat_con_2_1`), the base table pairs every seat with the FAR door:
each seat is evaluated against the opposite door and `CanReachSeatFromDoors` fails the 1.0 m
plan-distance test from the correct one, so no get-in appears with names, points and `componentNN`
all correct. Signature in `query_get_in_condition`: `unreachable` from the correct door and
`available` from the opposite one. Override it crossing the sides (driver->`seat_con_2_1`,
codriver->`seat_con_1_1`, cargo1->`seat_con_2_2`, cargo2->`seat_con_1_2`), as vanilla does for its
own layouts (`OffroadHatchback.c:364-379`, `Van_01.c:269-287`, DayZ 1.30.164014 Exp). On RHD cross
`GetSeatAnimationType` for the rear seats too (vanilla pairs L with the physical left side,
`CivilianSedan.c:119-134`); the driver keeps `VEHICLESEAT_DRIVER`, whose get-in animation will look
LHD-sided - an engine limit, not a mod bug.

## Invariant 1: the get-in radial needs a real script class

**"Get in" radial needs a real SCRIPT CLASS, not a bare config class.** A `class <Mod>: CarScript`
with no `.c` runs as bare `CarScript`, which inherits `Transport.CrewCanGetThrough()` → **`false`**
(`P:\scripts\3_game\vehicles\transport.c:724`) → the get-in action is filtered out and **never appears,
no bone/proxy/componentNN fix helps**. Author `<Mod>_Base extends CarScript` overriding
`CrewCanGetThrough` + `GetAnimInstance` + `GetSeatAnimationType` (+ `CfgMods` worldScriptModule).
Verified in-game LFQuad D34 + MercedesAMGLF + SUB_BRZ. → `vehicle-structural-parity.md` "Crew get-in".

## Invariant 2: the script module must load or the class never binds

**The script module must actually LOAD or the class never binds — silent.** `CfgMods` `files[]` with
back-slashes / a `.p3d` path that resolves to `*.p3d.p3d` → module not loaded → no get-in, no error.
→ the script binding notes in `rip-import.md`.

## Invariant 3: wheels not present (moved)

For a new car ripped from a source game and split into proxies (family B), this item now lives in the rip-vehicle-import skill, in its family B cookbook `cookbook-wheelpresent-0.md`.

## Invariant 4: seats and wheel hubs need the componentNN dual tag, and each seat must be hit by the view raycast

**Seats and wheel hubs must be `componentNN`-tagged (dual-tag) — AND each seat component must be raycast-collidable.** The engine enumerates collision
components only by `componentNN`; a seat/hub that is a standalone island (0% componentNN overlap) is
invisible → spawn blocker / no seat. Tag the SAME faces with a `componentNN` too. **Then the ViewGeo seat cube
must be INWARD-wound with every point flag = `0x0000003F`:** a py3d box left outward + flags 0 passes every
offline shape/winding/dual-tag check yet `RaycastRV(ObjIntersectView)` does NOT hit it → the get-in cursor
falls through to component0 → the driver "works" by fallback but the CODRIVER never resolves. The decisive,
in-game-confirmed copilot blocker on BOTH SUB_BRZ (s9) and MercedesAMGLF (s12, headless `hit=1 comp=6 crewIdx=1`). The s9 patch changed winding and flags together and never isolated the flag as cause; the safe rule is to copy the convention of the sealed vanilla control or of a positive control (LFQuad, Croco), never py3d's default. → "componentNN DUAL-TAG" + "CRITICAL EXTENSION 2026-06-28" (`vehicle-structural-parity.md`).
**Resolve the seat's `componentNN`; never hardcode its number (SP-079, added
2026-08-31).** Assembly order moves component numbers. For every `seat_*`
selection, compare both point and face membership against each `componentNN` in
the same LOD and require exactly one exact 1:1 match. Zero or multiple matches is
a hard failure. Re-run the equality after any transform or transfer so the
seat/component dual tag cannot be lost silently.

## Invariant 5: crew and wheel proxies in both View Geometry and Fire Geometry

**Crew/wheel proxies must exist in BOTH ViewGeometry AND FireGeometry**; the proxy triangle uses the
engine identity frame (`R=((-1,0,0),(0,0,1),(0,1,0))`, model-space), NOT py3d `rotation=None`. → parity + rip-import.

## Invariant 20: the config inherits a vanilla car but the script class does not (SP-059)

**Config inherits a vanilla car but your SCRIPT class does not extend that car's script = SWEEP every parent script override (SP-059).** If the config says `class X: OffroadHatchback` while the script is `class X extends MyBase` (with `MyBase extends CarScript`), the config->script binding does NOT drag in the parent car's script overrides - those live on the vanilla `inheritedcars\<parent>.c`, which your class never inherits. Every method with a hostile default in the base that ALL vanilla cars override then bites: `CrewCanGetThrough` (false in `Transport`, `P:\scripts\3_game\vehicles\transport.c:724` -> get-in impossible; see #1), `IsVitalGlowPlug` (true in `CarScript` -> engine won't start; see #8), `GetAnimInstance` / `GetSeatAnimationType` (`Error()` in `Transport`, `transport.c:665,685`), `Get3rdPersonCameraType` (`Error()`, `transport.c:701`). Procedure: diff method-by-method against the parent config's `.c` (`4_world\entities\vehicles\inheritedcars\<parent>.c`) and replicate EVERY runtime-contract override, not just the two pose ones - this is DZ-R7 (sweep the invariant to all call-sites) in config form. Origin: LFHeli R21-008 - `LFHeli_Placeholder: OffroadHatchback` (config) + `extends LFHeli_Base` (script) had no get-in and no engine start after passing two reviews; the first fix restored only the two pose methods.

## Invariant 20b: a working control's skeleton is baked into its ODOL (SP-145)

**A working control's skeleton is baked into its ODOL; inherited config must be
audited by EFFECTIVE value (SP-145, added 2026-08-31).** Shipped controls often
have no loose `model.cfg`. Read the baked skeleton and selection names through
an external ODOL→MLOD converter (not distributed with this pack), and validate
the reader first on a model whose `model.cfg` is available: name, `isDiscrete`,
bone count and every bone/parent pair must match. Binarized bone names are
lower-case. A uniform zero from both control and candidate is a tool-failure
signal; confirm known bytes directly before drawing a conclusion.
For a vehicle that inherits from the working vanilla control, an undeclared
property has the parent's effective value and cannot be a differential by
itself. Keep only differences where both independent controls agree and the
candidate differs, then inspect: candidate-only declarations; model-bound
skeleton/animation/selection data; and values both controls override but the
candidate neither declares nor inherits. Finally resolve every inherited model
name (`animDamper`, `wheelHub`, and peers) against the candidate `.p3d`; the
reference is inherited even when the named bone or selection is absent.

## Invariant 21: attached part is invisible (moved)

For family B this item now lives in the rip-vehicle-import skill, in its family B cookbook `cookbook-attachment-invisible.md`.

## Invariant 22: an attached part with its own actions needs a raycast-visible View Geometry

**An attached item with its OWN radial actions (CarDoor open/close, hood, trunk) needs a raycast-visible ViewGeometry — point flags 0x0000003F — or the action NEVER appears (SUB_BRZ s38).** The action chain resolves the TARGET by raycast: `ActionCarDoorsOutside.ActionCondition` casts `target.GetObject()` to CarDoor and reads the selections of the hit VG COMPONENT of the ITEM (`actioncardoorsoutside.c:34-46`); a VG whose points carry flags 0x0 is not hit by `RaycastRV(ObjIntersectView)` — the same mechanism as the seat-cube blocker (preflight #4, in-game verified SUB_BRZ s9 + MercedesAMGLF s12) — so the item under the cursor never resolves and the radial is silently filtered, with config, script overrides, slots, bones and anim sources all CORRECT. Contract for the item's VG: (a) componentNN dual-tagged with a selection named EXACTLY what the vehicle's `GetAnimSourceFromSelection` expects (e.g. `doors_driver`); (b) every VG point flags 0x0000003F; (c) inward winding (copy a fixed seat cube as control). Symptom signature: attachment renders/attaches/damages fine, `GetCarDoorsState` works, but no open/close radial (and hence no get-in-through-door). Diagnose offline in seconds: census the item's VG point flags vs a working control BEFORE touching config or scripts. Origin: SUB_BRZ s38 D4e; the door fix's own in-game gate CLOSED 2026-08-24 (the radial action DOES appear on the attached panel), but the raycast mechanism is the twice-verified #4 one.

## Invariant 23: the componentNN dual tag fixes seat and wheel selection failures; LOD order is hygiene

**`componentNN` dual-tag is the confirmed fix for simultaneous seat/wheel selection failures; ascending LOD order is match-vanilla practice, not a proven cause (LFHeli OH-1 v2, 2026-07-17).** Sorted-without-dual-tag still failed; sorted-plus-dual-tag spawned; dual-tag-without-sort was never isolated. Therefore a py3d/hand-assembled model with `seat_* not found` / `wheel ... no proper selection` must be checked for collision-selection dual-tag first. `model.lods.sort(key=resolution)` may remain as deterministic authoring hygiene, but no gate may report that sorting fixed the defect. `binarize` accepts either order silently.

> History of the superseded text: `history/superseded-family-b-rules.md`, section "Invariant 23".

## Invariant 28: one crew_cargo model, numbered by its instance index

**A 4-seat car numbers ONE `crew_cargo` model 1/2/3 — the index is the instance suffix, and two rear seats both at index 1 collide (added 2026-08-16, SUB_WRXSTI T8.2).** There is no `crew_cargo1.p3d`: `P:\DZ\vehicles\wheeled\proxies\` ships exactly `crew_cargo.p3d` + `crew_driver.p3d`, and the seat identity comes from the INDEX. The mapping the consumer actually applies is `bone = "crewcodriver" if index == 1 else "crewcargo%d" % (index - 1)`, so `crew_cargo.001→crewcodriver`, `.002→crewcargo1`, `.003→crewcargo2` (`<vehicle-import>\tools\verify_forza_car.py:983-986`; corroborated by the sealed AC02 control inventory, `profiles\contracts\brz_ac02_v1.json:347-364`, and by CivilianSedan's own Crew Cargo1/Cargo2 block at `P:\DZ\vehicles\wheeled\config.cpp:5221-5234`). Consequences: the front pair legitimately BOTH sit at index 1 because their PATHS differ (`crew_driver.001` and `crew_cargo.001`) — that is not the bug; adding two REAR seats at index 1 on the shared `crew_cargo` path is, and it fails as a duplicate-selection `ValueError` at authoring time if your builder checks, or as silently missing rear get-in if it does not. Extending a 2-seat rig: continue the `crew_cargo` index, never restart it, and pin the mapping with a test whose RED case is exactly the duplicate pair.

## Invariant 30: a seat box is a get-in volume, not the cushion

**A seat box is a GET-IN VOLUME, not the cushion — vanilla leads it ~0.15 m toward the nose of the crew position, and collapsing the two onto one point makes rear seats unenterable (added 2026-08-16, SUB_WRXSTI).** The engine resolves the get-in cursor by raycast against the ViewGeometry, so the seat box has to sit inside the DOOR APERTURE; the body that occupies the seat sits further back, against the backrest. Vanilla keeps them apart deliberately — measured on the sealed control `civiliansedan_mlod.p3d`: crew proxy z −0.173 vs seat box z −0.358 in front, +0.675 vs +0.531 in the rear, i.e. the box leads the crew proxy by 0.185 and 0.144. A rig that places both at the same declared point looks correct on a 2-seat car — there is open flank ahead of the front seat either way — and puts the box of a 4-seat car inside the C-pillar: the WRX measured **43% reach on BOTH rear seats** (21/49 rays; the 28 blocked were exactly those with z ≥ 0.876, against a pillar occluder starting at +0.881) while the front pair read 100%. Three riders. (a) The pillar occluder is CORRECT — do not carve the body or refine the occlusion grid to make a seat reachable; the tempting diagnosis "residual door skin left in the shell" was refuted by measurement (the rip's `doorhandlelr_a` carries 1970 `carpaint` faces of the rear PANEL — the rip names the skin after the handle — and it was already owned by the rear door roles). (b) Move the BOX, never the crew proxy: the passenger must stay on the cushion. (c) Calibrate the offset against a sealed vanilla 4-seater and cross-check it by sweeping the box along z against the car's own occluder — on the WRX the vanilla-derived 0.740 landed inside the independently swept 100%-clear window [0.700, 0.800], and the sweep reproduced the measured 43% at the shipped z, which is what makes the simulation admissible. The matching detector is invariant 31.

## Invariant 31: derive the seat roster from the crew bones

**Seat/crew checks written as a literal front pair go blind the day a car grows a rear row, and report `2/2 100%` while doing it (added 2026-08-16, SUB_WRXSTI).** `verify_forza_car.py` listed `("seat_driver", "seat_codriver")` in the reach ray fan, the componentNN overlap targets and the ViewGeo presence check, plus a hardcoded `/2` denominator in two report strings. On a 2-seat car that IS the whole roster, so the blindness never shows; on a 4-seat car it printed green over two seats it never scanned, one of which was 43% reachable. Derive the roster from the **crew bones** (`crewdriver→seat_driver`, `crewcargo1→seat_cargo1`, …), not from the seat boxes present: deriving from the boxes is blind in the other direction — a car that LOSES a seat box simply has one fewer thing to check and stays green. Same derivation for the `pos_*(_dir)` memory points. Calibrate against the sealed vanilla 4-seater (it measures 4/4 at 100%), which is what turns a 43% into a defect rather than a strict gate.

## Invariant 32: the open-door action reads the door proxy, and vanilla parity is not a behaviour spec

**Two halves of a car that a name-existence gate cannot see: the open-door action reads the DOOR PROXY, and vanilla parity is not a behaviour spec (added 2026-08-16, SUB_WRXSTI).** (a) `ActionCarDoorsOutside.ActionCondition` does `CarDoor.Cast(target.GetObject())` and then `carDoor.GetActionComponentNameList(...)` — the selection names come from the **attached door item's own `.p3d`**, not from the shell (`4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoorsoutside.c:30-58`, re-read 2026-08-16). If the proxy does not carry `doors_<role>`, `GetAnimSourceFromSelection` returns `""` for every one of its components and the open/close action never appears from outside — no error, no log. Measured placement on both the WRX and the shipped BRZ: the name lives in the proxy's **Geometry and ViewGeometry** LODs; FireGeo carries only `Component01/02`, `dmgzone_*` and `glass_<role>`. Every gate in this project measured the SHELL; nobody had ever opened the six door proxies. When verifying "the doors open", the evidence is the proxy — the shell only proves the model references it and that the animation axis exists. (b) Three behaviours are **correct vanilla ports and still wrong for a mod**: `OnDebugSpawn` drops the parts loose in cargo (`civiliansedan.c:415-437`) so a freshly spawned car needs ten manual attachments before it moves; `CarScript.EEOnCECreate` fills `Math.RandomFloat(0.0, capacity*0.35)` (`carscript.c:2412-2419`) so a CE-spawned car can arrive dry; `CanDisplayCargo` opens the cargo on the boot alone (`civiliansedan.c:174-183`). All three ship a car that loads, drives and looks right, and every structural gate passes them by construction because the criterion is "does it match vanilla". Declare behaviour PER CAR in the profile (`vehicle_script_policy {cargo_access, debug_spawn, ce_spawn_fuel}`) and measure the script against that declaration; derive the attachable roster from the config's own `inventorySlot[]` blocks so a renamed class reds by itself. Rider on the silent one: `CrewCanGetThrough` must compare against `DOORS_CLOSED`, because a torn-off door reports `DOORS_MISSING` — writing the same intent as `!= DOORS_OPEN` reads correctly, passes every structural check, and makes a doorless car unenterable. See LL-279.

## Invariant 34: an absent config key is a question about the parent

**An absent key in a config class is NOT a value — it is a question about the parent (added
2026-08-21, from a refutation that did not survive).** Reading `config.cpp` by grepping for a
key and treating "no hit" as "the default" gets the answer backwards whenever the class
extends another that sets it. Measured case: `CivSedanDoors_BackLeft` declares no
`rotationFlags` at all — four lines of body (`P:\DZ\vehicles\wheeled\config.cpp:4938-4947`) —
and extends `CivSedanDoors_Driver`, which sets `8` (`:4813`). A note published on
2026-08-19 read the absence as `4` and concluded the sedan REFUTES the left-8/right-4 rule;
it does not, it is the rule's own prediction. The other five do declare `4` (CoDriver
`:4936`, BackRight `:4957`, Hood `:4972`, Trunk `:5049`), which is exactly what made the
sixth look like an outlier instead of an inheritance. **Resolve the chain before quoting a
value, and say which link you read it from.** The same trap applies to every inherited
config key, not just `rotationFlags`.

## Family B: get-in absent

For a new car ripped from a source game and split into proxies, the step by step repair for a missing get-in is the family B cookbook `cookbook-get-in-missing.md` of the rip-vehicle-import skill.
