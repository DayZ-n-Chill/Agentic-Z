# Believable motion in F-curve terms

How the twelve animation principles show up in F-curves and how a script applies each one in Blender, what makes scripted motion read robotic and how to fix it, frame counts for common actions, and how a camera should move. The self-audit, previews and review rounds are in `blender-review-loop.md`.

This is animation craft and Blender behaviour, run against Blender 5.1 or taken from the API reference, so nothing here cites `P:\`. The DayZ side is in `blender-txa-export.md`. Frame counts here are at 24 fps; DayZ clips run at 30 fps, so convert before using them for a DayZ clip. Counts and percentages are rules of thumb.

## The principles as curves

| Principle | In the curves | How a script applies it |
|---|---|---|
| Timing and spacing | Key positions in time are timing; the slope between them is spacing. Steep is fast, flat is slow, a constant slope is mechanical. | Place keys from the timing table; shape spacing with handles, never with evenly spaced in-between keys. |
| Slow in and slow out | S-shaped segments, flat at the extremes, steepest in the middle. | `BEZIER` with `AUTO_CLAMPED` handles for the basic ease; the easing modes (`SINE` to `EXPO`) with `EASE_IN` for a speeding exit or `EASE_OUT` for a slowing arrival; `VECTOR` handles for a hard mechanical stop. |
| Arcs | Not visible in one channel: an arc comes from phase shifted curves across X, Y and Z. All channels peaking together is a straight line. | Give the perpendicular axis its own key mid travel, then check the motion path (`blender-bpy-objects-camera.md`, "Reading motion paths back"). |
| Anticipation | The curve dips the other way before the main move. | A key 2 to 8 frames before the action at about 10 to 20 percent of the travel the other way, or `BACK` with `EASE_IN` on the key before the action. |
| Follow-through and overlap | A follower is the leader's curve shifted 1 to 4 frames later, with a fading wobble after the leader stops. | Copy the leader's keys to the follower shifted 1 to 4 frames (`kp.co.x += offset`, then `fcu.update()`), lower the amplitude slightly, and end on an `ELASTIC` or hand keyed settle. |
| Squash and stretch | Scale curves spike at contact, the stretch axis up while the others dip, with a sharp V at the contact frame. | Key `scale` with `VECTOR` handles at impact and `BEZIER` after; keep `sx*sy*sz` near 1 to keep volume; stretch along the travel on fast frames. |
| Secondary action | Extra small channels keyed on other frames than the main action; remove them and the main read survives. | Add after the main action reads well, at a fraction of its amplitude, with no keys on the main action's story frames. |
| Moving holds | Instead of two equal keys, the hold drifts 1 to 5 percent (start at 1 to 2) of the last travel in the arriving direction, parts settling at different frames (hips first, head last). | Never duplicate a pose key to hold it; key a small drift and tag both keys `MOVING_HOLD`. |
| Straight ahead and pose to pose | Pose to pose is sparse story keys on every channel refined by breakdowns; straight ahead is dense keys on every frame. | Block with `CONSTANT` keys and spline later (`blender-review-loop.md`, "Working in stages"). A script that keys every frame from computed positions is straight ahead; avoid it. |
| Exaggeration | Bigger extremes, deeper anticipation, larger overshoot. | After a literal pass, push extreme values 10 to 30 percent away from neutral. A broken or overextended pose is fine for one or two frames. |
| Staging and solid posing | Mostly pose and camera; in the curves, big actions do not share story frames. | Schedule beats one after another with holds between, and review silhouettes for readability and balance. |
| Appeal | Left and right channels are not exact mirrors and are not keyed on the same frames. | Offset one side by a few degrees and shift its keys 1 to 3 frames. |

## Fixes for robotic motion

| Sign | In the curves | Fix |
|---|---|---|
| Linear everywhere | Straight segments; speed jumps at keys. | `BEZIER` with shaped handles, or the easing modes. Keep `LINEAR` for machines and conveyors. |
| Every channel keyed on the same frames | One column of keys per pose across all channels. | After splining, shift follower channels 1 to 3 frames, leading with the hips and root and delaying the extremities. Unison is right only while blocking. |
| Perfect symmetry | Left and right curves mirror exactly on the same frames. | Change one side's values 2 to 5 percent and shift its keys 1 to 3 frames. |
| Frozen holds | Two equal keys, a flat segment longer than 6 frames. | A moving hold drifting 1 to 5 percent of the last travel, parts settling at different frames, tagged `MOVING_HOLD`. |
| No anticipation | The curve leaves straight toward the target. | A counter dip key, or `BACK` with `EASE_IN` on the departing key. |
| No overshoot or settle | The curve lands exactly on the final value. | `BACK` with `EASE_OUT` on the arrival (a segment from 2 to 4 peaked at 4.175 before settling), or a hand keyed overshoot of 5 to 10 percent then the settle. |
| The same ease everywhere | Every segment the same S. | Vary by body part and beat: sharp `VECTOR` contacts, soft `SINE` drifts, `EXPO` snaps. |
| Broken arcs | Perpendicular channels flat, or peaking together. | Breakdown keys on the perpendicular axis; check the motion path curvature. |
| Metronome cycles | A Cycles modifier with no variation. | Small amplitude and timing changes per cycle, or a weak Noise modifier on top. |
| Everything starts and stops together | Key columns across the shot at action boundaries. | Stagger starts; let one part arrive, then the next. |

Noise (`fcu.modifiers.new(type='NOISE')`, `blender-bpy-fcurve-modifiers.md`) seasons idle motion and cameras; it does not repair bad timing or easing.

## Frame counts at 24 fps

Frames are seconds times `scene.render.fps`.

| Action | Frames | Notes |
|---|---|---|
| Walk, normal or brisk | 12 per step, 24 per cycle | Most people walk about two steps a second; a 24 frame cycle reads brisk. |
| Walk, strolling | 16 per step, 32 per cycle | Leisurely. |
| Run | 4 to 8 per step, 8 to 16 per cycle | An 8 frame cycle is a very fast run; 12 to 16 is typical. |
| Fast punch | Strike 2 to 4, impact pause 2 to 6 | Longest on the anticipation, slow recovery. Even timing on every frame is the commonest mistake. |
| Head turn | 10 to 14 | The eyes lead, the head lags a little. |
| Quick look | 4 to 6, then a 1 to 2 frame hold | |
| Hand pick up | 3 to 5 on contact, then a two stage lift | |
| Standing jump | About 12 to 18 in all | Crouch and landing get more frames, takeoff and fall fewer; the arc bunches at the top. |
| Settle after a stop | About 10 to 20 or more for heavy objects or emotional holds | Arrival, overshoot, settle, each smaller and shorter. |
| Hold between beats | 8 to 12 or more | Always as a moving hold. |

Weight comes from timing. Heavy is slower acceleration, more anticipation, a broad stance, a long settle and few, low bounces; light is snappy slopes, little anticipation and a quick fine settle. The same poses with different spacing read as different masses.

## How the camera should move

- Move with a reason: follow the action, reveal, or reframe. Start a camera move 2 to 4 frames after the subject starts and settle slightly after the subject settles.
- Leave lead room: frame the subject off centre with space ahead of its travel, more for faster motion. A tracking camera leads, not centres.
- Ease every move. A linear pan is the same robotic sign as linear keys.
- Layer the handheld feel. One noise frequency floats like jelly; use two Noise modifiers on the rotation curves, one slow sway (large `scale`, tiny `strength`) and one fine tremor (small `scale`, smaller `strength`), with rotation strengths around 0.002 to 0.01 radians. Put them on `delta_rotation_euler` so the base keys stay clean.
- Ease the shake in and out with the modifier's restricted frame range and `blend_in` and `blend_out`; shake that starts at full strength reads as a glitch.
- Never shake a tripod shot. Shake only where the story implies a person holding the camera.
