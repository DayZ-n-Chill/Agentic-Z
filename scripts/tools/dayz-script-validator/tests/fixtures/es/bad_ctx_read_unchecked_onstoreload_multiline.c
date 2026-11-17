class BadCtxReadMultilineFixture
{
    int m_X;

    override bool OnStoreLoad(
        ParamsReadContext ctx,
        int version
    )
    {
        ctx.Read(m_X);
        return true;
    }
}
