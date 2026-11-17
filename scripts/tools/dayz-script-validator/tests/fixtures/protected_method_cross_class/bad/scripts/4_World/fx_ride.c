// Inbox fb-20261006-002741-28fa (LFSkateboard): a protected method of the
// ride command, called from PlayerBase.OnRPC in the same module. The call
// sits on line 22.
class FX_RideCommand : HumanCommandScript
{
    protected void FX_OnServerState(int state)
    {
    }

    void Update()
    {
        FX_OnServerState(0);
    }
}

modded class PlayerBase
{
    override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
    {
        super.OnRPC(sender, rpc_type, ctx);
        FX_RideCommand cmd = FX_RideCommand.Cast(GetCommand_Script());
        cmd.FX_OnServerState(rpc_type);
    }
}
