# Network ownership and vehicle physics

Who simulates a vehicle (the owner client, with the server reconciling), why a seat forced on the server is not ownership, why writing the pose fights the owner, how to derive angular velocity, and the rules for a custom `PawnMove` and `PawnOwnerState` pair. Per-tick events and what a passenger's client sees are in `runtime-state-and-sync.md`; driving a car from an automated test is in `test-stand-and-mcp.md`; the same classes on an aircraft are in `aviation-networking.md`.

## The owner drives the physics

Check this before driving or automating a car from a client, or reasoning about who drives.

- The car is a `Pawn`: `Transport extends Pawn` (`P:\scripts\3_game\vehicles\transport.c:66`), `Car extends Transport` (`P:\scripts\3_game\vehicles\car.c:87`), `CarScript extends Car` (`P:\scripts\4_world\entities\vehicles\carscript.c:94`). `FEATURE_NETWORK_RECONCILIATION` is always defined (`P:\scripts\1_core\defines.c:64`).
- The `IsOwner()` inside `CarScript.IsServerOrOwner()` (`carscript.c:2592`) is the car's network ownership, not the player's. The vanilla `Glossary` comment says it: "Owner: The client that is controlling the pawn" (`P:\scripts\3_game\entities\pawn.c:5` to `:8`).
- `IsServerOrOwner()` does not gate the throttle; it is used only for teardown and fluids (`carscript.c:552`, `:577`, `:845`). `SetThrottle` is native on `Car` (`car.c:191`) and is applied by whoever simulates the body, which is the owner. The only script call to `SetThrottle` (`carscript.c:1202`) sits in the debug autopilot under `#ifdef DIAG_DEVELOPER` (`carscript.c:1045`), so it never runs in a release build.
- A car with no client owner is `IsAuthorityOwner()`, simulated by the server with no owner (`pawn.c:199` and `:200`), so a server-side `SetThrottle` moves it. On one machine running server and client that is easy to mistake for the server driving client-owned cars; measured in game, the server moved an unowned car 2.29 m.
- A server-side `StartCommand_Vehicle`, as a test tool's "enter vehicle" command uses, seats the player on the server only. The client never gets `GetCommand_Vehicle()` nor ownership of the car (measured in game six times). A real get-in, `ActionGetInTransport.Start()` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:71`), runs `StartCommand_Vehicle` on the client's player and reserves the seat through `SetVehicle` and `AddInventoryJunctureEx` (`:147`, `:150`). The ownership transfer is native; script has no `SetNetworkOwner`.
- So to drive or measure on the owner side from a client, the client must take ownership itself with a client-side get-in. A single machine test of owner authority is unreliable, because the client never truly owns; use a dedicated server with a remote client that gets in.
- Readings to log: `IsOwner()` (`pawn.c:194`), `IsAuthorityOwner()` (`pawn.c:200`), `GetOwnerIdentity()` (`pawn.c:209`), `GetNetworkID()` (`P:\scripts\3_game\entities\object.c:819`).

## Driving the owner side from script

`Car.SetThrottle`, `SetSteering` and `SetBrake` called from the mission (`OnUpdate` or a job) do not move a car its owner simulates: the `super` of `CarScript.OnInput(dt)` (`carscript.c:1041`) overwrites them every frame with the local driver's input, which is 0. Apply them inside a `modded class CarScript` `OnInput`, after `super.OnInput(dt)`, where the vanilla debug autopilot does it (`carscript.c:1202`). Vehicle input is native, so `HumanInputController` offers no way in. Measured in game from 0 to 39 km/h.

## Angular velocity is not yaw, pitch and roll

`dBodySetAngularVelocity` takes rotation around x, y and z. Vanilla says so: "Angular velocity, rotation around x, y and z axis (not yaw/pitch/roll)" (`P:\scripts\1_core\proto\enphysics.c:163`). The axis map is yaw on Y, pitch on Z, roll on X. Two vanilla sources agree: the `YawPitchRollMatrix("70 15 45", mat)` example (`P:\scripts\1_core\proto\enmath3d.c:127`), and the vehicle camera, which reads `dBodyGetAngularVelocity(vehicle)` and routes Y to yaw, Z to pitch and X to roll (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:128` to `:134`).

The `mat[i]` filled by `GetTransform` (`P:\scripts\1_core\proto\enentity.c:288`) and by `YawPitchRollMatrix` are world-space basis vectors (columns), not rows. Mixing them up flips the sign of any rotation derived from them.

A solver that keeps rate values in degrees per second (`m_PitchRate`, `m_RollRate`, `m_YawRate`) cannot feed them as angular velocity once a later step moves the pose without them (a levelling stabiliser, a cosmetic sway, a take-off level assist). The next `SetOrientation` contradicts the rotation, and the body judders against the pose. Derive angular velocity from the real pose change instead:

```c
GetTransform(before);
SetOrientation(target);
GetTransform(after);
// w * dt = 1/2 * sum over the three basis vectors of (b_i x a_i)
dBodySetAngularVelocity(this, sum * (0.5 / dt));
```

This is exact to third order while the change per tick stays under 6 degrees, ignores steps that move the pose on their own, and gives zero wherever the commanded pose equals the sampled one. If `SetOrientation` does not refresh the transform in the same tick, `after` equals `before` and the result is zero, the same as before the change.

## Writing the pose fights owner prediction

Check this for any "input lag", rubber-banding or "the client reverts transforms" on a `CarScript` the server steers.

- Measure the strategy first, on either side: `Print(GetNetworkMoveStrategy().ToString())`. The values are `NONE` 0, `LATEST` 1 and `PHYSICS` 2 (`pawn.c:138` to `:148`); the getter is native and open to script (`pawn.c:218`). `CarScript` ran `PHYSICS` by default on the pilot's client, measured on DayZ 1.29; no config key selects it, in vanilla or in DayZ Expansion, because the engine sets it by native class.
- Under `PHYSICS` the owner already simulates ahead with the full `Pawn` contract (`ObtainMove`, `ConsumeMove`, `ReplayMove`, `RewindState`, `pawn.c:256` to `:329`; the `CarScript` hooks at `carscript.c:2568` to `:2588`). So:
  1. A server that writes pose or velocity each tick (`SetOrientation`, `SetVelocity`) keeps correcting the owner, which shows as built-in round-trip lag and snap-backs, even on one machine.
  2. A transform written on the owner client reverts in about 0.3 s (measured in game). That is reconciliation working, not a bug.
  3. The compatible path, which DayZ Expansion uses from its 1.28 release (its own scripts, not vanilla): apply the same forces on owner and server with `dBodyApplyForce` (`enphysics.c:146`, world space), carry the input inside the native `PawnMove`, and add a custom move and owner state that call `super` first. The engine integrates; nobody writes the pose.
- Before committing to that design, test it cheaply: a tuning flag off by default, and a 1.5 s window in which both sides apply the same force (anti-gravity plus a sideways pulse on an axis nothing else touches) while the server pauses its pose writer, with per-tick traces on both sides and an offline parser that answers yes, no or inconclusive. Abort the same way on every exit (engine, seat, flight state), suppress the borrowed key before anything else reads it, and clear the window on any exit from flight.
- Measured on a test helicopter: three clean pulses on the owner (about 1.6 m/s² against 1.5 expected, at most a 30 percent brief reversal from the owner to server offset). The snap-back when the window closed was the pose writer taking over again. A pulse on the owner only, near the ground with the server not armed, reverted 91 percent. The pilot felt nothing at 0.15 g sideways, so judge by the traces, not by feel.

## A custom move and owner state

When the design is forces plus owner prediction, first build the custom types with hooks that only log and leave flight alone. That checks the engine wiring before any solver moves.

- Derive from the last class of each chain: `PawnMove`, `TransportMove`, `CarMove`, `CarScriptMove`, and `PawnOwnerState`, `TransportOwnerState`, `CarOwnerState`, `CarScriptOwnerState` (`transport.c:11` to `:50`; `car.c:78` to `:82`; `carscript.c:57` to `:74`). `TransportOwnerState` and `TransportMove` already carry the native transform and linear and angular velocity (`transport.c:13` to `:23`, `:35` to `:42`); do not copy them into your own state.
- The hooks are protected events (`pawn.c:238` to `:311`). `GetMoveType` and `GetOwnerStateType` are read at construction (`pawn.c:235`, `:244`), so the overrides must exist on the class from the start. Then `ObtainMove`, `ConsumeMove`, `ReplayMove` (returns `bool`; honour a refusal from `super` before your own work), `ObtainState` and `RewindState(state, move, inout NetworkRewindType)`. `CarScript` already implements the type getters, `ObtainState` and `RewindState` (`carscript.c:2568` to `:2588`); call `super` always and exactly once, because its `ObtainState` and `RewindState` carry `m_fTime`.
- In `Write` and `Read`, call `super` first, and never serialise a `vector`; write its three floats. `EstimateMaximumSize()` is `super` plus 4 bytes per value, a `bool` counted as 4.
- The move carries the raw axes before any scaling by authority, since attenuation and state machines are worked out again on each tick and baking them in breaks replay. Latched solver memory goes in the owner state, server to owner, not in the move.
- Read the raw local input inside `ObtainMove`. Script cannot see the native order of `ObtainMove` and `EOnSimulate`, so relying on the tick's last read can send zeroes or old values, and round-trip checks then pass on empty wiring. Make the payload check reject a run where every sample is neutral.
- To log the framework, pair owner and authority by exact `GetMoveId()` on both sides (for example `id % 64 == 0`), never by clock. Log every rewind, since they are rare, but only sample replays: a burst of rewinds replays every pending move and floods the client log, which cuts lines at about 255 characters. Sum counters once a second.
- Inert in flight is not inert on the network: custom types add payload to every move and correction, and a `Write` and `Read` mismatch desyncs the owner.
- Measured in one flight: the engine created and sent the custom types, 94 sampled moves carried the exact five axes on both sides (48 with a non-zero payload), and the owner saw 477 rewinds and 47 replays. The script log wraps each `Print` in single quotes, so strip the quote from the last token on a line or the payload check fails that field.

## Contacts while settling

On the same flight the script contact callbacks never fired for the skids settling on the ground: no `OnContact` call across the whole flight, with a real touchdown. Overriding `Car.OnContact` does not promise a call for a gentle settling contact. Before building logic on vehicle contacts, print once to prove the callback fires for your case. `EntityEvent.CONTACT` with `EOnContact` is the likely sturdier path, not yet tested.

## Input state and sleeping the body

- Decide attack and release from the raw input. A first-order filter such as `cmd += (raw - cmd) * k` never reaches exactly zero, so a flag taken from the filtered value (`cmd != 0`) stays on after release: attack constants stay selected and idle levelling never starts. Store the raw axis when it is read, keep the filtered command apart, and take activity from the raw value on every simulating side. Owner and server must use the same source. Checked in code; not yet compared in game.
- Do not call `dBodyActive(this, ActiveState.INACTIVE)` in the `EEInit` tick. The collider may not have finished registering, which splits the visual and physical position. Keep the body active for a measured warm-up, about 3 s in the tested case, before the first sleep (measured in game).
- Sleep only when speed is near zero and the height above ground is at the local surface. Set no lower bound on that height, since a settled pivot measured -0.02 m. Ask for `ACTIVE` explicitly while the body is not settled; stopping the repeated `INACTIVE` call does not wake it. Reviewed in design, partly checked in game.
- A tuning helper that clamps a warm-up or threshold only from below sets no upper limit (vanilla has no such helper; mods write their own). Cap it where it is used with `Math.Min(tuned, cap)`.
