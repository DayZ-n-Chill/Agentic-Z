// Stand-in for a dependency mod such as CF: its CfgPatches name is what the
// consumer's requiredAddons[] points at.
class CfgPatches
{
    class FX_Dep_Scripts
    {
        requiredAddons[] = {"DZ_Data"};
    };
};
