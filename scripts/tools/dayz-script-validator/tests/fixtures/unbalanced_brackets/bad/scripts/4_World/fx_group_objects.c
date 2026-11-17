// `m_Objects.Clear();` sabotaged to
// `m_Objects.Clear(;` got PASS from the validator.
class FX_GroupObjects
{
    ref array<Object> m_Objects = new array<Object>;

    void Reset()
    {
        m_Objects.Clear(;
    }
}
