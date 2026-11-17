# History: the complete family B runbook before change 1

The full body that change 1 removed from the critical path: the change 0 cutover, the legacy process rules, the smoke test notes, the recurring defects and the dated lessons on lift, doors, proxy frames, render gates, glass and winding lineage.

History only, no authority. The active adapter is the skill's `SKILL.md`; no command or gate is executed from this file. It describes the import project (`<vehicle-import>`) and its measured cars (SUB_BRZ, MercedesAMGLF, LFHeli OH-1 and HH-60G) and is not yet checked on `P:\`, except where a vanilla file is cited.

## rip to DayZ: runbook with the change 0 cutover (2026-08-05)

The rules were measured on the SUB_BRZ build, sessions s2 to s32; the consolidated research is `<vehicle-import>\reviews\2026-07-11-research-metodo-import.md`. They are given only in their final verified state. The historical why (root cause analyses, red herrings, superseded rules) is in the rip import history of the vehicles pack (`skills/_shared/vehicles/rip-import.md`); read it as history, not as procedure. The workspace is `<vehicle-import>`, kept outside any cloud-synced folder. The orchestrator is `scripts\import_car.py --car profiles\<car>.json`, a legacy and in-flight orchestrator; it is not the runner of the new family B lane.

## Change 0: the family B cutover (new assets only)

The cut applies to the next proxy-plus-doors car started from scratch. SUB_BRZ, MercedesAMGLF and any profile already open keep their runbook, their receipts and their frozen gates; they are not migrated while work is in flight.

The family B lane stops requiring these as inputs: F0 and freeze specs, readiness reports, the import validation matrix, per-run manifests, parallel part lists, separate alignment notes and the pilot report. Change 0 creates no substitute. The rip's `Manifest.xml` is kept as source data: it is not a manifest derived per run.

The earlier locations and procedure are in:

- `history-canonical-path.md`: the snapshot of the earlier checklist and pipeline.
- `history-retired-artifacts.md`: the catalogue of the seven retired types.
- The rip import history of the vehicles pack (`skills/_shared/vehicles/rip-import.md`): technical history and root cause analysis, which may be consulted during diagnosis.

### Offline allowlist of family B

Only these entries may run in the happy path of a new family B car:

1. `B1_BINARIZE_LOAD`: `binarize` with `PASS / CAPACITY_FAIL / OTHER_FAIL`.
2. `B2_DEPLOY_IDENTITY`: stage to deployed PBO with `rip_build_identity.py --stage`.
3. `B3_VEHICLE_PARITY`: the contractual mode of `verify_rip_car.py`, never the legacy mode.
4. `B4_CREW_ACTIONS`: `rip_action_contract_gate.py` by its real signature, invoked directly.
5. `B5_DOOR_ALIGNMENT`: `rip_door_engine_alignment_gate.py`, invoked directly.
6. `B6_NATIVE_DOOR`: the family's native post-binarize contract.

Every gate outside that list stays manual and is not run to get a routine green. That includes `gates_v2`, the complete artifact suite, the visual ladder, budgets, winding, glass, materials, rayfan, perf and the SUB_BRZ regressions. The final live test is kept apart: it is not an offline gate per build. (B7, the human visual signoff, joined the allowlist later, on 2026-08-16; see `SKILL.md`.)

### Executable state of the cut

No single runner carries out this allowlist. `import_car.py` runs the legacy verifier after `struct`; `--to gate` runs G0, Ga, Gb and Gb+; `--regression` runs the long suite. On top of that, at the time of this snapshot `<vehicle-import>` held no canonical copy of the B1 oracle, and the gate available for B6 was sealed to S42 and SUB_BRZ. So a new family B car stopped before geometry when B1 or B6 was not available: they are not replaced by legacy documents or by approximate gates. (The skill's current table lists both as available.)

The remaining sections keep knowledge and commands for cars in flight or for diagnosis. For a new family B car, the historical words "canonical", "mandatory" or "every car" further down do not widen the allowlist above.

## Legacy route: the 3 process rules before change 0

1. **No visual fix without a measured mechanism probe and a negative fixture.** The roughly 10 lost rebuilds of car number one were hypotheses with no measurement, validated in game. Probe first (raycast, census, multi-angle probe), fix afterwards, and a permanent gate when the fix closes.
2. **Performance is an entry requirement, not a rescue phase.** Budgets and the inventory of authored LODs come before anything is assembled (step 2). The BRZ at 231k faces froze for 10 seconds; the vanilla sedan has 14.6k.
3. **Offline never approves visuals.** The best offline verdict is `NEEDS_INGAME`; the engine's render (the MCP smoke test, then the user's eye only at the end) is the only visual judge. Two rebuilds with no progress mean STOP and a new diagnosis, never a third blind attempt.

## Legacy route: the day-1 checklist and the 12-step pipeline

The runbook carried the day-1 checklist (8 steps) and the 12-step `import_car.py` pipeline here. Both are kept, word for word in substance, in `history-canonical-path.md`.

## Manual diagnosis and in-flight route: the legacy MCP smoke test

- `world_spawn` expects an engine vector `[x, y_up, z]`; the connect log prints `[x, z, y_up]`.
- `camera_set` suppresses the player's controls, so use it only with an empty box. For first person, use `vehicle_get_in_client` and capture without `camera_set`.
- A capture with the display asleep is a black frame: bring the window to the foreground and wiggle the input first.
- Launch the server and the client through a `.bat` with `start ""` (detached); poll UDP 2302, not TCP.
- The DayZ box is exclusive between sessions. Verify who owns the port by its `@Mod` before killing anything; a process that belongs to someone else is not to be touched. Use the server's stock mission, not the dev one.
- Less than 2 GB of free RAM with low working sets means kernel zombies: ask for a restart before a rebuild or a launch.

## Manual diagnosis: recurring defects kept on record

This is a list of recurrence, not of mechanism: the user has seen each row in game on two or more projects. For a new family B car it is a list to consult during diagnosis, not a checklist that runs on every build. Where the mechanism is closed it is cited; where it is not, that is said.

| Defect seen | Projects | Where the mechanism is |
|---|---|---|
| Asymmetric headlights: one side has the light, the other only the plastic | SUB_BRZ, MercedesAMGLF | Open. Suspect a selection, `hiddenSelections` or a proxy missing on one side; compare left and right explicitly, do not look at only one. |
| Wheels correct in hand, invisible when mounted (the proxies do not activate) | SUB_BRZ, MercedesAMGLF | The wheels and doors as items section of the config and model.cfg topic of the vehicles pack (item, slot and proxy wiring; `skills/_shared/vehicles/vehicle-config-and-modelcfg.md` section 8), the "attachment or geometry silently missing" part of the structural parity topic (`skills/_shared/vehicles/vehicle-structural-parity.md`), and `cookbook-attachment-invisible.md`. |
| See-through from the interior (floor, roof, handlebars) | several | The visual gates and winding topic of the vehicles pack (`skills/_shared/vehicles/visual-gates-and-winding.md`): an imported single-sided shell, and the rule that the primary gate is topological uniformity per piece, run before the raycast. |
| A texture with the pattern applied wrongly, "the livery of another part" | OH-1, MercedesAMGLF (suspected) | See the OH-1 precedent below. |
| Doors that are not one item per door with a proxy that depends on the door being equipped | MercedesAMGLF | The same wheels and doors as items section. The vanilla pattern is one item per door, with the item's `inventorySlot` equal to an entry of the car's `attachments[]`; the chain is in `skills/_shared/vehicles/attachments-and-crew.md`. |

**The OH-1 precedent of a wrongly applied texture: two mechanisms, both measured.** They were confused with those of the HH-60G on 2026-08-02; they are written here so they can be found.

1. **Stamping by selection instead of by piece.** `TEX_CO_MAP` assigned by selection, so `Cockpit` (13k triangles), which belongs to the selection `fuselage`, received `oh1_fuselage_co`. Fix: stamp by piece. (LFHeli OH-1 R2, 2026-07-19.)
2. **UV collision in a single atlas.** 97.6% of the cells of one group lay inside the footprint of another (rotor 92.9%, tail 100%). The visual giveaway: a fuselage registration ("G-263") painted over the blades. (LFHeli OH-1 R21, 2026-07-27.)

Two method traps from that case, which apply to any texture fix:

- Before proposing "reassign texture X to piece Y", verify by hash that the `.paa` files really differ. On the OH-1 all four were byte-identical (`16B0FD97...`), so the proposed fix was a provable no-op.
- Measure the real universe of affected faces before sizing the job: 6,420 were claimed there and there were 25,444, four times as many.

The process corollary: when the user says "this already happened on the previous car", that is the promotion signal. The row goes in here the same day, without waiting for the diagnosis. Origin: on 2026-08-02 the user reported 3 of 9 defects as an explicit repeat of SUB_BRZ.

## References of the runbook

- `profile-schema.md`: the `profiles\<car>.json` field by field.
- The vehicles pack (`skills/_shared/vehicles/`): the rip import history (why each rule exists; `skills/_shared/vehicles/rip-import.md`) and the structural contract with the engine (`skills/_shared/vehicles/vehicle-structural-parity.md`).
- The generic DayZ vehicle checklist, the numbered invariants (0 to 35, spread over six files), indexed under "Numbered invariants" in `skills/dayz-vehicles/SKILL.md`.
- `<vehicle-import>\reviews\2026-07-11-research-metodo-import.md`: the consolidated research that set the priorities and this runbook.

## Lift or translation of geometry: no double transform with proxied chunks

Added 2026-07-14, session s34.

When you raise or move the geometry of a car whose chunks are instanced in the shell (`sub_brz.p3d`) through proxies (`proxy:\<MOD>\proxies\brz_chunk_*`), the effective displacement of each chunk is the delta of the proxy anchor in the shell plus the delta of the chunk's local geometry. Raising both doubles it. Origin, s34: "raise the car 7 cm" raised the chunk proxies in `sub_brz` by 0.07 and the geometry of each chunk by 0.07, an effective 0.14. The bodywork came out misaligned with gaps, the brake discs floated (the proxy of chunk_03 moved 0.07 while the discs inside stayed at their original Y) and the car floated (the chassis Geometry was raised). The diagnosis was confirmed three times, independently.

Rules:

1. Raise the geometry of the child (the chunk) or the anchor of the proxy, never both. Recommended: geometry only in the leaf assets, and chunk proxies at identity (anchor untouched).
2. Mixed chunks (sprung and unsprung parts, for example chunk_03 with tunnel and brakes, chunk_04 with trim and suspension): do not move the whole proxy. Partition by component or selection (brakes, suspension and hubs fixed; body and trim plus the delta), with no point shared between the groups.
3. Geometry LOD: raise the chassis (the body's componentNN), not the hubs (the wheel component and `wheel_*_damper_land`). `#Mass#` is a scalar and does not depend on Y: the mass does not change, the centre of mass does.
4. Wheels, brakes and suspension do not move; they touch the ground. Watch out: `drivewheel` is the steering wheel, not a road wheel. It moves with the body and must not be left fixed through a classifier error.
5. The mandatory gate is the effective delta (parent delta plus local delta) per instance, not the local delta per file. Negative fixture: parent +d plus child +d (so +2d) must fail. In s34 the census verified each file at +0.07 but not the effective value, so it passed the gate and broke the car.
6. Ride height through config (suspension stiffness and travel) gives no exact offset that can be verified, and it changes the handling. For an exact lift use geometry. Floating after a lift is `NEEDS_INGAME`: measure root, contact and suspension in Diag; do not patch it by lowering the Geometry.

Reference: `<vehicle-import>\work\s34_stance_audit_A.md` (the full spec).

## Doors and movable parts: the rip already ships them cut

Added 2026-07-17, session s36. Read the Manifest before planning any cut.

The source game versions each movable part as an independent model, because the game animates them (`MojoConfig.xml`, `doorLF/RF`). In the Manifest: `scene\exterior\doors\door<lf>_a.modelbin` (the sheet metal, with authored LODs), `doorhandle<lf>_a`, `doorjamb<lf>_a` and `scene\interior\doors\doorcard<lf>_a` (the interior panel). Only the left side; the right is a mirror, the standard RF pattern. (The door inventory of 2026-08-06 in `SKILL.md` later showed the container can come from either side.) The hinge axes are ready in `Locators.xml`: `carLocator_door{LF,RF}`, plus `doorHandle{LF,RF}` and `entryDoorLF`. That is the axis `class Doors` or AnimationSources needs, with the same transform as the geometry.

Rules:

1. Day 1: classify doors, hood and trunk as their own lane (separate assets plus the locator axis). The body is assembled without them; the door comes in as an attachment or proxy with a rig.
2. If an earlier assembly merged them into the body (chunks), the cut is solved by geometric matching against the transformed rip piece (tri_signature, centroids), never by manual marking in Blender.
3. When a phase that builds an artifact closes (for example door `.p3d` files with their LOD ladder), record it in the live state with a path and a checkpoint. SUB_BRZ s34 and s35 planned "manual marking of door cards" with the doors already built in `work\s33_f2_doors\` (C2b): two sessions budgeting a problem that did not exist.

Origin: SUB_BRZ s36 (2026-07-17). Root cause analysis: the doors and movable parts section of the rip import history in the vehicles pack.

## Attachment render: proxy frames and locator calibration

Added 2026-07-18, session s37.

1. **The attachment renders from the proxy of the visual LOD, with its frame.** The complete rule is `cookbook-attachment-invisible.md`: the frame per side of step 8 (wheels) or the uniform frame measured on the control (doors, `((-1,0,0),(0,0,1),(0,1,0))`), in every visual LOD plus View Geometry and Fire Geometry, point flags 63, and a `Proxy*` class equal to the file's base name (without case; `_ruined` against `_destroyed` killed the client on the swap, SUB_BRZ defect B5). An identity frame (py3d `rotation=None`) is a piece rotated about 90 degrees, hidden, with the simulation intact (defect B1). Gate: `derive_proxy_frame` equals the expected frame, plus the identity negative fixture. Diagnosing "attached but invisible": measure the frames before the item's LODs (the hypothesis of the item's LOD 0.0 was refuted in game in s37).
2. **`Locators.xml` to the DayZ frame, the empirical calibration of s37** (4 wheel locators against deployed anchors, matching to 6 decimals): `dayz_x = -Fx`, `dayz_z = -Fz`. The Y datum of a locator is not reliable (the anchors were normalized; it drifts by millimetres between wheels), so Y is derived from the geometry of the piece. The BRZ hinge axis is purely vertical (the up column of the SceneTransform). Always calibrate against a known deployed anchor before consuming a new locator.

## Headless render gate per container

Added 2026-07-17, session s38. Structural censuses do not refute visual defects.

A census (counts, bbox, flags, selections, materials) proves structure, not pose or render. A light bar lying flat on the roof fits in the same bbox as one standing up, and two rounds of fixes (s37 and s38) closed green offline gates with the car broken in game. The headless Blender render of the raw content of each container (an OBJ per LOD plus workbench, 3 angles) caught on the first run what no census saw: a light bar lying down and a duplicated floating bumper in chunk_00, broken in the file since s33 and identical to the user's in-game capture (the equivalence file equals render equals game was validated).

Rules:

1. A mandatory gate before deploying any new or edited visual piece: render the complete container before and after, not only the piece that was touched. Reusable pipeline: `<vehicle-import>\work\s39_f0_audit\render_all_chunks.py`.
2. A diagnosis of "files healthy" issued from censuses alone does not authorize blaming the runtime: render before you rule out the data.
3. Never match coverage against a reference derived from the very artifact being validated. The "lod0 recipe" for the doors described the broken item, a tautological gate that cost a whole round: the "unmatched" faces were exactly the holes.
4. Pane and glass materials: read the real alpha of the rvmat before moving faces to it. The vanilla `glass_i.rvmat` has alpha 0 in ambient, diffuse, emissive and specular, invisible by design (`P:\DZ\vehicles\wheeled\civiliansedan\data\glass_i.rvmat:1-5`); a "fix" that adds geometry with that material adds invisible glass.

## The glass of the rip is single-sided and wound inward

Added 2026-07-17, session s39. It is invisible from outside; make it double-sided.

Two premises of a research note can fall at the first attempt once the render gate is applied to the artifact the user complains about, not only to the fix. On SUB_BRZ s39 the direct render of the deployed model showed that (a) the "tipped-over light bar" was `bodyfoglights_a` in its authored pose (the rip's roof pod bar; it matched to below a millimetre), so it was no defect, and (b) the "holes in the door" were not gaps in the sheet metal (the metal renders solid with backface culling on); they were the invisible side windows. The one real cause of the windscreen, the side windows and the "holes":

1. **The glass of the source-game rip (`glass.rvmat`, `*privacy*`, `*tint*`) arrives single-sided and stitched with its winding inward.** The engine discards it by backface culling from outside: an invisible, hollow greenhouse. The definitive and cheap proof is a render of only the glass faces from outside with backface culling on and then off. If with culling off you see the whole greenhouse and with it on almost nothing, the winding is inward. It is not alpha: raising alpha does not make a culled face appear.
2. **The fix is to make the visible glass double-sided** (`glass.rvmat`, privacy, tint; never `glass_i`, which is alpha 0 and invisible by design). For each glass face add a twin with reversed vertex order and negated normal, in every visual LOD, including the ladder of the door items. From each side exactly one of the pair renders (culling discards the other), so alpha does not stack and the window is visible from both sides. Reusable pattern: `make_double_sided.py` filtered by glass material (scoped), with the structural LODs intact byte for byte (the get-in of the doors). This is the "measured exception" that the glass rule (step 6) allows for: here the rip does not bring legitimate exterior and interior pairs, it brings single-sided inward glass, so doubling is correct and preserving is not.
3. **The gate of the fix is data, not Blender.** Blender's backface culling on an imported OBJ does not reflect DayZ winding (Blender recomputes the normals; before and after come out identical). Verify per pane that there is now winding in both directions (the sign of cross.radial), that the glass count doubled, that non-glass is intact and that the structure is byte-identical. The real visual gate is in game: Blender does not judge DayZ winding.
4. **Method, extending the s38 render gate: first render the artifact of the complaint to confirm the mechanism of the defect, before specifying the fix.** It saves rebuilding things that are not broken. Here it avoided rebuilding the door (the metal was already solid) and raising alpha (the defect was winding), and redirected the work to double-sided glass, all offline before a single build.

## Winding lineage gate

`<vehicle-import>\scripts\winding_lineage_gate.py` compares the winding per face of the target against the sealed `source_face_id` and derives the expected relation from the determinant: positive is `PRESERVE`, negative is `REVERSE`. It emits `SOLID`, `INVERTED` or `MIXED` with exit codes 0, 1 and 2. A manifest, lineage or determinant that is missing, not finite or zero fails closed as `MIXED`.

This gate proves that lineage is preserved, not that visuals or collision are correct. The in-game A/B test and the View Geometry controls are still the final gate. The focused lineage suite passed 16 of 16 on 2026-07-24; no global test total is frozen because the source tree keeps changing.

## Material type override by exact identity

A material exception may be declared in `source.material_type_overrides`, but only by the exact identity `part + mat_name + mat_path`. It must match exactly one visible mesh or the map fails closed; it keeps the earlier type in `source_type` and records `override=source.material_type_overrides`.

The mechanism is verified against the source and its focused tests pass. The broad validation of the BRZ profile keeps a known, independent failure (`builder.occ_struct` still present); do not use that failure as evidence against the override, and do not hide it when stating the status of the profile.
