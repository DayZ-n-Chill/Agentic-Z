# Physics over the network

Covers what the engine sends to clients about a moving object, why a vehicle moves smoothly for everyone and a free body on an item does not, which machine simulates what, and what physics work can leave the server.

The vehicle script API itself (crew, controls, fluids, contact damage) is in `_shared/vehicles/`; who owns a vehicle's physics over the network is in `_shared/vehicles/network-physics-ownership.md`.

## A body collides only where it exists

Each machine has its own physics world. A body created by script on the server exists on the server. A client sees the entity move only through what the engine replicates for that kind of entity, and collides only with what exists in its own world. That is why players walk through a body made on the server (`player-controller.md`).

## What replicates, by kind of entity

| Entity | What clients receive | Source |
|---|---|---|
| A vehicle (`Transport`) | A continuous movement stream to every client (engine behavior, not visible on `P:\`; confirm in game). The owner also gets an occasional full state when its moves desync: world transform, linear and angular velocity | `TransportOwnerState`, `P:\scripts\3_game\vehicles\transport.c:11` to `:23`; "infrequently sent to the owner when there is a desync", `P:\scripts\3_game\entities\pawn.c:20` to `:23`. `Transport extends Pawn` only under `#ifdef FEATURE_NETWORK_RECONCILIATION` (`transport.c:9`, `:66`); otherwise it extends `EntityAI` (`:68`) |
| A thrown or dropped item | Simulated on the server and on the owner's client; other clients get the result | `HandActionThrow`, `P:\scripts\3_game\systems\inventory\hand_actions.c:77` to `:81` |
| Any `EntityAI` | Sync variables you register, sent when they change; position is not one of them | `RegisterNetSyncVariableBool`, `P:\scripts\3_game\entities\entityai.c:2832`; `SetSynchDirty`, `:3064` |

- `Pawn` is the engine's type for an entity with continuous network movement; its owner state exists to correct a desync by replaying moves (`PawnOwnerState`, `P:\scripts\3_game\entities\pawn.c:20` to `:25`). `Transport` supplies its own state and move types (`GetOwnerStateType`, `P:\scripts\3_game\vehicles\transport.c:160`) and uses `NetworkMoveStrategy.NONE` (the comment at `:65`).
- `ItemBase` is not a `Pawn`. A dynamic body put on an item by script is simulated on the server; clients get occasional position updates and never a velocity (engine behavior, not visible on `P:\`; confirm in game). It can look smooth in a local test at low latency and still stutter on a real server.
- Vehicle contact handling runs on the server (`Transport.OnContact` checks `IsServer()`, `P:\scripts\3_game\vehicles\transport.c:315` to `:317`).

## `Synchronize()` does not move anything

- `Transport` has a native `Synchronize()`: "Synchronizes car's state in case the simulation is not running" (`P:\scripts\3_game\vehicles\transport.c:171` and `:172`). Vanilla calls it only on the server after a part is attached or detached (`P:\scripts\4_world\entities\vehicles\carscript.c:514` and `:515`, `:593` and `:594`; `P:\scripts\4_world\entities\vehicles\motorbikescript.c:551` to `:554`, `:594` to `:597`).
- It does not wake a vehicle. A sleeping vehicle moved with `SetPosition` plus `Synchronize()` reaches no client until it wakes (measured in game; not checked on `P:\`). How to keep a vehicle awake on a moving platform is in `player-controller.md`, section "Riding a moving platform".
- `ItemBase` has no native call of this kind. The native `Synchronize()` on `Weapon` sends weapon state, not movement (`P:\scripts\4_world\entities\core\inherited\weapon.c:8` to `:11`), and the script `Synchronize()` methods on some items only push their own sync variables (for example `P:\scripts\4_world\entities\itembase\barbedwire.c:109`).

## Options for a mod object that must move for everyone

| Option | Cost |
|---|---|
| Use the native throw path (`ThrowPhysically`) | Cheapest. The body exists on the server and the owner; keep its lifetime alive (`drop-and-throw.md`). |
| Move it yourself: read position and velocity on the server each tick and send them by RPC; the client applies `SetPosition` and `SetVelocity` | Correct, but costs network traffic and script time. |
| Make it a `Transport` | Replicates for free, but needs a `CfgVehicles` class with a `SimulationModule` and a fitting model. Vehicle work goes to dayz-vehicle-specialist. |
| A separate entity moved from the same clock on server and clients | Works for lifts and platforms (`player-controller.md`). |

## Which machine simulates

- Classic vehicle networking simulates on the server. With `NetworkMoveStrategy.PHYSICS` the driving client simulates too: `CarScript.IsServerOrOwner()` returns `IsOwner()` in that case (`P:\scripts\4_world\entities\vehicles\carscript.c:2592`). The strategies are `NONE`, `LATEST` and `PHYSICS` (`enum NetworkMoveStrategy`, `P:\scripts\3_game\entities\pawn.c:138`).
- Owner prediction does not remove server work. The server consumes and replays the owner's move (`ConsumeMove`, `P:\scripts\3_game\entities\pawn.c:274`), and the native comparison runs beside the script one, with the higher result used (the `CompareMove` doc, `:261` to `:265`). A script `CompareMove` that always approves cannot switch corrections off.

## Taking physics load off the server

- Gameplay physics stays on the server. Script has no call into a native extension: no `callExtension`, `LoadLibrary` or `DllImport` anywhere in `P:\scripts`. The only way out of the process is `RestApi`: `GET` and `POST` with a callback (`P:\scripts\3_game\http\restapi.c:103`, `:123`), or `GET_now` and `POST_now`, which block the thread (`:108`, `:128`). None of that is usable for a physics step.
- Cosmetic physics can run on each client. `ECE_LOCAL` creates an object on that machine only (`P:\scripts\3_game\ce\centraleconomy.c:25`); vanilla creates a local preview object with collision using `ECE_LOCAL | ECE_CREATEPHYSICS` (`P:\scripts\5_mission\gui\scriptconsoleitemstab.c:696`), and creates its client side particles the same way (`P:\scripts\3_game\particles\particle.c:119`). On a multiplayer client, `CreateObjectEx` without `ECE_LOCAL` returns null (measured in game; not checked on `P:\`). Unverified (not tested in game): whether a local object accepts a dynamic body.
- Measure before you move anything. `EnProfiler` profiles script only (the `-profile` launch parameter, `P:\scripts\1_core\proto\enprofiler.c:63`). Native physics cost shows only as server CPU or frame rate with and without the load.
