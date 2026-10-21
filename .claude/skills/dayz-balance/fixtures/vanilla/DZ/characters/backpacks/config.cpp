// Test fixture: backpacks. Values are made up.
class CfgPatches
{
    class DZ_Characters_Backpacks
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = {"DZ_Data"};
    };
};
class CfgVehicles
{
    class Clothing;
    class Backpack_Base: Clothing
    {
        scope = 0;
        weight = 1000;
    };
    class TaloonPack: Backpack_Base
    {
        scope = 2;
        itemsCargoSize[] = {5, 6};
    };
    class HuntingPack: Backpack_Base
    {
        scope = 2;
        weight = 1400;
        itemsCargoSize[] = {6, 7};
    };
    class MountainPack: Backpack_Base
    {
        scope = 2;
        weight = 1800;
        itemsCargoSize[] = {7, 8};
    };
    class CourierBag: Backpack_Base
    {
        scope = 2;
        weight = 600;
        itemsCargoSize[] = {4, 5};
    };
};
