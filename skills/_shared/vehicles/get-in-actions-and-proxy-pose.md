# Get-in actions and the pose of a proxied submodel

The four-link condition chain behind the get-in prompt, the two registrations a cursor-targeted vehicle action needs, the `Geometry` and `autocenter=0` gate for a submodel placed by proxy, where the occupant's pose really comes from, and why a part's `model=` governs both the fitted part and the loose item.

> Status: the measurements below were taken on mod test vehicles (LFHeli, LFQuad, LFQuad2, SUB_BRZ), named in each entry; they are mod behaviour, not vanilla, and were not repeated for this file. A citation written with its full `P:\` path was opened on the vanilla data of this repo (a 1.30 build); a bare `file.c:N` repeats a full citation from the anchors list below. A number marked 1.29 belongs to the 1.29 build, which is not on `P:\`. "Invariant N", "preflight #N" and "#N" mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number. The symptom-first version of the get-in checks is in `invariants-get-in-and-seats.md` and in `attachments-and-crew.md` ("When a seat or door action does not appear"); the 1.30 changes to the condition are in `dayz-1-30-vehicles.md`, section 5.

Related files in this pack: `proxies-and-get-in.md` (proxy placement and the contract of detachable parts) and `invariants-get-in-and-seats.md` (the numbered get-in checks).

## Vanilla anchors checked on `P:\`

- The get-in condition first asks `CanGetIn`: `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:36`.
- It then asks `CrewCanGetThrough` and `IsAreaAtDoorFreeDiag`: `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:54`.
- It ends by calling `CanReachSeatFromDoors` with 1.0 from script: `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:64`.
- `CrewPositionIndex` maps a component to a crew index: `P:\scripts\3_game\vehicles\transport.c:179`.
- `CanGetIn` returns `true` on `Transport`: `P:\scripts\3_game\vehicles\transport.c:672`.
- `CrewCanGetThrough` returns `false` on `Transport` unless `CFGMODS_DEFINE_TEST` is defined: `P:\scripts\3_game\vehicles\transport.c:724`.
- `IsAreaAtDoorFree` with its default extents: `P:\scripts\3_game\vehicles\transport.c:889`.
- `GetDoorConditionPointFromSelection` maps a seat selection to a `seat_con_*` point: `P:\scripts\4_world\entities\vehicles\carscript.c:2141`.
- `CanReachSeatFromDoors` has `pDistance = 1.0` in its signature: `P:\scripts\4_world\entities\vehicles\carscript.c:2177`.
- `RegisterActions` of `ActionConstructor`: `P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:27`.
- `SetActions` of `PlayerBase`: `P:\scripts\4_world\entities\manbase\playerbase.c:1695`.
- `Hatchback_02_Wheel` is declared at `P:\DZ\vehicles\wheeled\config.cpp:8980`.
- `Hatchback_02_Wheel_Ruined` inherits it with another `model=`: `P:\DZ\vehicles\wheeled\config.cpp:9006`.
- `Hatchback_02_Door_1_1` is declared at `P:\DZ\vehicles\wheeled\config.cpp:9019`.
- `Hatchback_02_Door_2_1` is declared at `P:\DZ\vehicles\wheeled\config.cpp:9144`.
- `Hatchback_02_Door_1_2` is declared at `P:\DZ\vehicles\wheeled\config.cpp:9155`.
- `OffroadHatchback` overrides `GetDoorConditionPointFromSelection`: `P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:364`.
- `Van_01` overrides `GetDoorConditionPointFromSelection`: `P:\scripts\4_world\entities\vehicles\inheritedcars\van_01.c:269`.
- `Motorbike_01_ColorBase` overrides `CanGetIn`: `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:92`.

## Three layers that are easy to conflate

This reference isolates three commonly conflated layers: resolving a seat under
the cursor, registering a custom world action, and preserving the authored pose
of a `.p3d` instantiated by proxy.

## Get-in prompt: four ordered gates

`ActionGetInTransport.ActionCondition`
accepts a seat only when all four links pass:

1. The cursor-hit ViewGeometry component maps through
   `Transport.CrewPositionIndex(componentIndex)` to a crew index. A single
   envelope component in front of the seat components can therefore make the
   mapping fail even when the seat cubes themselves are valid.
2. `CrewCanGetThrough(crewIndex)` returns true. The base `Transport`
   implementation returns false outside `CFGMODS_DEFINE_TEST`, so a custom car
   must provide the correct runtime override through its script class.
3. `IsAreaAtDoorFree(crewIndex)` passes its collision-box check around the
   `CrewEntry` transform.
4. At least one action selection passes `CanReachSeatFromDoors`. `CarScript`
   maps `seat_driver`, `seat_codriver`, `seat_cargo1` and `seat_cargo2` to
   `seat_con_1_1`, `seat_con_2_1`, `seat_con_1_2` and `seat_con_2_2`
   respectively, requires that memory point to exist, ignores vertical
   distance and applies the 1 m horizontal limit that the action passes.

(until 1.29: the four gates above, with door clearance via `IsAreaAtDoorFree`.)
(since 1.30: the condition first asks `CanGetIn()` and wraps gate 3 as `IsAreaAtDoorFreeDiag`; the code and the 1.29 comparison are in `dayz-1-30-vehicles.md`, section 5, and the motorbike `SeatDriver` check inside `CanGetIn()` is in `motorbike-invariants.md`, item 4.)

Inspect and fix them in that order. Rebuilding `seat_con_*` cannot help while
the cursor resolves an envelope component, and script changes cannot help while
the model lacks the final memory point.

Source anchors (line numbers of the 1.30 build on `P:\`; on 1.29 the condition was `actiongetintransport.c:26-80` of that build):

- The whole condition: `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:26` to `:69`.
- `CrewPositionIndex` at `P:\scripts\3_game\vehicles\transport.c:179`, `CrewCanGetThrough` at `:724` to `:731`, and the two `IsAreaAtDoorFree` overloads at `:844` to `:899`.
- `GetDoorConditionPointFromSelection` at `P:\scripts\4_world\entities\vehicles\carscript.c:2141` to `:2160`, and `CanReachSeatFromDoors` at `:2177` to `:2199`.

The envelope-component failure was cross-checked in a custom vehicle; vanilla
source establishes the component-to-seat and subsequent condition order.

## Cursor-targeted world action: the constructor and the vehicle's own action list

A custom `ActionInteractBase` offered while the player looks at a vehicle needs both:

1. insertion of its typename from a `modded class ActionConstructor` override
   of `RegisterActions(TTypenameArray actions)`, after `super`;
2. addition to the vehicle's own action list, from the vehicle script class's
   `SetActions()` override with `AddAction(MyAction)`, after `super`.

The cursor reads the target's own list. `ActionInteractBase` uses
`InteractActionInput`, which inherits `ContinuousInteractActionInput`, and that
input sets `m_DetectFromTarget = true`; `UpdatePossibleActions` then collects the
actions of `target.GetObject()` and of its parent. Vanilla relies on this:
`ActionOpenCarDoorsOutside` and `ActionGetInTransport` are added only in
`CarScript.SetActions` and appear nowhere in `PlayerBase.SetActions`, yet the
cursor offers them.

The `PlayerBase.SetActions` map is what an action with no cursor target needs,
such as one offered to a seated occupant; that case is in `proxies-and-get-in.md`,
section "In-vehicle actions need two registrations".

Probe one boot with rate-limited log markers at: registration, action
construction, and `ActionCondition` after a successful target cast. Absence at
each marker identifies the dead link without changing the condition blindly.

Source anchors:

- `RegisterActions` starts at `P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:27`, and it inserts `ActionGetInTransport` at `:302`.
- `ActionInteractBase.GetInputType` returns `InteractActionInput`: `P:\scripts\4_world\classes\useractionscomponent\actions\actioninteractbase.c:61`.
- `ContinuousInteractActionInput` sets `m_DetectFromTarget = true`: `P:\scripts\4_world\classes\useractionscomponent\actioninput.c:552`; `InteractActionInput` inherits it at `:558`, and the target's actions are read at `:382` to `:386`.
- `CarScript.SetActions` adds `ActionOpenCarDoorsOutside`, `ActionCloseCarDoorsOutside` and `ActionGetInTransport`: `P:\scripts\4_world\entities\vehicles\carscript.c:2315` to `:2317`.
- `PlayerBase.SetActions` runs from `P:\scripts\4_world\entities\manbase\playerbase.c:1695` to `:1745` and holds the in-seat vehicle actions: start and stop engine with their boat and motorbike variants (`:1707` to `:1712`), `ActionSwitchSeats` (`:1713`), the inside door actions (`:1714` to `:1715`) and `ActionGetOutTransport` (`:1728`). It holds none of the outside door or get-in actions.

## Multi-LOD submodel instantiated by proxy

In the measured multi-LOD proxy
case, a visual-only submodel with no Geometry LOD was recentered during
binarization: the offset moved into ODOL `model_info.bounding_center` while the
shell proxy matrix remained authored, so the rendered part shifted.

The robust authoring gate is:

- add a Geometry LOD to the submodel, even an empty one;
- set its named property `autocenter=0`;
- after binarize, read the deployed ODOL and require
  `model_info.bounding_center == (0,0,0)` within the chosen numeric tolerance;
- compare the submodel MLOD/ODOL centroid and shell proxy transform against the
  expected world pose.

Treat a non-zero deployed bounding center as pose risk, not as proof of the
exact visual displacement. The evidence is cross-checked against one custom
vehicle plus working vanilla/community multi-LOD proxy controls; it is not a
claim that every single-LOD engine proxy follows the same path.

## Two caveats from the measured case (added 2026-07-26)

- several `modded class PlayerBase` files may coexist in a mod, but two of them must not add the same field or the same non-override method; a `SetActions` override can go in any of them, and each must call `super.SetActions()`.
- prompt shown + hand animation playing + server state flipping (`[LFHELI-DBG] door open=true`) with NO visible door motion = the SCRIPT chain is fine; suspect the baked-anim side (selection content in the binarized ODOL, skeleton bone, axis) — the script/anim boundary is exactly SetAnimationPhase.

## Vanilla script passes the 1 m limit; instrument before moving the condition point (added 2026-09-07)

Gate 4 above says `CanReachSeatFromDoors` applies a 1 m horizontal limit. Vanilla script calls
the method itself and passes `1.0` as `pDistance`, with the player's position as `pFromPos`
(`actiongetintransport.c:64`); `1.0` is also the default in the signature (`carscript.c:2177`).
The call, the code and what changed in 1.30 are in `dayz-1-30-vehicles.md`, section 5.

Note: an earlier version of this file read the 1 m as a signature default only and said no
vanilla script calls the method. That is false on the 1.30 data on `P:\` and, per
`dayz-1-30-vehicles.md` section 5, on 1.29 too.

What still holds is a warning against guessing the result of a memory-point change.
Measured cost of guessing (LFQuad2, 2026-09-07): a quad whose
`GetDoorConditionPointFromSelection` returned the approach points `pos_driver`/`pos_codriver`
instead of centred ones was "corrected" to return the centred crew points. The change had three
true supports — two vanilla vehicles return centred points (`van_01.c:269`,
`offroadhatchback.c:364`), the sibling mod does the same, and the offline arithmetic gave 0.85 m
and 0.83 m against the 1 m limit. In game it broke two things at once: the driver entering from
the right ended up yawed 15-20 degrees, and the codriver became unreachable from **both** sides.
Reverted.

Before changing which memory point this method returns, **instrument it**: a logging override
that prints `pSeatSelection`, `pFromPos` and `pDistance` on every call costs one cycle and
settles which point and distance each call actually uses. If it cannot be instrumented, the change is a bet:
ship it **alone**, never bundled with other changes, so the outcome is attributable.

## The occupant's pose comes from the ViewGeometry crew proxy, not the Memory point (added 2026-09-07)

Moving `crewdriver` in the **Memory LOD** does not move the occupant. Measured on LFQuad2 across
two runs differing only in that point (40 mm forward), with a probe printing player bone
positions in the vehicle frame:

    PEL   dX  -4.0   dY  -0.7   dZ  +1.4 mm      (143 and 1293 settled samples)
    LH    dX  +2.9   dY  +0.4   dZ  -0.9 mm
    RH    dX  -4.8   dY  +0.6   dZ  +3.3 mm

Nothing, and inside the noise (sd 0.05-0.08). The pelvis stayed at Z +0.2928 while the
ViewGeometry `crewdriver` proxy sat at +0.2948: 2 mm apart. Seventy millimetres of seat edits
applied before this was known moved the rider by nothing at all, across two review rounds.

**The anchors live in THREE places and must move together:**

    Memory LOD     crewdriver / crewcodriver                                   1 point
    ViewGeometry   crewdriver + proxy:\dz\vehicles\wheeled\proxies\crew_driver.001   3 points
    Geometry       only the proxy:\... name, NOT the crewdriver alias                3 points

Two traps when editing them. The two ViewGeometry names **share the same Point objects**, so a
script that iterates both selections shifts them twice unless it deduplicates by identity. And
the Geometry LOD carries only the `proxy:\...` names, so a verifier that looks up `crewdriver`
there raises `KeyError` instead of reporting a difference.

**Cheap offline check that catches a half-moved anchor**: the Memory-to-ViewGeometry offset must
match what the model shipped with, and in a healthy model it is **the same for every crew
position** — LFQuad measures 0.0 / 100.7 / 200.3 mm for driver and codriver alike. Two seats with
different offsets mean somebody moved one copy and not the others. On LFQuad2 that showed up as
18.9 mm of X disagreement on the codriver after a centring edit, and the user reported it as the
camera jumping for an instant on mounting: the engine seats you with one anchor and corrects to
the other.

## A model proxy is a HOLE the engine fills from the attached item's `model=` (added 2026-09-07)

The section above is about preserving the authored pose of a `.p3d` instantiated by proxy. This
one is about a prior question that is easy to get backwards: **the proxy baked into the vehicle
does not fix which mesh appears there.** It reserves the slot and the transform; the mesh comes
from the `model=` of whatever item is attached, exactly the way fitting a ruined wheel changes
the wheel you see.

Vanilla states it plainly — same proxy on the car, different `model=` per item:

    class Hatchback_02_Wheel: CarWheel
        model = "\DZ\vehicles\wheeled\Hatchback_02\proxy\Hatchback_02_Wheel.p3d";
    class Hatchback_02_Wheel_Ruined: Hatchback_02_Wheel
        model = "\DZ\vehicles\wheeled\Hatchback_02\proxy\Hatchback_02_Wheel_ruined.p3d";

and every door is its own file, one per side, in a directory literally called `proxy\`:
`Hatchback_02_Door_1_1.p3d` (driver), `Hatchback_02_Door_2_1.p3d` (codriver),
`Hatchback_02_Door_1_2.p3d`. Source anchors: the wheel, the ruined wheel and the three doors are at `P:\DZ\vehicles\wheeled\config.cpp:8980`, `:9006`, `:9019`, `:9144` and `:9155`;
the same pattern holds for the Niva (`HatchbackWheel` at `:853`, `HatchbackWheel_Ruined` at `:882`, `HatchbackDoors_Driver` at `:908`, `HatchbackDoors_CoDriver` at `:1030`) and the CivilianSedan (`CivSedanWheel` at `:4762`, `CivSedanWheel_Ruined` at `:4788`, `CivSedanDoors_Driver` at `:4803`, `CivSedanDoors_CoDriver` at `:4927`).

**The consequence that costs a deployment.** That one `model=` governs BOTH the fitted part and
the loose inventory item, because they are the same entity in two states. So it cannot be used to
fix an inventory preview, a loose-item icon or a mounted mesh in isolation: change it and both
move together. Pointing a codriver door item at the driver door's `.p3d` puts a left-hand door on
the right-hand side of the car — measured in a deployed build of a custom vehicle (SUB_BRZ,
reverted in the next build with a negative gate; the failing case was reported by the user as the door on the
wrong side, not as a config error).

**Before changing a part's `model=`, name both consumers.** Write down what the fitted part should
look like and what the loose item should look like. If the answer differs, `model=` is the wrong
lever and the fix belongs in the part's own `.p3d`, in a separate item class, or in the
`hiddenSelections` of the host — not in a path swap.
