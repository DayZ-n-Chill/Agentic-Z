class SyncVarBraceNextLineFixture
{
    bool m_X;

    void SyncVarBraceNextLineFixture()
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
