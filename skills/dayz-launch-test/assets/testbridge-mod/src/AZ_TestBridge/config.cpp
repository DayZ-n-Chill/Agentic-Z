// AZ_TestBridge: the in-game half of the dayz-testbridge test tool. Packed to
// P:\Mods\@AZ_TestBridge\ for one test session only, then removed. Every script
// file is inside #ifdef DIAG_DEVELOPER, so a retail build compiles nothing, and
// the mod does nothing unless the session passes -azBridge=<token>.
// Never ship it: /dayz-release-pack refuses a release that names it.
class CfgPatches
{
	class AZ_TestBridge
	{
		units[] = {};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Scripts"};
	};
};

class CfgMods
{
	class AZ_TestBridge
	{
		dir = "AZ_TestBridge";
		name = "AZ_TestBridge";
		type = "mod";
		author = "";
		version = "1.0";
		dependencies[] = {"Game", "World", "Mission"};
		class defs
		{
			class gameScriptModule
			{
				value = "";
				files[] = {"AZ_TestBridge/scripts/3_Game"};
			};
			class worldScriptModule
			{
				value = "";
				files[] = {"AZ_TestBridge/scripts/4_World"};
			};
			class missionScriptModule
			{
				value = "";
				files[] = {"AZ_TestBridge/scripts/5_Mission"};
			};
		};
	};
};
