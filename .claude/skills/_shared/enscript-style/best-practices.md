# Enforce Script style: Best practices and pitfalls

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: Engine traps are filed with the API they belong to; `../enscript/README.md` has the symptom to file map.

## Best Practices

### 1. Use Meaningful Names

```
// Good
float VehicleSearchRadius;
bool CanStoreWithCargo;

// Avoid
float vsr;
bool cswc;
```

### 2. Keep Methods Focused

Each method should do one thing well:

```
void SetDefaultLootingBehaviour()
{
    if (Behaviour == "ROAMING")
        LootingBehaviour = "ALL";
    else
        LootingBehaviour = "DEFAULT";
}
```

### 3. Use Constants for Magic Numbers

```
// Good
const int DEFAULT_MAX_VEHICLES = 10;
MaxStorableVehicles = DEFAULT_MAX_VEHICLES;

// Avoid
MaxStorableVehicles = 10;
```

### 4. Initialize Member Variables

Initialize in constructor or at declaration:

```
void MyMod_GarageSettings()
{
    EntityWhitelist = new TStringArray;
    m_IsLoaded = false;
}
```

### 5. Document Complex Logic

```
//! Toggle between hidden and previously set visibility state for each marker category
int visibility;
int previousVisibility;

visibility |= m_MarkerModule.GetVisibility(MyMod_MarkerType.SERVER);
previousVisibility |= m_MarkerModule.GetPreviousVisibility(MyMod_MarkerType.SERVER);
```

### 6. Use Bitwise Operations Appropriately

```
layerMask |= PhxInteractionLayers.BUILDING;
layerMask |= PhxInteractionLayers.VEHICLE;
layerMask |= PhxInteractionLayers.TERRAIN;

visibility &= MYMOD_MARKER_VIS_WORLD;
```

### 7. Leverage Type Safety

```
// Use enums
EMyMod_LootingBehavior behavior;

// Use proper casting
PlayerBase player = PlayerBase.Cast(entity);
if (player)
{
    // Safe to use player
}
```

### 8. Avoid Complex Expressions in Array Assignments

**Segfault Risk:**

Some language constructs that work in other languages cause segfaults in EnScript:

```
class MyClass
{
    bool m_IsInside[3];

    // WRONG: Causes segfault
    void TestBad(int index, vector a, vector b, float distSq)
    {
        m_IsInside[index] = vector.DistanceSq(a, b) <= distSq;
    }

    // CORRECT: Use intermediate variable
    void TestGood(int index, vector a, vector b, float distSq)
    {
        bool isInside = vector.DistanceSq(a, b) <= distSq;
        m_IsInside[index] = isInside;
    }
}
```

**Rule:** For array assignments with complex expressions, use an intermediate variable.

### 9. Be Aware of Integer Limits

**Integer Comparison Quirk:**

```
// int.MIN = -2147483648

1 < int.MIN;      // Returns TRUE in EnScript!
1 < -2147483647;  // Also returns TRUE!

// Always be careful with MIN/MAX integer comparisons
```

---

## Common Pitfalls and Issues

### Compiler Error Messages

**Misleading Error Locations:**

Compile errors involving:

- Undefined classes (missing addon not loaded)
- Variable name conflicts

Will **NOT** show the correct filename and line number. Instead, they show the last successfully parsed `.c` file at EOF, which is misleading and unhelpful.

**What to do:**

- If error location seems wrong, search for the class/variable name in your entire codebase
- Check that all required addons are loaded
- Look for name conflicts across files

### Understanding Log Files

- **Exception logs:** `crash_<date>_<time>.log`: Contains exceptions (NOT crashes)
- **Actual crashes:** Segfaults create different crash dumps
- Check both log types when debugging issues

### Common Segfault Causes

1. **Complex array assignments**: Use intermediate variables
2. **Empty preprocessor blocks**: Must contain at least one statement
3. **Misused `delete` keyword**: Let garbage collection handle it
4. **Over-specified `ref` usage**: Only use on members/typedefs

### Performance Considerations

- Aggressive garbage collection destroys function-scope instances immediately
- Use `ref`/`autoptr` on class members to prevent premature collection
- Avoid creating temporary objects in tight loops

---

## Engine traps & production pitfalls

Runtime/engine/vanilla-bug issues live next door in the **Enforce Script reference library** at `_shared/enscript/`: each pitfall is filed alongside the pattern, integration, or API it belongs to. See `_shared/enscript/README.md` for the symptom → file map.

---

## Conclusion

This style guide reflects the conventions used in professional DayZ modding. Consistency with these patterns will make your code more maintainable and easier to integrate with existing mods and the vanilla codebase.

### Key Takeaways

- Use PascalCase for classes and methods
- Use `m_` prefix for member variables, `s_` for static
- Use tabs for indentation
- Always use `override` keyword when overriding
- Check for null before using objects
- Document complex logic with comments
- Use preprocessor directives for conditional compilation
- Follow the modded class pattern for extending vanilla code
- Where possible, use proto methods over custom methods for expensive logic
- CfgMod class names are defines in script as of 1.26
- **NEVER use `ref` in method parameters, return types, or local variables**: only on member variables and templates
- **NEVER add inheritance (`: ParentClass`) to `modded` classes**: they already inherit from the original class

### References

- [DayZ Script Diff (Bohemia Interactive)](https://github.com/BohemiaInteractive/DayZ-Script-Diff)
- [Bohemia Interactive Community Wiki: Enforce Script](https://community.bistudio.com/wiki/DayZ:Enforce_Script_Syntax)
