# Designing a scripted AI brain

Covers the parts of an AI that vanilla does not give you: a human guard, or any creature whose decisions you script yourself instead of leaving them to the engine AI (`patrols-and-guards.md`). How to stop units flickering, freezing or all chasing one player.

These are design ideas in our own words, of the kind large community AI mods use to keep many units cheap and stable. Vanilla shows none of them, so every number below is a starting value to measure in the in game test, not a vanilla fact. The vanilla calls each idea uses are cited on `P:\`. Spreading periodic work over server ticks in general (a budget per tick, staggering, backoff, events before polling) is in `_shared/enscript/patterns/server_tick_budget.md`, and the AI rules in `spawning-and-performance.md`, section "Server performance"; this file does not repeat them.

## State machine

- **One state owns each switch.** To put a far unit to sleep, let a sleeping state do it on enter and undo it on exit, instead of scattering the call through other code. Leaving the state then always wakes the unit. Enter it only when the unit is not fighting, no player is in range, no route is pending and the unit is not moving. The vanilla call for a creature is `AIAgent.SetKeepInIdle(bool enable)` (`P:\scripts\3_game\ai\aiagent.c:6`), which vanilla itself uses only around a stealth kill (`spawning-and-performance.md`).
- **Behaviour as data.** A state machine whose states and transitions come from a data file, built from smaller machines (moving, fighting, reloading), changes behaviour without a script change. It pays off only for a large brain; a guard with three states is clearer in plain script.
- **Ask the state, not its internals.** Keep a flag such as "is fighting" in step with the state, so other systems ask the unit instead of reading the state machine.

## Entering and leaving combat

- **Two thresholds, not one.** Enter combat when the threat value reaches one level and leave only when it falls below a clearly lower one, for example enter at 0.4 and leave below 0.2. With a single threshold, a value hovering around it flips the unit in and out of combat every few ticks.
- **Guards before the state.** Check the cheap conditions that make combat impossible (restrained, unconscious, in a vehicle, busy with an action) before entering, and give each sub state its own short chain (for firing: has a target, is fighting).
- Infected and animals already do this in the engine. Read the result from the mind state (`creatures.md`, section "Infected mind states") instead of building your own threat value.

## Seeing a target

- **Cheap tests first.** Drop a candidate on angle and distance before any line of sight raycast; comparing two angles is almost free, a raycast is not. Narrow the view angle with stance if you model one. The vanilla raycast is `DayZPhysics.RaycastRV` (`P:\scripts\3_game\global\dayzphysics.c:123` and `:199`).
- **Cache the line of sight.** Keep the last result per target and check again only on an interval, or at once when the target changed. If the unit's own update interval is stretched (`_shared/enscript/patterns/server_tick_budget.md`, section "Backoff"), stretch the check interval with it, so a slowed unit does not check more often per second than a normal one.
- **Cache the threat value.** Recalculate a target's threat at most every few hundred milliseconds with a small random part per unit, for example 250 to 300 ms, so many units never recalculate on the same tick.
- **Scan a few entries per tick.** Walk the list of possible targets with a stored index, a few entries per tick, and start a new pass only after a short random pause, for example 0.1 to 0.2 s.

## Paths

- **Plan again only when it matters.** Plan a new path only when the target has moved more than a set distance since the last plan and a cooldown has passed. Measure what each plan costs and tune both values with it. Plan with `AIWorld.FindPath` (`P:\scripts\3_game\ai\aiworld.c:98`) on a timer, never in the command handler (`spawning-and-performance.md`).
- **Costs, not only flags.** A `PGFilter` takes include and exclude flags and a cost per area type with `SetCost(PGAreaType, float)` (`P:\scripts\3_game\ai\aiworld.c:59` and `:67`). A very high cost forbids in practice without a hard block: a cost such as 10 000 on `PGAreaType.DOOR_OPENED` (`:46`) makes units route around an open door instead of colliding with it. A small extra cost, for example 10, on crawl, crouch, jump and deep water areas makes units prefer plain ground. If units refuse a doorway or walk round a building, check the filter costs first.
- On a custom map, a path that fails after a game update points at the navmesh first (`patrols-and-guards.md`).

## Squads

- **Spread targets.** Before a member takes a target, count the members not yet tracking it; when that count reaches 0, refuse. The squad then spreads over several enemies with no explicit assignment. If every member still chases one player, check that targets reach members only through that one path.
- **Formation slots per unit.** Let each member recompute its own formation slot on its own clock, every 2 to 4 seconds with a random part, instead of the group telling every member to recompute at once when the leader moves.

## Symptom to cause

| Symptom in your own scripted AI | Look at |
|---|---|
| Units flicker in and out of combat | Two thresholds; the threat cache |
| Units stand frozen far from players | The sleeping state's enter and exit conditions; backoff |
| Units stop following their route | The sleeping state must not be entered while a route is pending; the path cooldown |
| Units walk round open doors or will not enter a building | Filter costs |
| Every unit chases the same enemy | Spreading targets |
| Units bunch up when the leader moves | Formation slots per unit |
| Units notice a target late | View angle, line of sight interval, scan rate |

Code for a user's mod is always written fresh against the vanilla calls above; nothing is copied from another mod.
