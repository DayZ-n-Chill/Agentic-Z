# Items in hands: profiles, IK poses and showing or hiding parts

How the game decides the pose of a held item, how a mod registers its own items, and the vanilla ways to show, hide or swap parts of a model with attach state. Worked patterns and measured results are in `skills/dayz-animation-pipeline/references/item-ik-and-hide.md`.

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

## Registering a mod item

Mod the callback class and call `super`:

```c
modded class ModItemRegisterCallbacks
{
    override void RegisterTwoHanded(DayZPlayerType pType, DayzPlayerItemBehaviorCfg pBehavior)
    {
        super.RegisterTwoHanded(pType, pBehavior);
        pType.AddItemInHandsProfileIK("MyMod_Crate", "dz/anims/workspaces/player/player_main/player_main_2h.asi", pBehavior, "dz/anims/anm/player/ik/two_handed/BatteryCar.anm");
    }
}
```

`ModItemRegisterCallbacks` is at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:305`. Its callbacks, each called with the matching behaviour: `RegisterEmptyHanded` (:307), `RegisterOneHanded` (:309), `RegisterTwoHanded` (:311), `RegisterRestrained` (:313), `RegisterSurrender` (:315), `RegisterHeavy` (:317), `RegisterPistol` (:319), `RegisterFireArms` (:321), `RegisterArcheryItem` (:323), `RegisterPoleArms` (:325), `RegisterLauncher` (:327), `RegisterCustom` (:329) and `CustomBoneRemapping` (:331).

Pick the instance and pose of the vanilla item closest in size and weight. Vanilla itself mixes them freely: `GiftBox_Small` uses the pot's instance with the cauldron's pose (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1042`). When the grip is right and only the direction the item points is wrong, turning the model is cheaper than a new pose.

## A profile belongs to a class, not to one item

Every profile call takes a class name or is global: `SetDefaultItemInHandsProfile` (`P:\scripts\3_game\dayzplayer.c:225`), `ResetItemInHandsProfiles` (`P:\scripts\3_game\dayzplayer.c:229`), `AddItemInHandsProfile` (`P:\scripts\3_game\dayzplayer.c:240`), `AddItemInHandsProfileIK` and `AddItemBoneRemap`. None takes an item instance or a player. The mod callbacks run from `DayZPlayerTypeRegisterItems` when the player type is set up (`RegisterFireArms` is called at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:460`), not when an item is picked up or an attachment changes. So a pose cannot be chosen per attachment inside a callback; the only built in variation is by class, registering a base class and overriding a subclass. Author one pose that works with and without the attachment.

## Weapon parts follow player bones

`AddItemBoneRemap(string pItemClass, array<string> pBoneRemap)` (`P:\scripts\3_game\dayzplayer.c:252`) pairs a weapon's selection names with player skeleton bones, so a player clip moves the weapon's parts. Rifles map `bolt` to `Weapon_Bolt`, `magazine` to `Weapon_Magazine` and `trigger` to `Weapon_Trigger` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1579`, registered for `Rifle_Base` at :1580). The model side is in `_shared/weapons/model-selections.md`.

## Showing and hiding parts

- `HideSelection(string selection_name)` and `ShowSelection` are on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:3355`, `:3364`). They are `SetAnimationPhase` calls: 1 hides and 0 shows (`:3359`). The selection needs a `user` source of the same name and a `hide` animation in `model.cfg`.
- **Two models in one item.** The flag carries a `folded` and an `unfolded` selection, declares both as `user` sources (`P:\DZ\gear\camping\config.cpp:13052` to `:13066`), shows `folded` in its constructor and swaps them in `OnWasAttached` and `OnWasDetached` (`P:\scripts\4_world\entities\itembase\flag_base.c:7`, `:25`, `:33`).
- **A part of the host that follows a slot.** Set a hide source's phase in the host's `EEItemAttached` and `EEItemDetached` (`P:\scripts\3_game\entities\entityai.c:1159`, `:1199`).

## Switching the instance from script (1.30)

`SetAnimationInstanceByName(string animationInstanceName, float blendingTime)` on `Human` changes the player's instance with nothing in the hands (`P:\scripts\3_game\human.c:1384`); its source comment warns of desync when misused. `HumanItemAccessor.EnableAutoAnimInstUpdateOnHandsChange(bool pNewValue)` stops the engine changing it back when the hands change (`P:\scripts\3_game\humanitems.c:115`).

Vanilla's use is the surrender: it turns the automatic change off, switches to `player_main_surrender.asi` (`P:\scripts\4_world\entities\manbase\playerbase.c:2087`, `:2088`), and later switches back to `player_main.asi` by path (`:2107`). A profile named `Empty` exists only so the base instance is loaded (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1548`).
