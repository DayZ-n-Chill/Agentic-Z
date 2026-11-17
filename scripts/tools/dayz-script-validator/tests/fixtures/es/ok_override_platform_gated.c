modded class Inventory
{
#ifdef PLATFORM_CONSOLE
    override string GetConsoleToolbarText()
    {
        return "";
    }
#endif
}
