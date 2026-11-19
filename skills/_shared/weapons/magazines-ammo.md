# Magazines, ammo and bullets

How a magazine, a pile of loose rounds and the fired bullet are three different classes, and how they name each other. Get one link wrong and the gun will not load or will fire the wrong round.

## Three classes per cartridge

| What | Config root | Vanilla example | Script class |
|---|---|---|---|
| Detachable magazine | `CfgMagazines`, parent `Magazine_Base` | `Mag_CZ527_5rnd` (`P:\DZ\weapons\attachments\magazine\config.cpp:4044`) | `Mag_CZ527_5rnd: MagazineStorage` (`P:\scripts\4_world\entities\itembase\magazine\magazines.c:27`) |
| Ammo pile (loose rounds in inventory) | `CfgMagazines`, parent `Ammunition_Base` | `Ammo_762x39` (`P:\DZ\weapons\ammunition\config.cpp:640`) | `Ammo_762x39: Ammunition_Base` (`P:\scripts\4_world\entities\itembase\magazine\ammunitionpiles.c:74`) |
| Bullet (the projectile in flight) | `CfgAmmo`, parent `Bullet_Base` | `Bullet_762x39` (`P:\DZ\weapons\projectiles\config.cpp:4461`) | none |

Ammo piles live in `CfgMagazines`, not `CfgAmmo`. The `Ammunition_Base` config class inherits `Magazine_Base` (`ammunition\config.cpp:17`).

## How they point at each other

- Weapon `magazines[]` names magazine classes; weapon `chamberableFrom[]` names ammo pile classes (`P:\DZ\weapons\firearms\cz527\config.cpp:55` and `:60`).
- Magazine `ammo` names the bullet it is filled with by default, `ammoItems[]` names the ammo piles that can load it, and `count` is its capacity (`magazine\config.cpp:4053` to `:4059`: `count=5`, `ammo="Bullet_762x39"`, `ammoItems[]={"Ammo_762x39","Ammo_762x39Tracer"}`).
- Ammo pile `ammo` names its bullet and `count` is the most rounds in one stack (`ammunition\config.cpp:648` and `:649`).
- Bullet `spawnPileType` names the pile it turns back into (`projectiles\config.cpp:4466`). Emptying a magazine creates that pile (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionemptymagazine.c:91`), so a wrong value spawns the wrong rounds.
- `AmmoTypesAPI.GetAmmoType` reads the default bullet of a magazine type (`P:\scripts\3_game\global\ammotypes.c:23`).
- `AmmoTypesAPI.MagazineTypeToAmmoType(string magazineType, out string ammoType)` turns a magazine or pile type into the bullet type the damage system uses, and passes a name through when it already is a bullet type (`P:\scripts\3_game\global\ammotypes.c:26`). Vanilla calls it when it fills a weapon (`P:\scripts\4_world\entities\firearms\weapon_base.c:840`). Use it; do not write your own lookup of `CfgMagazines <type> ammo`.

## Bullet registration

Every vanilla bullet also has an entry in `cfgAmmoTypes` in `P:\DZ\data\config.cpp` (from `:3782`), such as `AType_Bullet_762x39` with `name="Bullet_762x39"` at `:3872`. `AmmoTypesAPI.Exists` checks that registry (`ammotypes.c:21`). Give a new bullet class a matching `cfgAmmoTypes` entry the same way vanilla does.

## Magazine keys

From `Magazine_Base` (`magazine\config.cpp:17`) and `Mag_CZ527_5rnd` (`:4044`):

- `inventorySlot[]={"magazine","magazine2","magazine3"}` (`:22`). The weapon mode's `magazineSlot="magazine"` (`cz527\config.cpp:108`) is the slot it fits into on the gun.
- `recoilModifier[]={0.94999999,0.94999999,0.94999999}` (`:37`): a fitted magazine lowers recoil a little, like any attachment.
- `selectionFireAnim="zasleh"` (`:52`).
- `tracersEvery` (`:4060`), `weight` and `weightPerQuantityUnit` (`:4050`, `:4051`), `itemSize[]` (`:4052`).
- `class AnimEvents` with the fill and empty sound sets (`:4114`).

A magazine that players fill by hand needs the `MagazineStorage` script class, which adds the load and empty actions (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:463`). Inheriting a vanilla magazine in config gives the mod class that script class with no code.

The same keys on a 30 round magazine, `Mag_AKM_30Rnd` (`P:\DZ\weapons\attachments\magazine\config.cpp:3436`): `count=30` (`:3457`), `ammo="Bullet_762x39"` (`:3458`), `ammoItems[]` (`:3459`) and `tracersEvery=0` (`:3464`).

A magazine script class can do more than store rounds. `Mag_MP18_Drum32Rnd` (`P:\scripts\4_world\entities\itembase\magazine\magazines.c:67`) overrides `UpdateAnimation` to turn the animation source `drum` as rounds leave, stops at 12 rounds (`m_AmmoOffset`), plays `wpn_mp18_drum_mag_SoundSet` at the memory point `drum_sound` on clients, and saves `m_LastAnimPhase`, reading it back only from save version 144 on (`:79` to `:121`). Its config class declares the source as `class drum` with `source="user"` under `AnimationSources` (`P:\DZ\weapons_takistan\attachments\magazine\config.cpp:158`, `:240` to `:248`); a mod drum that copies the script needs the same source in its own config and model.

## Bullet keys

From `Bullet_762x39` (`projectiles\config.cpp:4461` to `:4513`):

- `initSpeed=640` and `typicalSpeed=740` (`:4471`, `:4472`), `airFriction` (`:4473`), `caliber` (`:4474`), `weight` (`:4478`).
- `damageBarrel` and `damageBarrelDestroyed` (`:4476`, `:4477`).
- `casing` and `round` name `CfgVehicles` classes in the same file for the ejected case and the visible round (`:4464`, `:4465`; `FxCartridge_762x39` at `:7042`, `FxRound_762x39` at `:7116`).
- `class DamageApplied` with `Health`, `Blood` and `Shock` damage (`:4482`).
- `class NoiseHit` (`:4508`).
- A tracer variant inherits the bullet and changes `model`, `spawnPileType` and the `tracer` values (`Bullet_762x39Tracer` at `:4514`).

## New calibre or reuse

Reusing a vanilla calibre is one line: put the vanilla pile in `chamberableFrom[]` and the vanilla bullet in the magazine's `ammo`. A new calibre needs all three classes, the `cfgAmmoTypes` entry, and loot entries from the server lead.

## Classifying a cartridge from script

For code that must treat ammo by class (pistol, intermediate, full power, shell, arrow) without a list of class names, so that modded ammo works too: a turret, per class ballistics, loot logic.

- The classes are `enum CartridgeType { None = 0, Pistol = 1, Intermediate = 2, FullPower = 3, Shell = 4, Arrow = 5 }` (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:3` to `:11`).
- The class is stored on the ammo pile's `CfgMagazines` class, not in `CfgAmmo`: `AmmoData` reads it with `g_Game.ConfigGetInt("CfgMagazines " + init_type + " iconCartridge")` (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:32`), after checking `ConfigIsExisting("CfgMagazines " + init_type)` (`:29`). `iconCartridge` is a UI icon key that doubles as the cartridge class. Check that each pile you depend on carries a sensible value before shipping balance built on it.
- Two paths fill the cache, and the server guard covers only one. The `Magazine` constructor preloads `m_AmmoData` only when `!g_Game.IsDedicatedServer()` (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:45` to `:64`). The static `Magazine.GetAmmoData(classname)` fills the map on demand with no such guard (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:117` to `:132`), so it does work on a dedicated server. The cost is allocation: the first miss constructs an `AmmoData` (`:123` to `:125`). Read it once on an attachment event and cache the result; never call it inside a per step loop.
- Gate on `IsAmmoPile()` when you mean loose rounds. `Object.IsAmmoPile()` returns false by default (`P:\scripts\3_game\entities\object.c:571` to `:574`) and `Ammunition_Base` overrides it to return true (`P:\scripts\4_world\entities\itembase\magazine\ammunitionpiles.c:27` to `:30`). Detachable magazines do not declare `iconCartridge` (no class in `P:\DZ\weapons\attachments\magazine\config.cpp` sets it), so logic that skips this gate classifies every magazine as `None`.
- Not every vanilla pile has a class. `Ammunition_Base` sets `iconCartridge=0` (`P:\DZ\weapons\ammunition\config.cpp:22`), and five `scope=2` piles never override it: `Ammo_CupidsBolt` (`:1642`), `Ammo_RPG7_HE` (`:1947`), `Ammo_RPG7_AP` (`:2012`), `Ammo_LAW_HE` (`:2077`) and `Ammo_GrenadeM4` (`:2142`). Any table keyed on the class needs a stated policy for `None`, and must tell "0 declared" from "key absent": test with `ConfigIsExisting` first, because what `ConfigGetInt` returns for a missing path is not documented.
- Without an unpacked `P:\DZ`, the same binarized configs can be read by running `CfgConvert -txt` (DayZ Tools) over `weapons_ammunition.pbo` and `weapon_magazines.pbo` from the installed game's `Addons` folder.

## Reading a bullet's damage before it is fired

A bullet's damage profile is plain config: `ConfigGetFloat("CfgAmmo " + ammoType + " DamageApplied Health damage")`, and the same path with `Blood damage` and `Shock damage`. Vanilla reads all three this way (`P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:273` to `:275`). A mod can use it to cap extreme modded ammo without a list of class names.
