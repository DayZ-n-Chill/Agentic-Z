# Motorbike_01 model anatomy

What the binarized model of the vanilla `Motorbike_01` holds: model info, LODs, skeleton, every animation with its source, memory points, proxies and selections. `Motorbike_01_ColorBase` loads it from `P:\DZ\vehicles\singletrack\Motorbike_01\Motorbike_01.p3d` (`P:\DZ\vehicles\singletrack\config.cpp:224`). The numbers were read with a binarized model reader and are not checked on `P:\`; how to read them, and what was checked, is in `motorbike-vanilla-p3d-anatomy.md`. The model file now on `P:\` is larger than the copy these tables were read from, so read it again before relying on a number.

## Model info

- Binarized model, ODOL version 56, 9 LODs.
- Mass 85.00 kg, armor 200.0, center of mass (-0.0000, 0.2763, -0.0459), geometry center (0.0000, 0.5099, 0.0506), bounding box (-0.600, -0.014, -2.481) to (0.600, 2.270, 0.993), bounding sphere radius 2.599, geometry sphere radius 0.908.
- Aiming center (0.000, 0.510, 0.051); inverse inertia diagonal (0.052, 0.054, 0.527); auto center `False`; can occlude `False`, can be occluded `True`; map type 22, special flags 768; property class `vehicle`; LOD index of memory 6, geometry 5, fire geometry 8, view geometry 7.

## LODs

| LOD | Resolution | Kind | Points | Faces | Selections | Proxies | Textures | Materials | Bounding box | Named properties |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | Visual | 28703 | 33692 | 52 | 7 | 8 | 8 | (-0.32, -0.01, -2.48) to (0.35, 2.27, 0.89) | none |
| 1 | 2 | Visual | 16638 | 16429 | 51 | 7 | 8 | 7 | (-0.32, -0.01, -2.48) to (0.35, 2.27, 0.89) | none |
| 2 | 3 | Visual | 8158 | 6791 | 37 | 7 | 8 | 7 | (-0.32, -0.01, -2.48) to (0.34, 2.27, 0.89) | none |
| 3 | 4 | Visual | 3913 | 3155 | 34 | 7 | 8 | 7 | (-0.31, -0.01, -2.48) to (0.34, 2.27, 0.88) | none |
| 4 | 5 | Visual | 1275 | 832 | 32 | 7 | 7 | 6 | (-0.31, -0.01, -2.48) to (0.34, 2.27, 0.88) | none |
| 5 | 1e+13 | Geometry | 108 | 96 | 14 | 0 | 1 | 0 | (-0.10, 0.17, -0.79) to (0.10, 0.85, 0.89) | `autocenter` = `0`, `class` = `vehicle`, `lodnoshadow` = `1` |
| 6 | 1e+15 | Memory | 92 | 0 | 30 | 0 | 0 | 0 | (-0.60, 0.00, -0.79) to (0.60, 1.04, 0.99) | none |
| 7 | 6e+15 | View Geometry | 433 | 671 | 62 | 7 | 1 | 0 | (-0.31, -0.00, -2.48) to (0.35, 2.27, 0.89) | `autocenter` = `0`, `lodnoshadow` = `1` |
| 8 | 7e+15 | Fire Geometry | 405 | 639 | 54 | 7 | 1 | 2 | (-0.31, -0.00, -2.48) to (0.35, 2.27, 0.89) | `autocenter` = `0`, `lodnoshadow` = `1` |

## Skeleton (35 bones)

Each bone sits under its parent; a bone with no parent hangs from the model root.

| Parent | Bones |
|---|---|
| Model root | `drivewheel`, `seat`, `crewdriver`, `crewcodriver`, `kickstand`, `battery`, `reflector_1_1`, `engine`, `seat_driver`, `damper_2`, `damper_2_debug`, `lights_brake`, `lights_rear` |
| `drivewheel` | `dial_speed`, `damper_1`, `damper_1_1`, `damper_1_2`, `damper_1_3`, `damper_1_4`, `damper_1_5`, `damper_1_6`, `damper_1_7`, `damper_1_8`, `damper_1_9`, `damper_1_10`, `damper_1_11`, `damper_1_12`, `damper_1_13`, `damper_1_14`, `damper_1_15`, `damper_1_16`, `damper_1_17`, `lights_front` |
| `damper_1` | `wheel_1` |
| `damper_2` | `wheel_2` |

## Animations (44)

| Animation | Type | Source | Value range | Phase | Angle or offset | Bones | Axis in LOD 0: position, direction |
|---|---|---|---|---|---|---|---|
| `Kickstand` | rotation | `kickstand` | 0.000 to 1.000 | 0.00 to 1.00 | -76.0° to 0.0° | `kickstand` | (0.010, 0.212, 0.053) · (-1.000, 0.000, 0.000) |
| `TurnFront` | rotation | `turnfront` | -1.571 to 1.571 | -1.57 to 1.57 | 90.0° to -90.0° | `drivewheel` | (-0.000, 0.937, -0.280) · (0.000, -0.882, -0.472) |
| `SeatAnim` | rotation | `seatdriver` | 0.000 to 1.000 | 0.00 to 1.00 | 0.0° to 110.0° | `seat_driver` | (0.020, 0.656, 0.080) · (-1.000, 0.000, 0.000) |
| `IndicatorSpeed` | rotation | `speed` | 0.000 to 80.000 | 0.00 to 80.00 | -145.0° to 145.0° | `dial_speed` | (0.000, 0.863, -0.424) · (0.000, 0.976, 0.217) |
| `wheel_1` | rotation | `wheelfront` | 0.000 to 6.283 | 0.00 to 6.28 | 0.0° to -360.0° | `wheel_1` | (0.002, 0.270, -0.672) · (1.000, 0.000, 0.000) |
| `wheel_2` | rotation | `wheelback` | 0.000 to 6.283 | 0.00 to 6.28 | 0.0° to -360.0° | `wheel_2` | (0.002, 0.270, 0.544) · (1.000, 0.000, 0.000) |
| `damper_2` | rotation | `damperback` | 0.000 to 1.000 | 0.00 to 1.00 | -6.9° to 9.2° | `damper_2` | (0.125, 0.305, 0.172) · (-1.000, 0.000, -0.000) |
| `damper_1` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.066 to 0.066 | `damper_1` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_1` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.004 to 0.004 | `damper_1_1` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_2` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.008 to 0.008 | `damper_1_2` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_3` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.012 to 0.012 | `damper_1_3` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_4` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.016 to 0.016 | `damper_1_4` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_5` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.019 to 0.019 | `damper_1_5` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_6` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.023 to 0.023 | `damper_1_6` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_7` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.027 to 0.027 | `damper_1_7` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_8` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.031 to 0.031 | `damper_1_8` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_9` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.035 to 0.035 | `damper_1_9` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_10` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.039 to 0.039 | `damper_1_10` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_11` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.043 to 0.043 | `damper_1_11` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_12` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.047 to 0.047 | `damper_1_12` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_13` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.050 to 0.050 | `damper_1_13` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_14` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.054 to 0.054 | `damper_1_14` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_15` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.058 to 0.058 | `damper_1_15` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_16` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.062 to 0.062 | `damper_1_16` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_17` | translation | `damperfront` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.066 to 0.066 | `damper_1_17` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.015 | `damper_1` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_1` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.001 | `damper_1_1` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_2` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.002 | `damper_1_2` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_3` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.003 | `damper_1_3` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_4` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.004 | `damper_1_4` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_5` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.004 | `damper_1_5` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_6` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.005 | `damper_1_6` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_7` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.006 | `damper_1_7` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_8` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.007 | `damper_1_8` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_9` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.008 | `damper_1_9` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_10` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.009 | `damper_1_10` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_11` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.010 | `damper_1_11` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_12` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.011 | `damper_1_12` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_13` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.011 | `damper_1_13` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_14` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.012 | `damper_1_14` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_15` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.013 | `damper_1_15` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_16` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.014 | `damper_1_16` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_17` | translation | `turnfront` | 0.000 to 1.396 | 0.00 to 1.40 | off 0.000 to -0.015 | `damper_1_17` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_2_debug` | translation | `damperback` | 0.000 to 1.000 | 0.00 to 1.00 | off -0.043 to 0.058 | `damper_2_debug` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.000) |

## Memory points (30 selections)

| Selection | Points |
|---|---|
| `axis_drivewheel` | (-0.000, 0.937, -0.280) ; (-0.000, 0.837, -0.334) ; (-0.000, 0.937, -0.280) ; (-0.000, 0.837, -0.334) |
| `axis_kickstand` | (0.010, 0.212, 0.053) ; (-0.010, 0.212, 0.053) ; (0.010, 0.212, 0.053) ; (-0.010, 0.212, 0.053) |
| `axis_seat` | (0.020, 0.656, 0.080) ; (-0.020, 0.656, 0.080) ; (0.020, 0.656, 0.080) ; (-0.020, 0.656, 0.080) |
| `axis_speed` | (0.000, 0.863, -0.424) ; (0.000, 0.867, -0.423) ; (0.000, 0.863, -0.424) ; (0.000, 0.867, -0.423) |
| `damper_1_axis` | (-0.000, 0.041, -0.779) ; (0.000, 1.041, -0.313) ; (-0.000, 0.041, -0.779) ; (0.000, 1.041, -0.313) |
| `damper_2_axis` | (0.125, 0.305, 0.172) ; (-0.125, 0.305, 0.172) ; (0.125, 0.305, 0.172) ; (-0.125, 0.305, 0.172) |
| `damper_debug_axis` | (0.000, 0.000, 0.543) ; (0.000, 1.000, 0.543) ; (0.000, 0.000, 0.543) ; (0.000, 1.000, 0.543) |
| `dial_speed` | (0.000, 0.863, -0.424) ; (0.000, 0.867, -0.423) ; (0.000, 0.863, -0.424) ; (0.000, 0.867, -0.423) |
| `dmgzone_back` | (0.000, 0.447, 0.876) ; (0.111, 0.655, 0.156) ; (-0.111, 0.655, 0.156) ; (0.111, 0.332, 0.263) … |
| `dmgzone_chassis` | (0.183, 0.205, -0.105) ; (0.183, 0.205, 0.282) ; (0.183, 0.691, -0.363) ; (-0.187, 0.205, -0.105) … |
| `dmgzone_engine` | (-0.000, 0.287, -0.178) ; (0.000, 0.277, -0.018) ; (-0.000, 0.287, -0.178) ; (0.000, 0.277, -0.018) |
| `dmgzone_fender` | (-0.001, 0.604, -0.737) ; (-0.001, 0.278, -0.349) |
| `dmgzone_front` | (-0.000, 0.575, -0.531) ; (0.000, 0.272, -0.663) ; (0.000, 0.935, -0.336) ; (-0.000, 0.575, -0.531) … |
| `dmgzone_fueltank` | (-0.050, 0.583, 0.223) |
| `dmgzone_lights_1_1` | (0.000, 0.785, -0.542) ; (0.000, 0.785, -0.542) |
| `light_1_1` | (0.000, 0.778, -0.588) ; (0.000, 0.778, -0.588) |
| `light_1_1_dir` | (0.000, 0.749, -0.787) ; (0.000, 0.749, -0.787) |
| `light_1_2_reverse` | (0.001, 0.574, 0.882) |
| `pos_codriver` | (0.600, 0.200, 0.337) ; (0.600, 0.200, 0.337) |
| `pos_codriver_dir` | (0.000, 0.200, 0.337) ; (0.000, 0.200, 0.337) |
| `pos_driver` | (-0.600, 0.200, 0.337) ; (-0.600, 0.200, 0.337) |
| `pos_driver_dir` | (0.000, 0.200, 0.337) ; (0.000, 0.200, 0.337) |
| `ptcdustpos` | (0.000, 0.085, 0.929) ; (0.000, 0.085, 0.929) |
| `ptcexhaust_end` | (0.126, 0.144, 0.993) |
| `ptcexhaust_start` | (0.126, 0.147, 0.653) |
| `refill` | (-0.050, 0.666, 0.168) |
| `reflector_1_1` | (0.000, 0.778, -0.528) ; (0.000, 0.778, -0.528) |
| `seat_driver` | (0.000, 0.730, 0.293) |
| `wheel_1_axis` | (0.002, 0.270, -0.672) ; (0.050, 0.270, -0.672) ; (0.002, 0.270, -0.672) ; (0.050, 0.270, -0.672) |
| `wheel_2_axis` | (0.002, 0.270, 0.544) ; (0.050, 0.270, 0.544) ; (0.002, 0.270, 0.544) ; (0.050, 0.270, 0.544) |

## Proxies in LOD 0

| Proxy | Position | Rotation | Bone index |
|---|---|---|---|
| `\dz\vehicles\wheeled\proxies\crew_driver` | (0.000, 0.000, 0.038) | none | 23 |
| `\dz\vehicles\wheeled\proxies\crew_driver` | (0.000, 0.000, 0.038) | none | 24 |
| `\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_exhaust` | (0.000, 0.185, 0.334) | 180° about Y | none |
| `\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_wheel_1` | (0.000, 0.270, -0.673) | none | 3 |
| `\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_wheel_2` | (0.000, 0.270, 0.544) | 180° about Y | 31 |
| `\dz\vehicles\parts\replacement_headlight` | (0.000, 0.780, -0.481) | 90° about X | not read |
| `\dz\vehicles\parts\sparkplug` | (0.000, 0.309, -0.253) | 72° about X | not read |

## Selections in LOD 0

Faces per selection are in brackets. Each proxy also has a `proxy:` selection of one face, left out here; the proxy table lists them.

- Damage zones: `dmgzone_chassis` (6820), `dmgzone_engine` (3100), `dmgzone_fueltank` (912), `dmgzone_lights_1_1` (3319), `dmgzone_front` (6671), `dmgzone_back` (10657), `dmgzone_fender` (2206).
- Dampers, `damper_1_10` to `damper_1_6`: `damper_1_10` (0), `damper_1_11` (0), `damper_1_12` (0), `damper_1_13` (0), `damper_1_14` (0), `damper_1_15` (0), `damper_1_16` (0), `damper_1_17` (0), `damper_1_1` (0), `damper_1_2` (0), `damper_1_3` (0), `damper_1_4` (0), `damper_1_5` (0), `damper_1_6` (0).
- Dampers, `damper_1_7` to `damper_2`: `damper_1_7` (0), `damper_1_8` (0), `damper_1_9` (0), `damper_1` (1302), `damper_2` (2780).
- Lights: `lights_brake` (452), `lights_rear` (452), `lights_front` (216).
- Other parts, `* cannot generate st coordinates` to `seat_driver`: `* cannot generate st coordinates` (23), `\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_fender` (2206), `brakelever` (266), `brakepedal` (104), `camo1` (8135), `camo_fender` (2206), `clutchlever` (266), `crewcodriver` (1), `crewdriver` (1), `dial_speed` (49), `drivewheel` (9618), `fender` (2206), `kickstand` (152), `seat_driver` (2035).
- Other parts, `wheel_1` to `wheel_2`: `wheel_1` (1), `wheel_2` (1).

## Geometry LOD

| Points | Faces | Selections |
|---|---|---|
| 8 | 6 | `component01`, `component02`, `component08` to `component11` |
| 10 | 11 | `component03`, `component06` |
| 16 | 15 | `component04`, `component05` |
| 16 | 0 | `wheel_2_damper_land`, `wheel_1_damper_land` |
| 8 | 8 | `component07` |
| 40 | 32 | `geotohide` |

- Named properties: `autocenter` = `0`, `class` = `vehicle`, `lodnoshadow` = `1`.

## View Geometry selections

- Damage zones: `dmgzone_chassis`, `dmgzone_engine`, `dmgzone_fueltank`, `dmgzone_lights_1_1`, `dmgzone_front`, `dmgzone_back`, `dmgzone_fender`.
- Components: `component01` to `component35`.
- Other: `seat_driver`, `drivewheel`, `damper_2`, `crewdriver`, `wheel_1`, `wheel_2`, `refill`, `motorbike_01_wheel_1`, `motorbike_01_wheel_2`, `* cannot generate st coordinates`, `crewcodriver`, `sparkplug`, `reflector_1_1`, plus one `proxy:` selection per proxy.

## Fire Geometry selections

- Damage zones: `dmgzone_chassis`, `dmgzone_engine`, `dmgzone_fueltank`, `dmgzone_lights_1_1`, `dmgzone_front`, `dmgzone_back`, `dmgzone_fender`.
- Components: `component01` to `component32`.
- Other: `seat_driver`, `drivewheel`, `damper_2`, `crewdriver`, `wheel_1`, `wheel_2`, `* cannot generate st coordinates`, `crewcodriver`, plus one `proxy:` selection per proxy.

## Textures and materials in LOD 0

Files under `dz\vehicles\singletrack\motorbike_01\data\` are named without the folder.

- Textures: `motorbike_01_colorized_blue_co.paa`, `motorbike_01_noncolorized_co.paa`, `motorbike_01_wheel_co.paa`, `motorbike_01_lights_co.paa`, `motorbike_01_glass_ca.paa`, `motorbike_01_lights_e.paa`, `motorbike_01_fender_blue_co.paa`.
- Materials: `motorbike_01_noncolorized.rvmat`, `motorbike_01_colorized.rvmat`, `motorbike_01_wheel.rvmat`, `motorbike_01_lights_nolight.rvmat`, `motorbike_01_lights.rvmat`, `motorbike_01_glass.rvmat`, `motorbike_01_lights_rear_brake.rvmat`, `motorbike_01_fender.rvmat`.
