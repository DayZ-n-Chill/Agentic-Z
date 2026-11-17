# Car profile schema (legacy and in flight)

Field by field, what a `profiles\<car>.json` of the import project holds and which script reads each field. Status of 2026-07-11.

The profile is the source of truth for a car in the pipeline. The common loader is `load_profile()` in `<vehicle-import>\scripts\rip_p3_structural.py`. `brz.json` is not a clean template: it mixes the fleet contract with surgical `exceptions` approved in game (E_flip, C1_safe, sunk_keep_z, the cabin palette). For car number two copy only the contract, never the exceptions. Fields marked (s1) come from the spec `<vehicle-import>\plans\2026-07-11-s1-frontend-intake.md`; verify that it was merged before using them.

**Change 0 (2026-08-05).** This schema keeps the wiring of cars already started and of the manual tools. It is not a template for the next family B car. In particular `source_inventory`, `manifest_decisions`, per-run receipts and `artifact_gates` outside B1 to B6 are not inputs of the new happy path (B7, the visual signoff, joined the allowlist on 2026-08-16). Existing consumers are not modified here; a new family B car stops before geometry as long as its downstream path does not exist.

Everything in this file describes the import project and its measured cars. None of it is a fact about the vanilla game, and it is not yet checked on `P:\`.

## Identity and paths

| Field | What it is | Consumer |
|---|---|---|
| `name` | Short token of the car (`brz`); prefixes the work outputs. | all |
| `shell_path` | The deployed `.p3d` in the mod tree; read-only, used for transplant. | repaint, gates, transplant |
| `struct_shell_in` | The work shell that feeds the structural builder. | `rip_p3_structural` |
| `out_path` | The full output `.p3d` of the builder, in work. | `rip_p3_structural` |
| `report_path` | The structural build JSON. | `rip_p3_structural`, gates |
| `geo_npz`, `geo_meta` | Phase 2 geometry and material npz and json (group). | builder v2, repaint |
| `locators_path` | The rip's `Locators.xml` (memory points and dimensions). | `rip_p3_structural` |

## Transform and physics

| Field | What it is |
|---|---|
| `transform{LIFT, hub_lift, contact_y, wheel_hub_rip_y}` | Derives `Y0 = (wheel_R - wheel_hub_rip_y) + LIFT`. `hub_lift` decouples the hub from the body lift (a rally lift is not a hub lift: `hub_lift=0` leaves the wheel at the knuckle). |
| `WHEEL_R` | Radius of the mounted wheel, equal to the real item radius. 0.3637 against a mounted 0.34 cost "wheels up". |
| `TARGET_MASS` | Target mass in kg for `#Mass#` in the Geometry LOD, cross-checked against public FH6 stats. |
| `seats{driver_x,y,z}` | The seats anchor. |

## Visual builder and structure

| Field | What it is |
|---|---|
| `builder{}` | Builder v2 policies: `interior_out` (prox_int), `budget` (merge classes with an authored LOD; micro-classes verbatim plus auto-full by inflation), `negate_classes`, `skip`, `glass_int_policy`. |
| `interior{viewpilot_subset, viewpilot_full}` | One interior (the prox_int pattern): full goes to resolution 1.0, a subset of at most 16k goes to resolution 1100. `viewpilot_full` is the BRZ decision (known lag); car number two uses the subset. |
| `viewpilot_parts` | Deprecated (Task 11 R2). Do not use. |
| `sedanwheel`, `crew_driver`, `crew_cargo` | Vanilla proxy paths, written without `.p3d`. |
| `shadow{max_faces}` | Shadow LOD budget (at most 5000; 40 degree dissolve). |
| `dual_tag` | componentNN dual-tag on. Mandatory; off only for the negative fixture. |
| `collision{chassis, dmgzones, seat_con, refill, crew}` | An exact box override (BRZ) or the bbox-bands fallback (other shapes). dmgzones equal hitpoints equal `config.componentNames`. |

## Legacy and in-flight gates

| Field | What it is |
|---|---|
| `gates{import_report, gb_paths, gbplus_new, gbplus_ref, bands}` | gates_v2 wiring: multi-anchor G0 (`import_report` is mandatory, fail-closed), Gb and Gb+ winding, per-profile bands. |
| `gate{proxy_dir, chunk_prefix, body_selections, exclude_selections, raycast, twin_eps_mm}` | gate_car (see-through): filter by body selection, the twin test and the complete raycast parameters. |
| `artifact_gates{perf_budget, lod_semantics, interior_rayfan, glass_occ, winding}` | The 8 fail-loud gates of the ledger. Calibrations are always scoped to evidence (never disable a gate). The BRZ has approved overrides (visual 231k, WARN only) that car number two does not inherit. |

## (s1) Legacy blocks: do not copy to the next family B car

| Field | What it is |
|---|---|
| `source{car_root, game_path, importer, manifest_dir, work_stem, import_report, blender_exe, material_type_overrides?}` | The rip paths and the derivation of every front-end work path (`<stem>_p2_raw.blend`, `<stem>_p2_geo.npz`, `<stem>_material_map.json`). `material_type_overrides` is an optional list of `{part, mat_name, mat_path, type}`; each entry must match exactly one visible mesh or the map fails closed. |
| `intake{budgets{visual_total_faces_max, viewpilot_resolved_max, shadow_faces_max, uv_uniq_min, dup_face_rate_max}, ladder_policy}` | Intake budgets plus the `authored_lod_by_budget` policy, giving `lod_plan.json` (part to authored LOD). Fails if no plan fits. |

## Usage rules

1. A missing required key is a FAIL that names the key. There are no silent defaults.
2. Calibrations and `exceptions` carry an evidence note (`*_note`) and stay scoped to the profile: they are the history of one car, not pipeline doctrine.
3. A schema change updates this file in the same commit; it is the contract car number N reads.
4. `material_type_overrides` does not replace the global classification by folder. It keeps `source_type`, records `override=source.material_type_overrides` and is admitted only with the exact identity `part + mat_name + mat_path`. (Exact claim `CLAIM-R21-RIP-MATERIAL-OVERRIDE-SCHEMA` in the import project's records.)
