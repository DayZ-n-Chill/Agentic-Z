// The four words in the positions vanilla uses them, and names that only
// start with them. None of this is a finding.
sealed class FX_SealedThing
{
}

class FX_Modifiers
{
    vector sealedPos;
    vector localOffset;
    EntityAI owner;
    int outCount;

    proto native owned string FX_GetName();

    void Fill(out array<string> names, local array<string> overridden, local bool check = false)
    {
        int count = 0;
    }

    void Read(notnull out array<EntityAI> items)
    {
    }

    // A modifier at the start of a continued parameter line, later
    // declarators and foreach variables with ordinary names.
    void Split(int a, int b,
        out vector pos, out int index)
    {
        bool first = a < b, outside = false;
        foreach (int i, vector localPos : m_Points)
        {
        }
    }
}
