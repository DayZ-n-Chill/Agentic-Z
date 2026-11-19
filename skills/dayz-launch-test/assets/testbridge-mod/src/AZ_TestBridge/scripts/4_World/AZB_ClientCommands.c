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
	bool m_HudHidden;
	CarScript m_Car;
	int m_Tries;
	float m_TryStarted;
	vector m_StartPos;
	float m_LastSample;
	float m_StopStarted;

	// look_at steers the local player's aim every frame (KeepView). Walking runs on the server.
	bool m_Looking;
	vector m_LookTarget;
	float m_YawError;
	float m_PitchError;

	static const float LOOK_GAIN = 0.2;
	static const float LOOK_DONE_DEG = 2.0;
	static const float LOOK_TIMEOUT_S = 6.0;
	static const int MAX_WIDGETS = 300;

	// Called every frame: a player camera change (getting out of a car ends with
	// one) takes the view back, so the scripted camera is made active again; a
	// turn feeds the player's own aim input (human.c:259 and :262).
	void KeepView()
	{
		if (m_Camera && !m_Camera.IsActive())
			m_Camera.SetActive(true);
		PlayerBase player = LocalPlayer();
		if (!m_Looking || !player || !player.GetInputController())
			return;
		HumanInputController input = player.GetInputController();
		// ENABLED holds until DISABLED is passed (human.c:10); StopSteering clears it.
		input.SetDisabled(false);
		MeasureLook();
		input.OverrideAimChangeX(HumanInputControllerOverrideType.ENABLED, m_YawError * Math.DEG2RAD * LOOK_GAIN);
		input.OverrideAimChangeY(HumanInputControllerOverrideType.ENABLED, m_PitchError * Math.DEG2RAD * LOOK_GAIN);
	}

	void StopSteering()
	{
		m_Looking = false;
		PlayerBase player = LocalPlayer();
		if (!player || !player.GetInputController())
			return;
		HumanInputController input = player.GetInputController();
		input.OverrideAimChangeX(HumanInputControllerOverrideType.DISABLED, 0);
		input.OverrideAimChangeY(HumanInputControllerOverrideType.DISABLED, 0);
	}

	// Degrees the camera must still turn to face m_LookTarget (positive yaw = to the right).
	void MeasureLook()
	{
		vector dir = GetGame().GetCurrentCameraDirection();
		vector want = vector.Direction(GetGame().GetCurrentCameraPosition(), m_LookTarget);
		want.Normalize();
		float yawNow = Math.Atan2(dir[0], dir[2]) * Math.RAD2DEG;
		float yawWant = Math.Atan2(want[0], want[2]) * Math.RAD2DEG;
		float yaw = yawWant - yawNow;
		if (yaw > 180)
			yaw = yaw - 360;
		if (yaw < -180)
			yaw = yaw + 360;
		m_YawError = yaw;
		m_PitchError = (Math.Asin(want[1]) - Math.Asin(dir[1])) * Math.RAD2DEG;
	}

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
			case "look_at":
				return CmdLookAt(c, r);
			case "inventory_move":
				return CmdInventoryMove(c, r);
			case "action_use":
				return CmdActionUse(c, r);
			case "action_cursor":
				return CmdActionCursor(c, r);
			case "ui_tree":
				return CmdUiTree(c, r);
			case "ui_click":
				return CmdUiClick(c, r);
			case "ui_set_text":
				return CmdUiSetText(c, r);
			case "ui_open":
				return CmdUiOpen(c, r);
		}
		return super.Execute(c, r);
	}

	// --- moving and aiming the player -----------------------------------------------------

	bool CmdLookAt(AZB_Command c, AZB_Result r)
	{
		if (!LocalPlayer())
		{
			Fail(r, "no_player");
			return true;
		}
		if (m_Step == 0)
		{
			m_LookTarget = ToVector(c.args.look_at);
			m_Looking = true;
			m_Step = 1;
			return false;
		}
		MeasureLook();
		bool aligned = Math.AbsFloat(m_YawError) < LOOK_DONE_DEG && Math.AbsFloat(m_PitchError) < LOOK_DONE_DEG;
		if (!aligned && m_Elapsed < LOOK_TIMEOUT_S)
			return false;
		StopSteering();
		r.data.aligned = aligned;
		r.data.yaw_error = m_YawError;
		r.data.pitch_error = m_PitchError;
		if (!aligned)
		{
			Fail(r, "not_aligned");
			r.data.reason = "yaw off " + m_YawError.ToString() + " deg, pitch off " + m_PitchError.ToString() + " deg";
		}
		return true;
	}

	// --- real inventory moves through the player's own predictive calls -----------------------

	bool CmdInventoryMove(AZB_Command c, AZB_Result r)
	{
		PlayerBase player = LocalPlayer();
		EntityAI item = EntityAI.Cast(FindByNetId(c.args.net_id));
		if (!player || !item)
		{
			Fail(r, "not_found");
			return true;
		}
		if (m_Step == 0)
		{
			EntityAI target = EntityAI.Cast(FindByNetId(c.args.target_net_id));
			bool sent = true;
			if (c.args.dest == "hands")
			{
				player.PredictiveTakeEntityToHands(item);
			}
			else if (c.args.dest == "ground")
			{
				sent = player.PredictiveDropEntity(item);
			}
			else if (!target)
			{
				Fail(r, "no_target");
				return true;
			}
			else if (c.args.dest == "cargo")
			{
				sent = player.PredictiveTakeEntityToTargetCargo(target, item);
			}
			else
			{
				sent = player.PredictiveTakeEntityToTargetAttachment(target, item);
			}
			if (!sent)
			{
				Fail(r, "move_refused");
				return true;
			}
			m_Step = 1;
			return false;
		}
		if (m_Elapsed < SEAT_WAIT_S / 2)
			return false;
		// Where the client now sees it; the server's view is object_state's parent_net_id.
		if (item.GetHierarchyParent())
			r.data.parent_net_id = NetId(item.GetHierarchyParent());
		r.data.pos = FromVector(item.GetPosition());
		return true;
	}

	// --- player actions ------------------------------------------------------------------

	// Only classes that inherit vanilla ActionBase can be named: an action, never any method.
	bool CmdActionUse(AZB_Command c, AZB_Result r)
	{
		PlayerBase player = LocalPlayer();
		ActionManagerClient manager;
		if (player)
			manager = ActionManagerClient.Cast(player.GetActionManager());
		if (!manager)
		{
			Fail(r, "no_player");
			return true;
		}
		if (m_Step == 1)
		{
			if (m_Elapsed < 1.0)
				return false;
			if (manager.GetRunningAction())
				r.data.running = manager.GetRunningAction().ClassName();
			return true;
		}
		typename actionType = c.args.action.ToType();
		if (!actionType || !actionType.IsInherited(ActionBase))
		{
			Fail(r, "not_an_action");
			return true;
		}
		ActionBase action = ActionManagerBase.GetAction(actionType);
		if (!action)
		{
			Fail(r, "not_registered");
			return true;
		}
		ActionTarget target;
		Object targetObject = FindByNetId(c.args.net_id);
		if (c.args.net_id == "")
			target = manager.FindActionTarget();
		else if (targetObject)
			target = new ActionTarget(targetObject, null, c.args.component, targetObject.GetPosition(), 0);
		if (!target)
		{
			Fail(r, "not_found");
			return true;
		}
		r.data.can = action.Can(player, target, player.GetItemInHands());
		if (!r.data.can)
		{
			Fail(r, "action_refused");
			return true;
		}
		manager.PerformActionStart(action, target, player.GetItemInHands());
		r.data.started = true;
		m_Step = 1;
		return false;
	}

	void AddOffers(AZB_Data d, ActionManagerClient manager, typename inputType, string inputName)
	{
		array<ActionBase> actions = manager.GetPossibleActions(inputType);
		if (!actions)
			return;
		foreach (ActionBase action : actions)
		{
			AZB_Offer offer = new AZB_Offer();
			offer.input = inputName;
			offer.action = action.ClassName();
			offer.text = action.GetText();
			d.offered.Insert(offer);
		}
	}

	// What the cursor offers now, read the way the vanilla action HUD reads it (actiontargetscursor.c:658).
	bool CmdActionCursor(AZB_Command c, AZB_Result r)
	{
		PlayerBase player = LocalPlayer();
		ActionManagerClient manager;
		if (player)
			manager = ActionManagerClient.Cast(player.GetActionManager());
		if (!manager)
		{
			Fail(r, "no_player");
			return true;
		}
		r.data.offered = new array<ref AZB_Offer>;
		AddOffers(r.data, manager, InteractActionInput, "interact");
		AddOffers(r.data, manager, ContinuousInteractActionInput, "continuous_interact");
		AddOffers(r.data, manager, DefaultActionInput, "single");
		AddOffers(r.data, manager, ContinuousDefaultActionInput, "continuous");
		ActionTarget target = manager.FindActionTarget();
		if (target && target.GetObject())
		{
			r.data.target_net_id = NetId(target.GetObject());
			r.data.target_type = target.GetObject().GetType();
		}
		return true;
	}

	// --- the open UI -------------------------------------------------------------------------

	void AddWidgets(AZB_Data d, Widget w, int depth)
	{
		while (w && d.widgets.Count() < MAX_WIDGETS)
		{
			AZB_Widget entry = new AZB_Widget();
			entry.name = w.GetName();
			entry.type = w.GetTypeName();
			entry.depth = depth;
			float x;
			float y;
			float width;
			float height;
			w.GetScreenPos(x, y);
			w.GetScreenSize(width, height);
			entry.x = x;
			entry.y = y;
			entry.w = width;
			entry.h = height;
			entry.visible = w.IsVisibleHierarchy();
			d.widgets.Insert(entry);
			AddWidgets(d, w.GetChildren(), depth + 1);
			w = w.GetSibling();
		}
	}

	UIScriptedMenu OpenMenu(AZB_Result r)
	{
		UIScriptedMenu menu = GetGame().GetUIManager().GetMenu();
		if (!menu || !menu.GetLayoutRoot())
		{
			Fail(r, "no_menu");
			return null;
		}
		r.data.menu = menu.ClassName();
		return menu;
	}

	bool CmdUiTree(AZB_Command c, AZB_Result r)
	{
		UIScriptedMenu menu = OpenMenu(r);
		if (!menu)
			return true;
		r.data.widgets = new array<ref AZB_Widget>;
		AddWidgets(r.data, menu.GetLayoutRoot(), 0);
		return true;
	}

	// Presses a widget the way the menu itself hears a click: its OnClick (uiscriptedmenu.c:238).
	bool CmdUiClick(AZB_Command c, AZB_Result r)
	{
		UIScriptedMenu menu = OpenMenu(r);
		if (!menu)
			return true;
		Widget w = menu.GetLayoutRoot().FindAnyWidget(c.args.widget);
		if (!w)
		{
			Fail(r, "no_widget");
			return true;
		}
		r.data.clicked = menu.OnClick(w, 0, 0, 0);
		return true;
	}

	// Opens one of a few vanilla menus by its fixed id (constants.c:184 and :192), or closes the open one,
	// so the UI commands have a vanilla screen to work on; a mod's own screen is opened by its own action.
	bool CmdUiOpen(AZB_Command c, AZB_Result r)
	{
		UIManager ui = GetGame().GetUIManager();
		if (m_Step == 0)
		{
			if (c.args.widget == "close")
			{
				UIScriptedMenu open = ui.GetMenu();
				if (open)
					open.Close();
			}
			else if (c.args.widget == "ingame")
			{
				ui.EnterScriptedMenu(MENU_INGAME, null);
			}
			else
			{
				ui.EnterScriptedMenu(MENU_CHAT_INPUT, null);
			}
			m_Step = 1;
			return false;
		}
		if (m_Elapsed < 0.5)
			return false;
		if (ui.GetMenu())
			r.data.menu = ui.GetMenu().ClassName();
		return true;
	}

	bool CmdUiSetText(AZB_Command c, AZB_Result r)
	{
		UIScriptedMenu menu = OpenMenu(r);
		if (!menu)
			return true;
		EditBoxWidget box = EditBoxWidget.Cast(menu.GetLayoutRoot().FindAnyWidget(c.args.widget));
		if (!box)
		{
			Fail(r, "not_an_edit_box");
			return true;
		}
		box.SetText(c.args.text);
		r.data.text = box.GetText();
		return true;
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
		// The client's target condition measures from the cursor hit, not the car
		// (cctcursornoruincheck.c:38 to :43), so aim at the seat's entry point.
		vector entryPos;
		vector entryDir;
		m_Car.CrewEntryWS(c.args.seat, entryPos, entryDir);
		ActionTarget target = new ActionTarget(m_Car, null, component, entryPos, 0);
		ActionBase action = ActionManagerBase.GetAction(ActionGetInTransport);
		if (m_Tries >= SEAT_TRIES)
		{
			Fail(r, "not_seated");
			r.data.tries = m_Tries;
			r.data.reason = SeatReason(player, manager, action, target);
			return true;
		}
		manager.PerformActionStart(action, target, null);
		m_Tries++;
		m_TryStarted = m_Elapsed;
		m_Step = 2;
		return false;
	}

	// Why a get-in did not seat: the action manager's own gate, the action's
	// condition from here, and the player's command and distance to the entry point.
	string SeatReason(PlayerBase player, ActionManagerClient manager, ActionBase action, ActionTarget target)
	{
		string text = "possible=" + manager.ActionPossibilityCheck(player.GetCurrentCommandID()).ToString();
		text = text + " can=" + action.Can(player, target, null).ToString();
		text = text + " command=" + player.GetCurrentCommandID().ToString();
		text = text + " entry_dist=" + vector.Distance(player.GetPosition(), target.GetCursorHitPos()).ToString();
		Transport transport = Transport.Cast(target.GetObject());
		int seat = transport.CrewPositionIndex(target.GetComponentIndex());
		text = text + " through=" + transport.CrewCanGetThrough(seat).ToString();
		text = text + " area_free=" + transport.IsAreaAtDoorFreeDiag(seat).ToString();
		array<string> selections = new array<string>;
		transport.GetActionComponentNameList(target.GetComponentIndex(), selections);
		bool reach = false;
		foreach (string selection : selections)
		{
			if (transport.CanReachSeatFromDoors(selection, player.GetPosition(), 1.0))
				reach = true;
		}
		text = text + " reach=" + reach.ToString();
		return text;
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
			// The driver's client owns the car now; an engine left off since the spawn starts here.
			if (!m_Car.EngineIsOn())
				m_Car.EngineStart();
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
		// Vanilla shows the HUD again on its own; MissionGameplay hides it every frame while this is set.
		m_HudHidden = !c.args.show;
		r.data.hud = c.args.show;
		return true;
	}
}
#endif
