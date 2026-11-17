// Server side: walks the registry one test at a time and logs one line per result.
//   [AUTOTEST] PASS <name> <message>
//   [AUTOTEST] FAIL <name> <message>
//   [AUTOTEST] DONE passed=<n> failed=<n>      <- the line an outside script waits for
// Checked by the offline script validator only (scripts/tools/dayz-script-validator), not run in game.
class AutoTestRunner
{
	static ref AutoTestRunner s_Instance;

	PlayerBase m_Player;
	int m_Index;
	int m_Passed;
	int m_Failed;
	bool m_InitialAllowDamage;
	string m_TargetId;
	bool m_Finished;

	static void Schedule(PlayerBase player, int delayMs)
	{
		if (s_Instance)
			return;   // one run per server start
		if (!player)
			return;
		s_Instance = new AutoTestRunner();
		s_Instance.m_Player = player;
		// Record the initial damage state before changing it; restored at the end of the run.
		s_Instance.m_InitialAllowDamage = player.GetAllowDamage();
		PlayerIdentity targetIdentity = player.GetIdentity();
		if (targetIdentity)
			s_Instance.m_TargetId = targetIdentity.GetId();
		// Godmode from the first moment: the character stands in the world while the client loads.
		player.SetAllowDamage(false);
		// The client is still loading when OnConnect fires; give it time to get a player entity.
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(s_Instance.Next, delayMs, false);
	}

	protected void FinalizeRun()
	{
		if (m_Finished)
			return;
		m_Finished = true;
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).Remove(Next);
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).Remove(Timeout);
		// Restore the recorded initial state; nothing is restored on a deleted object.
		if (m_Player)
			m_Player.SetAllowDamage(m_InitialAllowDamage);
		Print("[AUTOTEST] DONE passed=" + m_Passed + " failed=" + m_Failed);
	}

	void Next()
	{
		if (m_Finished)
			return;
		if (!m_Player)
		{
			m_Failed++;
			Print("[AUTOTEST] FAIL player_gone player gone");
			FinalizeRun();
			return;
		}
		array<ref AutoTestCase> all = AutoTestRegistry.All();
		if (m_Index >= all.Count())
		{
			FinalizeRun();
			return;
		}
		AutoTestCase t = all.Get(m_Index);
		m_Player.SetAllowDamage(t.NeedsDamage());   // godmode unless this test needs damage
		t.ServerSetup(m_Player);

		ScriptRPC rpc = new ScriptRPC();
		rpc.Write(t.Name());
		t.WriteRunParams(rpc);
		rpc.Send(m_Player, AUTOTEST_RPC_RUN, true, m_Player.GetIdentity());
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(Timeout, 20000, false, m_Index);
	}

	void OnResult(PlayerIdentity sender, string name, bool passed, string msg)
	{
		if (m_Finished)
			return;
		if (!sender)
		{
			Print("[AUTOTEST] ignoring result from a null sender");
			return;
		}
		if (sender.GetId() != m_TargetId)
		{
			Print("[AUTOTEST] ignoring result from a sender that is not the test player");
			return;
		}
		if (!m_Player)
		{
			Finish(false, name, "player gone");
			return;
		}
		array<ref AutoTestCase> all = AutoTestRegistry.All();
		if (m_Index >= all.Count() || all.Get(m_Index).Name() != name)
			return;   // late or duplicate answer

		string serverMsg;
		if (!all.Get(m_Index).ServerCheck(m_Player, serverMsg))
			passed = false;
		if (serverMsg != "")
			msg = msg + " | server: " + serverMsg;
		Finish(passed, name, msg);
	}

	void Timeout(int index)
	{
		if (m_Finished || index != m_Index)
			return;
		array<ref AutoTestCase> all = AutoTestRegistry.All();
		if (m_Index >= all.Count())
		{
			FinalizeRun();
			return;
		}
		Finish(false, all.Get(m_Index).Name(), "no answer from the client");
	}

	protected void Finish(bool passed, string name, string msg)
	{
		if (m_Finished)
			return;
		if (passed)
		{
			m_Passed++;
			Print("[AUTOTEST] PASS " + name + " " + msg);
		}
		else
		{
			m_Failed++;
			Print("[AUTOTEST] FAIL " + name + " " + msg);
		}
		m_Index++;
		Next();
	}
}

// Client side: run the requested test half, retry while it fails, then answer the server.
class AutoTestClient
{
	static ref AutoTestClient s_Instance;

	static void Run(string name)
	{
		if (!s_Instance)
			s_Instance = new AutoTestClient();
		s_Instance.Try(name, 0);
	}

	static void SendResult(string name, bool ok, string msg)
	{
		Print("[AUTOTEST-CLIENT] " + name + " ok=" + ok + " " + msg);
		ScriptRPC rpc = new ScriptRPC();
		rpc.Write(name);
		rpc.Write(ok);
		rpc.Write(msg);
		rpc.Send(GetGame().GetPlayer(), AUTOTEST_RPC_RESULT, true);
	}

	void Try(string name, int attempt)
	{
		AutoTestCase t = AutoTestRegistry.Find(name);
		string msg;
		bool ok = false;
		if (t)
			ok = t.ClientCheck(msg);
		else
			msg = "unknown test";

		if (!ok && t && attempt < 10)
		{
			GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(Try, 500, false, name, attempt + 1);
			return;
		}

		SendResult(name, ok, msg);
	}
}

modded class PlayerBase
{
	override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
	{
		super.OnRPC(sender, rpc_type, ctx);

		if (rpc_type == AUTOTEST_RPC_RUN && !GetGame().IsDedicatedServer())
		{
			string runName;
			if (ctx.Read(runName))
			{
				AutoTestCase runCase = AutoTestRegistry.Find(runName);
				if (runCase && !runCase.ReadRunParams(ctx))
				{
					AutoTestClient.SendResult(runName, false, "failed to read test parameters");
					return;
				}
				AutoTestClient.Run(runName);
			}
		}
		else if (rpc_type == AUTOTEST_RPC_RESULT && GetGame().IsDedicatedServer())
		{
			string name;
			bool passed;
			string msg;
			if (ctx.Read(name) && ctx.Read(passed) && ctx.Read(msg) && AutoTestRunner.s_Instance)
				AutoTestRunner.s_Instance.OnResult(sender, name, passed, msg);
		}
	}
}
