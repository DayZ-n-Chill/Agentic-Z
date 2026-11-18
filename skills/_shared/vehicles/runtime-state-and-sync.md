# Runtime state and sync

Which per-tick event a car runs, what a passenger's client reads for engine state, why script visual state is missing on a fresh spawn, and how to probe a vehicle that draws or gets out in the wrong place.

Facts measured in game were taken on test vehicles built on `CarScript`, a helicopter and a car; they say so where they apply.

## Per-tick events

The `CarScript` constructor registers `EntityEvent.POSTSIMULATE` and `EntityEvent.POSTFRAME` and nothing else (`P:\scripts\4_world\entities\vehicles\carscript.c:207` and `:208`), and its per-tick work runs in `EOnPostSimulate` (`:807`). `EOnSimulate` is an empty stub on the base entity (`P:\scripts\1_core\proto\enentity.c:201` to `:203`), so `super.EOnSimulate` does nothing on a car. Hook `EOnPostSimulate` for per-tick logic on a car.

`BoatScript`, unlike `CarScript`, overrides both `EOnPostSimulate` (`P:\scripts\4_world\entities\vehicles\boatscript.c:355`) and `EOnSimulate` (`:393`).

Vanilla runs much of its `EOnPostSimulate` work on the owner client too, but a mod's checks that depend on replicated items, such as `CheckVitalItem`, must stay on the server.

A custom flight loop that needs `EOnSimulate` must add `SetEventMask(EntityEvent.SIMULATE)` itself; see `aviation-carscript-base.md`, section "Where the flight loop runs". What 1.30 changed for vehicles is in `dayz-1-30-vehicles.md`.

## Engine state on a passenger's client

`EngineIsOn()` is native on `Car` (`P:\scripts\3_game\vehicles\car.c:230`). On a client that does not own the vehicle it returns `false` even while the server has the engine running, with no warning. Measured in game on a passenger seat: in the same frame the native value read `false` and a replicated copy read `true`, and the server log showed no stop. Any client feature gated on `EngineIsOn()` switches itself off; a thermal camera died the moment the passenger sat down.

Replicate the state yourself: a `RegisterNetSyncVariableBool` written in `OnEngineStart` and `OnEngineStop`, and have every client path read the native value or the replicated one. A snapshot held only on the owner does not reach passengers. When a client check decides to turn something off, print both values in the same frame.

## A vehicle drawn where it is not

When a vehicle draws somewhere the entity is not (the body on the ground while the vehicle climbs, a part left behind, a piece floating), logging transforms finds nothing. Measured in game over a 26 m climb: root position, `GetRenderTransform`, both bones, the physics body (`dBodyGetWorldTransform`) and the pilot's position all agreed to the digit while the hull was drawn on the ground. Any probe derived from the entity's root shares the root's blind spot, because the drawing fault lies after every transform script can read.

What works is a marker the engine places from a world point without the entity's transform, read off a screenshot: `Debug.DrawSphere` at `GetPosition()` plus a column of markers at fixed spacing below it. The spacing turns the gap into metres (markers times spacing) instead of an impression.

Check a probe before you trust it. Read it where the drawing is right (on the ground) and where it is wrong (in the air). If the value does not change while the eye sees a difference, the value is blind; stop using it. A difference of exactly `0.000` means the probe measures itself, not that it is precise.

Over flat ground, "the drawn height is frozen at take-off" and "the transform is computed from a height above ground" give the same two signs: the gap grows with height and goes back to zero on landing. So the flat ground result rules nothing out. Change the situation instead:

- Fly level at a constant height over ground at least 15 m lower. A height above ground follows the terrain; a frozen height does not.
- Descend without touching down, then climb again. A split between replicated and local state lags behind; a pure function of height does not.

These two manoeuvres have not been run in game yet; treat them as an untested procedure.

## Getting out at the wrong place

With `NetworkMoveStrategy.PHYSICS`, the former owner falls back on get-out to the last proxy snapshot it received before it took the seat, and gets no further server transform. A client `SetPosition` or a server nudge does not repair it: a client `SetPosition` had no effect, and a 10 cm server lift had not arrived 25 seconds later (measured in game).

What repairs it: about 500 ms after `OnDriverExit`, on the server and only when every crew seat is empty, rebuild the remote copy with `RemoteObjectTreeDelete` and `RemoteObjectTreeCreate` (`P:\scripts\3_game\global\game.c:708` and `:710`). Measured in game: 3 of 3 re-entries clean, with client and server positions within 0.12 m and 0.11 m. Schedule it from the server object that survives and cancel it if that object is deleted; a `CallLater` owned by the client copy that gets destroyed cannot finish safely.

To find the fault in one flight, add a one-shot probe in `OnDriverExit` that prints, on both client and server, the player position, the vehicle position, the crew entry point and the distances between them. A good exit has client equal to server. A bad exit has the client showing the vehicle at its spawn pose, sunk, and the player underground, while the server is right. Line up the client and server clocks with a pair of events both sides log (the two exit lines gave a steady offset), then compare against the owner's position log to find when they split. The ownership side is in `network-physics-ownership.md`.

## Script visual state on a fresh spawn

Visual code run from `OnVariablesSynchronized` never runs on a vehicle created with a bare spawn, because that vehicle has not synchronized anything yet. The car shows only what `config.cpp` gives in `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]`, and every script `SetObjectTexture` and `SetObjectMaterial` is missing.

The trap is that the config default often looks like a plausible script result: a near black screen, an unlit indicator, a blank panel. Reading those pixels as the script's output gives a confident wrong answer.

What does synchronize: attaching parts. A debug spawn that attaches battery, spark plug, radiator, four wheels and doors is a large attachment sync and triggers the visual update (measured in game). Seating a player and starting the engine also works, at the cost below.

Keep a control in the same capture. Pick a second selection whose script state is easy to tell from its config default, and read it in the same shot:

- the instrument cluster: config gives the off material, script the on one;
- any indicator light: off in config, on only from script.

A lit control means the script ran, so the subject shows the real result. An unlit control means the script did not run, and the subject tells you nothing. Compare the `emmisive[]` values of the two materials first (vanilla spells the key `emmisive`): 0.3 against 1.1 is clear in daylight, 0.9 against 1.0 is not.

Through the dayz-mcp test bridge (`test-stand-and-mcp.md`), starting the engine needs client ownership of the vehicle, and taking it leaves the free camera unusable until the client restarts. Framing the dashboard and running the engine then exclude each other on one client, so prefer the attachment sync.
