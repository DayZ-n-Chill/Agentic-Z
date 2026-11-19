class SyncVarFieldDeclarationFixture {
    protected int m_X = 0;

    void SyncVarFieldDeclarationFixture()
    {
        RegisterNetSyncVariableInt("m_X");
    }

    void SetX(int value)
    {
        #ifdef SERVER
        m_X = value;
        SetSynchDirty();
        #endif
    }
}
