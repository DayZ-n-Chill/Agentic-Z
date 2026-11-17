// FX_DepBManager lives in FX_DepB_Scripts, which only FX_DepA_Scripts requires.
class FX_TransitiveConsumer
{
    void Use()
    {
        FX_DepBManager.Get();
        FX_GoneEverywhere.Sort();
    }
}
