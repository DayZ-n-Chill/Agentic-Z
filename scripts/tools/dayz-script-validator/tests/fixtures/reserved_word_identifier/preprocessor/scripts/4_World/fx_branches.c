// Only the branch under another mod's flag is judged: it compiles once that
// mod is loaded. The other three never compile.
#define FX_ALWAYS_ON
#ifdef FX_ALWAYS_ON
#define FX_DERIVED_ON
#endif

class FX_Branches
{
    void Run()
    {
#ifndef FX_ALWAYS_ON
        vector local;
#endif
#ifdef FX_SOME_OTHER_MOD
        vector sealed;
#endif
#if 0
        int out;
#endif
#ifndef FX_DERIVED_ON
        EntityAI owned;
#endif
    }
}
