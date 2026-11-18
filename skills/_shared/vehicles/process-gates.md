# Import checks that can be trusted

How to write an offline check for an imported vehicle model that catches what it claims to: a failing test case for every rule, three exit states, controls that do not depend on the model under test, and why a config check that passes says nothing about what is on screen. Read it with `method-and-gate-calibration.md` and `deploy-gates-and-crash-fingerprint.md`. The cases below were measured on mod vehicles (a helicopter on `CarScript`, a motorbike derived from `Motorbike_02_ColorBase`, an imported sports car), not vanilla ones.

## Every rule needs a test case that makes it fail

Checking a rule against a model that works is needed but not enough. A helicopter mod's import checks were tuned against a good reference and still passed a broken model, failed the good one and accepted absurd input. Changing the model in memory showed it at once:

- Twelve proxies moved 100, 200 and 300 m away passed. The distance rule fired, but at INFO level, and the verdict counted only FAIL.
- 30,419 faces pointed at a texture that does not exist passed with no finding. The rule looked for unused files, never for missing ones.
- The reference model the suite required to pass had `dot(geometric, stored) = -1.0` on 24 of its 48 proxy vertices, the proxy triangle defect covered in `rip-geometry-and-winding.md`.
- The suite reported as eleven passing tests was seven tests with four failing, and could not start from the shipped layout because it pointed at a missing folder.

Rules for any model import check:

1. Every rule ships with two cases the suite runs: a good model that must pass, and a copy of a good model changed in memory to carry exactly the defect the rule claims to find, which must fail. A rule without a failing case is not finished.
2. No INFO or WARN inside the verdict. If it should block, it is a FAIL; if not, it is a printout outside the verdict and the exit code. A level that cannot change the result is a rule that does not exist.
3. Rebuild the reference model and check it against the rules it is meant to pass. A reference goes stale like anything else.
4. Prefer a few solid rules to many plausible ones. The rebuilt suite kept three, proxy normal agreement, referenced textures that exist and finite UVs, each with its failing case.
5. A threshold written as a bare number is suspect. Derive it from a measurement on the good model and keep the number and how it was derived in the code.
6. When a change to a check turns a passing model red, fix the rule or accept the finding; never change the expected value to make it pass. Which of the two is the owner's decision.

## Three exit states

Use exit `0` for a pass, `1` for a confirmed defect in the model or config, and `2` for could not inspect: missing or wrong format input, a parser or tool failure, an absent report, a missing row. A deliberately broken test model must give `1`, and an unreadable input must give `2`. Never treat `2` as a pass, or as a reason to repair the model.

## Controls that are really independent

- A known-good model is not a control if the axis map, orientation or measuring method used to read it was tuned on the model under test. Derive the convention separately, and use a witness that changes when the defect is present. Repeating the same circular chain on more controls adds nothing.
- Match data before and after a transform by identity, never by rounded position; see `invariants-import-mesh-and-winding.md`. Breaking this shows a false 180 degree normal change or a UV change of 1.0 on a mesh that did not change.
- When copying a mechanism from a working mod, list every place it is called. Paired state such as `SetDisabled`, input excludes, focus and active flags is set on the normal path and cleared on normal exit, forced exit, watchdog, abort and refused entry. Copying half of it leaves the lock on the least tested path. Track ownership with its own flag, make the cleanup safe to run twice, and call it from every way out of the state.

## Before any check is written

- Before deferring a feature, ask what its absence breaks and include what the engine requires. Every `CarScript` needs at least `DamageSystem` with `GlobalHealth`, as on `CivilianSedan` (`P:\DZ\vehicles\wheeled\config.cpp:5398`); a car without it can crash the game even when damage is planned for later.
- For black or see-through panels, decode the deployed `_co` texture first and measure its dark pixels. If the texture is clean, treat it as winding and get an in-game capture before flipping faces.

## A config check is not a visual check

On a motorbike derived from `Motorbike_02_ColorBase`, two config checks passed and the screen did not change. One required a duller silver material (specular 0.4) on visual LODs 3 to 6. The other required a crack material at health 0.5 and 0.3 and `"hidden"` at 0.0 in the `Front` and `Back` zones, the vanilla crack texture in it, and non-zero UVs on the glass; it never read `RefTexsMats[]`. In game the windscreen still drew at damage level 4 (the glass section of `vehicle-config-and-modelcfg.md`), and a white blob seen from afar did not change with the material: bright pixels in a centre window counted 60, 68, 39 and 23 at 40, 60, 85 and 240 m with the duller silver, 58, 68, 42 and 28 with a matte one, and looked the same with the original.

1. Name a pass by what the check reads. A check over config, stage files or the binarized model proves wiring; report it as a config pass, never as working. Judge a damage look or a far LOD look from in-game captures with a fixed camera, next to the logged state: damage level on server and client, and camera distance.
2. Take vehicle zones down the way the game does, with the call vanilla makes on contact: `ProcessDirectDamage(DamageType.CUSTOM, null, zoneName, "EnviroDmg", "0 0 0", dmg, pddfFlags);` (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:1350`; for cars see `invariants-engine-fluids-and-handling.md`). Measured in game: this swapped the damage materials on the import and on a vanilla `Motorbike_02` control, and `SetHealthMax` restored the healthy look. Runs with `SetHealth01` logged levels 2 and 4 without a swap, but they used other probe builds, so they do not show `SetHealth01` cannot swap; on clothing, scripted health steps do apply `healthLevels[]` (`_shared/textures/runtime-material-swaps.md`). Compare both with the same probe and control before blaming the method. The contact call swapped the import's body panels in three of four textured runs; in the fourth the client logged levels 2 and 4 and nothing changed, cause unknown. Repeat a run without a swap before blaming the kit or the method.
3. Give a marker a positive control. A marker that never shows, such as a saturated emissive in the incoming material, means nothing unless the same capture holds a part wearing that material from the start (the pair of frames rule in `_shared/textures/runtime-material-swaps.md`, and the self-check in `visual-metrics-and-viewer.md`).
4. A control must be able to show the change. A vanilla `Motorbike_02`'s nearly clear glass looks the same hidden or not, so it cannot witness a glass swap.
5. Know which LOD is drawn before tuning a far LOD material. Run the far look checks first: the collapsed UV count in `view-pilot-and-first-person.md` and the distance LOD rules in `invariants-lods-and-vertex-budget.md`. Those binarized models also had every material entry empty (`skills/dayz-build-pbo/references/addonbuilder-rules.md`), so a material edited in the `.p3d` was not shown to reach the screen. Unverified suggestion: give each visual LOD a colour mark visible away from the defect, and darken one material group in all LODs per build, against a control.
6. Point config checks at what ships:
   - For a zone that declares `RefTexsMats[]`, check in every visual LOD that each material meant to look damaged is listed, above all a far LOD stand-in for a listed material. The far silver sat on eight sections across `Back`, `Chassis`, `Front` and `FuelTank` in LOD 3 alone and was in no `RefTexsMats[]`, so those faces would presumably keep the healthy look on a wreck (not tested in game). The check names its deliberate exceptions (here 378 instrument faces with 41 materials left out of `Front`) and ships with its failing case.
   - Read the packed PBO and its binarized models. A check over stage files can pass on inputs other than the packed ones; the build's verdict is the PBO file table (`/dayz-launch-test`), and materials referenced only from `config.cpp` stay out of the PBO (`/dayz-build-pbo`).
   - Make the packer refuse diagnostic builds. A build with a red marker could be packed, and one of the checks would pass it.
