# Research map: weapons specialist

Private research map. Anchors point into vanilla data on `P:\`. Items marked **knowledge** are not verifiable from vanilla files on `P:\`.

| # | Topic | What the specialist needs to know | Verify at |
|---|---|---|---|
| 1 | Class hierarchy | `Weapon` then `Weapon_Base` then `Rifle_Base`/`Pistol_Base` and mechanism bases (bolt free, bolt lock, inner magazine, double barrel). | `P:\scripts\4_world\entities\core\inherited\weapon.c:4`; `P:\scripts\4_world\entities\firearms\weapon_base.c:38`; `...\rifle_base.c:10`; `...\pistol_base.c:149`; `...\rifleboltfree_base.c:92` |
| 2 | Picking the right mechanism base | New guns inherit the base that matches their action; this decides the FSM. Examples: AKM, M4A1, SKS, MP-133, IZH-18, FNX45, Magnum, double barrel. | `P:\scripts\4_world\entities\firearms\automaticrifle\akm.c:1`; `...\m4a1.c:1`; `...\sks.c:69`; `...\shotgun\mp133.c:64`; `...\rifle\izh18.c:5`; `...\pistol\fnx45.c:1`; `...\pistol\magnum.c:50`; `...\doublebarrel_base.c:119` |
| 3 | Weapon FSM | `WeaponFSM` hierarchical state machine; states, events, guards. | `P:\scripts\4_world\entities\firearms\weaponfsm.c:4`; `...\fsm\states\weaponstatebase.c:10`; `...\fsm\states\weaponstablestate.c:26` |
| 4 | `InitStateMachine` | Each mechanism base builds its states and transitions here; custom mechanisms override it. | `P:\scripts\4_world\entities\firearms\boltactionrifleexternalmagazine_base.c:123`; `...\doublebarrel_base.c:130`; `...\openbolt_base.c:136` |
| 5 | FSM states | Chambering, charging, fire, eject. | `P:\scripts\4_world\entities\firearms\fsm\states\weaponchambering.c:21`; `...\weaponcharging.c:4`, `:90`; `...\weaponfire.c:44`, `:112`, `:135` |
| 6 | FSM events | Trigger, trigger-to-jam, auto start, and processing via `ProcessWeaponEvent`. | `P:\scripts\4_world\entities\firearms\fsm\events.c:80`, `:86`, `:92`; usage `P:\scripts\4_world\classes\emotemanager.c:753` |
| 7 | Weapon actions and animation commands | `WeaponActions`, reload types, unjamming types; `GetWeaponSpecificCommand` maps to animation. | `P:\scripts\3_game\human.c:842`, `:858`, `:944`; `P:\scripts\4_world\entities\firearms\weapon_base.c:1257`; override example `...\automaticrifle\aug.c:18` |
| 8 | Weapon manager | Client/server reload, attach magazine, chamber, jam sync. | `P:\scripts\4_world\classes\weapons\weaponmanager.c:1`, `:222`, `:923` |
| 9 | Bullet visibility | `ShowBullet`/`HideBullet` for chambered round proxies. | `P:\scripts\4_world\entities\firearms\weapon_base.c:379`, `:389` |
| 10 | Firing hook | `EEFired` for script-side effects on shot. | `P:\scripts\4_world\entities\firearms\weapon_base.c:341`; `P:\scripts\3_game\entities\entityai.c:4927` |
| 11 | Jamming | `GetChanceToJam`, synced jam chance, unjam action. | `P:\scripts\4_world\classes\weapons\weaponmanager.c:923`-`937`; `P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:366` |
| 12 | Recoil | `RecoilBase` subclasses define curves; `SpawnRecoilObject` returns them. | `P:\scripts\4_world\classes\recoilbase\recoilbase.c:1`; `...\recoils\akmrecoil.c:1`; `P:\scripts\4_world\entities\firearms\weapon_base.c:1252` |
| 13 | Aiming and sway | `DayZPlayerImplementAiming` handles sway and recoil application. | `P:\scripts\4_world\entities\dayzplayerimplementaiming.c:32`, `:86` |
| 14 | Ironsights and optics cameras | Camera classes for ADS; `CanEnterIronsights`. | `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameraironsights.c:3`, `:362`; `P:\scripts\4_world\entities\dayzplayerimplement.c:1129` |
| 15 | Optics items | `ItemOptics`, zeroing step, config `PSO1Optic`. | `P:\scripts\4_world\entities\core\inherited\itemoptics.c:1`, `:121`; `P:\DZ\weapons\attachments\optics\config.cpp:2068` |
| 16 | Suppressors | `ItemSuppressor` class and config `AK_Suppressor`. | `P:\scripts\4_world\entities\core\inherited\inventoryitem.c:2`; `P:\DZ\weapons\attachments\muzzle\config.cpp:1059` |
| 17 | Magazines | Script `Magazine`; config `Mag_AKM_30Rnd`. | `P:\scripts\4_world\entities\itembase\magazine\magazine.c:38`; `P:\DZ\weapons\attachments\magazine\config.cpp:3436` |
| 18 | Ammo piles and rounds | `Ammunition_Base` script; `CfgMagazines` ammo items such as `Ammo_762x39`; `CanChamberBullet`. | `P:\scripts\4_world\entities\itembase\magazine\ammunitionpiles.c:2`; `P:\DZ\weapons\ammunition\config.cpp:14`, `:640`; `P:\scripts\4_world\entities\firearms\doublebarrel_base.c:311` |
| 19 | Projectiles | `CfgAmmo` bullets: speed, damage applied. | `P:\DZ\weapons\projectiles\config.cpp:11`, `:4461` (`Bullet_762x39`), `:1957` (`typicalSpeed`), `:1965` (`DamageApplied`) |
| 20 | Weapon config core | `chamberableFrom[]`, `magazines[]`, `ironsightsExcludingOptics[]`, `barrelArmor`, `PPDOFProperties`, `recoilModifier`. | `P:\DZ\weapons\firearms\akm\config.cpp:26`, `:33`, `:34`, `:42`, `:46`, `:51`, `:66` |
| 21 | Fire modes and shot sounds | `SemiAuto`/`FullAuto` mode classes with `soundSetShot[]`. | `P:\DZ\weapons\firearms\akm\config.cpp:87`, `:89` |
| 22 | Noise of shooting | `NoiseShoot` drives AI hearing. | `P:\DZ\weapons\firearms\akm\config.cpp:82` |
| 23 | Attachments slots | `attachments[]` on weapon config. | `P:\DZ\weapons\firearms\akm\config.cpp:197` |
| 24 | Muzzle particles | `Particles` with `OnFire`, `OnOverheating`; loaded by `WeaponParticlesBase`. | `P:\DZ\weapons\firearms\akm\config.cpp:218`, `:220`, `:240`; `P:\scripts\4_world\entities\weaponparticles.c:7`; `P:\scripts\4_world\entities\itembase.c:313` |
| 25 | Weapon damage | `DamageSystem` in weapon config. | `P:\DZ\weapons\firearms\akm\config.cpp:294` |
| 26 | Firearm user actions | Load bullet, multi-bullet, attach magazine, unjam. | `P:\scripts\4_world\classes\useractionscomponent\actions\weapons\firearmactionloadbullet.c:1`; `...\firearmactionloadmultibullet.c:1`; `...\firearmactionattachmagazine.c:11` |
| 27 | Melee | `DayZPlayerImplementMeleeCombat`, `MeleeTargeting`, native `ProcessMeleeHit`. | `P:\scripts\4_world\entities\dayzplayerimplementmeleecombat.c:19`; `P:\scripts\4_world\classes\meleetargeting.c:72`; `P:\scripts\3_game\dayzplayer.c:1291` |
| 28 | Hand animation registration | Weapons need an item-in-hands profile in `DayZPlayerTypeRegisterItems`. See animation map. | `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:334` |
| 29 | Persistence | Muzzle, mode, jam, FSM state saved. | `P:\scripts\4_world\entities\firearms\weapon_base.c:481`, `:616` |
| 30 | Weapon animations | Weapon `.anm`/`.asi` live under weapon folders and `P:\DZ\anims`. | `P:\DZ\anims\anm\player`; `P:\DZ\weapons` |
| 31 | Model requirements | Memory points (`usti hlavne`, `konec hlavne`, eye), `magazine`/`bullet` proxies, LODs. **knowledge**; inspect a vanilla p3d with `/dayz-p3d-audit`. | `P:\DZ\weapons\firearms\akm` |
