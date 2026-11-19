# Action, input and camera rules

Which rules keep actions, recipes, liquid containers, input files and vehicle sights working, each tied to a failure seen in a real mod. The general language rules are in `hard-rules.md`.

## Actions

- Use `CCINonRuined` for an action that needs an item in hand. `CCINone` means "no item condition" and checks no tool; reported, not checked on `P:\`: with `CCINone` plus a tool check in `ActionCondition` the action may not appear while the tool is held. `../patterns/actions.md` has the condition table.
- Check tools with `IsKindOf()`, not `GetType() ==`, so inherited and modded variants match, and use the same check in `ActionCondition` and in the server RPC handler.
- To stop a placed object being picked up or dragged, `RemoveAction(ActionTakeItem)` and `RemoveAction(ActionTakeItemToHands)`, and return false from `IsTakeable()` and `CanPutInCargo()`.
- Test the cursor's component through the engine's name list, in lower case. `GetActionComponentNameList(idx, list, "")` (`P:\scripts\3_game\entities\object.c:192`) returned `component14`, `component19` and `door1` for a runtime `House` (measured in game). The names are lower case, and the cursor index is 0 based while Object Builder's automatic names are 1 based (component 13 is `component14`, component 18 is `component19`, component 8 is `door1`). `IsActionComponentPartOfSelection(idx, "Component14", LOD.NAME_VIEW)` never matched, so the actions were dead with no error. Compare `list.Get(i)` after `ToLower()` against lower case names in the default geometry, and while diagnosing log `idx` and the list once per index.

## Recipes

Copy `ingredients[0]` and `ingredients[1]` to locals at the top of `CanDo`, and do not call `super.CanDo`. Measured in game on DayZ 1.29: a `CanDo` that began with `if (!super.CanDo(ingredients, player)) return false;` and then cast the two slots returned false on the server while every part of its condition read true, so `ActionWorldCraft.ActionConditionContinue` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionworldcraft.c:89` to `:107`) cancelled the craft as it started. Read after `super`, both slots held the same item. Copying both slots to locals and dropping `super` fixed it; the same change also split the final `return tray && ...` into a null guard, so which part mattered is not isolated.

Vanilla almost never calls it: of 218 `CanDo` overrides in `P:\scripts\4_world\classes\recipes\recipes\`, only `craftlongtorch.c:61` does, as its only statement: `return super.CanDo(ingredients, player);`. Without `super` the recipe loses the one check in `RecipeBase.CanDo`, that no ingredient has attachments (`P:\scripts\4_world\classes\recipes\recipebase.c:551` to `:561`); repeat it on the locals when the recipe needs it (not tested). Unverified: why the slots change, whether a `super` call after the copy is harmless, and whether vanilla's `return super.CanDo(...)` form is affected.

## Liquid containers

A container derived from `Bottle_Base` inherits the whole vanilla liquid action set; decide each one. `SetActions` adds 16 liquid actions in DayZ 1.30 (`P:\scripts\4_world\entities\itembase\edible_base\bottle_base.c:356` to `:376`; 14 in 1.29, at 1.29 `bottle_base.c:354` to `:372`, a build not on `P:\`), and each is a way in or out.

- The fill action takes gasoline from a pump: `m_AllowedLiquidMask = LIQUID_GROUP_DRINKWATER | LIQUID_GASOLINE` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfillbottlebase.c:41` to `:44`; the 1.30 `ActionObtainLiquidBase` sets the same mask at `actionobtainliquidbase.c:50`).
- With your container as the target, drain and pour belong to the held item (`ActionCondition` in `actiondrainliquid.c:33` to `:42` and `actionpourliquid.c:33` to `:42`, same folder). Removing them from the container's own `SetActions` hides nothing. Close them in a `modded` action's `ActionCondition` on `target.GetObject()`, or gate the liquid by overriding `GetLiquidContainerMask()`, the only input of `Liquid.CanFillContainer` (`P:\scripts\4_world\static\liquid.c:248`).
- The continuous pour can stop short of full (960 of 1000 ml, measured once in game). A rule that demands an exact amount needs a tolerance, or must finish in `OnEndServer` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:1409`).
- `ActionEmptyBottleBase` overrides `OnStartAnimationLoop` and `OnEndAnimationLoop` without `super` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionemptybottlebase.c:70` to `:78`). In its subclasses the protected `OnStartAnimationLoopServer`, `OnStartAnimationLoopClient` and `OnEndAnimationLoop*` of `ActionContinuousBase` (`P:\scripts\4_world\classes\useractionscomponent\actions\actioncontinuousbase.c:272` to `:286`, which set `m_WasActionStarted`) never run, with no error. Hook the public loop callbacks instead (called on both sides, `:197` to `:242`) and act only on the server; `OnEndServer` also runs after an interrupt and is the safe place to reset.

## Input files

- The root tag of `inputs.xml` is `<modded_inputs>`, not `<modinfo>`. `<actions>` declares the input names and `<preset>` sets default keys.
- Point `config.cpp` at the file with an `inputs` entry in `CfgMods`, with backslashes (`inputs = "ModName\\inputs.xml";`) or forward slashes from the prefix (`inputs = "MyMod/data/inputs.xml";`, see `../integrations/input_bindings.md`).
- Three ways to read an input, all used in shipped mods: `g_Game.GetInput().LocalPress("UAMyAction", false)` for a one-line check; `GetUApi().GetInputByName("UAMyAction").LocalPress()` per frame; a stored `UAIDWrapper wrapper = input.GetPersistentWrapper()` with `wrapper.InputP().LocalPress()`, the sturdiest for a kept reference.
- Avoid keys other mods take: VPPAdminTools uses `kP` (copy position), `kEnd` (toggle) and `kHome` (menu), Community Online Tools uses `kHome`, and group mods take more. Pick uncommon keys such as `kU` or `kO`.

## Excludes that kill mouse look

An `<exclude>` that includes `inventory` silently stops mouse look. `inventory` includes `aiming` (`P:\bin\specific.xml:242` to `:244`), and `aiming` is exactly `UAAimLeft`, `UAAimRight`, `UAAimUp` and `UAAimDown` (`:149` to `:154`). A camera, sight or scripted view that excludes `inventory` reads 0.0 from every look axis, with no error. The tell: the camera answers WASD, because raw `KeyState` bypasses excludes, but ignores the mouse.

- Exclude inventory's own contents without `aiming`: `gestures`, `stances`, `optics`, `actions` and `UAUIGesturesOpen`.
- Read the axes as the vanilla spectator does: `GetUApi().GetInputByID(UAAimLeft).LocalValue()` (`P:\scripts\4_world\entities\dayzspectator.c:39` to `:44`).
- `menu` includes `inventory` too (`specific.xml:277` and `:278`), so keeping `menu` in the exclude set as a fallback brings the same block back. Expand every group you pass and check that none reaches `aiming`; never trust a group's name.

Measured in game on a helicopter sight: the exclude and the axis read are separate problems, and fixing one alone changes nothing.

## Sights and turrets on a seated player

Never take the pawn away from a seated player. Mod vanilla's vehicle camera and write its transform instead:

- `CameraHandler` returns `DayZPlayerCameras.DAYZCAMERA_1ST_VEHICLE` (30, `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:18`, registered at `:61`) while the sight is up.
- `modded class DayZPlayerCamera1stPersonVehicle` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`) overrides `OnUpdate` to fill `pOutResult.m_CameraTM`: build it in world space with `Math3D.DirectionAndUpMatrix(dir, hullTM[1], camWorld)`, convert to player space with `Math3D.MatrixInvMultiply4(playerTM, camWorld, camLocal)`, set `m_fUseHeading = 0` so head turning does not drag the view, and use `StdFovUpdate` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera_base.c:327`) for the field of view, with zoom in `m_fFovMultiplier`.
- The pawn is never released, so nothing needs restoring: the input controller stays on, there is no focus lock and no exclude, which also removes the mouse look trap above. Verified in game on a helicopter sight.
- Block getting out while the sight is up with one condition, `modded class ActionGetOutTransport` overriding `ActionCondition` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:70`).

The `SelectPlayer(null)` and `SelectSpectator(...)` pattern from Community Online Tools and CCTV mods was written for a player on foot. From a seat, `SelectPlayer(identity, player)` on exit restores the pawn but not its `HumanCommandVehicle`, so the player freezes while every cleanup log reports success. Rebuilding the command as vanilla does after unconsciousness, `StartCommand_Vehicle(transport, CrewMemberIndex(p), GetSeatAnimationType(idx), true)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2391` to `:2396`; the proto is at `P:\scripts\3_game\human.c:1526`), puts the player back in the seat (a probe read `vehCmd=true seat1=true parent=true inVeh=true`), but the camera never returns and the mouse moves only the head (measured in game). If old code still uses this path, pair `ChangeGameFocus(-1)` with `ResetGameFocus()` (`P:\scripts\5_mission\gui\cameratools\cameratoolsmenu.c:797` to `:800`), since `HasGameFocus` is true only at exactly 0 (`P:\scripts\3_game\tools\input.c:29` to `:34`). In a vehicle vanilla takes the camera from `m_Camera3rdPerson` whenever the server allows third person (`dayzplayerimplement.c:2891` to `:2914`; 1.29 `:2849` to `:2868`), so a sight must force first person with `SetIsInThirdPerson(false)` (`:307` to `:310`) and restore the old value on exit.
