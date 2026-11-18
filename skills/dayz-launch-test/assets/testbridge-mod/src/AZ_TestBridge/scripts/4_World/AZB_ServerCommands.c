#ifdef DIAG_DEVELOPER
// AZ_TestBridge server peer: world state and what the server owns. Spawning,
// deleting, teleporting, time, weather, car setup, rays and surfaces.
// Car setup runs here because OnDebugSpawn does nothing on a client under
// server authority (references/vehicle-in-game-facts.md).

class AZB_ServerPeer : AZB_Peer
{
	static const float SETTLE_S = 1.0;   // read a spawn or teleport back after this
	static const float TICK_S = 0.5;     // read car fluids and weather back after this

	Object m_Object;
	ref array<Man> m_Players;

	void AZB_ServerPeer()
	{
		m_Players = new array<Man>;
	}

	override bool IsReady()
	{
		return true;
	}

	override void FillHello(AZB_Hello hello)
	{
		GetGame().GetPlayers(m_Players);
		hello.player_count = m_Players.Count();
		hello.player_loaded = m_Players.Count() > 0;
	}

	override bool Execute(AZB_Command c, AZB_Result r)
	{
		switch (c.cmd)
		{
			case "spawn":
				return CmdSpawn(c, r);
			case "spawn_in_inventory":
				return CmdSpawnInInventory(c, r);
			case "delete":
				return CmdDelete(c, r);
			case "find_objects":
				return CmdFindObjects(c, r);
			case "object_state":
				return CmdObjectState(c, r);
			case "teleport":
				return CmdTeleport(c, r);
			case "player_state":
				return CmdPlayerState(c, r);
			case "set_time":
				return CmdSetTime(c, r);
			case "set_weather":
				return CmdSetWeather(c, r);
			case "vehicle_prepare":
				return CmdVehiclePrepare(c, r);
			case "vehicle_state":
				return CmdVehicleState(c, r);
			case "raycast":
				return CmdRaycast(c, r);
			case "surface":
				return CmdSurface(c, r);
		}
		return super.Execute(c, r);
	}

	// The only player, or null with the reason set: player commands refuse a server with more than one.
	PlayerBase OnlyPlayer(AZB_Result r)
	{
		GetGame().GetPlayers(m_Players);
		if (m_Players.Count() == 0)
		{
			Fail(r, "no_player");
			return null;
		}
		if (m_Players.Count() > 1)
		{
			Fail(r, "more_than_one_player");
			return null;
		}
		return PlayerBase.Cast(m_Players[0]);
	}

	void FillObject(AZB_Data d, Object obj)
	{
		d.net_id = NetId(obj);
		d.type = obj.GetType();
		d.class_name = obj.ClassName();
		d.pos = FromVector(obj.GetPosition());
	}

	bool CmdSpawn(AZB_Command c, AZB_Result r)
	{
		if (m_Step == 0)
		{
			m_Object = GetGame().CreateObjectEx(c.args.cls, ToVector(c.args.pos), c.args.flags, c.args.placement);
			if (!m_Object)
			{
				Fail(r, "spawn_failed");
				return true;
			}
			m_Step = 1;
			return false;
		}
		if (m_Elapsed < SETTLE_S)
			return false;
		if (!m_Object)
		{
			Fail(r, "spawn_gone");
			return true;
		}
		FillObject(r.data, m_Object);
		return true;
	}

	bool CmdSpawnInInventory(AZB_Command c, AZB_Result r)
	{
		PlayerBase player = OnlyPlayer(r);
		if (!player)
			return true;
		EntityAI item;
		if (c.args.where == "hands")
		{
			if (player.GetHumanInventory().GetEntityInHands())
			{
				Fail(r, "spawn_failed");
				r.data.reason = "hands are not empty";
				return true;
			}
			item = player.GetHumanInventory().CreateInHands(c.args.cls);
		}
		else if (c.args.where == "attachment")
		{
			item = player.GetInventory().CreateAttachment(c.args.cls);
		}
		else
		{
			item = player.GetInventory().CreateInInventory(c.args.cls);
		}
		if (!item)
		{
			Fail(r, "spawn_failed");
			r.data.reason = "no free " + c.args.where + " place for " + c.args.cls + ", or no such class";
			return true;
		}
		r.data.net_id = NetId(item);
		r.data.quantity = item.GetQuantity();
		return true;
	}

	bool CmdDelete(AZB_Command c, AZB_Result r)
	{
		if (m_Step == 0)
		{
			Object obj = FindByNetId(c.args.net_id);
			if (!obj)
			{
				Fail(r, "not_found");
				return true;
			}
			Transport transport = Transport.Cast(obj);
			if (transport && transport.HasCrew())
			{
				// Deleting a car with crew crashed the game on 1.30 (vehicle-in-game-facts.md).
				Fail(r, "vehicle_has_crew");
				return true;
			}
			GetGame().ObjectDelete(obj);
			m_Step = 1;
			return false;
		}
		if (m_Elapsed < TICK_S)
			return false;
		r.data.removed = FindByNetId(c.args.net_id) == null;
		if (!r.data.removed)
			Fail(r, "still_there");
		return true;
	}

	bool CmdFindObjects(AZB_Command c, AZB_Result r)
	{
		array<Object> objects = new array<Object>;
		GetGame().GetObjectsAtPosition(ToVector(c.args.pos), c.args.radius, objects, null);
		r.data.objects = new array<ref AZB_Obj>;
		foreach (Object obj : objects)
		{
			if (r.data.objects.Count() >= 100)
				break;
			if (!obj)
				continue;
			if (c.args.cls != "" && !obj.IsKindOf(c.args.cls))
				continue;
			AZB_Obj entry = new AZB_Obj();
			entry.net_id = NetId(obj);
			entry.type = obj.GetType();
			entry.class_name = obj.ClassName();
			entry.pos = FromVector(obj.GetPosition());
			r.data.objects.Insert(entry);
		}
		return true;
	}

	bool CmdObjectState(AZB_Command c, AZB_Result r)
	{
		Object obj = FindByNetId(c.args.net_id);
		if (!obj)
		{
			Fail(r, "not_found");
			return true;
		}
		FillObject(r.data, obj);
		r.data.ori = FromVector(obj.GetOrientation());
		r.data.health = obj.GetHealth("", "");
		return true;
	}

	bool CmdTeleport(AZB_Command c, AZB_Result r)
	{
		PlayerBase player = OnlyPlayer(r);
		if (!player)
			return true;
		if (m_Step == 0)
		{
			vector pos = ToVector(c.args.pos);
			if (c.args.ground)
				pos[1] = GetGame().SurfaceY(pos[0], pos[2]);
			player.SetPosition(pos);
			m_Step = 1;
			return false;
		}
		if (m_Elapsed < SETTLE_S)
			return false;
		r.data.pos = FromVector(player.GetPosition());
		return true;
	}

	bool CmdPlayerState(AZB_Command c, AZB_Result r)
	{
		PlayerBase player = OnlyPlayer(r);
		if (!player)
			return true;
		r.data.pos = FromVector(player.GetPosition());
		r.data.health = player.GetHealth("", "");
		r.data.seat = -1;
		HumanCommandVehicle vehicleCommand = player.GetCommand_Vehicle();
		if (vehicleCommand && vehicleCommand.GetTransport())
		{
			Transport transport = vehicleCommand.GetTransport();
			r.data.in_vehicle = true;
			r.data.seat = transport.CrewMemberIndex(player);
			r.data.vehicle_net_id = NetId(transport);
		}
		EntityAI inHands = player.GetHumanInventory().GetEntityInHands();
		if (inHands)
			r.data.hands = inHands.GetType();
		return true;
	}

	bool CmdSetTime(AZB_Command c, AZB_Result r)
	{
		GetGame().GetWorld().SetDate(c.args.year, c.args.month, c.args.day, c.args.hour, c.args.minute);
		int year;
		int month;
		int day;
		int hour;
		int minute;
		GetGame().GetWorld().GetDate(year, month, day, hour, minute);
		r.data.year = year;
		r.data.month = month;
		r.data.day = day;
		r.data.hour = hour;
		r.data.minute = minute;
		return true;
	}

	bool CmdSetWeather(AZB_Command c, AZB_Result r)
	{
		Weather weather = GetGame().GetWeather();
		if (m_Step == 0)
		{
			weather.SetWeatherUpdateFreeze(c.args.freeze);
			weather.GetOvercast().Set(c.args.overcast, 0, 3600);
			weather.GetFog().Set(c.args.fog, 0, 3600);
			weather.GetRain().Set(c.args.rain, 0, 3600);
			// wind is a share of the map's maximum wind speed; the engine works in m/s (weather.c:203)
			weather.GetWindMagnitude().Set(c.args.wind * weather.GetWindMaximumSpeed(), 0, 3600);
			m_Step = 1;
			return false;
		}
		if (m_Elapsed < TICK_S)
			return false;
		r.data.overcast = weather.GetOvercast().GetActual();
		r.data.fog = weather.GetFog().GetActual();
		r.data.rain = weather.GetRain().GetActual();
		r.data.wind = 0;
		if (weather.GetWindMaximumSpeed() > 0)
			r.data.wind = weather.GetWindSpeed() / weather.GetWindMaximumSpeed();
		r.data.frozen = weather.GetWeatherUpdateFrozen();
		return true;
	}

	bool CmdVehiclePrepare(AZB_Command c, AZB_Result r)
	{
		CarScript car = CarScript.Cast(FindByNetId(c.args.net_id));
		if (!car)
		{
			Fail(r, "not_a_car");
			return true;
		}
		if (m_Step == 0)
		{
			car.OnDebugSpawn();
			m_Step = 1;
			return false;
		}
		// The tank can read 0 in the tick OnDebugSpawn fills it (vehicle-in-game-facts.md),
		// and the engine refuses to start before the battery and spark plug are in
		// (OnBeforeEngineStart, carscript.c:1713), so start it a tick later and read later still.
		if (m_Elapsed < TICK_S)
			return false;
		if (m_Step == 1)
		{
			if (c.args.engine_on)
				car.EngineStart();
			// A car with a driver door only takes a driver through an open door
			// (CrewCanGetThrough, hatchback_02.c:218 to :226). Open it the way the
			// vanilla door action does on the server (actioncardoorsoutside.c:104).
			if (c.args.open_driver_door)
			{
				string doorSource = car.GetAnimSourceFromSelection(car.GetDoorSelectionNameFromSeatPos(0));
				if (doorSource != "")
					car.SetAnimationPhase(doorSource, 1.0);
			}
			m_Step = 2;
			return false;
		}
		if (m_Elapsed < TICK_S * 3)
			return false;
		r.data.wheels_declared = car.WheelCount();
		r.data.wheels_present = car.WheelCountPresent();
		r.data.fuel = car.GetFluidFraction(CarFluid.FUEL);
		r.data.engine_on = car.EngineIsOn();
		r.data.door_open = car.CrewCanGetThrough(0);
		vector entryPos;
		vector entryDir;
		car.CrewEntryWS(0, entryPos, entryDir);
		r.data.entry_pos = FromVector(entryPos);
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

	bool CmdRaycast(AZB_Command c, AZB_Result r)
	{
		vector begin = ToVector(c.args.from_pos);
		vector end = ToVector(c.args.to_pos);
		r.data.hits = new array<ref AZB_Hit>;
		AZB_Hit hit;
		if (c.args.mode == "bullet")
		{
			Object hitObject;
			vector hitPosition;
			vector hitNormal;
			float hitFraction;
			PhxInteractionLayers layers = c.args.layer_mask;
			// 0 means the mask vanilla's melee obstruction test uses (dayzplayerimplementmeleecombat.c:674)
			if (layers == 0)
				layers = PhxInteractionLayers.BUILDING | PhxInteractionLayers.DOOR | PhxInteractionLayers.VEHICLE | PhxInteractionLayers.ROADWAY | PhxInteractionLayers.TERRAIN | PhxInteractionLayers.ITEM_SMALL | PhxInteractionLayers.ITEM_LARGE | PhxInteractionLayers.FENCE;
			if (DayZPhysics.RayCastBullet(begin, end, layers, null, hitObject, hitPosition, hitNormal, hitFraction))
			{
				hit = new AZB_Hit();
				hit.terrain = hitObject == null;
				if (hitObject)
				{
					hit.net_id = NetId(hitObject);
					hit.type = hitObject.GetType();
				}
				hit.pos = FromVector(hitPosition);
				hit.component = -1;
				hit.normal = FromVector(hitNormal);
				hit.dir_len = vector.Distance(begin, end) * hitFraction;
				r.data.hits.Insert(hit);
			}
			return true;
		}
		RaycastRVParams params = new RaycastRVParams(begin, end, null, 0);
		params.sorted = true;
		if (c.args.mode == "geom")
			params.type = ObjIntersect.Geom;
		else if (c.args.mode == "fire")
			params.type = ObjIntersect.Fire;
		else
			params.type = ObjIntersect.View;
		array<ref RaycastRVResult> results = new array<ref RaycastRVResult>;
		if (!DayZPhysics.RaycastRVProxy(params, results))
			return true;
		foreach (RaycastRVResult res : results)
		{
			hit = new AZB_Hit();
			hit.terrain = res.obj == null;
			if (res.obj)
			{
				hit.net_id = NetId(res.obj);
				hit.type = res.obj.GetType();
			}
			// A car's doors, trunk and parts are their own objects. Name the object they
			// hang on: the ray's proxy parent (dayzphysics.c:101) or the hierarchy root (entityai.c:879).
			if (res.parent)
				hit.parent_net_id = NetId(res.parent);
			EntityAI hitEntity = EntityAI.Cast(res.obj);
			if (hit.parent_net_id == "" && hitEntity && hitEntity.GetHierarchyRoot() != hitEntity)
				hit.parent_net_id = NetId(hitEntity.GetHierarchyRoot());
			hit.pos = FromVector(res.pos);
			hit.component = res.component;
			hit.entry = res.entry;
			hit.exit = res.exit;
			hit.dir_len = res.dir.Length();
			r.data.hits.Insert(hit);
		}
		return true;
	}

	bool CmdSurface(AZB_Command c, AZB_Result r)
	{
		r.data.ground_y = GetGame().SurfaceY(c.args.x, c.args.z);
		r.data.road_y = GetGame().SurfaceRoadY(c.args.x, c.args.z);
		string surfaceType;
		if (c.args.has_y)
			GetGame().SurfaceGetType3D(c.args.x, c.args.y, c.args.z, surfaceType);
		else
			GetGame().SurfaceGetType(c.args.x, c.args.z, surfaceType);
		r.data.surface = surfaceType;
		return true;
	}
}

// Car state as one peer sees it; the server and the client both use it.
class AZB_VehicleRead
{
	static void Fill(CarScript car, AZB_Data d)
	{
		d.speed = car.GetSpeedometer();
		d.rpm = car.EngineGetRPM();
		d.gear = car.GetGear();
		d.engine_on = car.EngineIsOn();
		d.wheels_declared = car.WheelCount();
		d.wheels_present = car.WheelCountPresent();
		string contact = "";
		for (int i = 0; i < d.wheels_declared; i++)
		{
			if (car.WheelHasContact(i))
				contact = contact + "1";
			else
				contact = contact + "0";
		}
		d.wheel_contact = contact;
		d.fuel = car.GetFluidFraction(CarFluid.FUEL);
		d.crew_seats = new array<int>;
		for (int seat = 0; seat < car.CrewSize(); seat++)
		{
			if (car.CrewMember(seat))
				d.crew_seats.Insert(seat);
		}
		d.net_id = AZB_Peer.NetId(car);
		d.pos = AZB_Peer.FromVector(car.GetPosition());
	}
}
#endif
