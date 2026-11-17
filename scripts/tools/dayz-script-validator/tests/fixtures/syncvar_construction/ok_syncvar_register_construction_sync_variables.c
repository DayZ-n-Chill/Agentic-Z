class SyncVarConstructionFixture : EntityAI
{
    int m_X;

    override protected void RegisterConstructionSyncVariables()
    {
        super.RegisterConstructionSyncVariables();
        if (m_X == 0)
        {
            RegisterNetSyncVariableInt("m_X");
        }
    }

    void SetX(int value)
    {
        #ifdef SERVER
        m_X = value;
        SetSynchDirty();
        #endif
    }
}
