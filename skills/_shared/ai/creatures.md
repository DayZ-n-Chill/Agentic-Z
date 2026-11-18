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

The script types are `DayZInfectedType` (`P:\scripts\3_game\entities\dayzinfectedtype.c:19`) and `DayZAnimalType` (`P:\scripts\3_game\entities\dayzanimaltype.c:1`), both children of `DayZCreatureAIType` (`P:\scripts\3_game\entities\dayzcreatureaitype.c:1`). The type reads the config path `CfgVehicles <class>` and its `AnimEvents` (`dayzcreatureaitype.c:13` and `:14`).

In config, both families inherit `DZ_LightAI` (`P:\DZ\data\config.cpp:3079`): `DayZInfected` at `P:\DZ\characters\zombies\config.cpp:21` and `AnimalBase` at `P:\DZ\animals\config.cpp:17`. Nothing else in vanilla inherits `DZ_LightAI`, which is why vanilla has no human AI.

Each animal species has its own script class, for example `Animal_CanisLupus` (`animalbase.c:82`) and `Animal_CervusElaphus` (`animalbase.c:209`). The Nasdara animals have theirs in the same file: `Animal_OvisGmelini` (mouflon, `:375`), `Animal_VaranusGriseus` (monitor lizard, `:512`), `Animal_CanisFamiliaris_Dobermann_ColorBase` (`:600`) and `Animal_CanisFamiliaris_GermanShepherd_ColorBase` (`:626`); the two dog bases copy the wolf's hit components and `IsDanger()` (`:602` to `:617`, against the wolf at `:84` to `:99`). Infected script classes split by sex in `zombiemalebase.c` and `zombiefemalebase.c` next to `zombiebase.c`.

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

The three hooks are declared on `DayZCreature` (`dayzanimal.c:175`, `:180`, `:185`) and return false by default. Override them in a `modded class ZombieBase` or your own subclass; call `super` unless you mean to replace vanilla handling. Vanilla `DayZCreatureAI` already overrides `ModCommandHandlerBefore` for its cinematic controller (`dayzanimal.c:433`), so both infected and animals inherit it; always call `super` there.

## Input controllers: what the AI wants

The engine AI writes its decisions into an input controller; the command handler reads them. Script can read the decisions, and can override them.

- `DayZCreatureAIInputController` (`P:\scripts\3_game\entities\dayzcreatureaiinputcontroller.c:1`): `OverrideMovementSpeed(bool state, float movementSpeed)`, `OverrideTurnSpeed`, `OverrideHeading(bool state, float heading)`, `OverrideJump`, `OverrideLookAt(bool state, vector direction)`, `OverrideAlertLevel(bool state, bool alerted, int level, float inLevel)`, `OverrideBehaviourSlot(bool state, int slot)`, and the matching getters. Pass `state = false` to hand control back to the AI.
- `DayZInfectedInputController` (`P:\scripts\3_game\entities\dayzinfectedinputcontroller.c:1`) adds `IsVault()`, `GetVaultHeight()`, `GetMindState()` and `GetTargetEntity()`.
- `DayZAnimalInputController` (`P:\scripts\3_game\entities\dayzanimalinputcontroller.c:49`) adds `IsDead()`, `IsAttack()`, `OverrideBehaviourAction(bool state, int action)` and `GetBehaviourAction()`. The slots and actions are the enums `DayZAnimalBehaviourSlot` (`:2`) and `DayZAnimalBehaviourAction` (`:26`).

Script never creates or destroys a controller (`dayzcreatureaiinputcontroller.c:30`); get it from `GetInputController()`.

## Infected mind states

`DayZInfectedConstants` (`dayzinfected.c:12` to `:18`) lists `MINDSTATE_CALM`, `MINDSTATE_DISTURBED`, `MINDSTATE_ALERTED`, `MINDSTATE_CHASE`, `MINDSTATE_FIGHT` and `MINDSTATE_COWER`. Movement states are `DayZInfectedConstantsMovement` (`:21`): idle, walk, run, sprint.

- The server reads the state every step in `HandleMindStateChange` (`zombiebase.c:454`) and syncs it: `RegisterNetSyncVariableInt("m_MindState", -1, 5)` (`zombiebase.c:54`). Clients read it with `GetMindStateSynced()` (`:182`).
- When the state changes, `HandleMindStateChange` sets the idle animation with `SetIdleState`: calm 0, disturbed 1, chase 2 (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:459` to `:472`). Chase sets its pose only when the infected comes from a lower state (`:470`). Every change also resets the attack cooldown and marks the sync variables dirty (`:482` and `:483`).
- `MINDSTATE_COWER` is new in 1.30 (not checkable on `P:\`, which holds 1.30 only) and is the sandstorm state. The infected goes back to the calm idle pose with `SetIdleState(0)`; the vanilla comment says the AI has already stopped its movement (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:474` to `:478`). What puts an infected into the cower state is engine code; script only shows this reaction. A mod that switches on the mind state in `HandleMindStateChange` or in its own hooks must handle this value, or the creature falls through the switch. A custom infected that registers its own `m_MindState` sync range must keep it wide enough for the value 5.
- Vanilla attacks only in chase and fight (`zombiebase.c:618` to `:623`): chase uses the `CHASE` attack group (`:704`), fight the `FIGHT` group (`:749`).
- A stealth kill is refused once the infected is disturbed or higher (`P:\scripts\4_world\entities\dayzplayerimplementmeleecombat.c:447` to `:449`), which includes cower, the highest value. A guard that should never be stealth killed must not sit in calm.

## Attacks

`DayZInfectedType.RegisterAttacks` (`dayzinfectedtype.c:49`) builds two groups from `DayZInfectedAttackGroupType` (`:13`): `CHASE` and `FIGHT`. Each `DayZInfectedAttackType` (`:1`) has distance, pitch, type, subtype, ammo, heavy flag, cooldown and probability. The ammo comes from config `AttackActions AttackShort`, `AttackLong` and `AttackRun` (`:57` to `:59`). `ChooseAttack(group, distance, pitch)` (`:96`) picks one. Cooldown drains at `GameConstants.AI_ATTACKSPEED` (1.5, `P:\scripts\3_game\constants.c:1126`), and only in the fight state (`zombiebase.c:733` to `:737`); the chase logic has no cooldown check.

Before `ZombieBase` starts an attack (`ChaseAttackLogic` at `zombiebase.c:682`, `FightAttackLogic` at `:723`):

- The target is whatever `GetTargetEntity()` returns; a player in a vehicle is never attacked (`:689`, `:730`).
- `CanAttackToPosition` must pass, and the target must be the first melee target in a cone of `TARGET_CONE_ANGLE_CHASE` 20 or `TARGET_CONE_ANGLE_FIGHT` 30 degrees (`:3`, `:4`, `:707`, `:752`).
- Damage lands only when the attack command reports `WasHit()` and the target is still within the attack's distance (`:631`, `:649`). A player blocking and facing the infected takes `MeleeZombie` from a heavy attack and `Dummy_Light` from a light one instead of the attack's ammo (`:652` to `:664`).

A custom target (a guard post, a decoy object) that the engine AI never returns from `GetTargetEntity()` is never attacked by this code.

## Damage and death hooks

- `DayZInfected.EEHitBy` (`dayzinfected.c:138`) turns the shock of nonlethal ammo (`transferShockToDamage` 1) into health damage and sends the kill event once (`:142` to `:176`). Only that nonlethal shock is checked against `LEG_CRIPPLE_THRESHOLD` 74 (`:129`): 74 or more on a leg zone sets that leg's health to 0, and on the torso or head forces a heavy hit (`HandleSpecialZoneDamage`, `:193` to `:203`). Ordinary bullets do not cripple through this code.
- `DayZAnimal.EEHitBy` (`dayzanimal.c:832`) turns nonlethal shock into health damage the same way, otherwise creates wounds, then queues a hit animation (`:837` to `:853`).
- `DayZCreatureAI.EEKilled` (`dayzanimal.c:237`) creates the body staging component used for skinning. The vanilla comment on that line says it is never called on clients in multiplayer, which is why skinning does not work properly there (`:240`).
- `ZombieBase.HandleDamageHit` (`zombiebase.c:867`) always plays the hit reaction for a heavy hit or while the infected is calm or disturbed; otherwise the chance is `SHOCK_TO_STUN_MULTIPLIER` 2.82 times the shock, out of 100 (`:7`, `:884` to `:886`). A new hit reaction waits at least `HIT_INTERVAL_MIN` 0.3 seconds after the last (`:864`, `:872`).
- Override these with `super` first to add loot, rewards or alarms.

## Classes you cannot mod

`AIWorld`, `AIGroup`, `AIAgent` and `AIGroupBehaviour` are rooted at `Managed` with private constructors (`P:\scripts\3_game\ai\aiworld.c:70`, `aigroup.c:1`, `aiagent.c:1`, `aigroupbehaviour.c:1`). Use them; do not `modded class` them (see `_shared/enscript/patterns/modded_class.md`).
