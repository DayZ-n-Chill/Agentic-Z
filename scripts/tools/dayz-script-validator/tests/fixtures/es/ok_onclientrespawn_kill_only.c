modded class MissionServer
{
    override void OnClientRespawnEvent(PlayerIdentity identity, PlayerBase player)
    {
        super.OnClientRespawnEvent(identity, player);
        if (player && player.IsUnconscious())
        {
            player.SetHealth("", "", 0.0);
        }
    }

    override PlayerBase OnClientNewEvent(PlayerIdentity identity, vector pos, ParamsReadContext ctx)
    {
        PlayerBase player = super.OnClientNewEvent(identity, pos, ctx);
        player.GetInventory().CreateInInventory("AKM");
        return player;
    }
}
