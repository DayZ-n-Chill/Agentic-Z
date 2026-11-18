# What a plane model contains

Which memory points, skeleton bones and selections a scripted plane's `.p3d` and `model.cfg` need, and how the dashboard switches its lit material.

The names come from LM_Planes (Workshop `3730564764`), read from its models and configs; they are that mod's conventions, not vanilla, and the script that reads them is in `aviation-fixed-wing.md`. The one vanilla anchor is the memory point check the script relies on: `MemoryPointExists` (`P:\scripts\3_game\entities\object.c:454`).

## Memory points

The script reads each point with `GetMemoryPointSafe(name, fallback)`, which returns the fallback position when the point is missing, so a missing point does not break the script but silently uses the fallback.

| Memory point | Used for |
|---|---|
| `axis_back`, `axis_front`, `axis_left`, `axis_right`, `axis_floor`, `axis_roof` | Direction vectors of the airframe |
| `axis_elevator_left`, `axis_elevator_right` | Elevator hinges, for the moment arm |
| `axis_flap_left`, `axis_flap_right` | Aileron hinges |
| `axis_rudder` | Rudder hinge |
| `axis_thruster` | Where the engine's thrust is applied |
| `wing_left`, `wing_right` | Wing tips, for the span and as a fallback for the navigation lights |
| `light_wing_left`, `light_wing_right`, `light_wing_tail` | Navigation lights: red, green and white (`aviation-effects-and-lights.md`) |
| `pos_driver`, `pos_codriver`, `pos_cargo1` to `pos_cargo3`, each with a `_dir` point | Where each crew member gets in, and which way they face |
| `dmgZone_*` | Centres of the damage zones in the `DamageSystem` |

The Catalina adds `light_left`, `light_right`, `light_1_1`, `light_2_1`, `light_dashboard` and `light_reverse` for its exterior lights. A seaplane also needs the four spray points in `aviation-seaplanes.md`.

## Skeleton bones

The bones go in `CfgSkeletons.<Aircraft>_skeleton.skeletonBones[]`, with no parent except along the wheel chain. The animation classes that drive them are in `aviation-animation-and-modelcfg.md`.

| Group | Bones |
|---|---|
| Flight controls, set from script | `elevator_1_1`, `elevator_2_1`, `aileron_1_1`, `aileron_2_1`, `rudder_1_1`, `gear_1_1` (gear retraction) |
| Propeller | `rotor_1_1` and `rotor_center`; `rotor_1_1_blur` for the blurred propeller. A second engine is `rotor_1_2` and `rotor_center2` on the DC-3, `rotor_2_1` and `rotor_center_2` on the Catalina |
| Dials set from script | `dial_compass`, `dial_horizon_bank`, `dial_horizon_pitch`, `dial_altitude`, `dial_volt` |
| Dials driven by the engine | `dial_rpm`, `dial_fuel`, `dial_temp`, `dial_speed` |
| Other | `engine`, `radiator`, `refill`; the yokes `drivewheel`, `drivewheel_1`, `drivewheel_2`; `crewdriver`, `crewcodriver`, `seat_driver`, `seat_codriver`, `seat_cargo1` to `seat_cargo3` |

`propeller` is a selection, not the rotor bone.

The wheel chain is parented: `damper_susp_X_Y` at the top with no parent, then `damper_X_Y`, then `wheel_X_Y`, then `wheel_X_Y_steering`. The tail wheel is simpler: `damper_2_2` has no `damper_susp` parent.

## Dashboard lit and unlit

The dashboard swaps between two materials that differ in two lines only:

| Line | `Controls.rvmat`, lights off | `Controls_on.rvmat`, lights on |
|---|---|---|
| `forcedDiffuse` | `{0,0,0,1}` | `{0.1,0.1,0.1,1}` |
| `Stage5` texture | `controls_SMDI` | `controls_on_SMDI` |

Everything else is the same. Aircraft share these materials across models: the Catalina's model points at `LM_Tigermoth/data/Controls.rvmat`, as the strings in its binarized `.p3d` show. The general rule for a lit material is in `emissive-led-materials.md`.
