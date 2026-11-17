class StringPlusBoolVariableFixture
{
    void Build(string prefix, bool flag)
    {
        string a = prefix + flag;
        string b = flag + prefix;
        string c = "count: " + 3;
    }
}
