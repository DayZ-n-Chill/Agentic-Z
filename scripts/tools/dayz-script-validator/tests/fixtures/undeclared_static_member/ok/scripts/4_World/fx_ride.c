modded class FX_Settings
{
    static bool s_Verbose;
}

class FX_Ride
{
    float m_Speed;

    void Tick()
    {
        m_Speed = FX_Constants.PUSH_SPEED;
        int v = FX_Constants.VERSION + FX_Constants.Count();
        if (FX_Constants.ANIM_SWAP_ENABLED)
            m_Speed = 0;
        if (FX_Settings.s_Verbose && FX_Settings.s_Level > 1)
            m_Speed = 1;
        FX_Mission.Cast(GetGame().GetMission());
        FX_Mission.GetMissionTime();
        FX_Constants self = FX_Constants.Cast(null);
        // FX_Constants.REMOVED in a comment
        string s = "FX_Constants.REMOVED";
#if 0
        FX_Constants.REMOVED = 1;
#endif
    }
}
