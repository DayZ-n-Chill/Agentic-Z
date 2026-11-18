# Patrols and guards: groups, navmesh and human AI

What vanilla gives you for creatures that walk a route or hold a post, and what it does not give you for human AI.

## What vanilla has and lacks

- Vanilla ships engine AI for infected and animals only. Their config parent `DZ_LightAI` (`P:\DZ\data\config.cpp:3079`) has exactly two children: `DayZInfected` and `AnimalBase` (see `creatures.md`).
- There is no human AI class, no bandit or soldier NPC, and no script brain that walks a human character along a path. A human guard is your own system built from the pieces below.
- The behaviour graph for infected and animals is native. Script tunes it through config (`behaviour-config.md`) and steers it through input controller overrides.

## AI world, groups and agents

- `GetGame().GetWorld().GetAIWorld()` returns the `AIWorld` (`P:\scripts\3_game\global\world.c:116`).
- `AIWorld.CreateGroup(string templateName)` (`P:\scripts\3_game\ai\aiworld.c:79`) makes a group with a group behaviour; `CreateDefaultGroup()` (`:83`) makes one with none; `DeleteGroup(notnull AIGroup group)` (`:87`) destroys the group and every agent in it. The engine deletes empty groups by itself.
- `AIGroup` (`P:\scripts\3_game\ai\aigroup.c:1`): `AddAgent`, `RemoveAgent` and `GetBehaviour()`. The vanilla note says to remove an agent from its old group before adding it to a new one, and that an empty group is deleted on the next frame (`aigroup.c:6` to `:10`).
- `AIAgent` (`P:\scripts\3_game\ai\aiagent.c:1`): `SetKeepInIdle(bool enable)` and `GetGroup()`. Get the agent with `DayZCreatureAI.GetAIAgent()` (`P:\scripts\3_game\entities\dayzanimal.c:193`).
- `DayZCreatureAI.InitAIAgent(AIGroup group)` (`dayzanimal.c:207`) starts the AI of a creature created without it, so you choose its group. `DestroyAIAgent()` (`:208`) removes it.
- Group templates are defined in `class GroupBehaviourTemplates` (`P:\DZ\data\aiconfigs\config.cpp:77`, addon `DZ_data_aiconfigs`). The animal ones are `DZAmbientLifeGroupBeh` (`:79`), `DZWolfGroupBeh` (`:87`), `DZDeerGroupBeh` (`:151`), `DZdomesticGroupBeh` (`:201`) and `DZSheepGroupBeh` (`:252`). Animal templates in `P:\DZ\AI\config.cpp` point at them with `defaultGroupTemplateName`, for example `DZDeerGroupBeh` (`:589`) and `DZWolfGroupBeh` (`:5424`).
- The infected pack template is `DZInfectedPackBeh` with `type="InfectedPack"` (`P:\DZ\data\aiconfigs\config.cpp:304`). Its keys include `groupRadius=10` (`:311`) and `agentPathLength=100` (`:313`). No vanilla script calls `CreateGroup` with it.
- The bear template `BlissBearGroupBeh` is in a second addon, `DZ_data_aiconfigs_bliss` (`P:\DZ\data_bliss\aiconfigs\config.cpp:9`).
- Each template has a `type` that selects the engine behaviour, and life cycle classes that name the kind of mission zone the group goes to with `zoneType`. The `type` and zone types of every vanilla template, and how the mission binds territories to them, are in `animal-territories.md` section 5.
- The Nasdara data of 1.30 has two more templates, `DZMouflonGroupBeh` (`type = "DomesticHerbivores"`) and `DZDogGroupBeh` (`type = "Predators"`, `zoneType = "HuntingGround"`); not yet checked on `P:\`. `P:\` holds other Nasdara data (the mouflon instance `mouflonskeleton_animinstance.asi` in the herbivores graph folder, the dog skeletons `canis_familiaris_dobermann_skeleton.xob` and `canis_familiaris_german_shepherd_skeleton.xob` in `P:\DZ\anims\cfg\skeletons.anim.xml:1047` and `:1121`), but no config defines these two group templates. A custom map that wants a new herd or pack copies or inherits a group template in its own config instead of rebuilding the behaviour in script.
- The two Nasdara templates as read in the 1.30 Nasdara data (`DZ\data_takistan\aiconfigs\config.cpp`, `GroupBehaviourTemplates`; that addon is not on this `P:\`, so every value here is unchecked). `DZMouflonGroupBeh` sets `alertDistributionSpeed` 20, `groupMaxAlertedSpreadRadius` 40, `catchUpTestDelay` 4, `catchUpStartRadius` 30, `catchUpTargetRadius` 12 and `groupRadius` 10, with a graze and rest life cycle and `safeKeeperIntervalMin` and `Max`. `DZDogGroupBeh` sets `alertDistributionSpeed` 10, `catchUpTestDelay` 4, `catchUpStartRadius` 60, `catchUpTargetRadius` 7 and `groupRadius` 10, and its life cycle uses `zoneType = "HuntingGround"` with `siegeAttackCountdownMin` 10 and `Max` 15, `huntAttackCountdownMin` and `Max`, and `safeKeeperIntervalMin` 20 and `Max` 40. The wolf template on `P:\` has the same `type="Predators"` (`P:\DZ\data\aiconfigs\config.cpp:87` to `:148`).

In 1.30 the navmesh file format changed with no backward compatibility, so a custom terrain must regenerate its navmesh for 1.30. The same 1.30 changelog says a navmesh can follow a hide animation source when the object's navmesh config sets one up. Neither is checked on `P:\`; a path that works on a vanilla map and fails on a custom one after the update points at the navmesh first.

## Waypoint patrols for infected

`BehaviourGroupInfectedPack` (`P:\scripts\3_game\ai\aigroupbehaviour.c:19`) is the one group behaviour with a script API:

- `SetWaypoints(array<ref BehaviourGroupInfectedPackWaypointParams> waypointParams, int waypointDefaultIndex, bool forwardDirection, bool loop)` (`:27`). Each waypoint is a centre and a radius (`BehaviourGroupInfectedPackWaypointParams`, `:7`). The vanilla note says `loop` true cycles the waypoints and false patrols them (`:25`); watch the in game test to see how a patrol walks after the last point.
- `SetWaypointsTraverseDirection`, `SetWaypointsLoop` and `SetCurrentWaypoint` (`:29` to `:31`) change the route while it runs.
- To use it, create the group with `GetGame().GetWorld().GetAIWorld().CreateGroup("DZInfectedPackBeh")`, then cast `group.GetBehaviour()` to `BehaviourGroupInfectedPack`. No vanilla script does this, so check the cast for null, log it, and fall back to the steering pattern below. The in game test must prove the route works before you report it as done.

## Steering pattern (our own design)

When no group behaviour fits, steer each creature yourself and let the engine AI take over in a fight:

1. Plan the route on the server once per leg with `AIWorld.FindPath(vector from, vector to, PGFilter pgFilter, out TVectorArray waypoints)` (`aiworld.c:98`). Snap posts and route points to the navmesh first with `SampleNavmeshPosition` (`:122`). `PGFilter` (`:59`) takes `PGPolyFlags` include and exclude masks (`:1`) and per area costs with `SetCost(PGAreaType, float)` (`:67`).
2. In `ModCommandHandlerBefore` of your creature class, while the mind state is calm or disturbed, call `OverrideHeading(true, heading)` and `OverrideMovementSpeed(true, speed)` on the input controller (`P:\scripts\3_game\entities\dayzcreatureaiinputcontroller.c:3`, `:9`). Return false so the vanilla handler still runs.
3. When `GetMindState()` reaches alerted or higher, pass `false` to every override so the engine AI chases and fights. Go back to the route when the state drops to calm.
4. A guard that holds a post is the same pattern with one waypoint and speed 0 when it arrives.

Movement speeds map through the creature's `InputController movementSpeedMapping[]` (`P:\DZ\characters\zombies\config.cpp:81` for infected: 0, 1.5, 2.9, 8.9 for idle, walk, run, sprint). Keep overrides inside that range.

## Human characters

For human patrols there is no vanilla AI, but these hooks exist on the human side:

- `Human.GetInputController()` (`P:\scripts\3_game\human.c:1458`) returns a `HumanInputController` (`:17`) with `OverrideMovementSpeed`, `OverrideMovementAngle`, `OverrideAimChangeX`, `OverrideAimChangeY`, `OverrideRaise` and more (`:253` to `:274`). Each takes a `HumanInputControllerOverrideType` (`:7`): `DISABLED`, `ENABLED` or `ONE_FRAME`.
- `HumanCommandScript` (`human.c:1236`) is a fully scriptable human command, started with `StartCommand_ScriptInst(typename)` (`:1624`). The same ownership warning as the creature version applies (`:1230` to `:1234`).
- `DayZPlayerImplement` has the same three mod hooks as creatures: `ModCommandHandlerBefore`, `Inside` and `After` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2266`, `:2271`, `:2276`).
- A human character class inherits the survivor chain, never the infected or animal one: `SurvivorBase` (`P:\DZ\characters\data\config.cpp:122`), then `SurvivorMale_Base` (`:9138`) or `SurvivorFemale_Base` (`:9192`), as the vanilla bodies such as `SurvivorM_Mirek` (`:9234`) do. That gives the player skeleton and player animations, not an AI. Body parts and the survivor class list are in `skills/_shared/wearables/references/characters.md`.
- `DayZPlayerInstanceType` lists `INSTANCETYPE_AI_SERVER`, `INSTANCETYPE_AI_REMOTE` and `INSTANCETYPE_AI_SINGLEPLAYER`, each commented `temporary!` (`P:\scripts\3_game\dayzplayer.c:1083` to `:1092`); a few vanilla checks still test for them (`P:\scripts\4_world\entities\dayzplayerimplement.c:590`).
- `PlayerBase.OnSpawnedFromConsole()` (`P:\scripts\4_world\entities\manbase\playerbase.c:5281`) puts a server side character with no client on the mission's dummy scheduler (`AddDummyPlayerToScheduler`, `P:\scripts\5_mission\mission\missionbase.c:507`, ticked in `UpdateDummyScheduler` at `:496`). The developer spawn calls it for every spawned `PlayerBase` (`P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:361`).
- Vanilla has a debug bot for player characters in `P:\scripts\4_world\systems\bot\`, with a state machine and states such as hunting and attacking (`bot_hunt.c:15`, `bot_attack.c`). All of it, and the `m_Bot` member on `PlayerBase`, is compiled only under `#ifdef ROBOCLIENT` (`bot.c:1`, `P:\scripts\4_world\entities\manbase\playerbase.c:237` to `:239`). Which builds define `ROBOCLIENT` is not checked on `P:\`; do not ship code that depends on it. Its movement state shows the steering pattern for a human: it overrides speed and angle with `ONE_FRAME` on every update (`P:\scripts\4_world\systems\bot\bot_movementrandomizer.c:38` to `:39`).
- Measured on a 1.30 Diag server (an in game test, not checkable on `P:\`): a survivor created on the server with `CreateObjectEx` and `ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_EQUIP_ATTACHMENTS`, then `OnSpawnedFromConsole()`, moved under that debug bot with no client connected, at sprint speed on land, for up to 100 such characters on one server. The headless client switch crashed in the same build.

Large community AI mods build human NPCs by spawning a player class character that no client owns, then driving it every step from a server side state machine through overrides like these, with their own path following and target choice. That is a big system with many edge cases (inventory, weapons, network ownership, persistence). Agentic-Z never copies any of it. When the user asks for human guards:

1. Say plainly that vanilla has no human AI and that a from scratch human AI is a large project.
2. Offer the infected or animal based guard first (a custom infected with its own template and a patrol route), which runs on the vanilla engine AI.
3. If the user still wants humans, plan it as its own milestone with the script lead and the architect, and write every class fresh against the vanilla hooks above. Whether a player class character can be created and simulated without a client must be proven in the in game test of the user's own build first. Vanilla shows the scheduler path above and one measured test saw it work under the debug bot, but no vanilla file shows a shipped human AI doing it.

For the brain itself (a sleeping state, entering and leaving combat, seeing a target, costed paths, spreading a squad over targets) read `design-ideas.md`; the code is still written fresh against the vanilla hooks above.
