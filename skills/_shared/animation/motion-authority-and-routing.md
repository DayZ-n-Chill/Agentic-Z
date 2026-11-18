# Authority and routing

Which file or skill owns which decision when an animation is authored for DayZ, how a request is routed, and what each side hands the other. Vanilla facts cite `P:\`. Lines marked "1.30 changelog" state 1.30 engine changes that are not yet checked on `P:\`.

## Precedence

The director is an orchestrator. It owns motion intent, realism contracts, quality gates, evidence states and the decision to advance. It does not own the implementation facts of Blender or DayZ.

1. The DayZ technical files of this pack (`tooling-and-walls.md`, `anm-clips.md`, `anim-graphs.md`, `player-skeleton.md`, `weapon-anim-blender.md`) win for engine routes, skeletons, graph and state names, formats, FPS and frame budgets, notetracks, export masks, Workbench and DayZATool, ASI and config, build and runtime integration.
2. `blender-mcp-workflow.md` wins for live or headless Blender operation, `bpy`, Actions, constraints, interpolation, simulations, previews and the Blender-side export action.
3. A domain skill wins for its own model, character, vehicle or physics contract.
4. This director owns the cross-skill sequence and the measurable quality contract.

If two authorities disagree, record both claims with their sources and stop the affected gate. Verify the current source or run the discriminating test. Never select the convenient claim merely because it lets an export proceed.

## Routing table

| Request | Primary route |
|---|---|
| Create, correct or polish realistic motion intended for DayZ | This director + `blender-mcp-workflow.md` + the DayZ technical files |
| Pure `model.cfg`, `AnimationSources`, ASI, skeleton or registration question | `model-cfg-animations.md`, `animation-sources.md`, `anim-graphs.md`, `player-skeleton.md` |
| Generic Blender animation with no DayZ destination | `blender-mcp-workflow.md` |
| Retarget external mocap into a DayZ source action | This director + the retargeting skill (`mixamo-retarget.md`) + both authorities |
| Player or custom human asset or rig | Add the body files of `skills/_shared/wearables/` (`body-rigging.md`, `canonical-bind.md`; 1.30: native surrender state, switching the animation instance from script, per-stance speed and camera rotation limits; see `dayz-1-30-changes.md`) |
| Vehicle occupant or contact choreography | Add the vehicle pack, `skills/_shared/vehicles/` (1.30: motorbikes on `MOTO1` and `MOTO2`, two-bone handlebar IK, rider lean) |
| Creature locomotion, combat or terrain alignment | Add `skills/_shared/ai/custom-infected.md` and `skills/_shared/wearables/references/canonical-bind.md` (1.30: `.agf` subgraphs, `AnimSrcNodeProcTransform` terrain rotation, skeletons without fixed bone indices) |
| P3D hierarchy, selection, proxy or mechanical axis | Add the relevant P3D or model skill (`/dayz-p3d-audit`, and the `dayz-object-builder` agent) |
| In-game verification | Add the current DayZ test skills (`/dayz-launch-test`, `/dayz-gate`, `/dayz-logwatch`; the bridge checks in `skills/dayz-launch-test/references/mcp/`) and follow their lease and lifecycle rules (`skills/dayz-launch-test/references/mcp/run-lifecycle.md`) |

## Non-duplication rules

- Link to current authority content instead of copying values or recipes.
- A task-local motion contract may snapshot the result returned by an authority. Label it with source and date; it is evidence for that animation, not a new universal rule.
- Do not promote one weapon's 291-frame duration, one creature's joint limit or one vehicle's seat offsets into defaults.
- Do not embed absolute local tool paths in reusable contracts. Supply them through CLI arguments or environment variables.
- Keep any unresolved export-mask conflict out of the quality checker. The checker validates the channels the current DayZ contract says should exist.

## Handoff contract

From the DayZ authority, request:

- route and target artifact. In 1.30 the player graph is a set of `.agf` subgraph files listed by the `AnimSrcGraph` index `player_main.agr` under `GraphFilesResourceNames` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`), and `.asi` files are `AnimSetInstanceSource` configs (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:1`);
- authoritative rig or skeleton and the bone and channel mask (1.30 changelog: global bone indices are resolved at run time by bone-name hash and the 250-bone limit is gone);
- timeline and event or notetrack constraints;
- runtime states, stances, handedness and camera modes. In 1.30 these include the motorbike third-person camera `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20`), the per-stance speed limits and the per-stance lock on horizontal camera rotation (`SetErectSpeedLimit` at `P:\scripts\3_game\human.c:230`, `DisableErectCameratHorizontalRotation` at `P:\scripts\3_game\human.c:240`);
- compile, wiring, build and deployment path (1.30 changelog: the Workbench Animation Editor moved to Enfusion 2021 with Live Editing, and the `-resolveFilePatchingUsingEnfusion=1` launch parameter);
- the exact in-game evidence required.

To the Blender authority, provide:

- source scene and immutable baseline;
- beat sheet and golden frames;
- landmarks, contacts, forbidden collision pairs and tolerances;
- channels allowed to change;
- preview and export requirements.

Back to the DayZ authority, provide:

- exported artifact and source scene;
- audit JSON and visual evidence;
- exact included and excluded channels;
- offline status and unresolved gates.
