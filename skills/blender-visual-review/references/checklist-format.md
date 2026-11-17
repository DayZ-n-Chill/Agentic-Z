# Checklist format

The JSON format of a question checklist for `vr_score.py`, how `--view` routes each question to one image, what `vr_calibrate.py` relies on, and how the view of each question in `checks_hardsurface.json` was chosen. It describes this skill's own files and measured results; nothing is a statement about the game.

## An entry

An entry is `{"q": "<question>", "view": "<framing>"}` and may declare `"skip": "<reason>"`. The framing is the name of the image the question is evaluated against, not a hint inside a contact sheet. An entry with `skip` stays visible as data but is not sent to the model or scored.

```json
[
  {"q": "Are cylindrical parts smooth and round rather than visibly faceted polygons?", "view": "zoom_muzzle__front_iso", "skip": "Requires a deterministic facet report."},
  {"q": "Is the object sitting on the ground plane rather than floating above it or sunk into it?", "view": "assembled__profile_L"}
]
```

`q` is the text the model sees and what is written to `answers[].q` in the shadow log when the entry is active. `skip` is a non-empty reason and removes the entry from both consumers. It does not replace one question with another or delete it from the file.

## The view token

The `view` token is subject plus view (`assembled__iso`, `zoom_muzzle__front_iso`): the first two segments of the file name `<subject>__<view>__<subject>__<version>.png`. It is not the view alone (`iso`, `profile`). The reason: `profile` exists as a view of `zoom_mag` (`zoom_mag__profile__zoom_mag__v1.png`), and the side views of the assembly are `profile_L` and `profile_R`. A bare `profile` or `iso` token cannot tell `assembled__profile_L` from `zoom_mag__profile` (or `assembled__iso` from `body__iso` or `hg__iso`) and brings back the original bug: the question would be evaluated against the wrong framing.

The tokens in `checks_hardsurface.json` are all taken from a real render inventory, none invented. The table lists four; `assembled__profile_R`, used by a skipped entry, follows the same pattern:

| View | File |
|---|---|
| `assembled__iso` | `assembled__iso__assembled__v1.png` |
| `assembled__profile_L` | `assembled__profile_L__assembled__v1.png` |
| `zoom_receiver__right_iso` | `zoom_receiver__right_iso__zoom_receiver__v1.png` |
| `zoom_muzzle__front_iso` | `zoom_muzzle__front_iso__zoom_muzzle__v1.png` |

The file keeps 8 entries with their text intact: 3 declare `skip` and 5 stay active for sending and scoring. `assembled__iso` covers connections, gaps and "does it look like a finished object?"; `zoom_receiver__right_iso` covers bevels; `assembled__profile_L` covers ground contact. The excluded entries keep their views for the record: `assembled__profile_R` for inverted faces, `zoom_muzzle__front_iso` for cylinders and `assembled__profile_L` for proportions.

## Passing several views on the command line

`--view NAME PATH` can be repeated. `NAME` must match a question's `view`; `PATH` is the PNG of that framing. The positional `render` argument stops being required for `ask` when at least one `--view` is given.

```cmd
python "<skill-dir>\vr_score.py" ask --view assembled__iso assembled__iso__assembled__v1.png --view assembled__profile_L assembled__profile_L__assembled__v1.png --view zoom_receiver__right_iso zoom_receiver__right_iso__zoom_receiver__v1.png --view zoom_muzzle__front_iso zoom_muzzle__front_iso__zoom_muzzle__v1.png --checklist "<skill-dir>\checks_hardsurface.json"
```

How views resolve:

- **Without any `--view`** (the `vr_calibrate.py run` sweep works this way): all active questions go to the positional PNG in one call. The `view` field is recorded in the answer but does not route. So a checklist that has already been migrated does not break `ask foo.png` or multiply the calibrator's GPU cost.
- **With `--view`**: the name is required. A missing `zoom_muzzle__front_iso` is an error, not a silent fallback. The token `render` is an alias of the positional PNG, for mixed checklists.
- Each framing is one Ollama call with one image. The views are never sent together in the same message.

`--reference` is unchanged: it stays the comparison photo or render, and is not one more framing. Its guard did change: it no longer checks the model name but the pixel dimensions of both images. Two images of the same pixel size collapse into one on `qwen3.x`, and which one survives is unpredictable (it follows the prompt cache), so the call is refused; a difference of a single pixel is enough to avoid it. The old guard by model name blocked `qwen3.5`, which works when the sizes differ, and let `qwen3.8` through, which has the same collision.

## The simple alternatives that were rejected

The simplest option was not touching the command line: a single PNG (the usual three-panel sheet) with the framing written into the prompt ("answer looking at the foreground").

That does not cover the measured case. In the measured runs, questions 1 and 3 have different answers depending on the panel of the same sheet, and that is exactly where the three models disagree. The diagnosis is that the unit of work is (question, image), not (question, instruction about a region). A hint in the prompt still sends all three panels together.

The other simple option does change the unit of work: `ask img0.png img1.png img2.png` with `"view": 2`. It covers a three-file capture in a fixed order and breaks when a file is left out or reordered: index 2 stops being the muzzle zoom and the bevel question is evaluated against another view. It is the same failure (a question against the wrong framing), moved into the argument list. `--view zoom_muzzle__front_iso zoom_muzzle__front_iso__zoom_muzzle__v1.png` fails loudly if that PNG is missing.

## Backward compatibility and migration

The old format, a flat array of strings, still loads. Each string becomes `{q: that string, view: null}` and is scored against the positional PNG. There is no `skip` and no `version` field. An old checklist does not need migrating for `ask` and `vr_calibrate.py` to work. Reading uses `utf-8-sig`, which accepts both JSON without a BOM and the BOM that PowerShell 5.1 writes.

To migrate an old `.json`: each string `s` becomes `{"q": s, "view": "<token>"}`. Choose the framing against which the question has a single answer. Do not rewrite the text. `checks_hardsurface.json` is already migrated this way.

## Contract with `vr_calibrate.py`

The calibrator does not index by question text. It indexes by:

1. `Path(record["render"]).name`, to join with `verdicts.json`
2. the position within the active list: `verdicts[name]["answers"][i]` against `record["answers"][i]["answer"]`

`vr_score.py` respects that: `answers` stays an array in the order of the active checklist entries, and entries with `skip` take no position. Each element still has `q` (a string) and `answer`. `view` and `image` (the PNG actually sent) are added, and the calibrator ignores them. The record's `render` stays the positional argument when there is one, otherwise the first PNG given with `--view`.

`vr_calibrate.py report` used to slice `questions[qi][:60]`, assuming strings; with objects that raises. `checklist_labels` now reuses the same normalization and exclusion as `ask`, so its counters only hold the five active positions. `run` still launches `ask <a.png>` without `--view` (the legacy routing, one image). A sweep over several views would need another folder convention and is not part of this change.

`checklist_labels` hands the reading to `load_checklist`, which keeps `encoding="utf-8-sig"`: PowerShell 5.1 writes a BOM, and plain `utf-8` kills the report.

## Where each question's view comes from (calibrated 2026-08-16)

The `view` field is not an opinion. It was measured with a broken and a fixed render of the same object, which needs no gold answer. The same question is asked about both versions and two things are checked:

- **Accuracy** against the object's gold answer, across both states.
- **Separation.** Does the answer change between broken and fixed, on the questions whose answer must change? A framing can score well by always answering the same.

Measured on one rifle model (8 framings, 3 models), with the real grouping `vr_score.py` builds: the checklist reaches 77.8% against a floor of 58.3% for a constant answer, and the connectivity question scores 12/12.

Three traps cost a whole run and must be avoided when calibrating again:

1. **Which questions travel in the call changes the answer.** The same shading question, image and model scored 18/18 in a call with four other shading questions and 9/12 in the call with all eight of the checklist. Comparing two framings is only valid if the batch is identical between them. And it is not the batch size: removing Q5 from `assembled__iso` lowered Q4 and Q6 by two points each, with a smaller batch.
2. **A framing without a fixed render cannot be compared.** `zoom_muzzle__front_iso` scores over 6 cells of the broken state instead of 12, and there a constant answer gets 6/6. Sorting by percentage crowns it with half the evidence and zero separation.
3. **What wins under uniform conditions can lose under real ones.** Moving Q1, Q4 and Q5 together to `assembled__profile_R` won in the audit and got worse under the real grouping: Q1 dropped from 12/12 to 8/12. Only Q5 was moved, the one that held up in validation.

## The faceting question (Q3) is broken, not misrouted

"Are cylinders smooth and round?" is at chance across the eight framings (50% at most), because its phrasing allows the polygonal handguard, which is flat by design, to be read as a faceted cylinder.

This section once closed with "it is fixed by rewriting it, not by moving it". That was retracted on 2026-08-22, after it was tested and came out the opposite (192 cells on the same rifle model plus a synthetic probe whose truth is set by construction, 2026-08-17):

- **Four phrasings were measured and the existing one wins** (6/6 and 6/6 in framings where the round piece fills the frame). A numeric threshold got 5/6, an exclusion clause 5/6, an angular silhouette 2/6. On a framing of the whole object all four drop to 1 or 2 of 3: framing outweighs phrasing.
- **A threshold inside the question is not applied as a count.** Asked about "roughly six or fewer sides", all three models said "yes" to the 12-sided variant.
- **Grouping halves the sensitivity.** 6/6 asked alone, 3/6 inside the batch of eight that `vr_score.py` builds. This is the third confirmation of the batch effect in this skill.
- **The object cannot answer it.** `hg_tube` is a regular octagon and is correct: the reference photo in that model's dossier dictates an octagonal section. The real cylinders (`body_brake` with 18 to 22 sides, `body_barrel` with 14, `endplate` with 24) have a sagitta `r*(1-cos(pi/N))` of 0.167 to 0.213 mm, under 1 px in any of the eight framings, against 1.91 mm and about 6.9 px for the octagon. The only visibly faceted piece of this weapon is the piece that should be.
- **8 of 12 cells are false alarms** under the real grouping, against a gold answer derived from the geometry. A question that flags correct geometry two thirds of the time cannot go into an automatic gate, and still less into a pre-filter that rejects: there a false alarm throws out good work. It is the failure of the winding gate, which was red on 73% of what was published.

**What to do instead.** Remove it from the vision-model checklist and from any pre-filter, and replace it with a deterministic report per part (sides, radius, deviation, sagitta) that reports and does not judge. The problem with Q3 was that it needed to guess the modeler's intent, and a row such as "`hg_tube`, 8 sides, r = 25.2 mm" hands that decision back to the person who can make it. The prototype, `facet_report.py`, is not in this skill; its contract is in `local-vlm-judge.md`.
