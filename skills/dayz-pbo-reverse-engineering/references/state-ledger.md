# State ledger: state files, novelty rules, loop and final write-up

How a PBO extraction project keeps its state: the four ledger files, how a finding is classified and where it goes, how to run the work one unit per turn, and what the closing document holds.

Not yet checked on `P:\`: this is a working method, not a statement about vanilla data. Counts and examples come from the LM_Planes extraction project (Workshop item 3730564764) as the knowledge pack's author recorded them. A finding about a mod is a fact about that mod; compare it with vanilla before using it as a rule, for example the base class `CarScript` at `P:\scripts\4_world\entities\vehicles\carscript.c:94`.

All four files live in `output/<project>-extraction/_state/`.

## `queue.md`

An ordered list of work units. Each line is `- [ ] <unit-id> — <description>` or `- [x] <unit-id> — DONE: <summary>`.

Unit types:

- `dim/<dimension>`: a pass 1 dimensional sweep
- `<entity>/<name>`: a pass 2 per-entity deep dive
- `APPLY skill_changes for <X>`: apply pending findings to a skill or pack
- `PASS_END_CHECK pass-<N>`: the convergence check

## `seen.json`

Machine-readable state per PBO and entity: extraction status, files read, dimensions extracted, the count of findings added per unit, and a SHA-1 cache so an unchanged file is skipped on a re-read. The `--json` output of `inventory.py` is a good first entry per PBO.

## `findings.jsonl`

Append-only, one finding per line:

```json
{
  "ts": "ISO-8601",
  "id": "f_001",
  "pbo": "<name>",
  "pass": 1,
  "unit": "dim/config-root",
  "dimension": "config.cpp|model.cfg|script|layout|rvmat|sounds|particles|persistence|other",
  "pattern": "<concise description>",
  "evidence": "<path>/<file>:<line_range>",
  "novelty": "new|variant|confirm|dup",
  "skill_target": "<existing skill or pack file>|new:<slug>|notes:<file>|notes:style-fingerprints",
  "action_pending": "append|consider_new_skill|note|skip|applied"
}
```

Use forward slashes in evidence paths (`LM_Planes/Scripts/4_World/file.c`): a JSON parser rejects an unescaped backslash.

## `skill_changes.md`

A log of every addition or new file applied to a skill or pack: one entry per edit with the list of findings, the lines added and removed, and the marker written.

## Novelty classification

| Novelty | When | Action |
|---|---|---|
| `new` | No current skill or pack documents the pattern | Counts toward the convergence threshold |
| `variant` | The same pattern as documented, in a different application or context | Document it with a cross-reference to the original |
| `confirm` | The pattern matches existing content exactly | Do not add it; track it for the statistics |
| `dup` | Already in this run's `findings.jsonl` | Skip it |

Per pattern: search `skills/` (the skills and the packs under `skills/_shared/`). Found and identical is `confirm`; found but the mod's version differs is `variant`; not found is `new`; already in this file's findings is `dup`.

Honest verification rule: do not claim `new` without searching first, and do not claim `confirm` without checking that the existing file documents the exact pattern.

## Cite, then verify

- Evidence is mandatory, as `<relative_path>:<line_range>`, or `<path>:<line>,<line>,<line>` for several lines.
- Never write "function X does Y" without an evidence path.
- Never extrapolate behaviour; document only what is literally in the code.
- If unsure, read the file again at the specific lines.

Their code may use undocumented engine calls or non-obvious patterns, or have bugs. Do not assume a pattern is correct: document it, and note suspected problems separately.

A good finding:

```
"pattern": "DC_3 OnDebugSpawn creates 4 wheels but attachments[] allows only 3 slots. The fourth ends up in the player's cargo."
"evidence": "LM_DC_3.c:79-86 vs LM_DC_3/config.cpp:134"
```

A bad one (assumed, not cited):

```
"pattern": "DC_3 spare wheel system"
"evidence": "LM_DC_3.c"  // line missing
```

A well-extracted finding (LM_Planes `f_037`):

```json
{
  "pattern": "Real aerodynamics in Enforce Script: the lift coefficient is a cubic polynomial Cl=ClCoef3*aoaRad^3 + ClCoef2*aoaRad^2 + ClCoef1*aoaRad + ClCoef0 with stall transition smoothing. The drag coefficient is parabolic plus induced drag Cd_i = Cl^2/(pi*AR*Oswald). Dynamic pressure q = 0.5*density*v^2. Forces are applied through SafeApplyForce / SafeApplyTorque. The lift direction is computed as (velocityNorm * up) * velocityNorm (perpendicular to the velocity).",
  "evidence": "LM_Planes_extracted/LM_Planes/Scripts/4_World/entities/LlamaPlaneScript.c:906-940,1020-1100",
  "novelty": "new",
  "skill_target": "new:dayz-aviation"
}
```

A specific algorithm is cited, the line ranges are given, the novelty is justified and the destination is chosen.

## Add to an existing skill, or create one

For each cluster of findings with the same `skill_target`:

```
Is there a skill or pack whose scope covers this domain?
├─ Yes → Do the findings refine or extend what is there?
│        ├─ Yes → ADD to that skill or pack
│        └─ No (they contradict or replace it) → ADD with a VARIANT marker and a note
└─ No → Are there 7 or more new+variant findings in the same domain?
         ├─ Yes → CREATE a new skill
         └─ No (fewer than 7) → ADD to the closest skill, or write a note
```

Relaxing the threshold: for a domain that is truly orthogonal (no existing skill could plausibly hold the patterns), create the skill even with fewer than 7 findings. Domain coherence wins over the count for a unique format. The particles skill was created from only 6 findings, because the Enfusion `.ptc` format is orthogonal to everything else; the aviation skill is an example of one created through the full workflow.

In this repo both actions change versioned files, so they need the user's request first, and a new skill follows `docs/prompt-conventions.md`.

## Mechanics of adding to a skill or pack

1. Read the whole target file first; do not add blindly.
2. Find the section the findings belong to, or create `## <ModName> mod extraction patterns` at the end.
3. Group by topic when there are many findings (for example "CfgMods patterns", "Performance", "Vehicles").
4. End with a marker that lists the finding ids:
   ```
   <!-- <modname>-mod-extraction: findings f_001, f_002, ... | pbo: <name> | pass: N | date: YYYY-MM-DD -->
   ```
5. Read the file again after writing, to check the marker is there and the content is consistent. Adding to a file that already has the section creates duplicates.

Every fact added names the mod it comes from. A pack file under `skills/_shared/` also needs its vanilla citation or its "not yet checked on `P:\`" line (`skills/_shared/README.md`).

## Notes for findings that fit no skill

```
output/<project>-extraction/notes/
├── <author>-style-fingerprints.md      # naming conventions, code style, authorship identifiers
├── <author>-curiosities-and-quirks.md  # anti-patterns, jokes, easter eggs, mistakes
├── <author>-3d-source-catalog.md       # inventory of the source asset PBOs
```

Always link a finding to its evidence path. The notes are what answers a later "what did this author do with X?". In LM_Planes about 20% of the findings fitted no skill but were valuable reference (style fingerprints, anti-patterns, jokes, telling decisions). Do not lose them.

## Loop mode for multi-day work

In Claude Code, `/loop` in dynamic mode runs one unit per turn:

```
/loop Process the next unit of the <project> extraction.
Spec: <path>/<project>-design.md
Queue: output/<project>-extraction/_state/queue.md
State dir: output/<project>-extraction/_state/

Protocol each turn:
1. Read queue.md and take the FIRST line with [ ]
2. Run the unit (dimensional / per-entity / APPLY / PASS_END_CHECK)
3. Update the state and tick the line
4. Schedule the next wake-up in 240 s if units remain; schedule nothing when converged or a flag was raised

Rules:
- ONE unit per turn
- Before each finding: search skills/ for honest novelty
- Evidence is mandatory, path:line
- Anti-runaway: more than 40 findings in one unit → raise a flag and stop
```

Pacing: 240 s between turns keeps the prompt cache warm (under the five-minute window) for back-to-back turns.

## Convergence outputs

- `_state/CONVERGED.md` with the metrics
- `<project>-final-report.md` in `output/<project>-extraction/` (summary, skills changed, patterns, recommendations)
- an update of the category's consolidated report, if one exists

## Structure of the closing document

```markdown
---
type: <project>-final-report
date: YYYY-MM-DD
passes_executed: N
findings_total: <N>
skills_created: [...]
skills_enriched: [...]
notes: [...]
---

# <Project> — Final Report

## Summary (one page at most)
What was done, key discoveries, status.

## Skills created
Per skill: scope, sections, finding count.

## Skills enriched
Per skill: lines added and removed, sections added.

## Notes
Per note: purpose, findings.

## Cross-cutting patterns
Patterns that appear in 7 or more of the N entities.

## Decisions and recommendations
For future mods in the same domain.

## Final metrics
Turns, time, files inspected, knowledge added.

## Open items
If the user chooses to extend (pass 3, more skills, and so on).
```
