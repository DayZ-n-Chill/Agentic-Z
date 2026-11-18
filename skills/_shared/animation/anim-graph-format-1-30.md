# The 1.30 graph format

How a 1.30 animation graph is written, using the vehicle sub-graph as a tour of the node types, how it differs from the 1.29 syntax, how to open the player graph in Workbench, and how to port a 1.29 `$AnimGraph 7` graph field by field. What the graph holds (commands, variables, tags) is in `anim-graphs.md`; instances and templates in `anim-instances-and-templates.md`.

The 1.30 side of every example cites `P:\`. The 1.29 side was read from a 1.29 unpack and cannot be checked on a 1.30 one.

## The vehicle graph, as a tour of the 1.30 node types

`P:\DZ\anims\workspaces\player\player_main\vehicles.agf` (3654 lines) is a good file to learn the format from. From `:1564` to `:1572`:

```cpp
AnimSrcNodeBlendT MotorBikeB {
 EditorPos 4 -18.3
 BlendTime "0.3"
 BlendFn S
 Condition "VehicleType == 10 || VehicleType == 11"
 Child0 "VehicleSTM"
 Child1 "MotorBikeSTM"
```

| Node type | Does | First example |
|---|---|---|
| `AnimSrcNodeBlendN` | Blends several children by thresholds on a weight (`BlendWeight "VehicleSpeed"`, `Thresholds`). | `vehicles.agf:5` |
| `AnimSrcNodeBlendT` | Switches between two children on a condition over a blend time. | `vehicles.agf:1564` |
| `AnimSrcNodeBlend` | Blends two children by a formula (`MotoYIntertiaB`). | `vehicles.agf:1556` |
| `AnimSrcNodePose` | Reads one pose out of a clip at a time given by an expression. | `vehicles.agf:47` |
| `AnimSrcNodeStateMachine` | A state machine with `states` and `transitions` (`MotorBikeSTM`). | `vehicles.agf:1582` |
| `AnimSrcNodeIK2Target`, `AnimSrcNodeIK2` | Two bone IK that pins the driver's hands to the steering. | `vehicles.agf:17`, `:31` |
| `AnimSrcNodeSourceSync` | Plays a clip on a sync line. | `vehicles.agf:69` |

`MotorBikeSTM` (`vehicles.agf:1582` to `:1751`) has the rider states `Idle`, `GetIn_L`, `GetIn_R`, `GetOut_L`, `GetOut_R`, `JumpOut_L`, `JumpOut_R`, `Death` and `GettingInDeath`. The get in states pick a side from the command value: `GetIn_L` on `GetCommandI(CMD_Vehicle_GetIn) == 0` (`:1618`), `GetIn_R` on 1 (`:1598`).

The motorbike is new in 1.30. Its animations are template columns (`Jawa_05` and `Jawa_Bitrak`, `P:\DZ\anims\workspaces\player\player_main\player_main.ast:1119`, `:1120`) with lines in the base instance (`Vehicle.Jawa_05.AccelerationSpine` at `P:\DZ\anims\workspaces\player\player_main\player_main.asi:5088`). A mod vehicle can read or borrow from this state machine; changing it means shipping graph files at the vanilla paths (`tooling-and-walls.md`).

## 1.29 and 1.30: both text, different syntax

1.30 did not swap binary for text. In a 1.29 unpack `player_main.agr` opens with `$AnimGraph 7 {`, lists eight sub-graphs as `.agr` files, and none of the nine files holds a NUL byte. What changed is the syntax. 1.29 writes a node with positional fields:

```cpp
$Node AnimNodeGroupSelect {
    "Boat_01ActionG" "" "VehicleTalkingT" "VehicleActions" "Boat_01"
```

and 1.30 with named ones (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1381` to `:1386`):

```cpp
AnimSrcNodeGroupSelect Jawa_BitrakActionG {
 EditorPos 27.6 -50
 Child "VehicleTalkingT"
 Group "VehicleActions"
 Column "Jawa_Bitrak"
}
```

A line diff across the two formats is noise; compare parsed nodes, variables and commands. Bohemia said the same when 1.30 Experimental shipped: in 1.29 a graph mod could be compared with vanilla in a text editor, and for 1.30 graph mods must redo their changes from scratch, with new limits such as the number of groups.

A 1.30 unpack made over a 1.29 one leaves the old `combat.agr`, `locomotion.agr` and the rest beside the new files. They are stale; the master graph lists only the `.agf` files (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`).

The 1.30 changelog removed the `Buffer Save` and `Buffer Use` nodes, and no vanilla 1.30 sub-graph has one. A custom graph that used them must move to variables or direct state machine transitions.

## Opening the player graph in the Workbench animation editor

- In 1.29 the compiled workspace `player_main.aw` had a line `#eventtable "{3037156104937B91}DZ/anims/workspaces/player/Player_EventTable.ae"`, which the source workspace of Bohemia's animation sample did not. Tutorials say to delete that line so the editor opens the graph; Workbench bound the event table again on export.
- In 1.30 the workspace names its event table directly: `EventTable "{3037156104937B91}DZ/anims/workspaces/player/Player_EventTable.ae"` (`P:\DZ\anims\workspaces\player\player_main\player_main.aw:15`). The 1.30 changelog says the editor is the 2021 Enfusion one, with live editing of a running graph, a "Show In Explorer" action and a ragdoll editor for `.ragdoll` files. Whether the delete trick is still needed is not tested.
- If Workbench fails to load a copied vanilla graph after events were added, fix the event table before touching graph logic.

## Porting a 1.29 `$AnimGraph 7` graph to 1.30

Whether 1.30 still loads a custom graph in the 1.29 format is not tested; the one attempt failed earlier, on script compilation. Vanilla 1.30 ships the new format. Port a custom graph as below, or load the old one first and read the RPT.

The mapping comes from the 1.29 and 1.30 versions of the same vanilla graphs: all seven `$AnimGraph 7` graphs (infected, `player_main`, `player_menu`, wolf, ambient life, herbivores, bear; `player_inventory` is `$AnimGraph 6`) and the older samples (`$AnimGraph 3` and `$AnimGraph 2`). A generator script has applied it to one custom graph end to end; that port has not been loaded in game.

### File set

The master stays `.agr` and becomes `AnimSrcGraph`. Every sub-graph becomes `.agf` (`AnimSrcGraphFile`). The template becomes `AnimSetTemplateSource` and the instance `AnimSetInstanceSource`. Delete the old sub-graph `.agr` files.

- `config.cpp` `graphname`, `defaultinstance` and `startnode` need no change; vanilla 1.30 configs still use backslash paths there.
- `DefaultRunNode` is optional: of the ten vanilla masters only the infected and `player_main` set one (`P:\DZ\anims\workspaces\infected\infected_main\infected.agr:433`). The config's `startnode` picks the entry.
- `AnimSyncTable` is optional too: the player inventory, player menu and ambient life masters have none; the wolf has one (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:3`).

### Master `.agr`

```cpp
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

Write numbers bare (`0`, `-180`), not `0.0`.

### Sub-graph `.agf`

The file is `AnimSrcGraphFile { Sheets { AnimSrcGraphSheet <Sheet> { Nodes { ...nodes... } } } }`. A node's name follows its class (`AnimSrcNodeSource Idle_SRC {`); quote it only when it has spaces or punctuation (`AnimSrcNodeGroupSelect "Swings-Short"`).

| 1.29, positional fields | 1.30, named fields |
|---|---|
| `AnimNodeSource "N" "Tag" "Key" "loop"` | `AnimSrcNodeSource N { Tags { "Tag" } EditorPos x y Source "Key" Looptype Loop }`. `noloop` becomes `Looptype "No Loop"`. Leave `Tags` out when the tag is empty. Drop an empty `$Predictions`; a non-empty one (126 of the 840 source nodes in the seven graphs) becomes a `Predictions { AnimSrcNodePrediction ... }` block, which this table does not map. |
| `AnimNodeBlend "N" "" "Weight" "C0" "C1" F` | `AnimSrcNodeBlend N { EditorPos BlendWeight "Weight" Child0 "C0" Child1 "C1" OptimizeMin F&1 OptimizeMax F>>1&1 }` |
| `AnimNodeBlendT "N" "" "C0" "C1" "On" "Off" "Cond" T "Fn" F` | `AnimSrcNodeBlendT N { EditorPos BlendTime "T" BlendFn Fn TriggerOn "On" TriggerOff "Off" Condition "Cond" Child0 "C0" Child1 "C1" OptimizeMin F&1 OptimizeMax F>>1&1 SelectMainPath F>>2&1 }`. Keep both triggers. Copy `Fn` as it is: `S` on 154 of the 155 such nodes and `S2` on one (now at `P:\DZ\anims\workspaces\player\player_main\locomotion.agf:13346`). |
| `AnimNodeGroupSelect "N" "Tag" "Child" "Group" "Column"` | `AnimSrcNodeGroupSelect N { Tags { "Tag" } EditorPos Child "Child" Group "Group" Column "Column" }`. Leave `Tags` out when empty. |
| `AnimNodeStateMachine "N" "Tag"` with `$States` and `$Transitions` | `AnimSrcNodeStateMachine N { Tags { "Tag" } EditorPos states { ... } transitions { ... } }`. Leave `transitions` out when there are none. |
| `$State { "S" "Tag" "Child" "Cond" "notime" X }` | `AnimSrcNodeState S { Tags { "Tag" } EditorPos Child "Child" StartCondition "Cond" TimeStorage Inherit IsExit X }`. `realtime` becomes `TimeStorage "Real Time"` and `normtime` `TimeStorage "Normalized Time"` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:92`). |
| `$Transition { "A" "B" "Cond" "D" "T" P "Fn" }` | `AnimSrcNodeTransition "{GUID}" { FromState "A" ToState "B" Duration "D" StartTime "T" Condition "Cond" BlendFn Fn PostEval 1 MotionVecBlend 0x33 0 }`. See the notes below. |
| `AnimNodeRot "N" "Tag" "Child" "Expr"` with `$rotitems { $ri { "Bone" "ymr" k } }` | `AnimSrcNodeProcTransform N { Tags { "Tag" } EditorPos Child "Child" Expression "Expr" Bones { AnimSrcNodeProcTrBoneItem "{GUID}" { Bone "Bone" Axis Y Space Model Op Rotate Amount k } } }`. Leave `Tags` out when empty. |

The transition row:

- `"T"` is the start time. Copy it as it is, number or expression, escaped quotes included, and write `StartTime ""` only when it is empty. Infected examples: `StartTime "0.2"` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:1380`), `StartTime "0.7"` (`P:\DZ\anims\workspaces\infected\infected_main\interaction.agf:62`), `StartTime "GetLowerTime()"` (`locomotion.agf:223`) and `StartTime "GetEventTime(\"Attack.Attack Left Light\", \"BlendIn\")"` (`P:\DZ\anims\workspaces\infected\infected_main\combat.agf:113`).
- `P` is a set of flags. 1 gives `PostEval 1` (no `PostEval` line without it). 6 gives `MotionVecBlend 0x30 0` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:1211`) and 24 gives `MotionVecBlend 0x3 0` (with `PostEval 1` from 25, at `:11283`) instead of `0x33 0`. The seven graphs use only 0, 1, 6, 7 and 25.
- `Fn` keeps `S` and `S2`, renames `Lin` to `Linear` (`BlendFn Linear`, `P:\DZ\anims\workspaces\player\player_main\locomotion.agf:13094`) and `SEnd` to `"Ease Out"` (`BlendFn "Ease Out"`, `P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:2472`).
- An empty `"A"` (from any state) gives no `FromState` line.

General rules:

- Write empty strings out, as vanilla does: `StartCondition ""`, `Condition ""`, `TriggerOn ""`, and `StartTime ""` for an empty start time. Drop only an empty `Tags`, `FromState`, `PostEval 0`, and empty `transitions` and `Predictions` blocks. In the seven graphs the start time is set on 495 of 1,251 transition lines, each value found as a `StartTime` in the 1.30 files; the 1,105 transition lines that pair one to one with a 1.30 transition all follow the `P` and `Fn` rules.
- The second string of a 1.29 node or state line is its tag field, written in 1.30 as `Tags { ... }`: `Tags { "TagVaultStart" }` on the infected vault state (`P:\DZ\anims\workspaces\infected\infected_main\interaction.agf:32` to `:35`), `TagProneBack` on a player group select (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:5065` to `:5068`). The field can hold several tags separated by spaces; 1.30 writes one quoted string each, so `"TagWater TagErected"` became `Tags { "TagWater" "TagErected" }` (`:1610` to `:1613`). The field is set on 260 of 1,452 state lines, 3 of 641 group select lines and 1 of 70 rot lines, and empty on every blend (100) and blend T (155) line, so no vanilla pair shows a tag on those two.
- Other node types occur in the same graphs and are not mapped here: `AnimNodeSourceSync`, `AnimNodeSwitch`, `AnimNodeBlendN`, `AnimNodeQueue` and more.
- `EditorPos x y` comes from the 1.29 `$EditorData { #EditorPos x y }` block with x kept and y negated: `#EditorPos 1.9 11.6000004` became `EditorPos 1.9 -11.6` on the infected `DeathT` node (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:1594` to `:1595`). The same holds for all 236 nodes and states whose name occurs once in the three infected sub-graphs.

What confirms each row, on vanilla 1.29 and 1.30 pairs:

- State, transition, source and group select come from the sample pairs.
- The blend and blend T flag bits hold for every node that pairs by name: all 155 blend T nodes, each keeping its blend function, and 99 of the 100 blend nodes. The hundredth, the player's `VehicleAccelerationB`, was an `AnimNodeBlend` in 1.29 and is an `AnimSrcNodeBlendT` in 1.30 (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:2769`). The infected `DeathT` has `OptimizeMin 1`, `OptimizeMax 1` and `SelectMainPath 1` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:1594` to `:1605`), matching its trailing `7` in 1.29. An old blend flag of 3 is minimum 1, maximum 1.
- The rot code letters are axis (`x`, `y`, `z`), space (`m` model, `l` local) and operation (`r` rotate, `t` translate).
- `Amount` takes the old coefficient unchanged, and the child and expression are unchanged. This and the letters hold for all 70 rot nodes against the 1.30 node of the same name, item by item (430 bone items, with the codes `xlr`, `xlt`, `xmr`, `ylr`, `ylt`, `ymr`, `zlr`, `zlt` and `zmr`). The wolf's terrain tilt was converted this way: the expression kept, `Amount 1`.
- Not tested in game: if a procedural twist turns too far or not far enough, `Amount` is the value to change.

### Template and instance: every key has three parts

A 1.29 group type with group names becomes one `AnimSetTemplateSource_AnimationGroup { Name "G" Animations { ... } Columns { ...the old group names... } }`. Keep groups, animations and columns sorted, as vanilla does.

The 1.29 unnamed group (keys like `"Melee0"`) has no 1.30 form. Use the pattern vanilla ships: `Name "Default"` with `Columns { "Normal" }`, instance keys `"Default.Normal.Melee0"`, and graph sources `Source "Default.Normal.Melee0"`.

Both source forms work in vanilla:

- `"Group.Anim"`, with the column chosen by an enclosing group select: `Source "Attack.Attack Left Heavy"` in the infected graph (`P:\DZ\anims\workspaces\infected\infected_main\combat.agf:7`).
- `"Group.Column.Anim"` written out: `Source "Default.Normal.attack_high"` in the wolf graph (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:49`).

The player's renamed group shows in its sources as `Source "Facial.FacialHitHeavy"` (`P:\DZ\anims\workspaces\player\player_main\combat.agf:393`).

Instance lines are `AnimSetInstanceSource_Line "G.C.Anim" { Resource "{GUID}path.anm" }` inside `Lines { }`, after `Template "{GUID}path.ast"` and `ParentTemplates { }`.

### Resource ids

Each `{16 hex digits}` prefix is a resource id. Vanilla clip ids did not change from 1.29: all 187 clips of the 1.29 infected instance keep their id in 1.30. For your own files and for ids local to a node (`AnimSrcNodeTransition`, `AnimSrcNodeProcTrBoneItem`, `AnimSrcGCT`), derive them from a stable seed, such as the first 16 hex characters of the SHA-1 of the path or node name, so a second run gives identical files. Give each resource one id everywhere it appears.

### Packing

RaG PBO Builder packs `.agf` as plain text next to the `.agr`, `.ast` and `.asi` (third party tool behaviour, not checked here). Check this in the built PBO, not the source tree.
