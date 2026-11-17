# Evidence and integration

The evidence ladder from contract to in-game proof, the visual review set, what to hand the DayZ pipeline, and what each output state means. Vanilla facts cite `P:\`. Lines marked "1.30 changelog" state 1.30 engine changes that are not yet checked on `P:\`.

## Evidence ladder

1. **Contract evidence:** authoritative source, route, timeline, channels, events and acceptance criteria.
2. **Blocking evidence:** golden-pose renders in measured on-axis and oblique views.
3. **Motion evidence:** full-speed preview plus contact, extreme and recovery frames.
4. **Numeric evidence:** sampled report and audit JSON, including failed checks and worst frames.
5. **Artifact evidence:** the exported file exists, is non-trivial and carries the intended channel and event mask. In DayZ 1.30, check that graphs are `.agf` subgraph files listed by an `AnimSrcGraph` index under `GraphFilesResourceNames` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`) and that `.asi` instances are `AnimSetInstanceSource` configs (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:1`).
6. **Build and deploy evidence:** the compiled or packed artifact is the one actually deployed, with hash and path when stale copies are possible. 1.30 changelog: named mod filesystems and the `-resolveFilePatchingUsingEnfusion=1` launch parameter let the game mount unbinarized `.agf` subgraphs, so they can be checked directly.
7. **In-game evidence:** target states exercised, RPT reviewed and visual behaviour confirmed. 1.30 changelog: the Workbench Animation Editor (now on Enfusion 2021) supports Live Editing of running graphs, so parameters such as `VehicleSteering`, `SlopeAngleX` and blend weights can be tuned on a running client.

Never promote evidence upward. A clean script run is not a clean animation; an offline render is not an exported artifact; an exported artifact is not the deployed PBO; a deployed PBO is not an in-game PASS.

## Visual review set

At minimum capture:

- entry pose;
- first contact;
- maximum load or effort;
- mechanical extreme or locomotion support extreme;
- release;
- clearance and return;
- final pose;
- full-speed video.

Use an on-axis view for orientation claims. Add top, side and end-on close-ups for fingers, grips, feet or mechanical clearances.

For vehicle interactions in DayZ 1.30, such as the motorbikes on `MOTO1` and `MOTO2`, capture the review set during get-in, get-out and seat switching, the three cases `IsTransitioning` covers (`P:\scripts\3_game\human.c:735-738`). Check the two-bone IK hand lock on the handlebars and the foot placement on the footpegs across the whole transition.

## Integration handoff

Send `dayz-animation-pipeline`:

- source scene and version, and the immutable donor;
- chosen route and the target state name supplied by the pipeline;
- exported artifact path (including the `.agf` files and `AnimSetInstanceSource` `.asi` mappings);
- FPS, frame range and events or notetracks;
- included and excluded channels;
- audit and render paths;
- current evidence state.

Then follow its current compile, wiring, build and test procedures. In DayZ 1.30 the test workflow can use Workbench Live Editing, the Ragdoll Editor for `.ragdoll` files and `-resolveFilePatchingUsingEnfusion=1` (all three: 1.30 changelog). Do not reproduce those procedures here.

## Output states

### `FAIL`

At least one required gate failed or an input was invalid. Report check IDs, measured values, worst frames and whether the failure is numeric, visual, runtime or missing data.

### `OFFLINE_PASS`

Blocking, motion, numeric audit, visual review and the relevant offline artifact pass. State explicitly that the DayZ runtime has not been confirmed.

### `MANUAL_REQUIRED`

The next gate requires unavailable GUI interaction, credentials, hardware, human judgment or an unsupported runtime harness. Give the exact action and evidence needed; do not present the previous state as final success.

### `IN_GAME_PASS`

The deployed build played correctly in the required states, cameras and stances, the RPT showed no relevant errors and the visual and mechanical contract passed. Record the build identity and the evidence.

## Regression closeout

If the user or the game refutes a prior PASS:

- mark the prior claim stale immediately;
- preserve the failing artifact;
- add a negative fixture;
- prove a corrected positive fixture can pass;
- update the project validation matrix, bug ledger and handoff;
- promote only the cross-project invariant, not project-specific coordinates or timing.
