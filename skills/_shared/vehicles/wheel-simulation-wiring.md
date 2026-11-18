# Wheel simulation wiring

What it looks like when a car's wheels are attached but do not simulate, which model property is only parity, and which wiring actually decides it.

## The symptom

`WheelCountPresent()` returns 0 while `WheelCount()` returns 4. There is no traction and no wheel spin, the body sinks or bounces, and the RPT shows no error. The vanilla comments say `WheelCount` is "How many wheel can be attached to a car (hubs only)" and `WheelCountPresent` is the "Number of actually attached wheels (hubs only)" (`P:\scripts\3_game\vehicles\car.c:344` to `:348`).

## Parity against the real cause

| Item | Role | Notes |
|---|---|---|
| Named property `class=vehicle` on the Geometry LOD | Parity, not the cause | All six vanilla wheeled vehicles checked carry it (**model knowledge**: a named property in a binarized `.p3d`, so no line to cite). Add it, it costs nothing; on its own it left the wheels unsimulated on a test vehicle in game. |
| The `selection` of the wheel slot in `CfgSlots` against the selection of the same name in the Fire Geometry LOD | The cause | Vanilla gives each wheel slot the model selection it shows: `Slot_CivSedanWheel_1_1` has `selection="wheel_1_1"` (`P:\scripts\config.cpp:1089` to `:1093`). |

Both produce the same symptom, so check the slot wiring first. The slot chain for one attachment is in `attachments-and-crew.md`, and the Fire Geometry wheel slot rule is written out in `vehicle-structural-parity.md`. `/dayz-p3d-audit` checks it offline.
