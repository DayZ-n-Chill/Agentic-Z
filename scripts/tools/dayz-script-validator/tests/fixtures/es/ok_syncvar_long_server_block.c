class SyncVarLongServerBlockFixture {
    bool m_Ready;
    int m_Count;
    float m_Load;

    void SyncVarLongServerBlockFixture()
    {
        RegisterNetSyncVariableBool("m_Ready");
        RegisterNetSyncVariableInt("m_Count", 0, 100);
        RegisterNetSyncVariableFloat("m_Load", 0.0, 1.0, 2);
    }

    void ApplyValues(bool ready, int count, float load)
    {
        #ifdef SERVER
        int localCount = count;
        m_Ready = ready;
        localCount = localCount + 1;
        m_Count = localCount;
        if (load > 0.0)
        {
            m_Load = load;
        }
        SetSynchDirty();
        #endif
    }
}
