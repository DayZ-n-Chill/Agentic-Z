# Vehicle door mechanisms

Which of the three unrelated door mechanisms a door needs, how to choose before modelling or scripting, and the trap on each vehicle route when a door shows no open or close action.

## Choose the mechanism first

DayZ has three door mechanisms that share words (`source`, `component`, `axis`) but nothing else. Picking the wrong one costs a full modelling and config cycle, and the symptom, a missing action, looks the same for all three. Choose from this table before any other work.

| You are building | Mechanism | Read |
|---|---|---|
| A door, hatch or lid on a building or static prop | `class Doors` under a `HouseNoDestruct` class; the animation `source` maps to a Doors `component` (`class Doors1` with `component="Doors1"`, `P:\DZ\structures\residential\config.cpp:24` to `:29`) | `_shared/animation/building-doors.md` |
| A door on a vanilla style car, as a part that comes off | A `CarDoor` item plus `ActionCarDoorsOutside`. The action casts its target to `CarDoor` and reads that item's action component names (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoorsoutside.c:34` to `:37`), so the target is found by a ray against the item's View Geometry | `attachment-proxies.md` and `invariants-get-in-and-seats.md` |
| A door that stays part of the shell, with no detach and its own action | Your own actions with your own door index lookup, open test and setter, and the motion in `model.cfg` `AnimationSources` | This file, "The scripted route" |

The building door API is for buildings: `IsDoorOpen` is declared on `Building` (`P:\scripts\3_game\entities\building.c:34`), and vanilla has no door index lookup or door setter for vehicles, so the scripted route writes its own. The building door files do not cover vehicle doors. If the door belongs to a car or a helicopter, their `class Doors` pattern will not produce a working action.

## The attachment route

The action never appears, with no error, when the points of the door item's View Geometry carry flags `0x0` instead of the flags of a working door. Config, script overrides, slots, bones and animation sources can all be right and the action is still filtered out. Compare the item's View Geometry point flags against a door that works before touching config. Two values have been written down for this, `0x02000000` and `0x0000003F` (`invariants-get-in-and-seats.md`), so take the value from your working door, not from either number (**model knowledge**).

Measured in game on a test car: with the flags matched, the attached door draws in place and its action appears.

## The scripted route

Make the open test fail closed: an unknown door reads as closed. Keep every diagnostic probe read only. A probe that calls `SetAnimationPhase` to look at a door changes live state: the door closes on screen while the logical state stays open, and the next diagnosis chases a bug the probe made.

This route was built and checked offline on a test helicopter, not yet in game; confirm it in game the first time you use it.
