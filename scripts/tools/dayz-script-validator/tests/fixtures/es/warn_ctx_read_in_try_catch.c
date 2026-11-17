class CtxReadTryCatchFixture
{
    int m_X;

    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        try {
            if (!ctx.Read(m_X)) return false;
        } catch (Exception e) {
            return false;
        }
        return true;
    }
}
