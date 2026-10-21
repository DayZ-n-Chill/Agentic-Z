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
- Known group template names in vanilla are the animal ones: `DZDeerGroupBeh`, `DZdomesticGroupBeh`, `DZSheepGroupBeh`, `DZWolfGroupBeh` and `DZAmbientLifeGroupBeh`, named by `defaultGroupTemplateName` in `P:\DZ\AI\config.cpp` (for example `:589`, `:5424`). No vanilla file names an infected group template, and no vanilla script calls `CreateGroup`.

## Waypoint patrols for infected

`BehaviourGroupInfectedPack` (`P:\scripts\3_game\ai\aigroupbehaviour.c:19`) is the one group behaviour with a script API:

- `SetWaypoints(array<ref BehaviourGroupInfectedPackWaypointParams> waypointParams, int waypointDefaultIndex, bool forwardDirection, bool loop)` (`:27`). Each waypoint is a centre and a radius (`BehaviourGroupInfectedPackWaypointParams`, `:7`). The vanilla note says `loop` true cycles the waypoints and false patrols them (`:25`); watch the in game test to see how a patrol walks after the last point.
- `SetWaypointsTraverseDirection`, `SetWaypointsLoop` and `SetCurrentWaypoint` (`:29` to `:31`) change the route while it runs.
- To use it you cast `group.GetBehaviour()` to `BehaviourGroupInfectedPack`. Because no vanilla file names the template that creates this behaviour, the cast can return null. Check for null, log it, and fall back to the steering pattern below. The in game test must prove the route works before you report it as done.

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

Large community AI mods build human NPCs by spawning a player class character that no client owns, then driving it every step from a server side state machine through overrides like these, with their own path following and target choice. That is a big system with many edge cases (inventory, weapons, network ownership, persistence). Agentic-Z never copies any of it. When the user asks for human guards:

1. Say plainly that vanilla has no human AI and that a from scratch human AI is a large project.
2. Offer the infected or animal based guard first (a custom infected with its own template and a patrol route), which runs on the vanilla engine AI.
3. If the user still wants humans, plan it as its own milestone with the script lead and the architect, and write every class fresh against the vanilla hooks above. Whether a player class character can be created and simulated without a client must be proven in the in game test first; no vanilla file shows it.
</content>
</invoke>
