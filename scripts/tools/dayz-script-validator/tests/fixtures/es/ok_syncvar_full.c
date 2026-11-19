class SyncVarFullFixture {
    bool m_Ready;

    void SyncVarFullFixture()
    {
        RegisterNetSyncVariableBool("m_Ready");
    }

    void SetReady(bool state)
    {
        #ifdef SERVER
        m_Ready = state;
        SetSynchDirty();
        #endif
    }
}
