---
name: rip-vehicle-import
description: "Guides the import of a ripped racing-game car (a Grub rip that is proxy-split and has moving doors, hood and trunk, called family B) into a drivable DayZ car: the six contract deltas, the single asset-contract ledger entry, the B1 to B7 check allowlist, the human visual signoff, the session A classification viewer and five symptom cookbooks. Use when the user imports a ripped racing-game vehicle or a non-Forza Grub rip, or when such a car shows no get-in prompt, wheelPresent=0, a white body, an invisible attachment or no door radial. For a vanilla-style CarScript car use dayz-vehicles."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /rip-vehicle-import

The day-0 critical path for the next ripped racing-game car: a Grub rip (`.modelbin` and `.carbin` source files) that is split into proxies and has moving parts. This is the family B adapter, change 2. The import project's own records call its three cutovers CAMBIO-0, CAMBIO-1 and CAMBIO-2; this skill writes them as change 0, change 1 and change 2.

Follow `skills/_shared/dayz-conventions.md`.

## What this skill ships and what it expects

- **Ships:** this adapter, the classification viewer (`export_car_glb.py` and `classify-viewer\index.html`) and the reference files listed at the end.
- **Expects:** the import project, written `<vehicle-import>` below. Its scripts, contracts, profiles and goldens are not in this repo. Every gate and primitive named here runs from that project. When a canonical path is missing, stop; never substitute a copy or another tool.
- **Evidence status:** the facts about the import project, its gates and its measured cars (SUB_BRZ, sub_wrxsti_04, MercedesAMGLF, LFQuad, LFQuad3, LFHeli) come from that project and are not yet checked on `P:\`. Facts about the vanilla game cite the file on `P:\`; those citations are in the cookbooks.
- **Scope:** if the asset is already in flight, use its frozen runbook. If an entry that applies is missing, STOP. The previous runbook is in `references/history-family-b-runbook.md` and is not executable. A ForzaTech or ForzaDayZ rip belongs to the author's `forza-to-dayz` skill, which uses the same family B template and is not shipped here. A vanilla-style `CarScript` car that is not a rip belongs to `dayz-vehicles`.

## Six mandatory deltas

| Field | Family B contract |
|---|---|
| Axes and units | Source `<vehicle-import>\rip\media\cars\<car>\`. Net transform `DayZ=(-Fx, Fy+Y0, -Fz)`, in meters, with no axis permutation and `det=+1`. `Y0` is measured and sealed in the ledger entry, never inherited from another car. Contract verified in `<vehicle-import>\tools\fit_transform.py:5-15,107-108`. |
| Monolithic or proxy-split | A host shell with the structural LODs; visual parts that exceed the budget, and attachments, are instanced as proxy submodels. Do not use a monolith as a silent fallback. |
| Moving parts | Doors, hood, trunk and wheel items keep their own identity, their measured pivot and their item, slot and proxy wiring. They are not merged into the shell. |
| Frame authority | The donor (golden) frame rules for structure; the source frame rules for imported visuals. Every conversion is tested with independent anchors. Never validate a part against a point produced by the same transform. |
| Golden | `<vehicle-import>\goldens\family-b\civiliansedan\r1\q1-structure.json`, revision `family-b-civiliansedan-r1`, 3,219,555 bytes, SHA-256 `3174D511F2761EE2F4E003694F566D7D92180BB30CE3479A8FA5F1EAA7C45AEB`; donor hashes in `golden-manifest.json`. It is structural, not clone-ready: an empty `mass_array` and proxy warnings require STOP before copying per-vertex mass or declaring full parity. |
| Checks allowlist | Only B1 to B7 from the table below. No legacy gate, snapshot or workspace copy widens the lane. |

## Source door inventory

Measured on 2026-08-06 over the library of 651 rips.

- A two-sided door container can come from either side: the BRZ provides only `doorlf`, `SUB_WRXSTi_04` provides only `doorRF_a`, and `FOR_BroncoRaptor_22` mixes sides (`doorLF_a`, `doorLF_b`, `doorLR_b`, `doorRF_a`). The real rule is "one side per container, whichever it is". Do not assume LF when classifying, counting doors or synthesizing the mirror.
- Variants `_a` and `_b` of the same door container are interchangeable platforms (the removable Bronco doors). Session A chooses one variant as INCLUDE and justifies the rest as EXCLUDE.
- A jamb, handle or door card without its `door<side>_<x>` panel means the door is merged into the bodywork (`BMW_M4_14`, `FOR_2_GT40_66`). This is not another naming convention; the part that could open does not exist in the rip.

## Single ledger entry and identity checkpoint

- Full template: `<vehicle-import>\contracts\asset-contract.json`. Review schema: `<vehicle-import>\contracts\asset-contract.schema.json`.
- The per-asset copy is named exactly `asset-contract.json`. It is the third and final day-0 file and replaces every parallel inventory or decision list: do not produce `source_inventory.json`, `manifest_decisions.json`, separate tombstones or any other list.
- Session A and B export: the human runs `<vehicle-import>\scripts\blender_export_asset_contract.py` on the collections `DZ_INCLUDE`, `DZ_EXCLUDE` and `DZ_MOVABLE`. The JSON is import evidence; after that the ledger entry rules.
- One primitive: `<vehicle-import>\scripts\asset_contract_checkpoint.py`, which prints its version on stdout. Copying it into a run is forbidden.
- Session A and B are imported with `import-blender`. After converting, `check` is the only `capability=LINEAGE_CHECKPOINT`.
- `PASS` allows work to continue only within the capability it issued. `DECISION_REQUIRED` goes back to the human. `TOOL_FAIL` blocks; it does not authorize touching geometry and is not recorded as an asset failure.
- Coverage is N:M. Every `INCLUDE` and `MOVABLE` appears in a `derived_from` inside an authorized operation; each justified `EXCLUDE` is its own tombstone. The source and the output do not have to be equal.

## Allowlist B1 to B7 and canonical location

| ID | Contract and location | Status for a new family B car |
|---|---|---|
| `B1_BINARIZE_LOAD` | Three-state oracle `PASS / CAPACITY_FAIL / OTHER_FAIL`: `<vehicle-import>\scripts\p3d_vertex_gate.py`. | Available; authority shown with a known-good model, a `CAPACITY_FAIL`, an `OTHER_FAIL` and residual ODOL. |
| `B2_DEPLOY_IDENTITY` | `<vehicle-import>\scripts\rip_build_identity.py --stage` (`:420-442`). | Available. |
| `B3_VEHICLE_PARITY` | `<vehicle-import>\tools\verify_rip_car.py` in contractual mode (`:1538-1546,1734-1736,1817`), never the legacy `build_checks()`. | Available. |
| `B4_CREW_ACTIONS` | `<vehicle-import>\scripts\rip_action_contract_gate.py` through its real CLI (`:732-742`). | Available. |
| `B5_DOOR_ALIGNMENT` | `<vehicle-import>\scripts\rip_door_engine_alignment_gate.py` through its real CLI (`:513-515`). | Available. |
| `B6_NATIVE_DOOR` | `<vehicle-import>\scripts\rip_native_door_contract_gate.py` through its canonical CLI (`--profile`, `--mlod-stage`, `--odol-stage`, `--debinarizer-scripts`, `--out`). W2 (`--matrix-authority` plus `--matrix-out`) is an optional extension, not the base authority. | Available; family B authority shown with a non-BRZ profile, the vanilla golden, a structural mutation and an instrument failure. |
| `B7_VISUAL_SIGNOFF` | Render: `<vehicle-import>\scripts\rip_assembled_viewer.py`. Verdict: `<vehicle-import>\scripts\rip_visual_signoff.py` (`--render`, `--verdict`, and the check with `--out`). | Available; first used on sub_wrxsti_04 on 2026-08-16, when the user's eye found in minutes four defects that B1 to B6 had passed. |

**One location.** Each primitive and gate runs only from its canonical path above. Copying it to `work\`, `sNN\`, `_validation\`, `.superpowers\sdd\` or any run workspace is forbidden. Existing copies are evidence snapshots: they are kept, they can be hashed, and they are not executed. If the canonical path is missing the result is STOP, never "use the newest copy".

## Classification viewer (session A review without Blender)

`classify-viewer\index.html` is a Three.js viewer for reviewing and reclassifying session A by click. It reads a GLB with node extras written by `export_car_glb.py` and collects deltas that the agent applies to the `.blend` with a headless script. It is advisory: authority stays with the `.blend`, then the export, then the ledger entry. Usage and the data contract are in `references/classify-viewer.md`. First used on sub_wrxsti_04 (2026-08-06).

```cmd
blender --background --python-exit-code 1 --python "<skill-dir>\export_car_glb.py" -- --blend <sessionA.blend> --out <dir>\car.glb
```

## B7: visual signoff before the build

First used on 2026-08-16 on sub_wrxsti_04.

B1 to B6 measure names, face counts, hashes and logical matrices. None of them can see a colour or the orientation of a proxy. On 2026-08-16 the user opened the WRX in a viewer for the first time and found, in minutes, four defects that the whole allowlist had passed:

- 64% of the car in one material and the whole interior in another. The import recorded `material_map: null` and sent 37 named parts (badges, mirrors, exhaust, jambs, skirts, underbody, suspension arms) to the bodywork paint bucket.
- The four wheel proxies written with the identity matrix, all four the same, when vanilla writes two mirrored frames, one per side. The same frame plus mirrored anchors means one side is mounted backwards, by arithmetic.
- The 176 mm vanilla sedan wheel instead of the car's own wheel.
- A bodywork colour that nobody had verified.

Half of the tool already existed. `rip_visual_sheet.py` renders artifacts and its own docstring says "renders, does not judge", but it draws the geometry in gray and part by part, so it could show none of the four. B7 is the other half.

Run it in this order and do not skip the middle step. Use absolute paths: the work spans two trees, `<vehicle-import>` (scripts, profiles, work) and the DayZ projects folder mounted as `P:\` (the deployed mod), and a relative command runs from only one of them. The first real B7 run failed with `can't open file ... No such file or directory` for exactly that reason.

```cmd
set FZ=<vehicle-import>

python "%FZ%\scripts\rip_visual_signoff.py" --car "%FZ%\profiles\<car>.json" ^
       --render "%FZ%\work\<car>_viewer.html"
   REM  (the human opens it and looks; the agent cannot do this step)
python "%FZ%\scripts\rip_visual_signoff.py" --car "%FZ%\profiles\<car>.json" ^
       --verdict pass^|fail --by "human:<who>" --note "<what you saw>"
python "%FZ%\scripts\rip_visual_signoff.py" --car "%FZ%\profiles\<car>.json" ^
       --out "%FZ%\work\_gates\b7.json"
```

Three rules make it a gate and not a rubber stamp:

1. **The render is assembled and has materials.** Shell, chunks, interior, the removable parts in their proxies and the wheels in theirs, with the colours of the rvmats that ship. Floating doors and inverted rims appear only when the car is assembled, not in loose gray parts.
2. **The verdict is tied to the bytes.** It carries the sha256 of every artifact that was viewed, and the check hashes them again. Rebuilding a part makes the signoff stale, not old, and the gate stays red until someone looks again. It is the lesson `positive_control` already paid for: a control that points at a path the next build overwrites is a tautology.
3. **It fails closed.** With no verdict the result is `NO_EVIDENCE`, never PASS. A verdict that covers fewer artifacts than the car has now is FAIL: a part that was not shown cannot be approved.

Signing for the human invalidates the whole gate. The `--verdict` command exists so the signature has a name and a date; an agent that runs it in the human's place forges it.

Two traps the render hides, both paid for on the same day:

- DayZ is left-handed and three.js is right-handed, so passing the coordinates through unchanged is a reflection. A mirrored car looks perfectly plausible until you read a badge; brand text is the calibrator.
- Proxy placement is `vertices @ effective_frame.T + anchor` with `effective_frame = MLOD_PROXY_CONVENTION_FRAME @ raw_frame` (`rip_detachable_doors.py:55-61,171-176`). Deducing it by eye from the proxy triangle placed each door one meter from the car.

## Symptom to cookbook index

| Symptom | Cookbook |
|---|---|
| No get-in prompt | `references/cookbook-get-in-missing.md` |
| `wheelPresent=0` | `references/cookbook-wheelpresent-0.md` |
| White car or missing texture | `references/cookbook-white-car.md` |
| Attachment invisible while its simulation works | `references/cookbook-attachment-invisible.md` |
| No door radial | `references/cookbook-door-radial-missing.md` |

This is the only index. Do not create an `INDEX.yaml`, a cookbook router or another symptom table.

## Day-0 sequence

1. Arrive here from the family selector of `dayz-vehicles`: the asset is a new Grub rip, proxy-split, with moving parts.
2. Open one ledger entry, `asset-contract.json`, created from the canonical template, and verify the source revision, `Y0`, the golden revision and the status.
3. The human classifies in Blender. The primitive captures the hash and the inventory and imports the lists and transforms into that same ledger entry. The agent neither opens nor maintains the schema or the export as state documents.
4. Check that B1 to B7 are present at their canonical paths, without executing snapshots. The allowlist is complete; any canonical absence is a STOP.
5. Convert while keeping provenance and require `LINEAGE_CHECKPOINT=PASS`; the other two states block.
6. Execute only the allowlist. The final live test stays separate from the preflight.
7. If one of the five symptoms appears, open only its cookbook. For any other symptom: STOP and an explicit diagnosis.

## Step 5 conversion rail

Work item SP-363; first used on sub_wrxsti_04 on 2026-08-06.

The car profile declares `source.asset_contract` (the path to the ledger entry). That turns on the contract mode of `rip_p2_import.py`: the INCLUDE and SHADOW lists are projected from the ledger entry by `scripts\rip_contract_source.py` (fail-closed on homogeneity per container), never from `manifest_decisions.json`; the far shell is deferred to the human classification; the G0 anchors come from the profile (`source.g0_anchors`, pairs of `[part, locator]`). `rip_p2_import.py` and `rip_contract_source.py` are scripts of the import project and are not shipped here. The three commands, in order:

```cmd
blender --background --factory-startup --python-exit-code 1 --python scripts\rip_p2_import.py -- --car profiles\<car>.json
python scripts\asset_contract_checkpoint.py import-conversion --contract <ledger-entry> --import-report <report> --contact-y-m C --hub-y-m H --lift-m L --y0-m Y0 --responsible "machine:rip_p2_import@<car>" --approved-by "human:<who>" --out <ledger-entry>
python scripts\asset_contract_checkpoint.py check --contract <ledger-entry>
```

- `--python-exit-code 1` is mandatory. Without it Blender exits 0 even when the Python script dies; on the first run a failed G0 passed as "completed". This applies to every headless Blender launch, not only this step.
- `import-conversion` validates the derivation `Y0 == contact - hub + lift`, the multiset match of object names per container (report against inventory, blind to Blender's `.NNN` suffixes) and that no excluded part was imported. It seals the 1:1 lineage `AXIS_UNIT_TRANSFORM` plus the frame, and it seals once: a retry returns `CONVERSION_ALREADY_IMPORTED`.
- A new profile starts minimal (see `profiles\wrx.json`): the source block, the anchors, the measured transform and `WHEEL_R` equal to the mounted wheel radius. Copying keys from `profiles\brz.json` is forbidden; they are scars of that one car. The legacy schema is in `references/profile-schema.md`.
- Known landmines further down the line, due for the next round of work: `rip_p2_group.py:33` hardcodes `IN_BLEND` to the BRZ, and `rip_p3_structural.py:715` defaults to `brz.json`.

## On Linux

Everything above is the Windows workflow and stays valid there. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in the shared Linux and Proton notes (`linux-proton.md` among the shared packs under `skills/_shared/`); this section only says what changes for this skill.

- Pack, sign and binarize with dayzmake 1.0.0 or later, bzed's DayZ fork of armake2 (https://github.com/bzed/dayzmake), pinned to `v1.0.0`: the release binary `dayzmake-v1.0.0-debian-trixie-x86_64.tar.gz` from https://github.com/bzed/dayzmake/releases/tag/v1.0.0, or `cargo install --git https://github.com/bzed/dayzmake --tag v1.0.0`. Use `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. Upstream armake2 is no substitute: it is built for Arma, its V3 file hash leaves out `*.c` files (dayzmake v1.0.0 includes them) and it lacks the DayZ-only functions dayzmake keeps adding. The `dayz-mod-pack.sh` wrapper wraps them (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`); its notes are in `dayzmake-linux.md`. The author's 2026-11-03 comparison of a textured cube against Bohemia's binarize from a `P:` root matched byte for byte (fork commit `7dcb3cf`, then still named armake2; `v1.0.0` contains it). That is not an in-game ODOL check.
- `P:\` is a plain directory mapped by `dayz-proton.sh init <dir>`; a `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...`.
- Object Builder and TexView run under Proton: `dayz-proton.sh gui ObjectBuilder <p3d>` and `gui TexView <paa>`. Object Builder opened and displayed a model; editing in it was not exercised. The offline checks (the tools under `scripts/tools/py3d/`, `scripts/tools/dayz-model-preflight/` and `scripts/tools/dayz-3d-viewer/`) are Python and run natively.
- In-game checks: the Linux notes of `dayz-test-ingame`.

## Building, testing and publishing the mod

When this work has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), follow the loop and the rules every mod task needs in `dayz-mod-dev`, the entry point for mod development.

## References

Open only the file the current step needs. All are in `<skill-dir>\references\`.

| File | Open it when |
|---|---|
| `references/classify-viewer.md` | Setting up or using the session A classification viewer: the Three.js files it needs, the steps per car, the GLB data contract. |
| `references/profile-schema.md` | Reading or repairing a `profiles\<car>.json` of a car already in flight (legacy schema; not a template for the next family B car). |
| `references/cookbook-get-in-missing.md` | The get-in prompt does not appear: the ordered guards of `ActionGetInTransport`, the instrument that names the guard, the right-hand-drive seat table. |
| `references/cookbook-wheelpresent-0.md` | `WheelCountPresent()` is 0 while `WheelCount()` is 4: no traction, the body sinks, no RPT error. |
| `references/cookbook-white-car.md` | The car is white or untextured on a dedicated server but fine with file patching. |
| `references/cookbook-attachment-invisible.md` | A wheel, door or rack item is attached and simulates but does not render: proxy frames, the `Proxy` class name rule, `ProxyVehiclePart` against `ProxyAttachment`, rifles and tools on one rack. |
| `references/cookbook-door-radial-missing.md` | A door shows no radial action: which of the three door mechanisms the vehicle uses and the trap of each. |
| `references/history-retired-artifacts.md` | Someone asks for one of the seven document types change 0 retired (freeze specs, readiness reports, per-run manifests and so on). |
| `references/history-canonical-path.md` | Working on a car started before change 0: the former day-1 checklist and the 12-step pipeline. |
| `references/history-family-b-runbook.md` | Diagnosing a car in flight with the complete pre-change-1 runbook: legacy rules, smoke test notes, recurring defects, lift, doors, proxy frames, the headless render gate, glass winding, the winding lineage gate, the material override. History only, no authority. |
