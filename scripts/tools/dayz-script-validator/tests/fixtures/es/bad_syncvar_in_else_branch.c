class SyncVarElseBranchFixture {
    bool m_X;

    void SyncVarElseBranchFixture()
    {
        RegisterNetSyncVariableBool("m_X");
    }

    void SetX(bool value)
    {
        #ifdef SERVER
        int serverOnly = 1;
        #else
        m_X = value;
        SetSynchDirty();
        #endif
    }
}
