# Motion evidence and handoff

What counts as proof at each step from contract to in game, which renders to capture, what to hand the DayZ pipeline, and what each result state means. The workflow that uses them is in `realistic-motion.md`.

Lines that say "1.30 changelog" give Bohemia's stated 1.30 engine changes that are not checked on `P:\`.

## Kinds of evidence, weakest first

1. Contract: the source, route, timeline, channels, events and acceptance are written down.
2. Blocking: the key poses are rendered in measured straight on and oblique views.
3. Motion: a full speed preview plus the contact, extreme and recovery frames.
4. Numbers: the sampled report and the checker's JSON, failures and worst frames included.
5. File: the export exists, is not trivial, and carries the intended channels and events. In 1.30 the graph is `.agf` subgraph files listed under `GraphFilesResourceNames` in an `AnimSrcGraph` index (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`), and `.asi` instances are `AnimSetInstanceSource` configs (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:1`).
6. Build and deploy: the packed file is the one actually deployed; give the path and a checksum when stale copies are possible. 1.30 changelog: named mod filesystems and `-resolveFilePatchingUsingEnfusion=1` let the game mount unbinarized `.agf` subgraphs, so they can be checked directly.
7. In game: the target states played, the RPT was read and the motion looked right. 1.30 changelog: the Workbench Animation Editor, now on Enfusion 2021, can Live Edit a running graph, so `VehicleSteering`, `SlopeAngleX` and blend weights can be tuned on a running client.

Never count a lower kind as a higher one. A clean script run is not a clean animation, a render is not an export, an export is not the deployed PBO, and a deployed PBO is not an in game pass.

## Renders to capture

- the start pose;
- first contact;
- the moment of most load or effort;
- the mechanical or support extreme;
- release;
- clearance and return;
- the end pose;
- a full speed video.

Use a straight on view for any claim about orientation. Add top, side and end on close ups for fingers, grips, feet and mechanical clearances.

For a vehicle such as a motorbike on `MOTO1` or `MOTO2`, capture the set during get in, get out and seat switch, the three cases `IsTransitioning` covers (`P:\scripts\3_game\human.c:735` to `:738`). Check the hand lock on the bars and the feet on the pegs through the whole transition.

## Handing the clip to the DayZ pipeline

The compile, wiring and build steps are in `anm-clips.md` and `weapon-anim-blender.md`. Hand over:

- the source scene, its version and the untouched copy;
- the route and the target state name the pipeline gave;
- the export path, with the `.agf` files and `AnimSetInstanceSource` `.asi` mappings;
- frame rate, frame range and events or notetracks;
- the channels included and left out;
- the checker and render paths;
- which kind of evidence above the clip has reached.

Then follow those files' own steps. 1.30 testing can use Workbench Live Editing, the Ragdoll Editor for `.ragdoll` files and `-resolveFilePatchingUsingEnfusion=1` (all from the 1.30 changelog). Do not repeat those steps here.

## Result states

| State | Means | Report |
|---|---|---|
| `FAIL` | A required check failed or an input was invalid. | Check ids, measured values, worst frames, and whether the failure is in the numbers, the picture, the game or missing data. |
| `OFFLINE_PASS` | Blocking, motion, numbers, renders and the offline file all pass. | Say plainly that the game has not confirmed it. |
| `MANUAL_REQUIRED` | The next step needs a GUI action, credentials, hardware, a human judgement or a test setup that is not available. | The exact action and the evidence it must produce; never present the previous state as success. |
| `IN_GAME_PASS` | The deployed build played right in the required states, cameras and stances, the RPT was clean and the visual and mechanical contract passed. | The build that was tested and the evidence. |

## When a pass turns out wrong

When the user or the game shows a passed clip is wrong:

- mark the earlier pass as no longer valid at once;
- keep the failing file;
- add a case that fails for that reason;
- show a corrected case passes;
- update the project's test list, bug list and handoff;
- carry over only the rule that holds across projects, never one project's coordinates or timing.
