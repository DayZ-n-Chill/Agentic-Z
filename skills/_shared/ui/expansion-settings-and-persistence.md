# Expansion settings and saved files

Where DayZ Expansion keeps its settings and saved state, which fields a market item has, how it splits server data from client preferences, and how another mod detects Expansion at run time. The Market menu itself is in `expansion-market-menu.md`.

DayZ Expansion is a third party mod. These facts are read from its own scripts (the paths below are inside its source), not measured on a server and not on `P:\`. Line numbers move between releases, so search for the symbol.

## The vanilla loader underneath

Expansion saves everything with vanilla `JsonFileLoader<T>` (`P:\scripts\3_game\tools\jsonfileloader.c:1`). It calls `JsonLoadFile` and `JsonSaveFile` (`:105` and `:134`), which still exist on 1.30 under a comment that says to use `LoadFile` (`:7`) and `SaveFile` (`:42`) instead. Write new code with `LoadFile` and `SaveFile`; they return a bool and an error message.

## One file per thing

The Market's paths are constants (`Scripts/3_Game/DayZExpansion_Market/Expansion_Market_Constants.c:14` to `:21`):

```c
static const string EXPANSION_TRADER_ZONES_FOLDER = EXPANSION_MISSION_FOLDER + "traderzones\\";
static const string EXPANSION_ATM_FOLDER = EXPANSION_FOLDER + "ATM\\";
static const string EXPANSION_MARKET_SETTINGS = EXPANSION_MISSION_SETTINGS_FOLDER + "MarketSettings.json";
static const string EXPANSION_MARKET_PRESETS_FOLDER = EXPANSION_FOLDER + "MarketPresets\\"; // client

// TraderZone.Save()
JsonFileLoader<ExpansionMarketTraderZone>.JsonSaveFile(EXPANSION_TRADER_ZONES_FOLDER + m_FileName + ".json", this);
// ATM_Data.Save()
JsonFileLoader<ExpansionMarketATM_Data>.JsonSaveFile(EXPANSION_ATM_FOLDER + m_FileName + ".json", this);
```

Global settings, categories, traders, zones with their stock, and ATMs each have their own file. `zone.Save()` runs after a finished trade: after a purchase (`ExpansionMarketModule.c:3147`) and after a sale (`:3725`).

## Where the files live

| What | Folder | Source |
|---|---|---|
| Settings | `$profile:ExpansionMod\Settings\` (`EXPANSION_FOLDER`, `EXPANSION_SETTINGS_FOLDER`) | `DayZExpansion/Core/Scripts/3_Game/DayZExpansion_Core/ExpansionConstants.c:75`, `:78` |
| Mission settings | `$mission:expansion\settings\` | `ExpansionConstants.c:85` |
| `AISettings.json`, `TerritorySettings.json`, `VehicleSettings.json` | The profile settings folder | `ExpansionConstants.c:98`, `:106` and `:107` |
| `QuestSettings.json` | The profile settings folder | `DayZExpansion/Quests/Scripts/3_Game/DayZExpansion_Quests/DayZExpansion_Quest_Constants.c:45` |
| `MarketSettings.json` | The mission settings folder | `DayZExpansion/Market/Scripts/3_Game/DayZExpansion_Market/Expansion_Market_Constants.c:14` to `:18` |
| Traders | `$profile:ExpansionMod\Traders\` | same |
| Market categories | `$profile:ExpansionMod\Market\` | same |
| Trader zones | `$mission:expansion\traderzones\` | same |

The settings file names have no `Expansion` prefix.

## Client preferences stay on the client

Not all state belongs to the server. Attachment presets are saved locally (`Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenuItemManagerPreset.c:13` to `:18` and `:34` to `:42`):

```c
class ExpansionMarketMenuItemManagerPreset
{
    string ClassName;
    string PresetName;
    ref array<string> ItemAttachments;

    void SaveItemPreset(string path)
    {
        JsonFileLoader<ExpansionMarketMenuItemManagerPreset>.JsonSaveFile(path + PresetName + ".json", this);
    }
}
```

The static `LoadItemPreset(string presetName, string path)` reads one back. They go under `MarketPresets\Weapons\` and `MarketPresets\Clothing\` (`EXPANSION_MARKET_WEAPON_PRESETS_FOLDER`, `EXPANSION_MARKET_CLOTHING_PRESETS_FOLDER`). The economy lives on the server; UI preferences live on the client, with the same loader.

## Market item fields

`ExpansionMarketItem` (`DayZExpansion/Market/Scripts/3_Game/DayZExpansion_Market/Settings/ExpansionMarketItem.c:30` to `:48`):

| Field | Type |
|---|---|
| `ClassName` | `string` |
| `MaxPriceThreshold`, `MinPriceThreshold` | `int` |
| `SellPricePercent` | `float` |
| `MaxStockThreshold`, `MinStockThreshold` | `int` |
| `QuantityPercent` | `int` |
| `SpawnAttachments[]`, `Variants[]` | arrays |

## Other names worth knowing

- `ExpansionQuestObjectiveType` starts at `NONE = 1`, then `TARGET`, `TRAVEL`, `COLLECT`, `DELIVERY`, `TREASUREHUNT`, `AIPATROL`, `AICAMP`, `AIESCORT`, `ACTION`, `CRAFTING` (`DayZExpansion/Quests/Scripts/4_World/DayZExpansion_Quests/Systems/Quests/ExpansionQuestObjectiveType.c:13` to `:26`). Use the names; the numbers don't start at 0.
- AI settings include `MaxRecruitableAI`, `OverrideClientWeaponFiring` and `RecreateWeaponNetworkRepresentation` (`DayZExpansion/AI/Scripts/3_Game/DayZExpansion_AI/Settings/ExpansionAISettings.c:53`, `:67` and `:68`).

## Detecting Expansion without depending on it

The Core patch class is `DayZExpansion_Core` (`DayZExpansion/Core/Stub/config.cpp:3`), so `g_Game.ConfigIsExisting("CfgPatches DayZExpansion_Core")` (vanilla `ConfigIsExisting(string path)`, `P:\scripts\3_game\global\game.c:612`) tells you at run time whether it is loaded. Each module's scripts patch is `DayZExpansion_<Module>_Scripts` (`DayZExpansion/Market/Scripts/config.cpp:3`).
