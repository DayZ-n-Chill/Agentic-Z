# Motorbike simulation config

What the vanilla `SimulationModule` and `AnimationSources` of `Motorbike_01_ColorBase` hold, as a starting point for a new bike's handling. In this file `config.cpp` alone means `P:\DZ\vehicles\singletrack\config.cpp`. The blocks are written the way a mod writes them, with short decimals; `motorbike-config-contract.md` says how they compare with the unpacked file, and holds the values of `Motorbike_02` side by side.

## `SimulationModule`

From `P:\DZ\vehicles\singletrack\config.cpp:267` to `:382`. There is no `Axles` block: `Wheels` holds `Front` and `Rear` directly, and the front brake sits on the handbrake channel (`input = 1`).

```cpp
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

## `AnimationSources`

From `config.cpp:383` to `:403`. `SeatDriver` drives the flip-up seat: `Motorbike_01_ColorBase.CanGetIn()` refuses entry unless its phase is 0 (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:89` to `:95`), so a bike that copies the source but never closes the seat cannot be mounted.

```cpp
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

`Motorbike_02_ColorBase` (`config.cpp:1576` to `:1596`) declares the same two dampers with `initPhase` `0.64` and `0.607`, and a `coolant` source (`source = "user"`, `initPhase = 0`, `animPeriod = 1`) in place of `SeatDriver`.
