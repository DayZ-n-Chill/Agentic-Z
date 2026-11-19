# Testing vehicles from script

What the engine does when a test seats, drives, unseats or films a vehicle from script instead of through a player's hands, and which actions the server still checks.

The vanilla code is cited from `P:\`. The behaviour around it was measured in game on DayZ 1.29 and 1.30 with `CivilianSedan` and a test helicopter, and is marked as measured where it applies.

## What vanilla checks

| Action | Condition | Source |
|---|---|---|
| `ActionGetOutTransport` | A vehicle command that is not `IsTransitioning`, a crew index of 0 or more, then `CrewCanGetThrough` and `IsAreaAtDoorFreeDiag` for that index. Its target condition is `CCTNone`, so the target plays no part. DayZ 1.29 had no transition check and called `IsAreaAtDoorFree` directly (not on `P:\`). | `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:57`, `:70` to `:79` |
| `ActionSwitchLights` | The player sits at `VEHICLESEAT_DRIVER`, checked on the server. | `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c:34` |
| Door state | A door reads closed at or below phase 0.5 in `TranslateAnimationPhaseToCarDoorState`; the door action moves it with `SetAnimationPhase`. | `P:\scripts\4_world\entities\vehicles\carscript.c:2248` to `:2258`; `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoors.c:91` |
| Sedan driver door | `CrewCanGetThrough` for seat 0 returns `false` while `CivSedanDriverDoors` is closed. | `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:226` to `:234` |
| Debug spawn | `SpawnEntityOnGroundPos` without a player creates a vehicle with `ECE_PLACE_ON_SURFACE`; in a `DEVELOPER` build a `Boat` gets `ECE_KEEPHEIGHT` instead. | `P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:498` to `:502` |
| Spawn flags | The fourth parameter of `CreateObjectEx` is a set of `RF_*` flags, not a heading. | `P:\scripts\3_game\global\game.c:703` |

## A seat on the client is not a seat on the server

A get-in done only on the client gives that client ownership of the vehicle, which is enough to start the engine and drive. It does not seat the player on the server, so an action the server checks still fails: `ActionSwitchLights` tests `CrewMemberIndex(player) == VEHICLESEAT_DRIVER` on the server, and the action kept starting on the client while nothing lit. Seating the player on the server as well made the next identical action work (measured in game).

For an action the server checks, seat the player on both peers, and never read "the action started" as proof; check the effect. Who simulates a vehicle and why a server seat is not ownership is in `network-physics-ownership.md`.

## Getting out after a scripted seat

A scripted get-out fails the same way at every site tested:

- The driver door spawns closed, and `CrewCanGetThrough` needs it open (see the table).
- Opening the door with an action started only on the client does not work. The client half starts, the server half does nothing and the phase stays 0.0. `ActionCloseCarDoors` then fails its condition, which needs a phase above 0.5, and that tells you the door never opened.
- A car stopped against a static object also blocks the door space, so pick sites with at least 150 m clear in the driving direction.

The clean teardown is deleting the vehicle with the player inside, then confirming the player is no longer in a vehicle command. It ejected cleanly every time it was measured. Do not judge a site by whether get-out works.

## Deleting, binding and spawning

- In a live play session, deleting a vehicle the player was seated in on the server, without taking them out first, split client and server: the client draws the player seated, the server has them on foot with no vehicle within 40 m, and the get-out key does nothing because the prompt is client side and the action is checked on the server (measured in game).
- Once a player is bound to a vehicle, a scripted get-in to another vehicle does not seat them. Teleporting the player and `ActionGetOutTransport` do not free them; only deleting the vehicle does. Comparing your vehicle with a vanilla one in the same session therefore needs a relaunch (measured in game).
- The server copy of a car the client owns stayed at its spawn point after the owner drove it 70 to 100 m (measured in game). A server-side search for the car by position must look near the spawn point.
- A spawned vehicle takes the ground's orientation at its point, about 11.6 degrees apart for two points 40 m apart, and the spawn call does not set a heading. When headings must match, choose sites by trial and read the real heading from the vehicle after it settles.
- Where a vehicle stands can stop it moving. The same build drove 91 m at one point and 0.12 m at another 40 m away, at full throttle. Before blaming config, ownership or code, swap sites and repeat in the order A, B, B, A.
- A car parked on a slope rolls again as soon as nothing holds it.

## The camera

A player in a vehicle command (`GetCommand_Vehicle()` not null, `P:\scripts\3_game\human.c:1528`) cannot leave a moving vehicle, so a scene that rolls away traps any camera set up after the get-in. Set a static scripted camera before getting in; it survives the get-in and gives an outside view of the seated player.

A scripted camera can also freeze the client's picture while simulation, sound and input carry on: the player walks, hears footsteps and moves on the server, but the image never changes. Several screenshots in a row come out identical while the player's position moves (measured in game). Releasing the camera did not bring the picture back, and moving the game window from outside did not either; at 150% display scale that left the window oversized and black. Only restarting the client recovered it.

Use a scripted camera only when nothing else will do, and before handing the game back to a person, compare two screenshots taken a moment apart to confirm the picture is live.

## Flying a mod that reads its own inputs

A test cannot fly a vehicle whose mod zeroes the car controller every tick (`SetSteering(0)`) and reads its own `UA` axes, because `UAInput` only reads values and has no setter (`P:\scripts\3_game\inputapi\uainput.c:33`). The route that should work is a diag script on the owner that replaces the `UA` reading before `WriteToMove`; with the Pawn pattern the server reads the axes from the move (`ReadFromMove`), so no sync or RPC is needed. Not yet confirmed in game.
