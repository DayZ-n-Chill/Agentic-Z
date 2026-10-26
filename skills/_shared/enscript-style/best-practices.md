# Enforce Script style: Best practices and pitfalls

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: Engine traps are filed with the API they belong to; `../enscript/README.md` has the symptom to file map.

## Best Practices

### 1. Use Meaningful Names

```
// Good
float WelcomeDelaySeconds;
bool EnableWelcomeMsg;

// Avoid
float wds;
bool ewm;
```

### 2. Keep Methods Focused

Each method should do one thing well:

```
void SetDefaults()
{
	MaxItems = DEFAULT_MAX_ITEMS;
	EnableWelcomeMsg = true;
}
```

### 3. Use Constants for Magic Numbers

```
// Good
const int DEFAULT_MAX_ITEMS = 10;
MaxItems = DEFAULT_MAX_ITEMS;

// Avoid
MaxItems = 10;
```

### 4. Initialize Member Variables

Initialize in constructor or at declaration:

```
void MyMod_Settings()
{
	AllowedItems = new TStringArray;
	m_IsLoaded = false;
}
```

### 5. Document Complex Logic

```
//! Keep the old value so a reload can tell whether the limit changed
int oldMaxItems = MaxItems;
Load();
if (MaxItems != oldMaxItems)
	OnMaxItemsChanged(oldMaxItems);
```

### 6. Use Bitwise Operations Appropriately

`PhxInteractionLayers` is a vanilla enum (`P:\scripts\3_game\global\dayzphysics.c:1`; `BUILDING` at :6, `TERRAIN` at :23):

```
layerMask |= PhxInteractionLayers.BUILDING;
layerMask |= PhxInteractionLayers.TERRAIN;

flags &= ~MYMOD_FLAG_HIDDEN;
```

### 7. Leverage Type Safety

```
// Use enums
EMyMod_State state;

// Use proper casting
PlayerBase player = PlayerBase.Cast(entity);
if (player)
{
	// Safe to use player
}
```

### 8. Avoid Complex Expressions in Array Assignments

**Unverified engine behaviour:** the wiki reports that assigning a complex expression straight into an array element segfaults. The compiler and runtime are engine code, so this cannot be checked on `P:\`; treat it as a report, not a rule:

```
class MyClass
{
	bool m_IsInside[3];

	// AVOID: reported (unverified) to segfault
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

Workaround (safe either way): for array assignments with complex expressions, use an intermediate variable.

### 9. Be Aware of Integer Limits

**Unverified engine behaviour:** the wiki reports this comparison quirk. Integer comparison is engine code, so it cannot be checked on `P:\`:

```
// int.MIN = -2147483648 (P:\scripts\1_core\proto\enconvert.c:28)

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

Are reported to **NOT** show the correct filename and line number, but the last successfully parsed `.c` file at EOF instead (unverified engine behaviour: the compiler is engine code, so this cannot be checked on `P:\`).

**What to do:**

- If error location seems wrong, search for the class/variable name in your entire codebase
- Check that all required addons are loaded
- Look for name conflicts across files

### Understanding Log Files

- **Exception logs:** `crash_<date>_<time>.log`: Contains exceptions (NOT crashes). Unverified: the engine writes these files, so the naming cannot be checked on `P:\`
- **Actual crashes:** Segfaults create different crash dumps (unverified, same reason)
- Check both log types when debugging issues

### Common Segfault Causes

1. **Complex array assignments** (unverified, see Best Practice 8): Use intermediate variables
2. **Misused `delete` keyword** (unverified as a segfault cause): `delete` on a script object is valid and vanilla does it (`P:\scripts\4_world\entities\manbase\playerbase.c:1224`), but never `delete` an entity; use `Delete()` or `DeleteSafe()` (`_shared/enscript/references/language_memory.md`, "Deleting entities")
3. **Over-specified `ref` usage** (unverified as a segfault cause): put `ref` on members and on container element types (`ref array<ref MyData>`, `language_memory.md` rule 2); two `ref`s pointing at each other leak both (`language_memory.md` rule 3)

### Performance Considerations

- A local created with `new` lives for the scope that uses it, so short lived helpers need no `ref` (engine behaviour, `language_memory.md` "Locals"; vanilla example `P:\scripts\3_game\entities\entityai.c:2140`)
- A member created with `new` that nothing else holds must be `ref`, or it is freed at once (engine behaviour, `language_memory.md` rule 1)
- Avoid creating temporary objects in tight loops (unverified engine behaviour: performance is not visible on `P:\scripts`)

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
- Where possible, use proto methods over custom methods for expensive logic (unverified engine behaviour: performance is not visible on `P:\scripts`)
- CfgMod class names are reported to be defines in script as of 1.26 (unverified engine behaviour; nothing on `P:\scripts` shows it, so declare your own `defines[]` instead of relying on it)
- Style rule, not a crash rule: mod code puts `ref` on member variables and on container element types (`array<ref T>`, `language_memory.md` rule 2), and leaves it off method parameters, return types and locals. Vanilla does use `ref` on returns and locals (`ref map<int, string> GetAttachSoundSets()`, `P:\scripts\3_game\inventoryitemtype.c:20`; `ref set<Object> victims`, `P:\scripts\4_world\classes\areadamage\areadamage.c:175`), so code like that is not a defect
- **NEVER add inheritance (`: ParentClass`) to `modded` classes**: they already inherit from the original class

### References

- [DayZ Script Diff (Bohemia Interactive)](https://github.com/BohemiaInteractive/DayZ-Script-Diff)
- [Bohemia Interactive Community Wiki: Enforce Script](https://community.bistudio.com/wiki/DayZ:Enforce_Script_Syntax)
