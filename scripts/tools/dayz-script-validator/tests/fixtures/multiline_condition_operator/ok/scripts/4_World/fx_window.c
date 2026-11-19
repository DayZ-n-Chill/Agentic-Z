class FX_Window
{
    static const float A = 1.0;

    static float Score(float t)
    {
        bool early = t >= A && t < 2.0;
        bool late = t >= 3.0 && t < 4.0;
        if (early || late)
            return -1.0;
        if (early) // a trailing ||
            return 0.0;
        if (Check(t,
                  early)) /* && */
            return 1.0;
        string s = "if (a ||";
#if 0
        if (early ||
            late)
            return 2.0;
#endif
        return t;
    }

    static bool Check(float t, bool b)
    {
        return b;
    }
}
