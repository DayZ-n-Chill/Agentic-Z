class SyncVarConstructionHelperFixture
{
    int m_X;

    void EEInit()
    {
        RegisterConstructionSyncVariables();
    }

    void RegisterConstructionSyncVariables()
    {
        RegisterNetSyncVariableInt("m_X");
    }
}
