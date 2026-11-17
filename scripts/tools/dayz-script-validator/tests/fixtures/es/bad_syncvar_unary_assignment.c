class SyncVarUnaryAssignmentFixture {
    int m_X;

    void SyncVarUnaryAssignmentFixture()
    {
        RegisterNetSyncVariableInt("m_X");
    }

    void AddX()
    {
        m_X++;
        SetSynchDirty();
    }
}
