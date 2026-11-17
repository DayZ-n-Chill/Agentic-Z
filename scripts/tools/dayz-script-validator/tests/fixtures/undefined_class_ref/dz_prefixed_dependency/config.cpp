// A mod may name its own patch DZ_*: only Bohemia's patch names count as
// vanilla, so this dependency is unknown.
class CfgPatches
{
    class FX_DzPrefixedConsumer
    {
        requiredAddons[] = {"DZ_Data", "DZ_FX_ThirdParty"};
    };
};
