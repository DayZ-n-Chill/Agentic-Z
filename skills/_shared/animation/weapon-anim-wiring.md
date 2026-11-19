# Wiring a weapon animation into the game

How a compiled weapon clip reaches the player: the instance file, the state names it may fill, the script registration and bone remap, how the graph picks column and state, the weapon's own `model.cfg` and `config.cpp`, and the mod layout. The link between a weapon and its animation is entirely in script, the `AddItemInHandsProfileIK` call; no `config.cpp` key holds it, and newcomers lose time looking for one. Compiling is in `weapon-anim-compile.md`.

## The instance file

One text file per weapon. The 1.30 form, as vanilla writes it for the AKM (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_akm.asi:1` to `:9`):

```text
AnimSetInstanceSource {
 Template "{F0C651DE8E24A5DE}DZ/anims/workspaces/player/player_main/player_main.ast"
 ParentTemplates {
  "{416372172B0AFA90}DZ/anims/workspaces/player/player_main/player_main_rifle.asi"
 }
 IkPose "{F7A52CEE6628658F}DZ/anims/anm/player/ik/weapons/izh18.anm"
 Lines {
  AnimSetInstanceSource_Line "WeaponOperations.ErcRas.Chambering_Closed" {
   Resource "{B3DA38AE1EEA3954}DZ/anims/anm/player/reloads/AKM/p_erc_chambering_Closed_AKM_ras.anm"
  }
```

- `Template` names the `.ast`, `ParentTemplates` the parent instance, `IkPose` the grip pose; each line maps one state to one clip.
- A rifle's parent chain is the weapon's instance, `player_main_rifle.asi`, `player_main.asi`; other weapons put the pistol, two handed, one handed or heavy instance in the middle.
- Copy the closest vanilla weapon's instance. The template lists every legal name and each weapon fills some; the AKM's has 11 lines per column.
- The demo mod's instance uses the 1.29 form (`$animsetinstance { #template ... #nparents 1 #parent ... #ikpose ... $animations { ... } }`). Write the 1.30 form; the port is in `anim-graph-format-1-30.md`, "Porting a 1.29 `$AnimGraph 7` graph to 1.30".

Keep the `{GUID}` prefixes. Every `Template`, parent, `IkPose` and `Resource` value in a vanilla instance carries one; only the hand written demo files omit them. Keep them on copied vanilla lines and let Workbench generate new ones. A `Resource` line also loaded with a bare path and with an invented `{GUID}` for a rider pose (`rider-pose-measured.md`), so a bare path is not known to fail, but nothing is gained by removing what vanilla writes.

## State names

A line is named `WeaponOperations.<column>.<state>`. The group has two columns, `ErcRas` (erect, raised) and `PneRas` (prone, raised), declared at its end (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1262` to `:1265`). There is no crouch column: crouch uses `ErcRas` and the stance machine handles the rest, so never invent `WeaponOperations.CroRas`. The 86 vanilla weapon instances of 1.30 hold 701 `ErcRas` lines, 697 `PneRas` lines and no other column.

The 42 states (`Name "WeaponOperations"` at `player_main.ast:1217`, listed `:1219` to `:1260`):

`ChamberingBulletL`, `ChamberingBulletR`, `ChamberingCancel`, `ChamberingFast_Closed`, `ChamberingFast_Open`, `ChamberingIn`, `ChamberingLook`, `ChamberingLoop`, `ChamberingLoop1`, `ChamberingLoop_Closed_Bullet`, `ChamberingLoop_Closed_NoBullet`, `ChamberingLoop_Open_Bullet`, `ChamberingLoop_Open_NoBullet`, `ChamberingOut`, `Chambering_Closed`, `Chambering_Closed_Uncocked`, `Chambering_NoBulletL`, `Chambering_NoBulletR`, `Chambering_Open`, `Fire`, `FireCocked`, `FireEmptyAutomatic`, `FireJam`, `FireLast`, `FireUncocked`, `Jamming`, `Jamming Cancel`, `Jamming Check`, `Obstruction`, `ReloadAction_Closed`, `ReloadAction_Closed_Uncocked`, `ReloadAction_Open`, `ReloadBoltAction2`, `ReloadClipInBullet`, `ReloadClipInNoBullet`, `ReloadClipOut`, `ReloadClipPose`, `ReloadMagBullet`, `ReloadMagNoBullet`, `ReloadMagazineDetach`, `ReloadNoMagBullet`, `ReloadNoMagNoBullet`.

Names are exact, dotted and case sensitive; `Jamming Cancel` and `Jamming Check` hold a real space. A mistyped or missing name falls back to the parent's clip with no error, or breaks that operation. The group has no mode switch state. `player_main.ast` is the schema of legal names; its grammar is undocumented, so copy from the vanilla file (the 1.30 form is in `anim-instances-and-templates.md`, "Template files (`.ast`): every group is named").

## Script registration

In the mod's `4_World` scripts:

```c
modded class ModItemRegisterCallbacks
{
    override void RegisterFireArms(DayZPlayerType pType, DayzPlayerItemBehaviorCfg pBehavior)
    {
        super.RegisterFireArms(pType, pBehavior);
        pType.AddItemInHandsProfileIK("MyMod_SVD_Base", "MyMod/Animations/SVD/MyMod_SVD.asi", pBehavior, "MyMod/Animations/SVD/MyMod_SVD_IK.anm", "MyMod/Animations/SVD/w_MyMod_SVD_states.anm");
    }

    override void CustomBoneRemapping(DayZPlayerType pType)
    {
        super.CustomBoneRemapping(pType);
        array<string> remap = { "bolt", "Weapon_Bolt", "magazine", "Weapon_Magazine", "trigger", "Weapon_Trigger", "charging", "Weapon_Bone_01", "bullet", "Weapon_Bullet", "mag_release", "Weapon_Bone_02", "boltrelease", "Weapon_Bone_03" };
        pType.AddItemBoneRemap("MyMod_SVD_Base", remap);
    }
}
```

- `ModItemRegisterCallbacks` is the vanilla class for this (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:305`), with `RegisterFireArms` at `:321` and `CustomBoneRemapping` at `:331`; vanilla calls the latter after its own remaps (`:1646`).
- `AddItemInHandsProfileIK(string pItemClass, string pAnimInstanceName, HumanItemBehaviorCfg pBehaviorCfg, string pIkPoseAnim, string pWeaponStates = "")` (`P:\scripts\3_game\dayzplayer.c:243`). The fifth argument is for weapons; other items use four with a generic instance.
- `AddItemBoneRemap(string pItemClass, array<string> pBoneRemap)` (`:252`). The pairs are, in the source's words, "bone in item's P3D first, bone in Character skeleton second".
- Register on the weapon's base class so every variant inherits and calls stay few.

The remap is why parts move. Each pair's first name is a selection of the weapon model, declared as a bone in the weapon's own `model.cfg`; the second a `Weapon_` bone. Standard parts go to `Weapon_Bolt`, `Weapon_Magazine`, `Weapon_Trigger` and `Weapon_Bullet`, others to `Weapon_Bone_01` to `06`. Without the remap the hands play while bolt, magazine and trigger stay still; a wrong name drops that part silently. A weapon inheriting a vanilla base gets its remap (`Rifle_Base` at `dayzplayercfgbase.c:1580`). Reported, not checked on `P:\`: `AddItemBoneRemap` works for weapon classes only, so a medical or other item cannot drive a `Weapon_Bone`; its anchors are `RightHand_Dummy` and, through constraints, `LeftHand_Dummy`.

An older pattern calls `GetDayZPlayerType().AddItemInHandsProfileIK(...)` in a modded `PlayerBase.Init()` guarded to run on the client; in the wrong place it does nothing, with no error. The callback is cleaner. Many stacked overrides across mods are reported to overflow the stack in `ModItemRegisterCallbacks` on heavily modded servers (not confirmed); registering on base classes keeps calls few.

## How the graph picks column and state

- Column: the group select nodes `WeaponStanceErc` (`Group "WeaponOperations"`, `Column "ErcRas"`, `P:\DZ\anims\workspaces\player\player_main\combat.agf:1150` to `:1155`) and `WeaponStancePne` (`Column "PneRas"`, `:1178` to `:1183`) both play `WeaponFireSTM`; the prone one starts on `Stance == 2` (`:1172`).
- Fire state: `FireCocked` starts on `GetCommandI(CMD_WeaponFire) == 2` (`:1120` to `:1123`).
- Commands, in the master graph: `CMD_Reload_Magazine`, `CMD_Reload_BoltAction`, `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`, `CMD_Reload_Exit`, `CMD_Reload_Clip` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:269` to `:284`), `CMD_Weapon_Jam` (`:359`) and `CMD_WeaponFire` (`:365`).

Which command or transition starts each single state is in the weapons sub-graph and not traced state by state; copy the closest vanilla weapon.

## The weapon's model.cfg

Two skeletons are in play. The weapon has its own small one, the selections the remap's first names point at; the player has the player skeleton. The `.anm` animates player bones, and `AddItemBoneRemap` is the bridge. The shape of the demo mod's SVD file, `sections[]` shortened; `gen_model_cfg.py` writes this kind of file:

```cpp
class CfgSkeletons
{
    class svd
    {
        skeletonInherit = "";
        isDiscrete = 1;
        SkeletonBones[] = { "magazine", "", "trigger", "", "bolt", "", "firemode", "", "bullet", "", "mag_release", "" };
    };
};
class CfgModels
{
    class Default;
    class svd: Default
    {
        skeletonName = "svd";
        sections[] = { "magazine", "zbytek", "bullet" };
    };
};
```

The plugin's Tools, "Generate DayZ Model Config (model.cfg)" writes a stub from the selected armature with `isDiscrete = 0`, bone and parent per bone and a model class to rename. It is meant for custom skeletons such as creatures, and skips the helper bones (`scene_root`, `entityposition`, the hand origins, hand dummies and forearm directions, in any case); those still appear as animated nodes in a `.txa`.

## The weapon's config.cpp

The weapon class carries `model`, `magazines[]`, `chamberableFrom[]`, `modes[]`, the `AnimEvents` sounds and `OpticsInfo`, and no `.anm` or `.asi`. The vanilla SVD: config class `SVD_Base: Rifle_Base` (`P:\DZ\weapons\firearms\svd\config.cpp:26`), script class `SVD_Base : RifleBoltLock_Base` (`P:\scripts\4_world\entities\firearms\rifle\svd.c:1`).

## The reloadAction key is legacy

`reloadAction` is an old `CfgWeapons` key from the Arma line that named a reload in the old gesture configs. The instance file binds clips by state name whatever it says, so leave it out, as vanilla rifles do:

- Neither `P:\DZ\weapons\firearms\ak74\config.cpp` nor `P:\DZ\weapons\firearms\svd\config.cpp` contains `reloadAction` or `shotAction`.
- It survives in two vanilla configs: `reloadAction="ReloadBow"` (`P:\DZ\data\config.cpp:4592`) and `reloadAction="ManActReloadAT"` (`:4756`).
- No weapon script reads it; the only hit under `P:\scripts` is in the key bindings menu.
- The demo SVD sets `reloadAction="ReloadSVD"`, which matches no vanilla class, and animates correctly through its instance file.
- `reloadAction`, `shotAction` and related keys are reported removed as obsolete around 1.25 to 1.26. Whether an invalid value logs more than a harmless warning is not checked.

## Mod layout

The demo mod uses one top folder per PBO:

```text
<Mod>/
  Animations/   .asi, and .txa, .anm, .anm.meta per weapon; config.cpp with CfgPatches <Mod>_Animations
  Firearms/     weapon .p3d, its model config, textures; config.cpp with CfgPatches <Mod>_Firearms
  Scripts/      config.cpp with CfgPatches <Mod>_Scripts and CfgMods; the .c files
  Workbench/    the Workbench project files
```

Here a mod lives under `workspace\<ModName>\`, and `/dayz-new-mod` or `/dayz-add-scaffold` create the layout with its prefix file. `requiredAddons[]` per PBO:

- Animations: `DZ_Anims_Anm_Player` (`P:\DZ\anims\anm\player\config.cpp:3`), `DZ_Anims_Cfg` (`P:\DZ\anims\cfg\config.cpp:3`), `DZ_Data`, `DZ_Scripts`, so vanilla clips and configs load first.
- Firearms: `DZ_Weapons_Firearms`, plus magazines, muzzles, optics or launchers as used.
- Scripts: `DZ_Scripts`; its config also holds `CfgMods` with a `worldScriptModule` pointing at the `4_World` folder.

`inputs.xml` is optional; the demo ships an empty one because reload, fire and chamber reuse vanilla inputs, and only a new bindable action such as an inspect would need one (untested). `stringtable.csv` is optional for localized names. The Workbench project file (`dayz.gproj`) declares the work drive as its file system, the skeleton definitions, image sets, widget styles and the five script modules; build and launch from Workbench so `.txa` files compile.
