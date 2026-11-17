class CtxReadPatternBFixture
{
    int m_X;

    bool Load(ParamsReadContext ctx)
    {
        if (ctx.Read(m_X))
        {
            m_X = m_X;
        }
        return true;
    }
}
