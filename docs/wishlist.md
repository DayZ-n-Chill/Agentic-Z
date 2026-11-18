# Wishlist

Ideas that would be nice to add but were not asked for. Nothing here is built during a job: the rule in `.claude/CLAUDE.md` ("Scope") sends every such idea here instead. The user picks what, if anything, becomes real work.

| Idea | Where it came up |
| --- | --- |
| Build Agentic-Z's own in-game test tool, written from scratch: a small in-game DayZ mod that carries out commands (spawn, teleport, drive a vehicle, raycast, camera and screenshot, read logs) and an MCP server in this repo that agents call, wired into `/dayz-launch-test` and `dayz-ingame-tester`. The engine facts are in `skills/dayz-launch-test/references/`. Next project; plan with `dayz-mod-architect` first. | Owner decision |
| Derive the seat roster in `skills/dayz-p3d-audit/scripts/audit_getin_wheels.py` from the car's `Crew` config, so it is right for four-seat cars and cars with no seat-back selections. | Vehicles review |
| A census script for the hidden-selection face ownership check and the light selection preflight the vehicle pack describes by hand. | Vehicles review |
| A PBO reader for the checks in section 5 of `skills/_shared/vehicles/build-packaging-and-debug.md` (completeness, build mode, baked wheel angle, stray drive letters); `scripts/tools/dayz-pbo-diff/` may cover part of it. | Vehicles review |
| An override resolver for the 1.30 migration checklist: flag an `override` of a method DayZ 1.30 deleted, which the script validator passes today. | Vehicles review |
| Turn the DXT1 PAA encoder printed in `skills/_shared/textures/png-to-paa-encoding.md` into a tested script with a DXT5 path. | Vehicles review |
| A `/dayz-p3d-audit` check for a vehicle sub-model whose visual LOD lacks `autocenter=0`. | Vehicles review |
| A `/dayz-p3d-audit` check built from a negative fixture that swaps the proxy frame sides and must fail. | Vehicles review |
| A script that finds each un-prefixed `file.c:N` citation in the vehicle field-note files on `P:\` and rewrites it with the `P:\` prefix, so the citation tests cover them. | Vehicles review |
| A short "Boats at run time" section in `skills/_shared/vehicles/class-hierarchy.md` (engine stop out of water, decay timer, water particle points). | Vehicles review |
| A `/dayz-lint` warning for a class that extends `CarScript`, defines `EOnSimulate` and never calls `SetEventMask(EntityEvent.SIMULATE)`. | Vehicles review |
| A `/dayz-lint` check that every `UA*` string read in script is declared in the mod's `inputs.xml`. | Vehicles review |
| A fixed phrase for facts reported for a newer game build than the one on `P:\`, as a convention. | Vehicles review |
| Eval questions for `dayz-vehicle-specialist` on aviation (event mask, `OnDriverExit` gear stop, `SyncedValue` priming) and motorbikes (brake `input` channels, `Wheels` without `Axles`, the battery override, the directional get-in pair). | Vehicles review |
| `/dayz-p3d-audit`: print a per-LOD resolved-vertex count, with a warning at 90 % of a ceiling the user gives. | Models review |
| `/dayz-p3d-audit`: script the checks its references describe by hand (wheel model memory points, ride height, component count and mass share on a vehicle, `#Mass#` outside Geometry, the per-component inward winding check, the get-in contract gate). | Models review |
| A UV audit script for MLOD models (`uv_audit.py`), and a `/dayz-p3d-audit` report of the share of zero and degenerate UVs per visual LOD. | Models review |
| Scripts for the parts of the clean UV atlas method (`skills/_shared/models/tools-uv-atlas.md`) that have none: the `smart_project` fallback (`smart_project` plus the exact fold loop) and the shared-sheet recipe for LODs. | Models review |
| Clean UV atlas engine (`skills/dayz-model-tools/scripts/project_atlas.py`): take the expected `.blend` hash, face count and shell lists from command-line options or the assignment JSON, pick the stage with a `--stage` option, and replace `render_atlas_pngs` with a small PNG writer. | Models review |
| `sat_gate.py`: print evaluated, skipped and total triangle counts, and stop cleanly when every triangle is collapsed. Share one module for the SAT check and the island finder, which exist two and three times. | Models review |
| A Blender-gated end-to-end test for the clean UV atlas scripts of `dayz-model-tools` (unwrap a small generated mesh, assert zero overlapping pairs). | Models review |
| Write `probe_truth.py` and `facet_report.py`, which `skills/_shared/models/tools-vlm-judge.md` documents but `/dayz-model-tools` does not ship. | Models review |
| A checker for shorthand citations (`file.c:123`, a bare `:123` after a path), which the integrity test skips. | Animation review |
| Name the graph layer in the opening sentence of `skills/_shared/animation/README.md`. | Animation review |
| A pytest for `gen_model_cfg.py` (it has only `--self-test`), one that builds the animation viewer page against `viewer_core.py`, and tests for `ik_pose_to_seanim.py` and `weapon_grip_viewer.py --data`. | Animation review |
| Finish `ik_pose_to_seanim.py`: write the step that turns joint positions into bone rotations, and drop its free text notes. | Animation review |
| A guard in `weapon_grip_viewer.py` that refuses a py3d without `IS_DAYZ_FORK`. | Animation review |
| `skills/dayz-animation-pipeline/scripts/retargeting.py`: reject an empty bone map, strip the `mixamorig:` prefix, register the three scene properties, fix the `KeyError` in `auto_map_bones`, and replace the emoji in its `print` calls with plain text. | Animation review |
| A filled-in `production` contract template for the motion checker (`skills/_shared/animation/motion-contract.md`), with provenance blocks, to copy per task. | Animation review |
| Run `skills/dayz-animation-pipeline/scripts/run_regression_tests.py` once on a machine with Blender and record the result. | Animation review |
| An in-game test of a `.txa` exported with the ring and pinky chains and their carpal bones, to settle an open disagreement. | Animation review |
| Run the two `get_fcurves` variants on a real Blender 4.3 and 4.4, to settle an open disagreement. | Animation review |
| Run the character winding gate as a step of `/dayz-gate build` or `/dayz-p3d-audit` for any mod with a skinned model. | Animation review |
| Rebuild the offline deform judge and the bone-list diff for characters as scripts, and add a script that reads the skeleton name out of a binarized model. | Animation review |
| An offline check script for a worn clothing model (skeleton name byte scan, anatomical facing test), and have the alignment viewer export its own cross-check samples. | Animation review |
| An offline check that every part `id` in a `Construction` block is unique and between 1 and 93, as part of `/dayz-lint`. | World review |
| A `types.xml` entry check against the public classes of `config.cpp`, as part of `/dayz-lint`. | World review |
| An offline script that builds the sidecar cleanup table (every file suffix written against every `DeleteFile` site) and the path helper table from a mod's scripts, for `/dayz-lint` or the deep data audit in `skills/_shared/persistence/deep-audit.md`. | World review |
| An eval question set for `dayz-physics-specialist` drawn from the physics pack, `skills/_shared/physics/`. | World review |
| `rvmat_lint.py`: warn when a Stage4 `_as` reads `uvSource="tex1"` in a material borrowed from vanilla, and when a `_nohq` source name lacks the suffix. | World review |
| A script that prints per channel statistics of an `_as` or `_smdi` `.paa`, and one under `scripts/dev/` that regenerates the procedural SMDI and `dir[]` counts after a game update. | World review |
| A `/dayz-p3d-audit` mode that compares the centre of each remapped weapon selection with the reference weapon. | World review |
| `scripts/dayz/` wrappers that build the API index from `P:\scripts` and query it, so Windows users get every inherited member of a class in one command. | Scripting review |
| Check each Expansion call shape in `expansion_style.md` against the Expansion PBOs and add file and line. | Scripting review |
| A script validator rule for `ChangeGameFocus(0)`. | Scripting review |
| A test that every file named in a `SKILL.md` reference table exists. | Scripting review |
| A script that prints, for one widget type, the vanilla styles whose `Normal` state has a non-empty `Center`. | Scripting review |
| A test that runs `scripts/tools/dayz-ui-lab` `parse.py --check` on the four UI layout templates. | Scripting review |
| A CSV stringtable check (keys used against column 1, header columns). | Scripting review |
| A build check that every `.rvmat` named in `config.cpp` is an entry of the PBO. | Scripting review |
| Compare the entries of two PBOs from `/dayz-build-pbo` with `scripts/tools/dayz-pbo-diff`. | Scripting review |
| `/dayz-setup-objectbuilder`: offer to set the external viewer to the game's `-buldozer` command line. | Scripting review |
| A guard in `/dayz-gate` and `dayz-ingame-tester` that never stops a running DayZ test session it did not start, for example one driven by Agentic-Z's own planned in-game test tool, unless the user confirms (`--yes`). | Scripting review |
| `/dayz-stop-test`: list each DayZ process command line before killing, and cover `DayZServer_x64.exe`. | Scripting review |
| A `--game-root` option on `/dayz-lint` for the `VANILLA-ROOT-BUILD-MISMATCH` rule. | Tools review |
| Let `/dayz-gate build` and `/dayz-build-pbo` find dependency folders from `requiredAddons[]` and pass them to the lint code stage. | Tools review |
| A thin skill for `scripts/tools/dayz-layout-viewer`, next to `/dayz-layout-preview`. | Tools review |
| Short `.cursorrules` and `.github/copilot-instructions.md` entry files that point at `AGENTS.md`. | Knowledge review |
| An eval question for `dayz-ui-specialist` on Dabs MVC. | Knowledge review |
| Panel (liked): a log errors card with the newest 5 `script.log`/RPT errors from `logwatch.py --json`, crash logs in red, each with an "Ask the debugger" button that fills the prompt box. | Mod panel review |
| Panel (liked): a test-server picker (instances under `.server\`, passed as `--server` to Launch and Check in game) and a mod picker (folders under `workspace\`, written through `skills/dayz-init/state.py`) so switching mods costs no tokens. | Mod panel review |
| Panel (liked): a scope lock indicator ("Edits locked to <Mod>" from `dayz-active-scope.json`, amber when it differs from the active mod) and environment detail behind the P: dot from the last preflight (Tools, vanilla data, `P:\Mods` junction, search index age). | Mod panel review |
| Panel (liked): a Work card showing the last `/dayz-route` decision and, during an orchestrator run, the task table, current wave and gate verdicts (via the mod API's tool hook, or a `dayz-progress.json` the orchestrator writes). | Mod panel review |
| Panel first step: `--json` on `skills/dayz-init/hub_status.py` (mod, mod folder exists, PBO age, servers, Diag state, needs, last gate, scope lock) so the panel, status line and `/dayz-init` read one source. | Mod panel review |
| Panel bugs: a failed gate card shows the health page path instead of the failure (read `gate.py --json`); Check in game fails after the panel's own Launch (pass `--yes`); Launch and Check in game ignore CF/Dabs/Expansion dependencies; active-mod dot stays green when the mod folder is gone. | Mod panel review |
| Panel fixes: refresh status on focus or a 15-30 s interval; neutral dot for "stopped"; cancel or elapsed time on long runs; keep API keys in Windows Credential Manager instead of the panel store; cache the home folder and Python path; move Deep dive off hotkey `v`. | Mod panel review |
| Panel quick wins: a Show output toggle (last 200 lines); dim buttons that cannot run with the reason, and a Mount button on the red P: dot; a Last checks row (build and gate verdict with age, from `.server\!Health\<Mod>\results\`); open `health.html` after Health; Fix in chat on red cards; relabel Build vs Build + check and add a Build, check, launch chain. | Mod panel review |
| A table of the `DayZAnimalBehaviourSlot` and `DayZAnimalBehaviourAction` values (`P:\scripts\3_game\entities\dayzanimalinputcontroller.c:2` and `:26`) and which animal templates use each, for `creatures.md` | Code check |
| The animal path filters in `PathGraphFilters` (`DeerOnRun`, `RoeDeerOnRun`, `CowOnRun`, `GoatOnRun`, `ChickenOnRun`, `WolfOnHunt`, `WolfOnOuterCircle`, `NoJumping`, `P:\DZ\data\aiconfigs\config.cpp:413` to `:656`) with their flags and costs, next to the infected table in `behaviour-config.md` | Code check |
| The NBC infected classes that override `ResistContaminatedEffect()` (`P:\scripts\4_world\entities\creatures\infected\zombiemalebase.c:212` to `:245`), as the vanilla model for infected that ignore gas zones | Code check |
| How `InfectedSoundEventHandler` picks voice sounds per mind state (`zombiebase.c:505` onward) for a custom infected with its own voice sets | Code check |
| The creature bite damage spheres in `CfgDamages` (`WolfBiteDamage`, `DogBiteDamage` and the rest, `P:\DZ\AI\config.cpp:6944` onward) and how `AddDamageSphere` uses them, for a custom predator | Code check |
| A side by side of the Enoch, Sakhal and Nasdara `cfgenvironment.xml` territories (`P:\DZ\worlds\<map>\ce\`) for a custom map author | Code check |
| The full `ZombieBase` finisher and backstab hooks (`IsBeingBackstabbed`, `SetBeingBackstabbed`, `OnRecoverFromDeath`, `zombiebase.c:1060` to `:1102`) for mods that change stealth kills | Code check |
| A table of every Badlands house that can be rebuilt (`P:\DZ\structures_takistan\Residential\config.cpp`) with its door entries and numbered lock slots (`Att_CodeLock1_Wood` and the rest) | Code check |
| A topic file on `class Construction` for houses that can be rebuilt (`rebuild_door1`, `door1_wood`, `physics_geom_names[]`, `essential_attachments[]`) and how `Rebuilding` uses it | Code check |
| The `GUIInventoryAttachmentsProps` groups that show a house's lock slots per door, with icons and `selection` (`structures_takistan\Residential\config.cpp:946` onwards) | Code check |
| `class Navmesh` `TransformParts` on doors and gates (`hideAnimationSource`, `transformAnimationSource`), and the fence's `UpdateNavmesh` call after its gate turns | Code check |
| Which four wolf instance lines the dobermann instance leaves out, and what the dog plays for them | Code check |
| What the `bool` in `DoorFinishParams` means, found by logging the door finish events in game | Code check |
| A table of the `DayzPlayerItemBehaviorCfg` setters (one handed, two handed, heavy, firearms) and what each sets, for `items-in-hands.md` | Code check |
| The full `VehicleAnimInstances` list and the seat animation types a mod vehicle returns from `GetSeatAnimationType`, cross linked from `get-in-sides.md` to the vehicles pack | Code check |
| An `.anm` `EVNT` chunk reader in `scripts/tools/dayz-animation-formats/` (frame, name, string, value per event), so event frames can be checked on `P:\` without DayZATool | Code check |
| Read the key data of `w_*_states.anm` with a script so the per weapon state frame counts in `weapon-anim-authoring.md` can be cited | Code check |
| Whether a passenger seat can also use directional boarding (`GetSeatAnimationTypeDirectional` for seats other than the driver), noted in `get-in-sides.md` | Code check |
| A short reference for ambient sound config, `CfgEnvSounds` and `CfgEnvSpatialSounds` (`P:\DZ\sounds\hpp\config.cpp:509018` and `:509047`), for a map mod that needs its own ambience | Code check |
| Step and impact sound tables for a custom surface: how a new `CfgSurfaces` class gets entries in `CfgStepSoundTables` and `CfgImpactSoundTables` (`P:\DZ\sounds\hpp\config.cpp:386921` and `:506974`) | Code check |
| List the other weapon shot sound arrays next to `soundSetShot[]`: `soundSetShotExt[]`, `soundSetShot1st[]`, `soundSetShotExt1st[]` (`P:\DZ\weapons\firearms\akm\config.cpp:98` to `:146`) and when the engine picks each | Code check |
| Find out whether a mod can add its own effecter class (a subclass of `ParticleEffecter`, `P:\scripts\3_game\effectmanager.c:775`) without a `CfgVehicles` entry; vanilla effecters have none on `P:\DZ` | Code check |
| Split `dayz-particles/references/vanilla-particle-catalog.md` (589 lines) under the 400 line ceiling | Code check |
| Bring `dayz-particles/references/emat-format-reference.md` to house style: `---` rules, arrows in code comments, hard wrapped prose | Code check |
| Note the `InventoryItemType` debug define `ITEM_SOUND_EVENTS_DEBUG` (`P:\scripts\3_game\inventoryitemtype.c:2`) as the way to see why an attach or detach sound did not register | Code check |
| List the `serverDZ.cfg` keys that vanilla script reads with `ServerConfigGetInt` (`disableBaseDamage`, `disableContainerDamage`, `disableRespawnDialog`, `disablePersonalLight`, `lightingConfig`, `enableDebugMonitor`, the `adminLog*` keys; `P:\scripts\3_game\cfggameplaydatajson.c:47` to `:79`, `P:\scripts\4_world\plugins\pluginbase\pluginadminlog.c:44` to `:47`) in `conventions/server.md` | Code check |
| Note in the persistence pack that `EntityAI.OnCEUpdate()` is marked obsolete in 1.30 in favour of `OnCEIterate(float currentTime, float elapsedTime)` (`P:\scripts\3_game\entities\entityai.c:4924` to `:4925`) | Code check |
| Restyle the vendored `enscript-style/` files to house style (drop `---` rules, bold capital warnings and the arrow in `best-practices.md`) | Code check |
| Re-check the Expansion and Community Framework citations in `enscript-style/debugging-and-errors.md` and `enscript-style/naming.md` against `P:\Mods` | Code check |
| `/dayz-p3d-audit` could warn (not fail) when a model whose bounding box centre sits far from its origin has no `ce_center` memory point, since `GetCenter` then falls back to the origin raised by 0.2 m | Code check |
| `/dayz-lint` could compare each `CfgMods` `files[]` path with the case of the folder on disk, as vanilla Frostline writes `DZ/data_sakhal/scripts/4_World` | Code check |
| List the other launch parameters vanilla script reads in `diag-direct-launch.md`: `-stresstest` and `-doAimLogs` (`P:\scripts\3_game\dayzgame.c:1045` to `:1053`), `-loadingTest` (`:746`), `-roboclient` under `#ifdef ROBOCLIENT` (`:1084` to `:1090`) and `-timeAccel=<on>,<big>,<small>` (`P:\scripts\4_world\plugins\pluginbase\plugindiagmenu\plugindiagmenu.c:1401` to `:1410`) | Code check |
| Note that `GetCLIParam` and `IsCLIParam` (`P:\scripts\1_core\proto\ensystem.c:128` and `:141`) read launch parameters too, beside `CommandlineGetParam` | Code check |
| Once an in-game run confirms vanilla's `-autotest` harness works on a diag client, ship a minimal example suite beside `assets/autotest-mod/` | Code check |
| Note that `AutoTestFixture.SpawnEntityAI` ignores its `flags` parameter and always places on surface (`P:\scripts\3_game\autotest\autotestfixture.c:30` to `:34`) | Code check |
| Have `/dayz-lint` flag a backslash in a `CfgMods` script module `files[]` entry (`dayz-1-30-server-measured.md` says lint does not yet) | Code check |
| Add the `ErrorEx` severity levels and `PrintFormat` (`P:\scripts\1_core\proto\endebug.c:83` and `:108`) to the probe rules in `debug-protocol.md` | Code check |
| List the remaining `LogManager` switches (`-doInvReservLog`, `-doInvHFSMLog`, `-doQuickbarLog`, `-doBaseBuildingLog`, `-doRadioGameplayLog`) and the `ENABLE_LOGGING` define that forces `-doLogs` (`P:\scripts\3_game\tools\debug.c:718` to `:738`) in `test-loop.md` | Code check |
| Note in `server-and-mission-config.md` that `CfgPlayerRestrictedAreaHandler.LoadData` takes its file list from `cfggameplay.json` only when `enableCfgGameplayFile` is set, else from the world's default paths (`P:\scripts\3_game\cfgplayerrestrictedareahandler.c:11` to `:22`) | Code check |
| Note that the client prepare event also syncs `CfgPlayerRestrictedAreaHandler` and `CfgBunkerBroadcastHandler` beside cfggameplay (`P:\scripts\5_mission\mission\missionserver.c:320` to `:322`) | Code check |
| In `server-load-and-dummy-bots.md`, describe the other `ROBOCLIENT` hooks in `PlayerBase` (`m_Bot.CheckForEnemies`, `m_Bot.OnUpdate`, `GetRespawnData` at `playerbase.c:1421`, `:3513`, `:4198`) | Code check |
| A small worked example of a vanilla `-autotest` run (config JSON, one suite, reading the XML report) once it has been tried in game | Code check |
| An audit WARNING when the Geometry LOD box is much larger than the Visual LOD on a deployable, since that box is the hologram footprint (`hologram.c:1067`, `:566`) | Code check |
| A small offline reader for ODOL headers (LOD resolutions, named property strings) so vanilla LOD and `autocenter` counts can be rerun after each game update | Code check |
| Find out what the engine reads from the `2e13` LOD of `boat_01.p3d` and the Takistan shipping containers | Code check |
| Let `/dayz-pack-texture` accept the rarer TexConvert suffixes vanilla uses (`_can`, `_nofhq`) | Code check |
| Document the remaining hologram checks (`IsCollidingPlayer`, `IsClippingRoof`, `IsCollidingAngle`, `HeightPlacementCheck`) and their `cfggameplay.json` switches for placed objects | Code check |
| `/dayz-add-server` could write `enableCfgGameplayFile = 1;` into its default `serverDZ.cfg`, so the mission's `cfggameplay.json` is read without a manual edit (`P:\scripts\3_game\cfggameplayhandler.c:53`) | Code check |
| `/dayz-build-imageset` could also build an `@2x` atlas and write it as a second `mpix 1` texture, as vanilla does (`P:\gui\imagesets\playstation_buttons2.imageset:9` to `:12`) | Code check |
| `/dayz-edit-types` could warn when the class does not inherit from a Central Economy root class in `cfgeconomycore.xml` (`P:\DZ\worlds\chernarusplus\ce\cfgeconomycore.xml:9` to `:18`) | Code check |
| `/dayz-edit-types` could say how to load a mod's own types file through a `<ce folder>` entry in `cfgeconomycore.xml`; vanilla has no such entry, so it needs an in-game check first | Code check |
| `/dayz-layout-preview` could cite a vanilla `GridSpacerWidgetClass` with `Padding`, `Margin`, `Columns` and `Rows` (used in `P:\gui\layouts\camera_tools\camera_tools.layout`) next to its spacer rules | Code check |
| A short table of `ActionBase` overridables beyond input type (`IsFullBody`, `IsUsingProxies`, `CanBePerformedFromQuickbar`, `UseMainItem`, `MainItemAlwaysInHands`, `IsDeploymentAction`; `actionbase.c:294` to `:758`) in `depth/actions-mission-api.md` | Code check |
| List the other `ActionInput` classes (`DropActionInput`, the vehicle horn inputs, `NoIndicationActionInputBase`; `actioninput.c:578` to `:760`) and when vanilla uses each | Code check |
| Note `EntityAI.DeferredInit()` (`entityai.c:277`) and `EEHitByRemote` (`:1153`) in the lifecycle table of `depth/api-patterns.md` | Code check |
| Give the full `CfgSlots` rebuild slot list in `depth/config-cpp.md` as a table with each `stackMax` (`P:\scripts\config.cpp:2915` on) | Code check |
| Restyle `enscript/README.md` and `integrations/central_economy.md` to the house style (title, arrow and em dash in the symptom heading, `---` rules, numbered headings, bold) | Code check |
| Document `ScriptInvoker.Insert` and `Remove` flags (`EScriptInvokerInsertFlags`, `EScriptInvokerRemoveFlags`; `P:\scripts\2_gamelib\tools.c:120` and `:122`) in `depth/server-side-gates.md` | Code check |
| Count which `storageCategory` values vanilla uses (1, 2, 3, 4, 7, 9, 10 under `P:\DZ`) and what classes carry each, since no script reads the key | Code check |
| Add a `CCIDummy` row (item not null) to the item condition table in `patterns/actions.md` (`P:\scripts\4_world\classes\useractionscomponent\itemconditioncomponents\ccidummy.c`) | Code check |
| Explain `RegisterPluginDebug` and `RegisterPluginDiag` next to `RegisterPlugin` in `integrations/vanilla_plugins.md` (`P:\scripts\4_world\plugins\pluginmanager.c:242` to `:256`) | Code check |
| Cover the three Workbench modules not in `references/workbench_api.md`: `AnimEditor`, `GameViewer`, `ParticleEditor` (`P:\scripts\1_core\workbenchapi\modules\`) | Code check |
| A short example of sending a JSON config to clients with `JsonFileLoader.MakeData` and `LoadData` over `ScriptRPC` | Code check |
| Measure which defines a DayZDiag build sets; `P:\scripts\staticdefinesdoc.c` has no row for it | Code check |
| Measure the `ErrorCategory` numbering in a connect error (the script enum counts `Unknown` as 0, the vanilla comment examples count one higher) and settle the wording in `references/api_game.md` | Code check |
| Note the `FEATURE_NETWORK_RECONCILIATION` and `FEATURE_CURSOR` defines in `references/language_compile.md` once their effect on mods is known (`P:\scripts\1_core\defines.c:59` and `:64`) | Code check |
| Recheck the CF, Expansion and LBmaster citations against `P:\Mods\` (it holds `@CF` and the `@DayZ-Expansion` mods; no LBmaster mod is installed there) | Code check |
| Re-run the named property scan of `named-properties.md` over all 10,626 models, Takistan included, with one documented method, and replace the counts that are now scoped to the 8,256 models outside the Takistan folders | Code check |
| Re-run the `Multi` material stage and texGen counts of `multi-rvmat-texturing.md` over all 2,680 files instead of the 1,960 outside the Takistan folders | Code check |
| A short note on the car effect memory points (`ptcExhaust_start`, `ptcExhaust_end`, `ptcEnginePos`, `ptcCoolantPos`, `drown_engine`, `P:\scripts\4_world\entities\vehicles\carscript.c:170` and `:276` to `:368`) in `memory-points.md`, pointing at the vehicles pack | Code check |
| What a buildable well model needs: `Land_WaterWell_Brick` gives water only once its `roof` construction part is built (`P:\scripts\4_world\entities\building\land_waterwell_brick.c:3` to `:17`) | Code check |
| Check in game whether `-cacheP3D=1` writes `.p3dcache` files beside an unbinarized `.p3d`, then cite the result in `dayz-1-30-models.md` | Code check |
| A repo script that rescans `P:\DZ` for the `uvSource`, Super, Multi and `uvTransform` counts in `uv-mapping.md`, so the numbers can be refreshed after each game update | Code check |
| Note `ProxyHide` (`simulation="alwayshide"`, `P:\bin\config.cpp:2290`) and the other engine proxy bases in `P:\bin\config.cpp` `CfgNonAIVehicles` in `proxy-attachment-config.md` | Code check |
| Make the 3D viewer read `simpleHiddenSelections[]` and offer a show or hide toggle per entry | Code check |
| Make the p3d inspector flag a hidden selection swap whose index would be -1 (name not in `hiddenSelections[]`) | Code check |
| Document the other `cfggameplay.json` base building switches (`disablePerformRoofCheck`, `disableIsCollidingCheck`, `disableDistanceCheck`, `P:\scripts\3_game\cfggameplaydatajson.c:276` to `:278`) beside the falling switches | Code check |
| Explain `RequiredPartsVariants` and `partVariants` on rebuild parts (`constructionparttyped.c:274` to `:310`) with a vanilla house example | Code check |
| A short note on `RebuildingSpawner` (diag only) as a test tool for rebuildable houses (`P:\scripts\4_world\classes\basebuilding\rebuildingspawner.c`) | Code check |
| List every hologram check in `Hologram.EvaluateCollision` (`P:\scripts\4_world\classes\hologram.c:446`) as a placement triage table | Code check |
| Note that `DigitalCodeLock_Bunker` takes its PIN length from the bunker broadcast config (`P:\scripts\4_world\entities\itembase\codelock.c:588` to `:600`) | Code check |
| Trace `physics_geom_names`, `override_animsource_names` and `proxyroadway_names` on rebuild parts to what they switch in the model | Code check |
| Rewrite the example table cells of the deep-audit files (third-party mod `file:line` values) with a `MyMod` prefix so citation scans stop matching them to vanilla files | Code check |
| A table of the other vanilla `Trigger` subclasses (`EffectTrigger`, `ContaminatedTrigger`, `TrapTrigger`, `BarbedWireTrigger`, `GeyserTrigger`) and what each overrides, in `scripted-triggers.md` | Code check |
| A short note on the `AreaDamageManager` and its damage components (`P:\scripts\4_world\classes\areadamage\`) as their own topic file, since `damage-pipeline.md` only names their default ammo | Code check |
| The crew damage formula in `CarScript.CheckContactCache` (impulse divided by body mass, times 1000, `carscript.c:1292`) cross-linked from `contact.md` to the vehicles pack | Code check |
| What `doPhxImpulse=1` on the `TransportHit` ammo does; no script reads it, so it needs an in game test | Code check |
| When vanilla uses `ObjIntersectIFire` (melee aim) versus `ObjIntersectFire`, with a probe example for each in `collision-lods.md` | Code check |
| Find out whether the engine reads the `CarScript` config keys `selectionDashboard`, `selectionLightFrontL`, `selectionLightFrontR` and `selectionBrakeLights` (`P:\DZ\vehicles\wheeled\config.cpp:260` to `:263`); no script on `P:\scripts` names them | Code check |
| Explain how a dyed item's procedural color (`ItemBase.SetColor`, `barrel_colorbase.c:603`) reaches other clients, next to the `SetObjectTexture` sync note in `runtime-material-swaps.md` | Code check |
| Measure the ground and sky halves of the other 17 environment maps in `P:\DZ\data\data\` for the table in `rvmat-cookbook.md` | Code check |
| Say what the `.paa` `FLAG` tag holds (925 vanilla `_co` and most `_ca` files carry it) in `paa-file-layout.md` | Code check |
| List the Takistan penetration materials in `P:\DZ\data_takistan\data\penetration` beside the `dz\data\data\penetration` set in `rvmat-cookbook.md` | Code check |
| Note that the vanilla rock `rock_apart1.rvmat` holds `color(1,1,1,1,Co)` in Stage9 where most Multi materials hold an `_mc` or the MC placeholder | Code check |
| Table of the login queue and login time screens: which layout each loads (`dialog_queue_position.layout` at `P:\scripts\3_game\dayzgame.c:129`) and which widgets their scripts look up, for mods that restyle them | Code check |
| Short note on the loading screen hint panel (`UiHintPanelLoading`, `P:\scripts\3_game\gui\hints\uihintpanel.c:293`, created in `LoadingScreen.ShowEx` at `dayzgame.c:837` to `:846`) and how a mod replaces the hints | Code check |
| Note in `layout-geometry.md` that a `SpacerBase` scriptclass also calls `m_root.SetHandler(this)` (`P:\scripts\3_game\gui\spacers\spacerbase.c:21`), so it takes the root's events from any other handler | Code check |
| In game test: can a `modded class ChatInputMenu` read the vanilla `private` field `m_edit_box`; record the answer in `chat-ui.md` | Code check |
| In game test: does `MB_PRESSED_MASK` compile in a mod script, given its script declaration is commented out (`P:\scripts\1_core\proto\ensystem.c:319`) | Code check |
| Document `UIScriptedMenu.OnVisibilityChanged(bool isVisible)` (`P:\scripts\3_game\tools\uiscriptedmenu.c:26`) for menus that pause work when the game window loses focus | Code check |
| A short recipe for `UIScriptedWindow` and `UIManager.OpenWindow`, the scripted windows that menus pass events to (`P:\scripts\3_game\tools\uimanager.c:178`) | Code check |
| A worked example of a world marker placed with `GetScreenPosRelative` on a proportional widget (`P:\scripts\3_game\global\game.c:965`) | Code check |
| A usage example for the `WidgetEventHandler` singleton (`RegisterOnClick` and friends) in `vanilla-menus-map.md` | Code check |
| Note the runtime `LoadWidgetImageSet(string filename)` and `ReloadTexture(string path)` globals with a test of whether a mod imageset can be loaded late | Code check |
| Note `IsCreatedHidden()` and the `FEATURE_CURSOR` branch of `LockControls` (`P:\scripts\3_game\tools\uiscriptedmenu.c:80` to `:85`) | Code check |
| Document `Transport.GetTransportCameraDistance()` and `GetTransportCameraOffset()` (`P:\scripts\3_game\vehicles\transport.c:652` and `:660`), which the bikes override to set their third person camera, as a per vehicle camera tuning hook | Code check |
| Say what `SetEnginePos(...)` sets, which `Offroad_02` and `Motorbike_01` call in their constructors (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:36`), and how it relates to the `drown_engine` point | Code check |
| Note the vanilla typo `TailRighttOnly` in the deprecated light block (`P:\scripts\4_world\entities\vehicles\carscript.c:2910`); it has no runtime effect because the block is never called | Code check |
| Label every RFFS short citation (`RFFSHeli_Core.c:N`) in the aviation files the same way, "in RFFS's scripts", so the citation scan stops reporting them as missing vanilla files | Code check |
| A small script that re-checks only the `transport.c` and `carscript.c` line numbers of the vehicle pack after each DayZ update, since most drift in this slice came from those two files | Code check |
| Re-read the `Motorbike_01` and `Motorbike_02` ODOL tables once an ODOL version 56 reader backend is available; the files on `P:\` changed size since the tables were made | Code check |
| Document the `MotorbikeEngineSoundState` states and how `HandleEngineSound` picks each sound set (`motorbikescript.c:42`, `:1476`) | Code check |
| Table of `VehicleAnimInstances` values with the vanilla vehicle that uses each (`vehicleaniminstances.c`) | Code check |
| Note the motorbike debug modes (`EMotorbikeDebugMode`, `DIAG_DEVELOPER` only) for test runs | Code check |
| List which vanilla cars override `HasGangedTailAndBrakeLights` (only `Offroad_02`, `offroad_02.c:68`) and what changes visually | Code check |
| Explain `GetWeightCoef()` on the bikes (`motorbike_01.c:84` returns 0.5) once its reader is found | Code check |
| A table of the `GetVehicleType()` strings (`"VehicleTypeBoat"`, `"VehicleTypeMotorbike"`, the car one) and the HUD class each selects through `m_VehicleHudMap` in `P:\scripts\5_mission\gui\ingamehud.c`, for a mod vehicle that wants its own HUD | Code check |
| List the vanilla `m_VehicleContactDamageCoef` and `m_CrewContactDamageCoef` values per car next to the bikes' (0.03 and 0.018, 0.035 and 0.012, `inheritedmotorbikes\motorbike_01.c:5` and `:6`, `motorbike_02.c:5` and `:6`) as a starting point for tuning crash damage | Code check |
| Check in game whether `BoatScript.EOnSimulate` runs although its constructor sets only `POSTSIMULATE` and `FRAME` (`P:\scripts\4_world\entities\vehicles\boatscript.c:95` and `:96`), and record the answer in `runtime-state-and-sync.md` | Code check |
| Note the refuel reach, `GetActionDistanceFuel()` returning 1.5 m (`P:\scripts\3_game\vehicles\transport.c:467` to `:470`), beside the `refill` memory point rule | Code check |
| Describe the diag car autopilot (`ECarDebugMode`, `CarScript.OnInput` under `DIAG_DEVELOPER`, `P:\scripts\4_world\entities\vehicles\carscript.c:1045` to `:1207`) as a vanilla way to drive a car in a diag test | Code check |
| Say that the boat engine repair also needs `Blowtorch.HasEnoughEnergyForRepair` and that `Blowtorch` is where it is added (`P:\scripts\4_world\entities\itembase\blowtorch.c:115`), so a mod boat's engine repair needs no action registration of its own | Code check |
| The `isSuicideWeapon` key that `Weapon_Base.CanBeUsedForSuicide` checks (`P:\scripts\4_world\entities\firearms\weapon_base.c:2212`; set on the flare gun, `P:\DZ\weapons\pistols\flaregun\config.cpp:36`) as a row in the `weapon-config.md` key table | Code check |
| The 1.30 gold retexture variants (`AKM_Gold`, `Magnum_Gold`, `SawedoffMagnum_Gold` under `P:\DZ\weapons_takistan\`) as a second worked example of a material-only variant with `RefTexsMats[]` in `weapon-config.md`, "Damage" | Code check |
| A note that `P:\DZ\weapons_takistan\config.cpp` redefines `class Mode_Safe: Mode_SemiAuto` at the config root with an empty `magazines[]`, and what that means for mods that declare `Mode_Safe` | Code check |
| A table of `ShoulderDistance` values across the vanilla pistols and stocked rifles, to pick a starting value for a mod gun's lift check | Code check |
| The fire mode `recoil` strings the 1.30 guns reuse (`recoil_fal` on the SCAR-L, `recoil_cz527` on the Lee-Enfield, `recoil_rak` on the MP18, `recoil_1911` on the Luger) added to the `recoil-fire-modes.md` note that those strings name no class | Code check |
| The jam sync juncture (`DayZPlayerSyncJunctures.SendWeaponJamChance` and its client handler) traced end to end as a short section for mods that change jamming at runtime | Code check |
| Explain `transferToAttachmentsCoef` in a wearable's `GlobalHealth` (0.5 on `PlateCarrierVest`, `P:\DZ\characters\vests\config.cpp:68`): how much hit damage passes on to pouches and holsters | Code check |
| Add the eyewear `isStrap` key to the slot exclusion table: with it, `noHelmet` and `noMask` block the head strap variants instead (`P:\scripts\3_game\entities\entityai.c:4474` to `:4484`) | Code check |
| Check why `DZ_Characters_Nasdara_Tops`, `_Pants` and `_Shoes` declare `MaleTorso_Base`, `MaleLegs_Base`, `MaleFeet_Base` and every survivor body part again (`P:\DZ\characters_takistan\tops\config.cpp:37`), and what that means for a mod that edits body parts | Code check |
| A short note on `absorbency`, `heatReduction` and `coldReduction` on `Inventory_Base` (`P:\DZ\data\config.cpp:3189` onwards) and whether any clothing uses them | Code check |
| Document what `HeadGearProtectionAgainstSun` returns when a worn clothing item that is not headgear comes first in the attachment loop (`P:\scripts\4_world\classes\environment\environment.c:2042` to `:2057`) | Code check |
| List the helmets that override `GetProtectionLevel` or `GetCachedEquipmentCategory` (dirt bike, Gorka, moto, welding mask, great helm) and what each returns | Code check |
| A wearer note on the `Nasdara` infected classes (`ZmbM_taki*`, `P:\DZ\characters_takistan\zombies\config.cpp`) and the gear they spawn with | Code check |
| Add a custom agent recipe: `eAgents` is a bit mask capped at 32 agents and must match the config side (`P:\scripts\3_game\enums\eagents.c:1`), plus registration in `PluginTransmissionAgents` | Code check |
| Document the Nasdara `cfggameplay.json` fields beyond sandstorm and bunker broadcast (`environmentMinTemps`, `environmentMaxTemps`, placement checks) in a world gameplay file | Code check |
| Read the two 1.30 screen effect widgets (`gewidgetsmetadataeyeveins.c`, `gewidgetsmetadatasquinting.c`) and say what drives each | Code check |
| List the Nasdara `env\` animal territory files (monitor, mouflon, dobermann and shepherd) next to `_shared/ai/animal-territories.md` | Code check |
| Explain `PlayerSandstormData` state bits and the in-game script console weather tab that hooks `GetSandstormStartSI` (`P:\scripts\5_mission\gui\scriptconsoleweathertab.c:434`) as a debugging aid | Code check |
| Describe the irrigation tunnel trigger layout on Nasdara (653 triggers) as a worked example of a long tunnel built from breadcrumbs | Code check |
| Note that phase 4 heat stroke and silicosis pass uninitialised `vignette`, `fadeOut` and `interval` to the faint symptom while the player is unconscious (`heatstroke.c:357` to `:369`) | Code check |
| Split `skills/_shared/figma-to-dayz-rules.md` (480 lines, over the 400 line ceiling) into a format file and a translation file, indexed in `skills/_shared/README.md` | Code check |
