class WarnCtxReadRpcIfndefServerFixture
{
    int m_X;

    override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
    {
#ifndef SERVER
        ctx.Read(m_X);
#endif
    }
}
