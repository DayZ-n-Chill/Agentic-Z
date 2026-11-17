# Bone remap: weapon selection to player skeleton bone

Which weapon selection maps to which player bone, when a remap is needed, and the rule that the selection must cover the part first. How the bone moves is animation work and belongs to the dayz-animation-pipeline skill.

Marks: `[VERIFIED in-game]` means measured in game on a custom 9x19 SMG build that inherits a third-party weapon pack (third-party mod behaviour, not vanilla; its files are not on `P:\`), `[VERIFIED-vanilla]` means read in the cited vanilla file, `[UNVERIFIED]` means inferred.

## The API

`[VERIFIED-vanilla]` `AddItemBoneRemap` is declared on `DayZPlayerType` (`P:\scripts\3_game\dayzplayer.c:252`):

```c
proto native int AddItemBoneRemap(string pItemClass, array<string> pBoneRemap);
```

The vanilla comment above it (`P:\scripts\3_game\dayzplayer.c:245-250`) says the array always has 2 x N members, the bone in the item's P3D first and the bone in the character skeleton second, and gives this example:

```c
//! array<string> remap = { "bolt", "Weapon_Bolt", "magazine", "Weapon_Magazine", "trigger", "Weapon_Trigger" };
//! AddItemBoneRemap("class", remap);
```

So the array is a flat list of pairs: weapon selection first, player skeleton bone second.

The call that binds the IK pose, `AddItemInHandsProfileIK`, is next to it (`P:\scripts\3_game\dayzplayer.c:243`) `[VERIFIED-vanilla]`:

```c
proto native int AddItemInHandsProfileIK(string pItemClass, string pAnimInstanceName, HumanItemBehaviorCfg pBehaviorCfg, string pIkPoseAnim, string pWeaponStates = "");
```

The fifth argument, `pWeaponStates`, is the weapon state `.anm` that drives `Weapon_Bolt`. That animation is made on the animation side (the dayz-animation-pipeline skill); the entity side only passes its path in the registration.

Both are called from a `modded class ModItemRegisterCallbacks` that overrides a `Register*` method and calls `super` first. `RegisterFireArms` is declared at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:321`.

## A real remap: a custom SMG

`[VERIFIED in-game]` (2026-06-30) The SMG's `DayZPlayerCfgBase.c` registers the pairs `bolt` to `Weapon_Bolt` and `trigger` to `Weapon_Trigger` for the weapon's base class, inside `override void RegisterFireArms(DayZPlayerType pType, DayzPlayerItemBehaviorCfg pBehavior)`, after `super.RegisterFireArms(...)`, next to the `AddItemInHandsProfileIK` call for the same class that binds the weapon's own weapon state `.anm`. Written for your own class, the shape is:

```c
modded class ModItemRegisterCallbacks
{
    override void RegisterFireArms(DayZPlayerType pType, DayzPlayerItemBehaviorCfg pBehavior)
    {
        super.RegisterFireArms(pType, pBehavior);

        array<string> partRemap = { "bolt", "Weapon_Bolt", "trigger", "Weapon_Trigger" };
        pType.AddItemBoneRemap("MyMod_Smg_Base", partRemap);
    }
}
```

- `Weapon_Bolt` is driven by the weapon state `.anm` (the fifth `AddItemInHandsProfileIK` argument).
- `Weapon_Trigger` is driven by the vanilla player fire and reload animations. On the SMG it was seen animated in `p_erc_fire_*_ras` and `p_erc_reload_action_pm73_ras`; without the remap the trigger does nothing on fire.
- `magazine` is left out of the remap on purpose: on the SMG it rides the `model.cfg` animation sources, so it is not driven twice.

## When a remap is needed

- **Needed** only when the weapon's bolt or trigger must be animated by the player skeleton, that is, when you inherit vanilla fire, reload or chamber animations that move the `Weapon_*` bones. `[VERIFIED in-game]` on the SMG.
- **Not needed** when a part animates only through `model.cfg` animation sources (the magazine on the SMG).

Condition learned the hard way (W-SEL1): the selection must really cover the part (`p3d-selection-contract.md`), and the weapon must have a `weaponStateAnim` whose bolt channel exists. The SMG kept the AKS74U weapon states as its `weaponStateAnim` and `onlyIfBoltIsOpen=1` in its config, so the state machine was ready; only the remap and a correct selection were missing.

## Bone remap is the standard pattern

`[VERIFIED-vanilla]` Vanilla registers a remap per weapon base: `Rifle_Base` with `bolt`, `magazine`, `trigger`, `charging`, `bullet`, `mag_release` and `boltrelease` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1579-1580`), `BoltActionRifle_Base` (`:1591-1592`), and single weapons after the "Specific weapons" comment at `:1594`.

Third-party weapon packs do the same, per weapon class (third-party mod behaviour, not vanilla, and not on `P:\`, so read the pack's own script before quoting an exact array). One pack registers each of its pump and semi-automatic shotgun base classes against two shared named arrays, one per mechanism; another registers its pistols the same way from its own `4_World` script.

## Boundary

`AddItemBoneRemap` is glue on the entity side: which selection maps to which bone, and checking the selection covers the part. The bone's motion (the weapon state `.anm` for the bolt, the action animations for fire, reload, chamber, jam and unjam, what the IK pose in `AddItemInHandsProfileIK` means, and the player skeleton bones `Weapon_Root`, `RightHand_Dummy` and `LeftHandIKTarget`) all belongs to the dayz-animation-pipeline skill.

## DayZ 1.30: vanilla hand profiles and extra remaps

`[VERIFIED-vanilla]` All lines below are in `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c`. The entity side only records the registration; making the `.anm` stays with the animation skill. The data on `P:\` has no model for the four new weapons (W-STAGING1 in `dayz-1-30-weapons.md`), so the arrays below are the selection names a model for those classes must cover.

The default rifle remap still applies to anything under `Rifle_Base` (`:1579-1580`): `bolt`, `magazine`, `trigger`, `charging`, `bullet`, `mag_release`, `boltrelease`. `SCARL_Base` and `MP18_Base` have no `AddItemBoneRemap` of their own; they inherit that rifle map. The `SCARL_Base` hand profile is the SCAR-H one (`:445`, the same `.asi`, IK pose and weapon states as `SCARH_Base` at `:444`).

```c
// [EXACT] P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1605
		array<string> LeeEnfieldBoneRemap ={ "bolthandle", "Weapon_Bolt", "boltbody", "Weapon_Bone_01", "trigger", "Weapon_Trigger", "bullet", "Weapon_Bullet", "bullet1", "Weapon_Bone_02", "magazine", "Weapon_Magazine"};
		pType.AddItemBoneRemap("LeeEnfield_Base", LeeEnfieldBoneRemap);
```

```c
// [EXACT] P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1621
		array<string> LugerBoneRemap ={ "bolt", "Weapon_Bolt", "magazine", "Weapon_Magazine", "bullet","Weapon_Bullet", "trigger", "Weapon_Trigger", "slide", "Weapon_Bone_01", "toggle1", "Weapon_Bone_02", "toggle2", "Weapon_Bone_03" };
		pType.AddItemBoneRemap("Luger_Base", LugerBoneRemap);
```

W-SEL1 still applies: `slide`, `toggle1` and `toggle2` (Luger) and `bolthandle`, `boltbody` and `bullet1` (Lee-Enfield) must cover those parts before you trust the remap. The recoil script classes (`SCARLRecoil`, `LugerRecoil`, `LeeEnfieldRecoil`, `MP18Recoil`) are in `P:\scripts\4_world\classes\recoilbase\recoils\`; see `dayz-1-30-weapons.md`.
