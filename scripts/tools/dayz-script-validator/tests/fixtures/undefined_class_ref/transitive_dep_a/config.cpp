// Two patches in one config.cpp: the dependency closure must follow it all
// the same.
class CfgPatches
{
    class FX_DepA_Scripts
    {
        requiredAddons[] = {"DZ_Data", "FX_DepB_Scripts"};
    };
    class FX_DepA_Extra
    {
        requiredAddons[] = {"DZ_Data"};
    };
};
