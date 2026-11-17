# Expansion AI: state machine and combat patterns

How DayZ Expansion's AI module (eAI) puts a unit to sleep, enters and leaves combat, builds its state machine and filters targets by field of view. Pattern IDs (PC-5, PC-9a, PC-11, PC-13) are the knowledge pack's labels.

Everything here describes third-party code: the DayZ Expansion scripts (`salutesh/DayZ-Expansion-Scripts`) at commit `8f75d554`. File paths are relative to that repository; none of it is on `P:\`. The knowledge pack reports every `path:line` below as confirmed against that commit; not yet checked for Agentic-Z. The patterns are described in our own words and no Expansion code is reproduced. Use them as ideas: code for a user's mod is written fresh against vanilla (`skills/_shared/ai/patrols-and-guards.md`).

## PC-5: the dormant state owns `DisableSimulation`

`Scripts/4_World/DayZExpansion_AI/Classes/FSM/states/eaistate_dormant.c:1-17`

The state `eAIState_Dormant` calls `DisableSimulation(true)` on the unit when it is entered and `DisableSimulation(false)` when it is left. The transitions into it require: no combat, no players nearby, no pending waypoints, no movement in progress, and a group leader that is itself an AI. `Master.xml` lists Dormant as an explicit state.

The pattern: let a state of the state machine, not a flag or a scattered `if`, switch physics and animation off. Leaving the state restores simulation, so no caller has to remember to turn it back on, and the enable and disable calls are not spread across the code.

## PC-11: the fighting state enters at 0.4 and leaves at 0.2

`Scripts/4_World/DayZExpansion_AI/Classes/FSM/states/eaistate_fighting.c:18-38`
`Scripts/4_World/DayZExpansion_AI/Classes/FSM/states/eaistate_fighting_fireweapon.c:78`

- The unit enters combat when `GetThreatToSelf()` is 0.4 or more.
- It leaves combat when `GetThreatToSelf()` falls below 0.2.

Before the state activates it checks guards: `IsRestrained`, `IsUnconscious`, `IsInTransport` and `GetRunningAction`. A flag, `IsFightingFSM`, is kept in step so other systems can ask whether the unit is fighting without looking inside the state machine. The fire weapon sub state machine has its own chain of guards: `IsRestrained`, then `GetTarget`, then `IsFighting`.

The rule to take away is hysteresis: the enter threshold is higher than the exit threshold. With one threshold, a threat value that hovers around it makes the unit flip in and out of combat.

## PC-13: the state machine is loaded from XML and built from sub state machines

`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c:661-666`
`Scripts/FSM/Master.xml:3-8`

`LoadFSM` in `eAIBase` does three things in order: `ExpansionFSMType.LoadXML(...)`, then `Spawn(...)`, then `StartDefault()`.

`Master.xml` composes sub state machines for vehicles, fighting and reloading; Dormant is a state of the master. Changing which states exist and how they connect means editing XML, not Enforce Script, so behaviour is defined apart from its implementation and adding or removing a state needs no script change.

## PC-9a: a field of view test before the line of sight raycast

`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c:8156-8168`

`eAI_CalculateFOVHalfAngleH` computes the half angle of the unit's field of view; the unit's stance narrows it. If the horizontal angle to a candidate (`angleDiffH`) is larger than the threshold (`threshAngleH`), the candidate is dropped before any raycast is made. A raycast is expensive; comparing two angles is nearly free and removes most candidates.

The general rule: run cheap spatial tests (angle, distance band) before expensive ones (raycast, physics query). The throttle on the raycast itself is PC-9b in `eai-pathfinding-groups.md`.
