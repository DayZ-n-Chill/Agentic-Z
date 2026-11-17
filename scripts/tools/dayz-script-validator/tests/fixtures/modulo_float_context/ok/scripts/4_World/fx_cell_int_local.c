// Inbox d35a, case A: case C with the '%' in an int local first. It compiled
// and ran on DayZDiag 1.30.164289.
class FX_CellIntLocal
{
    static const float STEP = 150;
    static const float RADIUS = 110;
    static const int SIDE = 103;

    static float Run(int cell)
    {
        int col = cell % SIDE;
        float x = col * STEP;
        x = x + STEP * 0.5;
        return x;
    }
}
