class FX_Rider
{
    Object m_Human;
    EntityAI m_Self;

    bool Probe(vector from, vector to)
    {
        vector pos;
        vector dir;
        int comp;
        set<Object> hits = new set<Object>;
        IEntity hitEntity;
        // An out argument: the proto writes it.
        FX_Physics.FX_Probe(hitEntity);
        // The fix: the entity cast first, then passed as an Object.
        Object hitObject = Object.Cast(hitEntity);
        bool hit = FX_Physics.FX_Raycast(from, to, pos, dir, comp, hits, hitObject, m_Human, true, false, 0);
        // An EntityAI where an Object is taken, and null.
        hit = FX_Physics.FX_Raycast(from, to, pos, dir, comp, hits, m_Self, null, true, false, 0);
        m_Self.FX_SetOwner(m_Human);
        // A comment, a string and a branch that never compiles.
        // m_Self.FX_SetOwner(hitEntity);
        string note = "m_Self.FX_SetOwner(hitEntity)";
        return hit;
    }
}

#if 0
class FX_Dead
{
    void F()
    {
        IEntity hitEntity;
        EntityAI own;
        own.FX_SetOwner(hitEntity);
    }
}
#endif
