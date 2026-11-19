# Reviewing a Blender model by eye

How to check a model in Blender by looking at it: render it from fixed angles, read the images against a checklist, fix one thing, render the same angles again, and stop when the stop rule says so. `verify_bounds()` and `audit_all()` (`blender-assembly-checks.md`) prove the topology is clean; they cannot prove the model is right. A chair facing backwards, a quad sunk into the ground or a roof at half scale passes every numeric check and fails the moment a person looks.

It needs a Blender MCP server in the session (`execute_blender_code` and `get_screenshot_of_area_as_image`); this repo configures none. The scripts are in `skills/dayz-model-tools/scripts/` (`correction_loop.py`, `vr_delta.py`, `vr_score.py`, `vr_calibrate.py` and the checklist `checks_hardsurface.json`): plain Python 3.10 or later with nothing to install, and none needs `P:\`, DayZ Tools or the game. It is a review method, not a fact about the game.

| Question | File or script |
|---|---|
| What to look for in the renders (orientation, scale, normals, animated parts, vanilla comparison, a reference photo) | `blender-review-checklist.md` |
| Catching a winding flip a lit render hides | `blender-winding-flips.md` |
| Has the fix loop gone on too long? | `correction_loop.py` ("The stop rule" below) |
| Did a fix change the render, and did anything else move? | `vr_delta.py` ("Did the fix land" below) |
| A local vision model as a first filter | `tools-vlm-judge.md` |
| The checklist JSON format and `--view` routing | `tools-vlm-checklist-format.md` |
| The starter checklist for hard surface models | `skills/dayz-model-tools/scripts/checks_hardsurface.json` |

## When to review

- After you build, import or change any model, and before you call it done or export it.
- Whenever the user says it looks off or asks you to look at it.
- Before an in-game test: a render is free and an in-game round is not.

## The loop

1. Set up an honest view: frame the object, add a scale reference, pick diagnostic shading.
2. Capture several angles. One angle hides defects: a gap invisible head on, a normal wrong on one side only.
3. Look, walking every category of `blender-review-checklist.md`.
4. Fix one diagnosis at a time.
5. Render the same angles again and compare. A fix you did not capture again is a fix you did not check.

Judge the parts that make the object itself (a grille shape, a stock profile, a hinge) one by one, each on a crop at native resolution. These are the main rows of the detail list (`blender-assembly.md`, "Plan the detail"). A render that reads well overall with one of them wrong fails the round; record that feature's tag.

Each round's note says what changed, in numbers ("guard edge moved from -0.56 to -0.48"), why, what still does not match, and what the check could not see ("front view passes; top view not rendered again"). A feature that got closer is "improved", never "done".

## The stop rule

Endless visual rounds do not converge on their own. End every round with exactly one action:

| Action | Meaning |
|---|---|
| `continue` | This part is good; go to the next check or part |
| `refine-spec` | The plan was wrong or thin (a missing detail row, a wrong joint, the wrong route). Fix the plan in `blender-assembly.md` and rebuild from it |
| `refine-code` | The plan is right and the build does not match it; fix the geometry or material |
| `request-input` | Show the user the before and after renders, what was tried and what still fails, and stop |
| `stop` | This input cannot reach the target (an unusable reference, the wrong approach); say so |

Keep a history per model next to the renders as `_review\history.json`, one entry per round: `{"fidelity": <your score from 0 to 1>, "defectTags": ["short-stable-labels"], "reverted": <true if the fix made it worse and was undone>}`. After each round run:

```cmd
python skills\dayz-model-tools\scripts\correction_loop.py --history _review\history.json --json
```

Without `--json` it prints one `stop=... action=... reason=...` line. Options: `--target` (default 0.85), `--max-iter` (default 6), `--min-delta` (default 0.02). Exit code 0 means keep going, 1 means stop with the action given, 2 means the history could not be read.

| Condition, first match wins | Result |
|---|---|
| Score at or above the target, no open defect tags | Stop with `continue` |
| The same defect tag survived two fixes in a row | Stop with `refine-spec`: the plan is wrong, not the code |
| Two reverted fixes, or the score changed direction | Stop with `refine-spec` |
| Gain under 0.02 while below the target | Stop with `request-input` |
| 6 rounds | Stop with `request-input`; no way around it |

Never argue past its stop with "one more try will fix it"; that is the failure it exists to catch. Take the evidence to the user instead.

## Screenshot or render

A viewport screenshot, `get_screenshot_of_area_as_image(area_ui_type="VIEW_3D")`, returns the current view in one call. Use it to glance, and for the Face Orientation overlay, which shows only in the viewport. A render from a fixed camera to a file gives the same framing every round, clean lighting and before and after evidence. Screenshot to glance, render to judge.

## Setting up an honest view

Put a 1 m wire cube at the origin so every render carries a known size:

```python
import bpy
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0.5))
ref = bpy.context.active_object
ref.name = "VR_ScaleRef_1m"
ref.scale = (0.5, 0.5, 0.5)            # a 1 m cube standing on z=0
bpy.ops.object.transform_apply(scale=True)
ref.display_type = 'WIRE'              # never hides the model
```

For shape, Solid shading with cavity shows facets and pinching that smooth shading hides. For normals, the Face Orientation overlay paints front faces blue and back faces red (viewport only):

```python
import bpy
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        sp = area.spaces.active
        sp.shading.type = 'SOLID'
        sp.shading.show_cavity = True            # facets and pinching
        sp.overlay.show_face_orientation = True  # front blue, back red
        break
```

Workbench has its own studio light, so it never renders black for want of a lamp. Use it to diagnose; switch to EEVEE or Cycles only to judge materials. In `blender -b`, a relative `render.filepath` without the `//` prefix saves to a folder at the root of the drive, so pass absolute paths.

## Capturing four angles

Run this through `execute_blender_code`. It renders front, right, top and iso to files, restores the scene's camera and engine, and returns the paths and the numbers to check. Then `Read` each path.

```python
import bpy, os, tempfile
from mathutils import Vector

def vr_capture(obj_name, tag="iter1", out_dir=None, res=900):
    obj = bpy.data.objects[obj_name]
    scene = bpy.context.scene
    vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    center, dims = (lo + hi) * 0.5, (hi - lo)
    max_dim = max(dims.x, dims.y, dims.z) or 1.0
    if out_dir is None:
        base = bpy.path.abspath("//") if bpy.data.filepath else tempfile.gettempdir()
        out_dir = os.path.join(base, "_review")
    os.makedirs(out_dir, exist_ok=True)
    prev = (scene.render.engine, scene.camera, scene.render.filepath,
            scene.display.shading.show_cavity)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.show_cavity = True
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
     scene.display.shading.show_cavity) = prev
    bpy.data.objects.remove(cam, do_unlink=True)
    if cam_data.users == 0:
        bpy.data.cameras.remove(cam_data)
    return {"renders": renders,
            "dims": [round(c, 4) for c in dims],
            "lowest_z": round(lo.z, 4),
            "center": [round(c, 4) for c in center],
            "counts": {"verts": len(obj.data.vertices), "faces": len(obj.data.polygons)}}

result = vr_capture("YOUR_OBJECT")   # optional: tag=, out_dir=, res=
```

Use `result["dims"]`, `result["lowest_z"]` and `result["counts"]` as the numbers behind the checklist. The bounds come from the base mesh; if a modifier changes the outline, apply it or evaluate the depsgraph first.

## Did the fix land

Before judging a fix by eye, compare the before and after renders of the same angle:

```cmd
python skills\dayz-model-tools\scripts\vr_delta.py _review\model__front__iter1.png _review\model__front__iter2.png --json
```

It reports silhouette IoU, bounding box scale and aspect changes, SSIM, edge overlap, tone, blowout and flat parity, and which signals moved beyond same camera noise. Exit code 0 on a report, 2 when an image cannot be read (8-bit PNG without interlacing only). Outside an agent session, `scripts\dayz\render-delta.bat` runs it with the same arguments.

- An intended edit must move at least one signal. `identicalImages: true` after an edit means the old mesh was rendered again (`blender-assembly-checks.md`, "Render traps over MCP").
- Signals that the edit should not touch must stay still: no tone shift after a pure geometry fix, no outline change after a material tweak.

These numbers only show change, never correctness; eyes on renders and native resolution crops decide. Use them on same camera pairs only. A render against a reference photo is not calibrated here; compare named landmarks instead (`blender-review-checklist.md`).

## A local model as a first filter

A local vision model served by Ollama can answer checklist questions about renders for free, leaving the agent's budget for the decisions:

```cmd
python skills\dayz-model-tools\scripts\vr_score.py ask _review\model__iso__iter3.png --checklist skills\dayz-model-tools\scripts\checks_hardsurface.json --model <model> --json
python skills\dayz-model-tools\scripts\vr_score.py score _review\model__iso__iter3.png --reference ref.jpg --model <model> --json
```

Prefer `ask` over `score`: concrete yes or no questions are easier for a small model, and each "no" points at something. Take the questions from the model's own detail list; `checks_hardsurface.json` is a generic starter set. The answers are evidence logged beside yours, never a gate: a "no" triggers a fix, and a clean pass only means the render now deserves your eyes. Read `tools-vlm-judge.md` before relying on any answer.

## Where renders go

The helper writes to `_review\` next to the `.blend`, or to the system temp folder for an unsaved file. For a `.blend` inside `workspace\<ModName>\`, pass `out_dir` under `output\<model>-review\` so renders stay out of the mod. Name files `<model>__<angle>__<iter>.png`, and keep the before and after pair for every angle you changed.
