class FX_HudHook
{
    IngameHud m_Hud;
    Mission m_Mission;

    void Attach()
    {
        Mission mission = GetGame().GetMission();
        // A cast to a derived class, and to a base.
        MissionGameplay gameplay = MissionGameplay.Cast(mission);
        Mission back = Mission.Cast(gameplay);
        // The fix: the HUD comes from the mission.
        Hud base = mission.GetHud();
        m_Hud = IngameHud.Cast(base);
        // A call's result: its type is not tracked.
        m_Hud = IngameHud.Cast(GetGame().GetMission());
        // A name declared nowhere in this function or class.
        m_Hud = IngameHud.Cast(g_Unknown);
        // A typedef, and Class, the root.
        FX_MissionAlias alias = mission;
        m_Hud = IngameHud.Cast(alias);
        Class anything = mission;
        m_Hud = IngameHud.Cast(anything);
        // A comment, a string and a branch that never compiles.
        // m_Hud = IngameHud.Cast(mission);
        string note = "IngameHud.Cast(mission)";
    }

    void FromParameter(Hud param)
    {
        m_Hud = IngameHud.Cast(param);
    }
}

#if 0
class FX_Dead
{
    void F()
    {
        Mission mission;
        IngameHud.Cast(mission);
    }
}
#endif
