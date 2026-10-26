// Test fixture for /dayz-gate behavior: a small mission init.c shaped like the
// vanilla one (a main() plus a CustomMission). Braces in this comment { and in
// the string below must not confuse the injector.
void main()
{
	Hive ce = CreateHive();
	if (ce)
	{
		ce.InitOffline();
	}
	Print("fixture mission main } done");
}

class CustomMission: MissionServer
{
	override void OnInit()
	{
		super.OnInit();
	}
};

Mission CreateCustomMission(string path)
{
	return new CustomMission();
}
