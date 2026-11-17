# Cookbook: wheelPresent=0

For a family B car whose wheels are attached but do not simulate: what the symptom looks like, which fix was refuted and where the real gate is.

Vanilla facts cite the file on `P:\`. The LFQuad measurement and the work items SP-017 and SP-027 come from the author's projects and are not yet checked on `P:\`.

## Symptom

`WheelCountPresent()` returns 0 while `WheelCount()` returns 4. There is no traction and no wheel spin, the body sinks or bounces, and the RPT shows no error. `WheelCount` is how many wheels can be attached (hubs only) and `WheelCountPresent` is how many are attached (`P:\scripts\3_game\vehicles\car.c:345-348`).

## What is parity and what is the gate

- **Parity, required but not the gate.** The Geometry LOD carries the named property `class=vehicle`. All six vanilla wheeled vehicles the author checked have it and it is cheap to replicate, so add it. It was refuted as the wheel simulation gate: deploying it alone left `wheelPresent=0` (LFQuad, in game, 2026-05-27).
- **The gate.** The wheel simulation depends on the wiring between `selection` in `CfgSlots` and the selection of the same name in the Fire Geometry LOD (SP-017). Vanilla gives each wheel slot the model selection it shows: `Slot_CivSedanWheel_1_1` has `selection="wheel_1_1"` (`P:\scripts\config.cpp:1089-1093`). The slot chain for one attachment is in the vehicles pack (`skills/_shared/vehicles/attachments-and-crew.md`).

The symptom is the same either way, so check the wiring first.

## Where the full rule is

The Fire Geometry wheel-slot rule is written out in the structural parity topic of the vehicles pack (`vehicle-structural-parity.md` in the source pack, with SP-027) and it is one of the vehicle checks of `dayz-p3d-audit`.
