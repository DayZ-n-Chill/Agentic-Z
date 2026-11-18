# Thresholds on in-game telemetry

How to set a numeric threshold on telemetry read from the game (a drive check, a flight spike, any scripted check) so that real physics can pass it and an incomplete trace cannot.

These are measured results from flight checks on a helicopter mod, read through dayz-mcp. None of it is a vanilla fact or checked on `P:\`. It applies to the drive checks in `vehicle-acceptance.md` and to the vehicle pack's own checks.

## Calibrate against the measured noise floor

- A threshold calibrated on ideal mathematical fixtures is one no real physics passes. The engine has its own noise: the body dithers between `SetVelocity` and the read, and the client's network interpolator adds more. Before you set a threshold, measure the floor in a real run (the 95th percentile of the metric on real data), set the threshold to that floor times a margin of at least 2, and write the measured numbers next to the constant. Two independent measurements that agree within 20 % validate the number. A jitter check set at 0.5 m/s against a real floor of 4.3 to 5.1 m/s gave a false fail; recalibrated, it passed with a 2.2 times margin.
- The smoothness a player sees is the frame to frame zigzag in metres: the second difference, the change in implied velocity times dt. It is not the residual against the ideal path per frame, which is autocorrelated and reads twice the real zigzag, and it is not the implied velocity in m/s, which scales with 1/dt and gives different floors at 30 and 60 FPS.
- Leave out start-up transients (the setup teleport and the interpolator chasing it) with a fixed warm-up in the client's scoring window. A real transient of 0.25 s against a 1.0 s warm-up is a 4 times margin. Everything else fails closed.
- Relative checks need an absolute floor too, and the median frame time misleads on a two-peaked distribution. A run at 250 FPS with frames in 4 ms bursts plus a group near 50 ms broke three relative thresholds: largest gap at 3 times the median, dt tolerance at 30 % of dt, and coverage as span over median dt. Use absolute floors with a physical basis (gap 0.150 s, dt tolerance 0.015 s), and measure coverage by the mean of the dt column. The mean of the differences of the time column checks nothing: it is the span divided by n-1, so the ratio is always about 1.

## Float error at the boundary, and a time balance over the whole trace

- Time comparators need an epsilon for float representation. "The boundary itself is allowed" (a 150 ms gap, a 15 ms deviation) breaks in binary: summed deltas give `0.15000000000000002 > 0.15`, a false reject that is not even repeatable. Compare with `> limit + EPS` (1e-6 s) in every time comparator, and test at N-1, N and N+1 (149, 150 and 151 ms; 14, 15 and 16 ms).
- Coverage as count times mean is an identity that a biased denominator slips past. `rows >= K*span/mean(dt)` is the same as `sum(dt) >= K*span`: a dt column biased 50 % high, still under the per-row floor, makes up for 40 % of lost rows, and the check passes an incomplete trace. Use a two-sided balance over the whole trace, `|span - sum(dt[1:])| <= max(1% * span, 0.1 s)`. For an honest producer it is near 0 by physics: at most 0.0001 % of the span in 9 real traces, against 9.98 % in the biased test trace.
- Keep both levels. The per-row check catches a single outlier; the whole-trace balance catches a small steady bias. Either alone leaves a gap: 40 % of rows dropped with dt at 6 ms passed a set of checks that each looked closed on its own.
