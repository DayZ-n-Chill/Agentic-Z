# Seated actions and get-in faults

How to offer an action to a player sitting in a vehicle, how to run continuous actions and input excludes from the seat, and three faults that look like a broken model or get-in and are not: a misread host, a shared script core and a phantom vehicle command. The get-in condition chain is in `get-in-actions-and-proxy-pose.md`; proxies and detachable parts are in `proxies-and-detachable-parts.md`. The cases were measured on mod vehicles, mostly a helicopter on `CarScript`.

## An action for a seated player needs two registrations

A close-door action that never appears for a seated player, with the action class itself correct, is missing one of these:

1. The action must allow use in a vehicle. `ActionBase.InitConditionMask` sets `ACM_IN_VEHICLE` only when `CanBeUsedInVehicle()` returns true (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:110`), and the base returns false (`actionbase.c:361`). Any world action inherited from `ActionInteractBase` is masked out once the player is seated.
2. A seated player has no cursor target on the vehicle carrying them, so use `CCTNone` and `HasTarget()` returning false, as vanilla does (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoors.c:20` and `:120`).
3. Register it twice. `ActionConstructor.RegisterActions` puts the instance in the global pool, and `PlayerBase.SetActions(out TInputActionMap)` must call `AddAction(MyMod_Action, InputActionMap)`, where vanilla adds `ActionOpenCarDoors` and `ActionCloseCarDoors` (`P:\scripts\4_world\entities\manbase\playerbase.c:1714` and `:1715`). The second one is the one that gets missed: `FindContextualUserActions` walks the player's input action map, not the pool, so an action only in the constructor is never offered.

Vanilla keeps inside and outside in separate classes (`ActionCloseCarDoors` and `ActionCloseCarDoorsOutside`); copy that split. Ship the opening half too: if getting in and out requires an open door, a close action from inside with no open action traps the occupant. Keep one exception: a door that is not mounted must leave the seat free to leave, since no action can open it.

## Continuous actions and input excludes from the seat

- A continuous action used from a seat needs a command modifier whose progress callback runs in a vehicle. Vanilla's example is `CMD_ACTIONMOD_STARTENGINE` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:14`). A walking or door-opening modifier can animate without ever reaching `OnFinishProgress` (measured in game).
- Before an interface calls `AddActiveInputExcludes(...)`, interrupt any running action with `ActionManagerClient.RequestInterruptAction()` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:1341`). Excluding input first can swallow the key release, lock the action manager and block every later action. Record which interface owns the exclude and remove only that one, safely more than once, on close, forced close, abort and teardown. `SetDisabled(true)` alone does not block action input.
- While an exclude is active, `UAInput.LocalValue()` reads zero. `KeyState` (`P:\scripts\1_core\proto\ensystem.c:291`) and `GetMouseState` still read the physical input, but `KeyState` ignores the player's key bindings; use it for diagnostics or handle bindings yourself.
- For a seated camera, prefer keeping the pawn possessed, overriding the vehicle camera, and gating get-out in `ActionGetOutTransport.ActionCondition`. That needs no broad input exclude, which would also zero the bound aiming axes.

## The proxied parts are the reference when the host draws wrong

When a host renders wrong there is usually nothing reliable to measure it against. Parts drawn through attachment proxies are placed by the engine from the entity transform, so they are reliable. If the proxies agree with each other and disagree with the host, the host is the broken one. Do not move the proxy anchors to match it: that deforms the correct piece, and the error changes with the host's state.

On the helicopter, the doors (just moved to proxies), both rotors and the interior rose with the aircraft while the fuselage stayed on the ground, which located the rendering fault on the fuselage.

A test tool's scene raycast in proxy mode returns the Geometry LOD, not the visual mesh, so it cannot settle a visual misalignment; on a coarse collision hull it reports a surface tens of centimetres inside the visible skin. Use it for collision questions only.

## A script core shared by several vehicles

When one Enforce Script core serves several vehicle lines (one base script for two helicopter airframes), any patch in it deploys whenever any line rebuilds the core PBO, even one gated by `ConfigIsExisting("vehicleProp")` so only one line runs it. "Do not deploy the core patch until the model has its memory points" does not survive the other line's next rebuild. In the measured case one airframe's rebuild sent out the other's get-in patch, which pointed at ten memory points its deployed model did not have.

1. A core patch that depends on the model (memory points, selections, bones) must survive their absence: fall back with `MemoryPointExists` to the previous mapping, so the patch stays inert until the model ships.
2. Or ship model and core in the same build. Never leave a patch in shared source waiting for its model.
3. To know what is live, scan the deployed PBO for the patch's symbols. A note that the core changed says nothing about what went out with it.

## A phantom vehicle command after a crash while seated

The get-in prompt shows but accepting does nothing, on every seat, with no trace in the RPT or script log, and rebuilding does not help because nothing in the mod is broken. `ActionGetInTransport.ActionCondition` runs on both sides. The client's player is clean and shows the prompt, but the server's player still has a `GetCommand_Vehicle()`, restored from player storage after the client crashed while seated. The first server check rejects it silently (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:42` and `:43`), and a null `StartCommand_Vehicle` in `Start()` (`:104` and `:105`) logs nothing either.

Before blaming the model, proxies or config for a get-in regression:

1. Look in the previous run's client profile for a `crash_*.log`; a crash while seated starts the phantom.
2. With the test tool's get-in query, `first_block=already_in_vehicle` with the player standing in the open confirms it, and seating the player directly on the owner side, skipping the action checks, shows whether the seat and model are healthy.
3. A clean logout clears it. "It fixed itself next session" is the sign of this fault, not of a flaky model.

In the measured case a full get-in regression was blamed on a model edit whose Geometry, View Geometry, Fire Geometry and Memory LODs were identical before and after.
