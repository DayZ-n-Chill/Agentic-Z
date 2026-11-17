// Do not write `modded class Transport`: the engine refuses it.
/* modded class Transport */
modded class CarScript
{
    string m_Note = "modded class Transport";
}

class FX_MyTransport extends Transport
{
}

#if 0
modded class Transport
{
}
#endif
