class CfgPatches
{
	class AutoTest
	{
		units[] = {};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Scripts"};
	};
};

class CfgMods
{
	class AutoTest
	{
		dir = "AutoTest";
		name = "AutoTest";
		type = "mod";
		author = "";
		version = "0.1";
		dependencies[] = {"Game", "World", "Mission"};
		class defs
		{
			class gameScriptModule
			{
				value = "";
				files[] = {"AutoTest/scripts/3_Game"};
			};
			class worldScriptModule
			{
				value = "";
				files[] = {"AutoTest/scripts/4_World"};
			};
			class missionScriptModule
			{
				value = "";
				files[] = {"AutoTest/scripts/5_Mission"};
			};
		};
	};
};
