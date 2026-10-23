# Research map: animation specialist

Private research map. Anchors point into vanilla data on `P:\`. Items marked **knowledge** are not verifiable from vanilla files on `P:\`.

| # | Topic | What the specialist needs to know | Verify at |
|---|---|---|---|
| 1 | Player animation graph | Workbench graph files `.agr`/`.agf` (master, locomotion, actions, combat, gestures), template `.ast`, instances `.asi`. | `P:\DZ\anims\workspaces\player\player_main\player_main.agr`, `master.agr`, `actions.agr`, `player_main.ast`, `player_main.asi` |
| 2 | Hand instances per item type | `player_main_1h.asi`, `_2h`, `_heavy`, `_bow`, restrained. | `P:\DZ\anims\workspaces\player\player_main\player_main_1h.asi` and siblings |
| 3 | Event and sync tables | `.ae` event table and `.asy` sync table. | `P:\DZ\anims\workspaces\player\player_eventtable.ae`, `player_synctable.asy`; `P:\DZ\anims\workspaces\infected\eventtable.ae` |
| 4 | Raw animations | `.anm` files for player and infected. | `P:\DZ\anims\anm\player`, `P:\DZ\anims\anm\infected` |
| 5 | Skeleton | Skeleton definitions for import and export. | `P:\DZ\anims\cfg\skeletons.anim.xml` |
| 6 | Item-in-hands registration | `DayZPlayerTypeRegisterItems` and `AddItemInHandsProfileIK` bind item classes to an `.asi` and IK. | `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:334`, `:373`; native `P:\scripts\3_game\dayzplayer.c:243` |
| 7 | Mod item registration hooks | `ModItemRegisterCallbacks.RegisterOneHanded/RegisterTwoHanded`. | `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:305`, `:309`, `:311`, `:1552` |
| 8 | Item behaviour config | `HumanItemBehaviorCfg` (stance, aiming, raised behaviour). | `P:\scripts\3_game\humanitems.c:5` |
| 9 | Command IDs | `DayZPlayerConstants` with `CMD_ACTIONMOD_*`, `CMD_ACTIONFB_*`, `CMD_GESTUREFB_*`. | `P:\scripts\3_game\dayzplayer.c:601`, `:741`, `:812`, `:867`, `:1011` |
| 10 | Starting action animations | `StartCommand_Action` (full body) and `AddCommandModifier_Action` (additive). | `P:\scripts\3_game\human.c:1567`, `:1597` |
| 11 | Action callbacks | `HumanCommandActionCallback`, `ActionBaseCB`, `OnAnimationEvent`. | `P:\scripts\3_game\human.c:329`, `:423`; `P:\scripts\4_world\classes\useractionscomponent\animatedactionbase.c:1` |
| 12 | Action classes | `ActionBase`, `AnimatedActionBase`, continuous, interact, single use; `m_CommandUID`, `m_StanceMask`. | `P:\scripts\4_world\classes\useractionscomponent\actionbase.c:51`; `...\animatedactionbase.c:145`; `...\actions\actioncontinuousbase.c:120`; `...\actions\actioninteractbase.c:38`; `...\actions\actionsingleusebase.c:29`; `P:\scripts\3_game\entities\entityai.c:105`-`107` |
| 13 | Registering actions on items | `SetActions` / `AddAction`. | `P:\scripts\4_world\entities\explosivesbase.c:191`, `:195` |
| 14 | Human commands | Move, fall, vehicle, weapons, additives, scripted commands. | `P:\scripts\3_game\human.c:453`, `:592`, `:711`, `:1026`, `:1152`, `:1236`; `StartCommand_Fall` `:1501` |
| 15 | Emotes | `EmoteManager`, `EmoteBase`, `EmoteConstructor`; emote start via `StartCommand_Action`. | `P:\scripts\4_world\classes\emotemanager.c:116`, `:699`; `P:\scripts\4_world\classes\emoteclasses\emotebase.c:1`; `P:\scripts\4_world\classes\emoteconstructor.c:1` |
| 16 | Animation sound events | `AnimSoundEvent`, `AnimSoundVoiceEvent`, `OnSoundEvent`, `OnStepEvent`. | `P:\scripts\3_game\dayzanimevents.c:134`, `:218`; `P:\scripts\3_game\dayzplayer.c:299`, `:302` |
| 17 | Player implementation | `DayZPlayerImplement` command handler. | `P:\scripts\4_world\entities\dayzplayerimplement.c:86` |
| 18 | Sync junctures | Server-to-client sync of animation-driven events (death, hits, unconscious). | `P:\scripts\4_world\entities\dayzplayersyncjunctures.c:4` |
| 19 | Fall damage | `DayZPlayerImplementFallDamage`. | `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:18` |
| 20 | Cameras | `RegisterCameraCreator`, `DayZPlayerCameras`. | `P:\scripts\3_game\dayzplayer.c:267`; `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:1`, `:46` |
| 21 | Object animation sources | `SetAnimationPhase`/`GetAnimationPhase` drive model.cfg animations (doors, base parts). | `P:\scripts\3_game\entities\entity.c:12`, `:15` |
| 22 | Vehicle seat animations | Vehicle anim instances and seat types. | `P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c`; `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:109`, `:119` |
| 23 | Infected and animal animation | Infected graph and model workspace; animal `enfanimsys` config. | `P:\DZ\anims\workspaces\infected\infected_main`; `P:\DZ\characters\zombies\config.cpp:71`; `P:\DZ\animals\cervus_elaphus\config.cpp:277` |
| 24 | Animation event entries in config | `AnimEvents` blocks in item and animal configs. | `P:\DZ\animals\cervus_elaphus\config.cpp:285`; `P:\DZ\characters\tops\config.cpp:2339` |
| 25 | model.cfg skeletons and animation sources | `CfgSkeletons` and `CfgModels` per model folder for bones and animations. **knowledge**; vanilla p3d folders hold `model.cfg` only in source form, not in this unpack. | Not verified on `P:\` |
| 26 | Authoring pipeline | Workbench Animation Editor, `.anm` export from Blender or Max, graph editing; changing the vanilla graph needs a replacement graph mod. **knowledge** | Not verifiable on `P:\` |
