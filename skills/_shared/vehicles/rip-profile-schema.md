# Car profile fields

What a per-car profile of a rip import pipeline holds, field by field, and which step reads each one. The pipeline itself is not shipped in this repo; use this as the list of decisions a ripped car needs written down.

A profile is the single source for one car. Earlier cars' profiles are not templates: they mix the shared fields with exceptions approved in game for that car alone (a flipped part, a kept sunk height, a cabin colour set). For the next car copy only the shared fields, never the exceptions.

## Identity and paths

| Field | What it is | Read by |
|---|---|---|
| `name` | Short token of the car; prefixes the work outputs. | Every step |
| `shell_path` | The deployed `.p3d` in the mod tree; read only. | Repaint, checks, transplant |
| `struct_shell_in` | The work shell that feeds the structural builder. | Structural builder |
| `out_path` | The builder's full output `.p3d`. | Structural builder |
| `report_path` | The structural build report (JSON). | Structural builder, checks |
| `geo_npz`, `geo_meta` | The geometry and material arrays and their description. | Visual builder, repaint |
| `locators_path` | The rip's `Locators.xml`: memory points and dimensions. | Structural builder |

## Transform and physics

| Field | What it is |
|---|---|
| `transform{LIFT, hub_lift, contact_y, wheel_hub_rip_y}` | Gives `Y0 = (wheel_R - wheel_hub_rip_y) + LIFT`. `hub_lift` separates the hub from the body lift: a rally lift is not a hub lift, and `hub_lift=0` leaves the wheel at the knuckle. |
| `WHEEL_R` | Radius of the mounted wheel, equal to the real wheel item's radius. A profile radius of 0.3637 against a mounted 0.34 floats the wheels up. |
| `TARGET_MASS` | Mass in kg for `#Mass#` in the Geometry LOD, checked against the real car's published weight. |
| `seats{driver_x,y,z}` | The seat anchor. |

## Visual build and structure

| Field | What it is |
|---|---|
| `builder{}` | Visual builder rules: where the interior goes, the face budget (merge classes into an authored LOD, keep tiny classes as they are), classes to flip, parts to skip, and the inner glass rule. |
| `interior{viewpilot_subset, viewpilot_full}` | One interior: the full one goes to resolution 1.0, a subset of at most 16k faces goes to the View Pilot LOD at 1100. Use the subset; the full interior in 1100 is known to lag (`view-pilot-and-first-person.md`). |
| `viewpilot_parts` | Retired; do not use. |
| `sedanwheel`, `crew_driver`, `crew_cargo` | Vanilla proxy paths, written without `.p3d`, for example `DZ\vehicles\wheeled\civiliansedan\proxy\sedanWheel` (`P:\DZ\vehicles\wheeled\config.cpp:23971`). |
| `shadow{max_faces}` | Shadow LOD budget: at most 5000 faces, 40 degree planar dissolve. |
| `dual_tag` | Tags each component as both its named selection and `componentNN`. Always on; off only for a test that must fail. |
| `collision{chassis, dmgzones, seat_con, refill, crew}` | An exact box override, or bands taken from the bounding box for other shapes. Damage zone components, hitpoints and `componentNames[]` in config must be the same set. `refill` is the memory point the engine reads for the fuel position (`P:\scripts\3_game\vehicles\transport.c:112`). |

## Check settings

| Field | What it is |
|---|---|
| `gates{import_report, gb_paths, gbplus_new, gbplus_ref, bands}` | Winding and anchor checks. `import_report` is required; with it missing the check fails. |
| `gate{proxy_dir, chunk_prefix, body_selections, exclude_selections, raycast, twin_eps_mm}` | The see-through check: which body selections it covers, the twin face test and the ray settings. |
| `artifact_gates{perf_budget, lod_semantics, interior_rayfan, glass_occ, winding}` | The checks that must fail loudly. A calibration is scoped to its evidence; never switch a check off. Overrides approved for one car (for example a higher visual face budget that only warns) are not inherited by the next. |

## Front end fields

| Field | What it is |
|---|---|
| `source{car_root, game_path, importer, manifest_dir, work_stem, import_report, blender_exe, material_type_overrides?}` | The rip paths and every work path derived from them (`<stem>_p2_raw.blend`, `<stem>_p2_geo.npz`, `<stem>_material_map.json`). `material_type_overrides` is an optional list of `{part, mat_name, mat_path, type}`; each entry must match exactly one visible mesh or the material map fails. |
| `intake{budgets{visual_total_faces_max, viewpilot_resolved_max, shadow_faces_max, uv_uniq_min, dup_face_rate_max}}` plus a LOD policy | Intake budgets and the policy that assigns each part to an authored LOD by budget, written to `lod_plan.json`. The intake fails if no plan fits. |

## Rules for profiles

1. A missing required key fails and names the key. There are no silent defaults.
2. Calibrations and exceptions carry a note (`*_note`) saying why, and stay in that car's profile.
3. A change to the fields changes this file in the same commit.
4. `material_type_overrides` does not replace the classification by folder. It keeps `source_type`, records that an override applied, and matches only on the exact `part`, `mat_name` and `mat_path`.
