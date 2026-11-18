# Animation graphs

What the animation graph that drives characters and creatures holds: where its files are, the `CMD_` commands the engine, AI and script send, the variables that steer blending, terrain alignment, tags, and which mod changes collide. Instance and template files are in `anim-instances-and-templates.md`; the 1.30 file format and porting a 1.29 graph are in `anim-graph-format-1-30.md`.

Everything except the clips is text on `P:\`. The vanilla data there is the 1.30 format; lines about 1.29 say so and were read from a 1.29 unpack, so they cannot be checked on a 1.30 one.

## Where the files are

| What | Path on `P:\` | Format |
|---|---|---|
| Player master graph | `P:\DZ\anims\workspaces\player\player_main\player_main.agr` | `AnimSrcGraph`: variables, commands, and the list of sub-graphs at `:1587` (`GraphFilesResourceNames`). |
| Player sub-graphs | `locomotion.agf`, `combat.agf`, `weapons.agf`, `gestures.agf`, `vehicles.agf`, `actions.agf`, `master.agf`, `tests.agf` in the same folder | `AnimSrcGraphFile`. In 1.29 these were `.agr` text files in the older `$AnimGraph 7` syntax. |
| Player template | `P:\DZ\anims\workspaces\player\player_main\player_main.ast` | `AnimSetTemplateSource`: which animation names exist, in named groups. |
| Player instances | `player_main.asi` and the other `.asi` files in the same folder, `props\` and `weapons\` | `AnimSetInstanceSource`: animation name to clip. |
| Player workspace | `P:\DZ\anims\workspaces\player\player_main\player_main.aw` | Names the template, instances, graph, event table and sync table. |
| Event and sync tables | `P:\DZ\anims\workspaces\player\player_eventtable.ae`, `player_synctable.asy` | Text. |
| Infected graph | `P:\DZ\anims\workspaces\infected\infected_main\` (`infected.agr`, `locomotion.agf`, `combat.agf`, `interaction.agf`, `infected.ast`, `infected_main.asi`) | Text. |
| Animal graphs | `P:\DZ\animals\animations\!graph_files\` (`wolf`, `herbivores`, `ambientlife`), and the bear in `P:\DZ\animals_bliss\animations\!graph_files\bear\` | Text. |
| Skeleton bone lists | `P:\DZ\anims\cfg\skeletons.anim.xml` | XML. |
| Clips | `P:\DZ\anims\anm\` | Binary `.anm`; leave them to DayZATool and Workbench. |

A creature class names its graph in `config.cpp`: the infected set `graphname`, `defaultinstance` and `startnode` in `class enfanimsys` (`P:\DZ\characters\zombies\config.cpp:71` to `:78`).

## Commands

A command name is `CMD_` followed by the name exactly as the graph declares it. Tutorials write "cmd death" or "cmd_death"; use the declared name.

Animals: each master graph declares `CMD_Attack`, `CMD_AttackSuccess`, `CMD_Death`, `CMD_JumpType`, `CMD_LookAt`, `CMD_AnimCallBack`, `CMD_Hit` and `CMD_LookAtXChange` (wolf: `P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:63` to `:84`; herbivores the same eight, starting with `CMD_Death`: `P:\DZ\animals\animations\!graph_files\herbivores\herbivores_graph.agr:63` to `:84`).

| Command | Starts |
|---|---|
| `CMD_Death` | The death state. |
| `CMD_LookAt`, `CMD_LookAtXChange` | Head tracking toward a target, and its change of axis. |
| `CMD_Attack` | The attack state. |
| `CMD_AttackSuccess` | The attack connected, so damage applies. There is no `CMD_Success`. |
| `CMD_Hit` | Being hit. |
| `CMD_AnimCallBack` | A general event callback. |

Infected use upper case names that differ from the animals': `CMD_HIT_LIGHT`, `CMD_HIT_HEAVY`, `CMD_DEATH`, `CMD_ATTACK`, `CMD_TURN`, `CMD_VAULT`, `CMD_CRAWL`, `CMD_NODEATH` (`P:\DZ\anims\workspaces\infected\infected_main\infected.agr:46` to `:67`).

The player's `Commands` block starts at `P:\DZ\anims\workspaces\player\player_main\player_main.agr:211` and holds 69 commands. The ones weapon and movement work meets:

| Command | Line | Starts |
|---|---|---|
| `CMD_Action` | `:218` | An action animation. |
| `CMD_Jump`, `CMD_Fall`, `CMD_Land` | `:245`, `:257`, `:263` | Jump, fall and landing. |
| `CMD_Reload_Magazine` | `:269` | A magazine reload. |
| `CMD_Reload_BoltAction` | `:272` | A bolt action reload. |
| `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast` | `:275`, `:278` | Chambering a round, and its fast form. |
| `CMD_Reload_Clip` | `:284` | A clip reload. |
| `CMD_Death` | `:287` | Death. |
| `CMD_Modifier_Additive` | `:338` | The sickness modifiers (see "Reload is not additive"). |
| `CMD_Vehicle_GetIn` | `:341` | Boarding a vehicle; its value picks the side. |
| `CMD_WeaponFire` | `:365` | Firing; its value picks the fire state (2 is firing while cocked and empty, `P:\DZ\anims\workspaces\player\player_main\combat.agf:1123`). |

Every command in every vanilla 1.30 master graph is `Synchronized 1`: 120 commands in 10 master graphs, none with 0.

## Action constants added in 1.30

Script names action animations through `DayZPlayerConstants` (`P:\scripts\3_game\dayzplayer.c`). The source files `ACTIONMOD` constants under "modifier (differential animation)" (`:740`) and `ACTIONFB` constants under "fb (full body)" (`:810`). Those added in 1.30:

| Constant | Value | Stances, from the source comment | Line |
|---|---|---|---|
| `CMD_ACTIONMOD_COMBINATIONLOCK` | 256 | Erect, crouch | `:766` |
| `CMD_ACTIONMOD_WASHFACE` | 257 | | `:767` |
| `CMD_ACTIONFB_COMBINATIONLOCK` | 256 | Prone | `:889` |
| `CMD_ACTIONFB_WASHFACEPOND` | 257 | Crouch | `:890` |
| `CMD_ACTIONFB_BUILDROPELADDER` | 258 | Crouch | `:891` |
| `CMD_ACTIONFB_BRICKSTACK` | 259 | Erect, crouch | `:892` |
| `CMD_ACTIONFB_BRICKTROWEL` | 260 | Erect, crouch | `:893` |
| `CMD_ACTIONFB_MIX_MORTAR` | 261 | Crouch | `:894` |
| `CMD_ACTIONFB_DRINKWELL_BUCKET` | 262 | Erect | `:895` |
| `CMD_ACTIONFB_SHARPEN` | 263 | Crouch | `:896` |
| `CMD_ACTIONFB_WASHFACEWELL` | 264 | Erect | `:897` |
| `CMD_ACTIONFB_WETCLOTH` | 265 | Crouch | `:898` |
| `CMD_ACTIONFB_WETCLOTHWELL` | 266 | Erect | `:899` |

## Variables

Variables are declared in the master graph's `ControlTemplate`, each with a default, a minimum and a maximum. From the wolf (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:4` to `:15`):

```cpp
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

All four animal graphs declare `speed`, `turn`, `behaviorAction`, `alertLevel`, `lookXAngle`, `lookYAngle`, `SlopeAngleX`, `SlopeAngleZ`, `InjuryLevel`, `behaviorSlotID` and `AnimalType` (`wolf_graph.agr:6` to `:56`).

- `speed` (0 to 5) steers the locomotion blend.
- `SlopeAngleX` and `SlopeAngleZ` (−90 to 90, `wolf_graph.agr:36`, `:41`) are filled by the engine and drive terrain alignment.
- No animal graph has a `swimming` variable. In the player graph swimming is a tag, `TagSwimming` on the `SwimmingMaster` state machine (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:7700` to `:7703`), not a number. A tutorial that treats `swimming` as a creature variable invents it.

The player's variables sit in the same place: `MovementSpeed` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:6`), `MovementDirection` (`:11`), `Stance` (`:16`), `TurnAmount` (`:21`), `Look` (`:26`), `LookDirX` (`:34`), `Raised` (`:49`), `Lean` (`:88`), `VehicleType` (`:108`) and the rest. Driving them from a scripted command is in `scripted-commands.md`. In 1.29 a declaration was a line such as `#Var speed float 0.0 0.0 5.0 ""`.

## Terrain alignment

There is no special terrain node. It is a procedural transform that turns bones by the slope variable converted from degrees to radians (0.01745329 is π/180). The wolf's `AlignToTerrain_Rot` (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:5` to `:16`):

```cpp
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

The herbivores have one node per body type, `TerrainRot_BoarAndPig`, `TerrainRot_CowAndBull`, `TerrainRot_Deers` and `TerrainRot_SheepAndGoat`, each clamping the slope to ±40 degrees first (`P:\DZ\animals\animations\!graph_files\herbivores\herbivores_maingraph.agf:2407`, `:2449`, `:2505`, `:2547`; the expression at `:2410`). For a new creature copy the node from the closest vanilla animal: a large quadruped from the cow, a medium one from the boar, a small one from the sheep. In 1.29 the node was an `AnimNodeRot`.

## Tags

A state or node carries tags in a `Tags { "Name" }` block, and conditions test them. In the motorbike state machine `GetIn_L` and `GetIn_R` carry `TagVehicleGetIn` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1614`, `:1594`), and the get out and jump out states carry `TagVehicleGetOut` (`:1604`, `:1624`, `:1634`, `:1651`). The death transition waits for boarding to finish: `Condition "IsCommand(CMD_Death) && !IsTag(\"TagVehicleGetIn\")"` (`:1719`).

Since 1.30 script can read tags with `BindTag(string pTagName)` and `IsTag(TAnimGraphTag iTag)` on `HumanAnimInterface` (`P:\scripts\3_game\human.c:318`, `:319`). No vanilla script does this yet; one use is keeping the handle from `BindTag("TagVehicleGetIn")` and polling `IsTag` on the fixed tick to line gameplay up with an animation phase.

## Reading and driving the graph from script

`HumanAnimInterface` binds graph names to ids: `BindCommand` (`P:\scripts\3_game\human.c:310`), `BindVariableFloat`, `BindVariableInt` and `BindVariableBool` (`:313` to `:315`), `BindTag` and `IsTag` (`:318`, `:319`). A `HumanCommandScript` (`:1236`) then writes them with `PreAnim_SetFloat`, `PreAnim_SetInt`, `PreAnim_SetBool` and `PreAnim_CallCommand` (`:1291` to `:1294`). What that does on the vanilla graph, measured in game, is in `scripted-commands.md`.

## Which changes collide

A mod that replaces a graph file, the player's `player_main` graph (as Expansion's animation addon and Survivor Animations do) or a creature's, collides with any other mod replacing the same graph. Whether two graph replacements can coexist on 1.30 is not measured.

A custom weapon or item animation replaces nothing. It reaches the engine through three layers, none of which edits the graph:

1. The clip: `.txa` compiled to `.anm` in Workbench.
2. A child `.asi` per item, whose lines map `WeaponOperations.<stance>.<state>` to the mod's clips, with `ParentTemplates` pointing at a vanilla instance (for a rifle `player_main_rifle.asi`, which inherits `player_main.asi`).
3. Script: `AddItemInHandsProfileIK(itemClass, instance, behaviour, ikPose, weaponStates)` binds the item class to the instance, an IK pose and a weapon states clip (`P:\scripts\3_game\dayzplayer.c:243`), and `AddItemBoneRemap(itemClass, pairs)` maps the weapon's part selections to the player's `Weapon_` bones (`:252`). Vanilla binds every weapon this way, for example `AKM_Base` to `weapons/player_main_akm.asi` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:412`).

Because the binding is per item class, each mod registers its own items and several such mods load together. When the plan is a custom weapon animation, do not warn about graph collisions. That the vanilla structure allows this is checked above; that a mod's own instance and clips play this way is a result measured in game (`weapon-anim-blender.md`).

Separate sub-graph files in 1.30 do not let a mod add to one; what adding one vehicle type would touch is in `tooling-and-walls.md`, "A mod cannot merge into a sub-graph". A rider pose for one vehicle class avoids all of it (`rider-poses.md`).

### A measured instance of that warning

Measured on a dedicated server running 1.30 Experimental, with third party mods: the Workshop mod Survivor Animations, which replaces the player graph, in a build made before 1.30, crashed the server at character creation (`CreateCharacter`, a native fault). It did so twice with a dependent addon and once with only that mod and a vanilla mission.

- Before building on a third party graph mod on a newer game version, load it alone with a vanilla mission and check a player can join.
- With a native fault under third party mods, that single mod run is the cheapest way to tell their fault from ours.
- Read such a mod's vehicle animation types through a run time `ConfigIsExisting("CfgPatches <Mod>")` check, never `#ifdef`.

## Reload is not additive

Some tutorials say a reload is an additive animation, torso and arms only, with another layer doing the rest. Vanilla does not show that:

- `CMD_Modifier_Additive` drives the sickness modifiers. Its values start `SickSneezeStanceSTM` (0), `SickCoughStanceSTM` (1) and `SickColdStanceSTM` (2) (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:5482` to `:5509`).
- Reloads use their own commands, none of them additive: `CMD_Reload_Magazine`, `CMD_Reload_BoltAction`, `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast` and `CMD_Reload_Clip` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:269` to `:284`).

The tutorial probably describes how the clip is keyed in Blender (torso and arms, legs left alone), not a run time layer. For a custom reload, find the vanilla weapon closest in feel and copy how its graph enters and leaves the state.

## Names tutorials get wrong

Correct these whenever the user repeats a tutorial spelling. The `model.cfg` key is not checked on `P:\`, since vanilla ships no `model.cfg` text (`model-cfg-animations.md`).

| Tutorial says | Real name |
|---|---|
| "Entity Position", "Pin Look At" | `EntityPosition`, `LookAt` (`P:\DZ\anims\cfg\skeletons.anim.xml:5`, `:17`) |
| "right hand dummy" | `RightHand_Dummy` (`P:\DZ\anims\cfg\skeletons.anim.xml:115`) |
| "cmd death", "cmd success", "cmd attack" | `CMD_Death`, `CMD_AttackSuccess`, `CMD_Attack` (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:63` to `:69`) |
| `discrete = 1` | `isDiscrete = 1` in `model.cfg` |
| `skeletonAnims.xml` | `skeletons.anim.xml` |
| "weapon cocked", "mag remove" as state names | `FireCocked`, `ReloadMagazineDetach` (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_1911.asi:19`, `:52`) |
| "bullet in chamber" as a state | No such state; chambering is `CMD_Reload_Chambering` and `CMD_Reload_ChamberingFast` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:275`, `:278`) |
| "reload is additive" | `CMD_Modifier_Additive` drives the sneeze and cough modifiers, not reloads (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:5483`) |

## Not covered here

- The full `.ast` grammar: copy from the closest vanilla template.
- The frame rate of player clips. No graph, template, workspace or sync file declares one; it is probably in the binary `.anm` or set by the exporter. The weapon clips read from the binaries run at 30 frames per second (`anim-instances-and-templates.md`). Set 30 in the exporter and round trip one short clip before making a set.
- The insides of `.anm` and `.xob`: DayZATool and Workbench.
- The script calls 1.30 added (instance switching, speed limits, ragdoll): `dayz-1-30-changes.md`.
