# Model anatomy of the vanilla 1.30 motorbikes (`Motorbike_01`, `Motorbike_02`)

What the binary models `P:\DZ\vehicles\singletrack\motorbike_01\motorbike_01.p3d` and `P:\DZ\vehicles\singletrack\motorbike_02\motorbike_02.p3d` hold: mass and centre of mass, LODs, skeleton, every animation with its source, memory points, proxies, selections and named properties. It is the parity reference for a new motorbike: what the vanilla engine, config and script find in the model.

> **Where the numbers come from.** The tables were generated on 2026-09-19 from JSON dumps of an ODOL reader patched to read version 56, with no hand-typed numbers. The reader and its extraction script are not in this repo, so the tables are tool output that is not yet checked on `P:\`: treat them as leads. What was checked here: the two files on `P:\` have the byte sizes the dumps record (2302438 and 1895327), both start with the `ODOL` signature and version 56, and the names `drivewheel`, `damper_1`, `kickstand`, `geotohide`, `pos_driver`, `light_1_1` and `refill` are present in `motorbike_01.p3d` as text.
>
> **Status: `parsed`.** Checks run on the reader, none of them repeated here: (a) the same `OffroadHatchback.p3d` read as version 54 (1.29) and version 56 (1.30) gives 20,602 identical numbers: named points, skeleton, proxies, selections, animations, mass and centre of mass; (b) the first and second runs of the parser agree on 365 of 367 digest lines (the other 2 are `NaN` to `null` fields); (c) an independent review rejected the first version of the reader patch as a general component but found the anatomy of the six motorbike models internally consistent, and the second version passes a gate with strict JSON, a closed failure on corrupted input, a content fingerprint per LOD, a check of the end of each LOD and a discriminating skinning test. Not verified: nothing here has been cross-checked in game or against Bohemia's source `model.cfg` (not distributed), and the review of the second version was still pending when the note was written. The meaning of the two new ModelInfo fields in version 56 is unknown (they are 0 in every model read).
>
> **How to read it.** Metres; model axes exactly as in the binary (X lateral, Y vertical, Z longitudinal). In these files the front of the motorbike is at negative Z: the headlight proxy `replacement_headlight` is in negative Z and the exhaust in positive Z. Angles are in degrees. The ModelInfo bounding box is larger than the mesh (it includes proxies and animation); for dimensions use the bounding box of each LOD.
>
> **Headlines.** `Motorbike_01`: 85 kg, centre of mass y = 0.276 m, wheelbase 1.217 m (wheel proxies at Z = −0.673 and +0.544), 5 visual LODs from 33,692 down to 832 faces, 35 bones, 44 animations. `Motorbike_02`: 118 kg, centre of mass y = 0.448 m, wheelbase 1.402 m (Z = −0.712 and +0.690), 7 visual LODs from 17,091 down to 206 faces, 37 bones, 60 animations. Neither has a shadow LOD, a ViewPilot LOD or a LandContact LOD; on `Motorbike_01` the Geometry, View and Fire LODs carry `autocenter=0` and `lodnoshadow=1` (on `Motorbike_02` only the Geometry LOD carries `autocenter=0`, see its LOD table). The crew uses the proxy `\dz\vehicles\wheeled\proxies\crew_driver` twice, at the model origin.

## Motorbike_01

- ODOL 56 (layout used by the reader: 54), 2302438 bytes, 9 LOD, animation parsing mode: `canonical_flag_animations`, errors per LOD: none.
- **ModelInfo**: mass **85.00 kg**, armor 200.0, center of mass (-0.0000, 0.2763, -0.0459), geometry_center (0.0000, 0.5099, 0.0506), bbox (-0.600, -0.014, -2.481) → (0.600, 2.270, 0.993), sphere 2.599 / geometry 0.908.
- Rest of ModelInfo: `bounding_center`=(0.000, 0.000, 0.000); `aiming_center`=(0.000, 0.510, 0.051); `bbox_min_visual`=(-0.600, -0.014, -2.481); `bbox_max_visual`=(0.600, 2.270, 0.993); `inv_inertia`=[[0.05234566330909729, -4.1324428323719076e-09, 1.3263715459288505e-07], [-4.1324428323719076e-09, 0.05367742478847504, -0.0067481533624231815], [1.3263715459288505e-07, -0.0067481533624231815, 0.5272793769836426]]; `auto_center`=False; `lock_auto_center`=False; `can_occlude`=False; `can_be_occluded`=True; `allow_animation`=True; `force_not_alpha`=0; `shadow_buffer_source`=0; `prefer_shadow_volume`=False; `shadow_offset`=None; `disable_cover`=True; `animated`=False; `map_type`=22; `special`=768; `remarks`=0; `and_hints`=0; `or_hints`=0; `view_density`=-10.0; `map_icon_color`=4291407795; `map_selected_color`=4290409330; `can_blend`=False; `property_class`=vehicle; `property_damage`=; `property_frequent`=False; `mass_array_n`=0; `lod_index_memory`=6; `lod_index_geometry`=5; `lod_index_fire_geometry`=8; `lod_index_view_geometry`=7; `lod_index_bytes_raw`=[255, 255, 255, 255, 255, 255, 255, 255, 255]; `min_shadow_u32`=4; `geometry_simple`=None; `geometry_phys`=None; `v56_after_shadow_buffer_source`=0; `v56_before_animations`=0; `ht_min`=1.0; `ht_max`=0.0; `af_max`=0.0; `mf_max`=0.0; `m_fact`=0.0; `t_body`=0.0

### LODs

| # | resolution | kind | points | faces | selections | proxies | textures | materials | bbox | named properties |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | visual | 28703 | 33692 | 52 | 7 | 8 | 8 | (-0.32, -0.01, -2.48) → (0.35, 2.27, 0.89) | {} |
| 1 | 2 | visual | 16638 | 16429 | 51 | 7 | 8 | 7 | (-0.32, -0.01, -2.48) → (0.35, 2.27, 0.89) | {} |
| 2 | 3 | visual | 8158 | 6791 | 37 | 7 | 8 | 7 | (-0.32, -0.01, -2.48) → (0.34, 2.27, 0.89) | {} |
| 3 | 4 | visual | 3913 | 3155 | 34 | 7 | 8 | 7 | (-0.31, -0.01, -2.48) → (0.34, 2.27, 0.88) | {} |
| 4 | 5 | visual | 1275 | 832 | 32 | 7 | 7 | 6 | (-0.31, -0.01, -2.48) → (0.34, 2.27, 0.88) | {} |
| 5 | 1e+13 | geometry | 108 | 96 | 14 | 0 | 1 | 0 | (-0.10, 0.17, -0.79) → (0.10, 0.85, 0.89) | {"autocenter": "0", "class": "vehicle", "lodnoshadow": "1"} |
| 6 | 1e+15 | memory | 92 | 0 | 30 | 0 | 0 | 0 | (-0.60, 0.00, -0.79) → (0.60, 1.04, 0.99) | {} |
| 7 | 6e+15 | view_geometry | 433 | 671 | 62 | 7 | 1 | 0 | (-0.31, -0.00, -2.48) → (0.35, 2.27, 0.89) | {"autocenter": "0", "lodnoshadow": "1"} |
| 8 | 7e+15 | fire_geometry | 405 | 639 | 54 | 7 | 1 | 2 | (-0.31, -0.00, -2.48) → (0.35, 2.27, 0.89) | {"autocenter": "0", "lodnoshadow": "1"} |

### Skeleton `Motorbike_01` (35 bones; is_discrete=True)

`drivewheel`←`∅`, `dial_speed`←`drivewheel`, `damper_1`←`drivewheel`, `wheel_1`←`damper_1`, `damper_1_1`←`drivewheel`, `damper_1_2`←`drivewheel`, `damper_1_3`←`drivewheel`, `damper_1_4`←`drivewheel`, `damper_1_5`←`drivewheel`, `damper_1_6`←`drivewheel`, `damper_1_7`←`drivewheel`, `damper_1_8`←`drivewheel`, `damper_1_9`←`drivewheel`, `damper_1_10`←`drivewheel`, `damper_1_11`←`drivewheel`, `damper_1_12`←`drivewheel`, `damper_1_13`←`drivewheel`, `damper_1_14`←`drivewheel`, `damper_1_15`←`drivewheel`, `damper_1_16`←`drivewheel`, `damper_1_17`←`drivewheel`, `lights_front`←`drivewheel`, `seat`←`∅`, `crewdriver`←`∅`, `crewcodriver`←`∅`, `kickstand`←`∅`, `battery`←`∅`, `reflector_1_1`←`∅`, `engine`←`∅`, `seat_driver`←`∅`, `damper_2`←`∅`, `wheel_2`←`damper_2`, `damper_2_debug`←`∅`, `lights_brake`←`∅`, `lights_rear`←`∅`

### Animations (44)

| name | type | source | min→max value | phase | angle0→1 (°) / offset0→1 | bone(s) | LOD0 axis: pos · dir |
|---|---|---|---|---|---|---|---|
| `Kickstand` | rotation | `kickstand` | 0.000 → 1.000 | 0.00–1.00 | -76.0° → 0.0° | `kickstand` | (0.010, 0.212, 0.053) · (-1.000, 0.000, 0.000) |
| `TurnFront` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 90.0° → -90.0° | `drivewheel` | (-0.000, 0.937, -0.280) · (0.000, -0.882, -0.472) |
| `SeatAnim` | rotation | `seatdriver` | 0.000 → 1.000 | 0.00–1.00 | 0.0° → 110.0° | `seat_driver` | (0.020, 0.656, 0.080) · (-1.000, 0.000, 0.000) |
| `IndicatorSpeed` | rotation | `speed` | 0.000 → 80.000 | 0.00–80.00 | -145.0° → 145.0° | `dial_speed` | (0.000, 0.863, -0.424) · (0.000, 0.976, 0.217) |
| `wheel_1` | rotation | `wheelfront` | 0.000 → 6.283 | 0.00–6.28 | 0.0° → -360.0° | `wheel_1` | (0.002, 0.270, -0.672) · (1.000, 0.000, 0.000) |
| `wheel_2` | rotation | `wheelback` | 0.000 → 6.283 | 0.00–6.28 | 0.0° → -360.0° | `wheel_2` | (0.002, 0.270, 0.544) · (1.000, 0.000, 0.000) |
| `damper_2` | rotation | `damperback` | 0.000 → 1.000 | 0.00–1.00 | -6.9° → 9.2° | `damper_2` | (0.125, 0.305, 0.172) · (-1.000, 0.000, -0.000) |
| `damper_1` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.066 → 0.066 | `damper_1` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_1` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.004 → 0.004 | `damper_1_1` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_2` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.008 → 0.008 | `damper_1_2` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_3` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.012 → 0.012 | `damper_1_3` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_4` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.016 → 0.016 | `damper_1_4` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_5` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.019 → 0.019 | `damper_1_5` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_6` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.023 → 0.023 | `damper_1_6` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_7` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.027 → 0.027 | `damper_1_7` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_8` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.031 → 0.031 | `damper_1_8` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_9` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.035 → 0.035 | `damper_1_9` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_10` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.039 → 0.039 | `damper_1_10` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_11` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.043 → 0.043 | `damper_1_11` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_12` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.047 → 0.047 | `damper_1_12` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_13` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.050 → 0.050 | `damper_1_13` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_14` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.054 → 0.054 | `damper_1_14` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_15` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.058 → 0.058 | `damper_1_15` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_16` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.062 → 0.062 | `damper_1_16` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_1_17` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.066 → 0.066 | `damper_1_17` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.015 | `damper_1` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_1` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.001 | `damper_1_1` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_2` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.002 | `damper_1_2` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_3` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.003 | `damper_1_3` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_4` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.004 | `damper_1_4` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_5` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.004 | `damper_1_5` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_6` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.005 | `damper_1_6` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_7` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.006 | `damper_1_7` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_8` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.007 | `damper_1_8` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_9` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.008 | `damper_1_9` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_10` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.009 | `damper_1_10` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_11` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.010 | `damper_1_11` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_12` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.011 | `damper_1_12` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_13` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.011 | `damper_1_13` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_14` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.012 | `damper_1_14` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_15` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.013 | `damper_1_15` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_16` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.014 | `damper_1_16` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `Steering_correction_17` | translation | `turnfront` | 0.000 → 1.396 | 0.00–1.40 | off 0.000 → -0.015 | `damper_1_17` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.466) |
| `damper_2_debug` | translation | `damperback` | 0.000 → 1.000 | 0.00–1.00 | off -0.043 → 0.058 | `damper_2_debug` | (0.000, 0.000, 0.000) · (0.000, 1.000, 0.000) |

### Memory LOD (30 selections with points)

| selection | points |
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

### Proxies (LOD 0)

| proxy | position | rest |
|---|---|---|
| `\dz\vehicles\wheeled\proxies\crew_driver` | (0.000, -0.000, 0.038) | {"orientation": [[0.9999998211860657, 0.0, 0.0], [0.0, 0.9999999403953552, 0.0], [0.0, 0.0, 0.9999998807907104]], "sequence_id": 1, "named_selection_index": 45, "bone_index": 23, "section_index": 0} |
| `\dz\vehicles\wheeled\proxies\crew_driver` | (0.000, -0.000, 0.038) | {"orientation": [[0.9999999403953552, 0.0, 0.0], [0.0, 0.9999999403953552, 0.0], [0.0, 0.0, 1.0]], "sequence_id": 2, "named_selection_index": 46, "bone_index": 24, "section_index": 0} |
| `\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_exhaust` | (0.000, 0.185, 0.334) | {"orientation": [[-0.9999999403953552, 0.0, -3.89414338997085e-07], [0.0, 0.9999999403953552, 0.0], [3.8941436741879443e-07, 0.0, -1.0]], "sequence_id": 1, "named_selection_index": 47, "bone_index": -1, "section_index": 0} |
| `\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_wheel_1` | (0.000, 0.270, -0.673) | {"orientation": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], "sequence_id": 1, "named_selection_index": 48, "bone_index": 3, "section_index": 0} |
| `\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_wheel_2` | (-0.000, 0.270, 0.544) | {"orientation": [[-1.0, 0.0, -3.8941436741879443e-07], [0.0, 1.0, 0.0], [3.8941436741879443e-07, 0.0, -1.0]], "sequence_id": 1, "named_selection_index": 49, "bone_index": 31, "section_index": 0} |
| `\dz\vehicles\parts\replacement_headlight` | (0.000, 0.780, -0.481) | {"orientation": [[0.9999999403953552, -1.0735128813889512e-16, -2.8421509530628455e-14], [-2.8421712818535796e-14, -0.003777087200433016, -0.999992847442627], [0.0, 0.999992847442627, -0.003777087200433016]], "sequence_id": 1, "named_selection_index": 50, "bon |
| `\dz\vehicles\parts\sparkplug` | (0.000, 0.309, -0.253) | {"orientation": [[1.0, 6.718492966416344e-15, 2.4722340467115897e-14], [2.1316282072803006e-14, 0.31708380579948425, -0.9483975768089294], [-1.4210854715202004e-14, 0.9483975172042847, 0.31708377599716187]], "sequence_id": 1, "named_selection_index": 51, "bone |

### LOD 0 Selections

`damper_1` (1302c), `damper_1_17` (0c), `damper_1_1` (0c), `damper_1_2` (0c), `damper_1_3` (0c), `damper_1_4` (0c), `damper_1_5` (0c), `damper_1_6` (0c), `damper_1_7` (0c), `damper_1_8` (0c), `damper_1_9` (0c), `damper_1_10` (0c), `damper_1_11` (0c), `damper_1_12` (0c), `damper_1_13` (0c), `damper_1_14` (0c), `damper_1_15` (0c), `damper_1_16` (0c), `damper_2` (2780c), `kickstand` (152c), `dial_speed` (49c), `seat_driver` (2035c), `drivewheel` (9618c), `camo1` (8135c), `lights_brake` (452c), `lights_rear` (452c), `brakepedal` (104c), `clutchlever` (266c), `brakelever` (266c), `lights_front` (216c), `dmgzone_chassis` (6820c), `dmgzone_engine` (3100c), `dmgzone_fueltank` (912c), `dmgzone_lights_1_1` (3319c), `dmgzone_front` (6671c), `dmgzone_back` (10657c), `crewdriver` (1c), `dmgzone_fender` (2206c), `wheel_1` (1c), `wheel_2` (1c), `fender` (2206c), `\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_fender` (2206c), `camo_fender` (2206c), `* cannot generate st coordinates` (23c), `crewcodriver` (1c), `proxy:\dz\vehicles\wheeled\proxies\crew_driver.001` (1c), `proxy:\dz\vehicles\wheeled\proxies\crew_driver.002` (1c), `proxy:\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_exhaust.001` (1c), `proxy:\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_wheel_1.001` (1c), `proxy:\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_wheel_2.001` (1c), `proxy:\dz\vehicles\parts\replacement_headlight.001` (1c), `proxy:\dz\vehicles\parts\sparkplug.001` (1c)

### Geometry LOD

- selections: `component01` (8p/6c), `component02` (8p/6c), `component03` (10p/11c), `component04` (16p/15c), `component05` (16p/15c), `wheel_2_damper_land` (16p/0c), `wheel_1_damper_land` (16p/0c), `component06` (10p/11c), `component07` (8p/8c), `component08` (8p/6c), `component09` (8p/6c), `component10` (8p/6c), `component11` (8p/6c), `geotohide` (40p/32c)
- named properties: {"autocenter": "0", "class": "vehicle", "lodnoshadow": "1"}

### view_geometry

- selections: `component01`, `component02`, `component03`, `component04`, `component05`, `component06`, `component07`, `component08`, `component09`, `component10`, `component11`, `component12`, `component13`, `component14`, `component15`, `component16`, `component17`, `component18`, `component19`, `component20`, `component21`, `component22`, `component23`, `component24`, `component25`, `component26`, `component27`, `component28`, `component29`, `seat_driver`, `drivewheel`, `damper_2`, `dmgzone_chassis`, `dmgzone_engine`, `dmgzone_fueltank`, `dmgzone_lights_1_1`, `dmgzone_front`, `dmgzone_back`, `crewdriver`, `component30`, `wheel_1`, `wheel_2`, `component31`, `component32`, `dmgzone_fender`, `refill`, `motorbike_01_wheel_1`, `motorbike_01_wheel_2`, `component33`, `* cannot generate st coordinates`, `crewcodriver`, `sparkplug`, `reflector_1_1`, `proxy:\dz\vehicles\wheeled\proxies\crew_driver.001`, `proxy:\dz\vehicles\wheeled\proxies\crew_driver.002`, `proxy:\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_exhaust.001`, `proxy:\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_wheel_1.001`, `proxy:\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_wheel_2.001`, `proxy:\dz\vehicles\parts\replacement_headlight.001`, `proxy:\dz\vehicles\parts\sparkplug.001`, `component34`, `component35`

### fire_geometry

- selections: `component01`, `component02`, `component03`, `component04`, `component05`, `component06`, `component07`, `component08`, `component09`, `component10`, `component11`, `component12`, `component13`, `component14`, `component15`, `component16`, `component17`, `component18`, `component19`, `component20`, `component21`, `component22`, `component23`, `component24`, `component25`, `component26`, `component27`, `component28`, `component29`, `seat_driver`, `drivewheel`, `damper_2`, `dmgzone_chassis`, `dmgzone_engine`, `dmgzone_fueltank`, `dmgzone_lights_1_1`, `dmgzone_front`, `dmgzone_back`, `crewdriver`, `component30`, `wheel_1`, `wheel_2`, `dmgzone_fender`, `component31`, `component32`, `* cannot generate st coordinates`, `crewcodriver`, `proxy:\dz\vehicles\wheeled\proxies\crew_driver.001`, `proxy:\dz\vehicles\wheeled\proxies\crew_driver.002`, `proxy:\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_exhaust.001`, `proxy:\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_wheel_1.001`, `proxy:\dz\vehicles\singletrack\motorbike_01\proxy\motorbike_01_wheel_2.001`, `proxy:\dz\vehicles\parts\replacement_headlight.001`, `proxy:\dz\vehicles\parts\sparkplug.001`

### Textures and Materials (LOD 0)

- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_blue_co.paa
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_co.paa
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_wheel_co.paa
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_co.paa
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_glass_ca.paa
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_e.paa
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender_blue_co.paa
- 
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_wheel.rvmat
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_nolight.rvmat
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights.rvmat
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_glass.rvmat
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_rear_brake.rvmat
- dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender.rvmat

## Motorbike_02

- ODOL 56 (layout used by the reader: 54), 1895327 bytes, 11 LOD, animation parsing mode: `canonical_flag_animations`, errors per LOD: none.
- **ModelInfo**: mass **118.00 kg**, armor 200.0, center of mass (-0.0000, 0.4480, -0.0375), geometry_center (-0.0000, 0.7188, 0.0069), bbox (-0.570, -0.000, -0.970) → (0.570, 1.285, 1.115), sphere 1.343 / geometry 1.019.
- Rest of ModelInfo: `bounding_center`=(0.000, 0.000, 0.000); `aiming_center`=(-0.000, 0.719, 0.007); `bbox_min_visual`=(-0.570, -0.000, -0.970); `bbox_max_visual`=(0.570, 1.285, 1.115); `inv_inertia`=[[0.05499432981014252, 9.960741920167493e-08, -1.963521526704426e-06], [9.960741920167493e-08, 0.05821184813976288, -0.00453296909108758], [-1.963521526704426e-06, -0.00453296909108758, 0.23062758147716522]]; `auto_center`=False; `lock_auto_center`=False; `can_occlude`=False; `can_be_occluded`=True; `allow_animation`=True; `force_not_alpha`=0; `shadow_buffer_source`=0; `prefer_shadow_volume`=False; `shadow_offset`=None; `disable_cover`=True; `animated`=False; `map_type`=22; `special`=768; `remarks`=0; `and_hints`=0; `or_hints`=0; `view_density`=-10.0; `map_icon_color`=4268054087; `map_selected_color`=4251276613; `can_blend`=False; `property_class`=; `property_damage`=; `property_frequent`=False; `mass_array_n`=0; `lod_index_memory`=8; `lod_index_geometry`=7; `lod_index_fire_geometry`=10; `lod_index_view_geometry`=9; `lod_index_bytes_raw`=[255, 255, 255, 255, 255, 255, 255, 255, 255]; `min_shadow_u32`=4; `geometry_simple`=None; `geometry_phys`=None; `v56_after_shadow_buffer_source`=0; `v56_before_animations`=0; `ht_min`=1.0; `ht_max`=0.0; `af_max`=0.0; `mf_max`=0.0; `m_fact`=0.0; `t_body`=0.0

### LODs

| # | resolution | kind | points | faces | selections | proxies | textures | materials | bbox | named properties |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | visual | 26371 | 17091 | 84 | 10 | 9 | 8 | (-0.42, -0.00, -0.90) → (0.43, 1.24, 1.07) | {} |
| 1 | 2 | visual | 13142 | 7656 | 74 | 8 | 9 | 8 | (-0.42, -0.00, -0.90) → (0.43, 1.24, 1.07) | {} |
| 2 | 3 | visual | 5666 | 3110 | 70 | 7 | 8 | 7 | (-0.42, -0.00, -0.90) → (0.43, 1.24, 1.06) | {} |
| 3 | 4 | visual | 2965 | 1507 | 61 | 7 | 8 | 7 | (-0.42, -0.00, -0.90) → (0.43, 1.22, 1.06) | {} |
| 4 | 5 | visual | 1659 | 879 | 53 | 7 | 8 | 7 | (-0.41, -0.00, -0.90) → (0.43, 1.22, 1.06) | {} |
| 5 | 6 | visual | 956 | 528 | 44 | 7 | 7 | 6 | (-0.41, -0.00, -0.89) → (0.42, 1.22, 1.06) | {} |
| 6 | 7 | visual | 414 | 206 | 30 | 7 | 4 | 3 | (-0.39, -0.00, -0.76) → (0.40, 1.21, 0.86) | {} |
| 7 | 1e+13 | geometry | 88 | 114 | 12 | 0 | 1 | 0 | (-0.39, 0.21, -0.78) → (0.39, 1.23, 0.80) | {"autocenter": "0"} |
| 8 | 1e+15 | memory | 93 | 0 | 54 | 0 | 0 | 0 | (-0.57, 0.00, -0.97) → (0.57, 1.23, 1.11) | {} |
| 9 | 6e+15 | view_geometry | 948 | 1033 | 114 | 10 | 1 | 0 | (-0.41, -0.00, -0.96) → (0.41, 1.29, 1.07) | {} |
| 10 | 7e+15 | fire_geometry | 891 | 992 | 98 | 7 | 1 | 8 | (-0.41, -0.00, -0.90) → (0.41, 1.20, 1.07) | {} |

### Skeleton `Motorbike_02` (37 bones; is_discrete=True)

`drivewheel`←`∅`, `dial_speed`←`drivewheel`, `dial_rpm`←`drivewheel`, `dial_temp`←`drivewheel`, `damper_1`←`drivewheel`, `wheel_1`←`damper_1`, `seat`←`∅`, `crewdriver`←`∅`, `crewcodriver`←`∅`, `kickstand`←`∅`, `battery`←`∅`, `reflector_1_1`←`∅`, `engine`←`∅`, `dial_fuel`←`∅`, `seat_driver`←`∅`, `drivewheel_0`←`∅`, `drivewheel_1`←`∅`, `drivewheel_2`←`∅`, `drivewheel_3`←`∅`, `drivewheel_4`←`∅`, `drivewheel_5`←`∅`, `drivewheel_6`←`∅`, `drivewheel_7`←`∅`, `drivewheel_8`←`∅`, `drivewheel_9`←`∅`, `damper_2`←`∅`, `wheel_2`←`damper_2`, `damper_2_mudshield`←`damper_2`, `damper_2_2`←`∅`, `damper_2_limited`←`∅`, `damper_2_debug`←`∅`, `damper_chain`←`∅`, `damper_chain_2`←`∅`, `rocker_link`←`∅`, `rocker`←`rocker_link`, `shock_bottoms`←`rocker`, `shock_tops`←`∅`

### Animations (60)

| name | type | source | min→max value | phase | angle0→1 (°) / offset0→1 | bone(s) | LOD0 axis: pos · dir |
|---|---|---|---|---|---|---|---|
| `TurnFront` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 90.0° → -90.0° | `drivewheel` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `IndicatorSpeed` | rotation | `speed` | 0.000 → 120.000 | 0.00–120.00 | -0.0° → -250.0° | `dial_speed` | (0.039, 1.137, -0.166) · (-0.000, -0.893, -0.451) |
| `IndicatorFuel` | rotation | `fuel` | 0.000 → 1.000 | 0.00–1.00 | 0.0° → -250.0° | `dial_fuel` | (-0.000, 1.098, -0.108) · (-0.000, -0.978, -0.208) |
| `IndicatorRPM` | rotation | `enginerpm` | 0.000 → 1.000 | 0.00–1.00 | 0.0° → -280.0° | `dial_rpm` | (-0.039, 1.137, -0.166) · (-0.000, -0.893, -0.451) |
| `IndicatorCoolant` | rotation | `coolant` | 0.000 → 1.000 | 0.00–1.00 | 0.0° → -135.0° | `dial_temp` | (-0.039, 1.130, -0.151) · (-0.000, -0.893, -0.451) |
| `wheel_1` | rotation | `wheelfront` | 0.000 → 6.283 | 0.00–6.28 | 0.0° → -360.0° | `wheel_1` | (-0.148, 0.301, -0.713) · (1.000, 0.000, 0.000) |
| `wheel_2` | rotation | `wheelback` | 0.000 → 6.283 | 0.00–6.28 | 0.0° → -360.0° | `wheel_2` | (-0.148, 0.301, 0.690) · (1.000, 0.000, 0.000) |
| `damper_2` | rotation | `damperback` | 0.000 → 1.000 | 0.00–1.00 | -20.0° → 30.0° | `damper_2` | (0.072, 0.451, 0.149) · (-1.000, 0.000, 0.000) |
| `damper_2_2` | rotation | `damperback` | 0.000 → 1.000 | 0.00–1.00 | -17.0° → 25.5° | `damper_2_2` | (0.072, 0.451, 0.149) · (-1.000, 0.000, 0.000) |
| `damper_2_limited` | rotation | `damperback` | 0.000 → 0.550 | 0.00–0.55 | -17.0° → 6.4° | `damper_2_limited` | (0.072, 0.451, 0.149) · (-1.000, 0.000, 0.000) |
| `rocker_link_1` | rotation | `damperback` | 0.000 → 0.100 | 0.00–0.10 | -16.9° → -13.4° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_2` | rotation | `damperback` | 0.100 → 0.250 | 0.10–0.25 | 0.0° → 6.3° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_3` | rotation | `damperback` | 0.250 → 0.400 | 0.25–0.40 | 0.0° → 7.1° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_4` | rotation | `damperback` | 0.400 → 0.500 | 0.40–0.50 | 0.0° → 5.0° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_5` | rotation | `damperback` | 0.500 → 0.600 | 0.50–0.60 | 0.0° → 5.2° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_6` | rotation | `damperback` | 0.600 → 0.750 | 0.60–0.75 | 0.0° → 8.0° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_7` | rotation | `damperback` | 0.750 → 0.900 | 0.75–0.90 | 0.0° → 8.3° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_link_8` | rotation | `damperback` | 0.900 → 1.000 | 0.90–1.00 | 0.0° → 5.7° | `rocker_link` | (0.046, 0.369, 0.187) · (-1.000, -0.000, 0.000) |
| `rocker_1` | rotation | `damperback` | 0.000 → 0.100 | 0.00–0.10 | -33.8° → -24.6° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_2` | rotation | `damperback` | 0.100 → 0.250 | 0.10–0.25 | 0.0° → 12.7° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_3` | rotation | `damperback` | 0.250 → 0.400 | 0.25–0.40 | 0.0° → 11.6° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_4` | rotation | `damperback` | 0.400 → 0.500 | 0.40–0.50 | 0.0° → 7.9° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_5` | rotation | `damperback` | 0.500 → 0.600 | 0.50–0.60 | 0.0° → 7.7° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_6` | rotation | `damperback` | 0.600 → 0.750 | 0.60–0.75 | 0.0° → 11.6° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_7` | rotation | `damperback` | 0.750 → 0.900 | 0.75–0.90 | 0.0° → 12.0° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `rocker_8` | rotation | `damperback` | 0.900 → 1.000 | 0.90–1.00 | 0.0° → 8.4° | `rocker` | (-0.034, 0.333, 0.333) · (1.000, 0.000, 0.000) |
| `shock_bottoms_1` | rotation | `damperback` | 0.000 → 0.100 | 0.00–0.10 | -19.1° → -13.1° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_2` | rotation | `damperback` | 0.100 → 0.250 | 0.10–0.25 | 0.0° → 7.3° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_3` | rotation | `damperback` | 0.250 → 0.400 | 0.25–0.40 | 0.0° → 5.7° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_4` | rotation | `damperback` | 0.400 → 0.500 | 0.40–0.50 | 0.0° → 3.4° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_5` | rotation | `damperback` | 0.500 → 0.600 | 0.50–0.60 | 0.0° → 3.2° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_6` | rotation | `damperback` | 0.600 → 0.750 | 0.60–0.75 | 0.0° → 4.4° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_7` | rotation | `damperback` | 0.750 → 0.900 | 0.75–0.90 | 0.0° → 4.2° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_bottoms_8` | rotation | `damperback` | 0.900 → 1.000 | 0.90–1.00 | 0.0° → 2.7° | `shock_bottoms` | (0.042, 0.298, 0.265) · (-1.000, 0.000, 0.000) |
| `shock_tops_1` | rotation | `damperback` | 0.000 → 0.100 | 0.00–0.10 | -1.7° → -1.2° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_2` | rotation | `damperback` | 0.100 → 0.250 | 0.10–0.25 | 0.0° → 0.4° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_3` | rotation | `damperback` | 0.250 → 0.400 | 0.25–0.40 | 0.0° → 0.7° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_4` | rotation | `damperback` | 0.400 → 0.500 | 0.40–0.50 | 0.0° → 0.4° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_5` | rotation | `damperback` | 0.500 → 0.600 | 0.50–0.60 | 0.0° → 0.4° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_6` | rotation | `damperback` | 0.600 → 0.750 | 0.60–0.75 | 0.0° → 0.8° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_7` | rotation | `damperback` | 0.750 → 0.900 | 0.75–0.90 | 0.0° → 1.0° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `shock_tops_8` | rotation | `damperback` | 0.900 → 1.000 | 0.90–1.00 | 0.0° → 0.8° | `shock_tops` | (0.031, 0.673, 0.174) · (-1.000, 0.000, 0.000) |
| `damper_2_debug` | translation | `damperback` | 0.000 → 1.000 | 0.00–1.00 | off -0.187 → 0.313 | `damper_2_debug` | (0.000, 0.000, 0.000) · (0.000, 0.919, 0.010) |
| `Kickstand` | rotation | `kickstand` | 0.000 → 1.000 | 0.00–1.00 | -76.0° → -80.0° | `kickstand` | (-0.125, 0.367, 0.186) · (1.000, 0.000, 0.000) |
| `Kickstand_damper_Min` | rotation | `damperback` | 0.000 → 0.430 | 0.00–0.43 | 30.0° → 0.0° | `kickstand` | (-0.125, 0.367, 0.186) · (1.000, 0.000, 0.000) |
| `Kickstand_damper_Max` | rotation | `damperback` | 0.800 → 1.000 | 0.80–1.00 | 0.0° → -12.0° | `kickstand` | (-0.125, 0.367, 0.186) · (1.000, 0.000, 0.000) |
| `damper_2_mudshield` | rotation | `damperback` | 0.700 → 1.000 | 0.70–1.00 | 0.0° → -15.0° | `damper_2_mudshield` | (0.064, 0.419, 0.356) · (-1.000, -0.000, 0.000) |
| `damper_chain` | rotation | `damperback` | 0.000 → 1.000 | 0.00–1.00 | -15.0° → 25.0° | `damper_chain` | (0.120, 0.378, 0.196) · (-1.000, 0.000, 0.000) |
| `damper_chain_2` | rotation | `damperback` | 0.000 → 1.000 | 0.00–1.00 | 10.0° → -10.0° | `damper_chain_2` | (0.062, 0.439, 0.054) · (1.000, 0.000, 0.000) |
| `damper_1` | translation | `damperfront` | 0.000 → 1.000 | 0.00–1.00 | off -0.010 → 0.250 | `damper_1` | (0.000, 0.000, 0.000) · (0.000, 0.949, 0.477) |
| `turnFront_0` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 4.5° → -4.5° | `drivewheel_0` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_1` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 9.0° → -9.0° | `drivewheel_1` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_2` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 18.0° → -18.0° | `drivewheel_2` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_3` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 27.0° → -27.0° | `drivewheel_3` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_4` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 36.0° → -36.0° | `drivewheel_4` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_5` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 45.0° → -45.0° | `drivewheel_5` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_6` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 54.0° → -54.0° | `drivewheel_6` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_7` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 63.0° → -63.0° | `drivewheel_7` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_8` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 72.0° → -72.0° | `drivewheel_8` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |
| `turnFront_9` | rotation | `turnfront` | -1.571 → 1.571 | -1.57–1.57 | 81.0° → -81.0° | `drivewheel_9` | (0.000, 0.847, -0.368) · (0.000, -0.893, -0.449) |

### Memory LOD (54 selections with points)

| selection | points |
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

### Proxies (LOD 0)

| proxy | position | rest |
|---|---|---|
| `\dz\vehicles\wheeled\proxies\crew_driver` | (0.000, 0.000, 0.071) | {"orientation": [[0.9999999403953552, 0.0, 0.0], [0.0, 0.9999999403953552, 0.0], [0.0, 0.0, 1.0]], "sequence_id": 1, "named_selection_index": 74, "bone_index": 7, "section_index": 0} |
| `\dz\vehicles\wheeled\proxies\crew_driver` | (0.000, -0.000, 0.071) | {"orientation": [[0.9999999403953552, 0.0, 0.0], [0.0, 0.9999999403953552, 0.0], [0.0, 0.0, 1.0]], "sequence_id": 2, "named_selection_index": 75, "bone_index": 8, "section_index": 0} |
| `\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_shieldleft` | (0.095, 0.603, 0.380) | {"orientation": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], "sequence_id": 1, "named_selection_index": 76, "bone_index": -1, "section_index": 0} |
| `\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_shieldright` | (-0.095, 0.603, 0.380) | {"orientation": [[-1.0, 0.0, -1.5685432686041167e-07], [0.0, 1.0, 0.0], [1.5685432686041167e-07, 0.0, -1.0]], "sequence_id": 1, "named_selection_index": 77, "bone_index": -1, "section_index": 0} |
| `\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_wheel_1` | (0.000, 0.301, -0.712) | {"orientation": [[0.9999998807907104, 0.0, 0.0], [0.0, 0.9999999403953552, 0.0], [0.0, 0.0, 0.9999999403953552]], "sequence_id": 1, "named_selection_index": 78, "bone_index": 5, "section_index": 0} |
| `\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_wheel_2` | (0.000, 0.301, 0.690) | {"orientation": [[0.9999998807907104, 0.0, 0.0], [0.0, 0.9999999403953552, 0.0], [0.0, 0.0, 0.9999999403953552]], "sequence_id": 1, "named_selection_index": 79, "bone_index": 26, "section_index": 0} |
| `\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_windshield` | (0.000, 0.983, -0.380) | {"orientation": [[2.7167970984010026e-07, 0.4999997317790985, -0.8660255074501038], [-1.5685424159528338e-07, 0.8660255074501038, 0.4999997317790985], [1.0, 0.0, 3.1370865372082335e-07]], "sequence_id": 1, "named_selection_index": 80, "bone_index": 0, "section |
| `\dz\vehicles\parts\replacement_headlight` | (0.000, 0.997, -0.302) | {"orientation": [[1.0000001192092896, -0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0000001192092896, 0.0]], "sequence_id": 1, "named_selection_index": 81, "bone_index": 11, "section_index": 0} |
| `\dz\vehicles\parts\sparkplug` | (0.048, 0.704, -0.094) | {"orientation": [[0.8679314851760864, -0.49668413400650024, 4.470348358154297e-07], [0.49046245217323303, 0.8570592999458313, -0.15778492391109467], [0.07836886495351791, 0.13694670796394348, 0.9874735474586487]], "sequence_id": 1, "named_selection_index": 82, |
| `\dz\vehicles\parts\sparkplug` | (-0.002, 0.685, -0.140) | {"orientation": [[0.9985364675521851, 0.05408112704753876, 1.8533319234848022e-07], [-0.05340364947915077, 0.9860283136367798, -0.15778543055057526], [-0.008533395826816559, 0.157554492354393, 0.9874733686447144]], "sequence_id": 2, "named_selection_index": 83 |

### LOD 0 Selections

`1111` (312c), `fusion surface` (902c), `accelerator` (128c), `brakelever` (78c), `clutchlever` (78c), `cables` (1390c), `caphi` (10c), `caplo` (17c), `chain_static` (48c), `chain_swing` (228c), `clutch_arm` (58c), `front_brake_lever1` (59c), `front_brake_lever_2` (26c), `gearshift` (73c), `headlamp_switch` (24c), `mirrorl` (748c), `mirrorr` (685c), `pistons_bottom` (172c), `pistons_top` (418c), `rear_brake` (57c), `rear_brake_lever` (96c), `starter_arm` (104c), `starter_lever` (106c), `drivewheel` (4737c), `suspension_arm` (710c), `damper_1` (770c), `wall` (344c), `shieldleft` (1c), `wheel_2` (1c), `wheel_1` (1c), `dial_fuel` (12c), `dial_rpm` (2c), `dial_speed` (2c), `zbytek` (16449c), `kickstand` (142c), `crewdriver` (1c), `damper_2` (983c), `rocker` (106c), `rocker_link` (36c), `shock_bottoms` (172c), `shock_tops` (410c), `damper_2_mudshield` (9c), `damper_2_2` (0c), `damper_chain` (0c), `damper_2_limited` (33c), `damper_chain_2` (0c), `drivewheel_3` (0c), `drivewheel_2` (9c), `drivewheel_1` (12c), `drivewheel_4` (0c), `drivewheel_5` (0c), `drivewheel_7` (0c), `drivewheel_9` (0c), `drivewheel_8` (0c), `drivewheel_6` (0c), `drivewheel_0` (0c), `lights_front` (96c), `lights_rear` (26c), `lights_brake` (26c), `camo` (14139c), `camo_exhaust` (960c), `camo_fenderfront` (557c), `camo_fenderrear` (336c), `dmgzone_fenderfront` (557c), `dmgzone_fenderrear` (336c), `dmgzone_exhaust` (960c), `dmgzone_engine` (2472c), `dmgzone_fueltank` (906c), `dmgzone_lights_1_1` (529c), `dmgzone_front` (4645c), `dmgzone_back` (2360c), `dmgzone_chassis` (4316c), `reflector_1_1` (1c), `crewcodriver` (1c), `proxy:\dz\vehicles\wheeled\proxies\crew_driver.001` (1c), `proxy:\dz\vehicles\wheeled\proxies\crew_driver.002` (1c), `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_shieldleft.001` (1c), `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_shieldright.001` (1c), `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_wheel_1.001` (1c), `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_wheel_2.001` (1c), `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_windshield.001` (1c), `proxy:\dz\vehicles\parts\replacement_headlight.001` (1c), `proxy:\dz\vehicles\parts\sparkplug.001` (1c), `proxy:\dz\vehicles\parts\sparkplug.002` (1c)

### Geometry LOD

- selections: `wheel_2_damper_land` (16p/15c), `wheel_1_damper_land` (16p/15c), `component01` (16p/15c), `component02` (16p/15c), `component03` (8p/12c), `component04` (8p/12c), `component05` (8p/12c), `component06` (8p/12c), `component07` (8p/12c), `component08` (8p/12c), `component09` (8p/12c), `geotohide` (24p/36c)
- named properties: {"autocenter": "0"}

### view_geometry

- selections: `1111`, `engine`, `mirrorl`, `steering`, `suspension_front`, `suspension_arm`, `fuel`, `shieldleft`, `wheel_2`, `wheel_1`, `crewdriver`, `seat_driver`, `dmgzone_fenderfront`, `dmgzone_fenderrear`, `dmgzone_exhaust`, `dmgzone_engine`, `dmgzone_fueltank`, `dmgzone_lights_1_1`, `dmgzone_front`, `dmgzone_back`, `dmgzone_chassis`, `component01`, `component02`, `component03`, `component04`, `component05`, `component06`, `component07`, `component08`, `component09`, `component10`, `component11`, `component12`, `component13`, `component14`, `component15`, `component16`, `component17`, `component18`, `component19`, `component20`, `component21`, `component22`, `component23`, `component24`, `component25`, `component26`, `component27`, `component28`, `component29`, `component30`, `component31`, `component32`, `component33`, `component34`, `component35`, `component36`, `component37`, `component38`, `component39`, `component40`, `component41`, `component42`, `component43`, `component44`, `component45`, `component46`, `component47`, `component48`, `component49`, `component50`, `component51`, `component52`, `component53`, `component54`, `component55`, `component56`, `component57`, `component58`, `component59`, `component60`, `component61`, `component62`, `component63`, `component64`, `component65`, `component66`, `component67`, `component68`, `refill`, `crewcodriver`, `sparkplug`, `motorbike_02_wheel_1`, `motorbike_02_wheel_2`, `reflector_1_1`, `component69`, `component70`, `component71`, `motorbike_02_windshield`, `motorbike_02_shieldright`, `motorbike_02_shieldleft`, `proxy:\dz\vehicles\wheeled\proxies\crew_driver.001`, `proxy:\dz\vehicles\wheeled\proxies\crew_driver.002`, `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_shieldleft.001`, `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_shieldright.001`, `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_wheel_1.001`, `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_wheel_2.001`, `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_windshield.001`, `proxy:\dz\vehicles\parts\replacement_headlight.001`, `proxy:\dz\vehicles\parts\sparkplug.001`, `proxy:\dz\vehicles\parts\sparkplug.002`, `component72`, `component73`, `component74`

### fire_geometry

- selections: `1111`, `engine`, `mirrorl`, `steering`, `suspension_front`, `suspension_arm`, `fuel`, `shieldleft`, `wheel_2`, `wheel_1`, `crewdriver`, `seat_driver`, `reflector_1_1`, `dmgzone_fenderfront`, `dmgzone_fenderrear`, `dmgzone_exhaust`, `dmgzone_engine`, `dmgzone_fueltank`, `dmgzone_lights_1_1`, `dmgzone_front`, `dmgzone_back`, `dmgzone_chassis`, `component01`, `component02`, `component03`, `component04`, `component05`, `component06`, `component07`, `component08`, `component09`, `component10`, `component11`, `component12`, `component13`, `component14`, `component15`, `component16`, `component17`, `component18`, `component19`, `component20`, `component21`, `component22`, `component23`, `component24`, `component25`, `component26`, `component27`, `component28`, `component29`, `component30`, `component31`, `component32`, `component33`, `component34`, `component35`, `component36`, `component37`, `component38`, `component39`, `component40`, `component41`, `component42`, `component43`, `component44`, `component45`, `component46`, `component47`, `component48`, `component49`, `component50`, `component51`, `component52`, `component53`, `component54`, `component55`, `component56`, `component57`, `component58`, `component59`, `component60`, `component61`, `component62`, `component63`, `component64`, `component65`, `component66`, `component67`, `component68`, `crewcodriver`, `proxy:\dz\vehicles\wheeled\proxies\crew_driver.001`, `proxy:\dz\vehicles\wheeled\proxies\crew_driver.002`, `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_shieldleft.001`, `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_shieldright.001`, `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_wheel_1.001`, `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_wheel_2.001`, `proxy:\dz\vehicles\singletrack\motorbike_02\proxy\motorbike_02_windshield.001`

### Textures and Materials (LOD 0)

- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_body_red_co.paa
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_wheel_co.paa
- #(argb,8,8,3)color(0.000,0.000,0.000,0.100,ca)
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_lights_co.paa
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_lights_e_co.paa
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_exhaust_co.paa
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_fenderfront_co.paa
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_fenderrear_co.paa
- 
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_wheel.rvmat
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_body.rvmat
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_glass.rvmat
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_fenderrear.rvmat
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_lights_rear_brake.rvmat
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_exhaust.rvmat
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_fenderfront.rvmat
- dz\vehicles\singletrack\motorbike_02\data\motorbike_02_lights_nolight.rvmat

## Wheels (proxies)

| model | mass | bbox min → max | Ø by bbox (greater of Y/Z) | width (X) | LODs |
|---|---|---|---|---|---|
| `Motorbike_01_wheel_1` | 4.86 | (-0.034, -0.290, -0.290) → (0.039, 0.290, 0.290) | 0.579 | 0.073 | visual:2784c, visual:1478c, visual:638c, visual:300c, visual:108c, geometry:28c, memory:0c, view_geometry:28c, fire_geometry:220c |
| `Motorbike_01_wheel_2` | 4.86 | (-0.039, -0.290, -0.290) → (0.058, 0.290, 0.290) | 0.579 | 0.097 | visual:2858c, visual:1512c, visual:672c, visual:406c, visual:130c, geometry:28c, memory:0c, view_geometry:28c, fire_geometry:220c |
| `Motorbike_02_wheel_1` | 4.86 | (-0.054, -0.300, -0.299) → (0.045, 0.300, 0.301) | 0.600 | 0.099 | visual:2730c, visual:746c, visual:241c, visual:98c, visual:38c, visual:30c, geometry:28c, memory:0c, view_geometry:15c, fire_geometry:74c |
| `Motorbike_02_wheel_2` | 4.86 | (-0.057, -0.299, -0.299) → (0.081, 0.300, 0.300) | 0.599 | 0.138 | visual:3129c, visual:994c, visual:156c, visual:76c, visual:41c, visual:30c, geometry:28c, memory:0c, view_geometry:15c, fire_geometry:75c |
