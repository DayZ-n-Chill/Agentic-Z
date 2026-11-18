# Runtime state, per-tick events and sync

Which per-tick event a car runs, what a non-owner client reads, why script visual state is missing on a fresh spawn, and how to probe a vehicle that draws or exits in the wrong place.

> Status: measured in game on worked vehicle builds, each named in its entry (TestHeli OH-1, TestCoupe), and not yet checked on `P:\`. A citation written with its full `P:\` path was opened on vanilla data (a 1.30 build); a bare `file.c:N` repeats a full citation from the anchors list below. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `README.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- The `CarScript` constructor registers `EntityEvent.POSTSIMULATE` and `EntityEvent.POSTFRAME` and no other event (`P:\scripts\4_world\entities\vehicles\carscript.c:207-208`); its per-tick work is in `EOnPostSimulate` (`P:\scripts\4_world\entities\vehicles\carscript.c:807`).
- `EOnSimulate` is an empty stub on the base entity (`P:\scripts\1_core\proto\enentity.c:201-203`).
- `BoatScript` overrides both `EOnPostSimulate` (`P:\scripts\4_world\entities\vehicles\boatscript.c:355`) and `EOnSimulate` (`P:\scripts\4_world\entities\vehicles\boatscript.c:393`).
- `EngineIsOn` is native on `Car` (`P:\scripts\3_game\vehicles\car.c:230`).
- `RemoteObjectTreeDelete` and `RemoteObjectTreeCreate` are native on the game object (`P:\scripts\3_game\global\game.c:708-710`).

## Per-tick events: CarScript has no EOnSimulate (added 2026-07-29, TestHeli OH-1)

Which events a `CarScript` registers, why `super.EOnSimulate` does nothing on a car, and where
the car's per-tick work runs are written once, in `aviation-carscript-base.md` ("Events: where the
flight loop runs"), together with the custom solvers that add `SetEventMask(EntityEvent.SIMULATE)`
and pump it by hand. On a car, hook `EOnPostSimulate` for per-tick logic. Two points that file
does not cover: `BoatScript`, unlike `CarScript`, overrides both events (`boatscript.c:355` and
`:393`); and although vanilla runs much of the `EOnPostSimulate` work on the owner client too, a
mod's checks that depend on replicated items (`CheckVitalItem`) must stay server-only.
(These are 1.30 line numbers; `dayz-1-30-vehicles.md` covers what 1.30 changed.)

## Engine state on a non-owner occupant

**Crew / engine state on a non-owner occupant (measured on TestHeli):**
`Car.EngineIsOn()` on a client that is not the Pawn owner returns **false** even when the
authority has the engine running — no exception, no warning. Measured on the occupant of
seat 1 with a two-component probe in the same frame (`natEng=false syncEng=true`) and the
server log showing no stop. Any client subsystem gated on `EngineIsOn()` shuts itself off
(the thermal camera died instantly). Remedy: replicate the state
(`RegisterNetSyncVariableBool` written in `OnEngineStart/Stop`) and have **every** client
path read `native OR replicated`; an `m_EngineOnAuthority` (OwnerState) snapshot does NOT
serve passengers. When a client check decides to turn something off, print BOTH sources in
the same frame.

## A mesh drawn in the wrong place is invisible to every script transform: qualify the probe first (added 2026-07-29)

When the user reports that a vehicle **draws** somewhere the entity is not — body on the ground while
the vehicle climbs, a part left behind, a piece floating — the reflex is to instrument the transforms
and compare. **That reflex has already been paid for and it returns nothing.**

Measured on TestHeli OH-1 over a 26 m climb: root position, `GetRenderTransform`, both bones, the
physics body (`dBodyGetWorldTransform`) and the pilot's world position **agreed digit-for-digit**
while the hull was drawn on the ground. The consequence is the general rule:

> **Any probe derived from the entity root inherits the root's blind spot.** A drawing-position defect
> lives downstream of every transform Enforce exposes, so no amount of transform logging can see it.

**What does work** — a marker the engine projects from a WORLD point without consulting the entity's
transform, read off a screenshot: `Debug.DrawSphere` at `GetPosition()` plus a ladder of rungs at
fixed spacing below it. The rung spacing is what makes the defect **quantitative** (gap in metres =
rungs × spacing) instead of an eye report.

**Probe qualification, mandatory before any number adjudicates:** read the magnitude in the regime
where the drawing is CORRECT (on the ground) and in the regime where it is WRONG (airborne). If it
does not change while the eye sees a difference, that magnitude is **blind** — stop using it. A delta
of exactly `0.000` is a tautology signal, not precision.

**The companion trap, on the inference side.** Over flat ground, "the visual Y is frozen at its
take-off value" and "the transform is computed from a ground-referenced magnitude" produce **the same
two signatures**: gap grows with height, gap returns to zero on landing. This is plain
arithmetic. So the flat-ground signature must never be used to EXCLUDE a family of causes — it
identifies nothing. Discriminate by changing the regime, not by reasoning:

- horizontal traverse at constant world Y over terrain ≥15 m lower — ground-referenced tracks the
  terrain, frozen-Y does not;
- descend without touching down and climb again — a replication/state split shows hysteresis, a pure
  function of height does not.

- Status honesty: the blind-spot measurement and the flat-ground ambiguity are **verified**; the two
  discriminant manoeuvres above were designed on 2026-07-29 and **had not been run in-game** at the
  time of writing. Treat them as an untested procedure until a cycle closes it.

## Get-out desync: a one-shot OnDriverExit probe on both sides

- **The ex-owner proxy is frozen until re-registered.** With `NetworkMoveStrategy.PHYSICS`, on get-out the former owner falls back to the last proxy snapshot received before possession and receives no further server transform. A client `SetPosition`/teleport or a server pose nudge cannot repair it (client `SetPosition` had no effect at 50 ms; 10 cm server lift had not arrived in 25 s). After a short server-side delay (~500 ms after `OnDriverExit`) and only when every crew seat is empty, rebuild the remote representation with `RemoteObjectTreeDelete/Create` (`scripts/3_game/global/game.c:708-710`): `3/3` re-entries, `|Δ| 0.12/0.11 m`. Schedule it from the surviving server object and cancel on deletion; a `CallLater` owned by the destroyed client replica cannot complete safely.

For "invisible/desync on exit" bugs, a one-shot probe in `OnDriverExit` that prints on BOTH
sides `playerPos`, `heliPos`, `crewEntryWS`, `dPH`, `dPC` adjudicates in one flight what
hypotheses do not: good exit = client == server; bad exit = client with the vehicle at the
spawn pose (sunk) and the player underground, server correct. Align client/server clocks by
PAIRS of twin events (the two EXIT lines gave a stable 33,99 s offset) and correlate with
the owner's position series (FRAME p0) to date the divergence. Complements the Pawn ladder
in `network-physics-ownership.md`.

## Script visual state is not applied to a newly spawned vehicle, and the config default looks like a result (added 2026-09-10, TestCoupe)

Visual code running from `OnVariablesSynchronized` **never executes** on a
vehicle created with a bare spawn, because that vehicle has not synchronized anything yet. Car paints
`hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` entries from `config.cpp` and
nothing else, so all script `SetObjectTexture` / `SetObjectMaterial` calls are missing.

It is a silent trap because **config default is usually a plausible version of
what script would have painted**: an almost black screen, unlit indicator light, blank panel.
Reading those pixels as result of scripted branch gives a confident and false verdict.

**What does synchronize, measured:** mounting parts. A debug-spawn fixture attaching battery,
spark plug, radiator, four wheels, and doors is a large attachment synchronization and triggers
visual update. Seating a player and starting engine also works, with cost
detailed below.

**The discriminant: carry a control IN THE SAME FRAME.** Choose a SECOND selection whose
script state is distinguishable at a glance from its config default, and read it in same
capture as subject:

- instrument cluster: config gives it OFF material, script gives it ON.
- any indicator light: OFF in config, ON only from script.

Thus frame answers two questions at once. Lit control => scripted branch
ran, therefore subject appearance **is** the result. Unlit control => script did not run
and subject says nothing, whatever it looks like.

Compare `emmisive[]` of the two materials before trusting the eye: scale difference of
0.3 vs 1.1 is unmistakable in broad daylight; 0.9 vs 1.0 is not.

**Cost of alternative route (DayZ-MCP harness, measured 2026-09-10):** starting the engine requires
client-side vehicle ownership, and taking it leaves free camera unusable for the entire
lifetime of client process. Framing dashboard and having engine running become mutually
exclusive on the same client. Prefer synchronization via attachments.
