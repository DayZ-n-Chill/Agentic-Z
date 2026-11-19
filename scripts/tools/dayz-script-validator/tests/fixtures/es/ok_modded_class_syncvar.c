modded class SyncVarModdedFixture {
    int m_Count;

    void SyncVarModdedFixture()
    {
        RegisterNetSyncVariableInt("m_Count", 0, 100);
    }

    void SetCount(int count)
    {
        #ifdef SERVER
        this.m_Count = count;
        SetSynchDirty();
        #endif
    }
}
