class SyncVarBadRegisterFixture {
    bool m_X;

    void SomeOtherMethod()
    {
        RegisterNetSyncVariableBool("m_X");
    }
}
