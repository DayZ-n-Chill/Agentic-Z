#ifdef DIAG_DEVELOPER
// AZ_TestBridge: the server peer runs from the server mission's update.
// Without -azBridge=<token> the peer stays inactive and Tick returns at once.
modded class MissionServer
{
	ref AZB_ServerPeer m_AZBPeer;

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		if (!m_AZBPeer)
		{
			m_AZBPeer = new AZB_ServerPeer();
			m_AZBPeer.Start("server");
		}
		m_AZBPeer.Tick(timeslice);
	}
}
#endif
