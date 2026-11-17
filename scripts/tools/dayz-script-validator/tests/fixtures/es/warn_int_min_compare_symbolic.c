class IntMinSymbolicFixture
{
    bool IsSet(int value)
    {
        if (value < int.MIN)
            return false;
        return true;
    }
}
