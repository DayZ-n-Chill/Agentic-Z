# Items in hands: profiles, IK poses and the animation instance

How the game decides the pose of a held item, how a mod registers its own items, how script switches the player's animation instance, and one measured method for syncing an object's pose with an action. All of it reuses the vanilla animation system instead of new clips. Showing, hiding or swapping parts of a model with attach state is in `attach-state-parts.md`.

## The profile

Every holdable class gets its pose from a profile registered in script:

```c
proto native int AddItemInHandsProfileIK(string pItemClass, string pAnimInstanceName, HumanItemBehaviorCfg pBehaviorCfg, string pIkPoseAnim, string pWeaponStates = "");
```

(`P:\scripts\3_game\dayzplayer.c:243`.)

| Argument | Meaning | Vanilla example |
|---|---|---|
| `pItemClass` | The config class. Children inherit the profile. | `Inventory_Base` gets the one handed default with the apple's pose (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:373`). |
| `pAnimInstanceName` | The animation instance (`.asi`): which clips play while it is held. | `player_main_heavy.asi` for car parts (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:902`). |
| `pBehaviorCfg` | The behaviour: one handed, two handed, heavy, firearm. | `heavyItemBehaviour` on the same line. |
| `pIkPoseAnim` | The IK pose clip: where the hands sit on this item. | `dz/anims/anm/player/ik/vehicles/hatchback_02/Hatchback_02_Wheel.anm` on the same line. |
| `pWeaponStates` | For weapons, the clip of the weapon's own part states. | `w_akm_states.anm` for `AKM_Base` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:412`). |

Vanilla registers everything in `DayZPlayerTypeRegisterItems` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:334`).

## Registering a mod item: reuse a vanilla IK pose

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

`ModItemRegisterCallbacks` is at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:305`. Its callbacks, each called with the matching behaviour: `RegisterEmptyHanded` (:307), `RegisterOneHanded` (:309), `RegisterTwoHanded` (:311), `RegisterRestrained` (:313), `RegisterSurrender` (:315), `RegisterHeavy` (:317), `RegisterPistol` (:319), `RegisterFireArms` (:321), `RegisterArcheryItem` (:323), `RegisterPoleArms` (:325), `RegisterLauncher` (:327), `RegisterCustom` (:329) and `CustomBoneRemapping` (:331).

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

Measured in game on a tray item on 1.29, not checked on `P:\`. When a vanilla IK pose already gives a natural grip and only the direction the item points is wrong, turn the item's geometry about its vertical, keeping its origin, and leave the pose alone. For the tray, turn it 90 degrees when the `.p3d` is assembled so its 43 cm length lay along X, then register it in `RegisterTwoHanded` with no pose of its own:

```c
pType.AddItemInHandsProfileIK("MyMod_Tray", "dz/anims/workspaces/player/player_main/props/player_main_2h_pot.asi", pBehavior, "dz/anims/anm/player/ik/vehicles/BatteryTruck.anm");
```

That pairs the truck battery's IK pose (vanilla `TruckBattery`, `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:867`) with the pot's animation set. Vanilla makes the same kind of pairing for `GiftBox_Small` (`:1042`: the pot's `.asi` with the cauldron's pose). The hands take the tray by its short ends in the battery's pose, and the pot's pour animation stays.

The pot's own pose puts the hands through the tray, and a custom pose with `RightHand_Dummy` turned about the wrong SEAnim axis breaks the grip (frames and axes: `player-skeleton.md`, "The frame an IK pose is keyed in"). Choose a grip in game among several vanilla poses, with one test subclass of the item per pose, the same method `weapon-in-hands.md` uses for weapons.

To shortlist poses by size, the wrist's distance from the item's origin (length of the `RightHand_Dummy` key, measured offline from the extracted clips): pot 16.9 cm, cauldron 16.3, car battery 18.4, truck battery 31.0, car radiator 36.9.

## A profile belongs to a class, not to one item

Every profile call takes a class name or is global: `SetDefaultItemInHandsProfile` (`P:\scripts\3_game\dayzplayer.c:225`), `ResetItemInHandsProfiles` (`P:\scripts\3_game\dayzplayer.c:229`), `AddItemInHandsProfile` (`P:\scripts\3_game\dayzplayer.c:240`), `AddItemInHandsProfileIK` and `AddItemBoneRemap`. None takes an item instance or a player. The mod callbacks run from `DayZPlayerTypeRegisterItems` when the player type is set up (`RegisterFireArms` is called at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:460`), not when an item is picked up or an attachment changes. So a pose cannot be chosen per attachment inside a callback; the only built in variation is by class, registering a base class and overriding a subclass. Author one pose that works with and without the attachment.

## Weapon parts follow player bones

`AddItemBoneRemap(string pItemClass, array<string> pBoneRemap)` (`P:\scripts\3_game\dayzplayer.c:252`) pairs a weapon's selection names with player skeleton bones, so a player clip moves the weapon's parts. Rifles map `bolt` to `Weapon_Bolt`, `magazine` to `Weapon_Magazine` and `trigger` to `Weapon_Trigger` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1579`, registered for `Rifle_Base` at :1580). The model side is in `_shared/weapons/model-selections.md`.

## Switching the instance from script (1.30)

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

Going back to empty hands: vanilla registers a profile named `Empty` so the base instance is loaded and can be switched to (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1548`). It switches by the `.asi` path, not the profile name: `SetAnimationInstanceByName("dz/anims/workspaces/player/player_main/player_main.asi", 1)` (`P:\scripts\4_world\entities\manbase\playerbase.c:2107`). Measured in game: a mod's child `.asi` registered the same way was switched to by its path (`rider-pose-measured.md`). Passing the name `"Empty"` instead of a path is not tested.

Surrender without a dummy item: up to 1.29 the hands up emote put an invisible `SurrenderDummyItem` in the hands. In 1.30 nothing goes into the hands. The dummy's profile is still registered so `player_main_surrender.asi` is loaded (`dayzplayercfgbase.c:1543`), and `PlayerBase` switches to it:

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

Measured in game on 1.30 Experimental on a pot emptying action, over seven runs with client and server within ±3 ms. Not checked on `P:\` beyond the calls named.

1. Probe first. Add a test `modded class` of the action that logs the `OnStart` and loop events, every change of `HumanCommandActionCallback.GetState()` (states at `P:\scripts\3_game\human.c:369` to `:380`, `GetState` at `:383`), and one sample every 0.1 s from `OnUpdateClient` and `OnUpdateServer` (both run every frame, `P:\scripts\4_world\classes\useractionscomponent\actionbase.c:1356`, `:1372`), each sample with the object's `GetAnimationPhase`.
2. A `user` source has one `animPeriod` for both directions. If out and back take different times, drive the return with targets set every frame on the client.
3. Two writers coexist only when they write the same target. The server writes the start and the end; the owning client carries the states between.
4. State timings alone are not enough. The engine starts the final segment 0.03 to 0.05 s after the loop and plays it 5 to 10 percent faster than 30 fps, and the curve inside a segment is not linear. Moving the object inside the animation itself removes the problem instead of softening it.
5. Even with states matched to the millisecond, the hand that is not the anchor follows the vanilla graph's curve.
