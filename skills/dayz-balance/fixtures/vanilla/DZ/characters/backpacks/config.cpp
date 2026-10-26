// Test fixture: backpacks. Class names and parents are vanilla; values are made up.
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
    class TaloonBag_ColorBase: Clothing
    {
        scope = 0;
        weight = 1000;
        inventorySlot[] = {"Back"};
    };
    class TaloonBag_Blue: TaloonBag_ColorBase
    {
        scope = 2;
        itemsCargoSize[] = {5, 6};
    };
    class TaloonBag_Green: TaloonBag_ColorBase
    {
        scope = 2;
        weight = 1400;
        itemsCargoSize[] = {6, 7};
    };
    class TaloonBag_Orange: TaloonBag_ColorBase
    {
        scope = 2;
        weight = 1800;
        itemsCargoSize[] = {7, 8};
    };
    class TaloonBag_Violet: TaloonBag_ColorBase
    {
        scope = 2;
        weight = 600;
        itemsCargoSize[] = {4, 5};
    };
};
