# Animation instances and templates

How `.asi` instance files map animation names to clips, which player instances vanilla ships, the weapon state names and what a weapon states clip stores, the `ikpose_` keys, and the named groups of a 1.30 `.ast` template. The graph itself is in `anim-graphs.md`; the 1.30 syntax and porting are in `anim-graph-format-1-30.md`.

## Instance files

An instance maps `Group.Column.Animation` names to clips and inherits the rest from its parents. The file is one `AnimSetInstanceSource` block; from `P:\DZ\anims\workspaces\player\player_main\player_main_rifle.asi:1` to `:9`:

```cpp
AnimSetInstanceSource {
 Template "{F0C651DE8E24A5DE}DZ/anims/workspaces/player/player_main/player_main.ast"
 ParentTemplates {
  "{0F5E6205A5E823C3}DZ/anims/workspaces/player/player_main/player_main.asi"
 }
 Lines {
  AnimSetInstanceSource_Line "ActionContinuous.BlowFireplaceCro.In" {
   Resource "{DACEA97B45382D18}DZ/anims/anm/player/actions/items/p_rfl_cro_blow_fireplace_in.anm"
  }
```

- `Template` names the `.ast` that says which animation names exist.
- `ParentTemplates` names the instance to inherit from; `player_main.asi` is the root of the player chain.
- `Lines` holds the mappings. A child lists only what it changes.

The 1.29 form was `$animsetinstance { #template "..." #nparents 1 #parent "..." $animations { "Name" "{GUID}path.anm" ... } }`.

## The player's instances

In `P:\DZ\anims\workspaces\player\player_main\`:

| Instance | For |
|---|---|
| `player_main.asi` | The base, parent of all. |
| `player_main_1h.asi`, `player_main_1h_restrained.asi` | One handed items, and the same while restrained. |
| `player_main_2h.asi` | Two handed items. |
| `player_main_heavy.asi` | Heavy items: wheel, door, barrel. |
| `player_main_pistol.asi`, `player_main_rifle.asi` | Pistols and rifles. |
| `player_main_bow.asi` | The bow, whose mechanic is reported unfinished (not checked on `P:\`). |
| `player_main_surrender.asi` | Hands up. |
| `menu_rifle.asi` | The rifle in the menu preview. |
| `props\` | 41 instances, one per prop (`player_main_2h_pot.asi` and others). |
| `weapons\` | 86 instances, one per weapon (`player_main_akm.asi`, `player_main_1911.asi` and others). |

For a custom item or weapon, inherit from the closest vanilla instance and list only your own lines. Never rewrite a whole instance: inherited locomotion and additive lines break easily when overwritten. Watch states whose clip has very few frames; a clip that ends on its second frame leaves the engine showing two frames (practice, not checked on `P:\`).

## Weapon state names

Weapon instances use `WeaponOperations.<stance>.<state>`. The stance key is the body stance: `ErcRas` is erect with the weapon raised, `PneRas` prone and raised. `Ras` means raised, not "rail accessory system" as some guides have it: the idle state `IdleRas` starts on `Raised && MovementSpeed == 0` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:6620` to `:6623`), and the 1911 has the same states under `ErcRas` and `PneRas`.

From the 1911 (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_1911.asi`):

| Line | Maps |
|---|---|
| `WeaponOperations.ErcRas.FireCocked` (`:19`) | The clip for firing while cocked and empty. |
| `WeaponOperations.ErcRas.ReloadMagazineDetach` (`:52`) | The clip named `..._reload_mag_remove_...`. |

| Tutorials call it | Real name | Note |
|---|---|---|
| "weapon cocked" | `FireCocked` | The graph plays it from the source `WeaponOperations.FireCocked` (`P:\DZ\anims\workspaces\player\player_main\combat.agf:1078` to `:1080`) when `GetCommandI(CMD_WeaponFire) == 2` (`:1123`). |
| "mag remove" | `ReloadMagazineDetach` | The clip's file name says `mag_remove`; the state does not. The clip only draws the hand moving away; inventory script decides when the magazine really leaves. |
| "bullet in chamber" | No such state | Chambering is the commands `CMD_Reload_Chambering` and `CMD_Reload_ChamberingFast`. |

## A weapon states clip stores 2 to 4 frames

The binary clips store a frame count and per channel key counts for each bone in their `HEAD` chunk; that is where these numbers were read, since the clips are not text. The intent when keying is three frames, closed, open and jammed, one per start state. Workbench drops consecutive keys that are nearly the same, so across the 50 `w_*_states.anm` clips in `P:\DZ\anims\anm\player\reloads\<weapon>\` each stores 2, 3 or 4 frames (24 hold 2, 19 hold 3, 7 hold 4), and no channel holds more keys than that. `w_akm_states.anm` holds 2 distinct frames, between which `Weapon_Bolt` slides and `Weapon_Bullet` ejects.

All player weapon reload, fire, jam, state and IK pose clips run at 30 frames per second, with a frame count of the last key index plus one. The AKM frame budget is in `weapon-anim-testing.md`.

## The `ikpose_` keys

`ikpose_chainoffset`, `ikpose_weaponoffset`, `ikpose_secchainoffset`, `ikpose_chainmiddledir`, `ikpose_chainmiddlediro`, `ikpose_secchainmiddledir` and `ikpose_secchainmiddlediro` are settings of the weapon IK node in the graph (`AnimSrcNodeWeaponIk`, `P:\DZ\anims\workspaces\player\player_main\combat.agf:5`, the keys at `:29` to `:35`). They are not in the template, the workspace, `config.cpp` or `model.cfg`. They say which bone plays which IK role, for example `ikpose_weaponoffset = RightHand_Dummy` and `ikpose_secchainoffset = LeftHandIKTarget`. Community guides leave out the two `...diro` keys. In the 1.29 graph files the block occurs 14 times across six files, the same each time (not checked on a 1.30 unpack).

## Template files (`.ast`): every group is named

A 1.30 template is an `AnimSetTemplateSource` whose groups each carry a `Name` (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1216` to `:1219`):

```cpp
  AnimSetTemplateSource_AnimationGroup "{694EE03ABF952F04}" {
   Name "WeaponOperations"
   Animations {
    "ChamberingBulletL"
```

The 1.29 format allowed a group with no name (`#ngroupnames 0`); the 1.30 changelog says the unnamed default group was removed. Vanilla renamed its unnamed groups to `Default` in the infected and wolf templates (`P:\DZ\anims\workspaces\infected\infected_main\infected.ast:76`; `P:\DZ\animals\animations\!graph_files\wolf\wolf.ast:4`), to `Facial` in the player template (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:441`), and to `.unnamed` only in the sample templates (`P:\DZ\anims\workspaces\samples\zombie_commonsamples\zow.ast:4`).

The rest of the template grammar is not documented. Treat a vanilla `.ast` as the schema and copy from the closest one. How a 1.29 template and instance map onto 1.30 keys is in `anim-graph-format-1-30.md`, "Template and instance: every key has three parts".
