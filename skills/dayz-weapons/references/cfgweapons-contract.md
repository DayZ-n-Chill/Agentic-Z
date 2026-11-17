# The `CfgWeapons` config of a custom firearm

Config inheritance, the chamber, magazine, muzzle and optics entries, fire modes, recoil, dispersion and the config side of jamming, as learned on the author's two weapon projects. The motion of the mechanism (bolt, reload, fire, jam and unjam animations) belongs to the dayz-animation-pipeline skill. The vanilla keys themselves, each with its `P:\` line, are in the weapons pack: `skills/_shared/weapons/weapon-classes.md`, `skills/_shared/weapons/weapon-config.md` and `skills/_shared/weapons/recoil-fire-modes.md`.

Marks: `[VERIFIED in-game]` means a real in-game test recorded in one of the author's projects (A6_MK47, A6_SR2M; third-party, not on `P:\`), `[VERIFIED-vanilla]` means read in the cited vanilla file, `[UNVERIFIED]` means inferred.

## The class tree is not a straight line

`[VERIFIED-vanilla]` Script side firearm classes, all under `P:\scripts\4_world\entities\firearms\`. `RifleBoltFree_Base` descends from `Rifle_Base`, but `BoltActionRifle_Base` and `Pistol_Base` extend `Weapon_Base` directly, not `Rifle_Base`:

```
Weapon (native)
 └─ Weapon_Base            (weapon_base.c:38)
     ├─ Rifle_Base         (rifle_base.c:10, extends Weapon_Base)
     │   ├─ RifleBoltFree_Base   (rifleboltfree_base.c:92, extends Rifle_Base)
     │   ├─ RifleBoltLock_Base   (rifleboltlock_base.c:119, extends Rifle_Base)
     │   └─ OpenBolt_Base        (openbolt_base.c:122, extends Rifle_Base)
     ├─ BoltActionRifle_Base     (boltactionrifle_base.c:5, extends Weapon_Base directly)
     │   └─ BoltActionRifle_ExternalMagazine_Base   (boltactionrifleexternalmagazine_base.c:112)
     └─ Pistol_Base              (pistol_base.c:149, extends Weapon_Base directly)
```

Do not assume a shared `Rifle_Base` parent in script. The config tree differs again: in config, `BoltActionRifle_Base` does inherit `Rifle_Base` (`P:\DZ\data\config.cpp:4259`).

Since 1.30 there are more script branches under the same `Weapon_Base` root (the warning about their missing models is in `dayz-1-30-weapons.md`):

- `SCARH_Base : RifleBoltLock_Base` (`P:\scripts\4_world\entities\firearms\automaticrifle\scarh.c:1`) and `SCARL_Base : SCARH_Base` (`P:\scripts\4_world\entities\firearms\automaticrifle\scarl.c:1`). The SCAR-H config class is `SCARH_Base: Rifle_Base` (`P:\DZ\weapons\firearms\scarh\config.cpp:26`). That config file has no `SCARL` class.
- `MP18_Base extends OpenBolt_Base` (`P:\scripts\4_world\entities\firearms\smg\mp18.c:1`).
- `LeeEnfield_Base : BoltActionRifle_ExternalMagazine_Base` (`P:\scripts\4_world\entities\firearms\rifle\leeenfield.c:1`).
- `Luger_Base : Pistol_Base` (`P:\scripts\4_world\entities\firearms\pistol\luger.c:1`); its pistol animation states come from the `Get*PistolAnimState()` getters (`pistol_base.c:611-629`), not from a second state machine.

`[VERIFIED-vanilla]` `Weapon_Base` owns the state machine and the jam state (`P:\scripts\4_world\entities\firearms\weapon_base.c`): `m_abilities` (`:48`), `m_fsm` (`:49`), `m_isJammed` (`:50`), `m_Charged` (`:54`), `m_WeaponOpen` (`:55`), `m_ChanceToJam` (`:72`).

`[VERIFIED-vanilla]` `RifleBoltFree_Base` builds its state machine in `InitStateMachine()` (`P:\scripts\4_world\entities\firearms\rifleboltfree_base.c:106`) with the stable states `C00`, `C10`, `C11`, `C01`, `JF0` and `JF1` (`:94-99`). The vanilla comment gives the pattern `[CLJ][01][01]`: closed, locked or jammed; no bullet or bullet; no magazine or magazine (`:128-129`). It adds ability records for reload (`:109-113`), chambering (`:115`), mechanism (`:117`), unjamming start and end (`:119-120`), and fire jam, normal and dry (`:122-124`).

### Choosing the config base

Inherit the config base of the vanilla or pack weapon whose ammo, magazines, recoil, sounds and animations you want for free, and override only what differs.

- MK47 `[VERIFIED in-game]`: config `A6_MK47_Base : A6_AKM_Base`, script `RifleBoltFree_Base` (`A6_MK47_dev\research\F0-herencia-decision.md:22-30`; the "fixed decisions" list in the project's notes).
- SR2M `[VERIFIED in-game]`: config `A6_SR2M_Base : A6_PP19_Base` (`A6_SR2M\config.cpp:783`), an SMG that inherits the A6 PP19 base, not an AK base. The base is chosen per weapon; do not copy MK47's.

### Inheriting another mod's weapon

Inheriting `MyWeapon_Base: SomePack_Weapon_Base` (another mod's weapon) works and brings its modes, slots and state machine already resolved, but that base must be forward declared inside `CfgWeapons` and its addon must be in `requiredAddons[]`. Pure inheritance, with no `Mode_*` reference of your own, avoids the fire mode scope trap below entirely; that is why a test clone on SR2M cycled its modes. The moment you declare the fire mode subclasses again to customize them (sounds, for example), the trap applies, so fix the scope first.

## Config keys

Read by the author in a derapified copy of the A6 AK config (`A6_MK47_dev\research\a6_ak_config\config.cpp`, from `A6_Weapons\...\AK\config.bin`; third-party, not on `P:\`). His line numbers are those of the 7.62x39 AKM block the MK47 inherits. The last column gives the same key in the vanilla AKM config, `P:\DZ\weapons\firearms\akm\config.cpp`.

| Key | Purpose | A6 AK config line | Vanilla AKM line |
|---|---|---|---|
| `initSpeedMultiplier` | The weapon's factor on muzzle velocity (effective velocity = weapon factor x ammo speed) | `:364` (also `:33`) | `:43` |
| `chamberableFrom[]` | Ammo types the chamber accepts (`Ammo_762x39` and variants) | `:367` | `:46` |
| `reloadAction` | Reload action (for example `"ReloadAKM"`) | `:374` | not set in the vanilla AKM config; vanilla sets it on the bow and launcher bases (`P:\DZ\data\config.cpp:4592`, `:4756`) |
| `modes[] = {"SemiAuto","FullAuto"}` | List of fire modes | `:375` | `:77` |
| `weaponStateAnim` | The weapon state `.anm` (bolt and bullet driver); made on the animation side, its path lives in config | `:378` | `:189` |
| `class SemiAuto : Mode_SemiAuto`, `class FullAuto : Mode_FullAuto` | Per mode `dispersion`, rate of fire, recoil, sound sets | (per mode blocks) | `:87`, `:119` |
| `dispersion` | Per mode cone | `:386` (in the mode block) | `:116`, `:164` |
| `magazines[]` | Accepted magazine classes | `F0-herencia-decision.md:14` | `:51` |
| `simpleHiddenSelections[]` | Simple selections script can hide (`hide_pistolgrip` and `hide_sidemount` on the A6 AK) | `F0-herencia-decision.md:17` | `:68` |
| `attachments[]` | Slots the weapon offers (`weaponOptics`, `weaponMuzzleAK`, `weaponButtstockM4`, `weaponForegrip`, `weaponLight*` and more) | `F0-herencia-decision.md:18` | `:197` |
| `inventorySlot` (on the magazine or attachment) | The slot an attachment occupies (for example `"magazine"`) | (attachment blocks) | see `skills/_shared/weapons/attachments.md` |

SR2M adds `discreteDistance[] = {100,200}` for its iron sights (vanilla AKM: `P:\DZ\weapons\firearms\akm\config.cpp:170`). Check a key's exact line with Grep before quoting it: the table is the AKM block, and the base you inherit may differ.

## W-CFG1: fire mode classes live at the root of the config

`[VERIFIED in-game]` SR2M bug 10, the most expensive weapon mistake found so far: about 12 rebuilds.

The vanilla fire mode base classes are defined at the root of the engine config, as siblings of `CfgWeapons`, not inside it. `[VERIFIED-vanilla]` in `P:\bin\config.cpp` (the unpacked `dta\bin.pbo`):

| Class | Line | Note |
|---|---|---|
| `WeaponMode_Base` | `P:\bin\config.cpp:224` | `autoFire=0` at `:226`, `burst=1` at `:228` |
| `Mode_SemiAuto: WeaponMode_Base` | `P:\bin\config.cpp:237` | |
| `Mode_Single: Mode_SemiAuto` | `P:\bin\config.cpp:254` | |
| `Mode_Burst: Mode_SemiAuto` | `P:\bin\config.cpp:271` | `burst=3` at `:274` |
| `Mode_Double: Mode_SemiAuto` | `P:\bin\config.cpp:293` | |
| `Mode_FullAuto: Mode_SemiAuto` | `P:\bin\config.cpp:315` | `autoFire=1` at `:318`: this is where full auto comes from |
| `OpticsInfoDefault` | `P:\bin\config.cpp:334` | also root |
| `Muzzle_Base` | `P:\bin\config.cpp:345` | also root |
| `CfgWeapons` | `P:\bin\config.cpp:366` | only here does `CfgWeapons` open |

(The author's note gave lines 260 to 347 from his own extraction of `bin.pbo`; the classes and their order are the same, the numbers above are the ones on `P:\`.) `DZ_Data` then adds to `Mode_SemiAuto` and defines `Mode_Safe`, again at the root (`P:\DZ\data\config.cpp:3771`, `:3778`).

**The bug.** Forward declaring `class Mode_FullAuto;` inside `class CfgWeapons {}` creates a new, empty `CfgWeapons.Mode_FullAuto` that hides the real root class. Any `class FullAuto: Mode_FullAuto` in the weapon then inherits the empty one, with no `autoFire`. The engine treats the mode as invalid and drops it. The weapon has one mode: it fires semi only, shows no mode name in the HUD, and the fire select key does not cycle.

**Why nothing warns you.** `CfgConvert` and binarize do not report it, because a forward declaration is a valid reference to an outside class. The derapified `.bin` looks perfect, and the weapon's config can be byte for byte the same as another weapon's that does cycle. You cannot find it by comparing mod configs; the answer is in the engine config.

**The fix.** Forward declare `class Mode_SemiAuto;` and `class Mode_FullAuto;` at the root, above `class CfgWeapons`, the way vanilla weapon configs do (`P:\DZ\weapons\firearms\akm\config.cpp:18-22`: `Mode_Safe`, `Mode_SemiAuto`, `Mode_Burst`, `Mode_FullAuto`, `OpticsInfoRifle`). Then `class FullAuto: Mode_FullAuto` resolves to the real class, inherits `autoFire=1`, and full auto and the selector work.

```cpp
class OpticsInfoRifle;
class Mode_SemiAuto;      // root: refers to the real engine class
class Mode_FullAuto;      // root
class CfgWeapons
{
    class Rifle_Base;        // weapon bases do go inside CfgWeapons (that is their scope)
    class A6_PP19_Base;      // the same
    class MyWeapon_Base: A6_PP19_Base   // or Rifle_Base
    {
        class SemiAuto: Mode_SemiAuto { soundSetShot[]={...}; };  // now resolves
        class FullAuto: Mode_FullAuto { soundSetShot[]={...}; };  // autoFire=1 inherited
    };
};
```

SR2M carries the same root cause as a comment in its config (`A6_SR2M\config.cpp:773-778`).

Which classes go where: weapon bases (`Rifle_Base`, a pack's `<Pack>_Base`) are forward declared inside `CfgWeapons`, their real scope. The `Mode_*` classes, `WeaponMode_Base`, `OpticsInfoDefault`, `Muzzle_Base` and `OpticsInfoRifle` (`P:\DZ\data\config.cpp:3930`) are root classes. Get the scope right per class. (The author's note listed `OpticsInfoRifle` among the classes declared inside `CfgWeapons`; on `P:\` it is a root class and vanilla declares it at the root, as his own example does.)

### How it was found: use this for "the weapon will not cycle modes"

1. **Isolate in game with a clone; do not keep comparing configs.** Add a throwaway weapon that inherits a base known to work, unchanged (for example `class MyTest: A6_PP19_Base { scope=2; model=<yours>; }`), and one that mirrors the structure you suspect. Spawn both and the real weapon, and press the fire mode key on each. If the clone of the working base cycles and yours does not, the fault is in your config, not in the model or the engine. This is what cleared the model and pointed at how `Mode_*` resolves instead of at any visible key.
2. **When two mod configs compare as identical, go to the engine config** (`P:\bin\config.cpp`; the author unpacked `dta\bin.pbo` with `ExtractPbo -P`). The difference was scope, which no mod's derapified config shows.
3. A throwaway weapon that inherits a `scope=0` base and has no `model=` crashes on spawn. Give every test weapon its own `model=`.

## Testing a weapon whose base classes come from a third-party pack with loose scripts

If the weapon depends on a separate pack (base classes in an already built PBO) whose scripts only warn on the retail game but fail on the Diag build:

- The Diag server stops before it binds, on the strict compile of the pack.
- The retail client with `-filePatching` crashes on connect (`CDPInitServer` / `CDPCreateClient`, a null read at 0x0).
- Use the retail executables without file patching. The PBO already carries your change, so file patching is not needed, and leaving it out avoids both failures. It is also the configuration closest to a live server.

With the knowledge pack's own launcher the author ran `dayz-test.ps1 -Mod <Mod> -Mode all -Retail -NoFilePatching -BaseMods "@CF;@Dabs Framework;@VPPAdminTools;@<pack>_deps"`. `/dayz-launch-test` starts the Diag build, so for such a pack start the retail server and client by hand with the same `-mod=` list.

## Jam and unjam: the config side

- Jamming is `Weapon_Base` state: `m_isJammed` (`weapon_base.c:50`) and `m_ChanceToJam`, one value per health level (`:72`). `[VERIFIED-vanilla]`
- `RifleBoltFree_Base` adds the `WeaponActions.UNJAMMING` start and end ability records (`rifleboltfree_base.c:119-120`) and the `FIRE_JAM` fire action (`:122`). `[VERIFIED-vanilla]`
- The vanilla firearm actions are in `P:\scripts\4_world\classes\useractionscomponent\actions\weapons\` (`firearmactionunjam.c`, `firearmactionmechanicmanipulate.c` and others).

On the config side you inherit the base's abilities and supply the jammed look through `weaponStateAnim`. The unjam motion is not config: the cause of the unjam loop fault (a hold of about 5 seconds driven by a timer, which needs `LoopStart` and `LoopEnd`) is written up in the dayz-animation-pipeline skill (author's SR2M notes, 2026-07-02). Do not try to fix a jam motion bug from config.

## Attachment and optics slots

- `attachments[]` declares the slots the weapon offers (`weaponOptics`, `weaponMuzzleAK`, `weaponButtstockM4`, `weaponForegrip`, `weaponLight*` and more). An attachment fits only if its own `inventorySlot[]` names one of them.
- SR2M `[VERIFIED in-game]` (first version, 2026-06-25): an optics mount (`A6_SR2M_RailMount`) is a slot inside a slot. The mount occupies the weapon's optics slot and itself offers a slot that takes M4 optics, so optics need the mount first. Two side slots use the A6 pack's switchable attachments (the "fixed decisions" list in the SR2M project's notes).
- `[UNVERIFIED]` The exact switchable rail flags (`hasRailFunctionality`, `CanAcceptLeft/RightFlashlight`) come from the SR2M product spec, which cites `A6_Switchable_Base.c:35-40`. Read that file before writing an attachment section that quotes them.

## Cite, then verify

The firearm tree is not linear and the per mode blocks differ by base. Grep for the key in `P:\scripts\4_world\entities\firearms\`, in `P:\DZ\weapons\` or in the derapified config of the base you inherit before writing it, and keep the marks.

## DayZ 1.30: config and script changes

Entity side only. Details and literal blocks: `dayz-1-30-weapons.md`.

- **Script recoil is not the config `recoil` string.** `SpawnRecoilObject()` returns `SCARLRecoil`, `LugerRecoil`, `LeeEnfieldRecoil` or `MP18Recoil` (`P:\scripts\4_world\classes\recoilbase\recoils\`). The shipped `SCARH_Base` still sets `recoil="recoil_fal"` in config (`P:\DZ\weapons\firearms\scarh\config.cpp:94`); that string is a different thing (see `skills/_shared/weapons/recoil-fire-modes.md`). Matching a 5.56 SCAR shaped mod to the SCAR-H means inheriting that config block and then changing `chamberableFrom[]`, `magazines[]` and the script recoil. The data on `P:\` has no `SCARL` config class to copy.
- **Magazine attach and detach.** `FirearmActionAttachMagazine` requires `TestAttachMagazine(GetCurrentMuzzle(), mag, false, true)` (`P:\scripts\4_world\classes\useractionscomponent\actions\weapons\firearmactionattachmagazine.c:256`). `FirearmActionDetachMagazine_Old` is marked `[Obsolete("1.30: Use class FirearmActionDetachMagazine instead")]` (`P:\scripts\4_world\classes\useractionscomponent\actions\weapons\firearmactiondetachmagazine.c:13`). Open bolt bases register the new detach action in `SetActions()` (`P:\scripts\4_world\entities\firearms\openbolt_base.c:388`).
- **State machine repair when a magazine is pulled.** `Weapon_Base.EEItemDetached` calls `ValidateAndRepair()` if `item.IsMagazine()` (`P:\scripts\4_world\entities\firearms\weapon_base.c:1115-1121`).
- **Explosives.** Do not call `ExplosivesBase.SetParticleExplosion` or `AddExplosionEffectForSurface` (both `[Obsolete("1.30: Handled in AmmoTypes instead")]`, `P:\scripts\4_world\entities\explosivesbase.c:306-310` and `:433`). Use the `CfgAmmo` key `particle` and `AmmoTypesAPI.GetExplosiveEffectData`.

## Spawning a loaded weapon, and the vanilla keys and calls around it

`Weapon_Base.CreateWeaponWithAmmo`, `SpawnAmmo` and the `WeaponWithAmmoFlags` values, the state queries on `Weapon` and `Weapon_Base`, the firearm action classes, and the config keys `chamberSize`, `chamberedRound`, `recoilModifier[]`, `aiRateOfFire` and the magazine keys are vanilla facts, so they live in the weapons pack: `skills/_shared/weapons/weapon-script-api.md` (script calls), `skills/_shared/weapons/weapon-config.md` (weapon keys) and `skills/_shared/weapons/magazines-ammo.md` (magazine keys).
