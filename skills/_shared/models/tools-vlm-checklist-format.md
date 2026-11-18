# Render checklist format

What a question checklist for `vr_score.py` looks like, how `--view` sends each question to one image, what `vr_calibrate.py` relies on, and how the view of each question in `checks_hardsurface.json` was chosen. It describes the visual review scripts of `/dayz-model-tools` and measured results; nothing here is a game fact. How the local model is used is in `tools-vlm-judge.md`.

## An entry

An entry is `{"q": "<question>", "view": "<framing>"}` and may add `"skip": "<reason>"`. The framing is the name of the image the question is asked against, not a hint inside a contact sheet.

```json
[
  {"q": "Are cylindrical parts smooth and round rather than visibly faceted polygons?", "view": "zoom_muzzle__front_iso", "skip": "Requires a deterministic facet report."},
  {"q": "Is the object sitting on the ground plane rather than floating above it or sunk into it?", "view": "assembled__profile_L"}
]
```

`q` is the text the model sees, and what goes into `answers[].q` in the shadow log when the entry is active. `skip` is a non empty reason; the entry stays in the file as data but is neither sent to the model nor scored. It does not replace or delete the question.

## The view token

The `view` token is subject plus view (`assembled__iso`, `zoom_muzzle__front_iso`): the first two parts of the file name `<subject>__<view>__<subject>__<version>.png`. These framings come from a capture set of their own, not from the `vr_capture` helper of `blender-visual-review.md`, which writes `<object>__<angle>__<tag>.png` for front, right, top and iso only. To run a checklist with `--view`, render the framings it names (an assembly view, side profiles, close ups of a part) yourself and pass each under its token.

The view alone (`iso`, `profile`) is not enough. `profile` exists as a view of `zoom_mag` (`zoom_mag__profile__zoom_mag__v1.png`), while the side views of the assembly are `profile_L` and `profile_R`. A bare `profile` or `iso` cannot tell `assembled__profile_L` from `zoom_mag__profile`, or `assembled__iso` from `body__iso` or `hg__iso`, and the question would be asked against the wrong framing.

Every token in `checks_hardsurface.json` comes from a real render set. The four in use, plus `assembled__profile_R` for a skipped entry, follow the same pattern:

| View | File |
|---|---|
| `assembled__iso` | `assembled__iso__assembled__v1.png` |
| `assembled__profile_L` | `assembled__profile_L__assembled__v1.png` |
| `zoom_receiver__right_iso` | `zoom_receiver__right_iso__zoom_receiver__v1.png` |
| `zoom_muzzle__front_iso` | `zoom_muzzle__front_iso__zoom_muzzle__v1.png` |

The file holds 8 entries with their text intact: 3 carry `skip` and 5 are active. `assembled__iso` covers connections, gaps and "does it look like a finished object?"; `zoom_receiver__right_iso` covers bevels; `assembled__profile_L` covers ground contact. The skipped entries keep their views for the record: `assembled__profile_R` for inverted faces, `zoom_muzzle__front_iso` for cylinders and `assembled__profile_L` for proportions.

## Passing several views

`--view NAME PATH` can be repeated. `NAME` must match a question's `view`; `PATH` is the PNG of that framing. The positional `render` argument is not required for `ask` once at least one `--view` is given.

```cmd
python skills\dayz-model-tools\scripts\vr_score.py ask --view assembled__iso assembled__iso__assembled__v1.png --view assembled__profile_L assembled__profile_L__assembled__v1.png --view zoom_receiver__right_iso zoom_receiver__right_iso__zoom_receiver__v1.png --view zoom_muzzle__front_iso zoom_muzzle__front_iso__zoom_muzzle__v1.png --checklist skills\dayz-model-tools\scripts\checks_hardsurface.json
```

How views resolve:

- Without any `--view` (the `vr_calibrate.py run` sweep works this way), all active questions go to the positional PNG in one call. The `view` field is recorded in the answer but does not route, so `ask foo.png` still works on a checklist with views and the calibrator's GPU cost does not grow.
- With `--view`, every view an active question routes to must be passed. A missing `assembled__profile_L` or `zoom_receiver__right_iso` is an error, not a silent fallback. Views named only by skipped entries (`assembled__profile_R`, `zoom_muzzle__front_iso`) are not needed, because skipped entries are removed before routing. The token `render` stands for the positional PNG, for mixed checklists.
- Each framing is one Ollama call with one image. Views are never sent together in one message.

`--reference` is the comparison photo or render, not another framing. The script refuses a reference with the same pixel size as the render: two images of the same size collapse into one on `qwen3.x`, and which one survives follows the prompt cache. A difference of a single pixel avoids it. The check is on pixel size, not on the model name, because `qwen3.5` works when the sizes differ and `qwen3.8` has the same collision.

## Why one image per question

Writing the framing into the prompt of a single three panel sheet ("answer looking at the foreground") does not work. Two questions have different answers depending on the panel of the same sheet, and that is exactly where the three models disagree. The unit of work is the pair (question, image), not a question with a note about a region.

Passing images by position (`ask img0.png img1.png img2.png` with `"view": 2`) breaks when a file is left out or reordered: index 2 stops being the receiver close up and the bevel question is asked against another view. With `--view zoom_receiver__right_iso <file>` the framing is named, and leaving it out fails loudly because the active bevel question routes to it.

## Older checklists

A flat array of strings still loads. Each string becomes `{q: that string, view: null}` and is scored against the positional PNG; there is no `skip` and no `version` field. An old checklist needs no change for `ask` and `vr_calibrate.py` to work. Reading uses `utf-8-sig`, which accepts JSON with or without the BOM that PowerShell 5.1 writes.

To convert an old file, turn each string `s` into `{"q": s, "view": "<token>"}`, choosing the framing in which the question has a single answer. Never rewrite the text. `checks_hardsurface.json` is already in the new form.

## What vr_calibrate.py relies on

The calibrator does not index by question text. It indexes by:

1. `Path(record["render"]).name`, to join with `verdicts.json`
2. the position in the active list: `verdicts[name]["answers"][i]` against `record["answers"][i]["answer"]`

`vr_score.py` keeps that: `answers` is an array in the order of the active entries, and skipped entries take no position. Each element has `q` (a string) and `answer`, plus `view` and `image` (the PNG actually sent), which the calibrator ignores. The record's `render` is the positional argument when there is one, otherwise the image of the first active question, whatever the order of the `--view` arguments. Without `--shadow` and without a positional PNG, the shadow log goes next to the first PNG given with `--view`.

`vr_calibrate.py report` builds its labels with `checklist_labels`, which uses the same normalization and exclusion as `ask`, so its counters hold only the five active positions. `checklist_labels` reads through `load_checklist` with `encoding="utf-8-sig"`, because plain `utf-8` fails on the BOM PowerShell 5.1 writes. `run` still calls `ask <a.png>` without `--view`, one image per call; a sweep over several views would need another folder layout.

## How each question's view was chosen

Each `view` was measured with a broken and a fixed render of the same object, which needs no reference answer. The same question is asked of both versions, and two things are checked:

- Accuracy against the object's known answer, across both states.
- Separation: does the answer change between broken and fixed where it must? A framing can score well by always giving the same answer.

On one rifle model (8 framings, 3 models), with the grouping `vr_score.py` really builds, the checklist reaches 77.8 % against 58.3 % for a constant answer, and the connectivity question scores 12/12.

Three things spoil a comparison of framings:

1. The other questions in the call change the answer. The same shading question, image and model scored 18/18 in a call with four other shading questions and 9/12 in the call with all eight. Compare two framings only with an identical batch. Size is not the cause: removing the shading question from the `assembled__iso` call lowered the gaps and finished object questions by two points each, with a smaller batch.
2. A framing without a fixed render cannot be compared. `zoom_muzzle__front_iso` scores over 6 cells of the broken state instead of 12, and there a constant answer gets 6/6. Sorting by percentage crowns it on half the evidence and no separation.
3. What wins under uniform conditions can lose under real ones. Moving the connectivity, gaps and shading questions together to `assembled__profile_R` won in isolation and got worse under the real grouping, the connectivity question dropping from 12/12 to 8/12. Only the shading question was moved, the one that held up when checked again.

## The faceting question cannot be fixed by wording

"Are cylinders smooth and round?" fails across the eight framings, and its result depends on the framing and the grouping, not on the wording. Its wording lets the polygonal handguard, flat by design, be read as a faceted cylinder. Measured over 192 cells on the same rifle model, plus a synthetic probe whose answer is set by construction:

- Of four wordings, the existing one is best: 6/6 and 6/6 in framings where the round piece fills the frame. A numeric threshold got 5/6, an exclusion clause 5/6, an angular silhouette 2/6. In a framing of the whole object all four drop to 1 or 2 of 3: framing outweighs wording.
- A threshold inside the question is not applied as a count. Asked about "roughly six or fewer sides", all three models said "yes" to the 12 sided variant.
- Grouping halves the sensitivity: 6/6 asked alone, 3/6 inside the batch of eight that `vr_score.py` builds.
- The object cannot answer it. `hg_tube` is a regular octagon and is correct: the reference photo for that model shows an octagonal section. The real cylinders (`body_brake` with 18 to 22 sides, `body_barrel` with 14, `endplate` with 24) have a sagitta `r*(1-cos(pi/N))` of 0.167 to 0.213 mm, under 1 px in any of the eight framings, against 1.91 mm and about 6.9 px for the octagon. The only visibly faceted piece is the one that should be.
- Under the real grouping, 8 of 12 cells are false alarms against an answer derived from the geometry. A question that flags correct geometry two thirds of the time cannot go into an automatic check, and least of all into a pre-filter that rejects work.

Remove it from the vision model checklist and from any pre-filter, and replace it with a deterministic report per part (sides, radius, deviation, sagitta) that reports and does not judge. A row such as "`hg_tube`, 8 sides, r = 25.2 mm" hands the decision about intent back to the modeler. That `facet_report.py` is not shipped; its contract is in `tools-vlm-judge.md`.
