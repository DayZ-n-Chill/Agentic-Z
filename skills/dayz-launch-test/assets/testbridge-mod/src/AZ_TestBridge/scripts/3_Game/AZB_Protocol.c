#ifdef DIAG_DEVELOPER
// AZ_TestBridge protocol: the command and result classes, the token, and the
// poll loop each peer runs. The host side is .claude/mcp/dayz-testbridge/bridge.py;
// skills/dayz-launch-test/references/test-bridge.md describes both halves.
// Every engine call here is pinned to its P:\scripts line in test_vanilla_calls.py.

class AZB_Args
{
	string label;
	string cls;
	ref array<float> pos;
	int flags;
	int placement;
	string where;
	string net_id;
	float radius;
	bool ground;
	int year;
	int month;
	int day;
	int hour;
	int minute;
	float overcast;
	float fog;
	float rain;
	float wind;
	bool freeze;
	bool engine_on;
	bool open_driver_door;
	ref array<float> from_pos;
	ref array<float> to_pos;
	string mode;
	int layer_mask;
	float x;
	float z;
	float y;
	bool has_y;
	int seat;
	float throttle;
	float steer;
	float brake;
	float seconds;
	float sample_hz;
	ref array<float> look_at;
	bool show;

	void AZB_Args()
	{
		pos = new array<float>;
		from_pos = new array<float>;
		to_pos = new array<float>;
		look_at = new array<float>;
	}
}

class AZB_Command
{
	int seq;
	string token;
	string cmd;
	ref AZB_Args args;

	void AZB_Command()
	{
		args = new AZB_Args();
	}
}

class AZB_Obj
{
	string net_id;
	string type;
	string class_name;
	ref array<float> pos;
}

class AZB_Hit
{
	string net_id;
	string type;
	bool terrain;
	ref array<float> pos;
	int component;
	bool entry;
	bool exit;
	float dir_len;
	ref array<float> normal;
}

class AZB_Sample
{
	float t;
	float speed;
	float rpm;
	int gear;
	ref array<float> pos;
}

class AZB_Data
{
	string version;
	string token;
	bool player_loaded;
	int player_count;
	string label;
	string net_id;
	string type;
	string class_name;
	ref array<float> pos;
	ref array<float> ori;
	float health;
	float quantity;
	string reason;
	bool removed;
	ref array<ref AZB_Obj> objects;
	bool in_vehicle;
	int seat;
	string vehicle_net_id;
	string hands;
	int year;
	int month;
	int day;
	int hour;
	int minute;
	float overcast;
	float fog;
	float rain;
	float wind;
	bool frozen;
	int wheels_declared;
	int wheels_present;
	string wheel_contact;
	float fuel;
	bool engine_on;
	bool door_open;
	ref array<float> entry_pos;
	float speed;
	float rpm;
	int gear;
	ref array<int> crew_seats;
	ref array<ref AZB_Hit> hits;
	float ground_y;
	float road_y;
	string surface;
	bool seated;
	int tries;
	bool on_foot;
	ref array<ref AZB_Sample> samples;
	float distance;
	float top_speed;
	ref array<float> camera_pos;
	bool player_view;
	bool hud;
	bool paused;
}

class AZB_Result
{
	int seq;
	bool ok;
	string error;
	string peer;
	int game_time_ms;
	ref AZB_Data data;

	void AZB_Result()
	{
		ok = true;
		data = new AZB_Data();
	}
}

class AZB_Hello
{
	string peer;
	string version;
	string token;
	bool player_loaded;
	int player_count;
	int game_time_ms;
}

// One peer of the bridge. The server and the client each run one, from their
// mission's OnUpdate. It reads only cmd/<next>.json, never lists the folder,
// never runs a command whose result already exists, and handles one command
// at a time; a long command keeps its state between ticks.
class AZB_Peer
{
	static const float POLL_S = 0.1;

	string m_Peer;
	string m_Token;
	string m_Dir;
	int m_Next;
	float m_Acc;
	bool m_HelloDone;
	ref AZB_Command m_Pending;
	ref AZB_Result m_Result;
	float m_Elapsed;
	int m_Step;

	// Reads -azBridge=<token>; without it the peer stays inactive and does nothing.
	void Start(string peer)
	{
		m_Peer = peer;
		m_Next = 1;
		string token;
		if (!GetGame().CommandlineGetParam("azBridge", token))
			return;
		if (token.Length() != 32)
			return;
		m_Token = token;
		m_Dir = "$profile:AZTestBridge/" + m_Token + "/";
		MakeFolder("$profile:AZTestBridge/");
		MakeFolder(m_Dir);
		MakeFolder(m_Dir + "cmd/");
		MakeFolder(m_Dir + "res/");
		Print("[AZ-BRIDGE] " + m_Peer + " active");
	}

	bool IsActive()
	{
		return m_Token != "";
	}

	void MakeFolder(string path)
	{
		if (!FileExist(path))
			MakeDirectory(path);
	}

	// Ready to say hello: overridden by each peer.
	bool IsReady()
	{
		return true;
	}

	void FillHello(AZB_Hello hello)
	{
	}

	void Tick(float timeslice)
	{
		if (!IsActive())
			return;
		m_Acc += timeslice;
		if (m_Acc < POLL_S)
			return;
		float dt = m_Acc;
		m_Acc = 0;

		if (!m_HelloDone)
		{
			if (!IsReady())
				return;
			WriteHello();
		}

		if (m_Pending)
		{
			m_Elapsed += dt;
			Continue();
			return;
		}
		Poll();
	}

	void WriteHello()
	{
		AZB_Hello hello = new AZB_Hello();
		hello.peer = m_Peer;
		hello.token = m_Token;
		string version;
		GetGame().GetVersion(version);
		hello.version = version;
		hello.game_time_ms = GetGame().GetTime();
		FillHello(hello);
		string err;
		if (JsonFileLoader<AZB_Hello>.SaveFile(m_Dir + "hello.json", hello, err))
		{
			m_HelloDone = true;
			Print("[AZ-BRIDGE] " + m_Peer + " hello");
		}
		else
		{
			Print("[AZ-BRIDGE] ERROR hello: " + err);
		}
	}

	void Poll()
	{
		string cmdPath = m_Dir + "cmd/" + m_Next.ToString() + ".json";
		string resPath = m_Dir + "res/" + m_Next.ToString() + ".json";
		while (FileExist(resPath))
		{
			if (FileExist(cmdPath))
				DeleteFile(cmdPath);
			m_Next++;
			cmdPath = m_Dir + "cmd/" + m_Next.ToString() + ".json";
			resPath = m_Dir + "res/" + m_Next.ToString() + ".json";
		}
		if (!FileExist(cmdPath))
			return;

		AZB_Command command = new AZB_Command();
		AZB_Result result = new AZB_Result();
		result.seq = m_Next;
		result.peer = m_Peer;
		string err;
		if (!JsonFileLoader<AZB_Command>.LoadFile(cmdPath, command, err))
		{
			Fail(result, "bad_json");
			Finish(result, "?");
			return;
		}
		if (command.seq != m_Next)
		{
			Fail(result, "seq_mismatch");
			Finish(result, command.cmd);
			return;
		}
		if (command.token != m_Token)
		{
			Fail(result, "wrong_token");
			Finish(result, command.cmd);
			return;
		}
		if (!command.args)
			command.args = new AZB_Args();

		m_Pending = command;
		m_Result = result;
		m_Elapsed = 0;
		m_Step = 0;
		Continue();
	}

	void Continue()
	{
		if (Execute(m_Pending, m_Result))
		{
			AZB_Result result = m_Result;
			string name = m_Pending.cmd;
			m_Pending = null;
			m_Result = null;
			Finish(result, name);
		}
	}

	void Finish(AZB_Result result, string name)
	{
		result.game_time_ms = GetGame().GetTime();
		string cmdPath = m_Dir + "cmd/" + m_Next.ToString() + ".json";
		string resPath = m_Dir + "res/" + m_Next.ToString() + ".json";
		string err;
		if (!JsonFileLoader<AZB_Result>.SaveFile(resPath, result, err))
			Print("[AZ-BRIDGE] ERROR result " + m_Next.ToString() + ": " + err);
		DeleteFile(cmdPath);
		string okText = "1";
		if (!result.ok)
			okText = "0";
		Print("[AZ-BRIDGE] " + m_Peer + " seq=" + m_Next.ToString() + " cmd=" + name + " ok=" + okText + " " + result.error);
		m_Next++;
	}

	static void Fail(AZB_Result result, string error)
	{
		result.ok = false;
		result.error = error;
	}

	// Runs one tick of a command; true when it is finished. Each peer overrides
	// this with its own switch and calls super for the names it does not know.
	bool Execute(AZB_Command c, AZB_Result r)
	{
		switch (c.cmd)
		{
			case "ping":
				return CmdPing(c, r);
			case "mark":
				return CmdMark(c, r);
		}
		Fail(r, "unknown_command");
		return true;
	}

	bool CmdPing(AZB_Command c, AZB_Result r)
	{
		AZB_Hello hello = new AZB_Hello();
		FillHello(hello);
		string version;
		GetGame().GetVersion(version);
		r.data.version = version;
		r.data.token = m_Token;
		r.data.player_loaded = hello.player_loaded;
		r.data.player_count = hello.player_count;
		return true;
	}

	bool CmdMark(AZB_Command c, AZB_Result r)
	{
		Print("[AZ-BRIDGE] MARK " + c.args.label);
		r.data.label = c.args.label;
		return true;
	}

	// --- helpers shared by both peers ------------------------------------------

	static vector ToVector(array<float> a)
	{
		if (!a || a.Count() < 3)
			return vector.Zero;
		return Vector(a[0], a[1], a[2]);
	}

	static array<float> FromVector(vector v)
	{
		array<float> a = new array<float>;
		a.Insert(v[0]);
		a.Insert(v[1]);
		a.Insert(v[2]);
		return a;
	}

	static Object FindByNetId(string netId)
	{
		array<string> parts = new array<string>;
		netId.Split(",", parts);
		if (parts.Count() != 2)
			return null;
		return GetGame().GetObjectByNetworkId(parts[0].ToInt(), parts[1].ToInt());
	}

	// "<low>,<high>". Vanilla's GetNetworkIDString joins high and low with no
	// separator (object.c:821 to :826), so it cannot be split back into the two
	// numbers GetObjectByNetworkId (game.c:356) takes.
	static string NetId(Object obj)
	{
		if (!obj)
			return "";
		int low;
		int high;
		obj.GetNetworkID(low, high);
		if (low == 0 && high == 0)
			return "";
		return low.ToString() + "," + high.ToString();
	}
}
#endif
