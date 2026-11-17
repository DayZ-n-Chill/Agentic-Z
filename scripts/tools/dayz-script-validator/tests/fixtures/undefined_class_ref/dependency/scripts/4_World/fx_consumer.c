class FX_Consumer
{
    void Use()
    {
        FX_DepManager manager = FX_DepManager.Get();
        FX_GonePlanner.Sort();
    }
}
