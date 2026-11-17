class FX_Reader
{
    static int Read(FX_Device device)
    {
        return device.FX_GetHidden();
    }
}
