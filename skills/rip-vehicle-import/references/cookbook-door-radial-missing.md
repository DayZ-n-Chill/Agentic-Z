# Cookbook: door radial missing

For a vehicle door that shows no open or close action: the three unrelated door mechanisms in DayZ, how to pick the right one before modelling or scripting, and the trap of each vehicle path.

Vanilla facts cite the file on `P:\`. The contracts measured on MercedesAMGLF, SUB_BRZ and LFHeli are not yet checked on `P:\`. Added 2026-07-27.

## Door mechanism selector

Decide this before modelling or scripting anything. DayZ has three unrelated door mechanisms. Picking the wrong one costs a full modelling and config cycle, and they share vocabulary (`source`, `component`, `axis`), so the mistake does not show in the symptom. Doors were solved from scratch on three projects (MercedesAMGLF, SUB_BRZ, LFHeli); pick from this table first.

| You are building | Mechanism | Where the contract lives |
|---|---|---|
| A door, hatch or lid on a building or static prop | `class Doors` under a `HouseNoDestruct` class; the animation `source` maps to a Doors `component` (vanilla example: `class Doors` with `component="Doors1"`, `P:\DZ\structures\residential\config.cpp:24-29`) | The skill `dayz-doors` |
| A door on a vanilla-style car, as a part that detaches | Attachment: a `CarDoor` item plus `ActionCarDoorsOutside`. The action casts its target object to `CarDoor` and reads the action component names of that item (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoorsoutside.c:34-37`), so the target is resolved by a raycast against the item's View Geometry | `references/cookbook-attachment-invisible.md` (invariant 21) and the door item View Geometry contract in the vehicles pack (invariant 22) |
| A door that must stay part of the shell (no detach, custom radial) | Own actions that drive `GetNearestDoorIndex`, `IsDoorOpen` (fail-closed) and `SetDoorOpen`, with the motion in `model.cfg` AnimationSources | The LFHeli OH-1 contract v5 (not shipped here) |

`GetNearestDoorIndex` and `SetDoorOpen` are methods of the LFHeli project, not vanilla: the scripts on `P:\` have neither. The vanilla `IsDoorOpen` belongs to buildings (`P:\scripts\3_game\entities\building.c:34`).

**`dayz-doors` does not cover vehicle doors.** Its scope is buildings and static props. The name attracts anyone with a door problem; if the door belongs to a car or a helicopter, that skill is the wrong contract and its `class Doors` pattern will not produce a working radial.

## Two traps of the vehicle paths

- **Attachment path.** The radial never appears, with no error, when the points of the item's View Geometry carry flags `0x0` instead of the flags of a working control. Config, script overrides, slots, bones and animation sources can all be correct and the action is still filtered. Census the item's View Geometry point flags against a working control before touching config. The required value is recorded two ways: `0x02000000` in the legacy seat rule (step 7 of `history-canonical-path.md`) and `0x0000003F` in invariant 22 (`skills/_shared/vehicles/invariants-get-in-and-seats.md`), so take the value from the control, not from either literal.
- **Scripted path.** Enumeration probes must be read-only. A diagnostic probe that calls `SetAnimationPhase` to "look at" a door corrupts live state: the door closes visually while the logical state stays open, and the next diagnosis chases a bug the probe created.

## Status

Invariants 21 and 22 were measured offline, and their in-game gate was still pending on 2026-07-18. Both were closed in game on 2026-08-24: the attached part renders in its place and the radial action appears on the attached panel. The OH-1 scripted contract v5 is implemented with its cycle gate pending; treat it as verified offline and confirm it in game on first use.
