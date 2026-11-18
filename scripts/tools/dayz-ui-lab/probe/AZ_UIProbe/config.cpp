class CfgPatches
{
    class AZ_UIProbe_Scripts
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = {"DZ_Scripts", "DZ_Data"};
    };
};

class CfgMods
{
    class AZ_UIProbe
    {
        type = "mod";
        name = "AZ_UIProbe";
        dir = "AZ_UIProbe";

        class defs
        {
            class missionScriptModule
            {
                value = "";
                files[] = {"AZ_UIProbe/scripts/5_Mission"};
            };
        };
    };
};
