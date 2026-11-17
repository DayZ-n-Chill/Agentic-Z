class CfgPatches
{
    class LF_UIProbe_Scripts
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = {"DZ_Scripts", "DZ_Data"};
    };
};

class CfgMods
{
    class LF_UIProbe
    {
        type = "mod";
        name = "LF_UIProbe";
        dir = "LF_UIProbe";

        class defs
        {
            class missionScriptModule
            {
                value = "";
                files[] = {"LF_UIProbe/scripts/5_Mission"};
            };
        };
    };
};
