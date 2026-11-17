# History: the canonical path before change 0

The day-1 checklist and the 12-step pipeline a ripped car followed before change 0, kept for cars that were started under them.

This is a snapshot of the skill body as it stood on 2026-08-05. It is not the happy path for a new family B asset. The rules describe the import project (`<vehicle-import>`) and its first car, SUB_BRZ; they are not yet checked on `P:\`, except the four vanilla facts listed at the end.

## Day-1 checklist (new car, all offline, without touching geometry)

1. Unzip to `<vehicle-import>\rip\media\cars\<car>\` (a junction if it comes from elsewhere). The shared cars `_library` is already in `rip\media\cars\_library\`; verify that the materialbins the car references resolve (the BRZ pattern was 13 of 13).
2. Write `profiles\<car>.json` from the template (see `profile-schema.md`): the `source` block, the `intake` budgets and the policies. Do not copy the surgical `exceptions` of the BRZ.
3. Step `manifest`: the inventory (INCLUDE, EXCLUDE, SHADOW `__slod`, far-LOD shells by the `LODs=` bitmask, mirror gaps by the RF `[ -f ]` probe) goes to `source_inventory.json`. Fixed traps:
   - A custom part that exists only as `__slod`: the visible one is the standard part.
   - `*wide*` parts are bolt-on flares on top of the shell. `body_a` is always included; removing it deletes the roof.
   - The `interior_a` far shell (LODs without bits {0,1}) is never close-view geometry.
   - Suspension and undercarriage are included (re-posed; the wheels rest on them visually).
   - Movable parts (doors, hood, trunk) are their own models, already cut in the rip, with the axis in `Locators.xml`. Classify them into their own lane from day 1; never merge them into the body or plan a manual cut (see the doors section of `history-family-b-runbook.md`).
4. Material map per mesh (`rip_material_map.py`): the type comes from the materialbin folder. The instance name lies (the rollcage "leather_MGL" is metal). Several materials on one part is normal (50 of 84 on the BRZ), so the map is per mesh; per part is only a hint.
5. Colour: `ManufacturerColors.bin` entry[0] (decoder `decode_color2.py`), never by eye.
6. Mass, drivetrain and distribution: public FH6 stats (game8, kudosprime, calculators.games). The GameDB is encrypted: do not mine it and do not upload it to third-party backends. Cross-checking the wheelbase from `Locators.xml` against the real specs validates the axes and units.
7. Dimensions and memory points: `Locators.xml` `SceneTransform _41/_42/_43` are x, y and z (y up, z along the car).
8. Intake gate: `lod_plan.json` (an authored LOD per part that meets the budget). It fails when no combination fits the budget. Pending decisions (stock or widebody variant, seats, extras) go to `pending_decisions[]` and must be asked; there are no defaults.

## Canonical pipeline (12 steps, the steps of `import_car.py`)

| # | Step | Hard rule | Gate |
|---|---|---|---|
| 1 | Intake and truth maps (day 1 above) | No silent defaults. | inventory + NEEDS_DECISION |
| 2 | Budgets and lod_plan | Visual at most about 120k faces. ViewPilot subset at most 16k resolved. Shadow at most 5k. uniqUV above 1. dup_rate below 2%. | The intake gate fails loudly. |
| 3 | Multi-LOD import in headless Blender | Net transform `(-Fx, Fy+Y0, -Fz)`, det +1, verified on at least 3 anchors (G0 stops on failure). | G0 |
| 4 | Topological normalization | Payload-aware dedup first. Then repair the minority by majority flood fill (a censused allowlist; a new conflict is a FAIL). Then smooth (plus cross) normals from the final winding. Forbidden: a global flip, orient-to-oracle, a fix from photos. | Gb and Gb+ plus winding_differential |
| 5 | Visual architecture | A real LOD0 shell (paint hiddenSelections and lights), proxy chunks below 65535 resolved, a dedicated `prox_int` (full at resolution 1.0, subset at 1100), shadow dissolve at 40 degrees, a ladder authored by distance. | budgets + lod_semantics |
| 6 | Glass (sub-pipeline) | The rip's double panes are preserved (a legitimate exterior and interior pair). A clone of the vanilla `glass.rvmat` (alpha 0.22 to 0.32, noZwrite). Single-sided. Twins or double-sided faces are a measured exception. Structural closure only with a gap shown by a multi-angle probe. The BRZ knobs (E_flip, C1, sunk) are profile, not doctrine. | glass_occ + probes |
| 7 | Structural (`rip_p3_structural`) | componentNN dual-tag (hubs and seats overlap 100%). A bone companion per attachment proxy. ViewGeo seats face inward with flags 0x02000000. `#Mass#` in the Geometry LOD only. `refill` (not fuelpoint). hitpoints equal firegeo dmgzones equal config. | verify_rip_car U+P, roundtrip_structural and the sedan positive control |
| 8 | Proxies | The path is written without `.p3d` (the default; a registered counterexample exists, so when in doubt verify against the control). Frame per side: x below 0 `((-1,0,0),(0,0,1),(0,1,0))`, x above 0 `((1,0,0),(0,0,-1),(0,1,0))`. Companions `wheel_X_Y` in visual, View and Fire. Model-space geometry that is not centred. Never `add_proxy` over an existing proxy (it loses the frame). | proxy identity checks |
| 9 | Config and script (the Codex lane) | `<MOD>_Base.c` always extends CarScript (CrewCanGetThrough, GetAnimInstance, GetSeatAnimationType; without it the get-in never appears). CfgMods `dir=` and backslashes. Inherit SimulationModule (do not declare it again). Vanilla slots `CivSedanWheel_*`. Petrol means SparkPlug vital and GlowPlug returning false. A complete OnDebugSpawn (identical kits for the mod and the control). Parity matrix PAR-001 to PAR-017. | CfgConvert + parity diff |
| 10 | Textures | Type to rvmat from the fleet table. Carpaint only on the paintable selection. Plastic is never re-typed (painted flares). `_co` solid and UV-invariant, plus a swatch through TEXCOORD2. The cabin from the real source (`_library` materialbins and the `TOY_*` UI; never an invented palette). High specular amplifies `_nohq` artifacts. | TYPEMAT unknown is a FAIL, plus surface_integrity |
| 11 | Deploy | Transplant (never overwrite the structural LODs of the deployed model). Atomic staging plus build identity. `.bak` files outside the compilable tree. `-Build -PackOnly` (PackOnly alone gives a stale PBO). `-include` replaces the copy list (it drops .paa and .rvmat: the white car). | G7 with 0 missing, identity and perf_budget |
| 12 | Test | The offline suite, then `NEEDS_INGAME`, then the MCP smoke test (spawn, standard captures, raycast, get-in probe), then the drive ladder, then the user: looks and feel approved in one bundled pass. | vehicle_smoke JSONL (a real INGAME_PASS, never from a prompt alone) |

## Checked on `P:\`

- Step 6: the vanilla sedan `glass.rvmat` has ambient and diffuse alpha 0.75 and the render flag `noZwrite` (`P:\DZ\vehicles\wheeled\civiliansedan\data\glass.rvmat:1-9`). The alpha range 0.22 to 0.32 in the table is therefore the import project's value for its clone, not the vanilla value.
- Step 7: the engine reads the fuel position from the memory point `refill` (`P:\scripts\3_game\vehicles\transport.c:112`).
- Step 9: the vanilla sedan script class is `CivilianSedan : CarScript` (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:1`), and its `IsVitalGlowPlug` override returns `false` (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:370`).
- Step 9: the vanilla wheel slot `Slot_CivSedanWheel_1_1` is defined at `P:\scripts\config.cpp:1089`.
