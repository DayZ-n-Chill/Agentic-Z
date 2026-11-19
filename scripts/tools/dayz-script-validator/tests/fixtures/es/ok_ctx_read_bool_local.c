class CtxReadBoolLocalFixture
{
    int m_X;

    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        bool ok = ctx.Read(m_X);
        if (!ok) return false;
        return true;
    }
}
