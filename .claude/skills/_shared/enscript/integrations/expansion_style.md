# Expansion style: naming and structure for mods that target DayZ Expansion

Naming and structure rules for a mod that extends DayZ Expansion or runs beside it.

> **Read this only for Expansion targeted work.** The default style for every script task is `_shared/enscript-style.md`, which uses vanilla examples. This file adds the points where a mod that touches Expansion must follow Expansion's own conventions, or must keep clear of them. Where the two disagree, this file wins for Expansion targeted code only.
>
> The examples below are original and short. They show the shape of each convention, not Expansion's code. Expansion ships packed and under its own license, so never paste its scripts into a mod. Check every class and method name you rely on against the Expansion version the mod declares in `requiredAddons[]`, because Expansion renames things between releases.
>
> **Where the names were checked.** Expansion and Community Framework (CF) are not vanilla, so their names are not under `P:\scripts\`. Every Expansion name below was checked in the shipped Expansion PBOs under `P:\Mods\`: mostly `P:\Mods\@DayZ-Expansion-Core\Addons\core_scripts.pbo`, with the defines in the `0_*_preload.pbo` files and the keybinds in `P:\Mods\@DayZ-Expansion\Addons\scripts.pbo`. A source line gives the PBO and the file inside it. CF names were checked in `P:\Mods\@CF\Addons\scripts.pbo`, the same PBO `community_framework.md` cites. Expansion renames things between releases, so recheck against the version the mod declares after an Expansion update.

## When this file applies

- The mod lists an Expansion addon (for example `DayZExpansion_Core_Scripts`, the `CfgPatches` class in the `config.bin` of `core_scripts.pbo`) in `requiredAddons[]`.
- The mod writes `modded class` on an Expansion class, or reads Expansion settings or modules.
- The mod must load cleanly with or without Expansion, and guards its Expansion code with a define.

For a plain vanilla mod, stop here and use `_shared/enscript-style.md`.

## 1. Class names: Expansion owns the `Expansion` prefix

Expansion names its own classes `Expansion<Thing>`, for example `ExpansionSettingBase` (`core_scripts.pbo`, `3_Game\DayZExpansion_Core\Settings\ExpansionSettingBase.c:13`) and the settings classes built on it, such as `ExpansionCoreSettings` (`3_Game\DayZExpansion_Core\Settings\Core\ExpansionCoreSettings.c:15`). That prefix belongs to Expansion.

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

Expansion adds many members to vanilla classes such as `PlayerBase` and `ItemBase`, and marks them `m_Expansion_<Name>`, for example `m_Expansion_LeavingSafeZone` in its `modded class PlayerBase` (`core_scripts.pbo`, `4_World\DayZExpansion_Core\Entities\ManBase\PlayerBase.c:31` and `:49`). Methods it adds to vanilla classes are named `Expansion_<Name>`, for example `Expansion_SendNear` in the same file (`PlayerBase.c:87`). Both stand out from vanilla and from other mods.

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

Do not reuse the `m_Expansion_` or `Expansion_` prefix for your own additions, even inside a `modded class` of an Expansion class. When Expansion later adds a member with the same name, the compiler reports a duplicate and your mod stops loading *(unverified: compiler behaviour; the engine compiler is not on `P:\`, so test it in Workbench)*.

## 3. Defines: guard every Expansion reference

Each Expansion part sets its own define in a preload script: `EXPANSIONMODCORE` (`P:\Mods\@DayZ-Expansion-Core\Addons\0_core_preload.pbo`, `Common\DayZExpansion_Core_Defines.c:77`, commented there as the define third party mods use to know Expansion is loaded), `EXPANSIONMODAI` (`P:\Mods\@DayZ-Expansion-AI\Addons\0_ai_preload.pbo`, `Common\DayZExpansion_AI_Defines.c:4`) and `EXPANSIONMODBASEBUILDING` (`P:\Mods\@DayZ-Expansion-Bundle\Addons\0_basebuilding_preload.pbo`, `Common\DayZExpansion_BaseBuilding_Defines.c:16`). Expansion Core guards on them itself, for example `#ifdef EXPANSIONMODAI` at `core_scripts.pbo`, `4_World\DayZExpansion_Core\Classes\Commands\ExpansionHumanST.c:87`.

- A mod that **requires** Expansion lists it in `requiredAddons[]` and needs no guard.
- A mod that **works with or without** Expansion wraps every line that names an Expansion type in the matching define. Without the guard the script fails to compile with `Unknown type` when Expansion is absent *(unverified: compiler behaviour; the engine compiler is not on `P:\`, so test it in Workbench)*.
- A guarded block that holds only comments is legal. Vanilla ships such blocks, for example `P:\scripts\4_world\classes\environment\environment.c:1-3` and `P:\scripts\3_game\entities\entityai.c:1147-1149`.

In the example, `GetExpansionSettings()` is a static function (`core_scripts.pbo`, `3_Game\DayZExpansion_Core\Settings\ExpansionSettings.c:320`) and `GetCore()` is its getter for `ExpansionCoreSettings` (`ExpansionSettings.c:281`).

```
#ifdef EXPANSIONMODCORE
    ExpansionCoreSettings core = GetExpansionSettings().GetCore();
    if (core)
        YourMod_ApplyCoreSettings(core);
#endif
```

Your own defines follow the vanilla rule: uppercase, with your tag first, such as `YOURMOD_EXPANSION_BRIDGE`. Do not invent defines that start with `EXPANSION`.

## 4. Settings: the Expansion settings class pattern

Expansion keeps each settings group in its own class built on `ExpansionSettingBase`, read through `GetExpansionSettings().Get<Group>()`. A settings class there typically has the following members, as `ExpansionSettingBase` and `ExpansionCoreSettings` show (paths inside `core_scripts.pbo`, under `3_Game\DayZExpansion_Core\Settings\`):

- a `static const int VERSION`, raised whenever the saved layout changes, with an upgrade step for older files (`Core\ExpansionCoreSettings.c:17`);
- `Defaults()` to fill in first run values (`ExpansionSettingBase.c:98`);
- `OnLoad()` and `OnSave()` for the JSON file in the server profile (`ExpansionSettingBase.c:61` and `:92`);
- `OnSend()` and `OnRecieve()` to sync the values a client needs (`ExpansionSettingBase.c:45` and `:38`).

Note the spelling: Expansion's receive method is `OnRecieve` (`ExpansionSettingBase.c:38`, overridden at `Core\ExpansionCoreSettings.c:27`). When you override it, the name must match exactly or `override` fails to compile *(unverified: compiler behaviour; the engine compiler is not on `P:\`, so test it in Workbench)*. Keep the spelling only in overrides of Expansion methods; spell `Receive` correctly in your own names.

**Where your settings go.** Do not add fields to an Expansion settings class. Its JSON file and network payload belong to Expansion. An added field is saved into Expansion's own JSON file in the server profile, and it never reaches clients, because `OnSend()` and `OnRecieve()` write and read a fixed list of fields one by one (`Core\ExpansionCoreSettings.c:55-59` and `:27-53`). Keep your settings in your own class and file, named with your tag, and read Expansion's settings only through their getters.

```
class YourMod_BountySettings
{
    static const int VERSION = 2;

    int Version = VERSION;
    bool Enabled = true;
    float RewardMultiplier = 1.0;
}
```

Load and save it with vanilla `JsonFileLoader` (`P:\scripts\3_game\tools\jsonfileloader.c:1`), and follow `_shared/enscript/patterns/json_config_migration.md` for version upgrades. The fields are public because `JsonFileLoader` maps them to JSON keys by name. `PascalCase` matches how Expansion names its own settings fields, for example `ServerUpdateRateLimit` (`Core\ExpansionCoreSettings.c:19`), so admins see one style across both files.

## 5. Modules: Expansion runs on Community Framework

Expansion's systems are Community Framework modules: classes named `Expansion<Thing>Module` that inherit `CF_ModuleWorld` or `CF_ModuleGame` and carry `[CF_RegisterModule(...)]`, for example `ExpansionZoneModule` (`core_scripts.pbo`, `4_World\DayZExpansion_Core\Classes\Systems\Zone\ExpansionZoneModule.c:16-17`). `CF_ModuleGame` is CF `scripts.pbo`, `3_Game\CommunityFramework\Module\CF_ModuleGame.c:1`; Expansion's `ExpansionSoundModule` uses it (`core_scripts.pbo`, `3_Game\DayZExpansion_Core\Sound\ExpansionSoundModule.c:17-18`). They are looked up with `CF_Modules<T>.Get(...)` (CF `scripts.pbo`, `1_Core\CommunityFramework\Module\CF_Modules.c:1`, with `static T Get()` at `:3` and `static bool Get(inout T module)` at `:11`), as Expansion does at `core_scripts.pbo`, `4_World\DayZExpansion_Core\Entities\ItemBase.c:431`, not vanilla `GetPlugin()` (`P:\scripts\4_world\plugins\pluginmanager.c:326`).

For a mod beside Expansion:

- Build your own systems the same way so they share the lifecycle Expansion uses. Name them `YourMod_<Thing>Module`. The CF module API is in `_shared/enscript/integrations/community_framework.md`; `OnInit()` and `EnableMissionStart()` in the example below are checked there (Module System section). In CF `scripts.pbo`, `OnInit()` is declared at `1_Core\CommunityFramework\Module\CF_ModuleCore.c:70` and `EnableMissionStart()` at `:81`.
- CF modules make CF a hard dependency. A mod that inherits `CF_ModuleWorld` or `CF_ModuleGame`, or uses `[CF_RegisterModule(...)]`, lists `JM_CF_Scripts` (the `CfgPatches` class in the `config.bin` of `P:\Mods\@CF\Addons\scripts.pbo`) in `requiredAddons[]`. Without CF loaded, the script compile fails on the unknown CF type *(unverified: compiler behaviour; the engine compiler is not on `P:\`, so test it in Workbench)*. A mod that must also run without CF uses vanilla plugins through `GetPlugin()` (`P:\scripts\4_world\plugins\pluginmanager.c:326`) instead.
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

- **Input actions.** Expansion names its keybinds `UAExpansion<Action>`, for example `UAExpansionAutoRunToggle` (`P:\Mods\@DayZ-Expansion\Addons\scripts.pbo`, `5_Mission\DayZExpansion\Mission\MissionGameplay.c:40`; Expansion Core has none). Name yours `UAYourMod<Action>` in your own `inputs.xml`, so the two sets never clash in the controls menu.
- **Tracing and errors.** Expansion has its own helpers, `EXTrace` for traces and `EXError` for errors (`core_scripts.pbo`, `3_Game\DayZExpansion_Core\ExpansionTracing.c:30` and `3_Game\DayZExpansion_Core\ExpansionStatic.c:139`). Code written inside Expansion's classes may use them when the mod requires Expansion. A mod that also runs without Expansion uses the vanilla `Print` (`P:\scripts\1_core\proto\endebug.c:96`) and `ErrorEx` (`P:\scripts\1_core\proto\endebug.c:83`) calls from the vanilla guide, so it does not depend on Expansion for logging. Do not use `Debug.Log` for messages you must see: it writes only when `LogManager.IsLogsEnable()` is true (`P:\scripts\3_game\tools\debug.c:595`; see `_shared/enscript/references/api_game.md`).

## Where this differs from the vanilla guide

Every Expansion and CF name in this table is cited in the sections above.

| Topic | Vanilla guide (default) | Expansion targeted work |
|---|---|---|
| New class names | Your mod tag | Your mod tag; `Expansion` only on `modded class` of an Expansion class |
| Members on vanilla classes | `m_YourMod_<Name>` | Same; never `m_Expansion_` |
| Service lookup | `GetPlugin(Type)` | `CF_Modules<T>.Get(...)` for Expansion and CF modules |
| Settings | Your own class with `JsonFileLoader` | Same; read Expansion settings through `GetExpansionSettings()`, never add to them |
| Receive override | Your own spelling | `OnRecieve`, exactly as Expansion spells it |
| Optional dependency | Not needed | Guard every Expansion type with its `EXPANSIONMOD...` define |
| Logging | `Print`, `ErrorEx` (`Debug.Log` writes only when logs are enabled) | Same, unless the mod requires Expansion and the code sits in its classes |

## References

- [DayZ Expansion Scripts](https://github.com/salutesh/DayZ-Expansion-Scripts): read for names and signatures only; do not copy code.
- `_shared/enscript/integrations/community_framework.md`: the CF module API.
- `/dayz-conflict-check`: finds class name and path collisions between a mod and Expansion, CF or COT.
