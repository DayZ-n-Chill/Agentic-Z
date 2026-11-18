# Model axes against the engine

Why an offset measured from a `.p3d` with py3d can land on the wrong end of an aircraft, and the runtime check that settles it. Open it before you pass any coordinate taken from a model (an eye point, a gimbal centre, a muzzle) to `ModelToWorld`.

The engine facts cite `P:\`. The py3d result was measured in game on two helicopter airframes and is not checked on `P:\`.

## The mirror

Geometry read from an MLOD `.p3d` with py3d (`scripts/tools/py3d/`, notes in `_shared/py3d-mlod-notes.md`) agrees with itself and, on both measured airframes, is mirrored on Z against the frame `ModelToWorld` uses. A py3d offset passed straight to the engine lands at `-Z` of where it belongs: 5.6 m off on an airframe the size of an OH-1, which put an eye point on the tail boom instead of the sight.

Every offline check agreed with every other, which is why it is easy to miss. In py3d coordinates the search light sat at Z -5.933, the landing light beam ran from -5.885 to -6.626, the canopy from -5.44 to -3.03, the tail beacon at +5.358 and `tail_rotor_axis` at +4.597, and the second airframe matched. All of it pointed to "the nose is at negative Z", and that was wrong.

## The engine decides

Engine forward is `+Z`: yaw 0 points along `+Z`. The vanilla example for `AnglesToVector` turns yaw 45 into `<0.707107,0,0.707107>` (`P:\scripts\1_core\proto\enconvert.c:359` to `:368`). In game, `GetDirection()` (`P:\scripts\3_game\entities\object.c:314`) returned `<-0.005, -0.019, +0.9998>` with the aircraft pointing where the pilot calls forward, and `ModelToWorld("0 0 5")` landed 5 m towards the nose.

## Rules

1. Never pass a py3d offset to `ModelToWorld` without one runtime check first. Print `GetDirection()`, `ModelToWorld("0 0 5")` and `GetMemoryPointPos(<a known landmark>)` (`object.c:452`), and compare the memory point's engine position with the same point read by py3d. If the Z signs disagree, negate Z on everything taken from the file: eye points, gimbal centres, fitted axes, all of it.
2. Look first for a value in the project that already crossed over. A HUD constant such as `PIPPER_NOSE_MS = "0 0.383 +5.826"` that already draws in the right place is in the engine frame, nose at positive Z, and settles the sign with no new measurement.
3. A model that agrees with itself proves nothing about the frame. Two readings of a `.p3d` that match show the reader is consistent, not that it matches the engine.
