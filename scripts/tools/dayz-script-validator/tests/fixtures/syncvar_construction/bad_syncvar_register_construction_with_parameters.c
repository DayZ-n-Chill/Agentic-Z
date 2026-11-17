class SyncVarLateRegistrationBase
{
    void RegisterConstructionSyncVariables(EntityAI target)
    {
    }
}

class SyncVarLateRegistrationFixture : SyncVarLateRegistrationBase
{
    override void RegisterConstructionSyncVariables(EntityAI target)
    {
        target.RegisterNetSyncVariableInt("m_X");
    }
}
