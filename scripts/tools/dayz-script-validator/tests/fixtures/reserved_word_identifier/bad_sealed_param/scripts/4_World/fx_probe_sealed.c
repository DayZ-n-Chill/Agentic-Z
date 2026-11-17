// The repro filed on 2026-10-02: DayZDiag 1.29.163709 rejected the World
// module with "Expected name, not a keyword 'sealed'" on the signature line.
class FX_ProbeSealed
{
    void Setup(vector rest, vector sealed)
    {
        Print(sealed);
    }
}
