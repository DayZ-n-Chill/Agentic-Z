# Reading numbers from a test session

How to read numbers out of a DayZ test session without fooling yourself: aligning client and server series, what the shape of a divergence means, and three statistical traps (a fitted clock offset that hides the defect, a range that measures how long you watched, a defect rate averaged over deliberately broken variants). The probe rules that come first are in `debug-protocol.md`.

This is method plus results measured on a helicopter mod's test runs; none of it can be read in a vanilla file, so it is not checked on `P:\`. The one script call the probes rely on is: `GetTickTime` is `proto native float GetTickTime()` on `CGame` (`P:\scripts\3_game\global\game.c:914`).

## The shape of a client and server divergence

The probe rules already fix the payload length, `t=GetTickTime()` on every line, clock offset calibration, interpolation and gap rejection (`debug-protocol.md`, "Probe rules"). Once both series are aligned, the shape of the divergence is a diagnosis:

- A sawtooth means a correction arrives and the system then drifts again, which points at replay determinism.
- A steady rise, or a plateau that never resets, means the transform gets no correction, which points at the correction being switched off.

Do not read the shape until both clocks and the sample gaps have passed those earlier checks.

## Fit the clock offset on the axes you are not investigating

The offset rule says to estimate the server to client offset and interpolate one series onto the other. It does not say which components to fit, and the obvious choice is wrong: minimising the full 3D distance absorbs a real single-axis divergence into the offset and removes it from the residual. The measurement then reports that the two sides agree, for a defect that is there.

Fit only on the axes that are not under investigation, and leave the axis in question as a measurement. On the helicopter, fitting horizontal X and Z only gave a 6 mm median residual over 405 cells and left a height divergence after landing of 0.169 m at the median and 0.833 m at most. A full 3D fit would have spent that height on the offset.

- Where the reference side is constant, the residual does not depend on the offset. With the airframe resting and the server reporting `|vy| <= 0.05`, height on that side does not move, so a clock error adds nothing. Prefer that window when it exists.
- Check the fit with a second estimator that shares nothing with it. A paired handshake line logged with `t=` on both sides is independent of the trajectory, and agreement bounds the alignment error. The two estimators differed by a constant 0.180 s, with 356 of 405 cells within 0.05 s of that median, which also shows the residual is send to apply latency, not error.

## A check on a range scores how long you watched

Peak to peak, a maximum and any other extreme grow with the number of samples. A check written on one of them scores how long the window lasted, and a variant that simply shortens the cells passes it without fixing anything.

Height peak to peak by number of samples at rest, inside one group (upright cells, one process), over 405 landing cells:

| Samples at rest | Median peak to peak |
|---|---|
| 0 to 4 | 0.0000 m |
| 5 to 7 | 0.0000 m |
| 8 to 11 | 0.0031 m |
| 12 to 17 | 0.1729 m |
| 18 to 24 | 0.2619 m |
| 25 or more | 0.4726 m |

The spread from sample count alone (0.0000 to 0.4726 m) is larger than the effect it was used to measure. The claim "flipped cells bounce less" (0.0023 against 0.2434) did not survive matching on sample count: inside a band the sign changed from band to band, and in the fullest band both groups agreed (0.2247 against 0.2619). The flipped cells had 7 samples and the upright ones 21; that was the whole difference.

Write the check this way:

1. A window of fixed length, for example the first 3 s at rest, so every cell contributes the same length of observation.
2. Statistics that do not grow with sample count: a rate (events per second), a quantile (the 90th percentile), or the RMS around the window's own median.
3. If you keep a range, keep its sample count with it, and never compare two ranges with different counts.

Before you compare two groups with a statistic, ask whether it grows with sample size. If it does, the comparison measures the sampling. Probe independence (`debug-protocol.md`) is the neighbouring trap: there two instruments share an origin, here a statistic shares its growth with the clock.

## A defect rate averaged over broken variants describes the experiment

A tuning run's results contain broken configurations on purpose. A defect averaged over all of them does not describe what the shipped mod does, yet that number gets quoted as if it did.

Landing rollover over the same 405 cells:

| Configuration | Cells | Upright | Tilted | On its side |
|---|---|---|---|---|
| The shipped one | 114 | 95.6 % | 2.6 % | 1.8 % |
| Tuning candidates | 291 | 49.1 % | 21.3 % | 29.6 % |
| All cells (the figure quoted) | 405 | 62.2 % | 16.0 % | 21.7 % |

The quoted figure was 21.7 %. The shipped configuration rolls over in 1.8 % of cells, and in six of nine evidence folders it was upright every time. The full set measured mostly how many bad candidates were tried.

Between the shipped configuration and the worst candidate only three fields change, none by more than 13 % (`AttitudeAlphaMaxRadS2` -5.3 %, `GroundEffectBonus` +12.6 %, `StabSoftDeg` -4.6 %), and rollover goes from 1.8 % to 66.7 %. All three moved at once, so the effect cannot be given to any one of them: it is a list of suspects for a run that changes one field at a time.

Every defect rate carries the configuration it was measured on; "X % of cells" without saying which cells has no population. Before you start a redesign over a high rate, check that the rate describes the shipped configuration and not the queue of experiments.

A test that does not reproduce a defect does not show the defect cannot happen. These cells are scripted landings in one spot without touching the cyclic; all they show is that this test, as it stands, does not reproduce the defect in the shipped configuration.
