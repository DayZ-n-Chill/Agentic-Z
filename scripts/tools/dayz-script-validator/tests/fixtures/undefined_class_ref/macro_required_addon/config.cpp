// Dependencies named through a macro and a bare number: neither is a string
// literal, so neither is read, and the rule must not judge.
#define FX_DEPENDENCY "FX_Dep_Scripts"
class CfgPatches
{
    class FX_MacroConsumer
    {
        requiredAddons[] = {"DZ_Data", FX_DEPENDENCY, 123};
    };
};
