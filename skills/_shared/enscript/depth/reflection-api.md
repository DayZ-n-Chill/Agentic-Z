# Reflection in practice

How production mods use Enforce Script reflection for data binding, registration at load time and calling by name, with worked examples and the limits that make a reflection based test unsafe. The declarations are listed in `../references/api_reflection_profiler.md`.

The vanilla declarations: `EnScript.GetClassVar` (`P:\scripts\1_core\proto\enscript.c:188`) and `SetClassVar` (`:211`); `CallFunction` and `CallFunctionParams` (`:146` and `:147`); `GetVariableCount`, `GetVariableName` and `GetVariableType` (`P:\scripts\1_core\proto\enconvert.c:586` to `:588`); `Spawn` (`enconvert.c:565`); `ToType` (`P:\scripts\1_core\proto\enstring.c:95`); `ScriptCaller` (`P:\scripts\2_gamelib\tools.c:160`) with `Create` (`:165`).

## Fields by name

```c
int intVal;
EnScript.GetClassVar(instance, "fieldName", 0, intVal);

string strVal;
EnScript.GetClassVar(instance, "fieldName", 0, strVal);

Class classVal;
EnScript.GetClassVar(instance, "fieldName", 0, classVal);

EnScript.SetClassVar(instance, "fieldName", 0, newValue);
```

Production mods read and write `int`, `float`, `string`, `bool`, `vector` and `Class` fields this way. Both calls return 1 on success.

## Methods by name

```c
Class returnVal;
g_Game.GameScript.CallFunction(instance, "MethodName", returnVal, singleParam);
g_Game.GameScript.CallFunctionParams(instance, "MethodName", returnVal, new Param1<string>(myString));
```

## Walking the fields of a class

```c
typename t = instance.Type();
int varCount = t.GetVariableCount();
for (int i = 0; i < varCount; i++)
{
    string name = t.GetVariableName(i);
    typename varType = t.GetVariableType(i);
    bool isWidget = varType.IsInherited(Widget);
}
```

## Creating a class from its name

```c
typename tn = "MyMod_Thing".ToType();
if (tn)
{
    Class obj = tn.Spawn();
    MyMod_Thing typed = MyMod_Thing.Cast(obj);
}
```

## Function references

`ScriptCaller` keeps a function to call later. Mods use it for event handlers, deferred work, test registration and RPC dispatch.

```c
ScriptCaller caller = ScriptCaller.Create(MyMod_Thing.MyStaticMethod);
caller.Invoke();
```

## Attributes that run at class load

An attribute runs when the class loads, and its return value is assigned to the field it decorates. A test framework can register each test this way:

```c
[MyMod_Registry.Register(SomeParam)]
static ref SomeType myField;

[MyMod_TestManager.StartTest(ScriptCaller.Create(MyTest))]
private static void MyTest()
{
    MyMod_Assert<int>.Assert(1 + 1, 2);
}
```

## Limits

Measured in game:

- `SetClassVar` can write a `private bool`, but it can't replace a `ref` collection field: eight attempts on a `protected ref TManagedRefArray` all returned 0. Don't recommend reflection writes as a general test hook.
- A failed write is not harmless. After those eight failed writes, deleting the object raised 48 null pointer exceptions, while the same object without reflection had none and kept valid elements. Why is unknown, so don't claim a specific partial change. When `SetClassVar` returns 0, stop using that object and don't send it through its normal deletion path.

`Class.Cast` returns `null` when the run time type doesn't match; it doesn't throw. Cast to a local and test it before use, especially for `array<ref Managed>` and `TManagedRefArray` collections.

## A safe reflection based test

A test that sets state through reflection is only valid when it fails closed:

1. Require `SetClassVar` to return 1 and read the state back before calling the code under test. Otherwise report a setup failure, never a pass.
2. Run the same test against the build without the fix first, and require it to fail.
3. Run one case per call, so one exception can't hide the other cases.
4. Keep the test outside the published PBO, and check that the published PBO is the same before and after. Don't write the test as a `modded class`, because that changes the compiled class tree you are testing.
