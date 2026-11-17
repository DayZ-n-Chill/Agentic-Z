class Foo
{
    void Check()
    {
        #ifdef SERVER
        int spawnFlags = 1;
        #else
        int spawnFlags = 2;
        #endif
    }
}
