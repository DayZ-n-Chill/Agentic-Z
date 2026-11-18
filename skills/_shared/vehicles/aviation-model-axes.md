# Model axes: py3d against the engine

Why an offset measured from a `.p3d` with py3d can land on the wrong end of the aircraft, and the one runtime probe that settles it. Open it before feeding any model derived coordinate (an eye point, a gimbal centre, a muzzle) to `ModelToWorld`.

The engine facts cite `P:\`. The py3d result was measured in game on two helicopter airframes and is not yet checked on `P:\`.

## What happens

Geometry read from an MLOD `.p3d` with py3d (`scripts/tools/py3d/`, notes in `skills/_shared/py3d-mlod-notes.md`) is consistent with itself and, on the measured airframes, **mirrored on Z** against the frame `ModelToWorld` uses. Feeding a py3d offset straight into the engine puts the point at `-Z` of where it belongs: 5.6 m off on an airframe the size of an OH-1, which put an eye point on the tail boom instead of the sight.

Every offline cross check agreed with itself, which is what made it expensive. In py3d coordinates the search light sat at Z -5.933, the landing light beam ran from -5.885 to -6.626, the canopy from -5.44 to -3.03, the tail beacon at +5.358 and `tail_rotor_axis` at +4.597, and a second airframe showed the same pattern. A confident, fully cited "the nose is at negative Z" came out of that, and it was wrong.

## The engine decides

Engine forward is `+Z`: yaw 0 points along +Z. The vanilla doc example for `AnglesToVector` at `P:\scripts\1_core\proto\enconvert.c:380-389` turns yaw 45 into `<0.707107,0,0.707107>`. In game, `GetDirection()` (`P:\scripts\3_game\entities\object.c:314`) returned `<-0.005, -0.019, +0.9998>` with the aircraft pointing where the pilot calls forward, and `ModelToWorld("0 0 5")` landed 5 m toward the nose.

## Rules

1. Never hand a py3d derived offset to `ModelToWorld` without one runtime probe first. Print `GetDirection()`, `ModelToWorld("0 0 5")` and `GetMemoryPointPos(<a known landmark>)` (`P:\scripts\3_game\entities\object.c:452`), and compare the memory point's engine coordinates against the same point read by py3d. If the Z signs disagree, negate Z on everything derived from the file: eye points, gimbal centres, axis fits, all of it.
2. Look for a constant in the project that already crossed the boundary before deriving a new one. A HUD constant such as `PIPPER_NOSE_MS = "0 0.383 +5.826"` that already draws in the right place is in the engine frame, nose at positive Z, and settles the sign without a new measurement.
3. Geometric self consistency is not evidence that the frame is right. Two independent `.p3d` readings that agree show that the reader is consistent, not that it matches the engine.
