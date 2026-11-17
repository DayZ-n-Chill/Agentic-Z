// Brackets inside comments and strings are not counted: ( [ {
/* nor in a block comment: } ] ) */
#define FX_ALWAYS_ON

class FX_Balanced
{
    string m_Label = "close ) ] } and open ( [ {";

#ifdef FX_SOME_OTHER_MOD
    void Run(int a, int b)
#else
    void Run(int a)
#endif
    {
#ifdef FX_SOME_OTHER_MOD
        if (a > 0) {
#else
        if (a < 0) {
#endif
            Print(m_Label);
        }
#ifndef FX_ALWAYS_ON
        Print(a];
#endif
#if 0
        int broken = (1 + 2];
#endif
    }
}
