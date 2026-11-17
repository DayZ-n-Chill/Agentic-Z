class IntMinSafeFixture
{
    int m_Sentinel;

    void IntMinSafeFixture()
    {
        m_Sentinel = -1;
    }

    bool IsSet(int value)
    {
        return value > m_Sentinel;
    }
}
