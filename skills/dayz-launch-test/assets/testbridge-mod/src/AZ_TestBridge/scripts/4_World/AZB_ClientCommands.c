#ifdef DIAG_DEVELOPER
// AZ_TestBridge client peer: what the local player owns, and the camera.
// Getting in and out uses the real actions, so the server mirrors the crew
// (references/test-cell-vehicles.md); driving runs on this client, which owns
// the car while its player drives (AZB_CarDrive.c).

class AZB_ClientPeer : AZB_Peer
{
	static const int SEAT_TRIES = 3;
	static const float SEAT_WAIT_S = 5.0;
	static const float GET_OUT_WAIT_S = 10.0;
	static const float STOP_WAIT_S = 5.0;
	static const int MAX_COMPONENTS = 64;

	Camera m_Camera;
	CarScript m_Car;
	int m_Tries;
	float m_TryStarted;
	vector m_StartPos;
	float m_LastSample;
	float m_StopStarted;

	PlayerBase LocalPlayer()
	{
		return PlayerBase.Cast(GetGame().GetPlayer());
	}

	override bool IsReady()
	{
		PlayerBase player = LocalPlayer();
		return player && player.IsPlayerLoaded();
	}

	override void FillHello(AZB_Hello hello)
	{
		hello.player_loaded = IsReady();
		hello.player_count = 0;
		if (hello.player_loaded)
			hello.player_count = 1;
	}

	override bool Execute(AZB_Command c, AZB_Result r)
	{
		switch (c.cmd)
		{
			case "vehicle_state":
				return CmdVehicleState(c, r);
			case "get_in":
				return CmdGetIn(c, r);
			case "get_out":
				return CmdGetOut(c, r);
			case "drive":
				return CmdDrive(c, r);
			case "camera_set":
				return CmdCameraSet(c, r);
			case "camera_reset":
				return CmdCameraReset(c, r);
			case "hud":
				return CmdHud(c, r);
		}
		return super.Execute(c, r);
	}

	bool CmdVehicleState(AZB_Command c, AZB_Result r)
	{
		CarScript car = CarScript.Cast(FindByNetId(c.args.net_id));
		if (!car)
		{
			Fail(r, "not_a_car");
			return true;
		}
		AZB_VehicleRead.Fill(car, r.data);
		return true;
	}

	// The component of `transport` whose crew position is `seat`, or -1.
	int SeatComponent(Transport transport, int seat)
	{
		for (int component = 0; component < MAX_COMPONENTS; component++)
		{
			if (transport.CrewPositionIndex(component) == seat)
				return component;
		}
		return -1;
	}

	bool CmdGetIn(AZB_Command c, AZB_Result r)
	{
		PlayerBase player = LocalPlayer();
		if (!player)
		{
			Fail(r, "no_player");
			return true;
		}
		if (m_Step == 0)
		{
			if (player.GetCommand_Vehicle())
			{
				Fail(r, "already_in_vehicle");
				return true;
			}
			m_Car = CarScript.Cast(FindByNetId(c.args.net_id));
			if (!m_Car)
			{
				Fail(r, "not_a_car");
				return true;
			}
			m_Tries = 0;
			m_Step = 1;
		}
		if (player.GetCommand_Vehicle())
		{
			// confirmed on a later tick than the action start, as the real seat
			r.data.seated = true;
			r.data.tries = m_Tries;
			return true;
		}
		if (m_Step == 2 && m_Elapsed - m_TryStarted < SEAT_WAIT_S)
			return false;
		if (m_Tries >= SEAT_TRIES)
		{
			Fail(r, "not_seated");
			r.data.tries = m_Tries;
			return true;
		}
		int component = SeatComponent(m_Car, c.args.seat);
		if (component < 0)
		{
			Fail(r, "no_seat_component");
			return true;
		}
		ActionManagerClient manager = ActionManagerClient.Cast(player.GetActionManager());
		if (!manager)
		{
			Fail(r, "no_action_manager");
			return true;
		}
		ActionTarget target = new ActionTarget(m_Car, null, component, vector.Zero, 0);
		manager.PerformActionStart(ActionManagerBase.GetAction(ActionGetInTransport), target, null);
		m_Tries++;
		m_TryStarted = m_Elapsed;
		m_Step = 2;
		return false;
	}

	bool CmdGetOut(AZB_Command c, AZB_Result r)
	{
		PlayerBase player = LocalPlayer();
		if (!player)
		{
			Fail(r, "no_player");
			return true;
		}
		HumanCommandVehicle vehicleCommand = player.GetCommand_Vehicle();
		if (m_Step == 0)
		{
			if (!vehicleCommand)
			{
				Fail(r, "not_in_vehicle");
				return true;
			}
			ActionManagerClient manager = ActionManagerClient.Cast(player.GetActionManager());
			ActionTarget target = new ActionTarget(vehicleCommand.GetTransport(), null, -1, vector.Zero, 0);
			manager.PerformActionStart(ActionManagerBase.GetAction(ActionGetOutTransport), target, null);
			m_Step = 1;
			return false;
		}
		if (!vehicleCommand)
		{
			r.data.on_foot = true;
			return true;
		}
		if (m_Elapsed < GET_OUT_WAIT_S)
			return false;
		Fail(r, "still_seated");
		return true;
	}

	bool CmdDrive(AZB_Command c, AZB_Result r)
	{
		PlayerBase player = LocalPlayer();
		if (m_Step == 0)
		{
			HumanCommandVehicle vehicleCommand;
			if (player)
				vehicleCommand = player.GetCommand_Vehicle();
			if (vehicleCommand)
				m_Car = CarScript.Cast(vehicleCommand.GetTransport());
			else
				m_Car = null;
			if (!m_Car || m_Car.CrewDriver() != player)
			{
				Fail(r, "not_driver");
				return true;
			}
			m_StartPos = m_Car.GetPosition();
			r.data.samples = new array<ref AZB_Sample>;
			AZB_Drive.Begin(m_Car, c.args.throttle, c.args.steer, c.args.brake);
			m_LastSample = -1;
			m_Step = 1;
		}
		if (!m_Car)
		{
			AZB_Drive.Stop();
			Fail(r, "car_gone");
			return true;
		}
		float speed = m_Car.GetSpeedometer();
		if (speed > r.data.top_speed)
			r.data.top_speed = speed;
		float interval = 1.0 / c.args.sample_hz;
		if (m_Step == 1 && m_Elapsed - m_LastSample >= interval)
		{
			AZB_Sample sample = new AZB_Sample();
			sample.t = m_Elapsed;
			sample.speed = speed;
			sample.rpm = m_Car.EngineGetRPM();
			sample.gear = m_Car.GetGear();
			sample.pos = FromVector(m_Car.GetPosition());
			r.data.samples.Insert(sample);
			m_LastSample = m_Elapsed;
		}
		if (m_Step == 1 && m_Elapsed >= c.args.seconds)
		{
			r.data.distance = vector.Distance(m_StartPos, m_Car.GetPosition());
			AZB_Drive.BrakeToStop();
			m_StopStarted = m_Elapsed;
			m_Step = 2;
		}
		if (m_Step == 2)
		{
			if (Math.AbsFloat(speed) > 1.0 && m_Elapsed - m_StopStarted < STOP_WAIT_S)
				return false;
			AZB_Drive.Stop();
			return true;
		}
		return false;
	}

	bool CmdCameraSet(AZB_Command c, AZB_Result r)
	{
		vector pos = ToVector(c.args.pos);
		if (!m_Camera)
			Class.CastTo(m_Camera, GetGame().CreateObject("staticcamera", pos, true));
		if (!m_Camera)
		{
			Fail(r, "no_camera");
			return true;
		}
		// A staticcamera leaves the player's simulation on, so a later get-in still works (screenshots-and-cameras.md).
		m_Camera.SetPosition(pos);
		m_Camera.LookAt(ToVector(c.args.look_at));
		m_Camera.SetActive(true);
		r.data.camera_pos = FromVector(m_Camera.GetPosition());
		return true;
	}

	bool CmdCameraReset(AZB_Command c, AZB_Result r)
	{
		if (m_Camera)
		{
			m_Camera.SetActive(false);
			GetGame().ObjectDelete(m_Camera);
			m_Camera = null;
		}
		r.data.player_view = true;
		return true;
	}

	bool CmdHud(AZB_Command c, AZB_Result r)
	{
		Hud hud = GetGame().GetMission().GetHud();
		if (!hud)
		{
			Fail(r, "no_hud");
			return true;
		}
		hud.ShowHud(c.args.show);
		hud.ShowQuickBar(c.args.show);
		r.data.hud = c.args.show;
		return true;
	}
}
#endif
