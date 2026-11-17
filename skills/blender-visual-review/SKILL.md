---
name: blender-visual-review
description: "Renders a Blender model from several angles through the Blender MCP, checks the images against a defect checklist, and confirms each fix by rendering the same angles again. Use when a model looks off, when the user asks to check, look at or review a model or a render, or suspects inverted normals, exploded parts or scale drift, and before calling a model done or exporting it. Complements blender-assembly, which checks numbers only. It cannot judge DayZ face winding: that is /dayz-p3d-audit."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# Blender visual review

`verify_bounds()` and `audit_all()` from `blender-assembly` prove a model's topology is clean: parts overlap, transforms are applied, nothing is silently scaled twice. They cannot prove the model is right. A chair facing backwards, a quad bike sunk into the ground, a roof at half scale, faces lit from the inside: each passes a numeric audit and fails the moment a person looks. Numbers verify topology; only eyes verify intent.

This skill is the other half of the loop: render the model, look at the images, diagnose what you see, fix one thing, and render the same angles again to confirm. Run the numeric checks in `blender-assembly` and the visual checks here.

It needs a Blender MCP server connected to the session (`execute_blender_code` and `get_screenshot_of_area_as_image`); this repo configures none. The scripts next to this file are plain Python 3.10 or later with no packages to install, and none of them needs `P:\`, DayZ Tools or the game. This is a review method, not a statement about the game: where a DayZ fact appears it says who measured it.

## What to read

| Question | Read or run |
|---|---|
| Has the fix loop gone on too long, and what should happen next | `<skill-dir>\correction_loop.py` ("Bounded loop" below) |
| Did a fix actually change the render, and did anything else drift | `<skill-dir>\vr_delta.py` ("Delta check" below) |
| How to detect a winding flip that a lit render hides, with the measurements behind it | `<skill-dir>\references\winding-flip-detection.md` |
| Using a free local vision model as a pre-filter: which questions it may answer, how it was calibrated, how to run `vr_score.py` and `vr_calibrate.py` | `<skill-dir>\references\local-vlm-judge.md` |
| The JSON format of a question checklist, `--view` routing, and how each question's view was chosen | `<skill-dir>\references\checklist-format.md` |
| The starter checklist for hard-surface models (8 questions, 5 active) | `<skill-dir>\checks_hardsurface.json` |

## When to use

- After you build, import or modify any model.
- Before you call a model done or export it.
- Whenever the user says it looks off, or asks you to check, look at or review a model.
- For DayZ, before spending an in-game test cycle: a render is free and an in-game iteration is not.

## The loop

1. **Set up an honest view.** Frame the object, add a scale reference, pick diagnostic shading.
2. **Capture from several angles.** One angle hides defects: a gap invisible head on, a normal wrong on one side only.
3. **Look, against the checklist.** Walk the categories below so you do not miss a whole class of defect.
4. **Fix one diagnosis at a time.**
5. **Render the same angles again** and compare before and after. A fix you did not capture again is a fix you did not verify.

## Bounded loop: typed outcomes and a stop policy

Step 4 says to fix one diagnosis at a time; this section bounds how many times. Visual iteration with no bound is a documented failure (a racing-game rip went N rounds on a red visual before anyone escalated to a person; the cap on in-game test rounds exists for the same reason). Every review iteration ends by choosing exactly one action:

- `continue`: this aspect is good; move to the next check or part.
- `refine-spec`: the plan was wrong or shallow (a missing detail row, a wrong connection-map entry, the wrong route). Go back to `blender-assembly` Phase 1 or 1.5, fix the plan and rebuild from it. Patching geometry around a wrong plan burns iterations without converging.
- `refine-code`: the plan is sound and the build does not match it. Fix the geometry or the material.
- `request-input`: show the user the evidence (before and after renders, what was tried, what still fails) and stop iterating.
- `stop`: the target cannot be reached from this input (an unusable reference, the wrong approach). Say so instead of faking progress.

Keep an iteration history per model, stored next to the renders as `_review\history.json`: a JSON list with one entry per iteration, `{"fidelity": <your visual score from 0 to 1>, "defectTags": ["short-stable-labels"], "reverted": <true if the fix made it worse and was undone>}`. After appending each iteration, run the stop policy:

```cmd
python "<skill-dir>\correction_loop.py" --history _review\history.json --json
```

Always pass `--json`: the plain output contains a `Δ` that crashes a cp1252 console. Options: `--target` (default 0.85), `--max-iter` (default 6), `--min-delta` (default 0.02). Exit code 0 means keep iterating, 1 means stop (the JSON says with which action), 2 means the history could not be read.

| Condition (in priority order) | Verdict |
|---|---|
| Fidelity at or above the target and no open defect tags | Stop: `continue` |
| The same defect tag survived 2 consecutive fixes | Stop: `refine-spec`. The plan is wrong, not the code |
| Oscillating: 2 reverted fixes, or the score changed direction | Stop: `refine-spec` |
| Progress stalled (gain under 0.02, below the target) | Stop: `request-input` |
| 6 iterations | Stop: `request-input`. Cannot be bypassed |

The script is the cycle counter nobody keeps under pressure. NEVER argue past its stop verdict with "one more try will fix it": that is the exact failure it exists to catch. Escalate with the evidence instead.

### Per-feature gates

A global "looks right" cannot rescue a failed critical feature. The detail list from `blender-assembly` Phase 1.5 is this review's contract. Its identity-defining rows, the ones that make the object this object (a grille shape, a stock profile, a hinge), each get their own pass or fail during step 3, judged on a crop at native resolution (LL-153). A render that reads well overall with one wrong critical feature fails the iteration; record that feature's tag in `defectTags`.

### Report honestly: "improved" is not "done"

Each iteration's note states what changed, with numbers ("guard edge extended -0.56 to -0.48"), why, what still does not match, and what the current check is blind to ("passes front view; top view not rendered again"). A feature that got closer is "improved", never "done". Loose wording here is how a defect survives into the next session.

## Two ways to see

There are two ways to get pixels back, and they answer different questions.

**Quick viewport screenshot.** `get_screenshot_of_area_as_image(area_ui_type="VIEW_3D")` returns the current viewport in one call, with no file step. Use it for "what does it look like right now", and for the Face Orientation overlay below, which shows only in the viewport, never in a render.

**Reproducible multi-angle render.** Place a camera at fixed angles, render each to a file, then `Read` the files. Use it when you need identical framing every iteration, clean lighting, and before and after evidence. The helper below renders all angles in one call and also returns the measurable numbers (dimensions, lowest vertex, counts), so numeric and visual come together.

Rule of thumb: screenshot to glance, render to judge.

## Setup that keeps captures honest

**Scale reference.** Proportion errors are invisible without a yardstick. Put a 1 m cube at the origin so every render carries a known unit (`size=2` so scale is the half-extent, as in `blender-assembly`):

```python
import bpy
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0.5))
ref = bpy.context.active_object
ref.name = "VR_ScaleRef_1m"
ref.scale = (0.5, 0.5, 0.5)            # a 1 m cube sitting on z=0
bpy.ops.object.transform_apply(scale=True)
ref.display_type = 'WIRE'              # wireframe so it never hides the model
```

**Diagnostic shading.** For shape and topology, Solid shading with cavity shows facets and pinching that smooth shading hides. For the direction of normals, the Face Orientation overlay paints front faces blue and back faces red: the fastest detector of inverted normals there is (viewport only). Set it, then take a viewport screenshot:

```python
import bpy
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        sp = area.spaces.active
        sp.shading.type = 'SOLID'
        sp.shading.show_cavity = True            # facets / pinching
        sp.overlay.show_face_orientation = True  # front = blue, back = red
        break
```

Workbench needs no scene lights (it has its own studio light), which avoids the classic render that came out black because the scene has no lamp. Use Workbench for diagnosis; switch to EEVEE or Cycles only when you are judging materials.

**Render paths in `blender -b` are absolute** (SP-451, measured 2026-10-01). A relative `render.filepath` without the `//` prefix saved the renders in a folder at the root of the drive, not in the working folder. Pass absolute paths.

## Multi-angle capture

Run this through `execute_blender_code`. It renders the object from front, right, top and iso to files you can read, restores the scene's original camera and engine, and returns the file paths and the measurable diagnostics. Then `Read` each path and look.

```python
import bpy, os, tempfile
from mathutils import Vector

def vr_capture(obj_name, tag="iter1", out_dir=None, res=900):
    obj = bpy.data.objects[obj_name]
    scene = bpy.context.scene

    # world-space bounds of the base mesh (good enough to frame and measure)
    vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    center, dims = (lo + hi) * 0.5, (hi - lo)
    max_dim = max(dims.x, dims.y, dims.z) or 1.0

    if out_dir is None:                       # a folder you can also Read afterwards
        base = bpy.path.abspath("//") if bpy.data.filepath else tempfile.gettempdir()
        out_dir = os.path.join(base, "_review")
    os.makedirs(out_dir, exist_ok=True)

    prev = (scene.render.engine, scene.camera, scene.render.filepath,
            scene.display.shading.show_cavity)
    scene.render.engine = 'BLENDER_WORKBENCH'         # fast, self-lit
    scene.display.shading.show_cavity = True          # facets / pinching in the render
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100

    cam_data = bpy.data.cameras.new("VR_Cam")
    cam = bpy.data.objects.new("VR_Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    dist = max_dim * 2.2

    views = {"front": (0,-1,0), "right": (1,0,0), "top": (0,0,1), "iso": (1,-1,0.8)}
    renders = []
    for name, off in views.items():
        cam.location = center + Vector(off).normalized() * dist
        cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join(out_dir, f"{obj_name}__{name}__{tag}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        renders.append(path)

    (scene.render.engine, scene.camera, scene.render.filepath,
     scene.display.shading.show_cavity) = prev        # restore, then drop temp camera
    bpy.data.objects.remove(cam, do_unlink=True)
    if cam_data.users == 0:
        bpy.data.cameras.remove(cam_data)

    return {"renders": renders,
            "dims": [round(c, 4) for c in dims],
            "lowest_z": round(lo.z, 4),
            "center": [round(c, 4) for c in center],
            "counts": {"verts": len(obj.data.vertices), "faces": len(obj.data.polygons)}}

result = vr_capture("YOUR_OBJECT")   # set the object name; optional: tag=, out_dir=, res=
```

`Read` each path in `result["renders"]` and look. Use `result["dims"]`, `result["lowest_z"]` and `result["counts"]` as the measurable backbone for the checklist. The bounds come from the base mesh; if a modifier changes the silhouette, apply it or evaluate the dependency graph first.

## Diagnostic checklist

Walk every category: the point of a checklist is to catch the defect you were not already worried about. Each item is a concrete signal you can check, tied to a number or a specific visual cue. An invariant written as loose prose gets nodded at and skipped (LL-062).

### A. General 3D correctness (every model)

- **Orientation.** Does forward point where it should? Is anything upside down or mirrored? Read it against the scale cube and the world axes, not from memory.
- **Proportion and scale.** Measure against the 1 m cube and `result["dims"]`. "Looks small" is a prompt to check the number, not a conclusion.
- **Inverted or black normals.** Face Orientation overlay: any red facing the camera is a back face you are seeing through. Also watch for surfaces lit as if from inside.
- **Shading artifacts.** Black facets, pinching, smooth shading bleeding across a hard edge, ngons on curved areas.
- **Exploded or floating parts.** Gaps between parts that should touch; a part hovering off its mount. `verify_overlap` from `blender-assembly` catches the ones that can be measured; the eye catches the rest.
- **Doubled geometry.** A shimmer that flickers between angles means two faces occupy the same place (z-fighting).
- **Animated parts: clearance per keyframe, not per render.** Presentation renders only show posed frames; impacts hide behind walls or closed doors. Evaluate the depsgraph mesh at every keyframe and at intermediate points of each travel span: `BVHTree.overlap` between each moving mesh and each fixed mesh, a sweep of fixed-geometry points (vertices, face centers, edge centers) that fall inside the part's footprint at rest and its travel range, and section cuts on the travel planes. A flush contact also reports as overlap; tell it from a penetration by measuring how deep the geometry enters the footprint, not how many triangles cross. Measured exactly on an animated rock platform (2026-10-01): its 9 presentation cameras showed nothing, while the sweep found a 12 × 14.6 m platform crossing a lip 0.27 m into its footprint, and an elevator cabin crossing the top threshold (0.14 m) on every ride, visible only from inside at frame 145.
- **Workbench `color_type = 'TEXTURE'` paints one image of the material, not its shading.** Measured exactly (2026-10-01): on a vanilla rock, the `rock_*_mask` input rendered as flat RGB mask colors and looked like a defect. Judge materials in EEVEE with the file's own lights.

### B. DayZ parity against a vanilla reference

Import a known-good vanilla model into the same scene at 1:1 and compare side by side (the import path is in `dayz-model-pipeline`). Anchor each check to the reference, not to taste:

- **Orientation and scale.** The same forward axis and roughly the same footprint as the vanilla equivalent.
- **Ride height (measurable).** For a ground item, the lowest vertex (`result["lowest_z"]`) sits at about the ground plane (z ≈ 0). For a vehicle, the wheel contact is at about ground level and the chassis belly clears it well: the source author measured a belly clearance of about 0.43 m on a vanilla sedan (a measurement on the binarized model, not checked on `P:\` here), and a wheel that is too small sinks the body. Measure it; do not eyeball "looks grounded" (LL-062). The vehicle structural parity notes are in the vehicles pack (`skills/_shared/vehicles/`).
- **Proxies and slots present.** Wheels, the FireGeo bulk and lights are visibly where the vanilla model has them.

### C. Comparison against a reference image

When matching a photo or a concept: load the reference as a camera background image (`cam_data.show_background_images = True`, then `cam_data.background_images.new().image = bpy.data.images.load(path)`), match the camera to the reference's angle, render, and compare named landmarks (roofline, wheel arch, handle position), not the overall impression. Report silhouette deviation, missing or extra masses and proportion drift by pointing at specific points.

### D. Scoring resemblance to a photo: calibrate the camera first (added 2026-09-25, SP-427)

- **One Blender camera per reference photo, calibrated by silhouette IoU.** Maximize the IoU between the Workbench alpha silhouette and the photo mask (Nelder-Mead over location, yaw, pitch, roll and focal length, started from a feature of known size such as the tyres from the spec sheet). Judge only photo and render crops taken with that same camera. With a "similar" camera set by eye, proportion errors (a wing out of place, a dome floating 5 cm) stay invisible.
- **Poor or partial views.** Low resolution or off-angle photos converge to a false camera (IoU 0.81 on a brochure front view). Solve PnP on 6 to 8 points triangulated across other photos instead, and reject any refinement that lowers the silhouette IoU (a bundle with 2 anchors moved the camera 38 cm along the view rays and dropped the IoU from 0.936 to 0.923).
- **Silhouette renders.** Set `render.use_compositing = False`: an Alpha Over compositor makes the whole silhouette opaque when `film_transparent` is on.
- **Judge blind, across model families.** Measured exactly in Blender 5.1.1 headless against studio photos (2026-09-25): self-scores from the same model family ran 1 to 2 checklist points above a blind audit by another model family over the same 27 image sets. The working score is the minimum, per criterion, of the self score and the blind score.

## Hard guardrail: a Blender render cannot judge DayZ winding

Blender, like any Three.js viewer, renders right-handed; DayZ culls left-handed. A model that looks perfectly solid in Blender can render inside out in game. This is a logged error of the source author, not a hypothetical: a render was used to declare "normals not inverted", and the exterior turned out transparent in game. Why a right-handed check misleads is in `skills/dayz-p3d-audit/references/winding-methodology.md`.

- **NEVER conclude that DayZ face winding or normal direction is correct from a Blender render or screenshot.** The render cannot tell you. Absolute winding is decided by `/dayz-p3d-audit` (its edge-pair topology check) and in game, not by eye.
- The only valid visual signal for winding is relative: the model winds the same way as a vanilla reference imported beside it. "Same as vanilla" means something; "looks fine to me" does not.
- The Blender to DayZ map is the det = -1 reflection `(x,y,z) -> (x,z,y)` with negated normals (`dayz-model-pipeline` Rule 12, measured in game by the source author on 2026-10-01; not checked on `P:\`, where vanilla models are binarized). A render cannot judge the result: the older det = +1 recipe renders solid in Blender and in DayZ and is still mirrored. Check chirality in game on text or on a one-sided part.

Everything else here (orientation, proportion, scale, exploded parts, ride height, match to a reference) the render judges well. Winding is the one thing it cannot; hand that to `/dayz-p3d-audit`.

A winding flip can still be caught early in Blender by two mechanisms that read the winding itself and ignore the declared normals: the Face Orientation overlay seen from outside the model, and a second render with backface culling on, compared with the first. Run them on any import from glTF, FBX or OBJ, on any pipeline with a configurable `reverse_winding`, and on any build for an engine that culls by winding. The workflow, the verdict rule and the measurements are in `references/winding-flip-detection.md`.

## Delta check (report only)

Before judging a fix by eye, run the pixel comparator on the before and after pair of the same angle:

```cmd
python "<skill-dir>\vr_delta.py" _review\model__front__iter1.png _review\model__front__iter2.png --json
```

It reports silhouette IoU, scale and aspect deltas of the bounding box, SSIM, edge overlap, tonal, blowout and flat parity, and which signals moved beyond same-camera noise. Exit code 0 on a report, 2 when an image cannot be read (8-bit PNG without interlacing only). Two uses:

- **Prove the fix landed.** An intended edit must move at least one signal. `identicalImages: true` after an edit means the old scene was rendered again, a failure that has been reproduced: the stale render depsgraph described in `blender-assembly` (`references/mcp-render-pitfalls.md`).
- **Catch collateral drift.** Signals moving that the edit should not touch: a tonal shift after a pure geometry fix, a silhouette change after a material tweak.

These numbers are a change filter, never a correctness verdict (LL-153). Correctness is decided by eyes on the renders and on crops at native resolution. Use it on same-camera pairs only: scoring a render against a reference photo is not calibrated here, because framing and background mismatch break every signal. That comparison stays with the named landmarks of checklist C.

Outside an agent session, `scripts\dayz\render-delta.bat` runs `vr_delta.py` with the same arguments.

## Free local second opinion (shadow mode)

A local vision model served by Ollama can answer checklist questions about renders at no credit cost, so the agent's budget goes to gates and final judgment instead of every glance inside the loop.

```cmd
python "<skill-dir>\vr_score.py" ask _review\model__iso__iter3.png --checklist "<skill-dir>\checks_hardsurface.json" --model gemma4:26b --json
python "<skill-dir>\vr_score.py" score _review\model__iso__iter3.png --reference ref.jpg --model gemma4:26b --json
```

Prefer `ask` over `score`: concrete yes or no questions are measurably easier for a small vision model than open judgment, and each "no" is a specific pointer instead of an opaque number. Derive the questions from the model's own detail list (`blender-assembly` Phase 1.5); `checks_hardsurface.json` is the generic starter set.

The local model's answers are evidence logged beside your own. They are never a gate and never a substitute for looking. The filter can reject, never approve: a "no" triggers a fix before anything is shown, and a clean pass only means the render now deserves your eyes. Which questions are delegated, how each was calibrated, the Ollama setup and the calibration runner are in `references/local-vlm-judge.md`. Read it before relying on any answer.

## Output and evidence

Render into a folder you can also read. The helper defaults to a `_review\` folder next to the `.blend`, or the OS temp folder when the file is unsaved; for a `.blend` kept inside `workspace\<ModName>\`, pass `out_dir` under `output\<model>-review\` so the renders stay out of the mod folder. Name files `<model>__<angle>__<iter>.png`. Keep the before and after pair for any angle you changed, so the diagnosis can be audited and you can prove the fix landed.

## Rules from the author's lessons log (added 2026-07-27)

Each rule keeps the `LL-NNN` number of the lesson it came from. The lessons log itself (symptom, origin, evidence) is the author's private file and is not in this repo.

- **LL-153.** Judge every critical visual zone on a crop at native resolution. Use RMS and scores only as a change filter, never as a correctness verdict, and keep the full-resolution crop as evidence.
