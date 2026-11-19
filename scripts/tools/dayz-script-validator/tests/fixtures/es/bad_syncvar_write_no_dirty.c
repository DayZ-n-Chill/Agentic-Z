class SyncVarBadNoDirtyFixture {
    bool m_X;

    void SyncVarBadNoDirtyFixture()
    {
        RegisterNetSyncVariableBool("m_X");
    }

    void SetX(bool value)
    {
        #ifdef SERVER
        m_X = value;
        #endif
    }
}
