class SyncVarGenericReturnFixture {
    int m_X;

    void SyncVarGenericReturnFixture()
    {
        RegisterNetSyncVariableInt("m_X");
    }

    array<int> BuildValues()
    {
        #ifdef SERVER
        m_X = 1;
        SetSynchDirty();
        #endif
        return new array<int>;
    }
}
