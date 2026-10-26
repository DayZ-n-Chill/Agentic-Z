// Test fixture: a mod that keeps its item classes in included .hpp files.
class CfgPatches
{
    class IncludeMod
    {
        units[] = {"IncludeMod_HeavyPlate", "IncludeMod_HugePack"};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Data", "DZ_Characters_Vests", "DZ_Characters_Backpacks"};
    };
};
class CfgVehicles
{
    class PlateCarrierVest;
    class TaloonBag_ColorBase;
    #include "items\vests.hpp"
    #include "\IncludeMod\items\backpacks.hpp"
    #include "items\missing.hpp"
};
