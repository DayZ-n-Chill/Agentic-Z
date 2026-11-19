# Local vision model as a pre-filter

How to use a free local vision model, served by Ollama, on renders with `vr_score.py` and `vr_calibrate.py`: the shadow mode rule, which checklist questions it may answer and which it may not, how each was calibrated, and the contract for the faceting report that replaces one question. The checklist JSON and `--view` routing are in `tools-vlm-checklist-format.md`. This is tool behaviour and measured results; nothing here is a game fact.

## Shadow mode

```cmd
python skills\dayz-model-tools\scripts\vr_score.py ask _review\model__iso__iter3.png --checklist skills\dayz-model-tools\scripts\checks_hardsurface.json --model <model> --json
python skills\dayz-model-tools\scripts\vr_score.py score _review\model__iso__iter3.png --reference ref.jpg --model <model> --json
```

Prefer `ask` over `score`: concrete yes or no questions are measurably easier for a small vision model than open judgment, and each "no" points at something specific instead of an opaque number. Derive the questions from the model's own detail list (`blender-assembly.md`); `checks_hardsurface.json` is the generic starter set.

The local model's answers are evidence logged beside your own. They are never a gate and never a substitute for looking. Every call appends to a JSONL shadow log (`vr_shadow.jsonl` next to the render unless `--shadow` names another file; `--no-shadow` skips it), and that log is the calibration data, collected for free during real work. A question can move from shadow to pre-filter (it throws out the obviously broken and you judge the rest), never to final judge.

Options of `vr_score.py`: `--model` (a local vision model), `--host` (the local Ollama server), `--ctx` (default 8192), `--reference`, `--shadow`, `--no-shadow`, `--json`; `ask` adds `--checklist` and the repeatable `--view NAME PATH`. Exit code 0 on an answer, 2 on bad arguments, an unreachable Ollama, or a reference with the same pixel size as the render (`tools-vlm-checklist-format.md`).

### Speed

On two renders and the 8 question checklist, `gemma4:26b` took about 15 s warm and `qwen3.5:27b` about 132 s at similar quality. The gap came from the factory `num_ctx`, which pushed 37 % of qwen onto the CPU. With `think:false` and `num_ctx=8192`, which `vr_score.py` sends, the times are 8.3 s and 17.2 s, so qwen works as a second opinion from another model family.

Both models flagged a faceted circle, and both answered "unsure" instead of guessing when the view could not decide. They gave opposite bevel verdicts on the same renders, so bevel and chamfer questions stay with the agent. Judge fine surface questions on a crop at native resolution, never on a full frame render.

### Setup notes

- Models live wherever `OLLAMA_MODELS` points. A 17 GB model takes most of a typical GPU's memory, so models load one at a time and compete with Blender for video memory. Unload before a heavy render.
- Address the server as `127.0.0.1`, never `localhost`: on Windows that resolves to IPv6 first, and a stray `ollama serve` bound to IPv6 answers from a different model library.
- With thinking on, current models put the whole reply in `message.thinking` and return an empty `message.content`, so every call ends in a JSON parse error. `vr_score.py` sends `think: false` for that reason.
- A checklist saved by PowerShell 5.1 carries a BOM; `vr_score.py` reads it with `utf-8-sig`.

## The checklist: five active questions, three excluded

The shadow rule governs any question not in this section. The JSON keeps eight entries: five reach the model and three carry `skip`. Only the pre-filter rows change the review loop.

The filter rejects; it never approves. A "no" triggers a fix before anything is shown. A clean pass does not mean "it is fine", only "it now deserves your eyes".

Measured on one rifle model with a broken and a fixed render of the same object, three models, and the grouping `vr_score.py` really builds. The whole checklist reaches 77.8 %, against 58.3 % for a constant answer.

| Question | Accuracy | In the loop |
|---|---|---|
| Connectivity, floating parts | 12/12 | Pre-filter; by far the strongest |
| Gaps or holes in the surface | 10/12 | Pre-filter |
| Black, flipped or wrongly shaded faces | 10/12, withdrawn | Not delegated; `skip`. The defect is not in the capture; use the back face culling comparison in `blender-winding-flips.md` |
| Finished object against bare boxes | 10/12 | Pre-filter |
| Consistent proportions | 10 to 12/12, withdrawn | Not delegated; `skip`. The broken and fixed pair it was measured on held no proportion defect, so always answering "yes" scored perfectly (next section) |
| Bevels, chamfered edges | 6/12 | Not delegated. It sits at the constant answer floor, as the opposite bevel verdicts of the two models already suggested |
| Faceted cylinders | Depends on framing and grouping, not on wording | Not delegated and not reworded; `skip`. See "Faceting question: closed" |

Two notes on the shipped JSON. The bevel question has no `skip`, so it is still sent, but its answer is not acted on. The eighth entry, ground contact, is active and has no row because it was never calibrated.

### Before believing a high score from this table

A yes or no question has two failure modes its own score hides, and the proportions row fell into both:

1. The constant. If the known answer never changes across the test set, a constant answer scores perfectly and nothing was measured. Check in one line: does the known answer change value in the set?
2. Confabulation. Asked for a reason, the model invents one. Shown a flange 37 % wider than expected, one model called it consistent with "standard fastener geometry" and another "appropriately scaled". A confident false note is worse than "unsure".

With two built in defects, `gemma4:26b`, `qwen3.8:27b` and `qwen3.5:27b` answered "yes" to the proportions question in all 9 cells (3 models by 3 variants). Asking instead for the measurement, the size and position of each piece as a fraction of the frame scored by the direction of change, got 6/6 on the same renders.

That measurement is not implemented: no `probe_truth.py` is shipped, and the question stays in `checks_hardsurface.json` with `skip`. Until it exists, check proportions by eye. One trap is already known: declaring a coordinate convention does not beat the model's own sense of up and down. Asking for y = 0 at the bottom and mirroring its answers cut the vertical error from 0.107 to 0.017 of the frame. Use the image convention, or detect the mirror before scoring.

### Where it enters the loop

Between capturing the angles and looking at them, in the loop of `blender-visual-review.md`. The four renders of `vr_capture` (front, right, top, iso) do not cover the three framings the five active questions use (`assembled__iso`, `assembled__profile_L` and the receiver close up `zoom_receiver__right_iso`), so render those yourself first (`tools-vlm-checklist-format.md`, section "The view token"). With only the `vr_capture` renders, pass one PNG positionally without `--view` and every active question goes to that image.

```cmd
python skills\dayz-model-tools\scripts\vr_score.py ask --checklist skills\dayz-model-tools\scripts\checks_hardsurface.json --model <model> --json --view assembled__iso _review\m__iso__iter3.png --view assembled__profile_L _review\m__profile_L__iter3.png --view zoom_receiver__right_iso _review\m__receiver__iter3.png
```

If any of the three pre-filter questions (connectivity, gaps, finished object) says no, fix and render again before asking for the user's eyes. The bevel and ground contact answers are logged only: bevel sits at the constant answer floor and ground contact was never calibrated. If no pre-filter question says no, look anyway; the filter approved nothing. The three excluded questions do not appear in the answers: inverted faces go to the culling comparison, and proportions and cylinders stay unchecked by the model until `probe_truth.py` and `facet_report.py` exist.

### Calibrating a question: a broken and a fixed render

`vr_calibrate.py report` warns below 15 renders you have already judged. Collecting judged renders would have found none of the faults above: the same question goes from 7/12 to 11/12 just by changing the framing, and from 9/12 to 18/18 just by changing which other questions travel in the same call. A cheaper test replaces it and also shows the cause.

Take two renders of the same object, one with the defect and one with it fixed, and ask the same question of both. It needs no known answer, and it measures two things:

- Sensitivity: does the answer change where it should?
- Specificity: does it stay still where it should not change?

A judge that answers the same for both versions is not reading the model, whatever its score. Any mod with a before and an after serves as the test bench.

The accumulation runner still ships, for the agreement report per question:

```cmd
python skills\dayz-model-tools\scripts\vr_calibrate.py run --renders <folder> --checklist skills\dayz-model-tools\scripts\checks_hardsurface.json --models <model> <model> --shadow cal.jsonl
python skills\dayz-model-tools\scripts\vr_calibrate.py report --shadow cal.jsonl --verdicts verdicts.json --checklist skills\dayz-model-tools\scripts\checks_hardsurface.json
```

`verdicts.json` is written by the agent after looking at the same renders: `{"<render file name>": {"answers": ["yes", "no", "unsure"], "note": "optional"}}`, with the answers in the order of the active questions. The report prints agreement per question, which is what gets delegated, not the model as a whole. It marks a question DELEGABLE at 0.85 or more, agent side under 0.7 and borderline in between. A verdicts file whose answer count does not match the active questions is skipped with a warning. Agreement is not accuracy: a model that shares the agent's blind spots scores well, which is acceptable for a pre-filter and not for a gate.

Three things spoil a comparison of framings:

1. The other questions in the call change the answer. The same question, image and model scored 18/18 in a call with four other shading questions and 9/12 in the call with all eight. Keep the batch fixed. Size is not the cause: removing one question made the two that stayed worse.
2. A framing without a fixed render cannot be compared with one that has it: it scores over half the cells, and there a constant answer gets 6/6.
3. The request temperature is 0.1, so two samples of the same cell come out almost identical. The real sample count is the number of cells, not the number of repeats.

All of this comes from a single object. Before writing that a model cannot do something, vary the wording, the framing and the batch, and say which of the three was varied; a test setup fault once passed for "these models do not detect geometric defects".

## Which local models hold up

The whole shipped checklist, over a pair of renders that differ only in facet count (48 against 6 sides), 3 seeds. Only the faceting question should move.

| Model | Correct | The miss |
|---|---|---|
| `qwen3-vl:30b` | 8/8 | None |
| `ornith-1.5:9b` | 7/8 | Calls the smooth variant holed, 2 of 3 seeds |
| `muse-glimmer:30b` | 7/8 | Reads the faceted variant as bevelled, 3 of 3 seeds |

`qwen3-vl:30b` is the cleanest of the three; a bigger or newer model did not beat it. `qwen3.5:27b` and `gemma4:26b` were not part of this screen. Scope: one object, one pair, one framing where the round part fills the frame, the one condition where the faceting question already works. It screens models; it does not rank them.

## Faceting question: closed

Do not reword the faceting question and do not delegate it. The current wording is the best of four measured, but that does not make it a gate. Asked alone it got 6/6; inside the batch of eight that `vr_score.py` builds it fell to 3/6. On the real object it gave 8 false alarms out of 12: the visible octagonal piece is intentional, and the real smoothed cylinders have a sagitta under one pixel in those framings. So:

- Keep the question unchanged, with `skip`. It stays out of the active checklist and the pre-filter.
- Do not call the result chance: the failure follows the framing and the grouping.
- To have a profile counted, frame the cross section until it fills the frame. The generic distance `max_dim * 2.2` leaves the end view of a long object with no information.
- The right replacement is deterministic and reports instead of judging: part, sides, radius, relative deviation and sagitta, with an allowlist for intentional prisms. Intent stays the modeler's decision.

`facet_report.py` is not shipped. This section sets its contract and limits; it does not claim the program exists.

## Contract for the faceting report

If `facet_report.py` is added, flag a part when `sides < 12` and `radius >= 6 mm`, not at a 4 mm radius. It also requires a nearly square cross section: a ratio of at most 1.30 between the sides of the transverse bounding box. That admits pentagons and hexagons and rejects the flat shapes that a 20 % outer filter mistakes for a cylinder. An allowlist silences deliberate prism profiles.

The coverage report matters as much as the flags. It must state:

- the meshes visible in the render and the parts with a circular profile
- the polygons examined, and their share of the visible ones
- the largest mesh not examined, and its share

`0 marked` is INCONCLUSIVE when no mesh is visible, or when a single unexamined mesh holds 30 % or more of the polygons. The overall share covered does not decide the verdict: an asset made mostly of boxes and rails can have low coverage and still be valid for the parts examined.

Its calibration: 0 false alarms across 41 circular parts from three real assets, all three parts of the synthetic defect flagged, and the 12 sided and 48 sided probes clean. Limits: it works per object, does not see tubes inside a merged mesh, can miss thin or heavily slotted profiles, and does not certify that geometry it did not flag is round. The test set includes no published mod checked in game, so never raise this report to a final gate.
