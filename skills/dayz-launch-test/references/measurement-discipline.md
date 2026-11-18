# Measurement discipline for in-game evidence

Rules for reading numbers out of a DayZ test session without fooling yourself: aligning client and server series, what the shape of a divergence means, and three statistical traps (a fitted clock offset that absorbs the defect, a range that measures the length of the observation, a defect rate averaged over deliberately broken variants). `debug-protocol.md` points here; the probe rules that come first are in `debug-protocol.md`.

Everything here is method plus measured results from a helicopter mod's test campaign. None of it can be read in a vanilla file, so it is not yet checked on `P:\`; the script calls the probes use are (`GetTickTime` is `proto native float GetTickTime()` on `CGame`, `P:\scripts\3_game\global\game.c:914`).

## The shape of a cross-process divergence

The probe rules already fix the payload length, `t=GetTickTime()` on every line, clock-offset calibration, interpolation and gap rejection (`debug-protocol.md`, "Probe rules"). After that alignment, use the shape of the divergence series as a diagnostic:

- a **sawtooth** means a correction arrives and the system then diverges again, which points at replay determinism;
- a **monotonic rise or a plateau with no reset** means the transform is not receiving correction, which points at the mechanism being gated off.

Do not interpret shape until both clocks and the sample gaps have passed those earlier gates.

## Fit the clock offset on the axis you are not investigating

The offset rule says to estimate the server-to-client offset and interpolate one series onto the other. It does not say which components to fit on, and the obvious choice is wrong: minimising the full 3D distance **absorbs a real single-axis divergence into the fitted offset** and removes it from the residual. The measurement then reports "the two sides agree" for a defect that is present, with no sign that anything failed.

Restrict the fit to the axes that are not under investigation, and leave the axis in question as a measurement, not a fit parameter.

Measured on 2026-09-04 on a helicopter mod: fitting horizontal X and Z only gave a 6 mm median residual over 405 cells and left a post-landing height divergence of 0.169 m at the median, 0.833 m at most, standing. A full 3D fit would have spent that height on the offset.

Two corollaries:

- **Where the reference side is constant, the residual is immune to offset error.** With the airframe resting and the server reporting `|vy| <= 0.05`, height on that side does not move, so any clock error contributes zero. Prefer that window when it exists: the result then does not depend on the fit at all.
- **Validate the fit with a second estimator that shares nothing with it.** A paired handshake line logged with `t=` on both sides is independent of the trajectory; agreement bounds the alignment error. Measured: the two estimators differed by a constant 0.180 s, with 356 of 405 cells within 0.05 s of that median, which also identifies the residual as send-to-apply latency, not error.

## A gate on a range scores how long you watched

Peak to peak (maximum minus minimum), a maximum, and any other extreme grow with the number of samples. A gate written on one of them scores, without saying so, **how long the window lasted**, and a variant that simply shortens the cells passes it without fixing anything.

Measured on 2026-09-10 on 405 archived landing cells. Inside one group (upright cells, one process), the height peak to peak by number of samples at rest:

| Samples at rest | Median peak to peak |
|---|---|
| 0 to 4 | 0.0000 m |
| 5 to 7 | 0.0000 m |
| 8 to 11 | 0.0031 m |
| 12 to 17 | 0.1729 m |
| 18 to 24 | 0.2619 m |
| 25 or more | 0.4726 m |

**The spread caused by the artifact (0.0000 to 0.4726 m) is larger than the effect being measured with it.** The conclusion that leaned on it, "flipped cells bounce less" (0.0023 against 0.2434), does not survive matching on sample count: inside a stratum the sign changes from stratum to stratum, and in the most populated one both groups agree (0.2247 against 0.2619). The flipped cells had 7 samples and the upright ones 21, and that was the whole difference.

Write the gate this way instead:

1. **A window of fixed length** (for example the first 3 s at rest), not "the whole window". Every cell then contributes the same length of observation and ranges are comparable again.
2. **Statistics that do not grow with the sample count:** a rate (events per second), a quantile (the 90th percentile), or the RMS around the window's own median.
3. If a range is kept, keep it **together with its sample count**, and never compare two ranges with different counts.

The general signal: before comparing two groups with a statistic, ask whether that statistic is a function of sample size. If it is, the comparison measures the sampling design. Probe independence (`debug-protocol.md`) is the neighbouring trap: there two instruments share an origin, here a statistic shares its growth with the clock.

## A defect rate averaged over mutated variants describes the experiment

A tuning campaign's corpus contains, on purpose, configurations that are broken. Averaging a defect over the whole corpus gives a number that does not describe what the product does, and that number ends up quoted as if it did.

Measured on 2026-09-10, the same run. Landing rollover:

| Configuration | Cells | Upright | Tilted | On its side |
|---|---|---|---|---|
| **Incumbent (the one shipped)** | 114 | **95.6 %** | 2.6 % | **1.8 %** |
| Mutated candidates | 291 | 49.1 % | 21.3 % | 29.6 % |
| **Whole corpus (what was quoted)** | 405 | 62.2 % | 16.0 % | **21.7 %** |

21.7 % was the figure in circulation. The shipped configuration rolls over in **1.8 %** of cells, and broken down by date it comes out 100 % upright in six of nine evidence folders. The corpus measured, above all, how many bad candidates were tried.

What produced the difference is worth recording: between the incumbent and the worst candidate only **three fields** change, none by more than 13 % (`AttitudeAlphaMaxRadS2` -5.3 %, `GroundEffectBonus` +12.6 %, `StabSoftDeg` -4.6 %), and the rollover rate goes from 1.8 % to 66.7 %. All three moved at once, so **the effect cannot be attributed to one of them**: it is a list of suspects for a run that changes one field at a time, not a cause.

How to report: every defect rate carries the configuration it was measured on. "X % of cells" without saying which cells is a figure with no population. Before opening a redesign plan because of a high rate, check that the rate describes the shipped configuration and not the queue of experiments.

A limit to say out loud: a test bench that does not reproduce a defect does not mean the defect cannot happen. These cells are scripted landings, in one spot and **without touching the cyclic**; the only thing they allow you to say is that the test bench, as it stands, does not reproduce the defect in the shipped configuration.
