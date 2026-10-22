# Enforce Script style: Class layout and comments

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: `[NonSerialized()]` is a vanilla attribute class (`P:\scripts\1_core\proto\enscript.c:122`); attributes are covered in `../enscript/references/language_compile.md`.

## Code Structure

### Class Declaration

```
class ClassName : ParentClass
{
    // Member variables (private/protected first)
    private bool m_PrivateVar;
    protected int m_ProtectedVar;

    // Public member variables
    bool PublicEnabled;
    int MaxItems;
    float WelcomeDelaySeconds;

    // Non-serialized members
    [NonSerialized()]
    bool m_IsLoaded;

    // Constructor
    void ClassName()
    {
        // Initialization
    }

    // Deconstructor
    void~ClassName()
    {
        // Object deletion
    }

    // Methods
    void MethodName()
    {
        // Implementation
    }

    override void ParentMethod()
    {
        super.ParentMethod();
        // Additional implementation
    }
}
```

### Indentation and Spacing

**Tabs vs Spaces:**

- Use **tabs** for indentation (the standard in the vanilla scripts)

**Braces:**

- Opening brace on the same line as declaration
- Closing brace on new line, aligned with declaration

```
void Method()
{
    if (condition)
    {
        // code
    }
    else
    {
        // code
    }
}
```

**Spacing:**

- Space after keywords: `if (`, `for (`, `while (`
- Space around operators: `x = y + z`
- No space before semicolons
- Space after commas: `Method(param1, param2)`

```
if (isEnabled && hasPermission)
{
    for (int i = 0; i < count; i++)
    {
        array.Insert(value);
    }
}
```

---

## Comments

### Single-line Comments

Use `//` for single-line comments:

```
// This is a single-line comment
int value = 5; // Inline comment
```

### Multi-line Comments

Use `/* */` for multi-line comments:

```
/*
 * This is a multi-line comment
 * explaining complex logic
 */
```

### Documentation Comments

Use `//!` for documentation comments:

```
//! Show the welcome message when a player connects
bool EnableWelcomeMsg;

//! @note runs on the server only; clients never load the settings file
void LoadSettings()
```

### Doxygen-style Comments

For class and method documentation:

```
/**
 * @class MyMod_Settings
 * @brief Settings loaded from the server profile folder
 */
class MyMod_Settings
```

### Comment Style

- Be descriptive but concise
- Explain **why**, not just **what**
- Update comments when code changes
- Use comments to mark sections of code

```
//! Settings menu
if (input.LocalPress("UAMyModOpenMenu", false) && !menuOpen)
{
    OpenSettingsMenu();
}

//! Help overlay
if (input.LocalPress("UAMyModToggleHelp", false))
{
    // Implementation
}
```
