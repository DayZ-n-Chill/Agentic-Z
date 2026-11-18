#ifdef DIAG_DEVELOPER
// AZ_TestBridge: the client peer runs from the client mission's update.
// Without -azBridge=<token> the peer stays inactive and Tick returns at once.

// `resume` lives here because the queued pause flag is MissionGameplay's own.
class AZB_MissionClientPeer : AZB_ClientPeer
{
	MissionGameplay m_Mission;

	override bool Execute(AZB_Command c, AZB_Result r)
	{
		switch (c.cmd)
		{
			case "resume":
				return CmdResume(c, r);
		}
		return super.Execute(c, r);
	}

	bool CmdResume(AZB_Command c, AZB_Result r)
	{
		if (!m_Mission)
		{
			Fail(r, "no_mission");
			return true;
		}
		m_Mission.AZB_Resume();
		r.data.paused = m_Mission.IsPaused();
		return true;
	}
}

modded class MissionGameplay
{
	ref AZB_MissionClientPeer m_AZBPeer;

	// Vanilla queues the pause menu when the window is not active at the
	// mission's first update (missiongameplay.c:298); a background test drops it,
	// as /dayz-gate visual's helper does.
	void AZB_Resume()
	{
		m_PauseQueued = false;
		if (IsPaused())
			Continue();
	}

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		if (!m_AZBPeer)
		{
			m_AZBPeer = new AZB_MissionClientPeer();
			m_AZBPeer.m_Mission = this;
			m_AZBPeer.Start("client");
		}
		m_AZBPeer.Tick(timeslice);
		m_AZBPeer.KeepView();
		if (m_AZBPeer.m_HudHidden)
		{
			GetHud().ShowHud(false);
			GetHud().ShowQuickBar(false);
		}
	}
}
#endif
