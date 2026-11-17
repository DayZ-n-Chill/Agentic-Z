# Weapon fire modes (single / burst / full-auto)

Config-side fire-mode inheritance for DayZ weapons: when to inherit vs override `class SemiAuto`/`FullAuto`, and the `Mode_*` root-scope forward-declaration trap. A line cited as `P:\...:N` was opened on `P:\`; the in-game results were measured in game and cannot be checked on `P:\`. Cross-ref: the config contract in `skills/dayz-weapons/references/cfgweapons-contract.md` ("W-CFG1: fire mode classes live at the root of the config").

---

## Fire modes on derived weapons: inherit, do not redeclare over a base that already defines them

On a weapon that inherits from another weapon that already defines its modes (`class SemiAuto`/`class FullAuto`), do not redeclare the mode subclasses with an explicit parent (`class FullAuto: Mode_FullAuto`): that re-derives from the abstract base `Mode_*` and the engine may be left with 1 valid mode. In-game symptom: the weapon only fires semi, the mode key (default X) does not cycle, and the mode name does not appear in the HUD. Instead:
- Inherit the modes without touching them (do not declare `modes[]` or the subclasses), or
- Override without a parent: `class FullAuto { soundSetShot[]=...; reloadTime=...; }` modifies the inherited one (it keeps its autofire) and changes only what you specify.

Redeclaring with `: Mode_*` is only correct when inheriting from `Rifle_Base` (which does not predefine the modes), as an AK that derives straight from `Rifle_Base` does.

Mechanism, checked in the vanilla scripts on `P:\`:
- Mode count = config `modes[]` + valid subclasses.
- Mode switch = native input `IsFireModeChange()` (default X key) → `GetWeaponManager().SetNextMuzzleMode()` (`P:\scripts\4_world\entities\dayzplayerimplement.c:1102`).
- Mode name in HUD = `GetCurrentModeName()` (`P:\scripts\4_world\classes\weapons\weaponmanager.c:1335`, read by the HUD at `P:\scripts\5_mission\gui\itemactionswidget.c:585`); empty string = engine sees 1 mode.
- Player animation profile (`pType.AddItemInHandsProfileIK(class, .asi, behaviorCfg, ik.anm, weaponStates.anm)`, from `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:409` on) and `behaviorCfg` (`SetFirearms`/`SetPistols`/`SetToolsOneHanded`, which fill an `ItemBehaviorType`, defined at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:167-239`) do not control mode count; but registering a weapon with `RegisterOneHanded` does make it behave like a one-handed tool (no selector).

Check before you assume: a "protected base" whose `config.bin` "cannot be read" must be verified by de-rapifying it with `CfgConvert -txt`. Measured case (2026-06-26): the `config.bin` of a submachine gun base de-rapified completely and already had `modes[]={"SemiAuto","FullAuto"}`, so the "protected, single mode" assumption was false.

### `Mode_*` (Mode_SemiAuto/FullAuto/Burst) belong in root scope, not inside `class CfgWeapons`

Failure case distinct from the previous one (not redeclaring the subclass, but misdeclaring the base `Mode_*`). Vanilla mode classes (`WeaponMode_Base`{autoFire=0}, `Mode_SemiAuto`, `Mode_Burst`, `Mode_FullAuto: Mode_SemiAuto` with `autoFire=1`) are defined in **ROOT scope** of the config of vanilla `bin.pbo` (`WeaponMode_Base` at `P:\bin\config.cpp:224`, `Mode_SemiAuto` `:237`, `Mode_Burst` `:271`, `Mode_FullAuto` `:315` with its `autoFire=1` at `:318`), BEFORE `class CfgWeapons` (`P:\bin\config.cpp:366`): they are **siblings** of CfgWeapons, not inside it. Forward-declaring `class Mode_FullAuto;` **inside `class CfgWeapons`** creates an empty `CfgWeapons.Mode_FullAuto` that **shadows** the real one → any `class FullAuto: Mode_FullAuto` inherits that stub **without `autoFire`** → engine discards the mode → single-mode weapon (semi only, no selector or mode name in HUD).

- **How to recognize it**: weapon with correct `modes[]={"SemiAuto","FullAuto"}` that in-game ONLY fires semi, despite byte-identical config to another that does cycle. Deceiving: CfgConvert/binarize DOES NOT complain (a forward-decl is a valid external) and de-rap looks perfect. Truth is in vanilla source (`bin.pbo`), not in comparing mod configs.
- **Fix**: forward-declare `class Mode_SemiAuto;` / `class Mode_FullAuto;` in **ROOT scope** (above `class CfgWeapons`, just like `class OpticsInfoRifle;`). Then `class FullAuto: Mode_FullAuto` resolves to the real one (`autoFire=1`). Diagnostic discriminator: a clone inheriting from an ALREADY-resolved base weapon cycles, while your base referencing `Mode_*` does not → isolates the cause to `Mode_*` resolution (NOT to the model).

Confirmed in game on a submachine gun (2026-06-28): about 12 build cycles were spent before the cause was found. Cross-ref: W-CFG1 in `skills/dayz-weapons/references/cfgweapons-contract.md`; the forward declarations are also in `skills/_shared/weapons/weapon-config.md`.
