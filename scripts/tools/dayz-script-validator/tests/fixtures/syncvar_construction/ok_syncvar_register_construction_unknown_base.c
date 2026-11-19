class SyncVarOtherModFixture : SyncVarOtherModBase
{
    int m_X;

    override void RegisterConstructionSyncVariables()
    {
        RegisterNetSyncVariableInt("m_X");
    }
}
