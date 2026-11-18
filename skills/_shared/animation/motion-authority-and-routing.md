# Who decides what in motion work

Which file or skill has the last word on each part of a realistic animation for DayZ, where a request goes, and what each side hands the other. The steps themselves are in `realistic-motion.md`.

Lines that say "1.30 changelog" give Bohemia's stated 1.30 engine changes that are not checked on `P:\`.

## Order of authority

`realistic-motion.md` owns the motion intent, the acceptance contract, the checks and their results, and the call to move on. It does not own Blender or DayZ facts. When files disagree, the more specific one wins:

1. The DayZ files of this pack (`tooling-and-walls.md`, `anm-clips.md`, `anim-graphs.md`, `player-skeleton.md`, `weapon-anim-blender.md`) decide clip routes, skeletons, graph and state names, formats, frame rate and frame budget, notetracks, export masks, Workbench and DayZATool, instance files and config, build and in game wiring.
2. `blender-mcp-workflow.md` decides how Blender is driven, live or from the command line: `bpy`, Actions, constraints, interpolation, simulations, previews and the export step.
3. A domain pack decides its own model, character, vehicle or physics rules.
4. `realistic-motion.md` decides the order of the work across files and the measured acceptance.

When two of them disagree, write down both claims with their sources and stop that check. Check the current source or run the test that tells them apart. Never take the claim that happens to let an export go ahead.

## Where a request goes

| Request | Open |
|---|---|
| Create, correct or polish realistic motion for DayZ | `realistic-motion.md`, `blender-mcp-workflow.md` and the DayZ files above |
| A pure `model.cfg`, `AnimationSources`, instance file, skeleton or registration question | `model-cfg-animations.md`, `animation-sources.md`, `anim-graphs.md`, `player-skeleton.md` |
| Blender animation with no DayZ destination | `blender-mcp-workflow.md` |
| Outside mocap into a DayZ source action | `realistic-motion.md` and `mixamo-retarget.md`, with both Blender and DayZ files |
| A player or custom human asset or rig | Add `_shared/wearables/references/body-rigging.md` and `_shared/wearables/references/canonical-bind.md`; the 1.30 surrender state, script instance switch and per stance limits are in `dayz-1-30-changes.md` |
| A vehicle occupant or contact with controls | Add `_shared/vehicles/` (1.30: motorbikes on `MOTO1` and `MOTO2`, two bone handlebar IK, rider lean) |
| Creature locomotion, combat or terrain alignment | Add `_shared/ai/custom-infected.md` and `_shared/wearables/references/canonical-bind.md` (1.30: `.agf` subgraphs, `AnimSrcNodeProcTransform` terrain rotation, skeletons without fixed bone indices) |
| `.p3d` hierarchy, selection, proxy or mechanical axis | `/dayz-p3d-audit` and `dayz-object-builder` |
| In game test | `/dayz-launch-test`, `/dayz-gate`, `/dayz-logwatch`, and the DayZ facts behind an in-game check listed in `skills/dayz-launch-test/references/README.md` |

## Keeping facts in one place

- Link to the file that owns a value or recipe; do not copy it.
- A contract for one animation may record a value an owning file returned. Note where it came from; it is evidence for that animation, not a new general rule.
- Never turn one weapon's 291 frame length, one creature's joint limit or one vehicle's seat offsets into defaults.
- Keep local tool paths out of reusable contracts; pass them as command line arguments or environment variables.
- Keep an unresolved export mask conflict out of the motion checker. It checks the channels the current DayZ route says should exist.

## What each side hands over

Ask the DayZ side for:

- the route and the file to produce. In 1.30 the player graph is a set of `.agf` subgraph files listed under `GraphFilesResourceNames` in the `AnimSrcGraph` index `player_main.agr` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`), and `.asi` files are `AnimSetInstanceSource` configs (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:1`);
- the skeleton and the bone and channel mask (1.30 changelog: global bone indices come from a hash of the bone name at run time, and the 250 bone limit is gone);
- the timeline and the event or notetrack limits;
- the states, stances, handedness and camera modes. 1.30 adds the motorbike third person camera `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20`), per stance speed limits (`SetErectSpeedLimit`, `P:\scripts\3_game\human.c:230`) and a per stance lock on horizontal camera turning (`DisableErectCameratHorizontalRotation`, `:240`);
- the compile, wiring, build and deploy path (1.30 changelog: the Workbench Animation Editor moved to Enfusion 2021 with Live Editing, and the launch parameter `-resolveFilePatchingUsingEnfusion=1` exists);
- the exact in game evidence needed.

Give the Blender side:

- the source scene and a copy that stays untouched;
- the beat sheet and the key poses;
- landmarks, contacts, forbidden collision pairs and tolerances;
- the channels it may change;
- the preview and export requirements.

Give back to the DayZ side:

- the exported file and its source scene;
- the checker's JSON and the renders;
- the exact channels included and left out;
- the offline result and any open checks.
