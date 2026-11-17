# Expansion AI: pathfinding, groups and perception patterns

How DayZ Expansion's AI module (eAI) limits path recalculation, weights navmesh areas, spreads a squad over several targets, keeps a formation, and throttles threat, target and line of sight work. The pattern IDs (PC-2 to PC-18) are the ones in the table in `SKILL.md`.

Everything here is third-party mod behaviour, not vanilla: the DayZ Expansion scripts at commit `8f75d554`. File paths are relative to the Expansion scripts repository; none of it is on `P:\`. Every `path:line` below refers to that commit and is not yet checked. The patterns are described in prose and no Expansion code is reproduced. Use them as ideas: code for a user's mod is written fresh against vanilla, with the vanilla navmesh calls in `skills/_shared/ai/patrols-and-guards.md` and the server rules in `skills/_shared/ai/spawning-and-performance.md`.

## PC-15: path recalculation behind thresholds, with its cost measured

`Scripts/4_World/DayZExpansion_AI/Classes/PathFinding/ExpansionPathHandler.c:581-592`

`ExpansionPathHandler` does not recalculate the path every time the target is updated. It is guarded by:

- `PATH_RECALCULATE_THRESHOLD`: the smallest change in position before the path counts as stale.
- `simulationPrecision`: controls the step resolution.
- `m_MinTimeUntilNextUpdate`: a cooldown between recalculations.
- `m_TimeIt.GetElapsed()`: the measured cost of each recalculation, which can feed an adaptive schedule.

There is an older path system, `eAIPathFinding`, switched on with `#define EAI_USE_LEGACY_PATHFINDING`. The default is `ExpansionPathHandler`.

## PC-16: path filters carry costs; an open door costs 10 000

`Scripts/4_World/DayZExpansion_AI/Classes/PathFinding/expansionpathfilters.c:131-147`

`SetFilterCost` gives each navmesh area type a weight:

- Crawl, crouch, jump and deep water areas: cost 10.
- An opened door area (`DOOR_OPENED`): cost 10 000, which makes the pathfinder route around an open door instead of through it and so avoids collisions with the door's physics geometry.

A filter is not just an include or exclude flag; it encodes a preference as cost. A cost of 10 000 forbids in practice without a hard block. If bots refuse to walk through open doors, or walk around a building instead, this cost is why. Vanilla's own filter is `PGFilter` with `SetCost` (`P:\scripts\3_game\ai\aiworld.c:67`).

## PC-17: group targets are distributed so the squad does not pile onto one enemy

`Scripts/4_World/DayZExpansion_AI/Classes/eAIGroup.c:726`
`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c:3497-3505`

`eAIGroup.AddTarget` passes target information to the group's members. Before a member takes a target, `eAIBase` checks a count, `num_ai_in_group_not_tracking`. If it has reached 0, meaning every member already tracks that target, the check returns false and the member does not take it.

In practice: if every bot is already chasing target X, the next attempt to give X to another member is refused, and the squad spreads over several enemies without any explicit assignment logic. If all bots chase the same player anyway, check that this count logic is intact and that targets go through `AddTarget` instead of around it.

## PC-18: formation positions are cached per unit and refreshed every 2 to 4 seconds

`Scripts/4_World/DayZExpansion_AI/Classes/eAIGroup.c:822-830`

`GetFormationPosition` compares `m_eAI_FormationPositionUpdateTime` with a random interval from `Math.RandomFloat(2.0, 4.0)`, drawn per unit. Each member recalculates its formation position on its own clock, not when the group says so. When the leader moves, the members do not all recalculate on the same tick; the work spreads over about two seconds. The group never broadcasts "recalculate now".

## PC-14: the threat value is cached for 250 to 300 ms

`Scripts/4_World/DayZExpansion_AI/Classes/Targets/eAITargetInformationState.c:58-67`

Each target information state keeps its own timestamp, `m_ThreatLevelUpdateTimestamp`. The threat level is recalculated only when a recalculation is forced, or when the time since that timestamp is larger than a random number of milliseconds drawn with `Math.RandomIntInclusive(250, 300)`. It then stores the current time and sets `m_ThreatLevel` from `m_Info.CalculateThreat(m_AI, this)`.

So `CalculateThreat` runs at most about once per 275 ms per target, and because the window is random per call, many units do not all recalculate threat on the same server tick.

## PC-7: the target scan advances one entry per tick and restarts after 0.1 to 0.2 s

`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c:2962-2966`

`UpdateTargets` adds the frame time to `m_eAI_UpdateTargetsTick` and walks the list `m_eAI_PotentialTargetEntities` one index per tick, using a persistent index `m_eAI_CurrentPotentialTargetIndex`. Only when the index has reached the end of the list and the tick counter is larger than `Math.RandomFloat(0.1, 0.2)` does it reset both the counter and the index to 0 and start a fresh pass.

The list is never scanned in full in one tick, and the random restart interval keeps the units from all finishing their scan together.

## PC-2: with no player in visibility range, the unit updates five times slower

`Scripts/4_World/DayZExpansion_AI/Classes/ExpansionWorld.c:247-250`

When the scheduler mode is on (`eAIBase.s_eAI_FTO` is 2 or more) and the unit's own list `m_eAI_PlayersWithinVisibilityDistanceLimit` is empty, the unit's update interval becomes `AI_UPDATE_INTERVAL * 5`. Otherwise it is the normal interval.

The logic is not switched off; it runs at a fifth of the rate, about every 250 ms instead of every 50 ms. The condition is local to the unit, so each one decides its own backoff.

## PC-9b: the line of sight check is throttled, and the throttle follows the update interval

`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c:8089-8097`

The interval between line of sight checks is `LOS_CHECK_INTERVAL` when the scheduler mode is off (`s_eAI_FTO` below 2). When it is on, the interval is `LOS_CHECK_INTERVAL` multiplied by the ratio of the unit's frame time `pDt` to `ExpansionWorld.AI_UPDATE_INTERVAL`. A timer, `m_eAI_LOSCheckDT`, is reset to 0 once it reaches the interval and then advanced by `pDt`. While the timer is below the interval and the target has not changed (`m_eAI_TargetChanged` is false), the function returns the cached result, `state.m_LOS`.

In scheduler mode the interval scales with `pDt`, so a unit updated at five times the base interval does not get five times the line of sight checks; the effective rate stays constant. Setting `m_eAI_TargetChanged` forces a fresh check and bypasses the cache.
