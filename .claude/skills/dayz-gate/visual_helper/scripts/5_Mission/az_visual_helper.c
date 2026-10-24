// AZ_VisualHelper: the fixed scene /dayz-gate visual takes its screenshots in.
// Loaded for the test session only. Every engine call is listed with its vanilla
// P:\scripts line in test_visual.py (HELPER_CALLS).

// Server: noon on midsummer, and clear, windless weather the engine may not change.
modded class MissionServer
{
	float m_AZVisualTick;
	bool m_AZVisualAnnounced;

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		m_AZVisualTick += timeslice;
		if (m_AZVisualTick < 1)
			return;
		m_AZVisualTick = 0;

		GetGame().GetWorld().SetDate(2026, 6, 21, 12, 0);
		Weather weather = GetGame().GetWeather();
		weather.SetWeatherUpdateFreeze(true);
		weather.GetOvercast().Set(0, 0, 3600);
		weather.GetFog().Set(0, 0, 3600);
		weather.GetRain().Set(0, 0, 3600);
		weather.GetSnowfall().Set(0, 0, 3600);
		weather.SetDynVolFogDistanceDensity(0, 0);
		weather.SetDynVolFogHeightDensity(0, 0);
		weather.SetDynVolFogHeightBias(0, 0);
		weather.SetWindMaximumSpeed(0);
		weather.SetWindFunctionParams(0, 0, 0);
		weather.GetWindMagnitude().Set(0, 0, 3600);

		if (!m_AZVisualAnnounced)
		{
			m_AZVisualAnnounced = true;
			Print("[AZ-VISUAL] SCENE noon, clear weather, no wind");
		}
	}
}

// Client: no pause menu, no HUD, and a still camera at the centre of the map
// facing north, so the picture never depends on the window, the mouse or the loot.
modded class MissionGameplay
{
	Camera m_AZVisualCamera;

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
		if (!player || !player.IsPlayerLoaded())
			return;

		// Vanilla queues the pause menu when the window is not active at the
		// mission's first update; the test runs in the background, so drop it.
		m_PauseQueued = false;
		if (IsPaused())
			Continue();

		if (!m_AZVisualCamera)
		{
			float half = GetGame().GetWorld().GetWorldSize() / 2;
			vector spot = Vector(half, GetGame().SurfaceY(half, half) + 1.7, half);
			Class.CastTo(m_AZVisualCamera, GetGame().CreateObject("staticcamera", spot, true));
			m_AZVisualCamera.SetOrientation("0 0 0");
			m_AZVisualCamera.SetActive(true);
			Print("[AZ-VISUAL] CAMERA " + spot.ToString() + " facing north");
		}
		GetHud().ShowHud(false);
		GetHud().ShowQuickBar(false);
	}
}
