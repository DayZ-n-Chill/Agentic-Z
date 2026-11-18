# Get-in guards

Which checks stand between a player and the "get in" prompt, in the order the action runs them, and how to find the one that blocks before touching the model.

The general seat and door methods are in `attachments-and-crew.md`; the seat and selection rules behind each guard are in `invariants-get-in-and-seats.md`.

## Find the guard before changing anything

The prompt passes ordered guards inside one function, and knowing the chain does not tell you which guard fires. Name the guard first; the fix then takes minutes.

`ActionGetInTransport.ActionCondition` has one path to `true`: the `return true` inside its `CanReachSeatFromDoors` loop (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:26` to `:69`).

Before it looks at a seat, it rejects when the target is not a `Transport` (`:33`), when `CanGetIn` is false (`:36`), when the player holds a heavy item (`:39`) or when the player is already in a vehicle command (`:42`). Base `Transport.CanGetIn` returns `true` (`P:\scripts\3_game\vehicles\transport.c:672`), so on an unmodified car these four are rarely the cause.

## The five seat guards

They reject in this order:

| Guard | Fails when | Source |
|---|---|---|
| `CrewPositionIndex` | It returns less than 0 for the component under the cursor. The native method maps an action component index to a crew position (`transport.c:179`). On test cars the cause was a View Geometry component not tagged as both its seat selection and `componentNN`, or a selection that is not the seat's `actionSel`. | `actiongetintransport.c:46` |
| `CrewMember` | It returns a player: the seat is taken. | `:50` |
| `CrewCanGetThrough` | The door state or seat fold check says no. Base `Transport.CrewCanGetThrough` returns `false` (`transport.c:724`). | `:54` |
| `IsAreaAtDoorFreeDiag` | The space at the door is blocked. It wraps `IsAreaAtDoorFree`, and a diag menu option can switch it off (`transport.c:909` to `:914`). | `:54` |
| `CanReachSeatFromDoors` | It returns `false` for every selection of the component, called with the player position and a distance of 1.0. | `:57` to `:66` |

`OffroadHatchback` handles only `posIdx` 0 to 3 in its `CrewCanGetThrough` and returns `false` after that (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:225` to `:264`). A vehicle with more than four seats that inherits it must override the method, or seats 4 and up never open. A `true` on `posIdx` 4 or higher proves your override runs.

## Why the last guard fails

`CarScript.CanReachSeatFromDoors` has three silent conditions (`P:\scripts\4_world\entities\vehicles\carscript.c:2177` to `:2199`):

- `GetDoorConditionPointFromSelection` must return a name (`:2179`). Base `CarScript` knows four lower case seats: `seat_driver`, `seat_codriver`, `seat_cargo1` and `seat_cargo2` (`:2141` to `:2160`). `OffroadHatchback` knows six, adding `seatback_driver` and `seatback_codriver` (`offroadhatchback.c:364` to `:379`). Any other seat name returns `""` and the seat can never be boarded, however right the config, bones, proxies and components are. A custom seat set needs an override of this method.
- `MemoryPointExists` must find that point (`carscript.c:2182`), so it has to be in the Memory LOD of the model that ships.
- The distance on the ground plane must be at most `pDistance`, 1.0 m from the action; both heights are set to 0 first (`:2188` to `:2191`). Vanilla puts its condition points about 0.26 m outside the hull at the door: on an MLOD conversion of `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d`, `seat_con_1_1` sits at x=1.1586 against a half width of 0.900 (**model knowledge**; the file on `P:\` is binarized, so only the point names can be read from it). The hatchback serves four seats from two points, `seat_con_1_1` and `seat_con_2_1` (`offroadhatchback.c:364` to `:379`). Two points cannot cover ten seats on a long fuselage.

## Right-hand drive cars

The base seat to door table is left-hand drive. On a right-hand drive car whose memory points are named by physical side, the base `GetDoorConditionPointFromSelection` pairs every seat with the far door: `seat_driver` with `seat_con_1_1`, `seat_codriver` with `seat_con_2_1`, `seat_cargo1` with `seat_con_1_2`, `seat_cargo2` with `seat_con_2_2` (`carscript.c:2141` to `:2160`). The 1.0 m test fails from the right door and no prompt appears, with names, points and components all correct. Measured in game on DayZ 1.29 and 1.30: the right door reports unreachable and the opposite door reports available, the mirror of a healthy car.

Override the method and cross the sides: driver to `seat_con_2_1`, co-driver to `seat_con_1_1`, cargo1 to `seat_con_2_2`, cargo2 to `seat_con_1_2`. Vanilla overrides it the same way for its own layouts (`offroadhatchback.c:364` to `:379`; `P:\scripts\4_world\entities\vehicles\inheritedcars\van_01.c:269` to `:287`).

Also cross `GetSeatAnimationType` for the rear seats (the vanilla shape is at `offroadhatchback.c:121` to `:137`). The driver keeps `VEHICLESEAT_DRIVER`, whose get-in animation still looks left-hand drive. That is an engine limit, not a mod bug.

## Asking the game which guard blocks

dayz-mcp, a third-party bridge into a running game that this repo does not ship, has `query_get_in_condition`. Given a `component` index it returns `first_block` as one of `componentNN`, `occupied`, `crew_can_get_through`, `area_blocked`, `unreachable`, `item_heavy`, `already_in_vehicle`, `no_component` or `""`, plus `crew_can_get_through`, `area_free`, `occupied` and `reachable` per seat. Its `reachable` loop runs the same `GetActionComponentNameList` and `CanReachSeatFromDoors` loop as the action. `FIRST_BLOCK_FIX` in `skills/dayz-launch-test/scripts/run_vehicle_checks.py` lists the fix for each value.

Pass a real component index. With `component=-1` it reports the whole crew, but `reachable` is then always false and `first_block` is `no_component` with `partial=1`, so that result is never a pass.

Read `first_block` per seat before editing the model, config or script. On a ten seat test helicopter every seat returned `unreachable` with the first four guards passing, which pointed at the last guard alone and ruled out seat name case and reach radius at once.
