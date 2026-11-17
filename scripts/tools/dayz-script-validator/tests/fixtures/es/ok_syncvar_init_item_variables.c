class SyncVarInitItemVariablesFixture
{
    bool m_X;

    override void InitItemVariables()
    {
        RegisterNetSyncVariableBool("m_X");
    }

    void SetX(bool value)
    {
        #ifdef SERVER
        m_X = value;
        SetSynchDirty();
        #endif
    }
}
