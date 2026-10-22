# Expansion style: naming and structure for mods that target DayZ Expansion

Naming and structure rules for a mod that extends DayZ Expansion or runs beside it.

> **Read this only for Expansion targeted work.** The default style for every script task is `_shared/enscript-style.md`, which uses vanilla examples. This file adds the points where a mod that touches Expansion must follow Expansion's own conventions, or must keep clear of them. Where the two disagree, this file wins for Expansion targeted code only.
>
> The examples below are original and short. They show the shape of each convention, not Expansion's code. Expansion ships packed and under its own license, so never paste its scripts into a mod. Check every class and method name you rely on against the Expansion version the mod declares in `requiredAddons[]`, because Expansion renames things between releases.

## When this file applies

- The mod lists an Expansion addon (for example `DayZExpansion_Core_Scripts`) in `requiredAddons[]`.
- The mod writes `modded class` on an Expansion class, or reads Expansion settings or modules.
- The mod must load cleanly with or without Expansion, and guards its Expansion code with a define.

For a plain vanilla mod, stop here and use `_shared/enscript-style.md`.

## 1. Class names: Expansion owns the `Expansion` prefix

Expansion names its own classes `Expansion<Thing>`, for example `ExpansionSettingBase` and the settings classes built on it. That prefix belongs to Expansion.

- **Your own classes take your mod tag, never `Expansion`.** A new class named `ExpansionBountyBoard` collides the day Expansion ships one, and readers will look for it in the wrong mod.
- **A `modded class` keeps the Expansion name**, because you are changing Expansion's class, not making a new one.

```
// Your own new class: your tag
class YourMod_BountyBoard
{
}

// Changing an Expansion class: its name stays, no inheritance added
modded class ExpansionSettingBase
{
}
```

The vanilla rule still holds: never add `: Parent` to a `modded class`.

## 2. Members and methods: one prefix per mod

Expansion adds many members to vanilla classes such as `PlayerBase` and `ItemBase`, and marks them `m_Expansion_<Name>`. Methods it adds to vanilla classes are named `Expansion_<Name>`. Both stand out from vanilla and from other mods.

When your mod adds to the same vanilla class, use your own tag in the same position. Two mods that both say `m_IsHidden` on `PlayerBase` break each other silently.

```
modded class PlayerBase
{
    // Expansion's additions read m_Expansion_..., yours read m_YourMod_...
    protected bool m_YourMod_IsBountyTarget;

    bool YourMod_IsBountyTarget()
    {
        return m_YourMod_IsBountyTarget;
    }
}
```

Do not reuse the `m_Expansion_` or `Expansion_` prefix for your own additions, even inside a `modded class` of an Expansion class. When Expansion later adds a member with the same name, the compiler reports a duplicate and your mod stops loading.

## 3. Defines: guard every Expansion reference

Each Expansion part has a `CfgMods` define, such as `EXPANSIONMODCORE`, `EXPANSIONMODAI` or `EXPANSIONMODBASEBUILDING`. Since DayZ 1.26 the engine creates these from the `CfgMods` class names (see the Preprocessor Directives section of the vanilla guide).

- A mod that **requires** Expansion lists it in `requiredAddons[]` and needs no guard.
- A mod that **works with or without** Expansion wraps every line that names an Expansion type in the matching define. Without the guard the script fails to compile with `Unknown type` when Expansion is absent.
- Never leave the guarded block empty; an empty `#ifdef` block crashes, as the vanilla guide explains.

```
#ifdef EXPANSIONMODCORE
    ExpansionCoreSettings core = GetExpansionSettings().GetCore();
    if (core)
        YourMod_ApplyCoreSettings(core);
#endif
```

Your own defines follow the vanilla rule: uppercase, with your tag first, such as `YOURMOD_EXPANSION_BRIDGE`. Do not invent defines that start with `EXPANSION`.

## 4. Settings: the Expansion settings class pattern

Expansion keeps each settings group in its own class built on `ExpansionSettingBase`, read through `GetExpansionSettings().Get<Group>()`. A settings class there typically has:

- a `static const int VERSION`, raised whenever the saved layout changes, with an upgrade step for older files;
- `Defaults()` to fill in first run values;
- `OnLoad()` and `OnSave()` for the JSON file in the server profile;
- `OnSend()` and `OnRecieve()` to sync the values a client needs.

Note the spelling: Expansion's receive method is `OnRecieve`. When you override it, the name must match exactly or `override` fails to compile. Keep the spelling only in overrides of Expansion methods; spell `Receive` correctly in your own names.

**Where your settings go.** Do not add fields to an Expansion settings class. Its JSON file and network payload belong to Expansion, and an extra field shifts every value read after it. Keep your settings in your own class and file, named with your tag, and read Expansion's settings only through their getters.

```
class YourMod_BountySettings
{
    static const int VERSION = 2;

    int Version = VERSION;
    bool Enabled = true;
    float RewardMultiplier = 1.0;
}
```

Load and save it with vanilla `JsonFileLoader`, and follow `_shared/enscript/patterns/json_config_migration.md` for version upgrades. The fields are public because `JsonFileLoader` maps them to JSON keys by name. `PascalCase` matches how Expansion names its own settings fields, so admins see one style across both files.

## 5. Modules: Expansion runs on Community Framework

Expansion's systems are Community Framework modules: classes named `Expansion<Thing>Module` that inherit `CF_ModuleWorld` or `CF_ModuleGame` and carry `[CF_RegisterModule(...)]`. They are looked up with `CF_Modules<T>.Get(...)`, not vanilla `GetPlugin()`.

For a mod beside Expansion:

- Build your own systems the same way so they share the lifecycle Expansion uses. Name them `YourMod_<Thing>Module`. The full CF module API is in `_shared/enscript/integrations/community_framework.md`.
- Reach an Expansion module only through `CF_Modules<T>.Get(...)`, inside the define guard from section 3, and null check the result before use.
- Do not subclass an Expansion module to change it. Use `modded class` on it, and call `super` in every override.

```
[CF_RegisterModule(YourMod_BountyModule)]
class YourMod_BountyModule : CF_ModuleWorld
{
    override void OnInit()
    {
        super.OnInit();
        EnableMissionStart();
    }
}
```

## 6. Inputs, logging and tracing

- **Input actions.** Expansion names its keybinds `UAExpansion<Action>`. Name yours `UAYourMod<Action>` in your own `inputs.xml`, so the two sets never clash in the controls menu.
- **Tracing and errors.** Expansion has its own helpers, `EXTrace` for traces and `EXError` for errors. Code written inside Expansion's classes may use them when the mod requires Expansion. A mod that also runs without Expansion uses the vanilla `Debug.Log` and `ErrorEx` calls from the vanilla guide, so it does not depend on Expansion for logging.

## Where this differs from the vanilla guide

| Topic | Vanilla guide (default) | Expansion targeted work |
|---|---|---|
| New class names | Your mod tag | Your mod tag; `Expansion` only on `modded class` of an Expansion class |
| Members on vanilla classes | `m_YourMod_<Name>` | Same; never `m_Expansion_` |
| Service lookup | `GetPlugin(Type)` | `CF_Modules<T>.Get(...)` for Expansion and CF modules |
| Settings | Your own class with `JsonFileLoader` | Same; read Expansion settings through `GetExpansionSettings()`, never add to them |
| Receive override | Your own spelling | `OnRecieve`, exactly as Expansion spells it |
| Optional dependency | Not needed | Guard every Expansion type with its `EXPANSIONMOD...` define |
| Logging | `Debug.Log`, `ErrorEx` | Same, unless the mod requires Expansion and the code sits in its classes |

## References

- [DayZ Expansion Scripts](https://github.com/salutesh/DayZ-Expansion-Scripts): read for names and signatures only; do not copy code.
- `_shared/enscript/integrations/community_framework.md`: the CF module API.
- `/dayz-conflict-check`: finds class name and path collisions between a mod and Expansion, CF or COT.
