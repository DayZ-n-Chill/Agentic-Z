# Cookbook: the get-in prompt does not appear

For a family B car whose "get in" prompt never shows: the ordered guards of the action, how to name the guard that blocks before touching the model, and the right-hand-drive seat table.

Vanilla facts cite the file on `P:\`. The measured cases (LFQuad, MercedesAMGLF, LFHeli OH-1 R3, LFHeli HH-60G, WRX STI) and the DayZ-MCP instrument are not vanilla and are not yet checked on `P:\`. Added 2026-07-29. The general seat and door methods are also in the vehicles pack (`skills/_shared/vehicles/attachments-and-crew.md`).

## Name the guard before touching the model

Four vehicles burned iterations on "the get-in prompt does not appear" (LFQuad, MercedesAMGLF, LFHeli OH-1 R3, LFHeli HH-60G). The prompt is gated by ordered guards inside one function, and a chain that is necessary is not a cause that was measured: knowing the prompt has to pass through `CanReachSeatFromDoors` says nothing about which guard fires. Name the guard first; the fix follows in minutes.

`ActionGetInTransport.ActionCondition` has exactly one path to `true`, the `return true` inside the `CanReachSeatFromDoors` loop (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:26-69`).

Before it looks at a seat it rejects when the target is not a `Transport` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:33`), when `CanGetIn` is false (`:36`), when the player holds a heavy item (`:39`) or when the player is already in a vehicle command (`:42`). Base `Transport.CanGetIn` returns `true` (`P:\scripts\3_game\vehicles\transport.c:672`), so on an unmodified car these four are rarely the cause.

Then five seat guards reject in this order:

1. `CrewPositionIndex` returns less than 0 for the component under the cursor (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:46`). The engine function maps an action component index to a crew position (`CrewPositionIndex`, `P:\scripts\3_game\vehicles\transport.c:179`). On the measured cars the cause was one of two: the ViewGeometry component under the cursor is not dual-tagged `componentNN`, or its selection is not the seat's `actionSel`.
2. `CrewMember` returns a player: the seat is occupied (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:50`).
3. `CrewCanGetThrough` returns `false`: the door state or seat fold gate (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:54`). Base `Transport.CrewCanGetThrough` returns `false` (`P:\scripts\3_game\vehicles\transport.c:724`). `OffroadHatchback` covers only `posIdx` 0 to 3 in its `CrewCanGetThrough` and then returns `false` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:225-264`), so a vehicle with more than four seats that inherits it must override the method or seats 4 and up are dead. A `true` on `posIdx` 4 or higher is proof your override is running.
4. `IsAreaAtDoorFreeDiag` returns `false`: the engine-side check of the area at the door (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:54`). It is a wrapper around `IsAreaAtDoorFree` that a diag menu option can switch off (`IsAreaAtDoorFreeDiag`, `P:\scripts\3_game\vehicles\transport.c:909-914`).
5. `CanReachSeatFromDoors` returns `false` for every selection of the component, called with the player position and a distance of 1.0 (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:57-66`).

Guard 5 has three sub-conditions in `CarScript`, all silent (`CanReachSeatFromDoors`, `P:\scripts\4_world\entities\vehicles\carscript.c:2177-2199`):

- `GetDoorConditionPointFromSelection` must return a name that is not empty (`P:\scripts\4_world\entities\vehicles\carscript.c:2179`). This is the trap. Base `CarScript` knows only four cases, all lower case: `seat_driver`, `seat_codriver`, `seat_cargo1` and `seat_cargo2` (`P:\scripts\4_world\entities\vehicles\carscript.c:2141-2160`). `OffroadHatchback` knows six, also lower case, adding `seatback_driver` and `seatback_codriver` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:364-379`). Any other seat selection name returns `""` and the seat can never be boarded, with config, bones, proxies and componentNN all correct. A custom seat set requires an override of this method.
- `MemoryPointExists` must find that point (`P:\scripts\4_world\entities\vehicles\carscript.c:2182`): it has to be in the Memory LOD of the shipped model.
- The distance in plan must be at most `pDistance`; the height of both points is set to 0 first (`conPointWS`, `P:\scripts\4_world\entities\vehicles\carscript.c:2188-2191`), and the action passes 1.0 m. Vanilla places its condition points about 0.26 m outside the hull at the door station (measured on an MLOD conversion of the ODOL model `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d`: `seat_con_1_1` at x=1.1586 against a half width of 0.900; the file on `P:\` is binarized, so these two figures are not checkable from it, though both point names are in it) and reuses two points, `seat_con_1_1` and `seat_con_2_1`, for four seats (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:364-379`). On a long fuselage two points cannot cover ten seats.

## The instrument

DayZ-MCP (an in-game bridge, not part of the vanilla game): `query_get_in_condition` with a `component` index returns `first_block` as one of `componentNN`, `occupied`, `crew_can_get_through`, `area_blocked`, `unreachable`, `item_heavy`, `already_in_vehicle`, `no_component` or `""`, plus `crew_can_get_through`, `area_free`, `occupied` and `reachable` per seat (the full list with the fix for each is `FIRST_BLOCK_FIX` in `skills/dayz-mcp-verify/references/drive_ladder.py`). The `reachable` loop is the same `GetActionComponentNameList` to `CanReachSeatFromDoors` loop the action runs. That names the guard in one call, without the user's eye. Pass `component=-1` for the whole crew bank; in that mode `reachable` is hardcoded false and `first_block` is `no_component` with `partial=1`, so the result is partial and never a pass, and only the call per component measures reachability.

Measured case, HH-60G on 2026-07-29: all ten seats returned `first_block="unreachable"` with guards 1 to 4 green on all ten, so the block was guard 5 alone. That killed two plausible sub-causes at once, because neither camelCase names nor the radius can explain a lower case seat whose point was 1 mm from the player.

The discipline this cost: a plan that declared a "measured mechanism" because the chain was necessary was rejected in review for exactly that. Measure `first_block` per seat before editing the model, the config or the script.

## Fourth sub-cause of guard 5: the base seat to door table is left-hand drive

Measured on the WRX STI, in game on DayZ 1.30.164014 Experimental; first measured on 1.29 Diag on 2026-09-04.

On a right-hand-drive car whose memory points are named by physical side, the base `GetDoorConditionPointFromSelection` pairs every seat with the far door: `seat_driver` with `seat_con_1_1`, `seat_codriver` with `seat_con_2_1`, `seat_cargo1` with `seat_con_1_2` and `seat_cargo2` with `seat_con_2_2` (`P:\scripts\4_world\entities\vehicles\carscript.c:2141-2160`). `CanReachSeatFromDoors` fails the 1.0 m plan test from the correct door and no get-in appears, with names, points and `componentNN` all correct.

The signature in `query_get_in_condition` is `unreachable` from the correct door and `available` from the opposite one, the exact mirror of a healthy sweep.

The fix is an override that crosses the sides (driver to `seat_con_2_1`, co-driver to `seat_con_1_1`, cargo1 to `seat_con_2_2`, cargo2 to `seat_con_1_2`), as vanilla overrides `GetDoorConditionPointFromSelection` for its own layouts (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:364-379`; `P:\scripts\4_world\entities\vehicles\inheritedcars\van_01.c:269-287`).

On a right-hand-drive car also cross `GetSeatAnimationType` for the rear seats (the vanilla shape is at `P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:121-137`). The driver keeps `VEHICLESEAT_DRIVER`, whose get-in animation will look left-hand-drive sided. That is an engine limit, not a mod bug.
