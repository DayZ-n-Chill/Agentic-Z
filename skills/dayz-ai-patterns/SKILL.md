---
name: dayz-ai-patterns
description: "Reference for AI behaviour patterns in DayZ, studied in the DayZ Expansion AI module (eAI): state machine states (Dormant, Fighting), combat hysteresis, threat and targeting, line of sight and field of view, pathfinding, group formation, squad target distribution, and the vanilla NoiseSystem. Use when AI bots do not attack, do not patrol, walk around or through doors, ignore sounds, all chase the same enemy or do not spread into formation, or when debugging eAIBase, eAIGroup, eAIState or ExpansionPathHandler. Triggers: eAI, DayZ AI, AI FSM, FSM pathfinding, group AI, squad AI, threat targeting, LOS FOV AI, Expansion AI, AI bots. Also DayZ 1.30 vanilla AI: sandstorm, MINDSTATE_COWER, AIParams, GetEnvironmentNoiseReduction, animal group AI, DZMouflonGroupBeh, DZDogGroupBeh."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ AI patterns (Expansion AI and vanilla 1.30)

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts, so there is no preflight gate. The `dayz-ai-specialist` agent reads it when a task involves human style AI, a mod that sits beside DayZ Expansion AI, or the 1.30 noise and infected changes.

Two kinds of material are in here, and they are checked differently:

- **Expansion AI patterns.** Twelve patterns that make up the core of how DayZ Expansion's AI module (eAI) works, as they stand in the DayZ Expansion scripts at commit `8f75d554fda209b257c00deb8f01c181e67c980a`. This is third-party mod behaviour, not vanilla, and none of it is on `P:\`. Every `path:line` refers to that commit; the lines are not yet checked, and do not hold for any later Expansion version.
- **Vanilla 1.30 AI facts.** Noise, the infected cower state and animal groups, each cited to the file on `P:\`.

The Expansion patterns are described in prose, with no Expansion code reproduced, so you can debug a server that runs Expansion AI and borrow the ideas; code for a user's mod is written fresh against vanilla, as `skills/_shared/ai/patrols-and-guards.md` says. For a mod that extends Expansion itself, also read `skills/_shared/enscript/integrations/expansion_style.md`.

## What to read

| Question | Read |
|---|---|
| How does Expansion AI sleep, enter and leave combat, build its state machine, filter targets by view angle? | `references/eai-fsm-combat.md` (P1 to P4) |
| How does it limit path work, weight doors, spread a squad over targets, keep formation, throttle threat and line of sight? | `references/eai-pathfinding-groups.md` (P5 to P12) |
| What did 1.30 change for vanilla noise, infected and animal groups, with the literal vanilla blocks? | `references/dayz-1-30-ai.md` |
| Vanilla creature classes, behaviour templates, noise and visibility, patrols, spawning | the AI pack, front index `skills/_shared/ai/README.md` |
| Animal territories in the mission (`cfgenvironment.xml`, `env\*_territories.xml`) | `skills/_shared/ai/animal-territories.md` |

## The twelve Expansion AI patterns

File names are relative to the Expansion scripts repository; the full paths are in the two reference files.

| ID | Pattern | Expansion file |
|---|---|---|
| P1 | Dormant state: the state machine switches simulation off and on | `eaistate_dormant.c:1-17` |
| P2 | Fighting state: two thresholds and a chain of guards | `eaistate_fighting.c:18-38` |
| P3 | State machine loaded from XML, built from sub state machines | `eAIBase.c:661-666`, `Master.xml:3-8` |
| P4 | Field of view test before the line of sight raycast | `eAIBase.c:8156-8168` |
| P5 | Line of sight throttle that follows the update interval | `eAIBase.c:8089-8097` |
| P6 | Threat value cached for a random 250 to 300 ms | `eAITargetInformationState.c:58-67` |
| P7 | Target scan one entry per tick, restart after a random 0.1 to 0.2 s | `eAIBase.c:2962-2966` |
| P8 | Five times slower updates with no player in visibility range | `ExpansionWorld.c:247-250` |
| P9 | Pathfinding: recalculation thresholds and measured cost | `ExpansionPathHandler.c:581-592` |
| P10 | Path filters: navmesh area costs (open door 10 000) | `expansionpathfilters.c:131-147` |
| P11 | Group targets: distribution by who already tracks a target | `eAIGroup.c:726`, `eAIBase.c:3497-3505` |
| P12 | Formation positions cached per unit, refreshed every 2 to 4 s | `eAIGroup.c:822-830` |

P5, P7 and P8 are the Expansion AI instances of general server scheduling rules (a budget per frame, an interval that adapts to load, staggering by index). The general rules for our own code are in `skills/_shared/ai/spawning-and-performance.md` ("Server performance") and `skills/_shared/enscript/patterns/scheduler.md`. The longer write-up is `skills/_shared/enscript/depth/server-performance.md`, which also covers `#ifdef SERVER` against `IsServer()` checks and the `ScriptInvoker` lifecycle (rules 17 to 20 and 28 in `skills/_shared/enscript/depth/hard-rules.md`).

### State machine

**P3: loaded from XML, built from sub state machines.** `LoadFSM()` in `eAIBase` calls `ExpansionFSMType.LoadXML(...)`, then `Spawn(...)`, then `StartDefault()`. `Master.xml` includes sub state machines for vehicles, fighting and reloading; Dormant is a state of the master. What follows: the set of states changes through XML, not Enforce Script, so adding or removing a state needs no script recompile.

**P1: the dormant state owns `DisableSimulation`.** On enter the state calls `unit.DisableSimulation(true)`, on exit `unit.DisableSimulation(false)`. The transitions into it require: no combat, no players within visibility range, no pending waypoints, no movement in progress, and a leader that is an AI unit. Do not scatter `DisableSimulation` calls through other logic; let the state own the switch. Leaving the state restores simulation, so no caller has to remember to turn it back on.

### Combat

**P2: enter at 0.4, leave at 0.2.** The unit enters combat when `GetThreatToSelf()` is 0.4 or more and leaves when it drops below 0.2 (`eaistate_fighting.c:18-38`; the fire weapon guards are at `eaistate_fighting_fireweapon.c:78`). The gap stops the unit flipping in and out when threat hovers around one value. Guards before entry: `IsRestrained`, `IsUnconscious`, `IsInTransport`, `GetRunningAction`. The fire weapon sub state machine has its own chain: `IsRestrained`, then `GetTarget`, then `IsFighting`. The `IsFightingFSM` flag lets other systems ask about combat without looking inside the state machine. The rule: always set the enter threshold above the exit threshold; a single threshold produces a flip-flop in practice.

### Threat and targeting

**P6: threat cached for 250 to 300 ms.** Each target information state carries its own timestamp and a random cooldown drawn per call with `Math.RandomIntInclusive(250, 300)`; `CalculateThreat` runs at most about once per 275 ms per target, and the random window keeps units from all recalculating on the same server tick.

**P7: staggered target scan.** `UpdateTargets` advances one index of the potential target list per tick instead of scanning the whole list. A fresh pass starts only when the index has reached the end and a random interval from `Math.RandomFloat(0.1, 0.2)` has passed, so the units do not all finish a scan together.

### Line of sight and field of view

**P4: field of view before raycast.** `eAI_CalculateFOVHalfAngleH` gives the effective half angle, narrowed by stance. If the angle to the candidate is larger than the threshold, the candidate is dropped before a raycast is issued. Comparing angles costs nanoseconds; a raycast costs microseconds to milliseconds depending on the scene. Run cheap spatial tests (angle, distance band) before expensive ones (raycast, physics query).

**P5: throttled line of sight.** In scheduler mode (`s_eAI_FTO` of 2 or more) the interval between checks is `LOS_CHECK_INTERVAL` scaled by the unit's frame time over `ExpansionWorld.AI_UPDATE_INTERVAL`; otherwise it is `LOS_CHECK_INTERVAL`. Between checks the cached `state.m_LOS` is returned unless `m_eAI_TargetChanged` is set, which forces a fresh check. A unit updated at five times the base interval therefore does not get five times the checks.

**P8: backoff with no player near.** When scheduler mode is on and no player is within the unit's visibility distance, its update interval goes from `AI_UPDATE_INTERVAL` to five times that, about 250 ms instead of 50 ms. The logic keeps running at a fifth of the rate, and each unit decides for itself.

### Pathfinding

**P9: recalculation thresholds and measured cost.** `ExpansionPathHandler` does not recalculate on every target update. Three guards: `PATH_RECALCULATE_THRESHOLD` (the smallest change in position before the path is stale), `m_MinTimeUntilNextUpdate` (a cooldown), and `m_TimeIt.GetElapsed()` (the measured cost of each recalculation, usable as feedback for scheduling). The older `eAIPathFinding` is switched on with `#define EAI_USE_LEGACY_PATHFINDING`; `ExpansionPathHandler` is the default.

**P10: path filters with costs.** `SetFilterCost` per area type: crawl, crouch, jump and deep water cost 10; `DOOR_OPENED` costs 10 000. That cost forbids in practice, so the pathfinder routes around an open door instead of through it and avoids the door's physics geometry. Filters encode preferences, not only include and exclude flags.

### Group and formation

**P11: group target distribution.** `eAIGroup.AddTarget` passes target data to members. Before a member takes target X, `eAIBase` checks `num_ai_in_group_not_tracking`; at 0 (everyone already tracks X) it returns false. The squad spreads over several enemies with no explicit assignment. If all bots chase the same player, check that this logic is intact and that `AddTarget` is being called and not bypassed.

**P12: formation positions per unit.** `GetFormationPosition` checks `m_eAI_FormationPositionUpdateTime` against `Math.RandomFloat(2.0, 4.0)`, per member. When the leader moves, members recalculate at different moments over about two seconds. The recalculation is per unit, not per group; the group never tells all members to recalculate at once.

## Symptom to pattern

| Symptom on a server running Expansion AI | Look at |
|---|---|
| Bots do not attack, or flicker in and out of combat | P2 (threat thresholds and guards), P6 (threat cache) |
| Bots stand frozen far from players | P1 (dormant), P8 (backoff) |
| Bots do not patrol or stop following waypoints | P1 entry conditions (pending waypoints), P9 |
| Bots walk around open doors, or will not enter a building | P10 (door cost) |
| Bots ignore sounds | the vanilla noise system below; `skills/_shared/ai/perception.md` |
| All bots chase the same enemy | P11 |
| Bots do not spread into formation, or bunch up when the leader moves | P12 |
| Bots notice a target late or do not see it | P4 (view angle), P5 (throttle), P7 (scan) |

## Vanilla: the noise system

Feeding the engine AI a noise it can hear is vanilla and works without Expansion. The calls (`AddNoise`, `AddNoisePos`, `AddNoiseTarget`, `NoiseParams.Load` and `LoadFromPath`), with their lines in `P:\scripts\3_game\noise.c`, are in `skills/_shared/ai/perception.md`. In short:

- The server calls `g_Game.GetNoiseSystem().AddNoise(entity, params, mult)`, `AddNoisePos(entity, pos, params, mult)` or `AddNoiseTarget(pos, lifetimeSec, params, mult)`.
- `AddNoiseTarget` creates a decoy at a position for a duration: infected and other AI investigate a place with no entity attached (distraction devices, impacts).
- Weapon shots are config: `class NoiseShoot` on the weapon (`skills/_shared/weapons/muzzle-effects.md`).
- Since 1.30 the engine lowers noise for weather itself. `NoiseSystem.GetEnvironmentNoiseReduction(vector pos)` returns the absolute noise-strength reduction the engine applies at that point, which the vanilla comment calls the single source of truth used by AI (`P:\scripts\3_game\noise.c:12-13`). It is not a multiplier like `GetNoiseReductionByWeatherEx`, where 1 means no reduction; the debug display starts it at 0 (`P:\scripts\4_world\plugins\pluginbase\pluginpresencenotifier.c:156-158`). Do not also multiply `AddNoise` by a weather factor from script: the engine applies its own reduction at the position and the noise would be lowered twice.

## Vanilla: the infected cower state (since 1.30)

This is not Expansion AI. Vanilla infected gained `DayZInfectedConstants.MINDSTATE_COWER` after `MINDSTATE_FIGHT` (`P:\scripts\3_game\entities\dayzinfected.c:18`). `ZombieBase` syncs `m_MindState` over the range -1 to 5 (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:54`). In the cower state, used for sandstorms, the infected holds the calm idle pose with `SetIdleState(0)`; the vanilla comment says the engine AI has already stopped its movement (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:474-478`). Literal blocks: `references/dayz-1-30-ai.md`.

## Vanilla: animal group templates (since 1.30)

The Nasdara data of 1.30 has two new group behaviour templates (`GroupBehaviourTemplates` in `DZ\data_takistan\aiconfigs\config.cpp:14-132`; not yet checked on `P:\`, which has no Nasdara data). They are engine group templates, not Expansion state machines:

- `DZMouflonGroupBeh`, `type = "DomesticHerbivores"`: a graze and rest life cycle, `safeKeeperIntervalMin` and `safeKeeperIntervalMax`, catch-up radii (`:16-67`).
- `DZDogGroupBeh`, `type = "Predators"`: `zoneType = "HuntingGround"`, `siegeAttackCountdownMin` and `Max`, `huntAttackCountdownMin` and `Max`, `safeKeeperIntervalMin` and `Max` (`:68-127`).

`[DESIGN]` A custom map that wants the same packs copies or inherits these classes in its own `aiconfigs` config instead of rebuilding predator or herbivore behaviour in script. The templates that are on `P:\`, and how mission territories bind to them, are in `skills/_shared/ai/animal-territories.md`.

## DayZ 1.30

What changed, what breaks, and what to change in a mod. Literal blocks: `references/dayz-1-30-ai.md`.

What changed:

- Native noise reduction. New proto `GetEnvironmentNoiseReduction(vector pos)` on `NoiseSystem` (`P:\scripts\3_game\noise.c:12-13`). The debug display reads it (`P:\scripts\4_world\plugins\pluginbase\pluginpresencenotifier.c:155-158`).
- `class AIParams` gained `snowfallToNoiseMultiplier=5`, `fogToNoiseMultiplier=10`, `windToNoiseMultiplier=10` and `sandstormToNoiseMultiplier=10` (`P:\DZ\data\aiconfigs\config.cpp:12-21`); 1.29 had the rain and sea keys only (not checkable on `P:\`, which holds 1.30). The official changelog says weather handling is native and that `Weather.GetNoiseReductionByWeather` was removed; the method still exists, marked `[Obsolete]` (`P:\scripts\3_game\weather.c:454-467`), next to `GetNoiseReductionByWeatherEx(object)` (`P:\scripts\3_game\weather.c:407-420`).
- Vanilla infected: `MINDSTATE_COWER` for sandstorms; the sync range of `m_MindState` ends at 5.
- The Nasdara animal group templates `DZMouflonGroupBeh` and `DZDogGroupBeh` (not yet checked on `P:\`, see above).
- The official changelog says the navmesh file format has no backward compatibility, so custom terrains must regenerate their navmesh (this matters to P9 and P10), and that a navmesh can use a hide animation source through the EntityType navmesh config. Not checked on `P:\`.

What breaks in an AI or stealth mod written for 1.29:

1. A compile warning from the `[Obsolete(...)]` attribute if it still calls `Weather.GetNoiseReductionByWeather` (`P:\scripts\3_game\weather.c:454`) or `NoiseAIEvaluate.GetNoiseReduction` (`P:\scripts\4_world\static\sensesaievaluate.c:92`).
2. Overriding `GetNoiseReductionByWeather` no longer changes what engine infected and animals hear; they hear the native `AIParams` curve.
3. Passing a weather based multiplier into `AddNoise` while the engine also applies its own reduction lowers the noise twice.
4. On a custom terrain, old navmesh files will not load (per the changelog).

Checklist for moving a mod to 1.30:

- [ ] To read the absolute reduction the engine AI applies at a point: `GetGame().GetNoiseSystem().GetEnvironmentNoiseReduction(pos)`. Do not multiply a noise by it.
- [ ] For a HUD or old script maths on one object: `weather.GetNoiseReductionByWeatherEx(object)`.
- [ ] To change how rain, snow, fog, wind and sandstorm lower what infected hear: the `class AIParams` keys in `DZ\data\aiconfigs\config.cpp` (`rainToNoiseMultiplier`, `snowfallToNoiseMultiplier`, `sandstormToNoiseMultiplier` and the rest). That an addon override of `AIParams` takes effect, and which way each multiplier works, is not yet checked on `P:\`; confirm in the in-game test.
- [ ] Call `AddNoise(entity, params)` without folding weather into `external_strenght_multiplier`.
- [ ] If you spawn custom infected, keep the `m_MindState` sync range wide enough for `MINDSTATE_COWER` (5).
- [ ] Custom maps: regenerate the navmesh. Copy or inherit `DZMouflonGroupBeh` or `DZDogGroupBeh` if you want those packs.
- [ ] The Expansion patterns P1 to P12 were read in the Expansion scripts as they were at commit `8f75d554`, before 1.30. Treat their line numbers as valid for that version only and read the current Expansion scripts before relying on one.

## Building, testing and publishing

When the work has to end in a mod that builds, loads and ships, use `/dayz-lint`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-gate`, and the dayz-mod-dev skill for the full loop.
