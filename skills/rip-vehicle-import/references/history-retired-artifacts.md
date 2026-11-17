# History: the artifacts change 0 retired

The seven document types a new family B car no longer produces or consumes since change 0 (2026-08-05), and where each one is kept in the import project.

This is a history pointer, not a working checklist. Nothing listed here is deleted. Existing vehicles keep their frozen evidence; a new family B asset does not produce or consume these seven document types in its happy path. Everything here describes the import project (`<vehicle-import>`), is not a fact about the vanilla game and is not yet checked on `P:\`.

| Retired type | Where it is kept, or its generator | Status after change 0 |
|---|---|---|
| F0 and freeze specs | `<vehicle-import>\scripts\rip_code_manifest_gate.py:3005,3012`; `<vehicle-import>\work\s39_f0_audit\F0_INVENTORY.md` | SUB_BRZ and in-flight history; manual only. |
| Readiness reports | `<vehicle-import>\scripts\smoke_checklist_f4.md:28-30`; `<vehicle-import>\work\sub_brz_final\*\receipts\offline-readiness.json` | Checklist and receipts kept; not an import input. |
| Import validation matrix | `<vehicle-import>\work\_r21_roadmap\inputs\40-validation-matrix.md` | SUB_BRZ traceability; not consumed by the generic runners. |
| Per-run manifests | `<vehicle-import>\scripts\rip_manifest.py:225-254`; the sealed SUB_BRZ manifests | Generator and evidence kept for manual and in-flight use. `Manifest.xml` stays as source data. |
| Parallel part lists | `source_inventory.json`, `manifest_decisions.json`; consumers at `<vehicle-import>\scripts\rip_p2_import.py:58-62,141-171` | Legacy consumer kept. A new family B car stops before geometry until its later path exists. |
| Separate alignment notes | `<vehicle-import>\work\_gates\s42_door_engine_alignment.json`; `work\sub_brz_final\*\receipts\brz-door-engine-alignment.json` | Technical gate outputs kept; no separate narrative note is required. |
| Pilot report | `<vehicle-import>\scripts\smoke_checklist_f4.md:32-68` | A manual smoke test is still possible; no separate pilot report is generated. |

The exact former day-1 checklist and the 12-step pipeline are in `history-canonical-path.md`. The root cause analysis stays in the rip import history of the vehicles pack (`skills/_shared/vehicles/rip-import.md`).
