class CfgPatches
{
    class MyVest
    {
        units[] = {"MyVest_PlateCarrier", "MyVest_Bandana"};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Characters_Vests"};
    };
};
class CfgVehicles
{
    class PlateCarrierVest;
    class Bandana_ColorBase;
    class MyVest_PlateCarrier: PlateCarrierVest
    {
        scope = 2;
        displayName = "My Plate Carrier";
    };
    class MyVest_Bandana: Bandana_ColorBase
    {
        scope = 2;
    };
};
