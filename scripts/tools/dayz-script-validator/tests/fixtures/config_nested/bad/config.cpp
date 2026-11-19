class CfgPatches
{
    class my_mod
    {
        units[] = {};
        requiredAddons[] = {"DZ_Data"};
    };
};
class CfgVehicles
{
    class my_base;
    class my_armed: my_base
    {
        class SimulationModule: SimulationModule
        {
            drive = "DRIVE_AWD";
        };
    };
};
