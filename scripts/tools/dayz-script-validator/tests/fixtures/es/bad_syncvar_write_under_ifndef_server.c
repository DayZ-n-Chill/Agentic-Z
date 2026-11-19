class SyncVarBadIfndefServerFixture {
    bool m_X;

    void SyncVarBadIfndefServerFixture()
    {
        RegisterNetSyncVariableBool("m_X");
    }

    void SetX(bool value)
    {
        #ifndef SERVER
        m_X = value;
        SetSynchDirty();
        #endif
    }
}
