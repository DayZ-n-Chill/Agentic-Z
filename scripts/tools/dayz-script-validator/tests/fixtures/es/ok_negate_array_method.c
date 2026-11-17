class Foo
{
    void Check(array<ref Item> list)
    {
        if (!list[1].IsValid())
        {
            return;
        }
    }
}
