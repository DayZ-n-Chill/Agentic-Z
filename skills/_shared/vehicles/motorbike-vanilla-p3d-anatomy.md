# Vanilla motorbike models

What the binarized models of the two vanilla motorbikes hold, at a glance, and how to read the full tables in `motorbike-01-model-anatomy.md` and `motorbike-02-model-anatomy.md`. Use them as the reference for a new motorbike: what the engine, config and script find in a working model.

## Where the numbers come from

The models are `P:\DZ\vehicles\singletrack\motorbike_01\motorbike_01.p3d` and `P:\DZ\vehicles\singletrack\motorbike_02\motorbike_02.p3d`, loaded by `Motorbike_01_ColorBase` and `Motorbike_02_ColorBase` (`P:\DZ\vehicles\singletrack\config.cpp:220`, `:1401`). The tables were generated from a reader for binarized (ODOL version 56) models, with no hand-typed numbers. That reader is not in this repo, so the tables are tool output, not checked on `P:\`; treat them as leads.

What is checked on `P:\`: the two files are 2,302,438 and 1,895,327 bytes, both start with the `ODOL` signature and version 56, and `motorbike_01.p3d` contains the names `drivewheel`, `damper_1`, `kickstand`, `geotohide`, `pos_driver`, `light_1_1` and `refill` as text. Nothing here is checked in game or against a source `model.cfg`, which vanilla does not ship. Version 56 adds two model info fields whose meaning is unknown; both are 0 in both models.

## How to read the tables

- Units are metres and degrees. Axes are as stored in the model: X across, Y up, Z along the bike.
- The front of the bike is at negative Z: the headlight proxy `replacement_headlight` sits at negative Z and the exhaust at positive Z.
- The model info bounding box is larger than the mesh, because it includes proxies and animation. For dimensions use the bounding box of each LOD.

## The two bikes side by side

| | `Motorbike_01` | `Motorbike_02` |
|---|---|---|
| Mass | 85 kg | 118 kg |
| Centre of mass height | 0.276 m | 0.448 m |
| Wheelbase | 1.217 m (wheel proxies at Z -0.673 and +0.544) | 1.402 m (Z -0.712 and +0.690) |
| Visual LODs | 5, from 33,692 down to 832 faces | 7, from 17,091 down to 206 faces |
| Bones | 35 | 37 |
| Animations | 44 | 60 |
| `autocenter=0` | On the Geometry, View Geometry and Fire Geometry LODs, which also carry `lodnoshadow=1` | On the Geometry LOD only |
| Crew proxy | `\dz\vehicles\wheeled\proxies\crew_driver` twice, near the origin, 0.038 m along Z | The same proxy twice, 0.071 m along Z |

Neither model has a shadow LOD, a View Pilot LOD or a LandContact LOD.

## Wheel models

All four wheel models weigh 4.86 kg, and none has a shadow LOD. Faces per LOD are listed visual LODs first, then Geometry, Memory, View Geometry and Fire Geometry. The models are set in `config.cpp` (`:159`, `:192`, `:1024`, `:1056`).

| Model | Mass (kg) | Bounding box | Diameter (larger of Y and Z) | Width (X) | Faces per LOD |
|---|---|---|---|---|---|
| `Motorbike_01_wheel_1` | 4.86 | (-0.034, -0.290, -0.290) to (0.039, 0.290, 0.290) | 0.579 | 0.073 | visual:2784c, visual:1478c, visual:638c, visual:300c, visual:108c, geometry:28c, memory:0c, view_geometry:28c, fire_geometry:220c |
| `Motorbike_01_wheel_2` | 4.86 | (-0.039, -0.290, -0.290) to (0.058, 0.290, 0.290) | 0.579 | 0.097 | visual:2858c, visual:1512c, visual:672c, visual:406c, visual:130c, geometry:28c, memory:0c, view_geometry:28c, fire_geometry:220c |
| `Motorbike_02_wheel_1` | 4.86 | (-0.054, -0.300, -0.299) to (0.045, 0.300, 0.301) | 0.600 | 0.099 | visual:2730c, visual:746c, visual:241c, visual:98c, visual:38c, visual:30c, geometry:28c, memory:0c, view_geometry:15c, fire_geometry:74c |
| `Motorbike_02_wheel_2` | 4.86 | (-0.057, -0.299, -0.299) to (0.081, 0.300, 0.300) | 0.599 | 0.138 | visual:3129c, visual:994c, visual:156c, visual:76c, visual:41c, visual:30c, geometry:28c, memory:0c, view_geometry:15c, fire_geometry:75c |
