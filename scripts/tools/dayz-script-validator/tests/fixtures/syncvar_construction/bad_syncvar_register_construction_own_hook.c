class SyncVarOwnHookBase
{
    void EEInit()
    {
        RegisterConstructionSyncVariables();
    }

    void RegisterConstructionSyncVariables()
    {
    }
}

class SyncVarOwnHookFixture : SyncVarOwnHookBase
{
    int m_X;

    override void RegisterConstructionSyncVariables()
    {
        RegisterNetSyncVariableInt("m_X");
    }
}
