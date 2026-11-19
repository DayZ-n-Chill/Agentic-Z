class Inventory
{
#ifdef PLATFORM_CONSOLE
    protected string GetConsoleToolbarText(int mask)
    {
        return "";
    }

    protected void ConsoleOnlyHook(int value)
    {
    }
#endif

#ifdef DIAG_DEVELOPER
    protected void DiagOnlyHook()
    {
    }
#endif

#ifdef PLATFORM_WINDOWS
    protected void WindowsOnlyHook()
    {
    }
#endif
}
