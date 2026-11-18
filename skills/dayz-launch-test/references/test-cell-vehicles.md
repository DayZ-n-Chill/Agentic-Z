# Vehicles in scripted test cells

How a scripted test seats a player in a vehicle without a person at the keyboard, how to tell why a test vehicle will not drive, and how to probe both peers when getting out goes wrong. Setting up the cell itself is in `automated-cells.md`.

Vanilla script facts cite the file on `P:\`. The rest was measured in game on test vehicles (a quad bike and a helicopter mod) and is not checked on `P:\`.

## Seating a player by script

Calling `StartCommand_Vehicle` directly on the client seats a local ghost: the client sees itself seated with the HUD active, but the server never registers the crew. Inject the real action instead:

```c
// client side, test build only
ActionManagerClient mgr = ActionManagerClient.Cast(player.GetActionManager());
mgr.PerformActionStart(ActionManagerBase.GetAction(ActionGetInTransport), target, null);
```

`PerformActionStart` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804`; the static `GetAction(typename)` is at `actionmanagerbase.c:214`) goes through `ActionStart` in multiplayer, a synchronized flow the server mirrors. Find the target's component index by walking components until `CrewPositionIndex(c)` returns the seat you want (`P:\scripts\3_game\vehicles\transport.c:182`). Confirm success with `GetCommand_Vehicle()` on the next tick, with a retry; do not mark the step done when the action is sent. `ActionCondition` is protected, so it cannot be checked from outside; the action manager validates it on both sides.

### Crew and the vehicle command are two things

Only the real action gives both:

- Crew is native engine state, not a script sync variable. `Transport` registers a single sync variable, `m_EngineZoneReceivedHit` (`transport.c:110`), and `CrewMember` and `CrewDriver` are `proto native` (`transport.c:190` and `:194`), readable on any client. That is how the get-in action refuses a seat that is already taken (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:50` to `:52`).
- `HumanCommandVehicle` is created by `StartCommand_Vehicle` on the machine that calls it. Across the 3,058 `.c` files under `P:\scripts` there are three call sites of the `proto native` method (`P:\scripts\3_game\human.c:1526`): the get-in action (`actiongetintransport.c:104`), the return from unconsciousness through `m_TransportCache` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2395`), and a debug path under `#ifdef DEVELOPER` (`SetGetInVehicleDebug`, `P:\scripts\4_world\entities\manbase\playerbase.c:3531` to `:3541`). None starts the command on learning over the network that the player is already seated.

So the client calling `StartCommand_Vehicle` gets the command without server crew, and the server seating someone by script gets crew without the client's command. In the second case every action that needs a seated player stays unavailable, because those conditions read `GetCommand_Vehicle()`, not `CrewMember`: getting out (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:70` to `:76`) and starting the engine (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:26` to `:37`) both do. `IsInVehicle()` accepts either route, the command or a `Transport` parent (`dayzplayerimplement.c:468` to `:471`), so it cannot tell them apart.

### A parked vehicle rejects the get-in

If the mod puts a vehicle to sleep at rest, the injected get-in is refused. Start the engine on the server from the test mission (`EngineStart`, `P:\scripts\3_game\vehicles\car.c:233`) as soon as the vehicle spawns, not when crew appears. Without the engine or simulation running, the owner state channel stays silent even with the player seated.

## Before injecting an action

- Teleport with the X and Z of the probed point and `Y = GetGame().SurfaceY(x, z)` (`P:\scripts\3_game\global\game.c:1176`). The Y of a memory point can leave the player falling (`ACID_Human_Fall`), and an action injected during the fall can abort with no error while the server has already reserved the seat.
- Require an accepted command id, no action in progress, `CanStoreInputUserData()` and `ActionBase.Can(...)` before you spend an attempt. Then watch for the real transition. A mismatch of server `Move` and client `Fall` points at placement first.

## A test vehicle that will not drive

When a modded `CarScript` spawns but its wheels mount without spinning, the chassis bounces or sinks, or the engine revs with no speed, the cause is almost always one of two measurable things, not mass or inertia. Log both beside a vehicle known to drive (the vanilla sedan, or a mod car that works) in the same run before touching geometry.

### Is each wheel seated and touching the ground

| Read | Meaning | Source |
|---|---|---|
| `WheelCountPresent()` | Wheels the simulation seated. `0` while `WheelCount()` returns N means the slot wiring to the Fire Geometry is wrong. | `P:\scripts\3_game\vehicles\car.c:348` |
| `WheelCount()` | Wheels the vehicle declares. | `car.c:345` |
| `WheelHasContact(i)` | `1` on the ground, `0` in the air. Print the four as a string: `wc=1111` is good, `wc=0000` means the whole vehicle hangs above the ground. | `car.c:286` |

`WheelCountPresent()` at 0 is the silent wheel binding fault (`error-catalog.md`, E20; mechanism in `_shared/enscript/depth/vehicle-scripting.md`). Four present wheels with `wc=0000` is a hull sitting too high or buried, which the next check isolates.

### Did placement bury or launch it

Spawn at an explicit height instead of letting the Central Economy drop it:

- `ECE_KEEPHEIGHT` (`524288`) places at the exact Y you pass with no surface trace (`P:\scripts\3_game\ce\centraleconomy.c:28`). Spawn at a known clear height and watch it settle.
- `ECE_PLACE_ON_SURFACE` (`1060`) is the normal surface placement (`centraleconomy.c:38`).

Stable with `ECE_KEEPHEIGHT` but bouncing or sinking with `ECE_PLACE_ON_SURFACE` means placement buries the hull (wheel well clearance against tyre radius), not a model fault.

Before you call the test failed on "no data", check that the parser still matches the current log line format. A renamed tag or reordered fields reads as a failure when the test ran fine; try the regex on a raw line first.

## Probing both peers

For a failure on getting out or a desync, log the callback that matches `OnDriverExit` on both peers, and print `playerPos`, `vehiclePos`, `crewEntryWS` and their distances in one window. Align the two clocks with pairs of the same event; never compare raw timestamps across peers.

- In an owner series with rewind and replay, several samples can share one `t`. Keep the first sample per tick, or merge a stated interval under 20 ms, before reading edges.
- Convert server events to the owner's clock. Trust the server's series first and the owner's second, and re-run the whole history after you change the parser.
- Nothing outside the game injects arbitrary values into `UAInput`. If the mod disables `CarController` and reads its own axes, the cell needs a DIAG script on the owner before `WriteToMove`, adopted only after a run in game shows it steers.

Log the symptom callback on both peers with a gated probe and a stack trace. On the client, print the stack one line at a time so it is not cut, and never call server only APIs there.

## Keeping a vehicle cell repeatable

- Spawn the fixture at a fixed place and the player at a fixed offset on `SurfaceY`; a random spawn turns obstacles and doors into noise. A default spawn also draws a random character class, so pin it (`vehicle-first-person-eye.md`, "Log the eye in every run").
- After getting out, rearm the placement on the server after a cooldown with the player on foot. Getting back in is part of the test: a ghost pose on the client spoils reach and `Can()`.
- While the scripted pilot runs, a DIAG guard in `ActionCondition` refuses human actions that would break the cell, and keeps a separate route for the script.
- Decide that the vehicle has settled from the server's mirrored state (the mod's ground or parked state), with height above ground only as a backup, never from one owner velocity sample. The owner can keep bouncing after the server has settled.
- `forces-off`, `clamp-abort`, `no-probes`, `no-pilot` and `not-owner` are `INCONCLUSIVE` and allow a bounded retry. A timeout after the preconditions were met is `FAIL`. The script runs the cell; the gates written before the run judge it.
