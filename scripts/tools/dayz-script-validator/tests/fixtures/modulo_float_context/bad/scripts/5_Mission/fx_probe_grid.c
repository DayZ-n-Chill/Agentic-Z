// Both shapes failed with "Unknown operator '%'": the first on DayZDiag 1.29
// (2026-09-28), the second on DayZ 1.30 Exp (2026-09-24).
class FX_ProbeGrid
{
    vector Cell(int g)
    {
        return Vector(((g % 5) - 2) * 7.0, 0, 0);
    }

    float Offset(int n)
    {
        float ox = (n % 4) * 0.7 - 1.05;
        return ox;
    }
}
