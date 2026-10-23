# Research map: AI specialist (infected and animals)

Private research map. Anchors point into vanilla data on `P:\`. Items marked **knowledge** are not verifiable from vanilla files on `P:\`.

| # | Topic | What the specialist needs to know | Verify at |
|---|---|---|---|
| 1 | Creature hierarchy | `DayZCreature` then `DayZCreatureAI`, then `DayZInfected` and `DayZAnimal`; script `ZombieBase`, `AnimalBase`. | `P:\scripts\3_game\entities\dayzanimal.c:24`, `:191`; `P:\scripts\4_world\entities\creatures\infected\zombiebase.c:1`; `P:\scripts\4_world\entities\creatures\animals\animalbase.c:1` |
| 2 | Infected commands | Move, death, hit, crawl; `StartCommand_Crawl`. | `P:\scripts\3_game\entities\dayzinfected.c:37`, `:45`, `:47`, `:58`, `:113` |
| 3 | Infected constants and mind states | `DayZInfectedConstants` (mind states), movement constants; synced mind state. | `P:\scripts\3_game\entities\dayzinfected.c:1`, `:21`; `P:\scripts\4_world\entities\creatures\infected\zombiebase.c:182` |
| 4 | Command handler | `ZombieBase` `HandleMove`, `HandleOrientation`, attack choice. | `P:\scripts\4_world\entities\creatures\infected\zombiebase.c:221`, `:222`, `:297`, `:704` |
| 5 | Attack types | `DayZInfectedType.ChooseAttack`, `DayZInfectedAttackType`, attack groups. | `P:\scripts\3_game\entities\dayzinfectedtype.c:1`, `:13`, `:19`, `:96` |
| 6 | Input controllers | Infected and animal input controllers (what the AI wants to do). | `P:\scripts\3_game\entities\dayzinfectedinputcontroller.c:1`; `P:\scripts\3_game\entities\dayzanimalinputcontroller.c:49`; `P:\scripts\3_game\entities\dayzcreatureaiinputcontroller.c:1` |
| 7 | Moddable infected commands | Vanilla moddable wrappers. | `P:\scripts\4_world\entities\dayzinfectedimplement.c:6` |
| 8 | Animal commands | Move, attack, jump; `ModCommandHandlerBefore/Inside`, `HandleDeath`. | `P:\scripts\3_game\entities\dayzanimal.c:572`, `:577`, `:582`, `:180`, `:433`, `:732` |
| 9 | AI agent templates | `CfgAIBehaviours` classes (Infected, InfectedMale, Predators_Wolf, Herbivores); referenced by `aiAgentTemplate=` in creature configs. | `P:\DZ\AI\config.cpp:14`, `:6214`, `:6437`, `:5420`; `P:\DZ\characters\zombies\config.cpp:160`, `:423`; `P:\DZ\animals\cervus_elaphus\config.cpp:27` |
| 10 | Behaviour (high level) | `BehaviourHLZombie` with movement speeds and mind-state slots. | `P:\DZ\AI\config.cpp:6219`, `:6221`, `:6261`, `:6285` |
| 11 | Alert system | Calm and alerted thresholds. | `P:\DZ\AI\config.cpp:6333`, `:6339`, `:6345` |
| 12 | Target system | `TargetSystemDZBase` (vision and hearing tuning). | `P:\DZ\AI\config.cpp:6355` |
| 13 | Noise system | `NoiseSystemParams`, `CfgNoises`, `AddNoisePos/AddNoiseTarget`, surface noise multiplier, weapon `NoiseShoot`. | `P:\DZ\AI\config.cpp:6378`, `:6903`; `P:\scripts\3_game\dayzgame.c:3618`, `:3788`, `:3833`; `P:\DZ\weapons\firearms\akm\config.cpp:82` |
| 14 | Visibility | Clothing `visibilityModifier` summed per player. | `P:\scripts\4_world\entities\manbase\playerbase.c:5423` |
| 15 | Script behaviour classes | `AIBehaviourHL`, `AIBehaviourHLZombie2`, `OnAnimationEvent`. | `P:\scripts\3_game\aibehaviour.c:26`, `:42`, `:64`, `:74` |
| 16 | AI world and groups | `AIWorld`, `CreateGroup`, `AIGroup`, `AIGroupBehaviour`, `AIAgent`. | `P:\scripts\3_game\ai\aiworld.c:70`, `:79`; `P:\scripts\3_game\ai\aigroup.c:1`; `P:\scripts\3_game\ai\aigroupbehaviour.c:1`; `P:\scripts\3_game\ai\aiagent.c:1`; `P:\scripts\3_game\global\world.c:116` |
| 17 | Navmesh queries | `FindPath`, `RaycastNavMesh`, `SampleNavmeshPosition`, `PGFilter`. | `P:\scripts\3_game\ai\aiworld.c:59`, `:98`, `:110`, `:122` |
| 18 | Navmesh test entities | Vanilla test building for navmesh. | `P:\scripts\4_world\entities\navmeshtest\navmeshtest.c:2` |
| 19 | Navmesh data | Per-map navmesh export. | `P:\DZ\worlds_chernarusplus_nav.txt` (index); `P:\DZ\worlds` |
| 20 | AI target callbacks | How players are targeted (head/body positions). | `P:\scripts\3_game\systems\ai\aitarget_callbacks.c:8`; `P:\scripts\4_world\entities\manbase\playerbase\aitargetcallbacksplayer.c:1` |
| 21 | Damage and death hooks | `EEHitBy`, `EEKilled` on creatures. | `P:\scripts\3_game\entities\dayzinfected.c:138`; `P:\scripts\3_game\entities\dayzanimal.c:237`, `:832`; `P:\scripts\3_game\entities\entityai.c:1104` |
| 22 | Zombie config | `ZombieBase` config: attachments, `InputController`, `NoiseTemplates`, `DamageSystem`, `AttackActions`. | `P:\DZ\characters\zombies\config.cpp:24`, `:79`, `:161`, `:169`, `:436` |
| 23 | Animal config | `Animal_CervusElaphus` example: damage, `enfanimsys`, `AnimEvents`. | `P:\DZ\animals\cervus_elaphus\config.cpp:20`, `:41`, `:277`, `:285` |
| 24 | Creature type classes | `DayZCreatureAIType`, `DayZAnimalType`, `DayZInfectedType`. | `P:\scripts\3_game\entities\dayzcreatureaitype.c:1`; `P:\scripts\3_game\entities\dayzanimaltype.c:1`; `P:\scripts\3_game\entities\dayzinfectedtype.c:19` |
| 25 | Melee against infected | Mind-state checks for stealth kills. | `P:\scripts\4_world\entities\dayzplayerimplementmeleecombat.c:447`, `:449` |
| 26 | Infected sounds | Sound event handler. | `P:\scripts\4_world\classes\soundevents\infectedsoundevents\infectedsoundeventhandler.c:14` |
| 27 | Spawning | Infected and animals spawn from CE (`events.xml`, zombie territories, `cfgeventspawns.xml`) in the server mission; script spawn via `CreateObjectEx`. **knowledge** for mission files. | `P:\scripts\3_game\dayzgame.c:3669` (CreateObjectEx pattern) |
| 28 | Limits of the engine AI | No script-side pathing brain for humans; vanilla offers no human AI. Behaviour graph logic is native and only tunable through config. **knowledge** | Native classes `P:\scripts\3_game\aibehaviour.c:42` |
