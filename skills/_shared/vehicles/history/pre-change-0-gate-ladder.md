# Imported-model gate ladder before change 0 (archived snapshot)

History only: the rule that set the order of the old ladder of visual gates for an imported car, kept for manual diagnosis and for vehicles already built against it.

Change 0 is the family B cutover of 2026-08-05: from then on a new ripped car runs only the offline check allowlist of `skills/rip-vehicle-import/SKILL.md` (B1 to B6, with B7 added on 2026-08-16), and every other gate, this ladder included, is run by hand only.

> Status: the measurement below was taken on a third-party vehicle mod (TestCoupe); it is third-party mod behaviour, not vanilla, and was not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. `gate_car` is a script of that mod's work folder, which is not part of this repo.

> Snapshot of 2026-08-05. Nothing here is current doctrine; the current rules are in `method-and-gate-calibration.md` and the invariant files.

Related file in this folder: `legacy-gate-ladder.md` (the rungs themselves, 0 to 6, including the LOD frame parity rung).

## Vanilla anchors checked on `P:\`

- The ladder's rung 0 diffs the model against a vanilla car; the control used throughout is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` (binarized, not read here).

## Gate ladder: imported-model visual correctness (run in order, cheap to expensive)

Every imported car (rip to DayZ) passed the gates in the order written in `legacy-gate-ladder.md`. Skipping a rung means re-work later: `gate_car` was built at rung 4 (see-through) while rung 2 (the most basic winding check) was missing, and the defect was caught in game (BRZ backlight mixed-winding, 2026-07-01). Rule: before building a "done" validator, enumerate the failure modes and name which rung covers each. If you cannot, do not code yet. Run cheap topological gates before expensive raycast and in-game ones.

## Calibration and scope

The three calibration rules that closed this snapshot (every rung must catch at least one known in-game bug, a pass states its scope, and the analysis stamps the model's freshness) are current and are written once, in `method-and-gate-calibration.md`, section "Calibration and scope, so a gate is trustworthy and not a false green".
