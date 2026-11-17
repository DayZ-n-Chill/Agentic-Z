class RenamedCtxFixture
{
    int m_X;

    override bool OnStoreLoad(ParamsReadContext reader, int version)
    {
        reader.Read(m_X);
        return true;
    }
}
