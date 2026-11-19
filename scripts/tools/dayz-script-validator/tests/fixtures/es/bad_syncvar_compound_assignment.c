class SyncVarCompoundAssignmentFixture {
    int m_X;

    void SyncVarCompoundAssignmentFixture()
    {
        RegisterNetSyncVariableInt("m_X");
    }

    void AddX()
    {
        m_X += 1;
        SetSynchDirty();
    }
}
