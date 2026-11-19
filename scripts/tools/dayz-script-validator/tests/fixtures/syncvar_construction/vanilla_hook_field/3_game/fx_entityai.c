// Minimal stand-in for Bohemia's vanilla tree: only what the fixtures name.
// EntityAI has a field, not a method, named like the construction hook.
class Managed
{
}

class EntityAI : Managed
{
    protected int RegisterConstructionSyncVariables;
}
