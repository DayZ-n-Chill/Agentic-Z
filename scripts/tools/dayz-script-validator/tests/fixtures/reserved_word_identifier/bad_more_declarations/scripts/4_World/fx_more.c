// A keyword declared as a name without its type right before it on the
// same line: a parameter split over two lines, later declarators (ended by
// `=`, `;`, `,` or `[`), a foreach variable and a second variable of a for
// header. A use is not reported.
class FX_MoreDeclarations
{
    void Count(array<vector> points, vector
        sealed)
    {
        int good = 1, out = 0;
        int total = Math.Clamp(good, out, 2);
        foreach (vector local : points)
        {
        }
        for (int i = 0, owned = 1; i < 2; i++)
        {
        }
        int first, local;
        int second, owned, third;
        vector fourth, out[2];
    }
}
