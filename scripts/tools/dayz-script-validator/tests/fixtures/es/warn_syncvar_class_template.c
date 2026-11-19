class SyncVarTemplateFixture<T> {
    bool m_X;

    void SyncVarTemplateFixture()
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
