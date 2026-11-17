class FX_ConstantsBase
{
    static const int VERSION = 3;

    static int Count()
    {
        return 1;
    }
}

class FX_Constants : FX_ConstantsBase
{
    static const float PUSH_SPEED = 2.5;

#ifdef FX_SWAP
    static const bool ANIM_SWAP_ENABLED = true;
#endif
}

// A class whose parent is not the addon's: a vanilla or another mod's member
// could be meant, so it is not judged.
class FX_Mission : MissionBase
{
}

// An addon class that another root mods is skipped as well (see the unit
// tests); here, a class with a modded declaration in the addon itself.
class FX_Settings
{
    static int s_Level;
}
