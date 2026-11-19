// 20 terms and no string literal: numbers are added, not joined. Not measured
// in game, and not judged.
class FX_Numbers20
{
    static float Run(int i0, float f0)
    {
        float x = 1 + i0 + 2 + f0 + 3 + i0 + 4 + f0 + 5 + i0 + 6 + f0 + 7 + i0 + 8 + f0 + 9 + i0 + 10 + f0;
        return x;
    }
}
