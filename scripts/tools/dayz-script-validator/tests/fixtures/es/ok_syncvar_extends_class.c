class SyncVarExtendsFixture extends ItemBase
{
    bool m_X;

    void SyncVarExtendsFixture()
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
