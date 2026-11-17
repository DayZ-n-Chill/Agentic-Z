# DayZ 1.30: what changed on the entity side of firearms

The new firearm scripts and where their models are, the pistol animation state getters, magazine detach on open bolt guns, the state machine repair on magazine removal, the new recoil classes, the explosion effect API, and the MP18 drum magazine. Animation motion stays with the dayz-animation-pipeline skill.

Every block marked `[EXACT]` is copied from the cited file on `P:\`. `[VERIFIED-vanilla]` means read in the cited vanilla file; `[DESIGN]` is a recommendation; `[UNVERIFIED]` is not confirmed. Statements about 1.29, and about the config classes of game build 1.30.164200, could not be read on `P:\` and are marked that way.

## W-STAGING1: scripts without a config class or a model

Until 1.29, any vanilla firearm with a script under `4_World\Entities\Firearms\` also shipped a model and a `CfgWeapons` class in the matching weapons PBO (the 1.29 data is not on `P:\`, so not checked there).

Since 1.30, four new firearm scripts and a bayonet compile, register their hand animations, and in two cases have their own bone remaps, while the vanilla data on `P:\` has no model and no `CfgWeapons` or `CfgMagazines` class for them. For a comparison, use a weapon that ships in the data you have: the SCAR-H for a rifle shaped like the SCAR-L, the P1 or Glock for a pistol, the CZ527 or Mosin for a bolt action, the PM73 RAK for an open bolt SMG (`PM73Rak_Base extends OpenBolt_Base`, `P:\scripts\4_world\entities\firearms\smg\pm73rak.c:5`; the CZ61 is closed bolt, `CZ61_Base : RifleBoltLock_Base`, `P:\scripts\4_world\entities\firearms\smg\cz61.c:4`).

`[VERIFIED-vanilla]` on `P:\`:

| Script class | Script file | Script parent | Config class and model on `P:\` |
|---|---|---|---|
| `SCARL_Base` | `P:\scripts\4_world\entities\firearms\automaticrifle\scarl.c:1` | `SCARH_Base` (not `RifleBoltFree_Base`) | None. `P:\DZ\weapons\firearms\` has no SCAR-L folder. The shipped relative is `P:\DZ\weapons\firearms\scarh\scarh.p3d` with `class SCARH_Base: Rifle_Base` at `P:\DZ\weapons\firearms\scarh\config.cpp:26`. |
| `Luger_Base` | `P:\scripts\4_world\entities\firearms\pistol\luger.c:1` | `Pistol_Base` | None. `P:\DZ\weapons\pistols\` has no Luger folder. |
| `LeeEnfield_Base` | `P:\scripts\4_world\entities\firearms\rifle\leeenfield.c:1` | `BoltActionRifle_ExternalMagazine_Base` | None. No Lee-Enfield folder under `P:\DZ\weapons\firearms\`. |
| `MP18_Base` | `P:\scripts\4_world\entities\firearms\smg\mp18.c:1` | `OpenBolt_Base` | None. No MP18 folder under `P:\DZ\weapons\firearms\`. |
| `P1907_Bayonet` | `P:\scripts\4_world\entities\itembase\inventory_base\p1907_bayonet.c:1` | `Inventory_Base` | None. Script only; no config class with that name under `P:\DZ\weapons\`. |

Magazine script classes exist too: `Mag_Luger_8Rnd`, `Mag_LeeEnfield_10Rnd` and `Mag_MP18_Drum32Rnd` (`P:\scripts\4_world\entities\itembase\magazine\magazines.c:65-67`). `P:\DZ\weapons\attachments\magazine\config.cpp` has no `CfgMagazines` class for any of them. Do not put these class names in `types.xml` or a trader list for a server whose data lacks them.

**Game build 1.30.164200**: the four weapons, their magazines and the bayonet ship in `nasdara\addons\weapons_nasdara.pbo` (prefix `DZ\weapons_takistan`), not in `weapons_firearms` or `weapons_pistols`, each weapon with its `.p3d` and a `config.bin` in its own folder. The prefix and the file list were read in the header of that PBO in an installed DayZ Server (Steam build 26220720); the PBO is not unpacked on `P:\`. The classes and line numbers below are those of the derapified configs and are not yet checked on `P:\` (paths relative to `DZ\weapons_takistan\`):

| Classes (scope 2) | Config parent | Config | Model |
|---|---|---|---|
| `SCARL`, `SCARL_Black: SCARL` | `SCARL_Base: Rifle_Base` (scope 0); its script parent is `SCARH_Base` | `firearms\SCARL\config.cpp:40`, `:202`, `:222` | `firearms\SCARL\ScarL.p3d` |
| `LeeEnfield` | `LeeEnfield_Base: BoltActionRifle_ExternalMagazine_Base` (scope 0) | `firearms\leeEnfield\config.cpp:41`, `:154` | `firearms\leeEnfield\leeEnfield.p3d` |
| `MP18` | `MP18_Base: Rifle_Base` (scope 0); its script parent is `OpenBolt_Base` | `firearms\mp18\config.cpp:40`, `:161` | `firearms\mp18\mp18.p3d` |
| `Luger` | `Luger_Base: Pistol_Base` (scope 0) | `pistols\Luger\config.cpp:40`, `:134` | `pistols\Luger\Luger.p3d` |
| `Mag_Luger_8Rnd` (8 rounds), `Mag_MP18_Drum32Rnd` (32), `Mag_LeeEnfield_10Rnd` (10) | `Magazine_Base`, in `CfgMagazines` | `attachments\magazine\config.cpp:38`, `:130`, `:234` | `attachments\magazine\magazine_*.p3d` |
| `P1907_Bayonet` | `Inventory_Base`, in `cfgVehicles`; `inventorySlot[]` holds `weaponBayonetLeeEnfield` and `Knife` | `attachments\muzzle\config.cpp:36` | `attachments\muzzle\bayonet_p1907.p3d` |

In that build `Luger_Base` and `MP18_Base` take the same two magazines, the Luger box and the MP18 drum (`pistols\Luger\config.cpp:55`, `firearms\mp18\config.cpp:54`), and `LeeEnfield` takes the bayonet (`attachments[]`, `firearms\leeEnfield\config.cpp:160`). For a comparison on that build, open the model you inherit from that PBO.

Loot: the vanilla `types.xml` files list all nine class names. On `P:\`, Chernarus and Sakhal give every one a nominal of 0 (`SCARL` at `P:\DZ\worlds\chernarusplus\ce\db\types.xml:19815` and `P:\DZ\worlds\sakhal\ce\db\types.xml:19934`), and Livonia gives every one 0 except `SCARL_Black`, which has 4 (`P:\DZ\worlds\enoch\ce\db\types.xml:19390`). The Nasdara mission is not on `P:\`; in an installed DayZ Server (Steam build 26220720), `mpmissions\dayzOffline.nasdara\db\types.xml` gives every one a nominal above 0 except `SCARL_Black` (`Luger` 55, `SCARL` 4). None of them has been spawned in game yet.

The hand animation files are in the data on `P:\` (the entity side only records the registration; the motion is animation work). All four lines are in `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c`:

- `Luger_Base`: `:395`, `player_main_luger08.asi` with `lugerP08.anm` and `w_LugerP08_states.anm`.
- `MP18_Base`: `:432`, `player_main_mp18.asi` with `mp18_IK.anm` and `MP18_states.anm`.
- `SCARL_Base`: `:445`, the same `.asi`, IK pose and weapon states as `SCARH_Base` at `:444` (`player_main_SCARH.asi`, `SCAR_ik.anm`, `w_SCAR_states.anm`).
- `LeeEnfield_Base`: `:446`, `player_main_leeEnfield.asi` with `enfield.anm` and `w_enfield_states.anm`.

```c
// [EXACT] P:\scripts\4_world\entities\firearms\automaticrifle\scarl.c:1
class SCARL_Base : SCARH_Base
{
    
    override RecoilBase SpawnRecoilObject()
    {
        return new SCARLRecoil(this);
    }
	
	override void OnDebugSpawn()
    {
        GameInventory inventory = GetInventory();

        inventory.CreateInInventory( "SCAR_StockBttstck" );
        inventory.CreateInInventory( "M4_T3NRDSOptic" );
        inventory.CreateInInventory( "Battery9V" );

        SpawnAttachedMagazine("Mag_STANAG_30Rnd");
    }
};
```

`SCARH_Base` itself extends `RifleBoltLock_Base` (`P:\scripts\4_world\entities\firearms\automaticrifle\scarh.c:1`), and its config class is `SCARH_Base: Rifle_Base` (`P:\DZ\weapons\firearms\scarh\config.cpp:26`). A 5.56 mod shaped like the SCAR-L that wants this family inherits the SCAR-H config and the `RifleBoltLock_Base` script, then overrides ammo, magazines and recoil.

`P1907_Bayonet` is both an attachment and a melee tool: `CanPutAsAttachment` refuses the slot when `suppressorImpro` or `weaponMuzzle` is reserved or occupied (`P:\scripts\4_world\entities\itembase\inventory_base\p1907_bayonet.c:13-26`), and `OnWasAttached` and `OnWasDetached` call `parent.SetBayonetAttached(...)` when `parent.IsWeapon()` (`:28-46`). `[DESIGN]` Treat it as a pattern for a bayonet slot.

## Pistol state machine: virtual animation state getters

Until 1.29, `Pistol_Base.InitStateMachine()` passed `PistolAnimState` constants into each stable state constructor (1.29 `Pistol_Base.c:203-212`; the 1.29 scripts are not on `P:\`, so the 1.29 lines in this file are not checked there).

Since 1.30 the same constructors take `GetDischargedPistolAnimState()`, `GetChargedPistolAnimState()`, `GetOpenPistolAnimState()` and `GetJammedPistolAnimState()`. Override those on the pistol class. The stable state classes still return `PistolStableStateID` values from `GetCurrentStateID()`; they were not rewritten.

`enum PistolAnimState` (`P:\scripts\4_world\entities\firearms\pistol_base.c:2-8`): `DEFAULT` is 0, `OPENED_DISCHARGED` 1, `CLOSED_CHARGED` 2, `JAMMED` 3. The base getters (`:611-629`) return `DEFAULT` for discharged, `CLOSED_CHARGED` for charged, `OPENED_DISCHARGED` for open and `JAMMED` for jammed.

```c
// [EXACT] P:\scripts\4_world\entities\firearms\pistol_base.c:199
		// setup state machine
		// basic weapon states
		// open-closed | discharged-charged | nobullet-bullet | nomag-mag
		// regexp: [OC][CDJ][01][01]
		CD00 = new Pistol_CLO_DIS_BU0_MA0(this, NULL, GetDischargedPistolAnimState());
		CC00 = new Pistol_CLO_CHG_BU0_MA0(this, NULL, GetChargedPistolAnimState());
		CC10 = new Pistol_CLO_CHG_BU1_MA0(this, NULL, GetChargedPistolAnimState());
		CJF0 = new Pistol_CLO_JAM_BU1_MA0(this, NULL, GetJammedPistolAnimState());
		OD00 = new Pistol_OPE_DIS_BU0_MA0(this, NULL, GetOpenPistolAnimState());
		CD01 = new Pistol_CLO_DIS_BU0_MA1(this, NULL, GetDischargedPistolAnimState());
		CC01 = new Pistol_CLO_CHG_BU0_MA1(this, NULL, GetChargedPistolAnimState());
		CC11 = new Pistol_CLO_CHG_BU1_MA1(this, NULL, GetChargedPistolAnimState());
		CJF1 = new Pistol_CLO_JAM_BU1_MA1(this, NULL, GetJammedPistolAnimState());
		OD01 = new Pistol_OPE_DIS_BU0_MA1(this, NULL, GetOpenPistolAnimState());
```

The Luger (toggle lock) overrides three getters, not the discharged one, and uses the enum names, not bare numbers:

```c
// [EXACT] P:\scripts\4_world\entities\firearms\pistol\luger.c:8
	override int GetChargedPistolAnimState()
	{
		return PistolAnimState.DEFAULT;
	}

	override int GetOpenPistolAnimState()
	{
		return PistolAnimState.OPENED_DISCHARGED;
	}
	
	override int GetJammedPistolAnimState()
	{
		return PistolAnimState.CLOSED_CHARGED;
	}
```

`[DESIGN]` A mod pistol whose slide does not behave like a Colt's maps its own `PistolAnimState` values (or a parallel enum its weapon state `.anm` understands) through these getters. Do not copy the `Pistol_CLO_*` state classes unless the graph of the state machine itself has to change.

## Open bolt guns can detach the magazine

Until 1.29, `OpenBolt_Base.SetActions()` only removed `FirearmActionLoadBullet` and `FirearmActionLoadBulletQuick` (1.29 `OpenBolt_Base.c:382-388`; not on `P:\`). Since 1.30 it also adds `FirearmActionDetachMagazine`:

```c
// [EXACT] P:\scripts\4_world\entities\firearms\openbolt_base.c:382
	override void SetActions()
	{
		super.SetActions();
		
		RemoveAction(FirearmActionLoadBullet);
		RemoveAction(FirearmActionLoadBulletQuick); // Easy reload
		AddAction(FirearmActionDetachMagazine);
	}
```

`OpenBolt_Base extends Rifle_Base` (`P:\scripts\4_world\entities\firearms\openbolt_base.c:122`), and the MP18 inherits this. Do not invent a workaround tied to the bolt phase to allow magazine detach on an open bolt SMG; the detach action is registered on the base.

`FirearmActionDetachMagazine` is at `P:\scripts\4_world\classes\useractionscomponent\actions\weapons\firearmactiondetachmagazine.c:151` and extends `ActionSequentialBase`. The old class, `FirearmActionDetachMagazine_Old`, is marked `[Obsolete("1.30: Use class FirearmActionDetachMagazine instead")]` at `:13`. The new action returns `true` from `CanBePerformedFromInventory()` (`:262-265`).

Quick reload is stricter: the `ActionCondition` of `FirearmActionAttachMagazineQuick` (class at `P:\scripts\4_world\classes\useractionscomponent\actions\weapons\firearmactionattachmagazine.c:225`, condition at `:231`) requires `weapon.TestAttachMagazine(weapon.GetCurrentMuzzle(), mag, false, true)` (`:256-257`). The `ActionCondition` of the plain `FirearmActionAttachMagazine` (`:26-35`) checks `WeaponManager.CanAttachMagazine` or `CanSwapMagazine` and does not call `TestAttachMagazine`. A 1.29 override of `TestAttachMagazine` that gets this case wrong blocks quick reload, not every magazine attach.

## `Weapon_Base`: removing a magazine validates the state machine; `EEFired` effects are client only

```c
// [EXACT] P:\scripts\4_world\entities\firearms\weapon_base.c:1115
	override void EEItemDetached(EntityAI item, string slot_name)
	{
		super.EEItemDetached(item, slot_name);

		GetPropertyModifierObject().UpdateModifiers();

		if(item.IsMagazine()) {ValidateAndRepair();}
	}
```

Until 1.29, `EEItemDetached` stopped after `UpdateModifiers()` (1.29 `Weapon_Base.c:1123-1128`; not on `P:\`).

`EEFired` is an `override` and wraps the muzzle flash and overheating effects in `if ( !g_Game.IsHeadlessOrDedicatedServer() )` (`P:\scripts\4_world\entities\firearms\weapon_base.c:341-346`).

Where a swapped magazine lands when it does not fit the inventory: 1.29 passed an uninitialized `float dir[4]` into `SetGroundEx` (1.29 `WeaponManager.c:1362-1365`; not on `P:\`). 1.30 fills it from the player's yaw:

```c
// [EXACT] P:\scripts\4_world\classes\weapons\weaponmanager.c:1364
					vector rotationMatrix[3];
					float dir[4];
					Math3D.YawPitchRollMatrix(m_player.GetOrientation(), rotationMatrix);
					Math3D.MatrixToQuat(rotationMatrix, dir);
					new_il.SetGroundEx( old_mag,  m_player.GetPosition(), dir);
```

Taking a cartridge in the state machine helper used `LocalAcquireCartridge` until 1.29 and uses `LocalAcquireCartridgeEx` since 1.30:

```c
// [EXACT] P:\scripts\4_world\entities\firearms\fsm\weapon_utils.c:7
		float damage;
		string type;
		if (mag && mag.LocalAcquireCartridgeEx(damage, type))
```

## Recoil classes (script `RecoilBase`, not the config `recoil` string)

All four new recoil classes extend `RecoilBase` and fill `m_HandsCurvePoints` plus the mouse and camera offsets; none of them uses a `m_HandsOffsetRelativePoseModel` string. They are in `P:\scripts\4_world\classes\recoilbase\recoils\`.

| Class | Hands curve height (points 1 and 2) | `m_MouseOffsetDistance` | `m_CamOffsetDistance` | Notes |
|---|---|---|---|---|
| `SCARLRecoil` | 1.3 and 1.6 | 1.5 | 0.01 | Its values are identical to `scarhrecoil.c` on `P:\`. |
| `LugerRecoil` | 3 and 4 | 0.95 | 0.02 | A sharp vertical hands curve. |
| `LeeEnfieldRecoil` | 1.75 and 2 | 1.6 | 0.02 | Short relative times (`m_HandsOffsetRelativeTime = 0.125`). |
| `MP18Recoil` | 0.9 and 0.85 | 0.9 | 0.005 | The lowest camera kick of the four. |

```c
// [EXACT] P:\scripts\4_world\classes\recoilbase\recoils\leeenfieldrecoil.c:18
		m_HandsOffsetRelativeTime = 0.125;
		
		m_MouseOffsetRangeMin = 80;//in degrees min
		m_MouseOffsetRangeMax = 100;//in degrees max
		m_MouseOffsetDistance = 1.6;//how far should the mouse travel
		m_MouseOffsetRelativeTime = 0.0625;//[0..1] a time it takes to move the mouse the required distance relative to the reload time of the weapon(firing mode)
	
		m_CamOffsetDistance = 0.02;
		m_CamOffsetRelativeTime = 0.125;
```

The weapons create them in `SpawnRecoilObject()` (`scarl.c:4-7`, `luger.c:3-6`, `leeenfield.c:3-6`, `mp18.c:7-10`). The config string `recoil="recoil_fal"` on `SCARH_Base` (`P:\DZ\weapons\firearms\scarh\config.cpp:94`) is a different thing from this script object. It is sometimes described as a `CfgRecoils` entry; on `P:\` the engine config does have a `class CfgRecoils` (`P:\bin\config.cpp:218`), but it holds only `empty[]` and `impulse[]`, and no `recoil_fal` entry exists under `P:\bin`, `P:\DZ` or `P:\scripts`. Tune recoil in the script class (`skills/_shared/weapons/recoil-fire-modes.md`).

## Explosion effects: the API changed and old calls no longer compile

Until 1.29, `AmmoTypesAPI.GetExplosionParticleID(string ammoName, string surfaceName)` returned an `int` (1.29 `AmmoTypes.c:57`, called from the explosion code in `DayZGame.c`; not on `P:\`).

Since 1.30 that method is gone; no file under `P:\scripts` contains `GetExplosionParticleID`. `ExplosiveEffectData` and `GetExplosiveEffectData(ammoName, surfaceName)` return the particle and an optional sound set. The signature is two strings in and an object out, not `(ammoType, outData)`.

```c
// [EXACT] P:\scripts\3_game\global\ammotypes.c:1
class ExplosiveEffectData
{
	int m_ParticleID;
	string m_SoundSetName;
	
	void ExplosiveEffectData(int particleID, string soundSetName = "")
	{
		m_ParticleID = particleID;
		m_SoundSetName = soundSetName;
	}
}
```

```c
// [EXACT] P:\scripts\3_game\global\ammotypes.c:90
	static ExplosiveEffectData GetExplosiveEffectData(string ammoName, string surfaceName)
	{
		ExplosiveEffectData result;
		
		#ifdef NO_GUI
		return result;
		#endif
```

The vanilla caller gets `surfaceType` from `SurfaceGetType3D` and then asks for the effect:

```c
// [EXACT] P:\scripts\3_game\ammoeffects.c:49
		string surfaceType;
		g_Game.SurfaceGetType3D(pos[0], pos[1], pos[2], surfaceType);
		ExplosiveEffectData explosiveEffectData = AmmoTypesAPI.GetExplosiveEffectData(ammoType, surfaceType);
		//int particleID = GetAmmoParticleID(ammoType);
		
		if (ParticleList.IsValidId(explosiveEffectData.m_ParticleID))
		{
			return ParticleManager.GetInstance().PlayInWorld(explosiveEffectData.m_ParticleID, pos) != null;
		}
```

The explosion code in `P:\scripts\3_game\dayzgame.c:3634-3638` also plays `explosiveEffectData.m_SoundSetName` through `SetStartSoundParams`. `Init()` registers `Hit_Desert_Sand` and `Hit_Sand` (and snow and ice) per ammo; the sand entries of the RGD5 and M67 grenades pass `"ExplosionDustEffect_SoundSet"` (`P:\scripts\3_game\global\ammotypes.c:66-72`).

`MagazineTypeToAmmoType` still exists. It moved from `AmmoTypes.c:14` in 1.29 (not on `P:\`) to `P:\scripts\3_game\global\ammotypes.c:26`, because `ExplosiveEffectData` was added above it. Vanilla calls it at `P:\scripts\4_world\entities\firearms\weapon_base.c:840` (1.29: `:848`, not on `P:\`).

`ExplosivesBase` (`P:\scripts\4_world\entities\explosivesbase.c`): `[Obsolete("1.30: Handled in AmmoTypes instead")]` marks `SetParticleExplosion(int particle)` (`:306-310`), both `AddExplosionEffectForSurface` overloads (`:387`, `:433`), `m_TypeToSurfaceParticleIDMap` (`:40-41`) and `InitSpecificsExplosionEffectForSurface` (`:380-384`). Put `particle = "..."` on the `CfgAmmo` class and `ammoType` on the explosive's `CfgVehicles` class; do not keep a script side map from surface to particle.

## The MP18 drum magazine

`Mag_MP18_Drum32Rnd` is not an empty class. It drives the animation source `drum`, stops the animation at 12 rounds (`m_AmmoOffset = 12`), plays `wpn_mp18_drum_mag_SoundSet` at the memory point `drum_sound`, and saves `m_LastAnimPhase`, which it reads back from save version 144 on (`P:\scripts\4_world\entities\itembase\magazine\magazines.c:67-121`). The data on `P:\` has no `CfgMagazines` entry for it (W-STAGING1). In build 1.30.164200 its `CfgMagazines` class is at `attachments\magazine\config.cpp:130` of the derapified `weapons_nasdara.pbo`, with 32 rounds; not yet checked on `P:\`.

## The changelog names script symbols that do not exist

The official 1.30 modding changelog announces `enum SoundHitType` and `SurfaceInfo.GetSoundHitType()`. Neither string appears anywhere under `P:\scripts`. `P:\scripts\3_game\surfaceinfo.c` adds proto natives for vehicle and dust particles, not a hit type. A weapon mod must not call `GetSoundHitType()` in Enforce Script on this data; it will not compile. Surface and impact particle work belongs with the surface material work, not here.

## Outside this skill

Other 1.30 changes, listed so they are not looked for here:

- `GunCase`, `GunCaseKeys` and their colour recipes: container work (`dayz-config-specialist`, with `skills/_shared/container-base.md`).
- Police baton health changed from 18 to 13 and from 40 to 30 (not yet checked on `P:\`), and the `hitBricks` and `hitMudDry` melee sound arrays: melee work.
- Registration of the `Hit_Mud_Brick` and `Hit_Desert_Sand` surfaces: surface work.
