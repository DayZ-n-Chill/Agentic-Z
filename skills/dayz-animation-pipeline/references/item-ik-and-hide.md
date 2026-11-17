# Items in hands, hide on attach, and switching the animation instance (layer 1)

Four patterns an agent writes as text, plus one measured method for syncing an object's pose with an action. All reuse the vanilla animation system instead of new clips. The checked short version is in `skills/_shared/animation/items-in-hands.md`.

## Pattern A: carry pose by reusing a vanilla IK pose

When the player picks up an item, the game needs an animation instance (`.asi`) and an IK pose (`.anm`) that say how it is held. Authoring a pose is animator work; pointing the item at a similar vanilla one is a few lines. Vanilla registers every item this way in `DayZPlayerTypeRegisterItems` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:334`), and mods add theirs through the callbacks of `ModItemRegisterCallbacks` (`:305`).

```c
modded class ModItemRegisterCallbacks
{
    override void RegisterHeavy(DayZPlayerType pType, DayzPlayerItemBehaviorCfg pBehavior)
    {
        super.RegisterHeavy(pType, pBehavior);
        pType.AddItemInHandsProfileIK(
            "MyMod_Wheel",
            "dz/anims/workspaces/player/player_main/player_main_heavy.asi",
            pBehavior,
            "dz/anims/anm/player/ik/vehicles/hatchback_02/Hatchback_02_Wheel.anm");
    }
}
```

`RegisterHeavy` is declared at `dayzplayercfgbase.c:317` and called with the heavy behaviour at `:1567`. The other callbacks (`RegisterOneHanded` :309, `RegisterTwoHanded` :311, `RegisterPistol` :319, `RegisterFireArms` :321, `RegisterCustom` :329 and the rest) work the same way; pick the one whose behaviour fits the item.

Vanilla poses for large parts, all with `player_main_heavy.asi` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:902` to `:912`):

| Item | IK pose under `dz/anims/anm/player/ik/vehicles/` |
|---|---|
| Wheel, medium (`Hatchback_02_Wheel`) | `hatchback_02/Hatchback_02_Wheel.anm` |
| Wheel, large (`Sedan_02_Wheel`) | `sedan_02/sedan_02_wheel.anm` |
| Doors | `hatchback_02/Hatchback_02_Door_driver.anm`, `Hatchback_02_Door_CoDriver.anm`, `Hatchback_02_Door_PassengerL.anm`, `Hatchback_02_Door_PassengerR.anm` |
| Hood, trunk | `hatchback_02/Hatchback_02_Hood.anm`, `hatchback_02/Hatchback_02_Trunk.anm` |

Limits: the instance file is fixed by the item's weight class, so start from the vanilla item closest to yours. The hands can clip when the item's proportions differ a lot from the vanilla one, which only an in-game test shows. One door pose used for both sides looks mirrored. Use this for an early mod with no animator and an item close to a vanilla one; a strong visual identity or a very different shape (a 1.5 m tractor wheel on the hatchback pose) needs its own pose.

### Turn the model, not the IK pose

Measured in game on a tray item (DayZDiag 1.29, 2026-09-27), not checked on `P:\`. When a vanilla IK pose already gives a natural grip and only the direction the item points is wrong, turn the item's geometry about its vertical, keeping its origin, and leave the pose alone. The tray was turned 90 degrees when the `.p3d` was assembled so its 43 cm length lay along X, then registered in `RegisterTwoHanded` with no pose of its own:

```c
pType.AddItemInHandsProfileIK("MyMod_Tray", "dz/anims/workspaces/player/player_main/props/player_main_2h_pot.asi", pBehavior, "dz/anims/anm/player/ik/vehicles/BatteryTruck.anm");
```

That pairs the truck battery's IK pose (vanilla `TruckBattery`, `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:867`) with the pot's animation set. Vanilla makes the same kind of pairing for `GiftBox_Small` (`:1042`: the pot's `.asi` with the cauldron's pose). The hands took the tray by its short ends in the battery's pose and the pot's pour animation stayed.

Before that, the pot's own pose put the hands through the tray, and a custom pose with `RightHand_Dummy` turned about the wrong SEAnim axis broke the grip (frames and axes: `player-skeleton.md`, "The frame an IK pose is keyed in"). The grip was chosen in game among six vanilla poses, with one test subclass of the item per pose, the same method `weapon-in-hands.md` uses for weapons.

To shortlist poses by size, the wrist's distance from the item's origin (length of the `RightHand_Dummy` key, measured offline from the extracted clips): pot 16.9 cm, cauldron 16.3, car battery 18.4, truck battery 31.0, car radiator 36.9.

## Pattern B: hide on attach

A part that is already in the host's `.p3d` appears or disappears with what is attached to a slot. Its visibility is a `hide` animation on a `user` source, set in the attach and detach events.

`config.cpp`:

```cpp
class AnimationSources
{
    class hide_barrel1 { source = "user"; animPeriod = 0.1; initPhase = 1; };   // starts hidden
};
```

`model.cfg`, inside `class Animations`:

```cpp
class hide_barrel1 { type = "hide"; source = "hide_barrel1"; selection = "barrel_1"; minValue = 0; maxValue = 1; hideValue = 0.5; };
```

Script on the host:

```c
override void EEItemAttached(EntityAI item, string slot_name)
{
    super.EEItemAttached(item, slot_name);
    if (slot_name == "MyMod_Barrel1")
        SetAnimationPhase("hide_barrel1", 0);   // 0 shows
}

override void EEItemDetached(EntityAI item, string slot_name)
{
    super.EEItemDetached(item, slot_name);
    if (slot_name == "MyMod_Barrel1")
        SetAnimationPhase("hide_barrel1", 1);   // 1 hides
}
```

- Phase 1 hides and phase 0 shows. Vanilla says so itself: `HideSelection` is `SetAnimationPhase(selection_name, 1)` with the comment "1 = hide, 0 = unhide!" (`P:\scripts\3_game\entities\entityai.c:3355` to `:3361`). The value where the flip happens is `hideValue`; vanilla barrel lids use 0.6 (`skills/_shared/animation/model-cfg-animations.md`), and the 0.5 above was used in game on a vehicle mod.
- `EEItemAttached` and `EEItemDetached` are on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:1159`, `:1199`). `EEItemAttached` also fires for items created with `CreateInInventory` (seen in game, not checked on `P:\`), so debug spawned attachments update too.
- The attached item is still a real inventory item; the hide only changes how the host shows it.
- Use it for visible cargo (jerry cans, barrels, spare wheels) and modular parts that would otherwise need many `.p3d` variants. Do not use it when the part changes collision: that needs real model variants.

## Pattern C: swap the model by attach state (two selections on the item)

The item carries two selections, a detailed one for the ground and a lighter one for when it is attached, and shows one of them. The item drives it from its own hooks, not the host. Vanilla does exactly this with the flag:

- Config: two `user` sources named after the selections, `folded` with `initPhase = 0` (shown) and `unfolded` with `initPhase = 1` (hidden) (`P:\DZ\gear\camping\config.cpp:13052` to `:13066`).
- Script: the constructor shows `folded` and hides `unfolded`, `OnWasAttached` swaps them and `OnWasDetached` swaps back (`P:\scripts\4_world\entities\itembase\flag_base.c:7`, `:25`, `:33`).

```c
void MyItem()
{
    ShowSelection("not_attached");
    HideSelection("attached");
}

override void OnWasAttached(EntityAI parent, int slot_id)
{
    super.OnWasAttached(parent, slot_id);
    HideSelection("not_attached");
    ShowSelection("attached");
}

override void OnWasDetached(EntityAI parent, int slot_id)
{
    super.OnWasDetached(parent, slot_id);
    ShowSelection("not_attached");
    HideSelection("attached");
}
```

`ShowSelection` and `HideSelection` are on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:3364`, `:3355`); the `OnWasAttached` and `OnWasDetached` hooks are declared at `:1864` and `:1867`. The `model.cfg` needs its own skeleton with both selections as bones and one `hide` animation per selection, each with the selection's name as its source. `hiddenSelections[]` still lists only the texture selections. Both selections must exist in the visual LODs and the View Geometry, and in the Geometry LOD when the attached model needs collision.

Compared with pattern B: B hides one selection from the host's attach events; C swaps two selections from the item's own events.

## Pattern D: switch the animation instance from script (1.30)

Since 1.30 script can change the player's animation instance at run time with no item in the hands.

```c
//! sets the animation instance of the player character - careful when using, could create desync if not used properly
proto native void SetAnimationInstanceByName(string animationInstanceName, float blendingTime);
```

`SetAnimationInstanceByName` is on `Human` (`P:\scripts\3_game\human.c:1384`). `HumanItemAccessor` lets a mod stop the engine changing the instance by itself when the item in hands changes (`P:\scripts\3_game\humanitems.c:112` to `:118`):

```c
proto native void OnItemInHandsChanged(bool pInstant = false, bool pChangeAnimationInstance = true);
proto native void EnableAutoAnimInstUpdateOnHandsChange(bool pNewValue);
proto native bool IsAutoAnimInstUpdateOnHandsChangeEnabled();
```

**Going back to empty hands.** Vanilla registers a profile named `Empty` so the base instance is loaded and can be switched to (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1548`). It switches by the `.asi` path, not the profile name: `SetAnimationInstanceByName("dz/anims/workspaces/player/player_main/player_main.asi", 1)` (`P:\scripts\4_world\entities\manbase\playerbase.c:2107`). Measured in game: a mod's child `.asi` registered the same way was switched to by its path (`vehicle-rider-ik-pose.md`). Passing the name `"Empty"` instead of a path is not tested.

**Surrender without a dummy item.** Up to 1.29 the hands up emote put an invisible `SurrenderDummyItem` in the hands. In 1.30 nothing goes into the hands. The dummy's profile is still registered so `player_main_surrender.asi` is loaded (`dayzplayercfgbase.c:1543`), and `PlayerBase` switches to it:

```c
protected void OnStartTransitionToSurrender()
{
    m_StartedSurrenderTransition = true;
    HumanInputController hic = GetInputController();
    hic.DisableProneCameraHorizontalRotation(true);
    g_Game.GetMission().AddActiveInputRestriction(EInputRestrictors.SURRENDER_TRANSITION);
    GetItemAccessor().EnableAutoAnimInstUpdateOnHandsChange(false);
    SetAnimationInstanceByName("dz/anims/workspaces/player/player_main/player_main_surrender.asi", 1);
    m_SurrenderTransitionTimer = m_SurrenderAnimationTransitionTime;
}
```

That is `OnStartTransitionToSurrender` at `P:\scripts\4_world\entities\manbase\playerbase.c:2081` to `:2090`.

State is set with `SetSurrenderState(bool newState)` (`playerbase.c:2116`) and read with `IsSurrendered()` (`P:\scripts\3_game\entities\man.c:67`). The class `SurrenderDummyItem` remains, marked obsolete (`P:\scripts\4_world\entities\itembase\surrenderdummyitem.c:1`).

## Syncing an object's pose to a continuous action

Measured in game on a pot emptying action (seven runs, client and server within ±3 ms; DayZ 1.30.164014 Experimental). Not checked on `P:\` beyond the calls named.

1. **Probe first.** Add a test `modded class` of the action that logs the `OnStart` and loop events, every change of `HumanCommandActionCallback.GetState()` (states at `P:\scripts\3_game\human.c:369` to `:380`, `GetState` at `:383`), and one sample every 0.1 s from `OnUpdateClient` and `OnUpdateServer` (both run every frame, `P:\scripts\4_world\classes\useractionscomponent\actionbase.c:1356`, `:1372`), each sample with the object's `GetAnimationPhase`.
2. **A `user` source has one `animPeriod` for both directions.** If out and back take different times, drive the return with targets set every frame on the client.
3. **Two writers coexist only when they write the same target.** The server writes the start and the end; the owning client carries the states between.
4. **State timings alone are not enough.** The engine started the final segment 0.03 to 0.05 s after the loop and played it 5 to 10 percent faster than 30 fps, and the curve inside a segment is not linear. Moving the object inside the animation itself removes the problem instead of softening it.
5. Even with states matched to the millisecond, the hand that is not the anchor follows the vanilla graph's curve.
