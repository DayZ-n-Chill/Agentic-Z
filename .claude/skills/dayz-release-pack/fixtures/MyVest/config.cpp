class CfgPatches
{
	class MyVest
	{
		units[] = {"MyVest_Black", "MyVest_Green"};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Characters_Vests", "JM_CF_Scripts"};
	};
};
class CfgVehicles
{
	class Vest_Base;
	class Armband_ColorBase;
	class MyVest_Base: Vest_Base
	{
		scope = 0;
		displayName = "Tactical Vest";
		model = "MyVest\data\myvest_g.p3d";
	};
	class MyVest_Black: MyVest_Base
	{
		scope = 2;
		displayName = "Tactical Vest (Black)";
	};
	class MyVest_Green: MyVest_Base
	{
		scope = 2;
		displayName = "$STR_MyVest_Green";
	};
	class MyVest_Hidden: MyVest_Base
	{
	};
	class MyVest_Patch: Armband_ColorBase
	{
		displayName = "Vest Patch";
	};
};
class CfgMagazines
{
	class Magazine_Base;
	class MyVest_Pouch: Magazine_Base
	{
		scope = public;
		displayName = "Vest Pouch";
	};
};
