// '%' between integers, as vanilla writes it (3_game/tools/uimanager.c:255,
// 3_game/tools/timeconversions.c:64), and the fix for the failing shape: the
// '%' goes into an int local first.
class FX_IntModulo
{
    int Pick(int timeInSeconds)
    {
        int index = Math.RandomInt(0, 100) % 2;
        timeInSeconds = timeInSeconds % (24 * 3600);
        return index + timeInSeconds;
    }

    float Offset(int n)
    {
        int m = n % 4;
        float ox = m * 0.7 - 1.05;
        return ox;
    }
}
