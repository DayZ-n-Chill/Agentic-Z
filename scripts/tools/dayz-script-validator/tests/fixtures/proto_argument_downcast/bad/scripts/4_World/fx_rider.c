// Inbox fb-20261006-030019-e074, DayZ 1.30.164014 server, on the source this
// one stands for: "Unsafe down-casting, use 'Object.Cast'", "Types 'IEntity'
// and 'Object' are unrelated" and "Cannot convert 'IEntity' to 'Object' for
// argument '6' to method 'RaycastRV'", and the World module did not compile.
// The calls sit on lines 19 and 21.
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
        FX_Physics.FX_Probe(hitEntity);
        bool hit = FX_Physics.FX_Raycast(from, to, pos, dir, comp, hits, hitEntity, m_Human, true, false, 0);
        // The same down-cast, to a proto that EntityAI has from Object.
        m_Self.FX_SetOwner(hitEntity);
        return hit;
    }
}
