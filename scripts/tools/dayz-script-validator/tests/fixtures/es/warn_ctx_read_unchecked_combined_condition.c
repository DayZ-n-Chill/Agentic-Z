class WarnCtxReadCombinedFixture
{
    int m_X;

    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!ctx.Read(m_X) && version > 1)
        {
            return false;
        }
        return true;
    }
}
