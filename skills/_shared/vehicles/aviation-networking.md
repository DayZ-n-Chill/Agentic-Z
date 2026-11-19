# Aircraft networking

How a scripted aircraft on `CarScript` stays smooth for its pilot: the vanilla Pawn classes and events, the move strategy a car reports, what full owner prediction needs, when ownership actually changes hands, and why the pilot's own camera must not be smoothed.

Vanilla facts cite `P:\`. Results measured in game on a test helicopter built on `CarScript`, and facts read from shipped mods (RFFS, MH6, LM_Planes, Expansion), say so and are not checked on `P:\`. Ground vehicle notes on ownership against a forced seat are in `network-physics-ownership.md`.

## The vanilla pieces

All of it sits inside `#ifdef FEATURE_NETWORK_RECONCILIATION` (`P:\scripts\3_game\entities\pawn.c:1`). In its terms the authority is the server, the owner is the client controlling the pawn, and a proxy is any other client.

| Piece | What it is | Where |
|---|---|---|
| `PawnOwnerState` | The full state sent to the owner when a desync is found, which starts a replay; script hooks `Write`, `Read`, `EstimateMaximumSize` | `pawn.c:25` |
| `PawnMove` | One move: used on the owner, sent to the authority, which consumes and plays the same move | `pawn.c:83` |
| `NetworkMoveStrategy` | `NONE`, `LATEST`, or `PHYSICS` ("sends over a fixed buffer of moves and re-simulates the physics steps on correction") | `pawn.c:138` to `:148` |
| `NetworkRewindType` | `NOT_SET`, `DROP`, `REPLAY`, `ADDITIVE` | `pawn.c:154` to `:168` |
| `IsOwner`, `IsAuthority`, `IsProxy` | This machine's role for the pawn | `pawn.c:194` to `:203` |
| `GetNetworkMoveStrategy` | The strategy the owner reconciles with | `pawn.c:218` |
| `GetOwnerStateType`, `GetMoveType` | Return the state and move classes | `pawn.c:238` to `:250` |
| `ObtainMove` | The owner fills the move with its input | `pawn.c:256` |
| `ConsumeMove` | The authority applies the move's input | `pawn.c:274` |
| `ReplayMove`, `SimulateMove` | The owner replays and simulates a move after a correction | `pawn.c:283` to `:294` |
| `ObtainState`, `RewindState` | Take a snapshot; set the entity back to a received state | `pawn.c:300` to `:312` |
| `TransportOwnerState`, `TransportMove` | Native transform, linear and angular velocity, buoyancy | `P:\scripts\3_game\vehicles\transport.c:11` to `:23`, and `:33` |
| `CarScriptOwnerState`, `CarScriptMove` | The classes an aircraft extends; vanilla adds only `m_fTime` | `P:\scripts\4_world\entities\vehicles\carscript.c:57` and `:72` |

`CarScript` already overrides `GetOwnerStateType`, `GetMoveType`, `ObtainState` and `RewindState` (`carscript.c:2568` to `:2588`), so call `super` first in an aircraft's overrides. `Transport` is commented as using `NetworkMoveStrategy.NONE` (`transport.c:65`). `IsServerOrOwner()` decides who simulates a car: the server always, the owner only when the strategy is `PHYSICS` (`carscript.c:2592` to `:2601`).

## A car is reconciled with PHYSICS

Measured in game on DayZ 1.29: a `CarScript` child reports `GetNetworkMoveStrategy() == NetworkMoveStrategy.PHYSICS` on the owner client (the probe printed 2). The engine expects the owner to predict and reconcile. Probe the strategy on the client before you choose a network model.

What does not work under `PHYSICS`:

- A client mirror, pumping `EOnSimulate` and `EOnPostSimulate` from `EOnFrame` the RFFS way, does not move the pose. `super.EOnSimulate` is empty, and pumping `EOnPostSimulate` runs the car's engine and fluid code on the owner, where its `m_Time` ran about five times too fast.
- Partial owner prediction, the solver behind `IsServerOrOwner` without the Pawn hooks, still snaps on corrections and desyncs; a crash gave a hard teleport.

What works is the full Pawn chain:

1. The aircraft's own move class and owner state class, both calling `super` and both implementing `EstimateMaximumSize`.
2. `ObtainMove`, `ConsumeMove` and `ReplayMove` carrying the raw input, not a smoothed buffer and not state the flight state machine has already changed.
3. `RewindState` calling `super` first, with a guard for `NetworkRewindType.ADDITIVE`.
4. The solver run once, in `EOnSimulate`, behind `IsServerOrOwner`.
5. Tuning values sent to the owner by a guaranteed RPC handshake: the values, an acknowledgement, then `ForceCorrection`.

LM_Planes, MH6 and Expansion ship this, with state and move classes on `CarScriptOwnerState` and `CarScriptMove`; their layouts are in `aviation-fixed-wing.md`, `helicopter-mh6.md` and `helicopter-expansion.md`. RFFS and SIB use plain synced variables and a server only solver instead.

For replays: mark every field the solver reads as restored, recomputed after the handshake, or always set up, and never set up gains or derived tables only on the server; retry the handshake until it is acknowledged, since crew, possession and spawn arrive out of order; and carry a scripted pilot's input in the move itself rather than a second RPC. The full rules are in `aviation-flight-testing.md`.

## ForceCorrection moves the vehicle, never a seated character

The vanilla comment on `ForceCorrection()` reads "Force a correction to the owner as a server only event was called (called on authority only)" (`P:\scripts\3_game\entities\pawn.c:205` and `:206`). What it rewinds is the vehicle's `TransportOwnerState`: transform, velocities and buoyancy (`transport.c:11` to `:23`). Vanilla never calls it; the declaration is its only occurrence in `P:\scripts`.

- A character's get-out pose comes from `GetOutVehicle()` or `JumpOutVehicle()` on the vehicle command (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:183` to `:185`), not from a correction.
- `Synchronize()` on `Transport` "Synchronizes car's state in case the simulation is not running" (`transport.c:171` and `:172`). Vanilla calls it on the server after a part is attached or detached (`carscript.c:515` and `:594`); it does not correct an owner's prediction.

## The RFFS client pump does not smooth anything

RFFS re-enters `EOnSimulate(0.025)` from `EOnFrame` on the client (`RFFSHeli_Core.c:1008` to `:1016`), but that never reaches the pose: its `FlightSimulation()` runs only when `IsServer() && m_heli_state == 2` (`RFFSHeli_Core.c:1149` to `:1156`), so the pump only advances `ExecuteAnimations()` and `KeyboardInputClient()` (`RFFSHeli_Core.c:1143` to `:1145`). Do not copy it hoping for a smoother picture. What other players see smoothly in RFFS is the car's native replication.

## Never smooth the pilot's own camera

A spring or spike filter on the seat camera delays the very feedback the pilot steers by. On the test helicopter, pitch response lagged (one tap dropped the nose hard) and the jerk came in bursts: the 95th percentile of the root change rose 14.65 percent with a 0.14 s spring, and it felt worse.

It also stacks on a lag vanilla already has: the third person vehicle camera smooths its offset and orientation with `Math.SmoothCD` and `Math.SmoothCDPI2PI` over 0.3 s (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:142` to `:148`), so a custom smoother is a second spring fighting the first.

Fix what the pilot sees in the cockpit model or in the network layer, never in the flying player's camera. Passenger and spectator cameras are a separate question.

## Read ownership in flight, not at mount

`IsOwner()` read at the mount event (`OnCommandVehicleStart`, `P:\scripts\4_world\entities\manbase\playerbase.c:4342`, or a get-in hook) is too early: the hand-over lands after the get-in completes. On the test helicopter, owner was false at mount, then true in 3,404 of 3,404 samples in flight over four flights, with the strategy at `PHYSICS`. Vanilla hands the pawn over in `OnVehicleSeatDriverEnter` with `identity.Possess(pawn)` (`playerbase.c:4561` to `:4577`). Decide any branch that depends on the role (a proxy path, an "is driver" check) from a reading taken in flight.

## Two ways shipped helicopters replicate

| Way | Who | Notes |
|---|---|---|
| Synced variables, server only solver | RFFS, SIB | A bank of `RegisterNetSyncVariable*` calls in the constructor and `SetSynchDirty()` on every change; the pose is the car's native replication. RFFS packs about 12 config booleans into one int (`RFFSHeli_Core.c:334` to `:345`). |
| Own Pawn state and move, owner prediction | MH6, LM_Planes, Expansion | Continuous flight state travels in the Pawn state; MH6 keeps two synced variables for the toggles every observer must see (`MH6_flightmodel.c:243` and `:244`). |

The general rules for synced variables are in `_shared/enscript/patterns/netsync.md`.
