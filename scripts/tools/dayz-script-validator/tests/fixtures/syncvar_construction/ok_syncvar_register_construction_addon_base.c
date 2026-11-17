class SyncVarKitBase : EntityAI
{
}

class SyncVarKitFixture : SyncVarKitBase
{
    int m_X;

    override void RegisterConstructionSyncVariables()
    {
        super.RegisterConstructionSyncVariables();
        RegisterNetSyncVariableInt("m_X");
    }
}
