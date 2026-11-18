# DayZ 1.30 get-in, boats and smaller changes

What the 1.30 get-in condition checks and which side a rider can board from, what boats gained, how `speedGeoms` hides parts at speed, which wrecks became wells, and where the motorbike camera lives.

Every line cites the 1.30 scripts on `P:\` unless it is marked 1.29. In-game results were measured on a quad mod and are mod behaviour. The rest of the 1.30 changes are indexed in `dayz-1-30-vehicles.md`.

## The get-in condition

On 1.29 the condition checked `CrewCanGetThrough`, then `IsAreaAtDoorFree`, then the `CanReachSeatFromDoors` loop. On 1.30, `ActionGetInTransport.ActionCondition` also needs `transport.CanGetIn()` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:36`; default `true`, `P:\scripts\3_game\vehicles\transport.c:675` to `:678`) and uses `IsAreaAtDoorFreeDiag(crewIndex)` (`actiongetintransport.c:54`). The reach check runs in script. From `actiongetintransport.c:54` to `:66`:

```c
		if (!transport.CrewCanGetThrough(crewIndex) || !transport.IsAreaAtDoorFreeDiag(crewIndex))
			return false;

		array<string> selections = new array<string>();
		transport.GetActionComponentNameList(componentIndex, selections);
		int selectionCount = selections.Count();
		vector playerPosition = player.GetPosition();

		for (int i = 0; i < selectionCount; ++i)
		{
			if (transport.CanReachSeatFromDoors(selections[i], playerPosition, 1.0))
				return true;
		}
```

The third argument, 1 m, is therefore visible to script (`actiongetintransport.c:64`). Treating the reach check as engine only is wrong on both builds.

1.29 already ended with the same `CanReachSeatFromDoors(selections[i], player.GetPosition(), 1.0)` loop (1.29 `ActionGetInTransport.c`, line 73), and `CarScript.CanReachSeatFromDoors` reads the same on both builds. The condition gained only two things in 1.30:

- `CanGetIn()`, default `true`. `Motorbike_01` overrides it to refuse while its `SeatDriver` animation phase is not 0 (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:89` to `:95`); it is the hook for any state that should block every seat at once.
- The `IsAreaAtDoorFreeDiag` wrapper, which returns `IsAreaAtDoorFree` unless the DiagMenu toggle `TRANSPORT_FREESPACE_DISABLED` is on (`transport.c:910` to `:924`).

`Start` keeps its order: it runs `super.Start`, where `OnStartServer` and `OnStartClient` fire, before `StartCommand_Vehicle` (1.29 `ActionGetInTransport.c`, lines 82 to 91; `actiongetintransport.c:71` to `:104`). A mod that adjusts the player in those two hooks, such as boarding from both sides, sees the same order on both builds. New in 1.30, `Start` asks `HasDirectionalInOutAction()` and, when it is true, picks the seat animation with `GetSeatAnimationTypeDirectional(crewIndex, direction)` from the side the player stands on (`:81` to `:102`); `class-hierarchy.md` has the override pair.

## Which side a rider can board from

The door condition point decides it. `CarScript.CanReachSeatFromDoors` measures the player's distance on the ground plane to the memory point that `GetDoorConditionPointFromSelection(selection)` names (`P:\scripts\4_world\entities\vehicles\carscript.c:2177` to `:2199`), and the action passes 1.0 m. It tests horizontal distance only, not which side the player stands on.

A quad mod with no `seat_con_*` points returns its approach points `pos_driver` and `pos_codriver` instead, both at model X -0.82, on the left of its shared seat. On a 1.30 diag build, next to the left point both seats passed every get-in guard (`get-in-guards.md`), the cursor showed `ActionGetInTransport`, and the action seated the player; at the same point mirrored to the right, both seats failed `CanReachSeatFromDoors` and the cursor showed nothing. That holds for that quad at the tested positions, not for every vehicle. A get-in check from one side says nothing about the other: test both sides for each seat in game.

## Boats

`BoatFluid` is now the shared enum under another name. From `P:\scripts\3_game\vehicles\boat.c:12` and `:13`:

```c
//!	Type of vehicle's fluid. (native, do not change or extend)
enum BoatFluid : ETransportFluid {}
```

Boats have a speedometer (`boat.c:42` to `:56`):

```c
	//!	Returns the current speed of the vehicle in km/h.
	float GetSpeedometer()
	{
		vector transform[4];
		GetTransform(transform);
		float velocity = GetVelocity(this).InvMultiply3(transform)[2];
		return velocity * 3.6;
	}

	//! Returns the current speed of the vehicle in km/h. Value is absolute
	float GetSpeedometerAbsolute()
	{
		return Math.AbsFloat(GetSpeedometer());
	}
```

- `BoatScript.GetHeatComfortOverride()` is at `P:\scripts\4_world\entities\vehicles\boatscript.c:256` to `:259`.
- The AI noise class `NoiseBoatEngine` has `strength=30` (`P:\DZ\vehicles\water\config.cpp:41` to `:45`).
- `ActionFillFuel` works through `ETransportFluid.FUEL` on `Transport` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionfillfuel.c:50`).

## speedGeoms: hiding parts at speed

The 1.30 change notes, in their modding section, describe the pair: named components are hidden at speed so they do not snag on the ground. The first vanilla motorbike (`P:\DZ\vehicles\singletrack\config.cpp:262` to `:266`):

```cpp
		speedGeomActivation=0.28999999;
		speedGeoms[]=
		{
			"geotohide"
		};
```

`Motorbike_02` uses `0.27` (`:1455`). The filter itself is engine code, not Enforce, so how it works is unverified. No car, truck or boat declares the pair: neither `P:\DZ\vehicles\wheeled\config.cpp` nor `P:\DZ\vehicles\water\config.cpp` contains `speedGeom`. Copy the motorbike pattern only when a high speed snag is measured.

## Wreck cisterns are wells

From `P:\scripts\4_world\entities\building\wrecks\wreck_truck01_aban1_cistern.c:1` and `:2`:

```c
class Land_Wreck_Truck01_Aban1_Cistern : Well {}
class Land_Wreck_Truck01_Aban1_Cistern_DE : Land_Wreck_Truck01_Aban1_Cistern {}
```

`Land_Wreck_Truck01_Aban2_Cistern` is the same (`wreck_truck01_aban2_cistern.c:1`). Players drink from them as wells; they are not vehicle wrecks. The Chinook and Mi24 wrecks are in `aviation-dayz-1-30.md`.

## Motorbike camera

`DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32`, registered with its creator (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20` and `:63`). The class `DayZPlayerCamera3rdPersonVehicleMotorbike` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:239`) sets `CONST_SPRING_SMOOTHTIME_YAW = 0.5`, `CONST_YAW_LAG_REVERSE = 0.3` and `UP_ANGLE_CAP = 10` (`:243` to `:258`). The rest is in `motorbike-rider-animation.md`.
