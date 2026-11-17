// Minimal stand-in for Bohemia's vanilla tree: only what the fixtures name.
// The DayZ 1.30 shape: EntityAI declares the construction hook.
class Managed
{
}

class EntityAI : Managed
{
    protected void RegisterConstructionSyncVariables()
    {
    }
}
