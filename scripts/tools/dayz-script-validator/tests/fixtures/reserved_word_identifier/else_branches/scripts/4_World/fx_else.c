// #else follows its macro both ways. FX_ELSE_ON is always defined here, so
// the #else of its #ifndef compiles and the #else of its #ifdef never does.
#define FX_ELSE_ON

class FX_ElseBranches
{
    void Run()
    {
#ifndef FX_ELSE_ON
        vector sealed;
#else
        vector local;
#endif
#ifdef FX_ELSE_ON
        EntityAI owned;
#else
        int out;
#endif
    }
}
