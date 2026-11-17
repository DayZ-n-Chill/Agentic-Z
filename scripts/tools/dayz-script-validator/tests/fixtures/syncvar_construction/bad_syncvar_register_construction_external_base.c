class SyncVarExternalHookFixture : SyncVarExternalHookBase
{
    int m_X;

    override void RegisterConstructionSyncVariables()
    {
        RegisterNetSyncVariableInt("m_X");
    }
}
