class SyncVarOtherPrefixFixture {
    int m_X;

    void SyncVarOtherPrefixFixture()
    {
        RegisterNetSyncVariableInt("m_X");
    }

    void CopyFrom(SyncVarOtherPrefixFixture other)
    {
        other.m_X = 1;
    }
}
