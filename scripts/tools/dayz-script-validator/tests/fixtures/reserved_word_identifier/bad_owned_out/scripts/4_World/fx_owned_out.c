class FX_OwnedOut
{
    EntityAI owned;

    int Count(EntityAI target)
    {
        int out = 0;
        if (target)
            out = 1;
        return out;
    }
}
