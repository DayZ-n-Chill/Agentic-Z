class FX_Device
{
    protected int m_FxHidden;
}

class FX_Helper
{
    static int Read(FX_Device device)
    {
        return device.m_FxHidden;
    }
}
