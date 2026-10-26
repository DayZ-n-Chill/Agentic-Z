# Recoil and fire modes

Recoil is a script class. Fire modes are config classes. This file covers both.

## Recoil is set in script

- `Weapon_Base.SpawnRecoilObject` returns the recoil object for each shot; the default is `DefaultRecoil` (`P:\scripts\4_world\entities\firearms\weapon_base.c:1252`).
- Each vanilla gun overrides it on its script base. The CZ527: `override RecoilBase SpawnRecoilObject() { return new CZ527Recoil(this); }` (`P:\scripts\4_world\entities\firearms\rifle\cz527.c:3` to `:6`).
- Recoil classes extend `RecoilBase` (`P:\scripts\4_world\classes\recoilbase\recoilbase.c:1`) and set their values in `Init` (`:40`), which the constructor calls (`:29` to `:38`). One file per gun lives in `P:\scripts\4_world\classes\recoilbase\recoils\`.

The fire mode's `recoil="recoil_cz527"` and `recoilProne` strings (`P:\DZ\weapons\firearms\cz527\config.cpp:105`, `:106`) do not name a config class: no `CfgRecoils` or `recoil_cz527` class exists anywhere under `P:\DZ` or `P:\scripts`. Tune recoil in the script class, not in those strings.

### What a recoil class sets

From `CZ527Recoil` (`P:\scripts\4_world\classes\recoilbase\recoils\cz527recoil.c`) and the field comments in `recoilbase.c:13` to `:27`:

| Field | Meaning |
|---|---|
| `m_HandsCurvePoints` | Points of a two dimensional curve the hands follow (z is ignored), ending at `"0 0 0"`. The CZ527 adds four random points then the origin (`cz527recoil.c:9` to `:17`). |
| `m_HandsOffsetRelativeTime` | Share of the mode's `reloadTime` the hands take to run the curve (0 to 1). |
| `m_MouseOffsetRangeMin`, `m_MouseOffsetRangeMax` | Angle range in degrees for the aim kick direction. The CZ527 uses 80 to 100 (`cz527recoil.c:20`, `:21`). |
| `m_MouseOffsetDistance` | How far the aim moves. |
| `m_MouseOffsetRelativeTime` | Share of `reloadTime` the aim kick takes. |
| `m_CamOffsetDistance`, `m_CamOffsetRelativeTime` | Camera push back along its axis and how long it takes. |

Random values come from `m_Player.GetRandomGeneratorSyncManager().GetRandomInRange(RandomGeneratorSyncUsage.RGSRecoil, min, max)` (`cz527recoil.c:9`) so client and server agree. Use the same call; never `Math.RandomFloat` in a recoil class.

The recoil object lives for one mode `reloadTime` and then deletes itself (`recoilbase.c:100` to `:103`), so a faster rate of fire means a shorter recoil curve.

### Recoil modifiers

`RecoilBase.GetRecoilModifier` takes the weapon's combined modifiers (`recoilbase.c:193`), which are the weapon's `recoilModifier[]` multiplied by each attachment's (`P:\scripts\4_world\classes\propertymodifiers.c:40` to `:51`). The first two values scale horizontal and vertical movement (`recoilbase.c:86` to `:90`); the third scales the camera offset (`:58`). Use `recoilModifier[]` on the weapon for a small change to a vanilla gun, and a new recoil class for a new feel.

### Writing a mod recoil class

A mod recoil class is Enforce Script in `4_World` and follows `skills/_shared/enscript-style.md`:

1. Create `MyMod_RifleRecoil : RecoilBase` with an `override void Init()` that fills the fields above, starting from the closest vanilla recoil file.
2. Create a script class with the same name as the mod's config base class, extending the vanilla script base (for example `class MyMod_Rifle_Base : CZ527_Base`), and override `SpawnRecoilObject` to return the new class.

## Fire modes

- `modes[]` lists the mode classes in the order the player cycles them (`cz527\config.cpp:81`: `"Single"`; AKM at `P:\DZ\weapons\firearms\akm\config.cpp:77`: `"SemiAuto"`, `"FullAuto"`).
- Each mode is a class inheriting a root mode base: `Mode_Single`, `Mode_SemiAuto`, `Mode_Burst` or `Mode_FullAuto` (`cz527\config.cpp:85`; AKM `SemiAuto` at `akm\config.cpp:87`, `FullAuto` at `:119`). `Mode_SemiAuto` and `Mode_Safe` are defined in `P:\DZ\data\config.cpp:3771` and `:3778`; `Mode_Burst` and `Mode_FullAuto` are only forward declared there (`:3776`, `:3777`). Declare whichever you use at the root of your file, as vanilla does.
- Burst sets `burst=3` on a `Mode_Burst` class (AUG at `P:\DZ\weapons\firearms\aug\config.cpp:88`, `:114`).
- Script hears a mode change through `Weapon_Base.OnFireModeChange` (`weapon_base.c:1048`).

Keys on each mode class:

| Key | What it does | Vanilla line |
|---|---|---|
| `reloadTime` | Seconds between shots, so it sets rate of fire and recoil length. AKM full auto uses `0.097999997`. | `akm\config.cpp:161` |
| `dispersion` | Spread of shots. | `cz527\config.cpp:107` |
| `magazineSlot` | Slot the magazine uses, `"magazine"`. | `cz527\config.cpp:108` |
| `soundSetShot[]`, `soundSetShotExt[]` | Shot sounds, plain and suppressed (see `muzzle-effects.md`). | `cz527\config.cpp:87`, `:95` |
| `soundSetShot1st[]`, `soundSetShotExt1st[]` | First shot of an automatic burst. | `akm\config.cpp:121`, `:135` |
| `recoil`, `recoilProne` | Strings that name no class; see above. | `cz527\config.cpp:105` |
