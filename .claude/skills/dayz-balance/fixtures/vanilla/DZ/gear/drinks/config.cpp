// Test fixture: drinks. Values are made up.
class CfgPatches
{
    class DZ_Gear_Drinks
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = {"DZ_Data"};
    };
};
class CfgVehicles
{
    class Bottle_Base;
    class WaterBottle: Bottle_Base
    {
        scope = 2;
        weight = 150;
    };
    class Canteen: Bottle_Base
    {
        scope = 2;
        weight = 250;
        varQuantityMax = 1200;
    };
    class GlassBottle: Bottle_Base
    {
        scope = 2;
        weight = 300;
        varQuantityMax = 500;
    };
};
