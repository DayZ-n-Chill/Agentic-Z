# Working method and check calibration

How to spend in-game cycles on a vehicle build, how to make sure an offline check can fail before trusting it, and what a pass actually covers. These rules cost more iterations than any config fact when skipped. Negative test cases for import checks are in `process-gates.md`.

## Count the cycles on one goal

- Track how many build and test cycles one objective has taken, and make the count stop you. At three, choose before touching code: change strategy, hand it to a person, or drop the objective. A rule like "after two rebuilds without progress, change strategy" does nothing when nobody counts.
- Two failed rebuilds on one symptom means build a probe, not a third rebuild. List the candidate causes, read the real mechanism in the vanilla scripts, log both client and server, and confirm the hook fires at all (a silent log is a signal; `OnUpdate` is not an engine callback). Then make one directed fix. If two probes also fail, review the real files with several agents at once.
- Keep test tooling out of the product task. If a product task is blocked twice by its own test tooling, stop and decide: make the tooling its own project, or run that one test by hand and move on.
- When the judge is the eye or the feel of driving, offline analysis gets one round to rule out cheap causes; then go to the game. Green offline checks do not predict the in-game result, and more offline rounds only delay the answer.
- A visual fault that survives several rounds is a reason to involve a person, not to run one more round. A decimated rip mesh, for example, may never reach game-ready quality and needs an artist.

## Habits that stop re-deriving known causes

1. Compare against vanilla first. Unpack a known-good vanilla car (the `CivilianSedan`; the copy on `P:\` has version 56 in its header) once, and diff your model against it: LODs, named selections, crew proxies, wheel hubs, `componentNN`, memory points. Fix every gap in one pass. See `vehicle-structural-parity.md`.
2. The game is the only check that counts; offline results are hints. A metric that is `0.000` or 100 percent by construction, such as winding measured against the model's own normals, proves the model agrees with itself, not that DayZ renders, spawns or seats it. Never close a step on such a check.
3. When a get-in action does not appear for a seat, probe the crew before any rebuild. Spawn the car and a control car whose get-in works, dump `CrewPositionIndex` for component indices 0 to 79 (`P:\scripts\3_game\vehicles\transport.c:182`), and cast a View Geometry ray (`ObjIntersect.View`, `P:\scripts\3_game\constants.c:34`) per seat from `pos_driver` and `pos_codriver`. This finds inward-facing seat geometry without guessing.
4. Re-aim an old probe before believing its negative. A probe carries the coordinates of the model it was written for; run unchanged on a newer model, a `hit=0` can be a miss, not a verdict. Take the aim point from what produced the current model, compute the ray's margin against the target box (less than about one half-extent means the result is not evidence), and log the aim point next to the result. On a test car an old probe still hit, but only 3.7 cm inside the box.

## Make a check able to fail before trusting it

These apply to every check: render and winding, capacity, parity, telemetry and policy. The common ways a check lies:

| Shape | What happened |
|---|---|
| A threshold copied, not measured | An assembler used 65535 as the resolved vertex limit; `binarize` rejected the model at 46,133, about 30 percent lower. The ratio differs by model (1.4205 on one test helicopter, 1.46 on another), so re-measure with `binarize` for each model; see `binarize-vertex-budget.md`. |
| A policy that changes nothing | Two winding policies were the same in maths (`dot(-cross,-n) == dot(cross,n)`), and four variants were built on them before anyone checked. |
| A check that shares the builder's assumption | Seat parity compared under pure translation, the same assumption the sub-model was built with. A delta of `0.000` proved the two agreed, not that either was right. |
| One field read from a larger output | `attachment_count=2` was read as a pass while the regression sat in the same output. |
| A LOD matched by its round resolution | On disk Fire Geometry reads `6999999976046592`, not `7e15`. An exact match finds nothing, so the check reports a selection as missing when it is there. Match with a relative tolerance: `abs(res - nominal) <= nominal * 1e-3`. This one shows up as a confident fail about missing data, not a suspicious pass. |

Before trusting a check:

- Run it on a known-bad case. A pass on a known-bad case means the check is the bug.
- Name in one line the assumption the model was built with, and confirm the check does not reuse it. A check only ever seen passing is unmeasured.
- Make every check catch at least one real fault already seen in game, not only a synthetic test. Keep a short list of known in-game faults per car and confirm the checks catch each one; a mixed-winding rear window, for example, showed as 18.2 percent of the glass area failing a winding consistency check.
- A check that stays red stops telling you anything. If a known failure is accepted on purpose, record its exact signature (entities and measurements) and report it apart from new failures. Any change in it, including an improvement, is new information.

## Scope of a pass

- Say what a pass covers, never a bare "clean". "No see-through faces in `color` and `glass`" is not "winding is clean"; reporting the second when only the first was checked is a false pass the player finds in game.
- Take the measurement window from where the defect shows (the viewing angles, what the user pointed at), not from the area the fix touched. A fail dismissed as a window artifact needs a separate control that proves the instrument wrong.
- Choose the comparison by where new faces came from. Invented points and UVs compare against a calibrated reference such as the material median. Geometry made from one face (a mirrored twin, a displaced panel) compares against that exact source face; an exact twin needs exact equality. A twin cannot fail a UV check, because it copies the UVs. A failure inherited unchanged from the source does not show the edit caused it.
- If a detector rejects about half of all entities, assume a structural cause, such as double-sided construction, until shown otherwise. Prefer measures inside one entity, such as the three vertex normals of a triangle more than 90 degrees apart, and re-measure the whole remainder after a fix: on a test car, flipping opposite normals fixed about 59 percent and the rest needed flattening against the face normal.
- Print the model's modification time with every analysis and flag a change since the last run; the deployed `.p3d` can change under you. Only the session working on a shared model edits it.

## Check names before writing them

Vehicle config and model values are easy to half remember. Before writing a class name, property or named selection, Grep it under `P:\DZ\vehicles\` and cite the `P:\` file and line. Mark a value you could not check as not yet checked on `P:\`.
