# Motorbike config: base class and key values

What the vanilla `MotorbikeScript` config class declares, and which key or script value of `Motorbike_01` and `Motorbike_02` does what and who reads it. In this file `config.cpp` alone means `P:\DZ\vehicles\singletrack\config.cpp`, `motorbikescript.c` means `P:\scripts\4_world\entities\vehicles\motorbikescript.c`, and `motorbike_01.c` and `motorbike_02.c` are in `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\`.

The other vanilla blocks are in two files: the `Motorbike_01` simulation and animation sources in `motorbike-simulation-config.md`, and its damage zones and wheel classes in `motorbike-damage-and-wheel-config.md`.

## How the blocks are written

The blocks are written the way a mod's `config.cpp` is: one statement per line and short decimals. The unpacked file on `P:\` splits string arrays over several lines and prints single-precision values in full (`0.9` shows as `0.89999998`), so a cited range is longer than its block. Each block matches its cited range token by token, comparing numbers as single-precision values.

## The `MotorbikeScript` class

From `config.cpp:23` to `:153`:

```cpp
class MotorbikeScript: Motorbike
{
	rotationFlags = 64;
	storageCategory = 4;
	debug_ItemCategory = 8;
	displayWeight = 0;
	insideSoundCoef = 0.9;
	fuelCapacity = 50;
	brakeFluidCapacity = 1;
	oilCapacity = 4;
	coolantCapacity = 6;
	brakeFluidLeakDebit[] = {0.0,0.0};
	oilLeakDebit[] = {0.0,0.0};
	coolantLeakDebit[] = {0.0,0.0};
	brakeFluidForceCoef[] = {0.0,1.0,1.0,1.0};
	damageFromOil[] = {0.0,0.0,1.0,0.0};
	damageFromCoolant[] = {0.0,0.0,1.0,0.0};
	engineBeltSlot = "EngineBelt";
	batterySlot = "CarBattery";
	electricPowerResName = "power";
	electricConsumptionIgnition = 3001;
	electricConsumptionEngine = 0.0;
	electricConsumptionLights = 0.0;
	electricOutputEngine = 5.0;
	selectionDashboard = "light_dashboard";
	selectionLightFrontL = "light_left";
	selectionLightFrontR = "light_right";
	selectionBrakeLights = "light_break";
	hasHistory = 1;
	class Crew
	{
		class Driver
		{
			actionSel = "seat_driver";
			proxyPos = "crewDriver";
			getInPos = "pos_driver";
			getInDir = "pos_driver_dir";
			isDriver = 1;
		};
		class CoDriver: Driver
		{
			actionSel = "seat_driver";
			proxyPos = "crewCoDriver";
			getInPos = "pos_codriver";
			getInDir = "pos_codriver_dir";
			isDriver = 1;
		};
	};
	class SimulationModule
	{
		class Wheels
		{
			class Front
			{
				inventorySlot = "";
				animTurn = "turnfront";
				animRotation = "wheelfront";
				animDamper = "damperfront";
				wheelHub = "wheel_1_damper_land";
			};
			class Rear
			{
				inventorySlot = "";
				animTurn = "turnback";
				animRotation = "wheelback";
				animDamper = "damperback";
				wheelHub = "wheel_2_damper_land";
			};
		};
	};
	attachments[] = {"CarBattery","Reflector_1_1","Reflector_2_1"};
	hiddenSelections[] = {""};
	hiddenSelectionsTextures[] = {""};
	hiddenSelectionsMaterials[] = {""};
	class AnimationSources
	{
		class HideDestroyed_1_1
		{
			source = "user";
			initPhase = 0;
			animPeriod = 0.001;
		};
		class HideDestroyed_1_2
		{
			source = "user";
			initPhase = 0;
			animPeriod = 0.001;
		};
		class HideDestroyed_2_1
		{
			source = "user";
			initPhase = 0;
			animPeriod = 0.001;
		};
		class HideDestroyed_2_2
		{
			source = "user";
			initPhase = 0;
			animPeriod = 0.001;
		};
		class AnimHitWheel_1
		{
			source = "Hit";
			hitpoint = "HitWheel_1";
			raw = 1;
		};
		class AnimHitWheel_2: AnimHitWheel_1
		{
			hitpoint = "HitWheel_2";
		};
	};
	class NoiseCarHorn
	{
		strength = 30.0;
		type = "sound";
	};
};
```

## Key values of the two vanilla bikes

Units and meanings are not written in `config.cpp`; the meaning column says what each key does in game.

| Key or method | Meaning | `Motorbike_01` | `Motorbike_02` | Read by, and where set |
|---|---|---|---|---|
| `simulation` | Simulation model | `"motorbike"` | `"motorbike"` | Native; set on `Motorbike` (`P:\bin\config.cpp:1486`) |
| `speedGeomActivation` | Threshold for hiding the speed geometry | `0.29` | `0.27` | Native (`config.cpp:258`, `:1448`) |
| `speedGeoms[]` | Components switched off while moving | `{"geotohide"}` | `{"geotohide"}` | Native (`config.cpp:259`, `:1449`) |
| `tipoverAngle` | Lean angle at which the bike tips over | `50.0` | `60.0` | Native, `Steering` (`config.cpp:268`, `:1458`) |
| `maxLeanAngle[]` | Maximum lean by speed (km/h, degrees) | `{1,0,5,8,15,10,30,17,40,22,80,30}` | `{1,0.0,5,8.0,10,12.0,30,20.0,60,30.0,120,40.0}` | Native, `Steering` (`config.cpp:270`, `:1460`) |
| `maxSteeringAngle[]` | Maximum bar angle by speed | `{1,40,5,40,15,20,30,5,40,3,80,1}` | `{1,40.0,5,40.0,10,35.0,30,12.0,60,3.0,120,1.0}` | Native, `Steering` (`config.cpp:269`, `:1459`) |
| `directControl[]` | Rider control against self-balance | `{0.0,1.0, ..., 80.0,0.0}` | `{0.0,1.0, ..., 80.0,0.0}` | Native, `Steering` (`config.cpp:277`, `:1467`) |
| `Brakes.Front.input` | Input channel of the front brake | `1` (handbrake, the lever) | `1` (handbrake, the lever) | Native, `Brakes` (`config.cpp:292`, `:1482`) |
| `Brakes.Rear.input` | Input channel of the rear brake | `0` (brake, the pedal) | `0` (brake, the pedal) | Native, `Brakes` (`config.cpp:301`, `:1491`) |
| `Engine.torqueCurve[]` | Torque curve, pairs of rpm and torque | `{400,0, ..., 7000,0}` (peak 8 Nm at 4500 rpm) | `{400,4, ..., 7000,0}` (peak 36 Nm, flat from 3830 to 5142 rpm) | Native (`config.cpp:318`, `:1508`) |
| `Engine.rpmIdle` | Idle rpm | `1200` | `1300` | `EngineGetRPMIdle()` (`P:\scripts\3_game\vehicles\motorbike.c:151`); value in `config.cpp:323`, `:1513` |
| `Engine.rpmRedline` | Rpm where over-revving starts | `6000` | `6000` | `EngineGetRPMRedline()` (`motorbikescript.c:788`); value in `config.cpp:326`, `:1516` |
| `Gearbox.ratios[]` | Ratio per gear | `{3.93, 2.43, 0.83}` (3 gears) | `{2.5, 1.3, 0.95, 0.55}` (4 gears) | Native, `Gearbox` (`config.cpp:338`, `:1528`) |
| `Wheels.Front.casterAngle` | Fork rake (caster, degrees) | `25.0` | `27.0` | Native (`config.cpp:348`, `:1538`) |
| `Wheels.Front.animDamper` | Front damper animation | `"damperfront"` | `"damperfront"` | Native, `AnimationSources` (`config.cpp:357`, `:1547`) |
| `Wheels.Rear.animDamper` | Rear damper animation | `"damperback"` | `"damperback"` | Native, `AnimationSources` (`config.cpp:374`, `:1564`) |
| `NoiseCarHorn.strength` | How far infected hear the horn | `30.0` | `30.0` | `vehiclehorncomponent.c:86` |
| `m_VehicleContactDamageCoef` | Contact damage to the bike | `0.03` | `0.035` | `motorbikescript.c:1263` (`motorbike_01.c:5`, `motorbike_02.c:5`) |
| `m_CrewContactDamageCoef` | Contact damage to the rider | `0.018` | `0.012` | `motorbikescript.c:1264` (`motorbike_01.c:6`, `motorbike_02.c:6`) |
| `GetAnimInstance()` | Rider set in the animation graph | `10` (`VehicleAnimInstances.MOTO1`) | `11` (`VehicleAnimInstances.MOTO2`) | `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1570`, `P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:13` and `:14`, `motorbike_01.c:50` and `motorbike_02.c:51` |
| `GetTransportCameraDistance()` | Third-person camera distance (script, not config) | `2.5` | `3.0` | `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:279`; value in `motorbike_01.c:40`, `motorbike_02.c:41` |
| `GetTransportCameraOffset()` | Camera offset in model space (script, not config) | `"0 1.3 -0.25"` | `"0 1.4 -0.3"` | `dayzplayercameravehicles.c:280`; value in `motorbike_01.c:45`, `motorbike_02.c:46` |

A later 1.30 stable build keeps every value in this table, adds the front and brake reflector materials to both bikes, and drops `itemBehaviour = 0` from `Motorbike_02_ShieldFront_ColorBase` (`config.cpp:1106` on `P:\`); not yet checked on `P:\`.
