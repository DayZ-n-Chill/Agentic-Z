# Flight testing

How to test a scripted flight model in game and judge it from logs: replay state and handshakes for a predicted aircraft, judging a control loop, phase checks, why a diagnostic probe can miss stutter, and how to line up client and server logs.

The numbers here were measured in game on a scripted `CarScript` helicopter that predicts on the owner with the Pawn classes (`aviation-networking.md`). They are not vanilla behaviour and not checked on `P:\` except where a `P:\` line is cited.

## Replay, handshakes and reconciliation

- List every field the solver or state machine reads during a replay, and mark each as restored, recomputed after the handshake, or always set up. Never set up gains or derived tables only inside an `IsServer` branch.
- Do not use a one shot handshake that depends on crew, possession or spawn state that is still arriving. Retry from the client until it is acknowledged, or push from the server when the state is ready. Compare identities by a stable ID, not by instance.
- Read reconciliation from aligned series. Sawteeth mean a correction followed by new drift. Steady growth, or a flat line with no resets, means the transform is not being corrected. Find what makes it converge before you change the solver.
- For a pulse that fires only past a threshold, list every writer of the same variable in that window and check whether the threshold can still be reached when the pulse is due. If a continuous actuator closes the error first (here dead reckoning blending about `0.35` per frame against a needed error of at least 0.5 m/s), open a coast window that pauses the actuator. A pulse that does not fire is recorded with its reason and does not spoil the whole window.

## Judging a control loop

- The shape of the control law proves nothing alone. Log each tick the raw law output, the target, the output actually applied and `out - target`, and look at the clamps after the law before you touch the law. A leftover equal to a tuning constant is saturation, not dynamics: a 9.0 degree residue was a 9 degree hover tilt limit capping the target before the roll law ran.
- Set the starting condition of a test from how a real pilot gets there. Read how earlier clean runs were started, copy those conditions, and add no extra limits "just in case", since that changes what is measured. A manual hover reaches 3.5 degrees or less, and 1 degree or less only after a recovery; an added ban on forward speed ruled out a whole run.
- The check in script must match, character for character, the one written down before the test. Detect "settled" by height above ground, not speed, and do not add a 0.5 m/s forward speed limit when the plan asks only for roll and sideways speed. Do not trust the owner's `GetVelocity()` (`P:\scripts\1_core\proto\enphysics.c:104`) on the ground: it can report the commanded velocity, -1.96 m/s with the helicopter still and a contact distance of 0.0003. Use a sustained height above ground condition and release the collective below 1 m.
- The Pawn move already carries a scripted pilot's input. When the server consumes the owner's move, inject the axes inside `ObtainMove`, between the local read and the move write. Keep the normal path unchanged while the override is off, and log entry and exit. Do not add an RPC or clock sync for data that already travels in that frame.

## Phases are decided by the server

The owner's view supports the verdict; the server decides it. When the server has published `GROUND_READY` or `PARKED`, the landing is over. The owner's height above ground can bounce through interpolation while the server is still; use it as a fallback and a witness, and never let it reopen a confirmed phase. Log both over the same interval, and judge `LEVEL` and `PRESTATE` the same way.

## A diagnostic probe is not a smoothness test

Before you use a probe to judge "smooth", "no stutter" or "no lag", or freeze a baseline from it, open the code that emits it and answer three questions.

1. How often does it emit? A probe written to measure a constant (an offset, a drift) is usually throttled to seconds. The reference state probe on the test helicopter emitted when `refProbeNow - m_RefProbeLastPeriodicLog >= 2.0`, so 0.5 Hz, capped at 10 lines per second.
2. What makes it fire early? That probe broke its period only when the reference state and the body were more than 6.0 m apart. The stutters measured 2.3 to 3.9 m, so they never triggered it.
3. Can it see the problem at all? A one frame jolt sampled every 2 s is invisible. A 5 Hz probe cannot tell whether a change happens in one frame or several either.

A baseline built from that probe is just as blind: 70 samples over 159 s. Comparing against it is fair, since both sides use the same probe, and still cannot answer whether the jolts went away. Both are true at once.

Run two streams in each test: the original probe at its original rate, so the comparison with the baseline stays valid, and a per frame stream of position and angle change and jerk that can see a single frame jump. Do not make the second stream depend on the first's result.

Raising a probe's rate and lowering its trigger for a test is a setting change, not new code. Never strip probes from a build before the tests that read them are finished.

## Lining up client and server logs

A parser that checks owner time windows against server events (`RECGATE`, `TDGATE`, `GND`) needs two things before it scores anything:

1. A clock offset. Client and server times do not share a zero. Measure the offset from pairs of the same event, `EXIT` on both sides or `LEVEL` on the client against the first `RECGATE` on the server; it was about 31 to 34 s. Without it a good window scores as invalid and a real fault can fall outside the band.
2. Duplicate removal. An owner that rewinds and replays emits the probe several times per frame with the same time `t`; 8 to 21 percent of samples were copies. On the edges of a hold the roll flag flickers across the copies, and the parser reports a false "roll active before the hold" or "reactivated at +0.001 s". Keep the first sample per tick, or within 20 ms: that one is the present, the rest are replays.

Score the server series first, since it has no replays, and treat the owner series as secondary. After changing the parser, run the earlier tests again and check that their results do not move.
