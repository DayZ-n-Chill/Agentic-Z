class CfgPatches
{
    class FX_Forms
    {
        requiredAddons[] = {"DZ_Data"};
    };
};

#define FX_CONFIG_SWITCH

class CfgMods
{
    class FX_Forms
    {
        defines[] = {"FX_FORMS_ON"};
    };
#ifdef FX_OPTIONAL_MOD
    class FX_FormsOptional
    {
        defines[] = {"FX_CONDITIONAL_CONFIG_FLAG"};
    };
#endif
#ifdef FX_CONFIG_SWITCH
    class FX_FormsSwitched
    {
        defines[] = {
            "FX_SWITCHED_FLAG",
#ifdef FX_OPTIONAL_MOD
            "FX_SPANNING_FLAG",
#endif
        };
    };
#endif
};
