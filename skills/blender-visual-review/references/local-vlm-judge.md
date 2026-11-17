# Local vision model as a pre-filter

How to use a free local vision model (served by Ollama) on renders with `vr_score.py` and `vr_calibrate.py`: the shadow-mode rule, which checklist questions may be delegated and which may not, how each was calibrated, and the contract for the faceting report that replaces one question. Everything here is tool behaviour and results measured by the source author on the dates given; nothing is a statement about the game.

The labels `SP-NNN` and `LL-NNN` are the author's own ticket and lesson numbers; the files they point to are not in this repo.

## Shadow mode (added 2026-07-30)

```cmd
python "<skill-dir>\vr_score.py" ask _review\model__iso__iter3.png --checklist "<skill-dir>\checks_hardsurface.json" --model gemma4:26b --json
python "<skill-dir>\vr_score.py" score _review\model__iso__iter3.png --reference ref.jpg --model gemma4:26b --json
```

Prefer `ask` over `score`: concrete yes or no questions are measurably easier for a small vision model than open judgment, and each "no" is a specific pointer instead of an opaque number. Derive the questions from the model's own detail list (`blender-assembly` Phase 1.5); `checks_hardsurface.json` is the generic starter set.

This is shadow mode, and that is not negotiable: the local model's answers are evidence logged beside your own, NEVER a gate and never a substitute for looking. Every call appends to a JSONL shadow log (`vr_shadow.jsonl` next to the render unless `--shadow` names another file; `--no-shadow` skips it). That log is the calibration dataset, built for free during real work. The promotion path is shadow, then pre-filter (it discards the obviously broken and you judge the survivors), and never final judge.

Options of `vr_score.py`: `--model` (default `qwen3.5:27b`), `--host` (default `http://127.0.0.1:11434`), `--ctx` (default 8192), `--reference`, `--shadow`, `--no-shadow`, `--json`; `ask` adds `--checklist` and the repeatable `--view NAME PATH`. Exit code 0 on an answer, 2 on bad arguments, an unreachable Ollama, or a reference with the same pixel size as the render (see `checklist-format.md`).

### Measured speed (2026-07-30, RTX 3090, 2 renders, provisional)

`gemma4:26b` took about 15 s warm for the 8-question checklist and `qwen3.5:27b` about 132 s for comparable quality, so gemma is the default in the commands above.

The cause of that 9x gap was refuted on 2026-08-16: it was not the model, it was the factory `num_ctx`, which pushed 37% of qwen onto the CPU. With `think:false` and `num_ctx=8192` the times are 8.3 s and 17.2 s, a 2x gap, and qwen becomes usable again as a second opinion from another model family. `vr_score.py` sends both settings.

Both models correctly flagged a faceted circle, and both answered "unsure" instead of guessing when the view could not decide. They gave opposite bevel verdicts on the same renders, so bevel and chamfer questions stay with the agent. Judge fine surface questions on a crop at native resolution, never on a full-frame render (LL-153).

### Setup notes

- Models live wherever `OLLAMA_MODELS` points. A 17 GB model fills a 24 GB card, so models load one at a time and compete with Blender for VRAM. Unload before a heavy render.
- Always address the server as `127.0.0.1`, never `localhost`: on Windows that resolves to IPv6 first, and a stray `ollama serve` bound to IPv6 will answer from a different model library.
- With thinking on, current models put the whole reply in `message.thinking` and return an empty `message.content`, so every call ends in a JSON parse error; `vr_score.py` sends `think: false` for that reason (measured 2026-08-16, SP-260).
- A checklist saved by PowerShell 5.1 carries a BOM; `vr_score.py` reads it with `utf-8-sig`.

## The checklist: five active questions, three excluded (added 2026-08-16, SP-277; calibration data in SP-270)

The shadow rule above governs any question not in this table. The JSON keeps eight entries: five reach the model and three carry `skip`. Only the pre-filter rows change the loop.

**The filter rejects, it never approves.** A "no" triggers a fix before anything is shown. A clean pass does not mean "it is fine"; it means "it now deserves your eyes". The rule that the local model is never the final judge stands: it has been given the power to stop, not to approve.

### What is calibrated and what is not

Measured on the `mk47_mutant` model with a broken and a fixed render of the same object, three models, and the real grouping `vr_score.py` builds. The whole checklist reaches 77.8%, against a floor of 58.3% for a constant answer.

| Question | Accuracy | In the loop |
|---|---|---|
| Connectivity, floating parts | 12/12 | Pre-filter. By far the strongest |
| Gaps or holes in the surface | 10/12 | Pre-filter |
| Black, flipped or wrongly shaded faces | (10/12, withdrawn) | Do not delegate. `skip`: the defect is not in the capture; use the backface-culling comparison in `winding-flip-detection.md` |
| Finished object against bare boxes | 10/12 | Pre-filter |
| Consistent proportions | (10 to 12/12, withdrawn) | Do not delegate (retracted 2026-08-22). That score is unfalsified: the broken and fixed pair it was measured on held no proportion defect, so answering "yes" always scored perfectly. See the next section |
| Bevels, chamfered edges | 6/12 | Do not delegate. It sits at the constant-answer floor, which confirms the 2026-07-30 warning that the two models gave opposite bevel verdicts |
| Faceted cylinders | At chance across 8 framings | Do not delegate, and do not rewrite it. Four phrasings were tested (2026-08-17) and the existing one is the best: 6/6 in framings where the round piece fills the frame, 1 or 2 of 3 in a framing of the whole object. Framing outweighs phrasing. The underlying failure is that the test object cannot answer it; see "Faceting question: closed" |

Two notes on the shipped JSON against this table. The bevel question has no `skip`, so it is still sent to the model, but its answer is not delegated. The eighth entry, ground contact, is active and has no row in the source's table.

### Before believing a high score from this table (2026-08-22)

A yes or no question has two failure modes that its own score hides, and the proportions row fell into both:

1. **The constant.** If the gold answer never changes value across the test set, a constant answer scores perfectly and the metric is unfalsified, not validated. The question looked like 10 to 12/12 because the pair it was measured on had no proportion defect. The check is one line: does the gold answer change value in the set? If not, you measured nothing.
2. **Confabulation.** Asked for a rationale, the model does not hesitate, it invents. Facing a flange 37% wider than expected, one model called it consistent with "standard fastener geometry" and another "appropriately scaled". A confident and false note is worse than "unsure".

Measured on 2026-08-17 with `gemma4:26b`, `qwen3.8:27b` and `qwen3.5:27b`: with two constructed defects, the question answered "yes" in all 9 cells (3 models × 3 variants). Asking instead for the measurement (the size and position of each piece as a fraction of the frame, scored by the direction of change) got 6/6 right on the same renders.

That measurement substitute is not implemented here: there is no `probe_truth.py` among this skill's scripts, and the question stays in `checks_hardsurface.json` as it is, with `skip`. Until it exists, this row is checked by eye and not delegated. One trap already bit when prototyping it: declaring a coordinate convention does not beat the model's own up and down prior. Asking for y = 0 at the bottom and mirroring its answers cut the vertical error from 0.107 to 0.017 of the frame. Use the image convention, or detect the mirror before scoring.

### Where it enters the loop

Between step 2 (capture the angles) and step 3 (look) of the loop in `SKILL.md`:

```cmd
python "<skill-dir>\vr_score.py" ask --checklist "<skill-dir>\checks_hardsurface.json" --model gemma4:26b --json --view assembled__iso _review\m__iso__iter3.png --view assembled__profile_R _review\m__profile_R__iter3.png --view assembled__profile_L _review\m__profile_L__iter3.png --view zoom_receiver__right_iso _review\m__receiver__iter3.png --view zoom_muzzle__front_iso _review\m__muzzle__iter3.png
```

If any of the five active questions triggers, fix and render again before spending the user's eyes. If none triggers, look anyway: the filter has approved nothing. The three excluded questions do not appear in the model's answers: inverted faces go to the mechanical comparison, and proportions and cylinders keep their declared gap until `probe_truth.py` and `facet_report.py` exist.

### The calibration gate: per question, with a broken and a fixed render

The shadow rule asks for at least 15 renders you have already judged before delegating a question (`vr_calibrate.py report` warns below 15). That is calibrating by accumulation, and it would have found none of the above: the same question goes from 7/12 to 11/12 just by changing the framing, and from 9/12 to 18/18 just by changing which other questions travel in the same call. A cheaper gate replaces it, and it also attributes the cause:

**Take two renders of the same object, one with the defect and one with it fixed, and ask the same question of both.** It needs no gold answer. It measures two different things:

- **Sensitivity.** Does the answer change where it should change?
- **Specificity.** Does it stay still where it should not change?

A judge that answers identically for both versions is not reading the model, whatever its score. Any mod with a before and an after serves as the test bench; nothing has to be built for it.

The accumulation runner is still shipped for the per-question agreement report:

```cmd
python "<skill-dir>\vr_calibrate.py" run --renders <folder> --checklist "<skill-dir>\checks_hardsurface.json" --models qwen3.5:27b gemma4:26b --shadow cal.jsonl
python "<skill-dir>\vr_calibrate.py" report --shadow cal.jsonl --verdicts verdicts.json --checklist "<skill-dir>\checks_hardsurface.json"
```

`verdicts.json` is written by the agent after looking at the same renders: `{"<render file name>": {"answers": ["yes", "no", "unsure"], "note": "optional"}}`, with the answers in the order of the active (not skipped) questions. The report prints the agreement per question, which is the unit that gets delegated, not the model as a whole. It marks a question DELEGABLE at 0.85 or more, agent-side under 0.7 and borderline between; a verdicts file whose answer count does not match the active questions is skipped with a warning, because the positions moved when entries gained `skip`. Agreement is not accuracy: a model that mirrors the agent's blind spots scores well, which is acceptable for a pre-filter and not for a gate.

### Three things that invalidate a framing comparison

1. **The batch of the call changes the answer.** The same question, image and model scored 18/18 in a call with four other shading questions and 9/12 in the call with all eight of the checklist. Comparing framings requires a fixed batch. And it is not the size: removing one question from the batch made the two that stayed worse.
2. **A framing without a fixed render cannot be compared** with one that has it: it scores over half the cells, and there a constant answer gets 6/6.
3. **The temperature is 0.1** in the request, so two samples of the same cell come out almost identical. The effective `n` is the number of cells, not the number of samples. Do not confuse repeating with measuring.

### Scope

All of the above comes from a single object. The day before, the author had recorded that these models "do not detect geometric defects", and it was false: it measured the harness, not the models, and closed a line of work that was working. Before writing that a model cannot do something, vary the phrasing, the framing and the batch, and state which of the three was varied (LL-289).

## What the local judges hold up on (2026-08-21)

The whole shipped checklist, over a pair of renders differing only in facet count (48 against 6 sides), 3 seeds. Only the faceting question should move; everything else should hold still.

| Model | Correct | The miss |
|---|---|---|
| `qwen3-vl:30b` | 8/8 | None |
| `ornith-1.5:9b` | 7/8 | Calls the smooth variant holed, 2 of 3 seeds |
| `muse-glimmer:30b` | 7/8 | Reads the faceted variant as bevelled, 3 of 3 seeds |

The incumbent is the cleanest of the three, and a bigger or newer model did not beat it. Scope: one object, one pair, one framing where the round part fills the frame, which is the condition where the faceting question is already known to work. It screens models; it does not rank them.

## Faceting question: closed (SP-282, added 2026-08-31)

Do not rewrite the faceting question and do not delegate it. The current phrasing is the best of four measured, but that does not make it a gate. Asked alone it got 6/6; inside the batch of eight that `vr_score.py` builds it fell to 3/6. On the real object it produced 8 false alarms out of 12: the visible octagonal piece is intentional, and the real smoothed cylinders have a sagitta under one pixel in those framings. Therefore:

- Keep the question unchanged, with `skip`. It does not enter the active checklist or the pre-filter.
- Do not describe the result as chance: the failure changes with the framing and the grouping.
- If you ask it to count a profile, frame the cross-section until it fills the frame. The generic distance `max_dim * 2.2` leaves the axial view of a long object without information.
- The correct substitute is deterministic, and it reports instead of judging: part, sides, radius, relative deviation and sagitta, with an allowlist for intentional prisms. Intent stays the modeler's decision.

`facet_report.py` is not shipped in this skill. This section sets its contract and its limits; it does not claim the program exists.

## Contract for the faceting report (SP-284, added 2026-08-31)

If `facet_report.py` is added, the calibrated candidate rule is `sides < 12` and `radius >= 6 mm`, never the provisional 4 mm threshold. It also requires a nearly square cross-section: a ratio between the sides of the transverse bounding box of at most 1.30. That limit admits pentagons and hexagons and rejects the planar shapes that the 20% outer filter mistakes for a cylinder. An allowlist silences deliberate prismatic profiles.

The coverage report matters as much as the flags. It must publish:

- the meshes visible in the render and the parts with a circular profile
- the polygons examined, and their percentage of the visible ones
- the largest mesh not examined, and its percentage

`0 marked` is INCONCLUSIVE when no mesh is visible, or when a single unexamined mesh holds 30% or more of the polygons. The overall percentage covered does not decide the verdict: an asset made mostly of boxes and rails can have low coverage and still be valid for the parts examined.

Declared calibration: 0 false alarms across 41 circular-profile parts from three real assets, all three parts of the synthetic defect stayed marked, and the 12-sided and 48-sided probes stayed clean. Limits: it works per object, it does not see tubes inside a merged mesh, it can miss thin or heavily slotted profiles, and it does not certify that geometry it did not flag is round. The corpus includes no published mod verified in game; do not raise this report to a final gate.
