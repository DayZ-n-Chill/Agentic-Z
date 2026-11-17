# Process gates: negative fixtures and promoted rules

Rules for writing a model-import gate that can be trusted: a negative fixture per rule, three exit states, controls that are independent of the candidate, and why a config gate that passes says nothing about what is on screen.

> Status: field notes measured on third-party mods, each named in its entry (LFHeli OH-1, the H2R motorbike import, SUB_BRZ). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. Tags such as SP-096 or LL-172 are the notes' own lesson numbers, and `CLAIM-...` tags are the notes' own claim register. Paths such as `<vehicle-import>\...`, `SUB_BRZ_dev\...`, `LFHeli_dev\...` or `AI/20_Knowledge/...` point into those mods' work folders and the author's notes, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number. Skills of other parts of this import are named without a path (dayz-model-pipeline, dayz-test-ingame, dayz-texture-pipeline, dayz-mcp-verify, enforce-script-reference).

## Vanilla anchors checked on `P:\`

- The contact-damage call quoted under SP-483, `ProcessDirectDamage`, is at `P:\scripts\4_world\entities\vehicles\motorbikescript.c:1350`, the same line number the note gives for 1.30.164014 Exp.
- LL-076: a vanilla car declares `GlobalHealth` inside its `DamageSystem`; for `CivilianSedan` that is `P:\DZ\vehicles\wheeled\config.cpp:5398`.

Nothing in this file is superseded: these are active lessons, ordered by topic instead of by date. Read it with `method-and-gate-calibration.md` (iteration budget, calibrating a gate against a working model) and `deploy-gates-and-crash-fingerprint.md`.

---

## An import gate rule is not deliverable without a negative fixture (SP-096, added 2026-07-27)

SP-091 established the method rule: calibrate every gate rule against a model that WORKS. That is
necessary and NOT sufficient. The LFHeli OH-1 gates were calibrated against a good reference and
still shipped a gate that passed the broken model, failed the good one, and accepted absurd input.
An adversarial review with in-memory mutation took them apart in one pass:

- 12 proxies displaced by 100/200/300 m -> **PASS**. The distance rule existed and fired, but it
  emitted INFO, and the verdict counted only FAIL.
- 30.419 faces repointed to a texture that does not exist -> **PASS**, with zero findings naming it.
  The rule walked the inventory looking for unreferenced files, never the reverse direction.
- The "corrected" reference fixture itself carried `dot(geometric, stored) = -1.0` on 24 of its 48
  proxy vertices - the exact defect SP-093 is about - and the suite asserted it must PASS.
- The suite advertised as "11 tests green" was 7 tests with 4 red, and could not even start from the
  official layout because it pointed at a directory that did not exist there.

RULES for any model-import gate:

1. **Every rule ships with TWO fixtures, both executed by the suite**: a positive (the good
   reference AND the current clean model both pass) and a **negative mutant** built in memory from a
   good model with the exact defect the rule claims to detect, which the rule MUST fail. A rule
   without a mutant that makes it fail is not deliverable - that is the hole every false PASS above
   came through.
2. **No INFO, no WARN inside the verdict.** If it should block, it is a FAIL; if it should not, it
   is a diagnostic print and stays out of the verdict and the exit code. A severity that cannot
   change the outcome is a rule that does not exist.
3. **Regenerate the reference fixture and verify it against the rules it is supposed to certify.**
   A fixture is an artifact like any other; it rots, and a corrupt one converts the whole suite into
   theatre.
4. **Prefer few solid rules to many plausible ones.** The rebuild kept three - proxy-normal
   coherence, referenced-texture existence, finite UVs - each with its mutant, and that suite is
   worth more than the twelve rules it replaced.
5. **A rule whose threshold is a bare literal is a smell.** Derive it from measurement on the good
   case and leave the number and its derivation in the code.
6. **When a gate change makes a previously green tree go red, fix the RULE or accept the finding -
   never re-baseline the expected value to make it pass.** Deciding between the two is the user's
   call, not implementation.

Origin: LFHeli OH-1 2026-07-27, R21 dual review (two independent agent reviewers). The rebuilt gate lives at
`LFHeli_dev\tools\import_gates_v2\`; the retired one at `tools\import_gates_RETIRED_20260726\` as a
negative reference.

## Rules promoted from lessons corpus (added 2026-07-27)

Promoted from `AI/20_Knowledge/lessons-learned.md` so that they arrive via trigger instead
of depending on someone remembering to look them up. Each rule cites its originating `LL-NNN`;
the full entry (symptom, origin, evidence) lives there. Do not remove the citation: the
`lessons-index.md` index detects promotion by searching for that reference inside skills.

- **LL-076** — Before deferring a feature, classify the severity of its absence and validate the minimums required by the engine. Every `CarScript` must include at least `DamageSystem.GlobalHealth`; its absence can kill the process even if damage is a later feature.
- **LL-172** — When facing black or see-through panels, first decode the deployed `_co` and measure dark pixels. If the texture is clean, treat the symptom as winding and require an in-game capture before flipping regions.

## Match transformed data by identity, never rounded position (SP-163, added 2026-08-31)

The same lesson from the import side is in `invariants-import-mesh-and-winding.md`, "Position is a candidate bucket, not identity".

A glTF/FBX seam can hold several source vertices at the same position with different
normal and UV values. Nearest/rounded-position matching can select the wrong twin
and report 180° normal drift or UV drift of 1.0 on an unchanged mesh. Carry the
source vertex/primitive identity through the operation. Before trusting the gate,
run source against itself through the same correspondence and require approximately
zero residual.

## Copy the whole lifecycle of a paired mechanism (SP-206, added 2026-08-31)

Before adopting a mechanism from a working reference, enumerate every call site.
Paired state (`SetDisabled`, active input excludes, focus, active flags) is usually
set on the happy path and cleared across normal exit, force-exit, watchdog, abort
and rejected entry. Half an adoption creates the same lock on the least-tested
path. Track ownership with a dedicated flag, make cleanup idempotent, and invoke it
from every transition out of the state.

## A control calibrated from the candidate is circular (SP-254, added 2026-08-31)

A known-good artifact is not an independent control if the axis map, orientation or
measurement chain used to read it was calibrated from the candidate. Derive the
instrument convention independently and require an asymmetric witness that changes
under the defect. Repeating the same circular chain across more controls does not
add evidence.

## Every executable gate has three outcomes (SP-294, added 2026-08-31)

Reserve exit `0` for `PASS`, `1` for a confirmed product/contract defect, and `2`
for `COULD_NOT_INSPECT`. Missing or wrong-format input, parser/import/tool failure,
an absent report, or a missing target row is state 2. A deliberate product mutant
must produce 1, and an unreadable-input fixture must produce 2. Never treat state 2
as PASS or as evidence that product geometry or configuration needs repair.

## A config gate is not a visual gate (SP-483, added 2026-10-24)

On the H2R import (2026-10) two feedback gates passed and the screen did not change. Gate 12 required a
duller silver rvmat (specular 0.4) on the far visual LODs, resolutions 3-6. Gate 13 required a crack rvmat
at 0.5 and 0.3 and `"hidden"` at 0.0 in `Front` and `Back`, the vanilla crack texture in that rvmat, and a
non-zero UV on the glass material; it never read `RefTexsMats[]`. The built config did list the glass
rvmat there, in its slot, but only a cross-family review noticed that the gate did not check it. In game
the windscreen still drew at level 4 (`vehicle-config-and-modelcfg.md`, end of §6b), and a white blob seen
from afar did not change between material variants: pixels of luminance 200 or more in an 80x60 window at
the centre were 60/68/39/23 at 40/60/85/240 m with the duller silver and 58/68/42/28 with a matte one
(specular 0, resolutions 2-6), and the blob looked the same with the original material on 2026-10-15
(claim: CLAIM-VEH-GATE-CONFIG-NOT-VISUAL-130).

1. **Name a PASS by what the gate reads.** A gate over config, stage files or ODOL proves wiring: report its
   PASS as "config", never as "works" (`method-and-gate-calibration.md`: iteration budget item 3, and SP-132 for calibrating the
   gate itself). A damage look or a far-LOD look is judged from in-game captures with a fixed camera, next
   to the logged state (damage level on server and client, camera distance).
2. **Take vehicle zones down the way the game does.** Use the call vanilla makes on contact,
   `ProcessDirectDamage(DamageType.CUSTOM, null, zoneName, "EnviroDmg", "0 0 0", dmg, pddfFlags);`
   (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:1350`, the same line in 1.30.164014 Exp; cars: invariant 35 in
   `invariants-engine-fluids-and-handling.md`).
   In one run it swapped the damage materials on the H2R and on a vanilla Motorbike_02 control, and
   `SetHealthMax` brought the healthy look back (DayZDiag 1.30.164014, 2026-10-15). Runs with `SetHealth01`
   logged levels 2 and 4 and showed no swap (2026-09-28, on the control too; 2026-10-07, control not
   recorded), with each level held 4 s as in that run. They also used other probe builds on other days,
   and `SetHealthMax` is itself a `SetHealth` call, so they do not show that `SetHealth01` cannot swap
   (LL-398 in the dayz-mcp-verify skill); on clothing the engine did apply `healthLevels[]` on scripted health
   steps (the dayz-texture-pipeline skill). Cross both with the same probe build and the same control before
   naming the method as a cause (LL-565, point 2; claim: CLAIM-VEH-CONTACT-DAMAGE-SWAP-130). On
   2026-10-24 (1.30.164200) the contact-damage call swapped the H2R's body panels in three of four
   textured runs; in the fourth, with the same kit as a later run that swapped, the client logged levels
   2 and 4 and no material changed, cause unknown. One run without a swap shows nothing either way: repeat
   it before blaming the kit or the method.
3. **Give a diagnostic marker a positive control.** When an unmistakable marker (a saturated emissive) in
   the rvmat that should come in never shows, that says nothing unless the same capture holds a part that
   carries that rvmat from the start: the pair rule of the dayz-texture-pipeline skill ("PASS ... is given by the pair")
   and SP-193's self-check (`visual-metrics-and-viewer.md`). The H2R's red marker had none.
4. **A control must be able to show the change** (SP-254 above). A vanilla Motorbike_02's nearly
   transparent glass looks the same hidden or not, so it cannot witness a glass swap.
5. **Know which LOD is drawn before tuning a far-LOD material.** The H2R never identified the LOD drawn at
   those distances, so its blob clears neither the material nor any LOD. Run the existing far-look checks
   first (the collapsed-UV census in `view-pilot-and-first-person.md`, and invariant 13 (b) and (d) in
   `invariants-lods-and-vertex-budget.md`); the H2R checked UVs, albedo and
   mipmaps and redid its far normals with no change, which settles little while the drawn LOD is unknown.
   Those ODOLs also carried every material entry empty (SP-155 rule 5 of the `/dayz-build-pbo` skill), so it is not
   shown that a face rvmat edited in the p3d reached the screen.
   [DESIGN] Give each visual LOD a colour mark visible away from the defect, and darken one material group
   in all its LODs per build, against a control.
6. **Point config gates at the delivered artifact.**
   (a) The far silver was on resolutions 3-6; in resolution 3 alone it sat on eight sections across
   `Back`, `Chassis`, `Front` and `FuelTank`, and it was in no `RefTexsMats[]`, so those faces would
   presumably keep the healthy look on a wreck. That was never tested in game, and the material was
   removed (claim: CLAIM-VEH-FAR-LOD-MAT-OUTSIDE-REFS-130).
   [DESIGN] For a zone that declares `RefTexsMats[]` (`vehicle-config-and-modelcfg.md` §6), check in every
   visual LOD that each rvmat meant to look damaged is in the list, above all a far-LOD stand-in for a
   listed rvmat. The gate names its deliberate exemptions (the H2R keeps 378 faces of its instrument
   cluster, with 41 materials, in `Front` out on purpose) and ships with its negative fixture (SP-096).
   (b) Read the packed PBO and its ODOLs: a gate over stage JSON or dumps can stay green on inputs other
   than the ones packed (the dayz-test-ingame skill: the verdict of a build is the PBO file table; the `/dayz-build-pbo` skill:
   rvmats referenced only from config.cpp stay out of the PBO).
   (c) Make the packer refuse diagnostic variants: the red-marker build was packable, and gate 13 could
   pass it.

Origin: the H2R import (2026-10): feedback gates 12 and 13, in-game runs from 2026-09-28 to 2026-10-24,
and a cross-family review of 2026-10-24 that found 6a-6c in the code.
