# Numeric gates on in-game telemetry

How to set a threshold on telemetry read from the game (a drive ladder, a flight spike, any later harness) so that real physics can pass it and an incomplete trace cannot.

Everything here is measured results from game sessions with dayz-mcp on a helicopter mod's flight gates (2026-07-11), not yet checked on `P:\`; none of it is a vanilla fact. It applies to the drive ladder of `acceptance-ladder.md` and to the vehicle pack's own gates.

## Calibrate against the measured physical floor, not ideal fixtures (added 2026-07-14)

1. **A threshold calibrated with ideal mathematical fixtures is a gate that no real physics passes.** The engine has a native noise floor (the body dithers between `SetVelocity` and the read; the client's network interpolator). Before setting a threshold, measure the floor in a real run (the 95th percentile of the metric on real data), set the threshold to the floor times a margin of at least 2, and write the measured numbers next to the constant. Two independent measurements that agree within 20 % (the implementer's and the receiver's) validate the number. Case: a jitter gate at 0.5 m/s against a real floor of 4.3 to 5.1 m/s gave a false no-go that cost a whole corrective pass; recalibrated, it gave a go with a 2.2 times margin.
2. **The smoothness a player perceives is the frame-to-frame zigzag in metres** (the second difference, the change in implied velocity times dt). It is not the residual against the ideal per frame, which is autocorrelated and reads twice the real zigzag, and it is not the implied velocity in m/s, which scales with 1/dt: the same process gives different floors at 30 and 60 FPS and breaks any comparison between FPS cells.
3. **Start-up transients** (the setup teleport and the interpolator chasing it) are excluded with a bounded warm-up in the client's scoring window: a real transient of 0.25 s against a warm-up of 1.0 s is a 4 times margin. Everything else fails closed.
4. **Relative structural checks need an absolute floor too, and the median frame time misleads on a bimodal distribution.** A run at 250 FPS with a bimodal frame time (4 ms bursts plus a population near 50 ms) broke three relative thresholds: maximum gap at 3 times the median, dt tolerance at 30 % of dt, and coverage as span over median dt. The fixes: absolute floors with a physical basis (gap 0.150 s, dt tolerance 0.015 s), and coverage by the mean of the dt column. The mean of the differences of the time column is a tautology (span divided by n-1, so the ratio is always about 1) and checks nothing.

Checked by two converging measurements and a 31 of 31 self-test.

## Float epsilon at boundaries, and an aggregated time balance (added 2026-07-14)

Two adversarial defects, reproduced on a gate that had already been sealed twice:

1. **Comparators on time thresholds need an epsilon for float representation.** A contract of "the boundary itself is tolerated" (a gap of 150 ms, a deviation of 15 ms) breaks in binary: accumulated deltas give `0.15000000000000002 > 0.15`, a false reject at the boundary that is not even deterministic. Fix: compare with `> limit + EPS` (1e-6 s) in every time comparator, with boundary fixtures at N-1, N and N+1 (149, 150 and 151 ms; 14, 15 and 16 ms).
2. **Coverage as count times mean is an identity that a biased denominator evades.** `rows >= K*span/mean(dt)` is the same as `sum(dt) >= K*span`: a dt column biased upward by a sustained 50 %, under the per-row floor, compensates for 40 % of lost rows, and the gate opens on an incomplete trace. Fix: an aggregated two-sided balance, `|span - sum(dt[1:])| <= max(1% * span, 0.1 s)`. For an honest producer it is near 0 by physical identity: at most 0.0001 % of the span in 9 real CSV traces, against 9.98 % in the adversarial fixture.
3. **A per-row floor and an aggregated invariant are a required pair.** The per-row check catches an isolated outlier; the aggregate catches a small sustained bias. One level alone leaves a flank open, and the fixture that shows it is the coupling of two checks that were each closed on their own (40 % of rows dropped with dt at 6 ms gave a go on an incomplete trace).
