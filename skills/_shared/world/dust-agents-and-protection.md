# Dust agents and protective gear

Covers the two agents a sandstorm puts on a player, silicosis and eye irritation, which gear stops each one, and the symptoms each one causes. The storm itself is in `sandstorm.md`; the worn item and its model are wearables work.

## Names to use in script

The agent IDs and the defence types:

```c
// P:\scripts\3_game\enums\eagents.c:14
	SILICOSIS 		= 512,
	EYES_IRRITATION	= 1024,
```

```c
// P:\scripts\3_game\constants.c:545
const int AGT_AIRBOURNE_SOLID	= 15;

const int DEF_BIOLOGICAL			= 1;
const int DEF_CHEMICAL				= 2;
const int DEF_DUST_PARTICLE_BREATH	= 3;
const int DEF_DUST_PARTICLE_EYES	= 4;
```

The modifiers are `MDF_SANDSTORM_EXPOSURE_STATIC`, `MDF_SANDSTORM_EXPOSURE_DYNAMIC`, `MDF_PARTICLES_BREATH`, `MDF_PARTICLES_EYES` and `MDF_HEAT_STROKE1` to `MDF_HEAT_STROKE4` (`P:\scripts\4_world\classes\playermodifiers\emodifiers.c:62` to `:69`). The enum starts at `MDF_TEMPERATURE = 1` (`emodifiers.c:3`) and gives no numbers after that, so always use the names. Integers copied from a list break as soon as the enum grows.

## How a storm passes the agents on

`SandstormExposureMdfrBase.TransmitAgents` sends each agent through `AGT_AIRBOURNE_SOLID` and sends nothing to an unconscious player (`P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\sandstormexposure.c:45` to `:51`). The base dose is 1.0 agent per second for each agent (`SILICOSIS_AGENTS_PER_SEC`, `sandstormexposure.c:16` and `:17`).

| Modifier | Active when | Dose |
|---|---|---|
| `SandstormExposureDynamicMdfr` | a storm is active and `GetIntensityForPlayer` is above 0 (`sandstormexposure.c:101` to `:104`) | base dose times the player's intensity (`:116` to `:121`) |
| `SandstormExposureStaticMdfr` | a zone switches it on and off; it has no conditions of its own | base dose, no intensity (`OnTick`, `:76` to `:80`) |

The only vanilla zone that uses the static modifier is `SandstormZoneSmall_TESTONLY` (`sandstormexposure.c:1` to `:11`). It is a test class; keep it off a live server.

## Which gear stops which agent

From `P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:414`:

```c
			case AGT_AIRBOURNE_SOLID:
				switch (sourceAgents)
				{
					float protectionLevel = 0.0;
					Man man = Man.Cast(target);

					case eAgents.SILICOSIS:
						protectionLevel = GetProtectionLevelCachedEquipment(
							DEF_DUST_PARTICLE_BREATH,
							ECachedEquipmentItemCategory.MASK,
							man,
						);
						break;				
					case eAgents.EYES_IRRITATION:
						protectionLevel = GetProtectionLevelCachedEquipment(
							DEF_DUST_PARTICLE_EYES,
							ECachedEquipmentItemCategory.EYEWEAR|ECachedEquipmentItemCategory.MASK|ECachedEquipmentItemCategory.NVG,
							man,
						);
						break;
				}
```

- Only an item in the `MASK` category with `DEF_DUST_PARTICLE_BREATH` stops silicosis. Glasses do nothing against it.
- `DEF_DUST_PARTICLE_EYES` on glasses, a mask or night vision goggles stops eye irritation.
- `GetProtectionLevelCachedEquipment` looks at attachments down to depth 2 and adds up `GetProtectionLevel(type)` of every match (`plugintransmissionagents.c:577` to `:592`).

## Giving an item protection

`ItemBase.GetProtectionLevel` reads the item's `class Protection` in `CfgVehicles`: `DEF_DUST_PARTICLE_BREATH` reads `dust_particle_breath` and `DEF_DUST_PARTICLE_EYES` reads `dust_particle_eyes` (`P:\scripts\4_world\entities\itembase.c:4088` to `:4092`; the path is built at `:4099`).

Vanilla values to copy:

| Item | `dust_particle_breath` | `dust_particle_eyes` | Source (class, then value) |
|---|---|---|---|
| `GasMask` | 1 | 1 | `P:\DZ\characters\masks\config.cpp:21`, `:138` |
| `NioshFaceMask` | 1 | none | `masks\config.cpp:161`, `:259` |
| `SurgicalMask` | 0.25 | none | `masks\config.cpp:1608`, `:1710` |
| `BalaclavaMask_ColorBase` | 0.45 | none | `masks\config.cpp:280`, `:373` |
| `TacticalGoggles` | none | 1 | `P:\DZ\characters\glasses\config.cpp:598`, `:684` |
| `SportGlasses_ColorBase` | none | 0.7 | `glasses\config.cpp:25`, `:117` |
| `AviatorGlasses` | none | 0.4 | `glasses\config.cpp:176`, `:259` |

The model, the slots and the rest of the clothing class are in `_shared/wearables/references/protection-and-insulation.md`.

## The two agents

| Agent | `m_MaxCount` | `m_TransferabilityIn` | `m_DieOffSpeed` | Source |
|---|---|---|---|---|
| `SilicosisAgent` | 1000 | 3.5 | 0.9 | `Init`, `P:\scripts\4_world\classes\transmissionagents\agents\silicosisagent.c:3` to `:15` |
| `EyesIrritationAgent` | 100 | 1.0 | 0.30 | `Init`, `P:\scripts\4_world\classes\transmissionagents\agents\eyesirritation.c:3` to `:15` |

Both return 0 from `GetDieOffSpeedEx` while the player is unconscious (`silicosisagent.c:18` to `:24`), so neither wears off during a blackout.

## Silicosis symptoms

`SilicosisMdfr` (`MDF_PARTICLES_BREATH`) is active while `GetSingleAgentCount(eAgents.SILICOSIS)` is above 0 (`P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\silicosis.c:36` to `:38`) and ticks every 5 s (`m_TickIntervalActive`, `silicosis.c:33`). `OnActivate` already queues `SYMPTOM_FAINT` (`:56`).

| Agent count | Effect |
|---|---|
| above 0 | `HEAVY_BREATHING` sound events. The intensity is `Math.Remap(HEAVY_BREATH_TRESHOLD_MIN, 1000, 0.1, 1.0, agentsCount)` (`silicosis.c:90`), and `Remap` clamps by default (`P:\scripts\1_core\proto\enmath.c:740` to `:746`), so below 200 it stays at 0.1: a 10% chance about every 22.8 s, checked on the 5 s tick. |
| from 200 (`HEAVY_BREATH_TRESHOLD_MIN`, `silicosis.c:15`) | the chance rises toward 1.0 and the interval falls toward 3 s at 1000 agents (`:16` and `:17`, `:91` to `:105`) |
| 600 or more (`STAMINA_LIMIT_TRESHOLD`, `:3`) | stamina modifier `DISEASE_PNEUMONIA` (`:112` to `:115`) |
| above 700 (`HEALTH_THRESHOLD`, `:4`) and still rising | `AddHealth` with a loss scaled from `HEALTH_LOSS` 2.0 (`:13`, `:133` to `:136`) |
| above 800 (`UNCON_THRESHOLD`, `:5`) | the faint effect, then unconsciousness for 5 to 10 s every 60 to 120 s, with shock set to 25 (`:8` to `:11`; `RequestUnconsciousness`, `:202` to `:208`) |

Vanilla spells the constants `TRESHOLD`; keep that spelling when you reference them.

## Eye irritation, squinting and coughing

`IrritatedEyesMdfr` (`MDF_PARTICLES_EYES`) is active while `GetSingleAgentCount(eAgents.EYES_IRRITATION)` is above 0 (`P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\irritatedeyes.c:19` to `:21`) and syncs through `MODIFIER_SYNC_PARTICLE_EYES` (`irritatedeyes.c:14`). The screen effect starts at 15 agents (`AGENTS_LIMIT`, `:79` to `:88`). Washing the head removes 10 agents, or 1.6 from a bottle (`heat-stroke.md`).

- `SandstormExposureMdfrBase.OnActivate` queues `SYMPTOM_SQUINT` (`sandstormexposure.c:32` to `:34`). On the client, `SquintSymptom.OnUpdateClient` looks for `DEF_DUST_PARTICLE_EYES` on glasses or a mask, depth 2, and uses the first item with any protection (`P:\scripts\4_world\classes\playersymptoms\states\secondary\squintstate.c:25` to `:39`).
- `HandleCoughing` looks for `DEF_DUST_PARTICLE_BREATH` on glasses or a mask, not on night vision goggles (`sandstormexposure.c:124` to `:141`). Cough strength is intensity minus protection, clamped to 0 to 1 (`coughIntensity`, `:143`), and the interval runs from `COUGH_INTERVAL_MAX` 25 s down to `COUGH_INTERVAL_MIN` 3 s (`:85` and `:86`). A mask stops the cough only when its protection covers the storm's intensity.

Squint and cough take the first protecting item; agent transmission adds up every item. Expect the two to disagree when a player wears more than one piece.

## Checking it in game

Start a storm on a local test server (`sandstorm.md`, section "Checking a storm in game"). With a dust mask the player neither coughs nor collects silicosis; with glasses the player does not squint.
