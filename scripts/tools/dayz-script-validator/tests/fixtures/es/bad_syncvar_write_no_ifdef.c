class SyncVarBadNoIfdefFixture {
    bool m_X;

    void SyncVarBadNoIfdefFixture()
    {
        RegisterNetSyncVariableBool("m_X");
    }

    void SetX(bool value)
    {
        m_X = value;
        SetSynchDirty();
    }
}
