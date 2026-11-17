# Network, physics and ownership: who controls the pose

Who simulates a vehicle (the owner client, with server reconciliation), why a forced seat is not ownership, why writing the pose fights the owner, how to derive angular velocity, and the rules of a custom `PawnMove` and `PawnOwnerState` pair.

> Status: the vanilla facts cite the script they were read in. A citation written with its full `P:\` path, and a bare `file.c:N` (the vanilla script of that name under `P:\scripts\`), were both opened on the vanilla data on `P:\` (a 1.30 build). The in-game results were measured on mod vehicles (a car driven through an automation bridge, and a helicopter built on `CarScript`), not on vanilla ones; the default move strategy was measured on DayZ 1.29. Statements about DayZ Expansion are third-party mod behaviour, not vanilla, and its files were not opened here. `[IN-GAME VERIFIED]`, `[CODE-VERIFIED]` and `[DESIGN REVIEWED]` say how far an entry was tested. Per-tick events and what a passenger's client sees are in `runtime-state-and-sync.md`; driving a car from an automated harness is in `test-stand-and-mcp.md`.

Related file in this pack: `aviation-networking.md` (the same Pawn owner-prediction classes applied to an aircraft on `CarScript`).

## Vanilla anchors checked on `P:\`

- `Transport extends Pawn` under the reconciliation define: `P:\scripts\3_game\vehicles\transport.c:66`.
- `FEATURE_NETWORK_RECONCILIATION` is defined unconditionally: `P:\scripts\1_core\defines.c:64`.
- `IsOwner` is native on `Pawn`: `P:\scripts\3_game\entities\pawn.c:194`.
- `IsAuthorityOwner` is native on `Pawn`: `P:\scripts\3_game\entities\pawn.c:200`.
- `GetNetworkMoveStrategy` is exposed to script: `P:\scripts\3_game\entities\pawn.c:218`.
- `NetworkMoveStrategy` lists the strategies: `P:\scripts\3_game\entities\pawn.c:138`.
- `IsServerOrOwner` is declared at `P:\scripts\4_world\entities\vehicles\carscript.c:2592`.
- `OnInput` of `CarScript`: `P:\scripts\4_world\entities\vehicles\carscript.c:1041`.
- `SetThrottle` is native on `Car`: `P:\scripts\3_game\vehicles\car.c:191`.
- `dBodySetAngularVelocity` takes rotation around x, y and z, not yaw, pitch and roll: `P:\scripts\1_core\proto\enphysics.c:163`.
- `dBodyApplyForce` is declared at `P:\scripts\1_core\proto\enphysics.c:146`.
- `GetOwnerStateType` is overridden by `CarScript`: `P:\scripts\4_world\entities\vehicles\carscript.c:2568`.

The sections below are ordered by topic. The reference tables of `skills/dayz-vehicles/SKILL.md` say when to read this file.

---

## Network ownership: a server-side forced seat is not client ownership, and the owner drives the physics

Check this before any attempt to drive or automate a car from a client peer, or to reason about "who drives". Read in the vanilla source and confirmed in game.

- The car is a **Pawn** (`Transport extends Pawn` under `FEATURE_NETWORK_RECONCILIATION`,
  transport.c:66 -> Car car.c:87 -> CarScript carscript.c:94). The `IsOwner()` inside `IsServerOrOwner()`
  (carscript.c:2592-2601) is the **car's network ownership**, not the player's (glossary pawn.c:5-8:
  Owner = the client controlling the pawn).
- **`IsServerOrOwner()` does not gate throttle.** Its only consumers are teardown and fluids
  (carscript.c:552, :577, :845). Throttle to physics is **proto native** (`SetThrottle` car.c:191, "future
  throttle value") and is applied by whoever simulates the body, which is the **owner**. The only script
  `SetThrottle` (carscript.c:1202) is dead in production (`#ifdef DIAG_DEVELOPER`).
- A car **with no client owner is `IsAuthorityOwner`** (authority without owner, pawn.c:199-200): the server
  simulates it, so a server-side `SetThrottle` **does move it**. That is an artifact of a single machine
  running server and client, not proof that the server drives cars owned by a client. (Measured: the
  server moved a car under the PHYSICS strategy by 2.29 m because no client owned it.)
- A server-side **`StartCommand_Vehicle`** (for example the `vehicle_enter` tool of the dayz-mcp bridge) seats
  the player on the server only: the client **never gets `GetGame().GetPlayer().GetCommand_Vehicle()` nor
  ownership of the car** (measured in game six times; the client peer reports `not_seated`). A real get-in
  (`ActionGetInTransport.Start()`, a method shared by client and server, actiongetintransport.c:71-111) runs
  `StartCommand_Vehicle` on the **client's** Human and reserves the seat through a juncture
  (`AddInventoryJunctureEx` and `SetVehicle`, :138-158). The ownership transfer is native (no
  `SetNetworkOwner` exists in script).
- **Practical consequence:** to drive or measure on the owner side from a client, the client must
  **take ownership itself** (a client-side get-in), not rely on a server-side forced seat. An
  owner-authority test on a single machine is **confounded** (the client never truly owns); the clean
  discriminator is a dedicated server with a remote client that performs the get-in.
- Diagnostic readings: `IsOwner()` (pawn.c:194), `IsAuthorityOwner()` (pawn.c:199-200),
  `GetOwnerIdentity()` (pawn.c:209), `GetNetworkID()` (object.c:819).
- **Driving the owner side from script (measured in game, 0 to 39 km/h):** `Car.SetThrottle`, `SetSteering`
  and `SetBrake` called from the mission (`OnUpdate` or a job) do not move a car simulated by its owner:
  the `super` of `CarScript.OnInput(dt)` (`carscript.c:1041`) overwrites them every frame with the local
  driver's input, which is 0. Fix: apply the throttle inside a `modded class CarScript` `OnInput`, **after
  `super.OnInput(dt)`** (where the vanilla debug autopilot does it, `carscript.c:1202`). There is no
  injection through `HumanInputController` (vehicle input is native, with no override API). Symptom: "the
  car belongs to its owner but `SetThrottle` does not move it".

## Angular velocity is not yaw, pitch and roll; derive omega from the pose delta

`dBodySetAngularVelocity` takes angular velocity as rotation around x, y and z, **not
yaw/pitch/roll**. Vanilla spells it at `enphysics.c:163`: *"Angular velocity,
rotation around x, y and z axis (not yaw/pitch/roll)"*. The Enfusion axis map is
yaw → Y, pitch → Z, roll → X (right-hand rule). Two vanilla sources agree:
`YawPitchRollMatrix("70 15 45", mat)` at `enmath3d.c:125-131`
matches the COLUMNS of `Rz(pitch) . Ry(yaw) . Rx(roll)` to 4e-7;
`dayzplayercameravehicles.c:132-134` reads `dBodyGetAngularVelocity(vehicle)` and
routes Y to yaw, Z to pitch, X to roll for camera lag. Corollary: `mat[i]` from
`GetTransform` (`enentity.c:288`) and from `YawPitchRollMatrix` are world-space
BASIS VECTORS (columns), not rows; mixing them up flips the sign of any rotation
derived from those matrices.

The trap: if the solver keeps rate accumulators in deg/s (`m_PitchRate`,
`m_RollRate`, `m_YawRate`), those rates are NOT the derivative of the orientation
that gets written once a later step moves the pose without touching them (a
levelling stabilizer, a cosmetic pendulum adding a roll delta, a takeoff
level-assist). Feeding them as omega commands a rotation that the next
`SetOrientation` contradicts. That is the "body fighting the pose" judder.

Recipe: derive omega from the REAL pose delta, never from the accumulators.

    GetTransform(before);
    SetOrientation(target);
    GetTransform(after);
    // w*dt = 1/2 * sum_i (b_i x a_i) over the three basis vectors
    dBodySetAngularVelocity(this, sum * (0.5 / dt));

Exact to O(theta^3) (the per-tick delta does not reach 6 deg), immune to the
pendulum or stabilizer moving the pose on their own, and automatically ZERO at
call sites that command the sampled pose (transition holds, ground clamp) with no
extra branch. Benign failure: if `SetOrientation` does not refresh the transform
on the same tick, `after == before`, omega = 0, behaviour identical to before.

## The PHYSICS strategy is owner prediction with reconciliation: writing the pose fights it

Extends the ownership section above. Read in the vanilla source and measured at runtime on a helicopter built on `CarScript`.
Check this on ANY symptom of "input lag", "rubberbanding" or "the client reverts transforms" in a
server-authoritative `CarScript`:

- **Measure the strategy before theorizing** (one line, either side): `Print(GetNetworkMoveStrategy().ToString())`.
  NONE=0, LATEST=1, PHYSICS=2 (`pawn.c:138-148`; the getter is proto native at `pawn.c:218`, so it is
  exposed to script). In DayZ 1.29 `CarScript` runs **PHYSICS by default** (measured `str=2 own=true` on the
  pilot's client); no config flag selects it, in vanilla or in DayZ Expansion: the engine sets it by native
  class. `FEATURE_NETWORK_RECONCILIATION` is unconditional (`defines.c:64`).
- **Under PHYSICS the owner already simulates predictively** (the full Pawn contract is in vanilla: `pawn.c:256-329`
  ObtainMove, ConsumeMove, ReplayMove, RewindState; `CarScriptMove` and `CarScriptOwnerState` hooks at
  `carscript.c:2568-2588`; `IsServerOrOwner()` at `carscript.c:2592-2601`). Consequences:
  1. A server that writes pose or velocity per tick (`SetOrientation`, `SetVelocity`) does not cooperate: it causes
     a continuous correction of the owner by the authority, which is **structural round-trip lag plus
     snap-backs**. The symptom shows even on loopback (the round-trip time is not the only latency: server
     tick, replication and rewind add to it).
  2. A transform written from the owner client reverts in about 0.3 s (measured). It is not a bug to
     debug: it is reconciliation working.
  3. The compatible path is the one DayZ Expansion uses from 1.28 on (third-party mod behaviour, not
     vanilla): **the same forces applied on owner and server** (`dBodyApplyForce`, `enphysics.c:146`, world
     space; the commit gated by `dBodyIsActive && dBodyIsDynamic` in its `ExpansionPhysicsState.c`), input
     carried inside the native `PawnMove` (its legacy RPC is turned off under PHYSICS, in its `CarScript.c`),
     and a custom Move and OwnerState contract that calls `super` first (its `ExpansionHelicopterScript.c`).
     The engine integrates; nobody writes the pose.
- **A cheap spike before committing to that architecture**: a tuning flag that is off by default, and a
  1.5 s window in which both sides apply the SAME force (anti-gravity plus a lateral pulse on an axis
  nothing else in the model touches) while the server suspends its kinematic actuator; per-tick traces on
  both sides; an offline parser that returns YES, NO or INCONCLUSIVE. Harness traps: the abort must be
  SYMMETRIC (engine, seat and flight state exits), suppression of the hijacked key goes UPSTREAM of every
  consumer of that channel, and any exit from the flight state clears the window.
- Evidence status: all measured. Verdict of the spike flight: **YES**. Three clean pulses on the
  owner (local slope about 1.6 m/s2 against 1.5 theoretical, the gain retained, a transient reversal of at
  most 30% from the owner to server offset); the snap-back when the window EXPIRES is the kinematic actuator
  reabsorbing (the reason to remove pose writing in the full path); an owner-only pulse near the ground
  (the server not armed, by height above ground) reverted 91%. The pilot felt nothing
  (0.15 g lateral during a climb at 7 to 11 m/s): the gate is telemetric, not feel-based.

## A custom Pawn framework (Move and OwnerState): the type ladder and its hard rules

Continues the section above. When the approach is "forces plus owner prediction", the FIRST step of
construction is an INERT Pawn framework (custom types and log-only hooks, flight untouched): it validates
the engine wiring before any solver is migrated. Recipe read in the vanilla source and proven by a compile
and a flight on a helicopter built on `CarScript`:

- **Type ladder** (derive from the last rung, not from the Pawn classes): `PawnMove -> TransportMove ->
  CarMove -> CarScriptMove` and `PawnOwnerState -> TransportOwnerState -> CarOwnerState ->
  CarScriptOwnerState` (`transport.c:11-50`, `car.c:78-82`, `carscript.c:57-74`).
  `TransportOwnerState` and `TransportMove` carry the NATIVE transform plus linear and angular velocity
  (`transport.c:13-23`, `:35-42`): **do not duplicate them in custom state**.
- **Hooks** (`pawn.c:238-311`, all `protected event`): `GetMoveType` and `GetOwnerStateType` (the
  engine instantiates the types AT CONSTRUCTION, `pawn.c:235`, `:244`, so the overrides must exist on the
  class and cannot activate late), `ObtainMove`, `ConsumeMove`, `ReplayMove` (bool: honour super's
  rejection before processing), `ObtainState`, `RewindState(state, move, inout NetworkRewindType)`.
  `CarScript` already implements the type getters, `ObtainState` and `RewindState` (`carscript.c:2568-2588`):
  call super ALWAYS and exactly once (super's `ObtainState` and `RewindState` carry `m_fTime`).
- **Serialization**: `Write` and `Read` with super FIRST; NEVER serialize a `vector` (expand it to
  floats); `EstimateMaximumSize()` = super + 4 bytes per scalar (a bool counts as 4, conservative).
  The Move carries the RAW axes before any authority scaling (attenuation and state machines are
  recomputed per solve tick; baking them in breaks replay determinism). Latched or stateful solver memory
  goes in the OwnerState (server to owner), not in the Move.
- **Read the raw local input INSIDE `ObtainMove`.** The native order of `ObtainMove` and `EOnSimulate` is
  not exposed to script; relying on the tick's last read can serialize zeroes or stale values, and the
  round-trip gates then validate EMPTY wiring. Also make the payload gate reject a run in which every
  sample is neutral.
- **Instrumenting the inert framework**: match owner and authority by EXACT `GetMoveId()`
  (deterministic sampling, `id % 64 == 0`, on BOTH sides), never by clock; a `rewind` is always
  logged (rare), a `replay` only sampled (a rewind storm re-runs every pending move and
  floods the client log, which truncates at about 255 characters per line); counters aggregated at 1 Hz.
- **"Inert" applies to FLIGHT, not to the NETWORK**: custom types add payload per
  move and per correction, and a `Write`/`Read` asymmetry desyncs the owner. The payload gate exists
  for that.
- Evidence status: all confirmed at runtime in one flight. The engine
  instantiates the custom types and transports them, 94 sampled moves carried the exact 5 axes on
  both sides and 48 a non-zero payload, and 477 rewinds plus 47 replays were visible on the owner.
  Log parser trap: the DayZ script log wraps each `Print` in single quotes, so a log
  parser must strip the quote attached to the LAST token on the line or the payload gate
  gives a false FAIL on that field.
- CAVEAT measured on the same flight: the script contact chain received NOT ONE callback from
  the skids settling on the ground (0 `OnContact` across the whole flight, with a real touchdown by
  height above ground). Overriding `Car.OnContact` does not guarantee a callback for gentle settling
  contacts. Before building logic on vehicle contacts, first measure that the callback fires for the
  case at hand (a one-shot print); `EntityEvent.CONTACT` with `EOnContact` is the candidate robust
  path, not yet validated.

## Attack and release state must read the raw input

**[CODE-VERIFIED; in-game A/B pending]** A first-order command filter such as
`cmd += (raw - cmd) * k` decays asymptotically and does not reach exact zero. A
boolean derived from the filtered working value (`cmd != 0`) therefore remains
active after release: attack constants stay selected and idle-only levelling or
damping never starts. Capture `m_<axis>Raw` when the input is read, keep the
filtered command separate, and derive activity only from the raw field on every
simulation side. Owner and server must use the same source; mixing raw owner
state with filtered server state creates a second disagreement.

## Forced sleep needs a registration warm-up and a settled-state gate

- **[IN-GAME VERIFIED]** Do not call `dBodyActive(this,
  ActiveState.INACTIVE)` in the `EEInit` tick. The collider may not finish
  registration, leaving visual and physical position split. Keep the body active
  for a measured warm-up (about 3 s in the verified case) before the first sleep.
- **[DESIGN REVIEWED; partial in-game gate]** Sleep only when speed is near zero
  and the height above ground is at the local surface. Do not impose a lower bound on that
  height: a settled pivot measured `-0.02 m`. Explicitly request `ACTIVE` while the body is not
  settled; merely stopping the repeated `INACTIVE` call does not wake a body.
- A tuning helper that clamps a warm-up or threshold value only to a minimum
  (no such helper exists in vanilla; a mod writes its own) imposes no upper cap.
  Apply a safety maximum at the consumer with `Math.Min(tuned, cap)`.
