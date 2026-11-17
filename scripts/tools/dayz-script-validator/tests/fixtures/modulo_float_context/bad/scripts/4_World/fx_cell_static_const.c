// Inbox d35a, case C, the ticket's: DayZDiag 1.30.164289 gave "Unknown operator '%'" at line 10.
class FX_CellStaticConst
{
    static const float STEP = 150;
    static const float RADIUS = 110;
    static const int SIDE = 103;

    static float Run(int cell)
    {
        float x = (cell % SIDE) * STEP + STEP * 0.5;
        return x;
    }
}
