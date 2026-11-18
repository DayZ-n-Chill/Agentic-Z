# Animation realism and the iterate, review, polish loop in Blender (bpy)

The twelve animation principles in F-curve terms, fixes for robotic motion, a timing table, the programmatic self-audit, preview and playblast recipes, the review method for an agent, the blocking-to-polish stages and camera feel.

Written for the workflow in `blender-mcp-workflow.md`. The reader is an agent driving a live Blender
through `execute_blender_code` (bpy), with no real-time viewport, that reviews its work
through rendered frames and programmatic f-curve inspection.

Everything here is Blender behaviour or general animation craft, checked against Blender
5.1.1 as marked. None of it is a fact about the DayZ game,
so nothing in this file cites `P:\`; the DayZ side of the work is in `blender-txa-export.md`. The
timing table is written at 24 fps; the DayZ pipeline default is 30 fps (see `blender-txa-export.md`),
so convert frame counts before using them for a DayZ clip.

Verification status: every bpy API marked **[VERIFIED 5.1.1]** was executed live against
Blender 5.1.1 through the MCP server (results quoted inline). APIs marked **[docs]** are taken
from the Blender Python API reference and were not executed. Frame counts are rules of thumb.
Code labels: `[EXACT]` = ran as shown; `[DESIGN]` = pseudocode/sketch, not executed.

## API ground rules (verified against live Blender 5.1.1)

These gate everything below — get these wrong and no principle can be implemented.

1. **`action.fcurves` is gone in 5.0+ (slotted/layered Actions).** Live 5.1.1:
   `action.fcurves` raises `AttributeError: 'Action' object has no attribute 'fcurves'`
   **[VERIFIED 5.1.1]**. Slotted Actions landed in Blender 4.4;
   4.4 and 4.5 kept `action.fcurves` as a legacy shim on the first slot, and 5.0 removed it
   (see "Export/handoff of sims" in `blender-bpy-physics.md`).
   New hierarchy: `Action -> layers[] -> strips[] -> channelbag(slot) -> fcurves`.
   Access on 5.x **[EXACT]**:
   ```python
   from bpy_extras import anim_utils
   def get_fcurves(obj):
       ad = obj.animation_data
       if not ad or not ad.action:
           return []
       cb = anim_utils.animdata_get_channelbag_for_assigned_slot(ad)  # 5.x only
       if cb is not None:
           return list(cb.fcurves)
       return list(getattr(ad.action, "fcurves", []))
   ```
   This ran on 5.1.1 only. `animdata_get_channelbag_for_assigned_slot` is not in
   `bpy_extras/anim_utils.py` on 4.3, 4.4 or 4.5, so there this function raises
   `AttributeError` before it reaches the `action.fcurves` fallback. When 4.x must work, use
   the `get_fcurves` in `blender-bpy-physics.md`: it tests `hasattr(action, "fcurves")` first and
   otherwise calls `action_get_channelbag_for_slot(action, slot)`, which exists from 4.4.
   Helpers verified live: `anim_utils.action_get_channelbag_for_slot(action, slot)`,
   `anim_utils.animdata_get_channelbag_for_assigned_slot(anim_data)`, and
   `action.fcurve_ensure_for_datablock(datablock, data_path, index=0, group_name="")`
   (creates layer/strip/slot as needed — its live docstring says so) **[VERIFIED 5.1.1]**.
2. **`obj.keyframe_insert(data_path, index=-1, frame=N, group="")` still works** and routes
   into the channelbag automatically **[VERIFIED 5.1.1]**.
3. **Prefer the data API over `bpy.ops.graph.*` / `bpy.ops.action.*`.** Graph-editor
   operators need a Graph Editor UI context; live headless call of
   `bpy.ops.graph.extrapolation_type(type='LINEAR')` failed with
   `RuntimeError: Operator ... poll() failed, context is incorrect` **[VERIFIED 5.1.1]**.
   Everything they do is reachable via `kp.interpolation`, `fcu.extrapolation`, etc.
4. **Keyframe point knobs** (`bpy.types.Keyframe`):
   - `kp.interpolation`: `CONSTANT, LINEAR, BEZIER, SINE, QUAD, CUBIC, QUART, QUINT, EXPO,
     CIRC, BACK, BOUNCE, ELASTIC` (`SINE` through `ELASTIC` are the easing-equation modes).
     `BEZIER`, `BACK`, `ELASTIC` set + read back live **[VERIFIED 5.1.1]**.
   - `kp.easing`: `AUTO, EASE_IN, EASE_OUT, EASE_IN_OUT` (`EASE_OUT` verified live).
   - `kp.handle_left_type / handle_right_type`: `FREE, ALIGNED, VECTOR, AUTO, AUTO_CLAMPED`
     (`AUTO_CLAMPED` verified live); `kp.handle_left/right` are editable 2D points.
   - `kp.back` (BACK overshoot size), `kp.amplitude` + `kp.period` (ELASTIC) — set live.
   - `kp.type`: `KEYFRAME, BREAKDOWN, MOVING_HOLD, EXTREME, JITTER` — the agent can tag its
     own pose intent and audit against it later **[VERIFIED 5.1.1]**.
   - Interpolation set on a key governs the segment from that key to the next one [docs].
5. `fcu.evaluate(frame)` samples the curve; `fcu.update()` re-sorts and recalcs handles
   after bulk edits; `fcu.extrapolation` in `{CONSTANT, LINEAR}`; cyclic motion = add
   `fcu.modifiers.new(type='CYCLES')` with `mode_before/mode_after` in
   `{NONE, REPEAT, REPEAT_OFFSET, MIRROR}` — all **[VERIFIED 5.1.1]**
   (`bpy.types.FCurve`, `bpy.types.FModifierCycles`).
6. `fcurve.keyframe_points.insert(frame, value, options={'FAST'}, keyframe_type=...)` for
   bulk insertion; options `REPLACE | NEEDED | FAST` [docs: `bpy.types.FCurveKeyframePoints`].
7. New keys in the test instance defaulted to `BEZIER` + `AUTO_CLAMPED` **[VERIFIED
   5.1.1]**, but that default is a user preference — always set `kp.interpolation`
   explicitly instead of relying on it.

## The 12 principles in f-curve terms

Each of the twelve principles of animation, translated to graph-editor mechanics.

### 1. Timing (& spacing)
- Theory: frame count = speed and mood; spacing (value distance per frame) = weight.
- F-curves: timing = X positions of keys; spacing = the curve slope between them. Steep =
  fast, flat = slow/held. Constant slope = constant (mechanical) velocity.
- Programmatic: place keys per the timing table below; control spacing by handle shaping,
  never by adding evenly-spaced in-between keys.

### 2. Slow in & slow out (ease)
- Theory: bodies accelerate and decelerate; more frames near the extremes.
- F-curves: S-shaped segments; flat tangents at extremes, steepest mid-segment.
- Programmatic: `kp.interpolation='BEZIER'` with `AUTO_CLAMPED` handles gives baseline
  ease-in/out; asymmetric ease via the easing modes (`SINE`..`EXPO`) + `kp.easing='EASE_IN'`
  (accelerating exit) or `'EASE_OUT'` (decelerating arrival). Sharp mechanical stops:
  `handle_type='VECTOR'` at the contact key.

### 3. Arcs
- Theory: organic motion travels on curved world-space paths; straight lines read robotic.
- F-curves: an arc is not visible in one channel — it emerges from phase-shifted sine-like
  curves across X/Y/Z. All channels peaking on the same frame = straight-line path.
- Programmatic: give the perpendicular axis its own key mid-travel (a breakdown that
  offsets the path); verify with motion paths:
  `bpy.ops.object.paths_calculate(display_type='RANGE', range='SCENE')` then read
  `obj.motion_path.points[i].co` (24 world-space points read back live) **[VERIFIED
  5.1.1]** (`bpy.types.MotionPath`).

### 4. Anticipation
- Theory: telegraph an action with a small counter-move (crouch before jump, pull-back
  before punch).
- F-curves: a dip below the start value just before the main rise — the curve leaves in
  the opposite direction first.
- Programmatic: insert an anticipation key 2-8f before the action at roughly minus 10-20%
  of the travel (rule of thumb). Alternatively
  `kp.interpolation='BACK'` with `kp.easing='EASE_IN'` on the pre-action key generates the
  counter-dip procedurally [docs: BACK = "cubic easing with overshoot and settle"].

### 5. Follow-through & overlapping action
- Theory: appendages (hair, cloth, tail, loose limbs) lag the body and keep moving after
  it stops, settling later.
- F-curves: the child channel is the parent curve shifted 1-4f right, with an extra decay
  oscillation after the parent flattens.
- Programmatic: copy the leader's key layout to the follower shifted +1..+4f (`kp.co.x +=
  offset` on the follower, then `fcu.update()`), reduce amplitude slightly, and end with
  an `ELASTIC`/manual settle: offset the keyframes of the parts that overlap.

### 6. Squash & stretch
- Theory: deformation communicates mass/softness; volume must stay constant.
- F-curves: scale channels spike at contacts — stretch axis up while squash axes dip
  (anti-correlated scale curves), sharp V at the contact frame.
- Programmatic: key `scale` with `VECTOR` handles at impact, `BEZIER` out; keep
  `sx*sy*sz ~= 1` for volume conservation (rule of thumb).
  Stretch along the velocity vector during fast travel frames.

### 7. Secondary action
- Theory: a supporting motion that enriches the main one without stealing focus (a walk +
  a head bob + a hand gesture).
- F-curves: extra low-amplitude channels keyed on different frames from the primary; if
  removed, the main read survives.
- Programmatic: author after the primary reads well; amplitude a fraction of the primary;
  audit rule: secondary channels must not add keys at the primary's story frames.

### 8. Moving holds (the anti-freeze)
- Theory: a held pose must still breathe — a complete static hold reads dead in 3D.
- F-curves: instead of two identical keys (flat segment), the hold drifts 1-5% (start at 1-2%) of the
  previous travel in the direction of the arriving momentum, with body parts settling at
  different frames (hips first, head last).
- Programmatic: never duplicate a pose key to hold it; add a second key with a small drift
  continuing the arrival direction, and tag both `kp.type='MOVING_HOLD'` **[VERIFIED
  5.1.1]** so audits can distinguish intentional holds.

### 9. Straight-ahead vs pose-to-pose
- Theory: pose-to-pose (keys first, in-betweens later) gives control of proportions,
  timing and story read; straight-ahead gives flow but drifts off-model and reads floaty.
  Production work combines both.
- F-curves: pose-to-pose = a sparse set of story keys on all channels, refined by
  breakdowns; straight-ahead = dense sequential keys (what naive scripts produce).
- Programmatic: the agent workflow — block poses with `CONSTANT` interpolation, convert to
  spline later (see ## Iteration structure). A script that computes per-frame positions
  and keys every frame is doing straight-ahead with extra steps; avoid.

### 10. Exaggeration
- Theory: push the essence of an action past literal reality so it reads at 24fps.
- F-curves: higher amplitude extremes, deeper anticipation dips, larger overshoots.
- Programmatic: after a literal pass, scale extreme key values ~10-30% away from the
  neutral pose (rule of thumb); a broken/hyperextended pose is acceptable if visible only
  1-2 frames.

### 11. Staging (+ solid drawing -> solid posing)
- Theory: present one idea at a time, readable in silhouette (the silhouette test). Solid
  drawing in CG = balanced poses with weight over the base of support.
- F-curves: staging is mostly pose + camera, not curves; its curve trace is separation in
  time — major actions do not overlap each other's story frames.
- Programmatic: schedule beats sequentially with holds between; audit renders in
  silhouette (see ## Review methodology) for readability and balance.

### 12. Appeal
- Theory: asymmetry, clear shapes, no "twinning" (mirrored limb poses read boring).
- F-curves: left/right channel pairs should not be exact mirrors (identical values,
  opposite signs) nor keyed on identical frames.
- Programmatic: when posing limb pairs, perturb one side (offset a few degrees, shift keys
  1-3f); audit check #6 below detects twinning.

## Robotic-animation fixes

What makes scripted animation read robotic, the curve-level signature, and the fix.
The detection mechanics were verified live (see the audit section).

| # | Robotic tell | F-curve signature | Fix (programmatic) |
|---|---|---|---|
| 1 | Uniform linear interpolation | straight segments everywhere; velocity steps at keys | `kp.interpolation='BEZIER'` + shaped handles, or the easing modes; reserve `LINEAR` for machines/conveyors |
| 2 | All channels keyed on identical frames | one column of keys per pose across every channel, forever | after splining, offset follower channels +1..+3f (lead with hips/root, delay extremities); keep unison only in blocking |
| 3 | Perfect symmetry / twinning | L/R curves are exact mirrors, same frames | perturb one side's values ~2-5% and shift its keys 1-3f (rule of thumb) |
| 4 | Frozen holds | two identical keys, dead-flat segment >6f | moving hold: drift key 1-5% of prior travel, stagger per-part settle frames; tag `MOVING_HOLD` |
| 5 | No anticipation | curve leaves directly toward the target | insert counter-dip key, or `BACK`+`EASE_IN` on the departure key |
| 6 | No overshoot/settle | curve lands exactly on final value, first try | `BACK`+`EASE_OUT` on arrival (live sample: 2->4 segment peaked at 4.175 mid-segment before settling **[VERIFIED 5.1.1]**), or manual overshoot key +5-10% then settle |
| 7 | Identical easing everywhere | every segment same S-shape | vary ease per body part and per beat: sharp `VECTOR` contacts, soft `SINE` drifts, `EXPO` snaps |
| 8 | Broken/jagged arcs | perpendicular channels flat or peaking in lockstep | breakdown keys on the perpendicular axis; verify via `motion_path.points` curvature |
| 9 | Metronomic repetition in cycles | `CYCLES` modifier with zero variation | vary repeated cycles: tiny per-cycle amplitude/timing jitter, or layer a weak `NOISE` modifier |
| 10 | Everything starts/stops together | shot-wide key columns at action boundaries | stagger action starts; let one part arrive, then the next (overlap) |

Noise as seasoning, not fix: `fcu.modifiers.new(type='NOISE')` with `scale` (time
scaling), `strength` (amplitude), `phase` (seed), `depth` — created and read back live
**[VERIFIED 5.1.1]** (`bpy.types.FModifierNoise`).
Good for idle micro-motion and camera; it does not repair bad timing/eases.

## Timing reference table

All values at 24 fps unless noted. These are professional rules of thumb, not physics.
Convert: frames = seconds * fps (`scene.render.fps`).

| Action | Frames @24fps | Notes |
|---|---|---|
| Walk, normal pace | 12 f per step (24 f full cycle) | most people walk on 12s, ~2 steps/s |
| Walk, brisk "natural" | 12 f per step | a 24 f cycle reads brisk and business-like |
| Walk, strolling | 16 f per step (32 f cycle) | leisurely |
| Run | 4-8 f per step (8-16 f cycle) | 8 f cycle = very fast run (4 f/step); 12-16 f cycles typical runs |
| Fast punch | anticipation longest; strike travel 2-4 f; hit-stop pause 2-6 f; recovery slow | even timing on every frame is the #1 mistake: slow antic, fast action, slow recovery |
| Head turn | 10-14 f | eyes lead, head lags a touch |
| Quick look / eye dart | 4-6 f + 1-2 f hold | |
| Hand pick-up | 3-5 f contact + two-stage lift | |
| Jump (standing) | ~12-18 f total: crouch + takeoff + air + landing | crouch/landing get more frames, takeoff/fall fewer — that contrast sells power vs floaty; the arc bunches at the apex |
| Settle after a stop | ~10-20+ f for heavy objects / emotional holds | arrival -> overshoot -> settle, each stage smaller and shorter |
| Hold between beats | >= 8-12 f as a moving hold, never frozen | |

Weight through timing: heavy = slower acceleration (shallower initial slope), more
anticipation frames, broader stance, longer settle, fewer/lower bounces; light = snappy
slopes, minimal anticipation, quick high-frequency settle. Same poses + different
spacing = different mass.

## Programmatic self-audit checks

Reading f-curves via bpy to detect the robotic tells. Checks 1-3 were executed live
against a deliberately robotic rig (pure-LINEAR, lockstep-keyed, mirrored pair) and a
hand-shaped organic curve; measured separation was total (see calibration). Thresholds
are proposed starting points (rule of thumb), to be tuned per shot type.

Reference implementation `[EXACT]` — ran on 5.1.1, uses the 5.x
`get_fcurves()` from the API ground rules (on 4.x use the `get_fcurves` in `blender-bpy-physics.md`):

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

Calibration from the live run **[VERIFIED 5.1.1]**: robotic rig -> `linear_ratio=1.0`,
`unison_ratio=1.0`, `overshoot_ratio=0.0`, exact mirror detected; organic curve ->
`linear_ratio=0.0`, `unison_ratio=0.0` (channels staggered 3f), `overshoot_ratio=0.25`
(the BACK/ELASTIC segments overshoot as designed).

Proposed audit battery (thresholds = proposed defaults, flag do not auto-fail):

1. **Linear-interpolation ratio** `[EXACT above]`. Organic character motion: flag if
   >0.3; 1.0 = certainly robotic. Exception: mechanical objects, constant-speed props.
2. **Keyframe unison ratio** `[EXACT above]`. Stage-dependent: ~1.0 is correct during
   blocking (poses keyed on all channels); after the overlap/polish pass flag if still
   >0.8. This is the single strongest "scripted look" tell.
3. **Zero-overshoot** `[EXACT above]`. If `overshoot_ratio == 0` across every arriving
   action and no manual settle keys exist, motion has no follow-through; expect >0 on
   arrivals. (Machines legitimately 0.)
4. **Velocity discontinuity at keys** `[DESIGN]`: sample `v_in = f(t)-f(t-eps)`,
   `v_out = f(t+eps)-f(t)` via `fcu.evaluate`; flag |v_out - v_in| spikes above ~3x the
   channel's median step where the key is not tagged `EXTREME`/contact — un-motivated
   pops.
5. **Frozen-hold detector** `[DESIGN]`: consecutive keys with identical values spanning
   >6 f and no `MOVING_HOLD` tag between them -> dead hold; propose drift keys.
6. **Twinning / perfect symmetry** `[DESIGN]`: for L/R channel pairs (name-matched, e.g.
   `.L`/`.R` bones), flag if key frames identical and values correlate >0.999 (sign
   allowing) — verified detectable via exact-mirror comparison in the live run.
7. **Arc smoothness / jitter** `[DESIGN]`: `bpy.ops.object.paths_calculate` then second
   difference over `motion_path.points[i].co` (world space) **[mechanism VERIFIED
   5.1.1]**; high-frequency sign flips of the second derivative = jitter; near-zero
   curvature on a limb tip during broad gestures = straight-line (broken arc). Jerk (rate
   of change of acceleration) is the standard smoothness metric in mocap cleanup.
8. **Foot slide** `[DESIGN]`: during contact frames (foot world height below threshold),
   horizontal displacement of the foot bone should be ~0; sum of horizontal deltas while
   in contact = slide metric. Sample world positions via
   `scene.frame_set(f)` + `obj.evaluated_get(depsgraph).matrix_world` [docs: `bpy.types.Depsgraph`].
9. **Intent-tag consistency** `[DESIGN]`: the agent tags keys at authoring time
   (`kp.type` = `EXTREME`/`BREAKDOWN`/`MOVING_HOLD` **[VERIFIED 5.1.1]**); audit that
   every arriving EXTREME has ease-out or overshoot, every MOVING_HOLD pair actually
   drifts, breakdowns sit off the halfway value (favoring one side).

## Preview/playblast recipes

The agent's substitute for scrubbing. Two tiers: golden-pose stills (cheap, first) and
OpenGL playblast sequences (motion check). All recipes ran from script through the MCP
bridge with no viewport dependency. That is the live (GUI) session: in `blender -b` there
is no OpenGL context and `render.opengl` fails, so render previews there with
`bpy.ops.render.render` on Workbench or EEVEE instead (hard rule 4 in `blender-mcp-workflow.md`).

### Golden-pose stills (cheapest review) `[EXACT]`

```python
import bpy
scene = bpy.context.scene
scene.render.resolution_percentage = 25          # 1920x1080 -> 480x270
scene.render.image_settings.file_format = 'PNG'
for f in [1, 12, 24]:                            # contacts/extremes/story beats
    scene.frame_set(f)
    scene.render.filepath = f"//review/pose_{f:04d}.png"
    bpy.ops.render.opengl(write_still=True, animation=False, view_context=False)
```

Verified live: wrote a 75 KB PNG at 25% resolution, effectively instant **[VERIFIED
5.1.1]**. `view_context=False` renders from the scene camera with scene settings instead
of whatever viewport happens to exist — mandatory for an agent [docs signature:
`bpy.ops.render.opengl(animation=False, render_keyed_only=False, sequencer=False,
write_still=False, view_context=True)`].

### OpenGL playblast (motion review) `[EXACT]`

```python
scene.frame_start, scene.frame_end = 1, 48
scene.render.resolution_percentage = 25
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = "//review/blast_"
bpy.ops.render.opengl(animation=True, view_context=False)   # writes blast_0001.png...
```

Verified live: 5-frame sequence written from script in the live session **[VERIFIED 5.1.1]**. `render_keyed_only
=True` renders only frames where selected objects have keys [docs, not executed] — a
built-in "contact sheet of my poses" for blocking review.

### Video (MP4) output: probe first, it can be absent `[DESIGN]`

On Blender 5.1.1, `scene.render.image_settings.file_format = 'FFMPEG'` is rejected while
`image_settings.media_type` is an image type: the enum then contains only image formats
(`AVIF, JPEG, OPEN_EXR, PNG, WEBP, BMP, CINEON, DPX, IRIS, JPEG2000, HDR, TARGA, TARGA_RAW,
TIFF`) **[VERIFIED 5.1.1]**. Set `media_type = 'VIDEO'` first; only then is `'FFMPEG'` a valid
`file_format` (hard rule 3 in `blender-mcp-workflow.md`). FFmpeg support is also a build option
(`bpy.app.build_options.codec_ffmpeg`), so never assume MP4 output exists. Static enum
introspection reports no `'FFMPEG'` on 5.x until `media_type` is set, so set it (when the
property exists) and probe by assignment inside try/except. Fall back to a PNG sequence when
the assignment fails.

```python
def enable_video(scene):                      # the ffmpeg settings below were not executed
    r = scene.render
    ims = r.image_settings
    try:
        if hasattr(ims, "media_type"):        # 5.x gate
            ims.media_type = 'VIDEO'
        ims.file_format = 'FFMPEG'
    except TypeError:
        return False                          # no FFmpeg here: use a PNG sequence
    r.ffmpeg.format = 'MPEG4'                 # container; enum incl. MPEG4, QUICKTIME, MKV, WEBM
    r.ffmpeg.codec = 'H264'                   # enum incl. H264, H265, AV1, WEBM, PRORES...
    r.ffmpeg.constant_rate_factor = 'MEDIUM'  # NONE|LOSSLESS|PERC_LOSSLESS|HIGH|MEDIUM|LOW...
    return True
```

Snapshot `media_type` and `file_format` before the probe and restore them afterwards (hard
rule 8 in `blender-mcp-workflow.md`). The ffmpeg enums are those of `bpy.types.FFmpegSettings` [docs].
PNG sequences are the safe default; stills are individually inspectable by the agent
anyway, which suits frame-by-frame review better than a video file it cannot watch.

### Engine + speed knobs

- Engine identifiers are version-dependent. Live 5.1.1 accepts `BLENDER_EEVEE`,
  `BLENDER_WORKBENCH`, `CYCLES`; `BLENDER_EEVEE_NEXT` is rejected **[VERIFIED 5.1.1]**.
  In 4.2-4.5 EEVEE's id was `BLENDER_EEVEE_NEXT`; it was renamed back for 5.0. Gotcha verified
  live: static enum introspection listed only the current engine; probing by try/except
  assignment is the reliable detection **[VERIFIED 5.1.1]**.
- `bpy.ops.render.opengl` ignores the heavy engine — it draws viewport-style (solid
  shading), which is exactly the playblast look; use it for all motion checks. Full
  `bpy.ops.render.render(animation=True)` [docs] with EEVEE only for lighting-dependent
  review; Workbench (`BLENDER_WORKBENCH`) for fastest full-render silhouettes.
- `scene.render.resolution_percentage = 25..50` for review passes (halving resolution is
  the standard first speed lever).
- `scene.frame_step = N` renders every Nth frame [docs: bpy.types.Scene] — playblast "on
  twos/fours" for long shots; or loop `frame_set` over a hand-picked frame list (the
  golden-pose recipe), which is cheaper still.
- No universal render-time numbers are quoted here on purpose: they depend on GPU/scene;
  the verified datapoint is that 480x270 OpenGL stills are subsecond-cheap, so reviewing
  10-20 stills per iteration is affordable.

## Review methodology for an agent

An agent cannot scrub, so it substitutes (a) targeted stills, (b) short low-res
playblasts, (c) numeric curve audits. Each review round should combine all three — stills
catch pose problems, numbers catch curve problems, playblasts catch timing problems.

### Which frames to render

Priority order:

1. **Story/key poses** — the poses that carry the idea; if these do not read, nothing
   else matters.
2. **Contact frames** — foot strikes, hand-object touches, impacts. Errors here
   (penetration, floating, slide) are the most visible realism killers.
3. **Extremes** — direction changes (top of jump, end of wind-up, deepest anticipation).
4. **Breakdowns/passing positions** — mid-motion frames that define the arc; render one
   per major transition (the turning point of a motion path, often the fastest moment).
5. **Hold midpoints** — one frame mid-hold to confirm the moving hold is alive.
6. **The frame after an impact** (+1/+2) — where overshoot/settle should be visible
   (an impact lives in the frame it connects and the first two frames after).

If keys were tagged at authoring time (`kp.type`), the frame list derives automatically:
render all `EXTREME` + contacts, plus `render_keyed_only=True` playblast for the full
pose contact-sheet.

### What to look for in stills

- **Silhouette test** (staging): is the action readable from shape alone? A flat-lit or
  Workbench render approximates this.
- **Line of action + balance**: one clear curve through the pose; weight over the base of
  support.
- **Twinning**: limbs mirrored?
- **Contacts**: feet on the ground plane, no interpenetration, hand actually wraps the
  prop.
- **Spacing between consecutive stills**: compare pose deltas across the golden frames —
  even deltas = even (robotic) timing; the deltas should cluster (small near holds and
  extremes, large mid-action).

### What only motion shows

Playblast (even 25%, on twos) is required to judge: timing feel (too even? floaty?),
pops (velocity discontinuities), arc breaks in perspective, overlap reading as intended,
moving holds alive vs twitchy. Numeric checks 4-8 pre-filter most of these; render the
playblast after numbers pass to confirm the feel.

### Comparing against reference descriptions

Without eyes on footage, reference = a written beat sheet: decompose the reference action
into beats with frame budgets from the timing table (e.g. "punch: 8f antic, 3f strike,
4f hit-stop overlap, 12f recovery"), then diff the authored key layout against the
budget. Deviations >30% (rule of thumb) either intentional (style) or flagged.

## Iteration structure

Block first, then spline, then polish — pose-to-pose is the professional default because
it locks story, proportions and timing before motion exists, and it is quicker to iterate
and easier to revise.
Straight-ahead output risks floaty, unfocused motion and drifting proportions — which is
exactly what naive per-frame scripted animation produces.

| Stage | Interpolation | What exists | Gate before next stage |
|---|---|---|---|
| 1. Layout/plan | none | beat sheet with frame budgets (timing table) | budgets sum to shot length; beats do not overlap (staging) |
| 2. Blocking | `CONSTANT` on every key | story poses + contacts, all channels keyed per pose (unison correct here) | golden stills: silhouette, balance, contacts, spacing deltas; story reads |
| 3. Blocking plus | still `CONSTANT` | breakdowns, anticipations, key holds added as poses | stills at breakdowns: arcs plausible, antic present |
| 4. Spline | convert to `BEZIER` (+ easing modes where wanted) | eases shaped; contacts sharpened (`VECTOR`); overshoots (`BACK`) | audit battery: linear ratio, overshoot, velocity pops; short playblast |
| 5. Overlap/offset | — | channels staggered 1-3f, follow-through keys, moving holds replace freezes | unison ratio drops below threshold; holds drift; playblast |
| 6. Polish | — | arc cleanup (motion-path metric), micro-drift, secondary action, noise seasoning | full audit + full-length playblast; zero unexplained flags |

Programmatic stage 2->4 conversion is trivial: flip `kp.interpolation` from `'CONSTANT'`
to `'BEZIER'` across all keys (the classic stepped->spline switch). Stay in stepped
longer, for fewer surprises with timing when going to spline: do not spline
until the still-based review passes, because stills of stepped blocking are the cheapest
possible review unit for an agent.

Iteration counts: the stages have approval gates (blocking is approved before refining), not
a universal pass count. Practical expectation: at least one review-fix cycle
per stage, so a believable shot passes through at least 2 to 4 review rounds; treat a shot
that "passes" on round 1 as un-audited, not as finished (rule of thumb).

## Camera feel

- **Motivated moves**: the camera moves because the subject/story moves — follow the
  action, reveal, or reframe; unmotivated drift reads amateur. For an agent: bind camera
  beats to subject beats — start the move 2-4f after the subject starts (reaction), settle
  slightly after the subject settles.
- **Lead room**: frame ahead of the motion — subject off-center with space in its travel
  direction, proportional to speed. A tracking camera should lead the subject, not center it.
- **Ease everything**: camera transforms are f-curves like any other — linear pans are
  the same robotic tell (#1). Slow in/out on every move; simple, motivated moves beat
  elaborate ones.
- **Imperfection, layered**: single-frequency noise looks like "floating in jelly";
  believable handheld = several noise layers at different frequencies/amplitudes.
  Implementation: two
  `fcu.modifiers.new(type='NOISE')` on camera rotation channels **[mechanism VERIFIED
  5.1.1]** — one slow sway (`scale` large, tiny `strength`), one fine tremor (`scale`
  small, even tinier `strength`); rotation strengths on the order of 0.002-0.01 rad
  (starting values, rule of thumb). Keep base keys clean by putting noise on
  `delta_rotation_euler` channels instead of the main ones (`delta_*` props are standard
  `bpy.types.Object` members [docs]).
- **Ease the shake itself in/out**: shake snapping on at full strength on frame 1 reads
  as a glitch; use the F-modifier restricted frame range with
  `blend_in`/`blend_out` [docs: `bpy.types.FModifier`].
- **Do not shake a tripod shot**: imperfection only where the fiction implies a human
  operator; static/mechanical shots stay clean (motivation principle again).
