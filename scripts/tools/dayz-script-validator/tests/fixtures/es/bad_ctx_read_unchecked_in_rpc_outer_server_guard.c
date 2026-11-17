#ifdef SERVER
class BadCtxReadOuterGuardFixture
{
    int m_X;

    override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
    {
        ctx.Read(m_X);
    }
}
#endif
