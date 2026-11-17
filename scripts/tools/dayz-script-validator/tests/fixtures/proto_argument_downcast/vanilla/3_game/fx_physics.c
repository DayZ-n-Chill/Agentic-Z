class Object : IEntity
{
    proto native void FX_SetOwner(Object owner);

    void FX_Attach(Object other)
    {
    }
}

class EntityAI : Object
{
    void FX_Adopt(Object owner)
    {
        FX_SetOwner(owner);
    }
}

class FX_Physics
{
    proto static bool FX_Raycast(vector from, vector to, out vector pos, out vector dir, out int component, set<Object> results, Object with, Object ignore, bool sorted, bool groundOnly, int kind, float radius = 0.0, int flags = 0);
    proto static void FX_Probe(out IEntity hit);
    proto static void FX_Find(out Object found, inout Object kept);
    proto static void FX_Many(Object many[2]);
    proto static void FX_Tag(Object owner, string tag = "a, b", Object other = null);
    proto static void FX_Hold(EntityAI item);
}
