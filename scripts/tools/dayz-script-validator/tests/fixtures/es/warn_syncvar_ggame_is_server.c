class SyncVarGGameIsServerFixture {
    bool m_X;

    void SyncVarGGameIsServerFixture()
    {
        RegisterNetSyncVariableBool("m_X");
    }

    void SetX(bool value)
    {
        if (g_Game.IsServer())
        {
            m_X = value;
            SetSynchDirty();
        }
    }
}
