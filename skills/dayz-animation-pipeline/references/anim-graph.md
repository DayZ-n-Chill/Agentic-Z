# Animation graphs: files, commands, variables, instances and the 1.30 format

The animation graph is the layer that drives characters and creatures: state machines, transitions, commands sent by the engine, AI or script, variables that steer blending, and the instance files that map state names to clips. Everything here except the clips is text you can read on `P:\`.

The vanilla data on `P:\` is the 1.30 format. Where a line describes the 1.29 format it says so; those lines cannot be checked on a 1.30 unpack and are kept as the source pack recorded them.

## Where the files are

| What | Path on `P:\` | Format |
|---|---|---|
| Player master graph | `P:\DZ\anims\workspaces\player\player_main\player_main.agr` | Text. `AnimSrcGraph`: variables, commands, and the list of sub-graphs at :1587 (`GraphFilesResourceNames`). |
| Player sub-graphs | `locomotion.agf`, `combat.agf`, `weapons.agf`, `gestures.agf`, `vehicles.agf`, `actions.agf`, `master.agf`, `tests.agf` in the same folder | Text. `AnimSrcGraphFile`. In 1.29 these were `.agr` files, also text, in the older `$AnimGraph 7` format. |
| Player template | `P:\DZ\anims\workspaces\player\player_main\player_main.ast` | Text. `AnimSetTemplateSource`: which animation names exist, in named groups. |
| Player instances | `player_main.asi` and the other `.asi` files in the same folder, `props\`, `weapons\` | Text. `AnimSetInstanceSource`: animation name to clip. |
| Player workspace | `P:\DZ\anims\workspaces\player\player_main\player_main.aw` | Text. Names the template, instances, graph, event table and sync table. |
| Event and sync tables | `P:\DZ\anims\workspaces\player\player_eventtable.ae`, `player_synctable.asy` | Text. |
| Infected graph | `P:\DZ\anims\workspaces\infected\infected_main\` (`infected.agr`, `locomotion.agf`, `combat.agf`, `interaction.agf`, `infected.ast`, `infected_main.asi`) | Text. |
| Animal graphs | `P:\DZ\animals\animations\!graph_files\` (`wolf`, `herbivores`, `ambientlife`), and the bear under `P:\DZ\animals_bliss\animations\!graph_files\bear\` | Text. |
| Skeleton bone lists | `P:\DZ\anims\cfg\skeletons.anim.xml` | XML. |
| Clips | `P:\DZ\anims\anm\` | Binary `.anm`. Leave them to DayZATool and Workbench. |

A creature class names its graph in `config.cpp`: the infected set `graphname`, `defaultinstance` and `startnode` in `class enfanimsys` (`P:\DZ\characters\zombies\config.cpp:71` to `:78`).

## Commands

Command names are exact: the prefix `CMD_` and then the name as the graph declares it. Tutorials and video transcripts write "cmd death" or "cmd_death"; use the declared name.

### Animals

Declared in each animal master graph, for example the wolf (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:63` to `:84`): `CMD_Attack`, `CMD_AttackSuccess`, `CMD_Death`, `CMD_JumpType`, `CMD_LookAt`, `CMD_AnimCallBack`, `CMD_Hit`, `CMD_LookAtXChange`. The herbivore graph declares the same eight (`P:\DZ\animals\animations\!graph_files\herbivores\herbivores_graph.agr:63` to `:84`, starting with `CMD_Death`).

| Command | Starts |
|---|---|
| `CMD_Death` | The death state. |
| `CMD_LookAt`, `CMD_LookAtXChange` | Head tracking toward a target, and its change of axis. |
| `CMD_Attack` | The attack state. |
| `CMD_AttackSuccess` | The attack connected, so damage applies. There is no `CMD_Success`. |
| `CMD_Hit` | Being hit. |
| `CMD_AnimCallBack` | A general event callback. |

### Infected

`CMD_HIT_LIGHT`, `CMD_HIT_HEAVY`, `CMD_DEATH`, `CMD_ATTACK`, `CMD_TURN`, `CMD_VAULT`, `CMD_CRAWL`, `CMD_NODEATH` (`P:\DZ\anims\workspaces\infected\infected_main\infected.agr:46` to `:67`). Note the upper case names: they differ from the animal ones.

### Player

Declared in the `Commands` block of the master graph, which runs from `P:\DZ\anims\workspaces\player\player_main\player_main.agr:211` and holds 69 commands. The ones weapon and movement work meets:

| Command | Line | Starts |
|---|---|---|
| `CMD_Action` | :218 | An action animation. |
| `CMD_Jump`, `CMD_Fall`, `CMD_Land` | :245, :257, :263 | Jump, fall and landing. |
| `CMD_Reload_Magazine` | :269 | A magazine reload. |
| `CMD_Reload_BoltAction` | :272 | A bolt action reload. |
| `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast` | :275, :278 | Chambering a round, and its fast form. |
| `CMD_Reload_Clip` | :284 | A clip reload. |
| `CMD_Death` | :287 | Death. |
| `CMD_Modifier_Additive` | :338 | The sickness modifiers (see "Reload is not additive"). |
| `CMD_Vehicle_GetIn` | :341 | Boarding a vehicle; its value picks the side. |
| `CMD_WeaponFire` | :365 | Firing; its value picks the fire state (2 is firing while cocked and empty, `P:\DZ\anims\workspaces\player\player_main\combat.agf:1123`). |

Every command in every vanilla 1.30 master graph is `Synchronized 1`: 120 commands in 10 master graphs, none with 0.

### Action command constants added in 1.30

Script names action animations through `DayZPlayerConstants`. The ones 1.30 added (`P:\scripts\3_game\dayzplayer.c`):

| Constant | Value | Stances, from the source comment | Line |
|---|---|---|---|
| `CMD_ACTIONMOD_COMBINATIONLOCK` | 256 | erect, crouch | :766 |
| `CMD_ACTIONMOD_WASHFACE` | 257 | | :767 |
| `CMD_ACTIONFB_COMBINATIONLOCK` | 256 | prone | :889 |
| `CMD_ACTIONFB_WASHFACEPOND` | 257 | crouch | :890 |
| `CMD_ACTIONFB_BUILDROPELADDER` | 258 | crouch | :891 |
| `CMD_ACTIONFB_BRICKSTACK` | 259 | erect, crouch | :892 |
| `CMD_ACTIONFB_BRICKTROWEL` | 260 | erect, crouch | :893 |
| `CMD_ACTIONFB_MIX_MORTAR` | 261 | crouch | :894 |
| `CMD_ACTIONFB_DRINKWELL_BUCKET` | 262 | erect | :895 |
| `CMD_ACTIONFB_SHARPEN` | 263 | crouch | :896 |
| `CMD_ACTIONFB_WASHFACEWELL` | 264 | erect | :897 |
| `CMD_ACTIONFB_WETCLOTH` | 265 | crouch | :898 |
| `CMD_ACTIONFB_WETCLOTHWELL` | 266 | erect | :899 |

The source groups the two kinds under its own comments: `ACTIONMOD` constants under "modifier (differential animation)" (`dayzplayer.c:740`) and `ACTIONFB` constants under "fb (full body)" (`dayzplayer.c:810`).

## Variables

Variables are declared in the master graph's `ControlTemplate`, each with a default, a minimum and a maximum:

```
 ControlTemplate AnimSrcGCT "{6930A8DF8B23ACB9}" {
  Variables {
   AnimSrcGCTVarFloat speed {
    DefaultValue 0
    MinValue 0
    MaxValue 5
   }
   AnimSrcGCTVarFloat turn {
    DefaultValue 0
    MinValue -180
    MaxValue 180
   }
```

That is the wolf (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:4` to `:15`). All four animal graphs declare `speed`, `turn`, `behaviorAction`, `alertLevel`, `lookXAngle`, `lookYAngle`, `SlopeAngleX`, `SlopeAngleZ`, `InjuryLevel`, `behaviorSlotID` and `AnimalType` (`wolf_graph.agr:6` to `:56`).

- `speed` (0 to 5) steers the locomotion blend.
- `SlopeAngleX` and `SlopeAngleZ` (−90 to 90, `wolf_graph.agr:36`, `:41`) are filled by the engine and drive terrain alignment.
- There is no `swimming` variable in any animal graph. In the player graph swimming is a tag, `TagSwimming` on the `SwimmingMaster` state machine (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:7700` to `:7703`), not a number. A tutorial that treats `swimming` as a creature variable is inventing it.

The player's variables are in the same place: `MovementSpeed` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:6`), `MovementDirection` (:11), `Stance` (:16), `TurnAmount` (:21), `Look` (:26), `LookDirX` (:34), `Raised` (:49), `Lean` (:88), `VehicleType` (:108) and the rest. Driving them from a scripted command: `scripted-command-locomotion.md`.

In 1.29 the same declarations were lines such as `#Var speed float 0.0 0.0 5.0 ""`.

## Terrain alignment

There is no special terrain node. It is a procedural transform that turns bones by the slope variable converted from degrees to radians (0.01745329 is π/180):

```
    AnimSrcNodeProcTransform AlignToTerrain_Rot {
     EditorPos -1 -4.7
     Child "Master_SM"
     Expression "SlopeAngleX  * 0.01745329251994329576923690768489"
     Bones {
      AnimSrcNodeProcTrBoneItem "{6930A8DF8B23795C}" {
       Bone "scene_root"
       Axis X
       Space Model
       Op Rotate
       Amount 1
      }
```

That is the wolf's `AlignToTerrain_Rot` node (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:5` to `:16`).

The herbivores have one node per body type, `TerrainRot_BoarAndPig`, `TerrainRot_CowAndBull`, `TerrainRot_Deers` and `TerrainRot_SheepAndGoat`, with the slope clamped to ±40 degrees first (`P:\DZ\animals\animations\!graph_files\herbivores\herbivores_maingraph.agf:2407`, `:2449`, `:2505`, `:2547`; the expression at `:2410`).

For a new creature copy the node from the vanilla animal closest in build: a large quadruped from the cow, a medium one from the boar, a small one from the sheep. In 1.29 the same node was an `AnimNodeRot` in the `.agr`.

## Instance files (`.asi`)

An instance maps `Group.Column.Animation` names to clips and inherits the rest from its parents:

```
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

(`P:\DZ\anims\workspaces\player\player_main\player_main_rifle.asi:1` to `:9`.)

- `Template` names the `.ast` that says which animation names exist.
- `ParentTemplates` names the instance to inherit from. `player_main.asi` is the root of the player chain.
- `Lines` holds the mappings. A child lists only what it changes.

The 1.29 form of the same file was `$animsetinstance { #template "..." #nparents 1 #parent "..." $animations { "Name" "{GUID}path.anm" ... } }`.

### The player's instances

In `P:\DZ\anims\workspaces\player\player_main\`:

| Instance | For |
|---|---|
| `player_main.asi` | The base; parent of all. |
| `player_main_1h.asi`, `player_main_1h_restrained.asi` | One handed items; the same while restrained. |
| `player_main_2h.asi` | Two handed items. |
| `player_main_heavy.asi` | Heavy items: wheel, door, barrel. |
| `player_main_pistol.asi`, `player_main_rifle.asi` | Pistols; rifles. |
| `player_main_bow.asi` | The bow. Reported unfinished by the workshop videos the source pack drew on. |
| `player_main_surrender.asi` | Hands up. |
| `menu_rifle.asi` | The rifle in the menu preview. |
| `props\` | 41 instances, one per prop (`player_main_2h_pot.asi` and others). |
| `weapons\` | 86 instances, one per weapon (`player_main_akm.asi`, `player_main_1911.asi` and others). |

For a custom item or weapon, inherit from the closest vanilla instance and list only your own lines. Do not rewrite a whole instance.

### Weapon state names

Weapon instances use `WeaponOperations.<stance>.<state>`. The stance key is the body stance: `ErcRas` is erect with the weapon raised, `PneRas` prone and raised. The source pack read `Ras` as "rail accessory system"; the graph shows it means raised, since the idle state `IdleRas` starts on `Raised && MovementSpeed == 0` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:6620` to `:6623`) and the 1911 has the same states under `ErcRas` and `PneRas`.

From the 1911 (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_1911.asi`):

| Line | Maps |
|---|---|
| `WeaponOperations.ErcRas.FireCocked` (:19) | The clip for firing while cocked and empty. |
| `WeaponOperations.ErcRas.ReloadMagazineDetach` (:52) | The clip named `..._reload_mag_remove_...`. |

| Tutorials call it | Real name | Note |
|---|---|---|
| "weapon cocked" | `FireCocked` | The graph plays it from the source `WeaponOperations.FireCocked` (`P:\DZ\anims\workspaces\player\player_main\combat.agf:1078` to `:1080`) when `GetCommandI(CMD_WeaponFire) == 2` (`:1123`). |
| "mag remove" | `ReloadMagazineDetach` | The clip's file name says `mag_remove`; the state does not. The clip only draws the hand moving away; inventory script decides when the magazine really leaves. |
| "bullet in chamber" | No such state | Chambering is the commands `CMD_Reload_Chambering` and `CMD_Reload_ChamberingFast`. |

### A weapon states clip has 2 to 4 keys per channel

Reported by the source pack from the binary clips (not checked on `P:\`). The intent when authoring is three frames, closed, open and jammed, one per start state. Workbench trims consecutive keys that are nearly the same, so across 47 vanilla `w_*_states.anm` the stored key count per channel is 2, 3 or 4. `w_akm_states.anm` holds 2 distinct frames at 30 frames per second (`Weapon_Bolt` slides between them and `Weapon_Bullet` ejects). All player weapon reload, fire, jam, state and IK pose clips are at 30 frames per second, with a frame count of the last key index plus one. The AKM frame budget is in `weapon-anim-blender-complete.md`.

### The `ikpose_` keys are in the graph's weapon IK node

The keys `ikpose_chainoffset`, `ikpose_weaponoffset`, `ikpose_secchainoffset`, `ikpose_chainmiddledir`, `ikpose_chainmiddlediro`, `ikpose_secchainmiddledir` and `ikpose_secchainmiddlediro` are settings of the weapon IK node in the graph (`AnimSrcNodeWeaponIk`, `P:\DZ\anims\workspaces\player\player_main\combat.agf:5`, the keys at `:29` to `:35`). They are not in the template, the workspace, `config.cpp` or `model.cfg`. They name which bone plays which IK role, for example `ikpose_weaponoffset = RightHand_Dummy` and `ikpose_secchainoffset = LeftHandIKTarget`. Community sources leave out the two `...diro` keys. The source pack counted the block 14 times across six 1.29 graph files, identical each time.

## Template files (`.ast`): every group is named

A 1.30 template is an `AnimSetTemplateSource` whose groups each carry a `Name`:

```
  AnimSetTemplateSource_AnimationGroup "{694EE03ABF952F04}" {
   Name "WeaponOperations"
   Animations {
    "ChamberingBulletL"
```

(`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1216` to `:1219`.)

The 1.29 format allowed a group with no name (`#ngroupnames 0`). The 1.30 changelog says the default unnamed group was removed. Vanilla renamed its unnamed groups: to `Default` in the infected and wolf templates (`P:\DZ\anims\workspaces\infected\infected_main\infected.ast:76`, `P:\DZ\animals\animations\!graph_files\wolf\wolf.ast:4`), to `Facial` in the player template (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:441`), and to `.unnamed` only in the sample templates (`P:\DZ\anims\workspaces\samples\zombie_commonsamples\zow.ast:4`).

The template grammar beyond this is not documented. Treat a vanilla `.ast` as the schema and copy from the closest one.

## The vehicle graph, as a tour of the 1.30 node types

`P:\DZ\anims\workspaces\player\player_main\vehicles.agf` (3654 lines) is a good file to learn the format from.

```
AnimSrcNodeBlendT MotorBikeB {
 EditorPos 4 -18.3
 BlendTime "0.3"
 BlendFn S
 Condition "VehicleType == 10 || VehicleType == 11"
 Child0 "VehicleSTM"
 Child1 "MotorBikeSTM"
```

(`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1564` to `:1572`.)

| Node type | What it does | First example |
|---|---|---|
| `AnimSrcNodeBlendN` | Blends several children by thresholds on a weight (`BlendWeight "VehicleSpeed"`, `Thresholds`). | `vehicles.agf:5` |
| `AnimSrcNodeBlendT` | Switches between two children on a condition over a blend time. | `vehicles.agf:1564` |
| `AnimSrcNodeBlend` | Blends two children by a formula (`MotoYIntertiaB`). | `vehicles.agf:1556` |
| `AnimSrcNodePose` | Reads one pose out of a clip at a time given by an expression. | `vehicles.agf:47` |
| `AnimSrcNodeStateMachine` | A state machine: `states` and `transitions` (`MotorBikeSTM`). | `vehicles.agf:1582` |
| `AnimSrcNodeIK2Target`, `AnimSrcNodeIK2` | Two bone IK that pins the driver's hands to the steering. | `vehicles.agf:17`, `:31` |
| `AnimSrcNodeSourceSync` | Plays a clip on a sync line. | `vehicles.agf:69` |

`MotorBikeSTM` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1582` to `:1751`) has the rider states `Idle`, `GetIn_L`, `GetIn_R`, `GetOut_L`, `GetOut_R`, `JumpOut_L`, `JumpOut_R`, `Death` and `GettingInDeath`. The get in states choose a side from the command's value: `GetIn_L` on `GetCommandI(CMD_Vehicle_GetIn) == 0` (`vehicles.agf:1618`), `GetIn_R` on 1 (`:1598`).

The motorbike is new in 1.30. Its animations are columns of the template (`Jawa_05` and `Jawa_Bitrak`, `P:\DZ\anims\workspaces\player\player_main\player_main.ast:1119`, `:1120`) with lines in the base instance (`Vehicle.Jawa_05.AccelerationSpine` at `P:\DZ\anims\workspaces\player\player_main\player_main.asi:5088`). A mod vehicle can read or borrow from this state machine; changing it means shipping vanilla path graph files (`tooling-and-walls.md`).

### Tags

A state or node carries tags in a `Tags { "Name" }` block, and conditions test them. In the motorbike machine `GetIn_L` and `GetIn_R` carry `TagVehicleGetIn` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1614`, `:1594`) and the get out and jump out states carry `TagVehicleGetOut` (`:1604`, `:1624`, `:1634`, `:1651`). The death transition waits for boarding to finish: `Condition "IsCommand(CMD_Death) && !IsTag(\"TagVehicleGetIn\")"` (`:1719`).

Script can read tags since 1.30: `BindTag(string pTagName)` and `IsTag(TAnimGraphTag iTag)` on `HumanAnimInterface` (`P:\scripts\3_game\human.c:318`, `:319`). A possible use, not found in any vanilla script: keep the handle from `BindTag("TagVehicleGetIn")` and poll `IsTag` on the fixed tick to line gameplay up with an animation phase.

## 1.29 and 1.30: both text, different syntax

The 1.30 format is not "text instead of binary". The source pack checked the 1.29 files: `player_main.agr` opens with `$AnimGraph 7 {`, lists eight sub-graphs as `.agr` files, and none of the nine files holds a NUL byte. What changed is the syntax. 1.29 writes a node as positional fields:

```
$Node AnimNodeGroupSelect {
    "Boat_01ActionG" "" "VehicleTalkingT" "VehicleActions" "Boat_01"
```

and 1.30 writes named ones:

```
AnimSrcNodeGroupSelect Jawa_BitrakActionG {
 EditorPos 27.6 -50
 Child "VehicleTalkingT"
 Group "VehicleActions"
 Column "Jawa_Bitrak"
}
```

(`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1381` to `:1386`.) A line diff across the two formats is noise; compare parsed nodes, variables and commands. Bohemia said the same when 1.30 Experimental shipped: in 1.29 a graph mod could be compared with vanilla in a text editor, and for 1.30 graph mods must redo their changes from scratch, with new limits such as the number of groups.

A 1.30 unpack made over a 1.29 one leaves the old `combat.agr`, `locomotion.agr` and the rest next to the new files. They are stale; the master graph lists only the `.agf` files (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`).

### A measured instance of that warning

Measured by the source pack (2026-09-24, dedicated server, DayZ 1.30.164014 Experimental). The Workshop mod Survivor Animations (2918418331) replaces the player graph; its build of 2026-07-20 predates 1.30. With it loaded the server crashed at character creation (`CreateCharacter`, a native fault): twice with a dependent addon and once with only that mod and a vanilla mission.

- Before building on a third party graph mod on a newer game version, load it alone with a vanilla mission and check a player can join.
- With a native fault under third party mods, that single mod run is the cheapest way to split "theirs" from "ours".
- Read such a mod's vehicle animation types through a run time `ConfigIsExisting("CfgPatches <Mod>")` check, never `#ifdef`.

## Which changes collide

A mod that replaces a graph file (the player's `player_main` graph, as Expansion's animation addon and Survivor Animations do, or a creature's) collides with any other mod replacing the same graph. Whether two graph replacements can coexist on 1.30 has not been measured.

A custom weapon or item animation does not have to replace anything. It reaches the engine through three layers, none of which edits the graph:

1. The clip: `.txa` compiled to `.anm` in Workbench.
2. A per item instance: a child `.asi` whose lines map `WeaponOperations.<stance>.<state>` to the mod's clips, with `ParentTemplates` pointing at a vanilla instance (for a rifle, `player_main_rifle.asi`, which inherits `player_main.asi`).
3. Script: `AddItemInHandsProfileIK(itemClass, instance, behaviour, ikPose, weaponStates)` binds the item class to the instance, an IK pose and a weapon states clip (`P:\scripts\3_game\dayzplayer.c:243`), and `AddItemBoneRemap(itemClass, pairs)` maps the weapon's part selections to the player's `Weapon_` bones (`:252`). Vanilla binds every weapon this way, for example `AKM_Base` to `weapons/player_main_akm.asi` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:412`).

Because the binding is per item class, each mod registers its own items and several such mods load together. When the plan is a custom weapon animation, do not warn about graph collisions. That the vanilla structure allows it is checked above; that a mod's own instance and clips play this way is the source pack's in-game result (`weapon-anim-blender-complete.md`).

## Reload is not additive

Some tutorials say a reload is an additive animation, torso and arms only, with another layer handling the rest. Vanilla does not show that:

- `CMD_Modifier_Additive` drives the sickness modifiers. Its values start `SickSneezeStanceSTM` (0), `SickCoughStanceSTM` (1) and `SickColdStanceSTM` (2) (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:5482` to `:5509`).
- Reloads use their own commands, with nothing additive about them: `CMD_Reload_Magazine`, `CMD_Reload_BoltAction`, `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`, `CMD_Reload_Clip` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:269` to `:284`).

The tutorial is probably describing how the clip is authored in Blender (animate torso and arms, leave the legs), not a run time layer. For a custom reload, find the vanilla weapon closest in feel and copy how its graph enters and leaves the state.

## Opening the player graph in the Workbench animation editor

- **1.29.** The compiled workspace `player_main.aw` had a line `#eventtable "{3037156104937B91}DZ/anims/workspaces/player/Player_EventTable.ae"` (line 137 there), which the source workspace of Bohemia's animation sample did not. Tutorials say to delete that line so the editor opens the graph; Workbench bound the event table again on export.
- **1.30.** The workspace names its event table directly: `EventTable "{3037156104937B91}DZ/anims/workspaces/player/Player_EventTable.ae"` (`P:\DZ\anims\workspaces\player\player_main\player_main.aw:15`). Per the 1.30 changelog the editor is the 2021 Enfusion one, with live editing of a running graph, a "Show In Explorer" action and a ragdoll editor for `.ragdoll` files. Whether the delete trick is still needed has not been tried.
- If Workbench fails to load a copied vanilla graph after events were added, fix the event table before touching graph logic.

## Porting a 1.29 `$AnimGraph 7` graph to 1.30

Whether 1.30 still loads a custom graph in the 1.29 format is not tested: the contributor's 1.29 files never loaded on 1.30 because their server failed earlier, on script compilation. Vanilla 1.30 ships its graphs in the new format. To move a custom graph, port it as below, or load the old one first and read the RPT.

The mapping was read off old and new versions of the same vanilla graphs by the source pack: all seven vanilla `$AnimGraph 7` graphs (infected, `player_main`, `player_menu`, wolf, ambient life, herbivores and the bear; `player_inventory` is `$AnimGraph 6`), with the samples on older layouts (`$AnimGraph 3` and `$AnimGraph 2`). The 1.30 side of every example below was opened on `P:\`; the 1.29 side cannot be on a 1.30 unpack. A contributor applied the mapping end to end in a generator of their own project. That port has not been loaded in game.

### File set

The master stays `.agr` and becomes `AnimSrcGraph`. Every sub-graph becomes `.agf` (`AnimSrcGraphFile`). The template becomes `AnimSetTemplateSource` and the instance `AnimSetInstanceSource`. Delete the old sub-graph `.agr` files.

- `config.cpp` `graphname`, `defaultinstance` and `startnode` need no change; vanilla 1.30 configs still use backslash paths there.
- `DefaultRunNode` is optional: of the ten vanilla master graphs only the infected and `player_main` set one (`P:\DZ\anims\workspaces\infected\infected_main\infected.agr:433`). The config's `startnode` picks the entry.
- `AnimSyncTable` is optional too: the player inventory, player menu and ambient life masters have none, while the wolf has one (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:3`).

### Master `.agr`

```
AnimSrcGraph {
 AnimSetTemplate "{GUID}Mod/anims/X_Template.ast"
 ControlTemplate AnimSrcGCT "{GUID}" {
  Variables {
   AnimSrcGCTVarFloat MovementSpeed {      // was  #Var MovementSpeed float 0.0 0.0 3.0 ""
    DefaultValue 0
    MinValue 0
    MaxValue 3
   }
   AnimSrcGCTVarInt IdleState {            // was  #Var IdleState int 0 0 2 ""
    DefaultValue 0
    MinValue 0
    MaxValue 2
   }
   AnimSrcGCTVarBool Look {                // was  #Var Look bool 0 ""   (DefaultValue only)
    DefaultValue 0
   }
  }
  Commands {
   AnimSrcGCTCmd CMD_ATTACK {              // was   CMD_ATTACK -1
    Synchronized 1
   }
  }
 }
 Debug AnimSrcGD "{same GUID as ControlTemplate}" {
 }
 GraphFilesResourceNames {
  "{GUID}Mod/anims/X_Graph.agf"
 }
}
```

Numbers are written bare (`0`, `-180`), not `0.0`.

### Sub-graph `.agf`

`AnimSrcGraphFile { Sheets { AnimSrcGraphSheet <Sheet> { Nodes { ...nodes... } } } }`. A node's name follows its class (`AnimSrcNodeSource Idle_SRC {`); quote the name only when it has spaces or punctuation (`AnimSrcNodeGroupSelect "Swings-Short"`).

| 1.29, positional fields | 1.30, named fields |
|---|---|
| `AnimNodeSource "N" "Tag" "Key" "loop"` | `AnimSrcNodeSource N { Tags { "Tag" } EditorPos x y Source "Key" Looptype Loop }`. `noloop` becomes `Looptype "No Loop"`. Leave `Tags` out when the tag is empty. Drop an empty `$Predictions`; a non-empty one (126 of the 840 source nodes in the seven graphs) becomes a `Predictions { AnimSrcNodePrediction ... }` block, which this table does not map. |
| `AnimNodeBlend "N" "" "Weight" "C0" "C1" F` | `AnimSrcNodeBlend N { EditorPos BlendWeight "Weight" Child0 "C0" Child1 "C1" OptimizeMin F&1 OptimizeMax F>>1&1 }` |
| `AnimNodeBlendT "N" "" "C0" "C1" "On" "Off" "Cond" T "Fn" F` | `AnimSrcNodeBlendT N { EditorPos BlendTime "T" BlendFn Fn TriggerOn "On" TriggerOff "Off" Condition "Cond" Child0 "C0" Child1 "C1" OptimizeMin F&1 OptimizeMax F>>1&1 SelectMainPath F>>2&1 }`. Both triggers are kept. `Fn` is copied as it is: `S` on 154 of the 155 such nodes and `S2` on one (now at `P:\DZ\anims\workspaces\player\player_main\locomotion.agf:13346`). |
| `AnimNodeGroupSelect "N" "Tag" "Child" "Group" "Column"` | `AnimSrcNodeGroupSelect N { Tags { "Tag" } EditorPos Child "Child" Group "Group" Column "Column" }`. Leave `Tags` out when empty. |
| `AnimNodeStateMachine "N" "Tag"` with `$States` and `$Transitions` | `AnimSrcNodeStateMachine N { Tags { "Tag" } EditorPos states { ... } transitions { ... } }`. Leave `transitions` out when there are none. |
| `$State { "S" "Tag" "Child" "Cond" "notime" X }` | `AnimSrcNodeState S { Tags { "Tag" } EditorPos Child "Child" StartCondition "Cond" TimeStorage Inherit IsExit X }`. `realtime` becomes `TimeStorage "Real Time"` and `normtime` becomes `TimeStorage "Normalized Time"` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:92`). |
| `$Transition { "A" "B" "Cond" "D" "T" P "Fn" }` | `AnimSrcNodeTransition "{GUID}" { FromState "A" ToState "B" Duration "D" StartTime "T" Condition "Cond" BlendFn Fn PostEval 1 MotionVecBlend 0x33 0 }`. See the notes under the table. |
| `AnimNodeRot "N" "Tag" "Child" "Expr"` with `$rotitems { $ri { "Bone" "ymr" k } }` | `AnimSrcNodeProcTransform N { Tags { "Tag" } EditorPos Child "Child" Expression "Expr" Bones { AnimSrcNodeProcTrBoneItem "{GUID}" { Bone "Bone" Axis Y Space Model Op Rotate Amount k } } }`. Leave `Tags` out when empty. |

Notes on the transition row:

- `"T"` is the start time. Copy it as it is, number or expression, escaped quotes included, and write `StartTime ""` only when it is empty. Examples in the infected graph: `StartTime "0.2"` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:1380`), `StartTime "0.7"` (`P:\DZ\anims\workspaces\infected\infected_main\interaction.agf:62`), `StartTime "GetLowerTime()"` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:223`), and `StartTime "GetEventTime(\"Attack.Attack Left Light\", \"BlendIn\")"` (`P:\DZ\anims\workspaces\infected\infected_main\combat.agf:113`).
- `P` is a set of flags. 1 gives `PostEval 1` (no `PostEval` line without it). 6 gives `MotionVecBlend 0x30 0` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:1211`) and 24 gives `MotionVecBlend 0x3 0` (with `PostEval 1`, from 25, at `P:\DZ\anims\workspaces\player\player_main\locomotion.agf:11283`) instead of `0x33 0`. The seven graphs use only 0, 1, 6, 7 and 25.
- `Fn` keeps `S` and `S2`, and renames `Lin` to `Linear` (`BlendFn Linear` at `P:\DZ\anims\workspaces\player\player_main\locomotion.agf:13094`) and `SEnd` to `"Ease Out"` (`BlendFn "Ease Out"` at `P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:2472`).
- An empty `"A"` (from any state) gives no `FromState` line.

General rules:

- **Empty strings are written out**, as vanilla does: `StartCondition ""`, `Condition ""`, `TriggerOn ""`, and `StartTime ""` for an empty start time. Only an empty `Tags`, `FromState`, `PostEval 0`, and empty `transitions` and `Predictions` blocks are dropped. In the seven vanilla graphs the start time is set on 495 of 1,251 transition lines, and each of those values occurs as a `StartTime` in the 1.30 files; the 1,105 transition lines that pair one to one with a 1.30 transition all follow the `P` and `Fn` rules above.
- **The second string of a 1.29 node or state line is its tag field**, which 1.30 writes as `Tags { ... }`: `Tags { "TagVaultStart" }` on the infected vault state (`P:\DZ\anims\workspaces\infected\infected_main\interaction.agf:32` to `:35`), and `TagProneBack` on a player group select (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:5065` to `:5068`). The field can hold several tags separated by spaces; 1.30 writes one quoted string per tag, so split on spaces: `"TagWater TagErected"` became `Tags { "TagWater" "TagErected" }` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:1610` to `:1613`). In the seven graphs the field is set on 260 of 1,452 state lines, 3 of 641 group select lines and 1 of 70 rot lines, and empty on every blend (100) and blend T (155) line, so no vanilla pair shows a tag on those two.
- **Node types the table does not cover** also occur in the same graphs: `AnimNodeSourceSync`, `AnimNodeSwitch`, `AnimNodeBlendN`, `AnimNodeQueue` and others.
- **`EditorPos x y`** comes from the 1.29 `$EditorData { #EditorPos x y }` block with x kept and y negated (1.29 `#EditorPos 1.9 11.6000004` became `EditorPos 1.9 -11.6` on the infected `DeathT` node, `P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:1594` to `:1595`). The same holds for all 236 nodes and states whose name occurs once in the three infected sub-graphs.

Where each row is confirmed (by the source pack, on vanilla pairs):

- State, transition, source and group select come from the sample pairs.
- The blend and blend T flag bits hold for every node that pairs by name with its 1.30 version: all 155 blend T nodes, each also keeping its blend function, and 99 of the 100 blend nodes. The hundredth, the player's `VehicleAccelerationB`, was an `AnimNodeBlend` in 1.29 and is an `AnimSrcNodeBlendT` in 1.30 (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:2769`). The infected death node `DeathT` has `OptimizeMin 1`, `OptimizeMax 1` and `SelectMainPath 1` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:1594` to `:1605`), matching the trailing `7` of the same node in 1.29. An old blend flag of `3` is minimum 1, maximum 1.
- The rot code letters are axis (`x`, `y`, `z`), space (`m` model, `l` local) and operation (`r` rotate, `t` translate).
- `Amount` takes the old coefficient unchanged, and the child and the expression are unchanged. This and the letters hold for all 70 rot nodes of the seven graphs against the 1.30 node of the same name, item by item (430 bone items, with the codes `xlr`, `xlt`, `xmr`, `ylr`, `ylt`, `ymr`, `zlr`, `zlt` and `zmr`). The wolf's terrain tilt was converted this way: the expression kept, `Amount 1`.
- Not tested in game: if a procedural twist turns too far or not far enough, `Amount` is the value to change.

### Template and instance: every key has three parts

A 1.29 group type with group names becomes one `AnimSetTemplateSource_AnimationGroup { Name "G" Animations { ... } Columns { ...the old group names... } }`. Keep groups, animations and columns sorted, as vanilla does.

The 1.29 unnamed group (keys like `"Melee0"`) has no 1.30 form. Use the pattern vanilla ships: `Name "Default"` with `Columns { "Normal" }`, instance keys `"Default.Normal.Melee0"`, and graph sources `Source "Default.Normal.Melee0"`.

Two source forms both work in vanilla:

- `"Group.Anim"`, with the column chosen by an enclosing group select: `Source "Attack.Attack Left Heavy"` in the infected graph (`P:\DZ\anims\workspaces\infected\infected_main\combat.agf:7`).
- `"Group.Column.Anim"` written out: `Source "Default.Normal.attack_high"` in the wolf graph (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:49`).

The player's renamed group shows up in its sources as `Source "Facial.FacialHitHeavy"` (`P:\DZ\anims\workspaces\player\player_main\combat.agf:393`).

Instance lines are `AnimSetInstanceSource_Line "G.C.Anim" { Resource "{GUID}path.anm" }` inside `Lines { }`, after `Template "{GUID}path.ast"` and `ParentTemplates { }`.

### GUIDs

Each `{16 hex digits}` prefix is a resource id. Vanilla clip ids did not change from 1.29: the source pack found all 187 clips of the 1.29 infected instance with the same id in 1.30. For your own files and for the ids local to a node (`AnimSrcNodeTransition`, `AnimSrcNodeProcTrBoneItem`, `AnimSrcGCT`), derive them from a stable seed, such as the first 16 hex characters of the SHA-1 of the path or node name, so that generating again gives identical files. Give each resource one id everywhere it appears.

### Packing

As the contributor reports it (not checked here), RaG PBO Builder packs `.agf` as plain text next to the `.agr`, `.ast` and `.asi`. Check this in the built PBO, not the source tree.

## Buffer nodes are gone

The 1.30 changelog removed the `Buffer Save` and `Buffer Use` nodes. The source pack found none in the 1.30 sub-graphs. A custom graph that used them must move to variables or direct state machine transitions.

## What this file does not cover

- The full `.ast` grammar: copy from the closest vanilla template.
- The frame rate of player clips. No text file under the workspaces declares one; the source pack searched every graph, template, workspace and sync file for it. It is probably stored in the binary `.anm` or set by the exporter. The workshop videos report 30 frames per second. Set 30 in the exporter and round trip one short clip before producing a set.
- The insides of `.anm` and `.xob`: DayZATool and Workbench.
- The script side that 1.30 added (instance switching, speed limits, ragdoll calls): `dayz-1-30-animation-changes.md`.
