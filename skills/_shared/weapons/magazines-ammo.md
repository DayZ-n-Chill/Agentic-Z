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
