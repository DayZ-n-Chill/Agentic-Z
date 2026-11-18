# Motorbike configuration contract (`DZ_Vehicles_Singletrack`)

The `config.cpp` blocks of the vanilla single-track vehicles, taken from `P:\DZ\vehicles\singletrack\config.cpp`, and a table of the parameters with the code that reads each one. Short citations: `config.cpp:N` is `P:\DZ\vehicles\singletrack\config.cpp`, and a bare script file name is the file of that name under `P:\scripts\` (`motorbike_01.c` and `motorbike_02.c` are the ones in `4_world\entities\vehicles\inheritedmotorbikes\`). Line numbers match the 1.30 data on `P:\` at the time of writing; when a line has moved, Grep for the symbol.

The blocks are written the way a mod's `config.cpp` is written: one statement per line and short decimals. The unpacked file on `P:\` splits string arrays over several lines and prints single-precision values in full (`0.9` appears as `0.89999998`), so a cited range is longer than its block. Every block below was compared with its cited range token by token, numbers as single-precision values. `[EXACT]` marks a block or value read in the cited vanilla file.

---

## EXACT config.cpp Blocks

### 1. `MotorbikeScript` Base Class
```cpp
// [EXACT] P:\DZ\vehicles\singletrack\config.cpp:23-153
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

---

### 2. Complete `SimulationModule` of `Motorbike_01_ColorBase`
```cpp
// [EXACT] P:\DZ\vehicles\singletrack\config.cpp:263-378
		class SimulationModule: SimulationModule
		{
			neutralGearMaxSpeed = 1.3;
			class Steering
			{
				tipoverAngle = 50.0;
				maxSteeringAngle[] = {1,40,5,40,15,20,30,5,40,3,80,1};
				maxLeanAngle[] = {1,0,5,8,15,10,30,17,40,22,80,30};
				steerIncreaseSpeed[] = {0,80,40,60,80,40,120,20};
				steerDecreaseSpeed[] = {0,80,40,60,80,40,120,20};
				steerCenteringSpeed[] = {0,40,40,25,80,15,120,10};
				leanAngleMultiplier[] = {0,1,120,1};
				leanTargetResponsiveness[] = {0,2,120,2};
				leanVelocityResponsiveness[] = {0,8,120,8};
				directControl[] = {0.0,1.0,5.0,1.0,30.0,0.6,60.0,0.2,80.0,0.0};
			};
			class Throttle
			{
				reactionTime = 0.15;
				defaultThrust = 0.82;
				gentleThrust = 0.3;
				turboCoef = 1.5;
				gentleCoef = 0.8;
				slopeCoef = 0.75;
			};
			class Brakes
			{
				class Front
				{
					input = 1;
					pressureBySpeed[] = {0,0.85,10,0.7,40,0.6,60,0.5,80,0.5};
					gentleCoef = 0.5;
					minPressure = 0.15;
					reactionTime = 0.25;
					driverless = 0.2;
				};
				class Rear
				{
					input = 0;
					pressureBySpeed[] = {0,0.95,10,0.1,20,0.1,40,0.1,50,0.1};
					gentleCoef = 0.5;
					minPressure = 0.05;
					reactionTime = 0.25;
					driverless = 0.2;
				};
			};
			class Aerodynamics
			{
				frontalArea = 0.8;
				dragCoefficient = 0.85;
				downforceCoefficient = 0.0;
				downforceOffset[] = {0,0.2,0.5};
			};
			class Engine
			{
				torqueCurve[] = {400,0,1100,4,2500,7,4500,8,5500,7,6000,5,7000,0};
				inertia = 0.03;
				frictionTorque = 1;
				rollingFriction = 0.1;
				viscousFriction = 0.5;
				rpmIdle = 1200;
				rpmMin = 1400;
				rpmClutch = 1500;
				rpmRedline = 6000;
			};
			class Clutch
			{
				maxTorqueTransfer = 30;
				uncoupleTime = 0.2;
				coupleTime = 0.6;
			};
			class Gearbox
			{
				type = "GEARBOX_MANUAL";
				reverse = 2.94;
				ratios[] = {3.93,2.43,0.83};
			};
			class Wheels: Wheels
			{
				class Front: Front
				{
					maxBrakeTorque = 800;
					wheelHubMass = 10;
					wheelHubRadius = 0.15;
					casterOffset = 0.0;
					casterAngle = 25.0;
					class Suspension
					{
						stiffness = 5500;
						compression = 600;
						damping = 1150;
						travelMaxUp = 0.066;
						travelMaxDown = 0.066;
					};
					animDamper = "damperfront";
					inventorySlot = "Motorbike_01_Wheel_1";
				};
				class Rear: Rear
				{
					maxBrakeTorque = 1200;
					wheelHubMass = 10;
					wheelHubRadius = 0.15;
					driveRatio = 10.2789;
					class Suspension
					{
						stiffness = 7000;
						compression = 750;
						damping = 1350;
						travelMaxUp = 0.058;
						travelMaxDown = 0.043;
					};
					animDamper = "damperback";
					inventorySlot = "Motorbike_01_Wheel_2";
				};
			};
		};
```

---

### 3. Animation Sources in `Motorbike_01_ColorBase`
```cpp
// [EXACT] P:\DZ\vehicles\singletrack\config.cpp:379-399
		class AnimationSources: AnimationSources
		{
			class damper_1
			{
				source = "user";
				initPhase = 0.64;
				animPeriod = 1;
			};
			class damper_2
			{
				source = "user";
				initPhase = 0.607;
				animPeriod = 1;
			};
			class SeatDriver
			{
				source = "user";
				initPhase = 0.0;
				animPeriod = 1.0;
			};
		};
```
*(In `Motorbike_02_ColorBase`, `config.cpp:1569-1589`, `class coolant` is defined instead of `SeatDriver`.)*

---

### 4. `DamageSystem` and `DamageZones` of `Motorbike_01_ColorBase`
```cpp
// [EXACT] P:\DZ\vehicles\singletrack\config.cpp:400-989
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 1000;
					healthLevels[] = {{1.0,{}},{0.7,{}},{0.5,{}},{0.3,{}},{0.0,{}}};
				};
			};
			class DamageZones
			{
				class Chassis
				{
					displayName = "$STR_CfgVehicleDmg_Chassis0";
					fatalInjuryCoef = -1;
					componentNames[] = {"dmgZone_chassis"};
					class Health
					{
						hitpoints = 1000;
						transferToGlobalCoef = 0;
						RefTexsMats[] = {"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat"};
						healthLevels[] = {{1.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat"}},{0.7,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat"}},{0.5,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_damage.rvmat"}},{0.3,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_damage.rvmat"}},{0.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_destruct.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_destruct.rvmat"}}};
					};
					inventorySlots[] = {};
				};
				class Fender
				{
					displayName = "$STR_CfgVehicleDmg_Fender0";
					fatalInjuryCoef = -1;
					componentNames[] = {"dmgZone_fender"};
					class Health
					{
						hitpoints = 200;
						transferToGlobalCoef = 0;
						RefTexsMats[] = {"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender.rvmat"};
						healthLevels[] = {{1.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender.rvmat"}},{0.7,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender.rvmat"}},{0.5,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender_damage.rvmat"}},{0.3,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender_damage.rvmat"}},{0.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender_destruct.rvmat"}}};
					};
					inventorySlots[] = {};
					inventorySlotsCoefs[] = {};
				};
				class Engine
				{
					displayName = "$STR_CfgVehicleDmg_Engine0";
					fatalInjuryCoef = 0.001;
					memoryPoints[] = {"dmgZone_engine"};
					componentNames[] = {"dmgZone_engine"};
					class Health
					{
						hitpoints = 1000;
						transferToGlobalCoef = 1;
						RefTexsMats[] = {"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat"};
						healthLevels[] = {{1.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat"}},{0.7,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat"}},{0.5,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_damage.rvmat"}},{0.3,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_damage.rvmat"}},{0.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_destruct.rvmat"}}};
					};
					inventorySlots[] = {"SparkPlug"};
					inventorySlotsCoefs[] = {0.03};
				};
				class Front
				{
					displayName = "$STR_Motorbike_Front0";
					fatalInjuryCoef = -1;
					memoryPoints[] = {"dmgZone_front"};
					componentNames[] = {"dmgZone_front"};
					class Health
					{
						hitpoints = 700;
						transferToGlobalCoef = 0;
						RefTexsMats[] = {"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat"};
						healthLevels[] = {{1.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat"}},{0.7,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat"}},{0.5,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_damage.rvmat"}},{0.3,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_damage.rvmat"}},{0.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_destruct.rvmat"}}};
					};
					transferToZonesNames[] = {"Engine","Fender","Chassis"};
					transferToZonesCoefs[] = {0.75,0.6,0.8};
					inventorySlots[] = {"Motorbike_01_Wheel_1"};
					inventorySlotsCoefs[] = {0.5};
				};
				class Reflector_1_1
				{
					displayName = "$STR_CfgVehicleDmg_Reflector0";
					fatalInjuryCoef = -1;
					memoryPoints[] = {"dmgZone_lights_1_1"};
					componentNames[] = {"dmgZone_lights_1_1"};
					class Health
					{
						hitpoints = 10;
						transferToGlobalCoef = 0;
						RefTexsMats[] = {"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_glass.rvmat"};
						healthLevels[] = {{1.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_glass.rvmat"}},{0.7,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_glass.rvmat"}},{0.5,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_glass_damage.rvmat"}},{0.3,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_glass_damage.rvmat"}},{0.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_destruct.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_destruct.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_destruct.rvmat","hidden"}}};
					};
					transferToZonesNames[] = {"Front"};
					transferToZonesCoefs[] = {1.0};
					inventorySlots[] = {"Reflector_1_1"};
					inventorySlotsCoefs[] = {1.0};
				};
				class Back
				{
					displayName = "$STR_Motorbike_Back0";
					fatalInjuryCoef = -1;
					memoryPoints[] = {"dmgZone_back"};
					componentNames[] = {"dmgZone_back"};
					class Health
					{
						hitpoints = 1000;
						transferToGlobalCoef = 0;
						RefTexsMats[] = {"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_wheel.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_rear_brake.rvmat"};
						healthLevels[] = {{1.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_wheel.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_rear_brake.rvmat"}},{0.7,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_wheel.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_rear_brake.rvmat"}},{0.5,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_wheel_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_rear_brake_damage.rvmat"}},{0.3,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_wheel_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_damage.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_rear_brake_damage.rvmat"}},{0.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_colorized_destruct.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_noncolorized_destruct.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_wheel_destruct.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_destruct.rvmat","dz\vehicles\singletrack\motorbike_01\data\motorbike_01_lights_rear_brake_destruct.rvmat"}}};
					};
					transferToZonesNames[] = {"Engine","FuelTank"};
					transferToZonesCoefs[] = {0.05,0.3};
					inventorySlots[] = {"Motorbike_01_Wheel_2"};
					inventorySlotsCoefs[] = {0.1};
				};
				class FuelTank
				{
					displayName = "$STR_CfgVehicleDmg_FuelTank0";
					fatalInjuryCoef = -1;
					componentNames[] = {"dmgZone_fuelTank"};
					class Health
					{
						hitpoints = 400;
						transferToGlobalCoef = 0;
						healthLevels[] = {{1.0,{}},{0.7,{}},{0.5,{}},{0.3,{}},{0.0,{}}};
					};
					inventorySlots[] = {};
					inventorySlotsCoefs[] = {};
				};
			};
			class GUIInventoryAttachmentsProps
			{
				class Engine
				{
					name = "$STR_attachment_Engine0";
					description = "";
					icon = "set:dayz_inventory image:cat_vehicle_engine";
					attachmentSlots[] = {"SparkPlug"};
				};
				class Body
				{
					name = "$STR_attachment_Body0";
					description = "";
					icon = "set:dayz_inventory_additional image:motorcycle_body";
					attachmentSlots[] = {"Reflector_1_1"};
				};
				class Chassis
				{
					name = "$STR_attachment_Chassis0";
					description = "";
					icon = "set:dayz_inventory_additional image:motorcycle_chassis";
					attachmentSlots[] = {"Motorbike_01_Wheel_1","Motorbike_01_Wheel_2"};
				};
			};
		};
```

---

### 5. Wheel Classes (Normal and Ruined)
```cpp
// [EXACT] P:\DZ\vehicles\singletrack\config.cpp:154-219
	class Motorbike_01_Wheel_1: MotorbikeWheel
	{
		scope = 2;
		displayName = "$STR_MotorbikeWheel0";
		descriptionShort = "$STR_MotorbikeWheel1";
		model = "\DZ\vehicles\singletrack\Motorbike_01\proxy\Motorbike_01_wheel_1.p3d";
		inventorySlot[] = {"Motorbike_01_Wheel_1"};
		rotationFlags = 8;
		radius = 0.29;
		width = 0.06;
		tyreType = 1;
		tyreOffroadResistance = 0.7;
		tyreRollResistance = 0.01;
		tyreGrip = 0.85;
		tyreRoughness = 1.0;
		tyreLongitudinalFriction = 0.85;
		tyreLateralFriction = 3.0;
	};
	class Motorbike_01_Wheel_1_Ruined: Motorbike_01_Wheel_1
	{
		model = "\DZ\vehicles\singletrack\Motorbike_01\proxy\Motorbike_01_wheel_1_ruined.p3d";
		radius = 0.22;
		width = 0.2;
		tyreOffroadResistance = 0.02;
		tyreRollResistance = 0.7;
		tyreGrip = 0.25;
		tyreRoughness = 1.0;
		tyreLongitudinalFriction = 0.5;
		tyreLateralFriction = 0.5;
	};
	class Motorbike_01_Wheel_2: MotorbikeWheel
	{
		scope = 2;
		displayName = "$STR_MotorbikeWheel0";
		descriptionShort = "$STR_MotorbikeWheel1";
		model = "\DZ\vehicles\singletrack\Motorbike_01\proxy\Motorbike_01_wheel_2.p3d";
		inventorySlot[] = {"Motorbike_01_Wheel_2"};
		rotationFlags = 8;
		radius = 0.29;
		width = 0.14;
		tyreType = 1;
		tyreOffroadResistance = 0.7;
		tyreRollResistance = 0.008;
		tyreGrip = 0.85;
		tyreRoughness = 1.0;
		tyreLongitudinalFriction = 0.85;
		tyreLateralFriction = 6.0;
	};
	class Motorbike_01_Wheel_2_Ruined: Motorbike_01_Wheel_2
	{
		model = "\DZ\vehicles\singletrack\Motorbike_01\proxy\Motorbike_01_wheel_2_ruined.p3d";
		radius = 0.22;
		width = 0.2;
		tyreOffroadResistance = 0.02;
		tyreRollResistance = 0.8;
		tyreGrip = 0.35;
		tyreRoughness = 0.5;
		tyreLongitudinalFriction = 0.5;
		tyreLateralFriction = 0.5;
	};
```

---

## Complete Parameter Table: Motorbike_01 vs Motorbike_02

| Parameter / Block | Physical / functional meaning | Motorbike_01 value | Motorbike_02 value | Who reads / consumes it (Citation) |
|---|---|---|---|---|
| `simulation` | Enfusion physical simulation model | `"motorbike"` | `"motorbike"` | Native engine (`P:\bin\config.cpp:1486`) |
| `speedGeomActivation` | Distance / threshold to toggle hidden geometry | `0.29` | `0.27` | C++ engine (`config.cpp:258, 1448`) |
| `speedGeoms[]` | Component array to disable while moving | `{"geotohide"}` | `{"geotohide"}` | C++ engine (`config.cpp:259, 1449`) |
| `tipoverAngle` | Critical tipover lean angle | `50.0` | `60.0` | C++ engine / Steering (`config.cpp:268, 1458`) |
| `maxLeanAngle[]` | Maximum lean curve by speed (km/h, degrees) | `{1,0,5,8,15,10,30,17,40,22,80,30}` | `{1,0.0,5,8.0,10,12.0,30,20.0,60,30.0,120,40.0}` | C++ engine / Steering (`config.cpp:270, 1460`) |
| `maxSteeringAngle[]` | Maximum handlebar steering angle by speed | `{1,40,5,40,15,20,30,5,40,3,80,1}` | `{1,40.0,5,40.0,10,35.0,30,12.0,60,3.0,120,1.0}` | C++ engine / Steering (`config.cpp:269, 1459`) |
| `directControl[]` | Rider direct control factor vs auto-balance | `{0.0,1.0, ..., 80.0,0.0}` | `{0.0,1.0, ..., 80.0,0.0}` | C++ engine / Steering (`config.cpp:277, 1467`) |
| `Brakes.Front.input` | Input channel assigned to front brake | `1` (handbrake / lever) | `1` (handbrake / lever) | C++ engine / Brakes (`config.cpp:292, 1482`) |
| `Brakes.Rear.input` | Input channel assigned to rear brake | `0` (brake / pedal) | `0` (brake / pedal) | C++ engine / Brakes (`config.cpp:301, 1491`) |
| `Engine.torqueCurve[]` | Engine torque curve [RPM, Nm] | `{400,0, ..., 7000,0}` (peak 8 Nm at 4500 RPM) | `{400,4, ..., 7000,0}` (peak 36 Nm, plateau 3830-5142 RPM) | C++ engine (`config.cpp:318, 1508`) |
| `Engine.rpmIdle` | Revolutions per minute at idle | `1200` | `1300` | `EngineGetRPMIdle()` (`motorbike.c:151`); value in `config.cpp:323, 1513` |
| `Engine.rpmRedline` | Over-rev threshold with mechanical damage | `6000` | `6000` | `EngineGetRPMRedline()` (`motorbikescript.c:788`); value in `config.cpp:326, 1516` |
| `Gearbox.ratios[]` | Transmission ratios per gear | `{3.93, 2.43, 0.83}` (3 gears) | `{2.5, 1.3, 0.95, 0.55}` (4 gears) | C++ engine / Gearbox (`config.cpp:338, 1528`) |
| `Wheels.Front.casterAngle` | Fork forward rake angle (caster in degrees) | `25.0` | `27.0` | C++ engine (`config.cpp:348, 1538`) |
| `Wheels.Front.animDamper` | Front suspension animation name | `"damperfront"` | `"damperfront"` | C++ engine / AnimationSources (`config.cpp:357, 1547`) |
| `Wheels.Rear.animDamper` | Rear suspension animation name | `"damperback"` | `"damperback"` | C++ engine / AnimationSources (`config.cpp:374, 1564`) |
| `NoiseCarHorn.strength` | Acoustic loudness for AI detection when sounding horn | `30.0` | `30.0` | `vehiclehorncomponent.c:86` |
| `m_VehicleContactDamageCoef` | Collision damage multiplier to vehicle | `0.03` | `0.035` | `motorbikescript.c:1263` (`motorbike_01.c:5`, `motorbike_02.c:5`) |
| `m_CrewContactDamageCoef` | Collision damage multiplier to occupants | `0.018` | `0.012` | `motorbikescript.c:1264` (`motorbike_01.c:6`, `motorbike_02.c:6`) |
| `GetAnimInstance()` | Animation profile ID in Enfusion graph | `10` (`VehicleAnimInstances.MOTO1`) | `11` (`VehicleAnimInstances.MOTO2`) | `vehicles.agf:1570`, `vehicleaniminstances.c:13-14`, `motorbike_01.c:50` and `motorbike_02.c:51` |
| `GetTransportCameraDistance()` | 3rd person camera distance (script override, not config key) | `2.5` | `3.0` | `dayzplayercameravehicles.c:279`; value in `motorbike_01.c:40`, `motorbike_02.c:41` |
| `GetTransportCameraOffset()` | Camera offset in model space (script override, not config key) | `"0 1.3 -0.25"` | `"0 1.4 -0.3"` | `dayzplayercameravehicles.c:280`; value in `motorbike_01.c:45`, `motorbike_02.c:46` |

> Every row was checked against `P:\DZ\vehicles\singletrack\config.cpp` and the cited scripts. Units and meanings cannot be read from `config.cpp`.
> On build 1.30.164200 the values in this table are unchanged; the config of that build adds the front and brake reflector materials to both bikes and drops `itemBehaviour = 0` from `Motorbike_02_ShieldFront_ColorBase` (on `P:\` it is at `config.cpp:1106`). Those statements about 1.30.164200 are not yet checked on `P:\`.
