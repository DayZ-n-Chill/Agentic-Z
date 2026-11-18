// One test = one class. The same PBO is loaded on server and client, so both sides know every
// test by name. The server drives the order; the client only runs what it is told to.
class AutoTestCase
{
	string Name() { return ""; }

	// Server half: runs first, on the server, before the client is asked to check anything.
	void ServerSetup(PlayerBase player) {}

	// Optional run parameters written after ServerSetup and read on the client before ClientCheck,
	// so a test can bind its client check to the exact entity ServerSetup created.
	void WriteRunParams(ParamsWriteContext ctx) {}
	bool ReadRunParams(ParamsReadContext ctx) { return true; }

	// Client half: runs on the client. Return false to be retried for a few seconds (server-side
	// changes need a moment to replicate), then reported as a failure with msg.
	bool ClientCheck(out string msg)
	{
		msg = "";
		return true;
	}

	// Server half, after the client has answered: assert on what the server sees now.
	bool ServerCheck(PlayerBase player, out string msg)
	{
		msg = "";
		return true;
	}

	// The character is in godmode for every test, so a zombie, an animal or a fall cannot kill it in
	// the middle of a run and fail an unrelated test. Return true only for a test that needs the
	// character to take damage; the runner re-enables godmode before the next test.
	bool NeedsDamage() { return false; }
}

// Godmode really blocks damage: the server hits the player and the health must not drop.
class AutoTestGodmode : AutoTestCase
{
	float m_Before;

	override string Name() { return "godmode_blocks_damage"; }

	override void ServerSetup(PlayerBase player)
	{
		m_Before = player.GetHealth("", "");
		player.ProcessDirectDamage(DamageType.CLOSE_COMBAT, player, "Torso", "MeleeZombie", "0 0 0", 1.0);
	}

	override bool ServerCheck(PlayerBase player, out string msg)
	{
		float now = player.GetHealth("", "");
		msg = "health " + m_Before + " -> " + now;
		return now >= m_Before;
	}
}

// The opt-out works: with NeedsDamage() the same hit does reduce the health.
class AutoTestDamageWhenNeeded : AutoTestCase
{
	float m_Before;

	override string Name() { return "damage_when_needed"; }
	override bool NeedsDamage() { return true; }

	override void ServerSetup(PlayerBase player)
	{
		m_Before = player.GetHealth("", "");
		player.ProcessDirectDamage(DamageType.CLOSE_COMBAT, player, "Torso", "MeleeZombie", "0 0 0", 1.0);
	}

	override bool ServerCheck(PlayerBase player, out string msg)
	{
		float now = player.GetHealth("", "");
		msg = "health " + m_Before + " -> " + now;
		return now < m_Before;
	}
}

// Client half only: the local player exists and is the right class.
class AutoTestClientHasPlayer : AutoTestCase
{
	override string Name() { return "client_has_player"; }

	override bool ClientCheck(out string msg)
	{
		PlayerBase p = PlayerBase.Cast(GetGame().GetPlayer());
		if (!p)
		{
			msg = "no local player";
			return false;
		}
		msg = "local player " + p.GetType();
		return true;
	}
}

// Server half changes the world, client half sees it: the item the server creates has to show up
// in the inventory the client has replicated, matched by network id so a pre-existing Chemlight_Red
// on a persisted character or spawn loadout cannot cause a false PASS.
class AutoTestServerItemSynced : AutoTestCase
{
	bool m_CreatedOk;
	int m_NetLow;
	int m_NetHigh;

	override string Name() { return "server_item_synced"; }

	override void ServerSetup(PlayerBase player)
	{
		m_CreatedOk = false;
		m_NetLow = 0;
		m_NetHigh = 0;
		if (!player || !player.GetInventory())
			return;
		EntityAI created = player.GetInventory().CreateInInventory("Chemlight_Red");
		if (!created)
			return;
		created.GetNetworkID(m_NetLow, m_NetHigh);
		if (m_NetLow != 0 || m_NetHigh != 0)
			m_CreatedOk = true;
	}

	override void WriteRunParams(ParamsWriteContext ctx)
	{
		ctx.Write(m_CreatedOk);
		ctx.Write(m_NetLow);
		ctx.Write(m_NetHigh);
	}

	override bool ReadRunParams(ParamsReadContext ctx)
	{
		m_CreatedOk = false;
		m_NetLow = 0;
		m_NetHigh = 0;
		if (!ctx.Read(m_CreatedOk))
			return false;
		if (!ctx.Read(m_NetLow))
			return false;
		if (!ctx.Read(m_NetHigh))
			return false;
		return true;
	}

	override bool ClientCheck(out string msg)
	{
		if (!m_CreatedOk)
		{
			msg = "ServerSetup CreateInInventory(Chemlight_Red) failed";
			return false;
		}
		PlayerBase p = PlayerBase.Cast(GetGame().GetPlayer());
		if (!p)
		{
			msg = "no local player";
			return false;
		}
		array<EntityAI> items = new array<EntityAI>;
		p.GetInventory().EnumerateInventory(InventoryTraversalType.PREORDER, items);
		int low = 0;
		int high = 0;
		foreach (EntityAI e : items)
		{
			if (!e)
				continue;
			low = 0;
			high = 0;
			e.GetNetworkID(low, high);
			if (low == m_NetLow && high == m_NetHigh && e.IsKindOf("Chemlight_Red"))
			{
				msg = "Chemlight_Red replicated to the client";
				return true;
			}
		}
		msg = "created Chemlight_Red not in the client's inventory";
		return false;
	}

	override bool ServerCheck(PlayerBase player, out string msg)
	{
		if (!m_CreatedOk)
		{
			msg = "CreateInInventory(Chemlight_Red) returned null on server";
			return false;
		}
		msg = "";
		return true;
	}
}

class AutoTestRegistry
{
	static ref array<ref AutoTestCase> s_Cases;

	// Order matters: the server runs them in this order. Add new tests here.
	static array<ref AutoTestCase> All()
	{
		if (!s_Cases)
		{
			s_Cases = new array<ref AutoTestCase>;
			s_Cases.Insert(new AutoTestClientHasPlayer());
			s_Cases.Insert(new AutoTestServerItemSynced());
			s_Cases.Insert(new AutoTestGodmode());
			s_Cases.Insert(new AutoTestDamageWhenNeeded());   // last: it leaves the character hurt
		}
		return s_Cases;
	}

	static AutoTestCase Find(string name)
	{
		array<ref AutoTestCase> all = All();
		for (int i = 0; i < all.Count(); i++)
		{
			if (all.Get(i).Name() == name)
				return all.Get(i);
		}
		return null;
	}
}
