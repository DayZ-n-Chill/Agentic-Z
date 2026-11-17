# Aircraft networking: prediction, ownership and the pilot's camera

How a scripted aircraft on `CarScript` stays smooth for its pilot: the vanilla Pawn classes and events, the move strategy a car reports, what a full owner prediction pipeline needs, when ownership really changes hands, and why the pilot's own camera must not be smoothed. Vanilla facts cite `P:\` (1.30 scripts). Results measured in the LFHeli helicopter project and facts read from shipped mods (RFFS, MH6, LM_Planes, Expansion) are marked and are not checked on `P:\`.

## The vanilla pieces

All of it sits inside `#ifdef FEATURE_NETWORK_RECONCILIATION` (`P:\scripts\3_game\entities\pawn.c:1`). The glossary there: the authority is the server, the owner is the client controlling the pawn, a proxy is any other client.

| Piece | What it is | Where |
|---|---|---|
| `PawnOwnerState` | The full state sent to the owner when a desync is detected, which triggers a replay; `Write`, `Read` and `EstimateMaximumSize` are the script hooks | `P:\scripts\3_game\entities\pawn.c:25` |
| `PawnMove` | One move: used on the owner and sent to the authority, which consumes and plays the same move | `P:\scripts\3_game\entities\pawn.c:83` |
| `NetworkMoveStrategy` | `NONE`, `LATEST`, or `PHYSICS` ("sends over a fixed buffer of moves and re-simulates the physics steps on correction") | `P:\scripts\3_game\entities\pawn.c:138-148` |
| `NetworkRewindType` | `NOT_SET`, `DROP`, `REPLAY`, `ADDITIVE` | `P:\scripts\3_game\entities\pawn.c:154-168` |
| `IsOwner`, `IsAuthority`, `IsProxy` | Which role this machine has for the pawn | `P:\scripts\3_game\entities\pawn.c:194-203` |
| `GetNetworkMoveStrategy` | The strategy the pawn is reconciled with on the owner | `P:\scripts\3_game\entities\pawn.c:218` |
| `GetOwnerStateType`, `GetMoveType` | Return the state and move classes the pawn uses | `P:\scripts\3_game\entities\pawn.c:238-250` |
| `ObtainMove` | Owner fills the move with its inputs | `P:\scripts\3_game\entities\pawn.c:256` |
| `ConsumeMove` | Authority applies the move's inputs | `P:\scripts\3_game\entities\pawn.c:274` |
| `ReplayMove`, `SimulateMove` | Owner replays and simulates a move after a correction | `P:\scripts\3_game\entities\pawn.c:283-294` |
| `ObtainState`, `RewindState` | Snapshot the state; set the entity back to a received state | `P:\scripts\3_game\entities\pawn.c:300-312` |
| `TransportOwnerState`, `TransportMove` | Native transform, linear and angular velocity, buoyancy | `P:\scripts\3_game\vehicles\transport.c:11-23` and `P:\scripts\3_game\vehicles\transport.c:33` |
| `CarScriptOwnerState`, `CarScriptMove` | The classes to extend for an aircraft on `CarScript`; vanilla adds only `m_fTime` | `P:\scripts\4_world\entities\vehicles\carscript.c:57` and `P:\scripts\4_world\entities\vehicles\carscript.c:72` |

`CarScript` already overrides `GetOwnerStateType`, `GetMoveType`, `ObtainState` and `RewindState` (`P:\scripts\4_world\entities\vehicles\carscript.c:2568-2588`), so an aircraft's overrides call `super` first. `Transport` itself is commented as using `NetworkMoveStrategy.NONE` (`P:\scripts\3_game\vehicles\transport.c:65`).

`IsServerOrOwner()` is how `CarScript` picks who simulates: the server always, and the owner only when the strategy is `PHYSICS` (`P:\scripts\4_world\entities\vehicles\carscript.c:2592-2601`).

## A car is reconciled with PHYSICS, so the owner must predict

Measured in LFHeli on 2026-07-14, in game on 1.29: a `CarScript` child reports `GetNetworkMoveStrategy() == NetworkMoveStrategy.PHYSICS` on the owner client (the probe printed 2). The engine expects the owner to predict and reconcile. Probe the strategy on the client before choosing a network model.

What does not work under `PHYSICS`:

- **A client mirror** (pumping `EOnSimulate` and `EOnPostSimulate` from `EOnFrame`, RFFS style) does not advance the pose. `super.EOnSimulate` is empty, and pumping `EOnPostSimulate` runs the car's engine and fluid logic on the owner, where its `m_Time` ran about 5 times fast.
- **Partial owner prediction** (the solver behind `IsServerOrOwner` without the Pawn hooks) still snaps on corrections and desyncs; a crash produced a hard teleport.

What works is the full Pawn pipeline:

1. A move class and an owner state class of the aircraft's own, both calling `super` and both implementing `EstimateMaximumSize`.
2. `ObtainMove`, `ConsumeMove` and `ReplayMove` carrying the raw inputs, not an attenuated buffer and not state the flight state machine has already changed.
3. `RewindState` calling `super` first, with a guard for `NetworkRewindType.ADDITIVE`.
4. The solver run once, in `EOnSimulate`, behind `IsServerOrOwner`.
5. Tuning values sent to the owner through a guaranteed RPC handshake: the values, an acknowledgement, then `ForceCorrection`.

LM_Planes, MH6 and Expansion ship this pattern (state and move classes on `CarScriptOwnerState` and `CarScriptMove`); their layouts are in the `dayz-aviation` skill's `references/fixed-wing-lm-planes.md`, `references/helicopter-mh6.md` and `references/helicopter-expansion.md`. RFFS and SIB sync with plain net sync variables and a server only solver instead.

Rules for the replay (LFHeli lessons; full text in the skill's `references/flight-testing-and-measurement.md`): class every field the solver reads during a replay as restored, recomputed after the handshake, or always initialised, and never initialise gains or derived tables only on the server; retry the handshake until it is acknowledged, because crew, possession and spawn are asynchronous; and use the move itself as the scripted pilot channel instead of a second RPC.

## ForceCorrection corrects the vehicle, never a seated character

`ForceCorrection` is documented as "Force a correction to the owner as a server only event was called (called on authority only)" (`P:\scripts\3_game\entities\pawn.c:205-206`). The state it rewinds is the vehicle's `TransportOwnerState`: transform, velocities and buoyancy (`P:\scripts\3_game\vehicles\transport.c:11-23`). Vanilla never calls it: the declaration is its only occurrence in `P:\scripts`.

- A character's get-out pose comes from `GetOutVehicle()` or `JumpOutVehicle()` on the vehicle command (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:183-185`), not from a correction.
- `Synchronize()` on `Transport` "synchronizes car's state in case the simulation is not running" (`P:\scripts\3_game\vehicles\transport.c:171-172`). No vanilla script on `P:\` calls it on a vehicle.

## The RFFS client pump is not a smoothing mechanism

RFFS re-enters `EOnSimulate(0.025)` from `EOnFrame` on the client (`RFFSHeli_Core.c:1008-1016`), but that never reaches the pose: its `FlightSimulation()` is gated on `IsServer() && m_heli_state == 2` (`RFFSHeli_Core.c:1149-1156`), so the pump only advances `ExecuteAnimations()` and `KeyboardInputClient()` (`RFFSHeli_Core.c:1143-1145`). Do not copy the pump expecting a smoother picture. Proxy pose smoothness in RFFS is native car replication. (LFHeli, 2026-08-03.)

## Never smooth the pilot's own camera

Refuted in LFHeli with data and with feel in two iterations (2026-08-03). A spring or spike filter on the seat camera delays exactly the feedback the pilot steers by: the pitch response lagged ("one tap dropped the nose hard", as the pilot put it) and the jerk distribution became more intermittent (the 95th percentile of the root delta rose 14.65 percent with a 0.14 s spring).

It also stacks with a lag vanilla already has: the third person vehicle camera smooths its offset and orientation with `Math.SmoothCD` and `Math.SmoothCDPI2PI` over 0.3 s (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:142-148`), so a custom smoother is a second spring fighting the first.

Fix presentation in the cockpit or shell visual or in the network layer, never in the flying player's camera. Passenger and spectator cameras are a separate question.

## Ownership is measured in flight, not at the mount event

`IsOwner()` sampled at the mount event (`OnCommandVehicleStart`, `P:\scripts\4_world\entities\manbase\playerbase.c:4342`, or a get-in hook) reads too early: the transfer lands after the get-in completes. LFHeli measured owner false at mount, then owner true in 3,404 of 3,404 samples in flight across four flights, with the strategy at `PHYSICS`. Vanilla hands the pawn over in `OnVehicleSeatDriverEnter` with `identity.Possess(pawn)` (`P:\scripts\4_world\entities\manbase\playerbase.c:4561-4577`). Any branch that depends on the role (a proxy path, a "is driver" trick) must be decided from a probe taken in flight.

## Two ways shipped helicopters replicate

| Way | Who | Notes |
|---|---|---|
| Net sync variables, solver on the server only | RFFS, SIB | A bank of `RegisterNetSyncVariable*` calls in the constructor plus `SetSynchDirty()` on every change; the pose is native car replication. RFFS packs about 12 config booleans into one int (`RFFSHeli_Core.c:334-345`). |
| Custom Pawn state and move, owner prediction | MH6, LM_Planes, Expansion | Continuous flight state rides the Pawn state; MH6 keeps two net sync variables for the toggles every observer must see (`MH6_flightmodel.c:243-244`). |

The general net sync rules are in `skills/_shared/enscript/patterns/netsync.md`.
