modded class MissionServer
{
    override void OnClientRespawnEvent(PlayerIdentity identity, PlayerBase player)
    {
        super.OnClientRespawnEvent(identity, player);
        player.GetInventory().CreateInInventory("AKM");
        EntityAI vest = player.GetInventory().CreateAttachment("PlateCarrierVest");
    }
}
