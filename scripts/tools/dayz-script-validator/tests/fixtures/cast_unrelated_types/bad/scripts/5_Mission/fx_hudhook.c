// Inbox fb-20261009-122148-c852, DayZDiag 1.29, on the source this one
// stands for:
//   Types 'IngameHud' and 'Mission' are not related
// and the Mission module did not compile. The cast sits on line 12.
class FX_HudHook
{
    IngameHud hud;

    void Attach()
    {
        Mission mission = GetGame().GetMission();
        hud = IngameHud.Cast(mission);
    }
}
