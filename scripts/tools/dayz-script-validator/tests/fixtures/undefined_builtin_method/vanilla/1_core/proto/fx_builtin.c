// Minimal stand-in for the built-in classes of Bohemia's vanilla tree: only
// the members the fixtures call, under their real names. vector has no Cross,
// as in 1.30.164200; a declaration of it inside a comment does not count:
// vector Cross(vector v)
class Class
{
	proto native external bool IsInherited(typename type);
	proto native owned external string ClassName();
}

class Managed
{
}

class bool
{
	string ToString()
	{
		return "";
	}
}

class int
{
	proto string ToString();
}

class float
{
	proto string ToString(bool simple = true);
}

class vector
{
	static const vector Up = "0 1 0";

	// One declaration written once per branch, each branch opening its own
	// `(`: counting brackets loses every name after it.
#ifdef FX_ROUND
	proto vector Rounded(float precision,
#else
	proto vector Rounded(int digits,
#endif
		bool keepSign);

	/* vector Cross(vector v) */
	proto float Normalize();
	proto native float Length();

	static float Dot(vector v1, vector v2)
	{
		return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2];
	}

#ifdef DIAG_DEVELOPER
	proto string ToDebugString();
#endif
}

class string
{
	proto native int Length();
	static proto string Format(string fmt, void param1 = NULL);
}

class typename
{
	proto native owned string ToString();

	static string EnumToString(typename e, int enumValue)
	{
		return "";
	}
}

class array<Class T>
{
	proto native int Count();
	proto native int Insert(T value);
}

class set<Class T>
{
	proto native int Count();
}

class map<Class TKey,Class TValue>
{
	proto native int Count();
	proto native bool Contains(TKey key);
}

typedef array<string> TStringArray;
typedef int[] FX_Handle;
typedef string FX_ResourceName;
class FX_ResourceName : string
{
}
