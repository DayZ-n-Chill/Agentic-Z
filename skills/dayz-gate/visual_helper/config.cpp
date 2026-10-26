// AZ_VisualHelper: packed and loaded by /dayz-gate visual for its test session
// only, then removed. It is not part of any mod.
class CfgPatches
{
    class AZ_VisualHelper
    {
        units[] = {};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Data"};
    };
};

class CfgMods
{
    class AZ_VisualHelper
    {
        dir = "AZ_VisualHelper";
        name = "AZ_VisualHelper";
        type = "mod";
        dependencies[] = {"Mission"};

        class defs
        {
            class missionScriptModule
            {
                value = "";
                files[] = {"AZ_VisualHelper/scripts/5_Mission"};
            };
        };
    };
};
