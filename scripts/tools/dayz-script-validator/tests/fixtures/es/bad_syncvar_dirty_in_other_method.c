class SyncVarDirtyOtherMethodFixture {
    bool m_X;

    void SyncVarDirtyOtherMethodFixture()
    {
        RegisterNetSyncVariableBool("m_X");
    }

    void MarkDirty()
    {
        SetSynchDirty();
    }

    void SetX(bool value)
    {
        #ifdef SERVER
        m_X = value;
        MarkDirty();
        #endif
    }
}
