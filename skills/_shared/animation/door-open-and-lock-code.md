# Door open and lock code in 1.30

How vanilla 1.30 script decides whether a building door may open, how the one sided door check works, and why combination and code locks are not `EBuildingLockType` values. The config keys these rules read are in `door-config-and-locks.md`; the lock slots on a mod building are in `building-door-locks.md`.

## The open check takes a parameter object

1.30 has two `CanDoorBeOpened` signatures on `Building`. The vanilla open action uses the one that takes a `DoorManipulationParams`:

```c
// P:\scripts\3_game\entities\building.c:5
class DoorManipulationParams
{
	int m_DoorIndex;
	bool m_CheckIfLocked;
	Object m_Caller;
}
```

`CanDoorBeOpened(notnull DoorManipulationParams params)` (`P:\scripts\3_game\entities\building.c:141`) returns false when the door is already open. With `m_CheckIfLocked` set it returns false for a locked door; without it, false for a door that is not locked. The older `CanDoorBeOpened(int doorIndex, bool checkIfLocked = false)` (`building.c:160`) only builds a params object without `m_Caller` and calls the first one.

Before 1.30 the `int` form was the only one, `ActionOpenDoors` called it directly, and `GetLockCompatibilityType` always returned `1 << EBuildingLockType.LOCKPICK`. That build is not on `P:\`, so this is not checked there.

So a mod that changes when a door may open overrides the params form and calls `super`. An override of the `int` form alone is never reached by the vanilla action.

## What the open action checks

`ActionOpenDoors` finds the door index from the aimed component, checks reach, runs the one sided check, then fills the params and asks the building:

```c
// P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:36
		BuildingBase building;
		if (Class.CastTo(building, target.GetObject()))
		{
			DoorManipulationParams doorParams = new DoorManipulationParams();
			doorParams.m_DoorIndex = building.GetDoorIndex(target.GetComponentIndex());
			if (doorParams.m_DoorIndex != -1)
			{
				if (!IsInReach(player, target, UAMaxDistances.DEFAULT)) 
					return false;
				
				if (!building.DoorsDirectionalCheck(player,target.GetComponentIndex()))
					return false;
				
				doorParams.m_CheckIfLocked = CheckIfDoorIsLocked();
				doorParams.m_Caller = player;

				return building.CanDoorBeOpened(doorParams);
			}
		}
```

`BuildingBase` then refuses the open while any slot in the door's `m_RelatedInventorySlotNames` holds a locked `DigitalCodeLock` or `CombinationLock` (`P:\scripts\4_world\entities\game\super\building.c:412` to `:438`). Its `IsLocked(int doorIndex)` (`:388` to `:410`) returns false on every path, a locked lock included, so test the lock items yourself as `CanDoorBeOpened` does; never rely on `IsLocked(int)`.

The action casts its target to `BuildingBase` (`actionopendoors.c:36` to `:37`), so a door on a class that is only a `Building` gets no Open. On the server `OnStartServer` asks `CanDoorBeOpened` again with the same params before it calls `OpenDoor` (`:59` to `:76`). `ActionLockedDoors` is the same action with `CheckIfDoorIsLocked()` returning false (`:101` to `:112`): it is offered only on a locked door, and the base check then lets it through.

## Doors that open from one side

`DoorsDirectionalCheck` (`P:\scripts\4_world\entities\game\super\building.c:441`) reads the door's `m_InteractLimitingPositionPoint` and `m_InteractLimitingDirPoint` and passes them to `MiscGameplayFunctions.MemPointDirectionalCheck` (`P:\scripts\4_world\static\miscgameplayfunctions.c:942`). The vanilla comment says: "some doors can only be operated from one side".

The helper compares the direction from the player's head to the start point with the direction from the start point to the end point, within a default tolerance of `Math.PI_HALF`. It only runs that test when both names are set and both points exist in the model; otherwise it returns true (`:944` to `:970`). The vanilla comment above it says so: "Intentionally returns true (no restriction) when the check cannot be performed" (`:942`). So a door with no points opens from both sides, and a typo in a point name silently does the same.

## Lock types are not the lock items

`EBuildingLockType` lists only engine lock keys (`P:\scripts\3_game\enums\ebuildinglocktypes.c:7`): `NONE` (the vanilla comment says "unlockable only via script"), `LOCKPICK`, and `SHIP_CONTAINER_0` to `SHIP_CONTAINER_4`. There is no combination lock or code lock value.

Combination locks and code locks are inventory items whose `IsExternalLockType()` returns true (`P:\scripts\4_world\entities\itembase\codelock.c:563`; `P:\scripts\4_world\entities\itembase\combinationlock.c:779`; the base method at `P:\scripts\4_world\entities\itembase.c:4852`).

`GetLockCompatibilityType` returns the door's `m_LockCompatibilityBitMask` (`P:\scripts\3_game\entities\building.c:193` to `:196`). `ActionLockDoors` still tests that mask against the tool's `GetKeyCompatibilityType()`, but first returns false when any related slot already holds an external lock item (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionlockdoors.c:40` to `:57`).

The native engine lock calls are unchanged: `IsDoorLocked`, `LockDoor` and `UnlockDoor` (`P:\scripts\3_game\entities\building.c:55` to `:70`).

## Door state queries and events

The state queries read the wanted phase or the current phase against three targets: closed 0.0, ajar 0.2 and open 1.0 (`P:\scripts\3_game\entities\building.c:33` to `:52`). `IsDoorOpen` is true once the door is asked to open (wanted phase above 0.5), before it has moved; use `IsDoorOpened` or `IsDoorClosed` when the door must have arrived. `UnlockDoor(index, animate = true)` swings the door ajar (`:69` to `:70`), and `LockDoor` with `force = true` closes an open door first (`:66` to `:67`).

Override these on a `BuildingBase` child and call `super`; all are empty on `Building` (`:101` to `:139`):

| Event | Params |
|---|---|
| `OnDoorOpenStart`, `OnDoorOpenAjarStart`, `OnDoorCloseStart` | `DoorStartParams`, the door index |
| `OnDoorOpenFinish`, `OnDoorOpenAjarFinish`, `OnDoorCloseFinish` | `DoorFinishParams`, the door index and a `bool` |
| `OnDoorLocked`, `OnDoorUnlocked` | `DoorLockParams`, the door index |

The param types are at `:1` to `:3`. `BuildingBase` already uses the open and close start events to move the physics of a door that can be rebuilt (`P:\scripts\4_world\entities\game\super\building.c:468` to `:482`), and `Bunker` uses them for its auto close timer (`building-door-locks.md`, "Bunker door"). What the `bool` of the finish params means and on which machine the events fire is not visible in script.
