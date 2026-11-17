class GettypeStringFixture
{
    string Describe()
    {
        // Stripper removes the string; the regex never sees `.GetType() ==` here.
        return "Avoid obj.GetType() == \"X\" — use IsKindOf";
    }
}
