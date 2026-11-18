# Dust agents, protective gear and symptoms

The two dust agents the 1.30 sandstorm puts on a player (silicosis and eye irritation), the gear that stops each one, and the symptoms each causes. Checked on `P:\` (DayZ 1.30).

## Enums and constants

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

The modifiers are `MDF_SANDSTORM_EXPOSURE_STATIC`, `MDF_SANDSTORM_EXPOSURE_DYNAMIC`, `MDF_PARTICLES_BREATH`, `MDF_PARTICLES_EYES` and `MDF_HEAT_STROKE1` to `MDF_HEAT_STROKE4` (`P:\scripts\4_world\classes\playermodifiers\emodifiers.c:62` to `:69`). The enum starts at `MDF_TEMPERATURE = 1` (`emodifiers.c:3`) and has no explicit numbers after that, so use the names, never integers copied from a list.

## How the agents get in

`SandstormExposureMdfrBase.TransmitAgents` sends the agent through `AGT_AIRBOURNE_SOLID` and sends nothing to an unconscious player (`P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\sandstormexposure.c:45` to `:51`). The base dose is 1.0 agent per second for each agent (`SILICOSIS_AGENTS_PER_SEC`, `sandstormexposure.c:16` to `:17`).

| Modifier | Active when | Dose |
|---|---|---|
| `SandstormExposureDynamicMdfr` | a storm is active and `GetIntensityForPlayer` is above 0 (`sandstormexposure.c:101` to `:104`) | base dose times the player's intensity (`sandstormexposure.c:116` to `:121`) |
| `SandstormExposureStaticMdfr` | switched on and off by a zone, never by its own conditions | base dose, no intensity (its `OnTick`, `sandstormexposure.c:76` to `:80`) |

The only vanilla zone that uses the static modifier is `SandstormZoneSmall_TESTONLY` (`P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\sandstormexposure.c:1` to `:11`). It is a test class; do not place it on a live server.

## Which gear stops which agent

```c
// P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:414
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

- Silicosis is stopped only by an item in the `MASK` category with `DEF_DUST_PARTICLE_BREATH`. Eyewear does nothing against it.
- Eye irritation is stopped by `DEF_DUST_PARTICLE_EYES` on eyewear, a mask or night vision goggles.
- `GetProtectionLevelCachedEquipment` looks at attachments up to depth 2 and adds up the `GetProtectionLevel(type)` of every match (`P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:577` to `:592`).

## Writing the protection into an item

`ItemBase.GetProtectionLevel` reads the value from the item's `class Protection` in `CfgVehicles`: `DEF_DUST_PARTICLE_BREATH` reads `dust_particle_breath` and `DEF_DUST_PARTICLE_EYES` reads `dust_particle_eyes` (`P:\scripts\4_world\entities\itembase.c:4088` to `:4092`, path built at `:4099`).

Vanilla values to copy from:

| Item | `dust_particle_breath` | `dust_particle_eyes` | Where |
|---|---|---|---|
| `GasMask` | 1 | 1 | `dust_particle_breath` at `P:\DZ\characters\masks\config.cpp:138` |
| `NioshFaceMask` | 1 | none | `dust_particle_breath` at `P:\DZ\characters\masks\config.cpp:259` |
| `SurgicalMask` | 0.25 | none | `dust_particle_breath` at `P:\DZ\characters\masks\config.cpp:1710` |
| `BalaclavaMask_ColorBase` | 0.45 | none | `dust_particle_breath` at `P:\DZ\characters\masks\config.cpp:373` |
| `TacticalGoggles` | none | 1 | `dust_particle_eyes` at `P:\DZ\characters\glasses\config.cpp:684` |
| `SportGlasses_ColorBase` | none | 0.7 | `dust_particle_eyes` at `P:\DZ\characters\glasses\config.cpp:117` |
| `AviatorGlasses` | none | 0.4 | `dust_particle_eyes` at `P:\DZ\characters\glasses\config.cpp:259` |

The worn model, slots and the rest of the clothing class are wearables work: `_shared/wearables/references/protection-and-insulation.md`.

## The agents

| Agent | `m_MaxCount` | `m_TransferabilityIn` | `m_DieOffSpeed` | Where |
|---|---|---|---|---|
| `SilicosisAgent` | 1000 | 3.5 | 0.9 | `Init`, `P:\scripts\4_world\classes\transmissionagents\agents\silicosisagent.c:3` to `:15` |
| `EyesIrritationAgent` | 100 | 1.0 | 0.30 | `Init`, `P:\scripts\4_world\classes\transmissionagents\agents\eyesirritation.c:3` to `:15` |

Both return 0 from `GetDieOffSpeedEx` while the player is unconscious (`silicosisagent.c:18` to `:24`), so neither wears off during a blackout.

## `SilicosisMdfr` (`MDF_PARTICLES_BREATH`)

Active while `GetSingleAgentCount(eAgents.SILICOSIS)` is above 0 (`P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\silicosis.c:36` to `:38`), ticking every 5 s (`m_TickIntervalActive`, `silicosis.c:33`). `OnActivate` already queues `SYMPTOM_FAINT` (`silicosis.c:56`).

| Agent count | Effect |
|---|---|
| above 0, rising from 200 (`HEAVY_BREATH_TRESHOLD_MIN`, `silicosis.c:15`) | `HEAVY_BREATHING` sound events at any agent count: the intensity is `Math.Remap(HEAVY_BREATH_TRESHOLD_MIN, 1000, 0.1, 1.0, agentsCount)`, which clamps by default (`silicosis.c:90`; `P:\scripts\1_core\proto\enmath.c:740` to `:746`), so below 200 it stays at 0.1: a 10% chance about every 22.8 s, checked on the 5 s tick. From 200 the chance rises toward 1.0 and the interval toward 3 s at 1000 agents (`silicosis.c:16` to `:17`, `:91` to `:105`) |
| 600 or more (`STAMINA_LIMIT_TRESHOLD`, `silicosis.c:3`) | stamina modifier `DISEASE_PNEUMONIA` (`silicosis.c:112` to `:115`) |
| above 700 (`HEALTH_THRESHOLD`, `silicosis.c:4`) and still rising | `AddHealth` with a loss scaled from `HEALTH_LOSS` 2.0 (`silicosis.c:13`, `:133` to `:136`) |
| above 800 (`UNCON_THRESHOLD`, `silicosis.c:5`) | the faint effect, then unconsciousness for 5 to 10 s every 60 to 120 s with shock set to 25 (`UNCONSCIOUSNESS_LENGTH_MIN` and the three constants after it, `silicosis.c:8` to `:11`; `RequestUnconsciousness`, `silicosis.c:202` to `:208`) |

## `IrritatedEyesMdfr` (`MDF_PARTICLES_EYES`)

Active while `GetSingleAgentCount(eAgents.EYES_IRRITATION)` is above 0 (`P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\irritatedeyes.c:19` to `:21`), with the sync bit `MODIFIER_SYNC_PARTICLE_EYES` (`irritatedeyes.c:14`). The screen effect starts at 15 agents (`AGENTS_LIMIT`, `irritatedeyes.c:79` to `:88`).

Washing the head removes 10 agents, or 1.6 from a bottle (`heat-stroke.md`).

## Squinting and coughing

- `SandstormExposureMdfrBase.OnActivate` queues `SYMPTOM_SQUINT` (`sandstormexposure.c:32` to `:34`). On the client, `SquintSymptom.OnUpdateClient` looks for `DEF_DUST_PARTICLE_EYES` on eyewear or a mask, depth 2, and takes the first item with any protection (`P:\scripts\4_world\classes\playersymptoms\states\secondary\squintstate.c:25` to `:39`).
- `HandleCoughing` looks for `DEF_DUST_PARTICLE_BREATH` on eyewear or a mask, not on night vision goggles (`sandstormexposure.c:124` to `:141`). Cough strength is intensity minus protection, clamped to 0 to 1 (`coughIntensity`, `sandstormexposure.c:143`), and the interval runs from `COUGH_INTERVAL_MAX` 25 s down to `COUGH_INTERVAL_MIN` 3 s (`sandstormexposure.c:85` to `:86`). A mask stops the cough only when its protection covers the storm's intensity.

The two checks differ from the agent check above: squint and cough take the first protecting item, while agent transmission adds up every item.

## Testing in game

During a storm on a local test server (`sandstorm.md`, "Testing a storm in game"): with a dust mask, no cough and no silicosis; with glasses, no squint.
