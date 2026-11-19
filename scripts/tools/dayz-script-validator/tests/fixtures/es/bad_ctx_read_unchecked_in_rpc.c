class BadCtxReadRpcFixture
{
    int m_X;

    override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
    {
#ifdef SERVER
        ctx.Read(m_X);
#endif
    }
}
