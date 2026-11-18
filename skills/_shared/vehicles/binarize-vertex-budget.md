# Binarize as the load check

How to use `binarize.exe` to tell, offline, whether the engine will load a model: its three verdicts, the real vertex ceiling in resolved triples, how thin a deployed model's headroom can be, and which log lines mean nothing.

The results here were measured on mod models: a helicopter checked against 25 in-game verdicts, a second helicopter, a test vehicle and two buildings. They are mod behaviour, not vanilla. The short rule is in `invariants-lods-and-vertex-budget.md`; this file holds the evidence behind it. Read it when a model passes every offline check and still will not spawn, or before you add geometry to a model near its limit.

## What vanilla shows

- `binarize.exe` ships with DayZ Tools and reads its source from the work drive; run `/dayz-preflight` before any step here that calls it.
- Vanilla models are that tool's output: `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` starts with the `ODOL` signature, version 56. So a verdict here can only be reproduced on a mod's own MLOD source, never on a vanilla model.

## Too many vertices looks like missing geometry

`Too many vertices` and `Won't simulate, it has no geometry` are the same fault. The engine rejects the model while loading the MLOD, before conversion, so it drops the whole model and prints the generic physics message even when the Geometry LOD is fine. If a model that passes every offline check does not spawn, run binarize on it before you touch the Geometry LOD.

## Run it on a batch

`binarize.exe -always <source under P:\> <out>` checks many models in one pass, in about 90 s. Give it a `model.cfg` that declares every base name in the source folder; an undeclared name falls back to `Default` and takes a different code path. On the reference helicopter, 28 variants gave 13 pass and pass, 12 fail and fail against their in-game verdicts, with no false green and no false red. A model bisection drops from about 6 minutes per variant to about 90 s per batch.

Also pass `-addon=<bench>`, where `<bench>` is a folder holding the source folder; binarize parses every `config.cpp` under `-addon` (`skills/dayz-build-pbo/references/addonbuilder-rules.md`). The 28 variant check ran without it. On the test vehicle, with its source outside `P:\` and no `-addon`, a run waited about 5 minutes before loading its first model, and a later run gave no ODOL in 30 minutes; with `-addon` the first model loaded within a second, all 8 still passed, and kits built from them spawned in game. No capacity failure has been run with `-addon`, and the stall was seen only with a source outside `P:\`.

The `Material not loaded` lines (see "Log lines that mean nothing") do not affect the verdict, but they do affect the ODOL: every material entry in the test vehicle's 8 ODOLs came out empty, with `-addon` and without. Run the empty material check in `skills/dayz-build-pbo/references/addonbuilder-rules.md` before you ship an ODOL from the bench.

## Three verdicts, not two

| Verdict | Means |
|---|---|
| `PASS` | A new, non-empty ODOL for the base name under test, in an output folder that did not already hold it. Without the "new" condition, a leftover ODOL gives a false pass. |
| `CAPACITY_FAIL` | No new ODOL, and a `Too many vertices` line naming that MLOD. |
| `OTHER_FAIL` | Any other missing output: a bad `model.cfg`, an undeclared base name, a malformed MLOD, a file error, an aborted tool. It blocks the build and never justifies touching geometry. |

Without the third state you decimate a mesh because the bench was set up wrong.

The capacity line names the MLOD, not the LOD. On a building it came from collision LODs that had grown while the visual LOD was as before (`_shared/models/lods-authoring.md`). Before you blame the latest change, compare every LOD with the last build that passed.

One cause prints nothing of its own (measured on a building, not a vehicle): with too many pieces in its collision LODs, `binarize.exe` wrote no ODOL and no capacity line, and the bench read `OTHER_FAIL` although it was set up correctly. Rule it in only when the MLOD reads through to `#EndOfFile#` in every LOD (a truncated MLOD gives the same verdict) and the same model passes without its collision LODs. Those two checks place the fault in the collision LODs; they do not measure the limit. The fix moves pieces into another model with the same transform and leaves every piece as it is, none merged or decimated, and each resulting model must still pass. The limits and figures are in `_shared/models/building-collision-limits.md`.

The verdict repeats; the ODOL bytes do not. The same `.p3d` gave 1,725,025 and 1,726,689 bytes with different hashes in two clean runs, so never check an ODOL by its hash.

## Log lines that mean nothing

These appear for a known good model too: `Material not loaded`, `No entry '.CfgVehicles'`, `Trying to access error value`, `Error occured: Loading LODShape`, `UV mapping too varied`, `vertices of bone X are shared with bone Y`, `Too detailed shadow lod`. The word `Error` in the log decides nothing. Tie the outcome to a model and a cause, or record `OTHER_FAIL`.

## The ceiling is not 65535

Walking four differently built versions of the same model to the limit gave the same number each time: 46,133 resolved triples load and 46,134 do not. The engine's hard cap does appear to be 65,535, but on vertices after splitting, and a `(point, normal, uv)` counter undercounts those by a factor that depends on the model: 1.4205 on that helicopter and 1.46 on the second one. An assembler with `RESOLVED_LIMIT = 65535` hard coded passed its own check, for weeks, on a model the engine refused. Measure each model; the binarize verdict is the real check.

## Know the headroom

The deployed reference helicopter sat at 46,019 of 46,133: 114 triples of margin, 99.8 percent full. Any change that adds more than 114 resolved vertices breaks it: a normal tweak, a UV seam, a texture that forces another split. Count resolved vertices before and after every visual edit.

## A new normal costs budget; a corner order does not

A winding fix that negated the stored normal per corner, on the 151 faces (0.43 percent) whose source normal disagreed with their winding, added 630 pool entries and 886 resolved vertices from 453 corners. Reversing the corner order of the same 151 faces gives the same result at no cost. A face's corner order is free; a new normal is not.

Before you "fix" a winding by inverting things, keep this in mind: `dot(-cross, -n) == dot(cross, n)`. Reversing the corners and negating the normal together changes nothing between them.

## Step past the engine's rounding

When you walk a limit, each step must survive the engine's quantisation. Nudging one component of a normal by 1e-4 (about 0.006 degrees) does not survive DayZ's normal compression: the estimator counted 120 new triples, the engine saw none, 42 samples "passed", and the ceiling would have been reported 7 too high. Use a step clearly above the quantum (3 degrees or more for normals), and include one sample past the known failing value as a self check.

A resolved triple counter (py3d, one count per LOD) is a guide; only a binarize run gives the three state verdict. No bench script for it ships in this repo: write one from the three states above.

## Check a warning against the deployed model first

Before you change geometry over a numeric warning, run the same counter on the known good model taken from the deployed PBO. If that model already exceeds the threshold, the threshold does not apply to that load path. Check the packed file, not the editable source, and read its signature: `MLOD` means the engine loads it unbinarized, `ODOL` means binarized. Neither result proves the other.

A tolerance sweep proves only the points it sampled. Steps of ten can jump over the useful range; refine around the change, and for unit normals test an angular merge, not only rounding each component. A refined sweep must first reproduce every earlier sample before any new point counts.

## Read the verdict file, not the exit code

A bench's binarize run and a Python import error can both exit `1`. Have the bench write a verdict file per run, for example `_verdicts.json`, and read the state from a freshly written one; a missing file or row is `OTHER_FAIL`, never a pass or a capacity failure. The child process needs its module on `PYTHONPATH`, since a `sys.path` change inside the parent is not inherited. Allow for start up (about 68 s even for a four point test model); give a batch a longer timeout, and put a tiny known good model in the same run. If that control does not pass, no failure in the run can be blamed on capacity.

Keep three counts apart: a modelling tool's estimate may split one source point by rounded corner normal and UV; py3d `resolved` counts `(point_index, normal value, uv)` on the assembled MLOD; the engine limits vertices after splitting. Budget in assembled py3d counts and decide with the binarize verdict. Count with the host's proxies in place: each proxy adds three points, one face normal, one face and three resolved entries.

## A source count plans, it does not approve

Before you give up the artist's normals, decimate or repartition, compose the source nodes' world transforms and count `POSITION` accessor vertices for each final owner container. Count every instance: a mesh used by three nodes costs three times. The glTF accessor total is a safe planning bound and is available before the MLOD exists.

It tells you where to measure next; it does not approve a build. Do not compare it with a fixed 60,000, 65,535 or roughly 32,768: those numbers mix source vertices, assembled resolved triples and engine vertices after splitting. Use the py3d count as a guide and the binarize verdict as the decision. This replaces the fixed vertex targets in `decimation-libraries.md` and `external-obj-import.md` for planning, without weakening any measured check.
