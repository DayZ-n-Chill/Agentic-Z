# Reviewing animation without scrubbing

How an agent that cannot scrub a timeline checks Blender animation: the numeric self-audit on F-curves, cheap still and preview renders, which frames to look at and for what, and the stages from blocking to polish. The principles and frame counts are in `blender-realism-and-review.md`; driving Blender is in `blender-mcp-workflow.md`.

This is Blender behaviour and animation craft, run against Blender 5.1 or taken from the API reference, so nothing here cites `P:\`. Thresholds are starting points to tune per shot.

## Reaching the curves on 5.x

`action.fcurves` is gone from 5.0. On 5.x:

```python
from bpy_extras import anim_utils
def get_fcurves(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return []
    cb = anim_utils.animdata_get_channelbag_for_assigned_slot(ad)   # 5.x only
    if cb is not None:
        return list(cb.fcurves)
    return list(getattr(ad.action, "fcurves", []))
```

`animdata_get_channelbag_for_assigned_slot` does not exist on 4.3 to 4.5, so there this raises `AttributeError` before the fallback. When 4.x must work, use the `get_fcurves` in `blender-bpy-sim-baking-export.md`, "Reading baked keys back". Edit curves through the data (`kp.interpolation`, `fcu.extrapolation`); `bpy.ops.graph.*` fails without a Graph Editor. New keys in a default install are `BEZIER` with `AUTO_CLAMPED` handles, but that is a user preference, so set interpolation explicitly. The interpolation on a key governs the segment from it to the next key.

## The self-audit

Three numbers, run on a deliberately robotic test rig (all linear, keyed in lockstep, a mirrored pair) and on a hand shaped organic curve, separate the two completely: robotic gives `linear_ratio` 1.0, unison 1.0 and overshoot 0.0 with the mirror found; organic gives 0.0, 0.0 (channels staggered 3 frames) and 0.25 (its `BACK` and `ELASTIC` segments overshoot).

```python
from collections import Counter

def linear_ratio(fcurves):
    total = linear = 0
    for fcu in fcurves:
        for kp in fcu.keyframe_points:
            total += 1
            if kp.interpolation == 'LINEAR':
                linear += 1
    return linear / total if total else 0.0

def keyframe_unison_ratio(fcurves, share_fraction=0.6):
    per_curve = [[round(kp.co[0], 3) for kp in f.keyframe_points] for f in fcurves]
    counter = Counter(fr for frames in per_curve for fr in frames)
    total = sum(len(f) for f in per_curve)
    if total == 0 or len(fcurves) < 2:
        return 0.0
    threshold = max(2, int(share_fraction * len(fcurves)))
    shared = sum(1 for frames in per_curve for fr in frames if counter[fr] >= threshold)
    return shared / total

def overshoot_ratio(fcurves, samples=8, tol=0.02):
    hits = segs = 0
    for fcu in fcurves:
        kps = fcu.keyframe_points
        for i in range(len(kps) - 1):
            f0, v0 = kps[i].co; f1, v1 = kps[i + 1].co
            if f1 <= f0: continue
            segs += 1
            lo, hi = sorted((v0, v1)); span = hi - lo
            if span < 1e-6: continue
            for s in range(1, samples):
                val = fcu.evaluate(f0 + (f1 - f0) * s / samples)
                if val > hi + tol * span or val < lo - tol * span:
                    hits += 1; break
    return hits / segs if segs else 0.0
```

The checks, to flag rather than fail:

| Check | Flag when | Status |
|---|---|---|
| Linear ratio | Above 0.3 for character motion; 1.0 is certainly robotic. Machines and constant speed props are exempt. | Code above, run. |
| Unison ratio | Still above 0.8 after the offset pass. About 1.0 is correct while blocking. The strongest sign of a scripted look. | Code above, run. |
| No overshoot | 0 on every arrival with no hand keyed settle, so there is no follow-through. Machines may be 0. | Code above, run. |
| Speed jumps at keys | `fcu.evaluate` just before and after a key differ by over about 3 times the channel's median step, on a key not tagged `EXTREME` or contact. | Design only. |
| Frozen holds | Equal keys over more than 6 frames with no `MOVING_HOLD` tag. | Design only. |
| Twinning | Left and right pairs (`.L` and `.R`) keyed on the same frames with values correlating above 0.999, sign allowed. | Design; an exact mirror was detected in the run. |
| Arc jitter | Second differences over `motion_path.points[i].co` flip sign at high frequency, or a limb tip has near zero curvature during broad gestures. Jerk is the usual smoothness measure in motion capture cleanup. | Design; reading motion paths works. |
| Foot slide | Horizontal movement of the foot while its world height is below a contact threshold, summed over contact frames; sample with `scene.frame_set(f)` and `obj.evaluated_get(depsgraph).matrix_world`. | Design only. |
| Tag consistency | An `EXTREME` arrival without ease out or overshoot, a `MOVING_HOLD` pair that does not drift, or a breakdown sitting exactly halfway. | Design only. |

## Stills and previews

These run from a script with the scene camera. In the live MCP session `bpy.ops.render.opengl` is the fast path; under `blender -b` it fails with no OpenGL context, so use `bpy.ops.render.render` on Workbench or EEVEE (`blender-mcp-workflow.md`, "Runtime rules").

Key pose stills, the cheapest review (a 480×270 PNG takes under a second):

```python
scene = bpy.context.scene
scene.render.resolution_percentage = 25
scene.render.image_settings.file_format = 'PNG'
for f in [1, 12, 24]:                      # contacts, extremes, story beats
    scene.frame_set(f)
    scene.render.filepath = f"//review/pose_{f:04d}.png"
    bpy.ops.render.opengl(write_still=True, animation=False, view_context=False)
```

`view_context=False` renders from the scene camera with scene settings rather than whatever viewport exists; always pass it. The signature is `bpy.ops.render.opengl(animation=False, render_keyed_only=False, sequencer=False, write_still=False, view_context=True)`.

A preview sequence for motion:

```python
scene.frame_start, scene.frame_end = 1, 48
scene.render.filepath = "//review/blast_"
bpy.ops.render.opengl(animation=True, view_context=False)   # blast_0001.png and on
```

`render_keyed_only=True` renders only frames where selected objects have keys, a contact sheet of the blocking (not run).

## Video output

On 5.1, `image_settings.file_format = 'FFMPEG'` is refused while `media_type` is an image type, since the list then holds only image formats (`AVIF`, `JPEG`, `OPEN_EXR`, `PNG`, `WEBP`, `BMP`, `CINEON`, `DPX`, `IRIS`, `JPEG2000`, `HDR`, `TARGA`, `TARGA_RAW`, `TIFF`). Set `media_type = 'VIDEO'` first. FFmpeg is also a build option (`bpy.app.build_options.codec_ffmpeg`), so never assume video exists; test by assigning inside `try` and fall back to PNGs.

```python
def enable_video(scene):                      # the ffmpeg lines were not run
    r = scene.render
    ims = r.image_settings
    try:
        if hasattr(ims, "media_type"):        # 5.x
            ims.media_type = 'VIDEO'
        ims.file_format = 'FFMPEG'
    except TypeError:
        return False                          # no FFmpeg: use a PNG sequence
    r.ffmpeg.format = 'MPEG4'                 # also QUICKTIME, MKV, WEBM
    r.ffmpeg.codec = 'H264'                   # also H265, AV1, WEBM, PRORES
    r.ffmpeg.constant_rate_factor = 'MEDIUM'
    return True
```

Save `media_type` and `file_format` before and restore them after. PNG sequences are the safe default, and single stills suit an agent that cannot watch a video anyway.

## Speed settings

- Engine names change by version. 5.1 takes `BLENDER_EEVEE`, `BLENDER_WORKBENCH` and `CYCLES` and refuses `BLENDER_EEVEE_NEXT`, EEVEE's name in 4.2 to 4.5. Static enum lists showed only the current engine, so test by assigning inside `try`.
- `render.opengl` draws like the viewport in solid shading whatever the engine, which is the preview look; use it for every motion check. Use a full `render.render` with EEVEE only when lighting matters, and Workbench for the fastest silhouettes.
- Review at 25 to 50 percent resolution.
- `scene.frame_step = N` renders every Nth frame for long shots, or loop `frame_set` over a chosen list.
- Render times depend on the machine, so none are given; stills at 480×270 are cheap enough for 10 to 20 per round.

## Which frames to look at

In priority order:

1. Story poses: if these do not read, nothing else matters.
2. Contacts: foot strikes, hand touches, impacts. Passing through, floating and sliding here are the most visible faults.
3. Extremes: changes of direction, the top of a jump, the end of a wind up, the deepest anticipation.
4. Passing positions: one per major transition, at the turn of the motion path, often the fastest moment.
5. The middle of each hold, to see that it is alive.
6. One and two frames after an impact, where overshoot and settle should show.

With keys tagged by type, the list comes for free: every `EXTREME` and contact, plus a `render_keyed_only` contact sheet.

What to check on stills: the silhouette reads (a flat lit or Workbench render approximates it); one clear line of action with weight over the base of support; no mirrored limbs; feet on the ground, nothing passing through, the hand wrapping the prop; and the pose changes between stills cluster small near holds and extremes and large mid action, since even steps mean even, robotic timing.

Only motion shows timing feel, pops, arc breaks in perspective, whether overlap reads as meant, and whether holds are alive or twitchy. The numeric checks catch most of these first; render the preview after they pass.

Without footage to compare, write the reference as a beat sheet with frame budgets from the timing table ("punch: 8 frames anticipation, 3 strike, 4 impact overlap, 12 recovery") and compare the key layout to it. A beat more than 30 percent off is either deliberate style or a flag.

## Working in stages

Block, then spline, then polish. Pose to pose fixes story, proportions and timing before motion exists and is quicker to revise; straight ahead output drifts and floats, which is what naive per frame scripts produce.

| Stage | Interpolation | What exists | Check before moving on |
|---|---|---|---|
| Plan | None | A beat sheet with frame budgets | Budgets add up to the shot; beats do not overlap. |
| Blocking | `CONSTANT` on every key | Story poses and contacts, every channel keyed per pose | Stills: silhouette, balance, contacts, spacing; the story reads. |
| Blocking plus | Still `CONSTANT` | Breakdowns, anticipations, key holds | Stills at breakdowns: arcs plausible, anticipation present. |
| Spline | `BEZIER`, with easing modes where wanted | Shaped eases, sharp `VECTOR` contacts, `BACK` overshoots | Linear ratio, overshoot, speed jumps; a short preview. |
| Offset | | Channels staggered 1 to 3 frames, follow-through keys, moving holds | Unison below threshold; holds drift; preview. |
| Polish | | Arc cleanup, small drift, secondary action, light noise | Full audit and full length preview with no unexplained flags. |

Switching blocking to spline is one loop setting `kp.interpolation` from `CONSTANT` to `BEZIER`. Stay stepped until the still review passes; stepped stills are the cheapest review there is.

Each stage needs at least one review and fix round, so a believable shot takes two to four rounds. Treat a shot that passes on the first round as not yet audited.
