# Behaviour config: templates, alert, vision and noise

How a creature's engine AI is tuned in config: the `CfgAIBehaviours` template a creature points at, and the alert, vision and noise numbers inside it.

The behaviour graph itself is native code. Script cannot replace it, only override its output through the input controller (see `creatures.md`). Most "smarter" or "dumber" infected work is done here, in config.

## The link from creature to template

Every creature class names a template with `aiAgentTemplate`.

| Creature config | Template | Where |
|---|---|---|
| `ZombieBase` | `Infected` | `P:\DZ\characters\zombies\config.cpp:160` |
| `ZombieFemaleBase` | `InfectedFemale` | `P:\DZ\characters\zombies\config.cpp:423` |
| `ZombieMaleBase` | `InfectedMale` | `P:\DZ\characters\zombies\config.cpp:553` |
| `ZmbM_SoldierNormal_Base` | `InfectedMSoldier` | `P:\DZ\characters\zombies\config.cpp:9497` |
| `Animal_CanisLupus` | `Predators_Wolf` | `P:\DZ\animals\canis_lupus\config.cpp:37` |
| `Animal_CervusElaphus` | `Herbivores_CervusElaphus` | `P:\DZ\animals\cervus_elaphus\config.cpp:27` |

The templates live in `class CfgAIBehaviours` in `P:\DZ\AI\config.cpp:14` (addon `DZ_AI`, `:3`). The bear template `Predator_UrsusArctos` is in `P:\DZ\AI_bliss\config.cpp:16` (addon `DZ_AI_Bliss`).

Templates by family, all in `P:\DZ\AI\config.cpp`:

- Ambient life (hen, hare, fox): `AmbientLife` (`:16`), `AmbientLife_Gallus_Gallus_Domesticus` (`:155`), `AmbientLife_Lepus_Europaeus` (`:294`) and `AmbientLife_Vulpes_Vulpes` (`:440`). Each is declared with no parent and sets its own `teamName="AmbientLife"`.
- Herbivores: `Herbivores` (`:585`) and species classes such as `Herbivores_CervusElaphus` (`:4883`). Each is declared with no parent and sets its own `teamName="BigGame"`.
- Wolf: `Predators_Wolf` (`:5420`), `teamName="Predator"`.
- Infected: `Infected` (`:6214`), `teamName="Zombies"`. These are the only templates that inherit from each other, with children from `InfectedFemale` (`:6397`) to `InfectedMMummy` (`:6861`), for example `InfectedMSoldier` (`:6477`) and `InfectedRunner` (`:6797`).

Animal templates also name a group behaviour with `defaultGroupTemplateName`, for example `DZDeerGroupBeh` (`:589`) and `DZWolfGroupBeh` (`:5424`). The infected template has none. The group templates themselves, including the infected pack template `DZInfectedPackBeh`, are defined in `P:\DZ\data\aiconfigs\config.cpp` (see `patrols-and-guards.md`).

## Infected template layout

Inside `Infected` (`P:\DZ\AI\config.cpp:6214`):

| Class or key | Line | What it sets |
|---|---|---|
| `BehaviourHLZombie` | `:6219` | The high level behaviour. |
| `MovementWalk`, `MovementRun`, `MovementSprint` | `:6221`, `:6231`, `:6243` | `maxSpeed` 1.5, 3 and 9, acceleration, turn speed, and the `pathFilter` (`ZombieCalm` for walk, `ZombieAlerted` for run and sprint). |
| `SlotCalm` then `BehaviourZombieCalm` | `:6261` | Idle and wander timing: `StandingDurationMin/Max`, `WalkingDurationMin/Max`. |
| `SlotAlerted` then `BehaviourZombieAlerted` | `:6285` | `fightStateEnterDistance` 2 (`:6291`), `attractedSearchDistance` 15 (`:6303`), utility weights for vision, noise and damage, and `NoiseMakeAlert` (`:6326`, strength 40): the scream that alerts other infected. |
| `AlertSystem` | `:6333` | `visionToAlertMultiplier` 20, `noiseToAlertMultiplier` 1, `damageToAlertMultiplier` 10000, `noiseShotToAlertMultiplier` 1.7 (`:6335` to `:6338`); `Calm` and `Alerted` levels with `DropSpeed`, `DropDelay` and `MaxAlertValue` 20 and 100 (`:6339`, `:6345`). |
| `TargetSystemDZBase` | `:6355` | Vision: proximity, close and far ranges (`visionRangeMax` 40, `:6363`), field of view, peripheral vision, and multipliers for night (`visionNightMaxMult` 0.3, `:6372`), rain and fog. |
| `NoiseSystemParams` | `:6378` | Hearing: `rangeMax` 35 for ordinary noise, `rangeShotMax` 110 for shots (`:6381`, `:6383`), and `NoiseStrengthTeamMultipliers` per team (`:6389`). |

Children override only what differs. `InfectedMSoldier` (`:6477`) lowers its alert scream to strength 25 (`:6487`).

## Making your own variant

To make infected that see further or react harder to gunfire, add a new template and point your creature at it. Never edit the vanilla template in place for one creature, because every infected using it changes.

```cpp
class CfgPatches
{
    class MyMod_AI
    {
        units[] = {};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = { "DZ_AI", "DZ_Characters_Zombies" };
    };
};
class CfgAIBehaviours
{
    class InfectedMSoldier;
    class MyMod_InfectedGuard: InfectedMSoldier
    {
        // redeclare only the classes you change, each with its vanilla parent
    };
};
class CfgVehicles
{
    class ZmbM_SoldierNormal;
    class MyMod_ZmbM_Guard: ZmbM_SoldierNormal
    {
        scope = 2;
        aiAgentTemplate = "MyMod_InfectedGuard";
    };
};
```

Rules for the variant:

- Nested classes inherit only when you redeclare them with their parent, as vanilla does in `InfectedFemale` (`P:\DZ\AI\config.cpp:6397` to `:6433`). A nested class written without its parent loses every vanilla key it had.
- The two addons are `DZ_AI` (`P:\DZ\AI\config.cpp:3`) and `DZ_Characters_Zombies` (`P:\DZ\characters\zombies\config.cpp:3`).
- Vanilla never adds a template from another addon, so this is unverified until the in game test confirms the creature still moves and reacts. Check the server RPT for config errors after the first run.

## Creature config keys the AI reads

On `ZombieBase` (`P:\DZ\characters\zombies\config.cpp:24`):

- `class InputController` (`:79`): `movementSpeedMapping[]` maps idle, walk, run and sprint to speeds.
- `class NoiseTemplates` (`:161`): the noise its own steps make.
- `class DamageSystem` (`:169`): 100 global health by default.
- `class AttackActions` on the sex bases (`:436` for female): `AttackLong` and `AttackRun` with `ammoType`, `distance`, `cooldown`. Script reads the ammo from these names (see `creatures.md`, "Attacks").

## Noise classes

`CfgNoises` (`P:\DZ\AI\config.cpp:6903`) holds named noises such as `ZombieRoarNoise` and `WolfStepNoise`, each with `type`, `continuousRange` and `strength`. Weapons carry their own `NoiseShoot` class, for example strength 80 and type `shot` in `P:\DZ\weapons\firearms\akm\config.cpp:82`. Script loads any of these with `NoiseParams` (see `perception.md`).
