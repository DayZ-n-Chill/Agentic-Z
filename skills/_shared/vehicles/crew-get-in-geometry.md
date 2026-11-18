# Crew and get-in geometry

What a car's model and script must provide for the get-in action to appear on every seat and for the seated player to sit right: seat components, the crew proxy triangle, the script class, and how to probe seats without aiming by hand.

The guards the action runs, in order, are in `get-in-guards.md`; the seat and door rules are in `invariants-get-in-and-seats.md`. Measurements here were taken in game and with a headless probe on test cars and a test quad.

## The seat comes from the component under the cursor

`Transport.CrewPositionIndex(componentIdx)` (`P:\scripts\3_game\vehicles\transport.c:182`) picks the seat from the collision component the cursor ray hits in View Geometry; the default intersection type is `ObjIntersectView` (`P:\scripts\3_game\global\dayzphysics.c:88`), and the get-in condition reads the result (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:45` and `:46`). Memory point distance and `GetCrewIndex` play no part, and neither does the door system: the driver prompt worked on two test vehicles without either.

So each seat needs its own clean, closed convex component:

- `seat_driver` is one dedicated `ComponentNN` cube and `seat_codriver` another, each seat selection sharing all its faces with its component (`vehicle-proxies.md`). The sedan uses `component31` and `component32`, one each.
- Seats painted across a grid of components leave the ray never landing cleanly on the second seat, so every hit reads as the driver. On a test quad the seats spread over 88 and 112 points across about 23 components, and the co-driver prompt never showed.
- A solid box in View Geometry, such as a central spine, is hit before the seat cube and blocks get-in. Remove it.

## Seat cubes must be inward wound with point flags 63

Clean outward cubes are not enough. A seat cube with outward winding and point flags 0, as py3d writes by default, is invisible to `DayZPhysics.RaycastRV(..., ObjIntersectView)`: the ray never resolves it, `CrewPositionIndex` falls back to component 0, and only the driver seems to work. Rebuilt with inward winding and the point flags `0x0000003F`, the same cube returned `hit=1 comp=1 crewIdx=1` and the co-driver prompt worked in game; a second test car confirmed it.

The value comes from the vanilla sedan: on a converted copy all 478 View Geometry points carry `0x0000003F`, and the reference quad carries it on all 482 (**model knowledge**). The `0x02000000` recorded elsewhere is what a py3d exporter writes, measured on a product, not on vanilla. Winding and flags were changed together, so the flag was never isolated as the cause; copy both.

When the seat components already map to the right crew positions, change only them: flip the seat faces in place to inward winding, recompute each face normal, and set their point flags to `0x0000003F`. Leave other View Geometry components outward with flags 0, which keeps them out of the cursor ray.

A closed car needs no body shell in View Geometry, only the two seat cubes; open vehicles keep a shell because they have window openings. Giving a closed car's View Geometry a body, or moving seats to high component indices, did not fix the co-driver; winding and flags did.

When an open vehicle does need a shell occluder, small components alone do not prove the seats are reachable: detachable doors or interior pieces left in the shell still block every ray. Build the occluder from surfaces the shell owns, and check two things against a working vehicle and broken test models: the ratio of the largest component's box volume to the shell's (a single body envelope fails it), and rays cast from both door sides toward each seat, whose first hit must be that seat's own `componentNN` (models with door or interior surfaces left in the shell must fail). The ray fan treats triangles as two sided and cannot predict the game's culling, so the get-in test in game still decides.

## The crew proxy triangle sets the seated pose

The seated player's position and facing come from the crew proxy triangle (`crewdriver`, `crewcodriver`, in View Geometry and Fire Geometry), not from `pos_driver` or `pos_codriver`. `class Crew` names those proxies through `proxyPos` (vanilla `proxyPos="crewDriver"` and `proxyPos="crewCoDriver"`, `P:\DZ\vehicles\wheeled\config.cpp:270` and `:278`); memory points of the same name are not enough.

- Make the triangle's shape unambiguous: `origin + e1 + e2` with edges of about 1.0 and 2.0, angles 90, 63.4 and 26.6 degrees. A 90, 45, 45 triangle ties in the engine's angle sort and turns each seat differently. A tiny triangle (py3d `add_proxy(scale=0.1)`, edges about 0.05) falls below the engine's threshold: the player is misplaced and moving the proxy has little visible effect.
- The facing depends on `e1`, `e2` and the model's own orientation. A car facing -z, like vanilla, uses `e1=(0,0,1)`, `e2=(0,2,0)`, which gives `R=((-1,0,0),(0,0,1),(0,1,0))`. A model turned 180 degrees needs `e1=(0,0,-1)`, giving `R=((1,0,0),(0,0,-1),(0,1,0))`. Copy a known good car with the same orientation and confirm the sign of one move in game.
- The triangle's origin sets the seated height and fore and aft position. Move all three points together in steps of about 15 cm; smaller steps read as no change. A low roof may clip the standing pose whatever you do.

Builders that create crew proxies with `add_proxy(..., scale=0.1)` and paint seats over the collision grid hit both faults. Emit the canonical triangle with the right frame in both LODs and build the seats as two dedicated cubes from the start.

## A script class, not bare `CarScript`

A car declared `class MyMod_Car: CarScript` with no script class runs as bare `CarScript`, and get-in never appears however perfect the model. `CarScript` and `Car` do not override `CrewCanGetThrough`; only concrete vanilla cars do. The base `Transport.CrewCanGetThrough` returns `false` in a normal build (`#ifndef CFGMODS_DEFINE_TEST`, `transport.c:727` to `:734`). The base `GetAnimInstance` and `GetSeatAnimationType` raise "not implemented" errors (`:665` to `:673`, `:685` to `:690`). Telemetry shows the class name as `CarScript` instead of yours.

A thin base class fixes it, with signatures as on the sedan (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:109` and `:119`):

```c
// scripts/4_World/MyMod/Vehicles/MyMod_Car_Base.c
class MyMod_Car_Base extends CarScript
{
    override int GetAnimInstance() { return VehicleAnimInstances.SEDAN; }
    override int GetSeatAnimationType(int posIdx)
    {
        switch (posIdx)
        {
            case 0: return DayZPlayerConstants.VEHICLESEAT_DRIVER;
            case 1: return DayZPlayerConstants.VEHICLESEAT_CODRIVER;
        }
        return 0;
    }
    override bool CrewCanGetThrough(int posIdx) { return posIdx == 0 || posIdx == 1; }
}
class MyMod_Car extends MyMod_Car_Base {}
```

These three methods are enough to get in and drive. Opening doors and switching seats also need `GetCarDoorsState`, the door slot mappers, the `CanReach` methods, `GetSeatIndexFromDoor` and `GetAnimSourceFromSelection`. A shipped third-party car mod uses the same pattern: its base class extends `CarScript` directly and overrides these methods itself. The leaf class lets telemetry read the exact config class name.

The model must carry the memory points `seat_con_1_1` and `seat_con_2_1` within 1.0 m of a player at the door, and the crew config must use `seat_driver` and `seat_codriver`; the base `GetDoorConditionPointFromSelection` maps them (`P:\scripts\4_world\entities\vehicles\carscript.c:2141`). That mapping is left-hand drive; right-hand drive cars need the override in `get-in-guards.md`.

Doors are not needed. `GetCarDoorsState` returns `DOORS_MISSING` when no `CarDoor` is attached (`civiliansedan.c:185` to `:193`), which is not `DOORS_CLOSED`, so `CrewCanGetThrough` passes. A car with doors baked into the body gets in fine; opening doors is a separate feature (`CarDoor` classes, door proxies and models, the `AnimationSources` door classes such as `DoorsDriver`, and door bones in `model.cfg`; `vehicle-door-mechanisms.md`).

## The script module must load

If `CfgMods` `worldScriptModule` does not load the script path, the class never binds and every override is dead without an error; an empty `script.log` looks clean and telemetry shows `CarScript`. On DayZ 1.29 `dir = "MyMod";` with a backslash path worked. On DayZ 1.30 a backslash path loaded nothing on the server and the same path with forward slashes loaded (measured in game; `dayz-1-30-vehicles.md`). Write forward slashes, then compare the script log's `Module: World; loaded Nx files` line with a run without the mod.

## Probing the seats

A headless mission probe finds whether the mapping, the ray or the collision is at fault in one run: spawn the car and a working car near the player, dump `CrewPositionIndex` for components 0 to 79, and cast `DayZPhysics.RaycastRV` (view and fire) at each seat from both sides and both ends. Parse the raw `hit=N comp=N crewIdx=N` integers; a regex for `1` also matches `-1`.

Aim at `pos_driver` and `pos_codriver` with `GetMemoryPointPos`, which returns engine-space coordinates, but only when those points sit inside the seat cubes. On a vanilla car they are the entry point at the sill (the sedan's sit near y 0.07, x ±1.4), so a ray aimed there hits the body; aim at the seat component's centroid on vanilla.

Inject the probe into the mod's own test mission `init.c`, not a shared one, poll `script.log` for the probe lines, and restore the original file afterwards. To build the probe PBO without launching, call AddonBuilder directly (`<src> <target> -prefix=<Mod> -temp=<fresh folder> -packonly`); a fresh temp folder gives a clean sync.

A forced seat entry proves nothing about get-in: `vehicle_enter` through the test bridge seats the player without running `ActionCondition` (`test-stand-and-mcp.md`). Watch for the prompt itself.
