// The 20 terms of the 20-term probe in two statements, of 10 and 11 terms (s
// is a term again in the second). Not measured in game; each is under 18.
class FX_Split20
{
    static string Run(int i0, float f0)
    {
        string s = "a" + i0 + " b" + f0.ToString() + " c" + i0 + " d" + f0.ToString() + " e" + i0;
        s = s + " f" + f0.ToString() + " g" + i0 + " h" + f0.ToString() + " i" + i0 + " j" + f0.ToString();
        return s;
    }
}
