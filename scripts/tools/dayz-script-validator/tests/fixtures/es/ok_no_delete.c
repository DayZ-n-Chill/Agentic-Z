class NoDeleteFixture
{
    void Test()
    {
        ref Param param = new Param();
        param = null;
    }
}
