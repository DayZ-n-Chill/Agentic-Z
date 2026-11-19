// Minimal stand-in for Bohemia's vanilla tree: only what the fixtures name.
class Managed
{
}

class Object : Managed
{
}

class EntityAI : Object
{
}

class array<Class T>
{
}

typedef array<string> TStringArray

enum EVanillaMode
{
    A,
    B
}

/*sealed*/ class SurfaceDetectionParameters
{
}

#ifdef DIAG_DEVELOPER
class FX_VanillaDiagOnly
{
}
#endif
