# Get-in, seat and door checks

Why a get-in, seat or door action does not appear on a new or imported car, and the model, config and script rules that make it appear.

The get-in condition link by link, and which anchor places the occupant, are in `get-in-actions-and-proxy-pose.md`; the step-by-step repair for a missing prompt is in `get-in-guards.md`. Vanilla facts cite `P:\` (DayZ 1.30). Measured cases come from mod vehicles; several were measured against a debinarized copy of the vanilla sedan, which is not on `P:\`, so those positions are not checked there.

## The car needs a script class

A config class with no script class of its own runs as bare `CarScript`, which inherits `Transport.CrewCanGetThrough()`. That returns `false` unless `CFGMODS_DEFINE_TEST` is defined (`P:\scripts\3_game\vehicles\transport.c:724` to `:727`), so the get-in action is filtered out and never appears; no bone, proxy or component fix helps. Write `MyMod_Base extends CarScript` overriding `CrewCanGetThrough`, `GetAnimInstance` and `GetSeatAnimationType`, and register the script module in `CfgMods`. Confirmed in game on three mod vehicles. See also `crew-get-in-geometry.md`.

The script module must actually load, or the class never binds and nothing reports it. `CfgMods` `files[]` with the wrong slashes, or a path that resolves to `*.p3d.p3d`, leaves the module unloaded: no get-in, no error. The binding notes are in `crew-get-in-geometry.md`, section "The script module must load".

## A config parent does not bring its script

If the config says `class MyMod_Car: OffroadHatchback` but the script class is `MyMod_Car extends MyMod_Base` with `MyMod_Base extends CarScript`, the parent car's script overrides do not come along: they live in the vanilla `inheritedcars\<parent>.c`, which your class never inherits. Every method with a hostile default in `Transport` that all vanilla cars override then bites:

| Method | Default in `Transport` | Effect |
|---|---|---|
| `CrewCanGetThrough` | `false` (`transport.c:724`) | No get-in |
| `IsVitalGlowPlug` | `true` (`:409` to `:412`) | A petrol car will not start (`invariants-engine-fluids-and-handling.md`) |
| `GetAnimInstance` | `Error()` (`:665`) | No seat animation |
| `GetSeatAnimationType` | `Error()` (`:685`) | No seat animation |
| `Get3rdPersonCameraType` | `Error()` (`:701`) | No camera |

Diff method by method against the parent's `P:\scripts\4_world\entities\vehicles\inheritedcars\<parent>.c` and copy every runtime override, not only the two pose methods. A test helicopter with an `OffroadHatchback` config parent and its own script base had neither get-in nor engine start after two reviews; the first fix restored only the pose methods.

## Check where the engine is before copying a car

`Sedan_02` looks like the four-seat sedan to copy, but it is rear-engined: it keeps `CarBattery` and `SparkPlug` behind `Sedan_02_Trunk` (`P:\scripts\4_world\entities\vehicles\inheritedcars\sedan_02.c:142`) and `CarRadiator` behind `Sedan_02_Hood` (`:156`), and its `CanDisplayCargo` tests the hood (`:203`). Ported to a front-engined car, the engine parts sit behind the wrong lid, a bug that only shows in game. For a front-engined four-seater copy `CivilianSedan`. Check where the engine lives, not only how many seats there are.

## Four seats

Rear seats need, on top of the front pair:

- Memory points `pos_cargo1`, `pos_cargo1_dir`, `pos_cargo2`, `pos_cargo2_dir`, `seat_con_1_2` and `seat_con_2_2`.
- `seat_cargo1` and `seat_cargo2` boxes tagged into their exact `componentNN` in Geometry and View Geometry.
- `crewcargo1` and `crewcargo2` proxies in View Geometry and Fire Geometry, on one `crew_cargo` path with distinct instance numbers (below).
- `Crew` `Cargo1` and `Cargo2` entries with `actionSel`, `proxyPos`, `getInPos` and `getInDir`; `CivilianSedan` declares them with `proxyPos` `crewCargo1` and `crewCargo2` (`P:\DZ\vehicles\wheeled\config.cpp:5221` to `:5234`).
- The two passenger cases in both `GetSeatAnimationType` (`VEHICLESEAT_PASSENGER_L`, `VEHICLESEAT_PASSENGER_R`) and `CrewCanGetThrough`, as `CivilianSedan` does (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:119`; `CrewCanGetThrough` at `:226` to `:256`).

`CarScript` already maps `seat_driver`, `seat_codriver`, `seat_cargo1` and `seat_cargo2` to `seat_con_1_1`, `seat_con_2_1`, `seat_con_1_2` and `seat_con_2_2` (`P:\scripts\4_world\entities\vehicles\carscript.c:2141` to `:2156`), so an override of `GetDoorConditionPointFromSelection` that repeats that table is dead code.

`CrewCanGetThrough` must compare each door with `DOORS_CLOSED`, as `CivilianSedan` does. A torn-off door reports `DOORS_MISSING`, so the same intent written as `!= DOORS_OPEN` reads right, passes every structural check, and makes a doorless car impossible to enter.

## Right-hand drive

The base door table is the left-hand-drive mapping. On a right-hand-drive car whose memory points are named by physical side (driver door `seat_con_2_1`), it pairs every seat with the far door, so `CanReachSeatFromDoors` fails its 1 m distance from the right door and no get-in appears even with names, points and components correct. A condition probe shows "unreachable" from the right door and "available" from the opposite one.

Override it with the sides crossed: driver to `seat_con_2_1`, co-driver to `seat_con_1_1`, cargo 1 to `seat_con_2_2`, cargo 2 to `seat_con_1_2`, as vanilla does for its own layouts (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:364` to `:379`; `P:\scripts\4_world\entities\vehicles\inheritedcars\van_01.c:269` to `:287`). Cross `GetSeatAnimationType` for the rear seats too, since vanilla pairs L with the physical left (`civiliansedan.c:119` to `:134`). The driver keeps `VEHICLESEAT_DRIVER`, whose get-in animation still looks left-hand-drive; that is an engine limit, not a mod bug.

## Crew proxies are one model, numbered by instance

Vanilla ships exactly two crew proxy models, `P:\DZ\vehicles\wheeled\proxies\crew_cargo.p3d` and `P:\DZ\vehicles\wheeled\proxies\crew_driver.p3d`; there is no `crew_cargo1.p3d`. The seat comes from the instance number: `crew_cargo.001` is the co-driver, `.002` cargo 1, `.003` cargo 2 (the bone is `crewcodriver` for index 1, else `crewcargo<index - 1>`), which matches the sedan's `Cargo1` and `Cargo2` crew block. The front pair both sit at index 1 because their paths differ (`crew_driver.001`, `crew_cargo.001`). Two rear seats both at index 1 on `crew_cargo` collide: a duplicate selection error if your builder checks, silently missing rear get-in if not. When extending a two-seat rig, continue the `crew_cargo` numbering, and pin it with a test whose failing case is exactly that duplicate.

Crew and wheel proxies must exist in both View Geometry and Fire Geometry. The proxy triangle uses the engine's identity frame, `R=((-1,0,0),(0,0,1),(0,1,0))` in model space, not py3d's `rotation=None` (**model knowledge**).

## Seats and hubs need their `componentNN`, and must be hit by the view ray

The engine lists collision components only by `componentNN`. A seat or wheel hub that is a separate island with no `componentNN` overlap is invisible to it: the car will not spawn or the seat is missing. Tag the same faces with a `componentNN` as well (**model knowledge**).

The View Geometry seat box must also be hit by `RaycastRV(ObjIntersectView)`: wound inward, with every point flag `0x0000003F`. A py3d box left outward with flags 0 passes every offline shape, winding and tag check, but the ray misses it, the cursor falls through to `component0`, the driver works by fallback and the co-driver never resolves. That blocked the co-driver in game on two test cars; the fix changed winding and flags together, so copy the convention of the vanilla sedan or of a mod car whose get-in works, never py3d's default.

Find each seat's `componentNN`; never hardcode its number, because assembly order moves component numbers. For every `seat_*` selection, compare point and face membership against each `componentNN` in the same LOD and require exactly one exact match; zero or several is a hard failure. Run it again after any transform.

When a model fails with both `seat_* not found` and `wheel ... no proper selection`, the confirmed fix is the `componentNN` tag. Sorting LODs by resolution matches vanilla and is fine as tidy authoring, but it is not a proven cause: sorted without the tag still failed, sorted with it spawned, and the tag without sorting was never tried. `binarize` accepts either order silently.

## A seat box is a get-in volume, not the cushion

The cursor resolves seats by raycast against View Geometry, so the seat box must sit in the door opening, while the body that occupies the seat sits further back against the backrest. Vanilla keeps them apart: on the debinarized sedan, the crew proxy is at z -0.173 and the seat box at -0.358 in front, +0.675 against +0.531 in the rear, so the box leads the proxy toward the nose by 0.185 and 0.144 m.

A rig that puts both at one point looks fine on a two-seater and, on a four-seater, puts the rear boxes inside the C-pillar. One imported car reached only 43 percent on both rear seats (21 of 49 rays; the 28 blocked were exactly those at z 0.876 or more, against a pillar starting at +0.881) while the front pair read 100 percent.

- The pillar is correct; do not carve the body or refine the occlusion grid to free a seat. Leftover door skin in the shell was ruled out by measurement.
- Move the box, never the crew proxy; the passenger must stay on the cushion.
- Calibrate the offset against the vanilla four-seater and cross-check by sweeping the box along z against the car's own pillar. On that car the vanilla-derived 0.740 landed inside the swept clear window of 0.700 to 0.800, and the sweep reproduced the 43 percent at the shipped z.

## Derive the seat list from the crew bones

Seat checks written as a literal front pair go blind when a car gets a rear row, and report "2/2 100%" while doing it: one checker listed only `seat_driver` and `seat_codriver` in its ray fan, component overlap and presence checks, with a hardcoded "/2", and printed green over two seats it never scanned, one at 43 percent. Derive the list from the crew bones (`crewdriver` to `seat_driver`, `crewcargo1` to `seat_cargo1` and so on), not from the seat boxes present; deriving from the boxes is blind the other way, because a car that loses a box has one fewer thing to check. Do the same for the `pos_*` memory points. The vanilla four-seater measures 4 of 4 at 100 percent, which is what makes 43 percent a defect.

## Parts with their own actions

The outside door action does `CarDoor.Cast(target.GetObject())` and then `carDoor.GetActionComponentNameList(...)` on the door item itself (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoorsoutside.c:34` and `:37`, inside the outside branch that starts at `:30`), then asks the car for `GetAnimSourceFromSelection` (`:43`). The selection names come from the attached door's own `.p3d`, not the shell. If the door model does not carry `doors_<role>`, every component returns `""` and open or close never appears from outside, with no error.

So an attached part with its own actions (door, hood, trunk) needs, in its own model:

- A View Geometry `componentNN` tagged with a selection named exactly what the car's `GetAnimSourceFromSelection` expects, such as `doors_driver`.
- Every View Geometry point flag `0x0000003F`; a View Geometry with flags 0 is not hit by the ray, the item under the cursor never resolves, and the action is filtered out with config, scripts, slots, bones and sources all correct.
- Inward winding; copy a working seat box as the control.

On two imported cars the name lives in the door's Geometry and View Geometry LODs; Fire Geometry carries only `Component01`, `Component02`, `dmgzone_*` and `glass_<role>`. The symptom is a part that attaches, renders and takes damage, with `GetCarDoorsState` working, but no open or close action and so no get-in through that door. Count the part's View Geometry point flags against a working control before touching config or script. A check that only measures the shell never opens the door models; when verifying that doors open, the evidence is the door model.

## Vanilla behaviour that is wrong for a mod

Three behaviours are faithful vanilla ports, pass every check that compares with vanilla, and can still be wrong for your car:

- `OnDebugSpawn` creates wheels, doors, hood and trunk with `CreateInInventory` (`civiliansedan.c:415` to `:437`), which may put a part in cargo instead of its slot (`P:\scripts\3_game\systems\inventory\inventory.c:876` to `:893`), so a fresh car can need up to ten parts fitted by hand before it moves.
- `CarScript.EEOnCECreate` fills a random 0 to 35 percent of fuel (`carscript.c:2412` to `:2419`), so a Central Economy spawn can arrive almost dry.
- `CanDisplayCargo` opens cargo through the boot alone (`civiliansedan.c:174` to `:183`).

Decide each per car, write the decision down, and check the script against it. Take the list of attachable parts from the config's own `inventorySlot[]` blocks, so a renamed class fails on its own.

## Inherited config

An absent key in a config class is not a default; it is a question about the parent. `CivSedanDoors_BackLeft` declares no `rotationFlags` (`P:\DZ\vehicles\wheeled\config.cpp:4938` to `:4947`) and inherits `rotationFlags=8` from `CivSedanDoors_Driver` (`:4813`). Reading the absence as 4 makes the sedan look like it breaks the "left 8, right 4" rule; it is the rule's own prediction. The co-driver door (`:4936`), back right door (`:4957`), hood (`:4972`) and trunk (`:5049`) declare 4. Resolve the chain before quoting a value, and say which link you read it from.

Shipped vanilla cars usually have no loose `model.cfg`; their skeleton is baked into the binarized model. Read the baked skeleton and selection names with an outside ODOL to MLOD converter, after validating the reader on a model whose `model.cfg` you have: name, `isDiscrete`, bone count and every bone and parent pair must match. Binarized bone names are lower case. A uniform zero from both control and candidate means the tool failed; confirm known bytes directly before concluding anything.

For a car that inherits a working vanilla car, an undeclared property has the parent's value and cannot by itself be the difference. Keep only differences where two independent controls agree and the candidate differs, then look at: what only the candidate declares; skeleton, animation and selection data tied to the model; and values both controls override but the candidate neither declares nor inherits. Finally resolve every inherited model name (`animDamper`, `wheelHub` and the like) against the candidate `.p3d`; the reference is inherited even when the named bone or selection is missing.

## Moved elsewhere

Wheels that do not simulate: `wheel-simulation-wiring.md`. An attached part that does not render: `attachment-proxies.md`.
