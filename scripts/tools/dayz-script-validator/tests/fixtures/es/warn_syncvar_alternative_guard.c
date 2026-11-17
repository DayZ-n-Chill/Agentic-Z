class SyncVarAlternativeGuardFixture {
    bool m_X;

    void SyncVarAlternativeGuardFixture()
    {
        RegisterNetSyncVariableBool("m_X");
    }

    void SetX(bool value)
    {
        if (GetGame().IsServer())
        {
            m_X = value;
            SetSynchDirty();
        }
    }
}
