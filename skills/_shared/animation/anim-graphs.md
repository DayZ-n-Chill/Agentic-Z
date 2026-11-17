# Animation graphs and instance files

Where the player and creature animation graphs live on `P:\`, the names they declare, and which mod changes collide. Open this when a task names a `CMD_` command, an `.asi` file, a graph variable or a weapon state. The depth (formats, the 1.29 to 1.30 port, measured results) is in `skills/dayz-animation-pipeline/references/anim-graph.md`.

## The files (1.30)

| What | Path | Holds |
|---|---|---|
| Master graph | `P:\DZ\anims\workspaces\player\player_main\player_main.agr` | Variables, commands, and the list of sub-graphs (`GraphFilesResourceNames`, :1587). |
| Sub-graphs | `locomotion.agf`, `combat.agf`, `weapons.agf`, `gestures.agf`, `vehicles.agf`, `actions.agf`, `master.agf`, `tests.agf` in the same folder | State machines and blend nodes. They were `.agr` files in 1.29; a 1.30 unpack made over an older one leaves those stale files beside the new ones. |
| Template | `P:\DZ\anims\workspaces\player\player_main\player_main.ast` | The animation names that exist, in named groups such as `WeaponOperations` (:1217). |
| Instances | `player_main.asi` and its children in the same folder, `props\` and `weapons\` | Animation name to `.anm` clip. A child lists only what it changes. |
| Workspace | `P:\DZ\anims\workspaces\player\player_main\player_main.aw` | Ties template, instances, graph, `EventTable` (:15) and `SyncTable` (:16) together. |
| Infected | `P:\DZ\anims\workspaces\infected\infected_main\infected.agr` and its `.agf`, `.ast` and `.asi` files | The same layout. |
| Animals | `P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr` and the `herbivores` and `ambientlife` folders beside it | The same layout. |

All of these are text. Only the `.anm` clips are binary.

## Names the graphs declare

- **Player commands** are in the `Commands` block of the master graph (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:211`): `CMD_Action` (:218), `CMD_Jump` (:245), `CMD_Reload_Magazine` (:269), `CMD_Reload_Chambering` (:275), `CMD_Death` (:287), `CMD_Modifier_Additive` (:338), `CMD_Vehicle_GetIn` (:341), `CMD_WeaponFire` (:365) and the rest.
- **Animal commands**: `CMD_Attack`, `CMD_AttackSuccess`, `CMD_Death`, `CMD_JumpType`, `CMD_LookAt`, `CMD_AnimCallBack`, `CMD_Hit`, `CMD_LookAtXChange` (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:63` to `:84`). There is no `CMD_Success`.
- **Infected commands** are upper case: `CMD_HIT_LIGHT`, `CMD_HIT_HEAVY`, `CMD_DEATH`, `CMD_ATTACK`, `CMD_TURN`, `CMD_VAULT`, `CMD_CRAWL`, `CMD_NODEATH` (`P:\DZ\anims\workspaces\infected\infected_main\infected.agr:46` to `:67`).
- **Player variables**: `MovementSpeed` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:6`), `MovementDirection` (:11), `Stance` (:16), `Raised` (:49), `Lean` (:88), `VehicleType` (:108).
- **Animal variables**: `speed`, `turn`, `SlopeAngleX`, `SlopeAngleZ` and others (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:6`, `:11`, `:36`, `:41`).
- **Weapon states** are instance lines of the form `WeaponOperations.<stance>.<state>`, for example `WeaponOperations.ErcRas.FireCocked` and `WeaponOperations.ErcRas.ReloadMagazineDetach` (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_1911.asi:19`, `:52`). `ErcRas` is erect with the weapon raised; `PneRas` is prone and raised.

`CMD_Modifier_Additive` is not about reloads: its values start the sneeze, cough and cold modifiers (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:5482` to `:5509`).

## How a clip reaches one item without touching the graph

1. An instance file for the item: a child `.asi` whose `ParentTemplates` names a vanilla instance and whose `Lines` map the states it changes to its own clips. The shape is the same as vanilla's own children (`P:\DZ\anims\workspaces\player\player_main\player_main_rifle.asi:1` to `:9`).
2. Script binds the item class to that instance with `AddItemInHandsProfileIK` (`P:\scripts\3_game\dayzplayer.c:243`), as vanilla does for every weapon (`AKM_Base` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:412`). Details: `items-in-hands.md`.

Nothing in the graph, template or workspace is replaced, so several mods can each do this for their own items.

## What collides

A mod that ships its own copy of a graph file (the player's `player_main` graph, or a creature's) replaces it for everyone, and two mods replacing the same graph conflict. Third party examples are the animation addons of DayZ Expansion and Survivor Animations. The source pack measured a pre 1.30 build of Survivor Animations crashing a 1.30 server at character creation; whether two graph replacements can coexist on 1.30 is not measured. Tell the art lead when a plan needs a replaced graph, and do not raise it for config driven animation or for the per item route above.

1.30's separate sub-graph files do not let a mod add to one. A new vehicle type, for example, needs a state in the `VehicleMaster` state machine (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:2913`), a column next to `Jawa_05` and `Jawa_Bitrak` in the template (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1114` to `:1127`), and above type 12 a change to the master graph, which declares `VehicleType` with `MaxValue 12` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:108` to `:112`). All of those are vanilla path files, and the player's config names one graph (`graphName` in `class enfAnimSys`, `P:\DZ\characters\data\config.cpp:156`). A rider pose for one vehicle class can avoid all of it: `rider-poses.md`.

## Reading and driving the graph from script

`HumanAnimInterface` binds graph names to ids: `BindCommand` (`P:\scripts\3_game\human.c:310`), `BindVariableFloat`, `BindVariableInt`, `BindVariableBool` (:313 to :315), `BindTag` and `IsTag` (:318, :319). A `HumanCommandScript` (`:1236`) then writes them with `PreAnim_SetFloat`, `PreAnim_SetInt`, `PreAnim_SetBool` and `PreAnim_CallCommand` (:1291 to :1294). What that achieves on the vanilla graph, as measured in game by the source pack: `skills/dayz-animation-pipeline/references/scripted-command-locomotion.md`.
