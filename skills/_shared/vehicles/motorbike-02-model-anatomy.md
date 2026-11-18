# Motorbike_02 model anatomy

What the binarized model of the vanilla `Motorbike_02` holds: model info, LODs, skeleton, every animation with its source, memory points, proxies and selections. `Motorbike_02_ColorBase` loads it from `P:\DZ\vehicles\singletrack\Motorbike_02\Motorbike_02.p3d` (`P:\DZ\vehicles\singletrack\config.cpp:1408`). The numbers were read with a binarized model reader and are not checked on `P:\`; how to read them, and what was checked, is in `motorbike-vanilla-p3d-anatomy.md`. The model file now on `P:\` is larger than the copy these tables were read from, so read it again before relying on a number.

Its rear suspension is a linkage: `damperback` drives `damper_2`, the swingarm, and in steps of the damper phase the `rocker_link`, `rocker`, `shock_bottoms` and `shock_tops` bones, each with eight animations that cover one band of the phase. The handlebar sweep is split over `drivewheel_0` to `drivewheel_9`, which turn from 4.5 up to 81 degrees at full lock while `drivewheel` itself turns 90.

## Model info

- Binarized model, ODOL version 56, 11 LODs.
- Mass 118.00 kg, armor 200.0, center of mass (-0.0000, 0.4480, -0.0375), geometry center (-0.0000, 0.7188, 0.0069), bounding box (-0.570, -0.000, -0.970) to (0.570, 1.285, 1.115), bounding sphere radius 1.343, geometry sphere radius 1.019.
- Aiming center (-0.000, 0.719, 0.007); inverse inertia diagonal (0.055, 0.058, 0.231); auto center `False`; can occlude `False`, can be occluded `True`; map type 22, special flags 768; property class `none`; LOD index of memory 8, geometry 7, fire geometry 10, view geometry 9.

## LODs

| LOD | Resolution | Kind | Points | Faces | Selections | Proxies | Textures | Materials | Bounding box | Named properties |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | Visual | 26371 | 17091 | 84 | 10 | 9 | 8 | (-0.42, -0.00, -0.90) to (0.43, 1.24, 1.07) | none |
| 1 | 2 | Visual | 13142 | 7656 | 74 | 8 | 9 | 8 | (-0.42, -0.00, -0.90) to (0.43, 1.24, 1.07) | none |
| 2 | 3 | Visual | 5666 | 3110 | 70 | 7 | 8 | 7 | (-0.42, -0.00, -0.90) to (0.43, 1.24, 1.06) | none |
| 3 | 4 | Visual | 2965 | 1507 | 61 | 7 | 8 | 7 | (-0.42, -0.00, -0.90) to (0.43, 1.22, 1.06) | none |
| 4 | 5 | Visual | 1659 | 879 | 53 | 7 | 8 | 7 | (-0.41, -0.00, -0.90) to (0.43, 1.22, 1.06) | none |
| 5 | 6 | Visual | 956 | 528 | 44 | 7 | 7 | 6 | (-0.41, -0.00, -0.89) to (0.42, 1.22, 1.06) | none |
| 6 | 7 | Visual | 414 | 206 | 30 | 7 | 4 | 3 | (-0.39, -0.00, -0.76) to (0.40, 1.21, 0.86) | none |
| 7 | 1e+13 | Geometry | 88 | 114 | 12 | 0 | 1 | 0 | (-0.39, 0.21, -0.78) to (0.39, 1.23, 0.80) | `autocenter` = `0` |
| 8 | 1e+15 | Memory | 93 | 0 | 54 | 0 | 0 | 0 | (-0.57, 0.00, -0.97) to (0.57, 1.23, 1.11) | none |
| 9 | 6e+15 | View Geometry | 948 | 1033 | 114 | 10 | 1 | 0 | (-0.41, -0.00, -0.96) to (0.41, 1.29, 1.07) | none |
| 10 | 7e+15 | Fire Geometry | 891 | 992 | 98 | 7 | 1 | 8 | (-0.41, -0.00, -0.90) to (0.41, 1.20, 1.07) | none |

## Skeleton (37 bones)

Each bone sits under its parent; a bone with no parent hangs from the model root.

| Parent | Bones |
|---|---|
| Model root | `drivewheel`, `seat`, `crewdriver`, `crewcodriver`, `kickstand`, `battery`, `reflector_1_1`, `engine`, `dial_fuel`, `seat_driver`, `drivewheel_0`, `drivewheel_1`, `drivewheel_2`, `drivewheel_3`, `drivewheel_4`, `drivewheel_5`, `drivewheel_6`, `drivewheel_7`, `drivewheel_8`, `drivewheel_9`, `damper_2`, `damper_2_2`, `damper_2_limited`, `damper_2_debug`, `damper_chain`, `damper_chain_2`, `rocker_link`, `shock_tops` |
| `drivewheel` | `dial_speed`, `dial_rpm`, `dial_temp`, `damper_1` |
| `damper_1` | `wheel_1` |
| `damper_2` | `wheel_2`, `damper_2_mudshield` |
| `rocker_link` | `rocker` |
| `rocker` | `shock_bottoms` |

## Animations (60)

| Animation | Type | Source | Value range | Phase | Angle or offset | Bones | Axis in LOD 0: position, direction |
|---|---|---|---|---|---|---|---|
| `TurnFront` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 90.0° to -90.0° | `drivewheel` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `IndicatorSpeed` | rotation | `speed` | 0.000 to 120.000 | 0.00 to 120.00 | -0.0° to -250.0° | `dial_speed` | (0.039, 1.137, -0.166) · (-0.000, -0.893, -0.451) |
| `IndicatorFuel` | rotation | `fuel` | 0.000 to 1.000 | 0.00 to 1.00 | 0.0° to -250.0° | `dial_fuel` | (-0.000, 1.098, -0.108) · (-0.000, -0.978, -0.208) |
| `IndicatorRPM` | rotation | `enginerpm` | 0.000 to 1.000 | 0.00 to 1.00 | 0.0° to -280.0° | `dial_rpm` | (-0.039, 1.137, -0.166) · (-0.000, -0.893, -0.451) |
| `IndicatorCoolant` | rotation | `coolant` | 0.000 to 1.000 | 0.00 to 1.00 | 0.0° to -135.0° | `dial_temp` | (-0.039, 1.130, -0.151) · (-0.000, -0.893, -0.451) |
| `wheel_1` | rotation | `wheelfront` | 0.000 to 6.283 | 0.00 to 6.28 | 0.0° to -360.0° | `wheel_1` | (-0.148, 0.301, -0.713) · (1.000, 0.000, 0.000) |
| `wheel_2` | rotation | `wheelback` | 0.000 to 6.283 | 0.00 to 6.28 | 0.0° to -360.0° | `wheel_2` | (-0.148, 0.301, 0.690) · (1.000, 0.000, 0.000) |
| `damper_2` | rotation | `damperback` | 0.000 to 1.000 | 0.00 to 1.00 | -20.0° to 30.0° | `damper_2` | (0.072, 0.451, 0.149) · (-1.000, 0.000, 0.000) |
| `damper_2_2` | rotation | `damperback` | 0.000 to 1.000 | 0.00 to 1.00 | -17.0° to 25.5° | `damper_2_2` | (0.072, 0.451, 0.149) · (-1.000, 0.000, 0.000) |
| `damper_2_limited` | rotation | `damperback` | 0.000 to 0.550 | 0.00 to 0.55 | -17.0° to 6.4° | `damper_2_limited` | (0.072, 0.451, 0.149) · (-1.000, 0.000, 0.000) |
| `rocker_link_1` | rotation | `damperback` | 0.000 to 0.100 | 0.00 to 0.10 | -16.9° to -13.4° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_2` | rotation | `damperback` | 0.100 to 0.250 | 0.10 to 0.25 | 0.0° to 6.3° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_3` | rotation | `damperback` | 0.250 to 0.400 | 0.25 to 0.40 | 0.0° to 7.1° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_4` | rotation | `damperback` | 0.400 to 0.500 | 0.40 to 0.50 | 0.0° to 5.0° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_5` | rotation | `damperback` | 0.500 to 0.600 | 0.50 to 0.60 | 0.0° to 5.2° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_6` | rotation | `damperback` | 0.600 to 0.750 | 0.60 to 0.75 | 0.0° to 8.0° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_7` | rotation | `damperback` | 0.750 to 0.900 | 0.75 to 0.90 | 0.0° to 8.3° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_8` | rotation | `damperback` | 0.900 to 1.000 | 0.90 to 1.00 | 0.0° to 5.7° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_1` | rotation | `damperback` | 0.000 to 0.100 | 0.00 to 0.10 | -33.8° to -24.6° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_2` | rotation | `damperback` | 0.100 to 0.250 | 0.10 to 0.25 | 0.0° to 12.7° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_3` | rotation | `damperback` | 0.250 to 0.400 | 0.25 to 0.40 | 0.0° to 11.6° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_4` | rotation | `damperback` | 0.400 to 0.500 | 0.40 to 0.50 | 0.0° to 7.9° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_5` | rotation | `damperback` | 0.500 to 0.600 | 0.50 to 0.60 | 0.0° to 7.7° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_6` | rotation | `damperback` | 0.600 to 0.750 | 0.60 to 0.75 | 0.0° to 11.6° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_7` | rotation | `damperback` | 0.750 to 0.900 | 0.75 to 0.90 | 0.0° to 12.0° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_8` | rotation | `damperback` | 0.900 to 1.000 | 0.90 to 1.00 | 0.0° to 8.4° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `shock_bottoms_1` | rotation | `damperback` | 0.000 to 0.100 | 0.00 to 0.10 | -19.1° to -13.1° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_2` | rotation | `damperback` | 0.100 to 0.250 | 0.10 to 0.25 | 0.0° to 7.3° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_3` | rotation | `damperback` | 0.250 to 0.400 | 0.25 to 0.40 | 0.0° to 5.7° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_4` | rotation | `damperback` | 0.400 to 0.500 | 0.40 to 0.50 | 0.0° to 3.4° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_5` | rotation | `damperback` | 0.500 to 0.600 | 0.50 to 0.60 | 0.0° to 3.2° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_6` | rotation | `damperback` | 0.600 to 0.750 | 0.60 to 0.75 | 0.0° to 4.4° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_7` | rotation | `damperback` | 0.750 to 0.900 | 0.75 to 0.90 | 0.0° to 4.2° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_8` | rotation | `damperback` | 0.900 to 1.000 | 0.90 to 1.00 | 0.0° to 2.7° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_tops_1` | rotation | `damperback` | 0.000 to 0.100 | 0.00 to 0.10 | -1.7° to -1.2° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_2` | rotation | `damperback` | 0.100 to 0.250 | 0.10 to 0.25 | 0.0° to 0.4° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_3` | rotation | `damperback` | 0.250 to 0.400 | 0.25 to 0.40 | 0.0° to 0.7° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_4` | rotation | `damperback` | 0.400 to 0.500 | 0.40 to 0.50 | 0.0° to 0.4° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_5` | rotation | `damperback` | 0.500 to 0.600 | 0.50 to 0.60 | 0.0° to 0.4° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_6` | rotation | `damperback` | 0.600 to 0.750 | 0.60 to 0.75 | 0.0° to 0.8° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_7` | rotation | `damperback` | 0.750 to 0.900 | 0.75 to 0.90 | 0.0° to 1.0° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_8` | rotation | `damperback` | 0.900 to 1.000 | 0.90 to 1.00 | 0.0° to 0.8° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `damper_2_debug` | translation | `damperback` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.187 to 0.313 | `damper_2_debug` | (0.000, 0.000, 0.000) · (0.000, 0.919, 0.010) |
| `Kickstand` | rotation | `kickstand` | 0.000 to 1.000 | 0.00 to 1.00 | -76.0° to -80.0° | `kickstand` | (-0.125, 0.367, 0.186) · (1.000, 0.000, 0.000) |
| `Kickstand_damper_Min` | rotation | `damperback` | 0.000 to 0.430 | 0.00 to 0.43 | 30.0° to 0.0° | `kickstand` | (-0.125, 0.367, 0.186) · (1.000, 0.000, 0.000) |
| `Kickstand_damper_Max` | rotation | `damperback` | 0.800 to 1.000 | 0.80 to 1.00 | 0.0° to -12.0° | `kickstand` | (-0.125, 0.367, 0.186) · (1.000, 0.000, 0.000) |
| `damper_2_mudshield` | rotation | `damperback` | 0.700 to 1.000 | 0.70 to 1.00 | 0.0° to -15.0° | `damper_2_mudshield` | (0.064, 0.419, 0.356) · (-1.000, -0.000, 0.000) |
| `damper_chain` | rotation | `damperback` | 0.000 to 1.000 | 0.00 to 1.00 | -15.0° to 25.0° | `damper_chain` | (0.120, 0.378, 0.196) · (-1.000, 0.000, 0.000) |
| `damper_chain_2` | rotation | `damperback` | 0.000 to 1.000 | 0.00 to 1.00 | 10.0° to -10.0° | `damper_chain_2` | (0.062, 0.439, 0.054) · (1.000, 0.000, 0.000) |
| `damper_1` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.010 to 0.250 | `damper_1` | (0.000, 0.000, 0.000) · (0.000, 0.949, 0.477) |
| `turnFront_0` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 4.5° to -4.5° | `drivewheel_0` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_1` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 9.0° to -9.0° | `drivewheel_1` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_2` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 18.0° to -18.0° | `drivewheel_2` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_3` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 27.0° to -27.0° | `drivewheel_3` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_4` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 36.0° to -36.0° | `drivewheel_4` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_5` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 45.0° to -45.0° | `drivewheel_5` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_6` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 54.0° to -54.0° | `drivewheel_6` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_7` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 63.0° to -63.0° | `drivewheel_7` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_8` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 72.0° to -72.0° | `drivewheel_8` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_9` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 81.0° to -81.0° | `drivewheel_9` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |

## Memory points (54 selections)

| Selection | Points |
|---|---|
| `axis_drivewheel` | (0.000, 0.847, -0.368) ; (0.000, 0.657, -0.464) |
| `axis_fuel` | (-0.000, 1.098, -0.108) ; (-0.000, 1.010, -0.126) |
| `axis_gearshift` | (0.091, 0.379, 0.054) ; (0.142, 0.379, 0.054) |
| `axis_kickstand` | (-0.125, 0.367, 0.186) ; (0.125, 0.367, 0.186) |
| `axis_kickstart` | (-0.152, 0.446, -0.090) ; (-0.125, 0.446, -0.090) |
| `axis_kickstart_arm` | (-0.143, 0.560, -0.091) ; (-0.144, 0.602, -0.092) |
| `axis_light` | (-0.000, 1.057, -0.363) ; (-0.000, 1.062, -0.318) |
| `axis_rpm` | (-0.039, 1.137, -0.166) ; (-0.039, 1.096, -0.187) |
| `axis_speed` | (0.039, 1.137, -0.166) ; (0.039, 1.096, -0.187) |
| `axis_suspension_rear` | (-0.380, 0.451, 0.149) ; (0.072, 0.451, 0.149) ; (-0.081, 0.451, 0.149) |
| `axis_temp` | (-0.039, 1.130, -0.151) ; (-0.039, 1.089, -0.172) |
| `camo` | (0.046, 0.369, 0.187) ; (-0.046, 0.369, 0.187) ; (0.064, 0.419, 0.356) ; (-0.078, 0.419, 0.356) |
| `chain_static` | (0.120, 0.378, 0.196) ; (0.059, 0.378, 0.196) ; (0.062, 0.439, 0.054) ; (0.095, 0.439, 0.054) |
| `damage` | (0.000, 0.675, -0.516) ; (0.000, 0.212, -0.732) ; (0.000, 1.160, -0.236) ; (0.000, 0.838, -0.275) |
| `damper_1_axis` | (0.000, 0.278, -0.655) ; (0.000, 1.227, -0.177) |
| `damper_2_axis` | (0.072, 0.451, 0.149) ; (-0.081, 0.451, 0.149) |
| `damper_2_debug_axis` | (0.000, 0.000, 0.689) ; (0.000, 0.919, 0.699) |
| `damper_2_mudshield_axis` | (0.064, 0.419, 0.356) ; (-0.078, 0.419, 0.356) |
| `damper_chain_2_axis` | (0.062, 0.439, 0.054) ; (0.095, 0.439, 0.054) |
| `damper_chain_axis` | (0.120, 0.378, 0.196) ; (0.059, 0.378, 0.196) |
| `dmgzone_back` | (0.000, 0.868, 0.555) ; (0.104, 0.823, 0.212) ; (-0.104, 0.823, 0.212) ; (0.000, 0.308, 0.670) |
| `dmgzone_chassis` | (-0.000, 0.966, -0.278) ; (-0.000, 0.390, -0.183) ; (-0.000, 0.394, 0.172) ; (-0.000, 0.967, 0.831) |
| `dmgzone_engine` | (-0.000, 0.622, -0.113) ; (0.000, 0.427, 0.000) |
| `dmgzone_exhaust` | (0.155, 0.709, 0.789) ; (-0.124, 0.617, -0.257) |
| `dmgzone_fenderfront` | (-0.000, 0.862, -0.775) ; (-0.000, 0.730, -0.340) |
| `dmgzone_fenderrear` | (-0.000, 0.797, 0.953) |
| `dmgzone_front` | (0.000, 0.675, -0.516) ; (0.000, 0.212, -0.732) ; (0.000, 1.160, -0.236) ; (0.000, 0.838, -0.275) |
| `dmgzone_frontwheel_1` | (0.000, 0.304, -0.970) |
| `dmgzone_fueltank` | (-0.000, 0.912, -0.119) |
| `dmgzone_lights_1_1` | (0.000, 1.000, -0.385) |
| `engine` | (-0.152, 0.446, -0.090) ; (-0.125, 0.446, -0.090) |
| `light_1_1` | (0.000, 1.002, -0.440) |
| `light_1_1_dir` | (0.000, 0.988, -0.666) |
| `light_1_2` | (0.001, 0.997, 0.844) |
| `light_1_2_reverse` | (0.001, 0.997, 0.844) |
| `pos_codriver` | (0.570, 0.190, 0.320) |
| `pos_codriver_dir` | (-0.000, 0.190, 0.320) |
| `pos_driver` | (-0.570, 0.190, 0.320) |
| `pos_driver_dir` | (0.000, 0.190, 0.320) |
| `ptcdustpos` | (0.000, 0.066, 1.026) |
| `ptcexhaust_end` | (0.151, 0.711, 1.115) |
| `ptcexhaust_start` | (0.151, 0.710, 0.652) |
| `refill` | (0.000, 1.058, -0.117) |
| `reflector_1_1` | (0.000, 0.989, -0.421) |
| `rocker_axis` | (-0.034, 0.333, 0.333) ; (0.045, 0.333, 0.333) |
| `rocker_link_axis` | (0.046, 0.369, 0.187) ; (-0.046, 0.369, 0.187) |
| `seat_driver` | (0.000, 0.890, 0.271) |
| `shock_bottoms_axis` | (0.042, 0.298, 0.265) ; (-0.047, 0.298, 0.265) |
| `shock_tops_axis` | (0.031, 0.673, 0.174) ; (-0.037, 0.673, 0.174) |
| `sparkplug` | (0.000, 0.709, -0.129) |
| `starter_lever` | (-0.152, 0.446, -0.090) ; (-0.125, 0.446, -0.090) |
| `wheel_1_axis` | (-0.148, 0.301, -0.713) ; (0.150, 0.301, -0.713) |
| `wheel_2_axis` | (-0.148, 0.301, 0.690) ; (0.150, 0.301, 0.690) |
| `zbytek` | (0.046, 0.369, 0.187) ; (-0.046, 0.369, 0.187) ; (0.064, 0.419, 0.356) ; (-0.078, 0.419, 0.356) |

## Proxies in LOD 0

| Proxy | Position | Rotation | Bone index |
|---|---|---|---|
| `\dz\vehicles\wheeled\proxies\crew_driver` | (0.000, 0.000, 0.071) | none | 7 |
| `\dz\vehicles\wheeled\proxies\crew_driver` | (0.000, 0.000, 0.071) | none | 8 |
| `\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_shieldleft` | (0.095, 0.603, 0.380) | none | none |
| `\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_shieldright` | (-0.095, 0.603, 0.380) | 180° about Y | none |
| `\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_wheel_1` | (0.000, 0.301, -0.712) | none | 5 |
| `\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_wheel_2` | (0.000, 0.301, 0.690) | none | 26 |
| `\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_windshield` | (0.000, 0.983, -0.380) | 94° about (-0.25, -0.94, -0.25) | 0 |
| `\dz\vehicles\parts\replacement_headlight` | (0.000, 0.997, -0.302) | 90° about X | 11 |
| `\dz\vehicles\parts\sparkplug` | (0.048, 0.704, -0.094) | 31° about (0.29, -0.08, 0.96) | not read |
| `\dz\vehicles\parts\sparkplug` | (-0.002, 0.685, -0.140) | 10° about (0.95, 0.03, -0.32) | not read |

## Selections in LOD 0

Faces per selection are in brackets. Each proxy also has a `proxy:` selection of one face, left out here; the proxy table lists them.

- Damage zones: `dmgzone_fenderfront` (557), `dmgzone_fenderrear` (336), `dmgzone_exhaust` (960), `dmgzone_engine` (2472), `dmgzone_fueltank` (906), `dmgzone_lights_1_1` (529), `dmgzone_front` (4645), `dmgzone_back` (2360), `dmgzone_chassis` (4316).
- Dampers: `damper_1` (770), `damper_2` (983), `damper_2_mudshield` (9), `damper_2_2` (0), `damper_chain` (0), `damper_2_limited` (33), `damper_chain_2` (0).
- Lights: `lights_front` (96), `lights_rear` (26), `lights_brake` (26).
- Other parts, `1111` to `clutchlever`: `1111` (312), `accelerator` (128), `brakelever` (78), `cables` (1390), `camo_exhaust` (960), `camo_fenderfront` (557), `camo_fenderrear` (336), `camo` (14139), `caphi` (10), `caplo` (17), `chain_static` (48), `chain_swing` (228), `clutch_arm` (58), `clutchlever` (78).
- Other parts, `crewcodriver` to `drivewheel_8`: `crewcodriver` (1), `crewdriver` (1), `dial_fuel` (12), `dial_rpm` (2), `dial_speed` (2), `drivewheel_0` (0), `drivewheel_1` (12), `drivewheel_2` (9), `drivewheel_3` (0), `drivewheel_4` (0), `drivewheel_5` (0), `drivewheel_6` (0), `drivewheel_7` (0), `drivewheel_8` (0).
- Other parts, `drivewheel_9` to `rear_brake`: `drivewheel_9` (0), `drivewheel` (4737), `front_brake_lever1` (59), `front_brake_lever_2` (26), `fusion surface` (902), `gearshift` (73), `headlamp_switch` (24), `kickstand` (142), `mirrorl` (748), `mirrorr` (685), `pistons_bottom` (172), `pistons_top` (418), `rear_brake_lever` (96), `rear_brake` (57).
- Other parts, `reflector_1_1` to `zbytek`: `reflector_1_1` (1), `rocker_link` (36), `rocker` (106), `shieldleft` (1), `shock_bottoms` (172), `shock_tops` (410), `starter_arm` (104), `starter_lever` (106), `suspension_arm` (710), `wall` (344), `wheel_1` (1), `wheel_2` (1), `zbytek` (16449).

## Geometry LOD

| Points | Faces | Selections |
|---|---|---|
| 16 | 15 | `wheel_2_damper_land`, `wheel_1_damper_land`, `component01`, `component02` |
| 8 | 12 | `component03` to `component09` |
| 24 | 36 | `geotohide` |

- Named properties: `autocenter` = `0`.

## View Geometry selections

- Damage zones: `dmgzone_fenderfront`, `dmgzone_fenderrear`, `dmgzone_exhaust`, `dmgzone_engine`, `dmgzone_fueltank`, `dmgzone_lights_1_1`, `dmgzone_front`, `dmgzone_back`, `dmgzone_chassis`.
- Components: `component01` to `component74`.
- Other: `1111`, `engine`, `mirrorl`, `steering`, `suspension_front`, `suspension_arm`, `fuel`, `shieldleft`, `wheel_2`, `wheel_1`, `crewdriver`, `seat_driver`, `refill`, `crewcodriver`, `sparkplug`, `motorbike_02_wheel_1`, `motorbike_02_wheel_2`, `reflector_1_1`, `motorbike_02_windshield`, `motorbike_02_shieldright`, `motorbike_02_shieldleft`, plus one `proxy:` selection per proxy.

## Fire Geometry selections

- Damage zones: `dmgzone_fenderfront`, `dmgzone_fenderrear`, `dmgzone_exhaust`, `dmgzone_engine`, `dmgzone_fueltank`, `dmgzone_lights_1_1`, `dmgzone_front`, `dmgzone_back`, `dmgzone_chassis`.
- Components: `component01` to `component68`.
- Other: `1111`, `engine`, `mirrorl`, `steering`, `suspension_front`, `suspension_arm`, `fuel`, `shieldleft`, `wheel_2`, `wheel_1`, `crewdriver`, `seat_driver`, `reflector_1_1`, `crewcodriver`, plus one `proxy:` selection per proxy.

## Textures and materials in LOD 0

Files under `dz\vehicles\singletrack\motorbike_02\data\` are named without the folder.

- Textures: `motorbike_02_body_red_co.paa`, `motorbike_02_wheel_co.paa`, `#(argb,8,8,3)color(0.000,0.000,0.000,0.100,ca)`, `motorbike_02_lights_co.paa`, `motorbike_02_lights_e_co.paa`, `motorbike_02_exhaust_co.paa`, `motorbike_02_fenderfront_co.paa`, `motorbike_02_fenderrear_co.paa`.
- Materials: `motorbike_02_wheel.rvmat`, `motorbike_02_body.rvmat`, `motorbike_02_glass.rvmat`, `motorbike_02_fenderrear.rvmat`, `motorbike_02_lights_rear_brake.rvmat`, `motorbike_02_exhaust.rvmat`, `motorbike_02_fenderfront.rvmat`, `motorbike_02_lights_nolight.rvmat`.
