# Extraction ledger: state files, novelty, loop and final report

How a study of a packed mod (`study-a-packed-mod.md`) keeps its state: the four ledger files, how a finding is classified and where it goes, how to run the work one unit per turn, and what the closing report holds.

This is a working method, not a statement about vanilla data. A finding about a mod is a fact about that mod; compare it with vanilla before using it as a rule, for example the base class `CarScript` at `P:\scripts\4_world\entities\vehicles\carscript.c:94`.

All four files live in `output/<project>-extraction/_state/`.

## `queue.md`

An ordered list of work units. Each line is `- [ ] <unit-id>: <description>` or `- [x] <unit-id>: DONE <summary>`.

Unit types:

- `dim/<dimension>`: a pass 1 dimensional sweep
- `<entity>/<name>`: a pass 2 per-entity deep dive
- `APPLY skill_changes for <X>`: apply pending findings to a skill or pack
- `PASS_END_CHECK pass-<N>`: the convergence check

## `seen.json`

Machine-readable state per PBO and entity: extraction status, files read, dimensions extracted, the count of findings added per unit, and a SHA-1 cache so an unchanged file is skipped on a re-read. The `--json` output of `pbo_inventory.py` is a good first entry per PBO.

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
  "skill_target": "<existing skill or pack file>|notes:<file>",
  "action_pending": "append|note|skip|applied"
}
```

Use forward slashes in evidence paths (`TheirMod/Scripts/4_World/file.c`): a JSON parser rejects an unescaped backslash.

## `skill_changes.md`

One entry per edit applied to a skill or pack: the finding ids, the lines added and removed, and the target file.

## Novelty

| Novelty | When | Action |
|---|---|---|
| `new` | No skill or pack documents the pattern | Counts toward the convergence threshold |
| `variant` | The same pattern as documented, in a different context | Document it with a link to the original |
| `confirm` | The pattern matches existing content exactly | Do not add it; count it for the statistics |
| `dup` | Already in this run's `findings.jsonl` | Skip it |

Per pattern, search `skills/` (the skills and the packs under `skills/_shared/`): found and identical is `confirm`; found but the mod's version differs is `variant`; not found is `new`; already in this file is `dup`.

## Evidence

- Evidence is `<relative_path>:<line_range>`, or `<path>:<line>,<line>,<line>` for several lines.
- If unsure, read the file again at those lines.

A good finding names the lines and the mismatch:

```
"pattern": "OnDebugSpawn creates 4 wheels but attachments[] allows only 3 slots; the fourth ends up in the player's cargo."
"evidence": "TheirCar.c:79-86 vs TheirCar/config.cpp:134"
```

A bad one has no line: `"pattern": "spare wheel system", "evidence": "TheirCar.c"`.

## Where a finding goes

Findings land in the pack that owns the subject (the index is `skills/_shared/README.md`), never in a new skill: skills hold only things you run. For each cluster of findings with the same target:

- A pack covers the subject and the findings refine it: add them there, as facts about the named mod.
- The findings contradict the pack: add them as a variant with a note, and check vanilla on `P:\` to decide which is right.
- No pack covers the subject: write a note under `notes/` and tell the user which pack could hold it.

Every change edits versioned files, so it needs the user's request first. Mechanics:

1. Read the whole target file first; adding to a file that already has the section creates duplicates.
2. Add the findings to the section they belong to, grouped by topic.
3. Every fact names the mod it comes from, and a pack file keeps its vanilla citation (`skills/_shared/README.md`).
4. Read the file again after writing to check it reads as one piece.

## Notes for findings that fit no pack

```
output/<project>-extraction/notes/
├── <author>-style-fingerprints.md      # naming conventions, code style
├── <author>-quirks.md                  # anti-patterns, mistakes, oddities
├── <author>-3d-source-catalog.md       # inventory of the source asset PBOs
```

Link every note entry to its evidence path. About a fifth of the findings in a large study typically fit no pack but answer a later "what did this author do with X?".

## Loop mode for long studies

In Claude Code, `/loop` in dynamic mode runs one unit per turn:

```
/loop Process the next unit of the <project> extraction.
Queue: output/<project>-extraction/_state/queue.md
State dir: output/<project>-extraction/_state/

Each turn:
1. Read queue.md and take the FIRST line with [ ]
2. Run the unit (dimensional, per-entity, APPLY or PASS_END_CHECK)
3. Update the state and tick the line
4. Schedule the next wake-up in 240 s if units remain; schedule nothing when converged or a flag was raised

Rules:
- One unit per turn
- Search skills/ for novelty before each finding
- Evidence is mandatory, path:line
- More than 40 findings in one unit: raise a flag and stop
```

240 s between turns keeps the prompt cache warm (under its five-minute window).

## Final report

When converged: `_state/CONVERGED.md` with the metrics, and `output/<project>-extraction/<project>-final-report.md`:

```markdown
# <Project>: final report

## Summary (one page at most)
## Packs changed (per pack: lines added and removed, sections added)
## Notes (per note: purpose, findings)
## Cross-cutting patterns (seen in 7 or more of the N entities)
## Recommendations (for future mods in the same area)
## Metrics (passes, findings, files inspected)
## Open items
```
