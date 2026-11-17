// Minimal stand-in for Bohemia's vanilla tree: only what the fixtures name.
// The DayZ 1.30 shape, with a string holding a brace before the hook.
class Managed
{
}

class EntityAI : Managed
{
    protected string m_Open = "{";

    protected void RegisterConstructionSyncVariables()
    {
    }
}
