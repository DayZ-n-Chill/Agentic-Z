class WarnCtxReadOnVarSyncFixture
{
    int m_X;

    override void OnVariablesSynchronized(ParamsReadContext ctx)
    {
        ctx.Read(m_X);
    }
}
