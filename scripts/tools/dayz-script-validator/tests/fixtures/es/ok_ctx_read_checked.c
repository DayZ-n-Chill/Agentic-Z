class CtxReadCheckedFixture
{
    int m_X;
    int m_Y;

    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!ctx.Read(m_X)) return false;
        if (!ctx.Read(m_Y)) return false;
        return true;
    }
}
