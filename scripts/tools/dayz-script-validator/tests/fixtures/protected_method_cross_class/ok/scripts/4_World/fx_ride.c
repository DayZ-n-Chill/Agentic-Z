class FX_RideBase : HumanCommandScript
{
    protected void FX_Hidden()
    {
    }

    void FX_Public()
    {
    }
}

class FX_RideCommand : FX_RideBase
{
    protected void FX_OnServerState(int state)
    {
    }

    void FX_Apply(FX_RideCommand other)
    {
        // the same class, and an ancestor's method from a descendant
        other.FX_OnServerState(1);
        other.FX_Hidden();
    }
}

class FX_SubCommand : FX_RideCommand
{
    void FX_Relay(FX_RideCommand other)
    {
        other.FX_OnServerState(2);
    }
}

modded class FX_RideCommand
{
    void FX_Bridge(int state)
    {
        FX_OnServerState(state);
    }
}

modded class PlayerBase
{
    override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
    {
        super.OnRPC(sender, rpc_type, ctx);
        FX_RideCommand cmd = FX_RideCommand.Cast(GetCommand_Script());
        cmd.FX_Bridge(rpc_type);
        cmd.FX_Public();
        HumanCommandScript base = cmd;
        base.SetFlagFinished(true);
        // cmd.FX_OnServerState(rpc_type);
#if 0
        cmd.FX_OnServerState(rpc_type);
#endif
    }
}
