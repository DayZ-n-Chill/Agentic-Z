# Motorbike_02 model anatomy

What the binarized model of the vanilla `Motorbike_02` holds: model info, LODs, skeleton, every animation with its source. Memory points, proxies and selections are in `motorbike-02-model-selections.md`. `Motorbike_02_ColorBase` loads it from `P:\DZ\vehicles\singletrack\Motorbike_02\Motorbike_02.p3d` (`P:\DZ\vehicles\singletrack\config.cpp:1408`). The numbers were read with a binarized model reader and are not checked on `P:\`; how to read them, and what was checked, is in `motorbike-vanilla-p3d-anatomy.md`. The model file now on `P:\` is larger than the copy these tables were read from, so read it again before relying on a number.

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
