# Creatures: classes, commands and mod hooks

How vanilla infected and animals are built in script, how their command handler decides what animation command runs, and the hooks a mod can use.

## Class chain

| Class | Parent | Defined at |
|---|---|---|
| `DayZCreature` | `EntityAI` | `P:\scripts\3_game\entities\dayzanimal.c:24` |
| `DayZCreatureAI` | `DayZCreature` | `P:\scripts\3_game\entities\dayzanimal.c:191` |
| `DayZInfected` | `DayZCreatureAI` | `P:\scripts\3_game\entities\dayzinfected.c:104` |
| `DayZAnimal` | `DayZCreatureAI` | `P:\scripts\3_game\entities\dayzanimal.c:655` |
| `ZombieBase` | `DayZInfected` | `P:\scripts\4_world\entities\creatures\infected\zombiebase.c:1` |
| `AnimalBase` | `DayZAnimal` | `P:\scripts\4_world\entities\creatures\animals\animalbase.c:1` |

The script types are `DayZInfectedType` (`P:\scripts\3_game\entities\dayzinfectedtype.c:19`) and `DayZAnimalType` (`P:\scripts\3_game\entities\dayzanimaltype.c:1`), both children of `DayZCreatureAIType` (`P:\scripts\3_game\entities\dayzcreatureaitype.c:1`). The type reads the config path `CfgVehicles <class>` and its `AnimEvents` (`dayzcreatureaitype.c:13`).

In config, both families inherit `DZ_LightAI` (`P:\DZ\data\config.cpp:3079`): `DayZInfected` at `P:\DZ\characters\zombies\config.cpp:21` and `AnimalBase` at `P:\DZ\animals\config.cpp:17`. Nothing else in vanilla inherits `DZ_LightAI`, which is why vanilla has no human AI.

Each animal species has its own script class, for example `Animal_CanisLupus` (`animalbase.c:82`) and `Animal_CervusElaphus` (`animalbase.c:209`). Infected script classes split by sex in `zombiemalebase.c` and `zombiefemalebase.c` next to `zombiebase.c`.

## Commands

An AI creature always runs one animation command. The command handler starts a new one when the AI wants something different.

Infected commands (`P:\scripts\3_game\entities\dayzinfected.c`):

- IDs in `DayZInfectedConstants` (`:1`): `COMMANDID_MOVE`, `COMMANDID_VAULT`, `COMMANDID_DEATH`, `COMMANDID_HIT`, `COMMANDID_ATTACK`, `COMMANDID_CRAWL`, `COMMANDID_SCRIPT`.
- Starters on `DayZInfected`: `StartCommand_Move()` (`:108`), `StartCommand_Vault(int pType)` (`:109`), `StartCommand_Death(int pType, float pDirection)` (`:110`), `StartCommand_Hit(bool pHeavy, int pType, float pDirection)` (`:111`), `StartCommand_Attack(EntityAI pTarget, int pType, float pSubtype)` (`:112`), `StartCommand_Crawl(int pType)` (`:113`).
- `CanAttackToPosition(vector pTargetPosition)` (`:115`) checks whether an attack can reach a point.
- Moddable wrappers of each command class exist in `P:\scripts\4_world\entities\dayzinfectedimplement.c:1`.

Animal commands (`P:\scripts\3_game\entities\dayzanimal.c`):

- IDs in `DayZAnimalConstants` (`:562`): `COMMANDID_MOVE`, `COMMANDID_JUMP`, `COMMANDID_DEATH`, `COMMANDID_HIT`, `COMMANDID_ATTACK`, `COMMANDID_SCRIPT`.
- Starters on `DayZAnimal`: `StartCommand_Death(int pType, int pDirection)`, `StartCommand_Move()`, `StartCommand_Jump()`, `StartCommand_Attack()`, `StartCommand_Hit(int pType, int pDirection)` (`:666` to `:670`).
- `SignalAIAttackStarted()` and `SignalAIAttackEnded()` (`:677`, `:678`) tell the AI an attack began or ended; the vanilla handler calls them around every attack.

## Fully scripted commands

For movement vanilla does not have, write your own command class and start it with `StartCommand_ScriptInst(typename)`.

- Infected: `DayZInfectedCommandScript` (`dayzinfected.c:67`), started by `StartCommand_Script` or `StartCommand_ScriptInst` (`:122`, `:123`). Its constructor takes the `DayZInfected` as the first parameter (`:70`). Override `PostPhysUpdate(float pDt)` (`:94`); return false or call `SetFlagFinished(true)` (`:77`) to end it.
- Animals: `DayZAnimalCommandScript` (`dayzanimal.c:619`), started the same way (`:673`, `:674`).
- The engine owns the instance once it is running. The vanilla warning (`dayzinfected.c:61` to `:65`) says deleting it while it runs crashes the game, so prefer `StartCommand_ScriptInst` and never hold a `ref` to it.

## Command handler order

`ZombieBase.CommandHandler` (`zombiebase.c:198`) runs every simulation step on the side that simulates the infected, in this order:

1. `ModCommandHandlerBefore`; return true to skip everything below.
2. `HandleDeath`.
3. `HandleMove` and `HandleOrientation` (they copy speed and heading into sync variables).
4. If the current command finished, start `StartCommand_Move()` and stop.
5. `ModCommandHandlerInside`.
6. `HandleCrawlTransition`, `HandleDamageHit`.
7. With the input controller: `HandleVault`, `HandleMindStateChange` (`:450`), `FightLogic` (`:613`).
8. `ModCommandHandlerAfter`.

`DayZAnimal.CommandHandler` (`dayzanimal.c:722`) has the same three mod hooks around `HandleDeath` (`:791`), `HandleDamageHit`, then jump and attack from the input controller.

The three hooks are declared on `DayZCreature` (`dayzanimal.c:175`, `:180`, `:185`) and return false by default. Override them in a `modded class ZombieBase` or your own subclass; call `super` unless you mean to replace vanilla handling. Vanilla `DayZAnimal` already overrides `ModCommandHandlerBefore` for its cinematic controller (`dayzanimal.c:433`), so always call `super` there.

## Input controllers: what the AI wants

The engine AI writes its decisions into an input controller; the command handler reads them. Script can read the decisions, and can override them.

- `DayZCreatureAIInputController` (`P:\scripts\3_game\entities\dayzcreatureaiinputcontroller.c:1`): `OverrideMovementSpeed(bool state, float movementSpeed)`, `OverrideTurnSpeed`, `OverrideHeading(bool state, float heading)`, `OverrideJump`, `OverrideLookAt(bool state, vector direction)`, `OverrideAlertLevel(bool state, bool alerted, int level, float inLevel)`, `OverrideBehaviourSlot(bool state, int slot)`, and the matching getters. Pass `state = false` to hand control back to the AI.
- `DayZInfectedInputController` (`P:\scripts\3_game\entities\dayzinfectedinputcontroller.c:1`) adds `IsVault()`, `GetVaultHeight()`, `GetMindState()` and `GetTargetEntity()`.
- `DayZAnimalInputController` (`P:\scripts\3_game\entities\dayzanimalinputcontroller.c:49`) adds `IsDead()`, `IsAttack()`, `OverrideBehaviourAction(bool state, int action)` and `GetBehaviourAction()`. The slots and actions are the enums `DayZAnimalBehaviourSlot` (`:2`) and `DayZAnimalBehaviourAction` (`:26`).

Script never creates or destroys a controller (`dayzcreatureaiinputcontroller.c:30`); get it from `GetInputController()`.

## Infected mind states

`DayZInfectedConstants` (`dayzinfected.c:12` to `:18`) lists `MINDSTATE_CALM`, `MINDSTATE_DISTURBED`, `MINDSTATE_ALERTED`, `MINDSTATE_CHASE`, `MINDSTATE_FIGHT` and `MINDSTATE_COWER`. Movement states are `DayZInfectedConstantsMovement` (`:21`): idle, walk, run, sprint.

- The server reads the state every step in `HandleMindStateChange` (`zombiebase.c:454`) and syncs it: `RegisterNetSyncVariableInt("m_MindState", -1, 5)` (`zombiebase.c:54`). Clients read it with `GetMindStateSynced()` (`:182`).
- Vanilla attacks only in chase and fight (`zombiebase.c:618` to `:623`): chase uses the `CHASE` attack group, fight the `FIGHT` group.
- A stealth kill is refused once the infected is disturbed or higher (`P:\scripts\4_world\entities\dayzplayerimplementmeleecombat.c:447` to `:449`). A guard that should never be stealth killed must not sit in calm.

## Attacks

`DayZInfectedType.RegisterAttacks` (`dayzinfectedtype.c:49`) builds two groups from `DayZInfectedAttackGroupType` (`:13`): `CHASE` and `FIGHT`. Each `DayZInfectedAttackType` (`:1`) has distance, pitch, type, subtype, ammo, heavy flag, cooldown and probability. The ammo comes from config `AttackActions AttackShort`, `AttackLong` and `AttackRun` (`:57` to `:59`). `ChooseAttack(group, distance, pitch)` (`:96`) picks one. Cooldown drains at `GameConstants.AI_ATTACKSPEED` (1.5, `P:\scripts\3_game\constants.c:1126`).

## Damage and death hooks

- `DayZInfected.EEHitBy` (`dayzinfected.c:138`) applies shock as damage for nonlethal ammo, cripples legs above `LEG_CRIPPLE_THRESHOLD` 74 (`:129`), and sends the kill event once.
- `DayZAnimal.EEHitBy` (`dayzanimal.c:832`) creates wounds and queues a hit animation.
- `DayZCreatureAI.EEKilled` (`dayzanimal.c:237`) creates the body staging component used for skinning.
- Override these with `super` first to add loot, rewards or alarms.

## Classes you cannot mod

`AIWorld`, `AIGroup`, `AIAgent` and `AIGroupBehaviour` are rooted at `Managed` with private constructors (`P:\scripts\3_game\ai\aiworld.c:70`, `aigroup.c:1`, `aiagent.c:1`, `aigroupbehaviour.c:1`). Use them; do not `modded class` them (see `_shared/enscript/patterns/modded_class.md`).
</content>
</invoke>
