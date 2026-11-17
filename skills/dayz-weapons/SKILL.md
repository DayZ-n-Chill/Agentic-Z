---
name: dayz-weapons
description: "Reference for building and importing the entity side of a DayZ firearm (rifle, SMG or pistol): the .p3d bolt, trigger and magazine selections and memory points, the player bone remap (AddItemBoneRemap, Weapon_Bolt, Weapon_Trigger), CfgWeapons inheritance, chamberableFrom, magazines, Mode_SemiAuto and Mode_FullAuto, dispersion, recoil and jam config, attachment and optics slots, muzzle and ejection points, face winding and the binarized model path. Use for a custom weapon import, choosing a CfgWeapons base, a bolt or trigger that does not move, a deformed mesh, a magazine or optic that will not attach, a misplaced muzzle or casing ejection, chamber or jam problems, a missing fire mode, a white or invisible weapon, or a crash on equip. Also covers DayZ 1.30: GetExplosiveEffectData and ExplosiveEffectData, the Get*PistolAnimState getters, and the Nasdara SCARL, Luger, LeeEnfield and MP18. Hand pose, aiming, reload, fire and jam animations belong to the animation skill, not here."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ firearms: the entity side

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts of its own, so there is no preflight gate. The `dayz-weapon-specialist` agent reads it for a custom firearm, and `dayz-object-builder` reads it for what the weapon model must contain.

A custom firearm extends the vanilla `Weapon` chain; it is never built from `EntityAI`. Inheriting the config base of the vanilla or pack weapon whose ammo, magazines, recoil, sounds and animations you want gives all of that for free. You write only the mesh, the part names the `.p3d` must carry, the config differences and the import transform. This skill covers that entity layer: the selections and memory points of the `.p3d`, the bone remap that ties them to the player skeleton, the `CfgWeapons` config, and the model path, winding and binarized build rules that decide whether the weapon loads at all.

This skill is not weapon animation. The hand pose, the aiming line, and the motion of the bolt, trigger, reload, fire and unjam (the `.anm` and `.asi` files) belong to the dayz-animation-pipeline skill and the `dayz-animation-specialist` agent. This skill owns which selections and points must exist and cover the right part, and which selection maps to which bone, not how they move. The owner table below gives the exact split.

Where the facts come from: vanilla facts cite the file on `P:\` they were read in. The measured lessons come from two finished weapon projects of the knowledge pack's author, both tested in game: A6_MK47 (a 7.62x39 rifle built from an AI generated mesh, tested 2026-06-11: import transform, model path, winding) and A6_SR2M (a 9x19 SMG built from a hand made mesh, tested 2026-06-30: bone remap, a selection painted on the wrong part and its repaint, casing side, fire mode scope). Those projects and the A6 weapon pack they build on are third-party; their files are not on `P:\`. Marks: `[VERIFIED in-game]` means a real in-game test recorded in one of those projects, `[VERIFIED-vanilla]` means read in the cited vanilla file, `[UNVERIFIED]` means inferred and not confirmed.

## What to read

| Question | Read |
|---|---|
| Which selections and memory points must the weapon `.p3d` have, how do I check a selection covers the real part, which side do casings eject? | `references/p3d-selection-contract.md` |
| Which selection maps to which player bone, and when is a remap needed? | `references/bone-remap.md` |
| Which config base do I inherit, what do the fire mode, jam, attachment and optics entries look like, why is my gun stuck in single fire? | `references/cfgweapons-contract.md` |
| How do I import the mesh (axis swap, normals, winding), where must `model=` point, why must I test the binarized build? | `references/import-rule-v4.md` |
| What changed for firearms in DayZ 1.30 (pistol animation state getters, open bolt magazine detach, explosion effect API, the Nasdara weapons)? | `references/dayz-1-30-weapons.md` |
| Vanilla class parents by mechanism, `CfgWeapons` keys, magazines and ammo, slots, recoil classes, muzzle effects | the weapons pack, front index `skills/_shared/weapons/README.md` |
| Script calls: spawning a loaded weapon, reading a weapon's state, classifying ammo on the server | `skills/_shared/weapons/weapon-script-api.md` and `skills/_shared/weapons/magazines-ammo.md` |

## Checks to make before the first in-game test

Each one cost many builds on one of the two projects. All of them can be checked offline; a firearm test cycle costs as much as any other DayZ rebuild.

1. **W-BUILD1: `model=` points at the real path inside the PBO, and the build is clean.** `[VERIFIED in-game]` MK47. The config pointed at the PBO root while the `.p3d` lived under `data\`. A build without a clean temp folder carried an old unbinarized copy at the root, and that copy was the model the engine loaded, so every offline winding and normal measurement described the wrong file. Fix: `model="\<Mod>\data\<weapon>.p3d"` and a clean rebuild (`/dayz-build-pbo <ModName> --clean`). See `references/import-rule-v4.md`, "Model path".
2. **W-BUILD2: test the binarized build; test A6 family mods with the retail game.** `[VERIFIED in-game]` MK47. The winding and normals rule only holds on the binarized model, because binarizing flips the winding. A build served unbinarized measures the wrong thing. The A6 weapon pack also uses script without braces that the Diag build refuses to compile while the retail build only warns. See `references/import-rule-v4.md`.
3. **W-SEL1: every selection that feeds a bone remap covers its real part.** `[VERIFIED in-game]` SR2M. The `bolt` selection had been painted on the barrel (X from -0.19 to -0.09, in front of the chamber), not on the bolt, so the remap would have slid the barrel. It was caught offline by comparing the selection's centre with the anatomy of the gun: a bolt sits behind the chamber. See `references/p3d-selection-contract.md`, "A selection on the wrong part".
4. **W-MEM1: the casing ejection side depends on the weapon's axes; read the reference weapon, do not assume.** `[VERIFIED in-game]` SR2M. `nabojnicestart` and `nabojniceend` set the side. SR2M had them on +Z, which threw casings into the receiver; -Z was correct. See `references/p3d-selection-contract.md`.
5. **W-MEM2: a weapon `.p3d` carries no hand or grip memory points.** Read in the memory LOD of a debinarized vanilla `akm.p3d`; not yet checked on `P:\`, where the vanilla models are binarized. The grip comes from the player's IK pose animation and from matching the reference weapon's shape. That is animation work. See `references/p3d-selection-contract.md`.
6. **W-CFG1: `Mode_SemiAuto` and `Mode_FullAuto` are forward declared at the root of the config, before `class CfgWeapons`.** `[VERIFIED in-game]` SR2M. Declared inside `CfgWeapons` they become empty classes without `autoFire=1`, the engine drops the full auto mode, and the gun fires single shots only. The real classes are at the root of the engine config (`Mode_FullAuto` at `P:\bin\config.cpp:315`). See `references/cfgweapons-contract.md`, "Fire mode classes live at the root".
7. **W-STAGING1 (since 1.30): a firearm script under `4_World\Entities\Firearms\` does not mean a `.p3d` or a `CfgWeapons` class ships for it.** `[VERIFIED-vanilla]` The vanilla data on `P:\` has the scripts for `SCARL_Base` (`P:\scripts\4_world\entities\firearms\automaticrifle\scarl.c:1`), `Luger_Base`, `LeeEnfield_Base` and `MP18_Base`, and their hand animation registrations, but no folder for them under `P:\DZ\weapons\firearms\` or `P:\DZ\weapons\pistols\`. Use a shipped weapon as the reference instead: the SCAR-H, a 1.29 pistol, the CZ527 or the CZ61. The knowledge pack reports that game build 1.30.164200 ships these four in `nasdara\addons\weapons_nasdara.pbo`, where a config parent is not always the script parent (`SCARL_Base: Rifle_Base` in config, `SCARL_Base : SCARH_Base` in script); not yet checked on `P:\`. See `references/dayz-1-30-weapons.md`.

Memory point checks (each was a real fault on the AI generated MK47 mesh): `usti hlavne` and `konec hlavne` share Y and Z, so the bore is level; `bolt_axis` runs parallel to the bore; the ejection direction is within about 25 degrees of the reference weapon's; the height of `eye` over the bore is close to the reference. See `references/p3d-selection-contract.md`, "Memory point checks".

## Compare with the vanilla weapon you inherit

Both projects come down to one habit. Pick the vanilla or pack weapon whose behaviour you want (the AKM for an AK pattern rifle, the AKS74U or PM73 for an SMG), get a readable copy of its model, read its memory LOD and its config, and match them: the same named selections, memory points laid out the same way, and a config base chosen for its ammo, magazines, recoil, sounds and animations. Every check in the list above falls out of that one comparison instead of one in-game failure at a time.

Agentic-Z ships no debinarizer, and the vanilla weapon models on `P:\` are binarized, so the comparison uses the vanilla config and scripts on `P:\` plus a readable model you already have the right to open (the author used an external ODOL to MLOD converter). For the mod's own model, `/dayz-p3d-audit` reads the MLOD source.

Since 1.30 the weapon you inherit in script may have no model in the data you have (W-STAGING1). On `P:\` the SCAR-H model is `P:\DZ\weapons\firearms\scarh\scarh.p3d`; use it, or another shipped weapon, for a `SCARL` shaped rifle. Details: `references/dayz-1-30-weapons.md`.

## Symptom to cause

| Symptom | Likely cause | Read |
|---|---|---|
| Invisible or white weapon, or a crash on equip | `model=` points at the PBO root and not at `data\`, or the build was not clean and carried an old model (W-BUILD1) | `references/import-rule-v4.md`, "Model path" |
| Winding or normals edited, nothing changes in game | The game is loading an unbinarized model, not the binarized one (W-BUILD2) | `references/import-rule-v4.md` |
| Bolt or charging handle does not move | The selection is on the wrong part (W-SEL1), or the bone remap is missing, or the `weaponStateAnim` has no bolt channel | `references/p3d-selection-contract.md`, `references/bone-remap.md` |
| Trigger does not move when firing | No `trigger` to `Weapon_Trigger` remap; the vanilla fire and reload animations drive that bone | `references/bone-remap.md` |
| Casings eject on the wrong side | Flip `nabojnicestart` and `nabojniceend` in the memory LOD (W-MEM1) | `references/p3d-selection-contract.md` |
| Stuck in single fire, full auto missing | `Mode_*` declared inside `CfgWeapons` and not at the root (W-CFG1) | `references/cfgweapons-contract.md` |
| Tilted fire line, muzzle flash off the barrel | `usti hlavne` and `konec hlavne` not level, or `usti hlavne` misplaced | `references/p3d-selection-contract.md`, "Memory point checks" |
| Magazine will not attach, or sits in the wrong slot | `magazines[]` or the magazine's `inventorySlot[]` does not match | `references/cfgweapons-contract.md`, `skills/_shared/weapons/magazines-ammo.md` |
| Optic or attachment refused | The slot name in `attachments[]` does not match the attachment's `inventorySlot[]`; or the optic needs a mount first | `references/cfgweapons-contract.md`, `skills/_shared/weapons/attachments.md` |
| Grip, hands, aiming or rider pose wrong | Not this skill: animation | the dayz-animation-pipeline skill, weapon in hands |
| Bolt slide, reload, fire or unjam motion wrong | Not this skill: animation (`.anm` and `.asi`) | the dayz-animation-pipeline skill, weapon animation |
| `SCARL`, `Luger`, `LeeEnfield` or `MP18` will not spawn | W-STAGING1: script and hand animation exist, the data you run has no config class or model for them | `references/dayz-1-30-weapons.md` |
| Compile error on `GetExplosionParticleID` (1.30) | Replaced by `AmmoTypesAPI.GetExplosiveEffectData(ammo, surface)` | `references/dayz-1-30-weapons.md`, "Explosion effects" |
| Pistol slide or toggle shows the wrong state (1.30) | Override the `Get*PistolAnimState()` getters; do not copy the pistol state machine | `references/dayz-1-30-weapons.md`, "Pistol state machine" |

## Who owns what

| Concern | Owner |
|---|---|
| Which selections and memory points the `.p3d` must have and what each must cover; casing side | this skill, `references/p3d-selection-contract.md`; the model itself is `dayz-object-builder` work |
| `AddItemBoneRemap`: which selection goes to which bone, and the check that the selection covers the part | this skill, `references/bone-remap.md` |
| `CfgWeapons`: inheritance, chamber, magazine, muzzle and optics slots, fire modes, recoil, dispersion and jam config | this skill, `references/cfgweapons-contract.md`, with the weapons pack; `dayz-weapon-specialist` writes it |
| Model path, import transform, winding, binarized build | this skill, `references/import-rule-v4.md` |
| 1.30 pistol animation state getters, open bolt magazine detach, explosion effect API, the Nasdara weapons | this skill, `references/dayz-1-30-weapons.md` |
| Grip, hand pose, aiming line, what `AddItemInHandsProfileIK` means, player skeleton bones | the dayz-animation-pipeline skill (its weapon in hands and player skeleton references); `dayz-animation-specialist` |
| The weapon state `.anm` (bolt slide, bullet eject), the fire, reload and chamber action animations, the unjam loop | the dayz-animation-pipeline skill (its weapon animation references) |
| The full memory point catalogue and the grip viewer `weapon_grip_viewer.py` | the dayz-animation-pipeline skill (referenced from here, not copied) |
| Mesh assembly, LODs, generated textures | the dayz-model-pipeline skill; `dayz-object-builder` |
| Texture and `.rvmat` zones | the `dayz-texture-pipeline` skill; `dayz-asset-specialist` |
| Collision, action and path audit of the `.p3d` | `/dayz-p3d-audit` |
| Enforce Script rules (`modded class`, the script side of config) | `skills/_shared/enscript-style.md` and the Enforce Script pack; the `enforce-script-reference` skill |
| Packing and binarizing the PBO | `/dayz-build-pbo` |
| Build, deploy, launch and checks in game | `/dayz-launch-test` and `/dayz-gate` |

## Cite, then verify

Weapon config keys and selection names are easy to half remember, and the vanilla firearm class tree is not a straight line: `RifleBoltFree_Base` extends `Rifle_Base` (`P:\scripts\4_world\entities\firearms\rifleboltfree_base.c:92`), but `BoltActionRifle_Base` and `Pistol_Base` extend `Weapon_Base` directly (`P:\scripts\4_world\entities\firearms\boltactionrifle_base.c:5`, `P:\scripts\4_world\entities\firearms\pistol_base.c:149`). Before writing a class name, a key or a selection name, Grep for it in vanilla (`P:\scripts\4_world\entities\firearms\`, `P:\DZ\weapons\`) or in the cited reference, and keep the marks the references use. Tie every new weapon lesson to a real file with `path:line`, never to memory.

Until 1.29 the pistol stable states were built with `PistolAnimState` constants (reported for 1.29 `Pistol_Base.c:203-212`; not on `P:\`). Since 1.30 `InitStateMachine` passes `GetDischargedPistolAnimState()`, `GetChargedPistolAnimState()`, `GetOpenPistolAnimState()` and `GetJammedPistolAnimState()` (`P:\scripts\4_world\entities\firearms\pistol_base.c:203-212`). Override those getters on an unusual pistol, as the Luger does (`P:\scripts\4_world\entities\firearms\pistol\luger.c:8-21`: charged returns `DEFAULT`, jammed returns `CLOSED_CHARGED`). Do not duplicate the `Pistol_CLO_*` state classes.

## Classifying ammo on the server

A system that must treat cartridges by class (pistol, intermediate, full power, shell, arrow) without a list of class names, such as a turret, per class ballistics or loot logic that must also work for modded weapons, reads `iconCartridge` from the ammo pile's `CfgMagazines` class. The full recipe, with the vanilla lines, the five vanilla piles that resolve to `None`, and the rule to gate on `IsAmmoPile()`, is in `skills/_shared/weapons/magazines-ammo.md`, "Classifying a cartridge from script". It came out of a turret built for the author's LFPowerGrid mod (2026-08-13).

## DayZ 1.30

What changed, what breaks, and what to change in a mod. Citations and literal blocks: `references/dayz-1-30-weapons.md`. Recoil curves and the Luger and Lee-Enfield bone remaps: `references/bone-remap.md`, `references/cfgweapons-contract.md`.

What changed:

- Four firearm scripts (`SCARL_Base : SCARH_Base`, `Luger_Base`, `LeeEnfield_Base`, `MP18_Base`) plus `P1907_Bayonet` and three magazine script classes. The Luger and Lee-Enfield get their own `AddItemBoneRemap` arrays. Their hand animation files are in the data on `P:\`; their models and config classes are not (W-STAGING1).
- Pistol animation states are virtual getters on `Pistol_Base` (`pistol_base.c:611-629`, used at `:203-212`).
- `OpenBolt_Base.SetActions()` adds `FirearmActionDetachMagazine` (`openbolt_base.c:388`).
- `Weapon_Base.EEItemDetached` calls `ValidateAndRepair()` when the detached item is a magazine (`weapon_base.c:1121`).
- Explosion effects: `ExplosiveEffectData` and `AmmoTypesAPI.GetExplosiveEffectData(string, string)` replace `GetExplosionParticleID`. `ExplosivesBase.SetParticleExplosion` and `AddExplosionEffectForSurface` are marked `[Obsolete("1.30: Handled in AmmoTypes instead")]`.
- The attach magazine action requires `TestAttachMagazine(...)` (`firearmactionattachmagazine.c:256`).
- The chamber helper uses `LocalAcquireCartridgeEx` (`weapon_utils.c:9`).

What breaks in a weapon mod written for 1.29:

1. A compile error if it still calls `AmmoTypesAPI.GetExplosionParticleID`.
2. Reloading never starts if its `TestAttachMagazine` is too strict or wrong for a custom muzzle.
3. Workarounds that let an open bolt gun drop its magazine now fight the new `AddAction(FirearmActionDetachMagazine)`.
4. Spawning `SCARL`, `Luger`, `LeeEnfield`, `MP18`, `Mag_Luger_8Rnd` or `Mag_MP18_Drum32Rnd` from `types.xml` or a trader fails on data that has no config class for them. The official 1.30 modding changelog also names `SoundHitType` and `GetSoundHitType()`; neither exists in the scripts on `P:\`, so do not call them.

Checklist for moving a mod to 1.30:

- [ ] Replace explosion particle lookups with `GetExplosiveEffectData(ammoType, surfaceType)`.
- [ ] Drop `SetParticleExplosion` and script side surface to particle maps; set `particle` on the `CfgAmmo` class.
- [ ] Unusual pistols: override `Get*PistolAnimState()` and keep the stock pistol state machine.
- [ ] Check `TestAttachMagazine` for custom magazine and bolt states.
- [ ] Use `LocalAcquireCartridgeEx` in custom chamber helpers.
- [ ] Compare against a model that ships in the data you have; for the four new weapons that may be another weapon.
- [ ] Do not add the four new class names to `types.xml` unless the server's data has their config classes.

## On Linux

Everything above is the Windows workflow and stays valid there. The shared Linux and Proton notes (`skills/_shared/linux-proton.md`, with the scripts `skills/_shared/scripts/dayz-mod-pack.sh` and `skills/_shared/scripts/dayz-proton.sh`) carry the Proton setup, the measured tool matrix and the pitfalls; this section only says what changes for firearms. None of it was run for Agentic-Z.

- Pack, sign and binarize with dayzmake 1.0.0 or later, bzed's DayZ fork of armake2 (https://github.com/bzed/dayzmake), pinned to `v1.0.0` (the release binary `dayzmake-v1.0.0-debian-trixie-x86_64.tar.gz` from https://github.com/bzed/dayzmake/releases/tag/v1.0.0, or `cargo install --git https://github.com/bzed/dayzmake --tag v1.0.0`): `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. Upstream armake2 is no substitute: it is built for Arma, its V3 file hash leaves out `*.c` files (dayzmake v1.0.0 includes them), and it lacks the DayZ only functions dayzmake keeps adding. `dayz-mod-pack.sh` wraps these (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`); the PBO build notes for Linux (`skills/dayz-build-pbo/references/dayzmake-linux.md`) describe it. The author's 2026-11-03 comparison of a textured cube against BI binarize from a `P:` root matched byte for byte (fork commit `7dcb3cf`, then still named armake2; `v1.0.0` contains it); that is not an in-game check of the binarized model.
- `P:\` is a plain folder mapped by `dayz-proton.sh init <dir>`; a `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...`.
- Object Builder and TexView run under Proton (`dayz-proton.sh gui ObjectBuilder <p3d>`, `gui TexView <paa>`). Object Builder opened and showed a model; editing in it was not tried. The offline Python checks under `scripts/tools/` (py3d, dayz-model-preflight, dayz-3d-viewer) run natively.
- In-game checks: the Linux notes of the `dayz-test-ingame` skill (`skills/dayz-test-ingame/references/linux.md`).

## Building, testing and publishing

When the work has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons[]`, the PBO and its signature, a start on a local server), use `/dayz-lint`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-gate`, and the dayz-mod-dev skill for the full loop.
