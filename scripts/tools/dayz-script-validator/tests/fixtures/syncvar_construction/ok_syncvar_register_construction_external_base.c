class SyncVarExternalKitFixture : SyncVarExternalKitBase
{
    int m_X;

    override void RegisterConstructionSyncVariables()
    {
        super.RegisterConstructionSyncVariables();
        RegisterNetSyncVariableInt("m_X");
    }
}
