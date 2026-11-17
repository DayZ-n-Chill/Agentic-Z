// Minimal stand-in for Bohemia's vanilla tree: only what the fixtures name.
// EntityAI holds the construction hook's name only in a string.
class Managed
{
}

class EntityAI : Managed
{
    protected string m_HookName = "RegisterConstructionSyncVariables";
}
