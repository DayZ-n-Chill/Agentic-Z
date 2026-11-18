#ifdef DIAG_DEVELOPER
// AZ_TestBridge drive: throttle, steering and brake for the car the local
// player drives. The driver's client owns the car (playerbase.c:4561 to :4576),
// so the values are applied there, in CarScript.OnInput after super, where the
// engine reads them (carscript.c:1041). Only the client peer, which exists only
// with -azBridge=<token>, ever sets s_Car.

class AZB_Drive
{
	static const float UPSHIFT_GAP_S = 0.3;  // ShiftUp every tick skipped gears (vehicle-in-game-facts.md)

	static CarScript s_Car;
	static float s_Throttle;
	static float s_Steer;
	static float s_Brake;
	static bool s_Braking;
	static float s_Clock;
	static float s_LastUpshift;

	static void Begin(CarScript car, float throttle, float steer, float brake)
	{
		s_Car = car;
		s_Throttle = throttle;
		s_Steer = steer;
		s_Brake = brake;
		s_Braking = false;
		s_Clock = 0;
		s_LastUpshift = -1;
	}

	static void BrakeToStop()
	{
		s_Braking = true;
	}

	static void Stop()
	{
		s_Car = null;
		s_Braking = false;
	}

	static void Apply(CarScript car, float dt)
	{
		if (car.CrewDriver() != GetGame().GetPlayer())
			return;
		s_Clock += dt;
		if (s_Braking)
		{
			car.SetThrottle(0);
			car.SetSteering(0);
			car.SetBrake(1);
			return;
		}
		// A manual box needs a gear: first from neutral or reverse, then up near
		// the redline, as vanilla's own debug drive does (carscript.c:1159 to :1199).
		// An automatic box is left to the engine.
		if (car.GearboxGetType() == CarGearboxType.MANUAL && s_Throttle > 0)
		{
			if (car.GetGear() < CarGear.FIRST)
			{
				car.ShiftTo(CarGear.FIRST);
			}
			else if (car.EngineGetRPM() > car.EngineGetRPMRedline() * 0.8)
			{
				if (s_Clock - s_LastUpshift >= UPSHIFT_GAP_S)
				{
					car.ShiftUp();
					s_LastUpshift = s_Clock;
				}
			}
		}
		car.SetThrottle(s_Throttle);
		car.SetSteering(s_Steer);
		car.SetBrake(s_Brake);
		car.SetHandbrake(0);
	}
}

modded class CarScript
{
	override void OnInput(float dt)
	{
		super.OnInput(dt);
		if (AZB_Drive.s_Car == this)
			AZB_Drive.Apply(this, dt);
	}
}
#endif
