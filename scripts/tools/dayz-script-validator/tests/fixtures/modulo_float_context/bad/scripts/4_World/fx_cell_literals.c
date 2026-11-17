// Inbox d35a, case B: DayZDiag 1.30.164289 gave "Unknown operator '%'" at line 6.
class FX_CellLiterals
{
    static float Run(int cell)
    {
        float x = (cell % 103) * 150 + 150 * 0.5;
        return x;
    }
}
