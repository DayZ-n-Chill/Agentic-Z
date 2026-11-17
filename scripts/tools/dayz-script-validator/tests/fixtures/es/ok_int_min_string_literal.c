class IntMinStringFixture
{
    string Describe()
    {
        // Stripper should remove this string before the regex sees `int.MIN`.
        return "int.MIN < other documented in pitfalls-advanced.md";
    }
}
