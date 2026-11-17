# Expansion Market menu: a full stack UI pattern, end to end

The DayZ Expansion Market menu as a worked example of a complete UI feature: an MVC menu, RPCs where the server has authority, an explicit UI state machine and stock that survives restarts. Read `expansion-mvc-patterns.md` first for the base MVC patterns.

**How facts are marked here.** DayZ Expansion is a third party mod, so nothing here is a vanilla fact and none of it can be checked on `P:\`. Every `path:line` in P1 to P12 points into the DayZ Expansion scripts, branch `release`, commit `8f75d554fda209b257c00deb8f01c181e67c980a`; the last section reads a later snapshot. Nothing was checked against the Workshop build of the mod, so line numbers will have moved in the copy on your machine: search for the symbol. The only vanilla call the pattern relies on is `JsonFileLoader`, declared at `P:\scripts\3_game\tools\jsonfileloader.c:1`. The `JsonLoadFile` and `JsonSaveFile` calls the mod uses still exist on 1.30 (`:105` and `:134`), each under a comment that says to use `LoadFile` (`:7`) and `SaveFile` (`:42`) instead; write new code with those two.

---

## Overview: what the Market menu does

```
[Server module]                     [Client menu]
StartTrading()
  → RPC_LoadTraderData          →   CreateSVMenu("ExpansionMarketMenu")
                                     ExpansionMarketMenu: ExpansionScriptViewMenu
                                     layout: scriptclass "ExpansionMarketMenuController"
  → RPC_LoadTraderItems (batch) →   ObservableCollection.Insert/InsertAt
                                     ViewBinding updates widgets automatically
                                     SI_SetTraderInvoker.Invoke() on final batch

[User clicks Buy]
  OnBuyButtonClick()
    SetMenuState(DIALOG) or REQUESTING_PURCHASE (skip confirmations)
    m_MarketModule.RequestPurchase(itemID, qty, price_seen, ...)
  → RPC_RequestPurchase (server RPC)
      FindPurchasePriceAndReserveEx()   ← recalculates, tolerates ±1 rounding
      zone.RemoveStock(..., true)        ← temporary reserve
  ← RPC_Callback(PurchaseSuccess) (client RPC)
      SetMenuState(NONE)
      ActualPurchase / ConfirmPurchase
  → RPC_RequestPurchase [confirmation]
      zone.RemoveStock real + RemoveMoney + Spawn + zone.Save()
  ← RPC_Callback(final) → UpdateUI

Golden rule: the UI sends intents; the server has authority.
The menu never assumes price/stock are correct — it waits for server confirmation before
updating visually.
```

---

## P1 — MVC root: ExpansionScriptViewMenu + ExpansionViewController + ObservableCollection

**Path:line**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenu.c:19` (menu class)
and `:3620` (controller)
Confidence: high (two independent reads).

```
class ExpansionMarketMenu: ExpansionScriptViewMenu
...
class ExpansionMarketMenuController: ExpansionViewController
{
    ref ObservableCollection<ref ExpansionMarketMenuCategory> MarketCategories = new ObservableCollection<...>(this);
    ref ObservableCollection<ref ExpansionMarketMenuDropdownElement> DropdownElements = ...
    string MarketName;
    string PlayerTotalMoney;
    override void PropertyChanged(string property_name)
```

The controller is an active state hub: when `ShowSellables` changes, it cascades updates to
client settings, filters, categories, preview, and skins (`:3648`, `:3655-3664`).

Menu opened from module: `CreateSVMenu("ExpansionMarketMenu")` in `ExpansionMarketModule.c:4587`
after `MoneyCheck()`. UI is NOT opened from a direct RPC.

---

## P2 — Layout binding: scriptclass "ViewBinding" with two-way

**Path:line**: `GUI/layouts/market/expansion_market_menu.layout:12` (root controller) and `:77` (text binding)
Confidence: high (two independent reads).

```
FrameWidgetClass ExpansionMarketMenu {
 scriptclass "ExpansionMarketMenuController"
 ...
      TextWidgetClass market_text {
       scriptclass "ViewBinding"
       Binding_Name "MarketName"
       Two_Way_Binding 1
```

The layout is the declarative binding contract. Root declares controller by name; each child
declares `ViewBinding` with `Binding_Name`. Checkboxes use `Two_Way_Binding 1`.
Collections (`MarketCategories`, `DropdownElements`, `SkinsDropdownElements`) render from
`ObservableCollection`.

---

## P3 — UI state machine: enum ExpansionMarketMenuState with 7 states

**Path:line**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenuState.c:15`
Confidence: high (one read).

```
enum ExpansionMarketMenuState
{
    INVALID = -1,
    NONE,
    LOADING,
    DIALOG,
    REQUESTING_SELECTED_ITEM,
    REQUESTING_PURCHASE,
    REQUESTING_SELL,
    COUNT
};
```

The menu manages an explicit state that blocks interactions during async RPC operations.
`REQUESTING_PURCHASE` is set before the RPC to prevent double-clicks.
State transitions: LOADING → NONE → DIALOG → REQUESTING_PURCHASE / REQUESTING_SELL.

---

## P4 — Confirmation flow: optional dialog + state-blocking before RPC

**Path:line**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenu.c:2591` and `:2637`
Confidence: high (one read).

```
void OnBuyButtonClick()
{
    if (GetExpansionClientSettings().MarketMenuSkipConfirmations)
    {
        OnConfirmBuyButtonClick();
    }
    else
    {
        SetMenuState(ExpansionMarketMenuState.DIALOG);
        m_PurchaseDialog = new ExpansionMenuDialog_MarketConfirmPurchase(this, dialogData);
        m_PurchaseDialog.Show();
    }
}
// In OnConfirmBuyButtonClick:
SetMenuState(ExpansionMarketMenuState.REQUESTING_PURCHASE);
m_MarketModule.RequestPurchase(GetSelectedMarketItem().ItemID, m_Quantity, m_BuyPrice, ...);
```

Pattern applicable to any menu with async operations: set a blocking state BEFORE sending the
RPC. The client setting `MarketMenuSkipConfirmations` can bypass the modal dialog.

---

## P5 — Server-authoritative purchase: price recheck with ±1 tolerance

**Path:line**: `Scripts/4_World/DayZExpansion_Market/Systems/Market/ExpansionMarketModule.c:2862`
and `ExpansionMarketMenu.c:2623-2644`
Confidence: high (two independent reads).

```
if (!FindPurchasePriceAndReserveEx(item, player, count, reservedList, ..., result)
    || reservedList.Price != currentPrice
    || result == ExpansionMarketResult.FailedNotEnoughRepBuy)
{
    if (Math.AbsInt(reservedList.Price - currentPrice) == 1)
    {
        if (reservedList.Price < currentPrice)
            reservedList.Price = currentPrice;
    }
    else
        result = ExpansionMarketResult.FailedStockChange;
```

The price sent by the client is a proposal only. Server recalculates with
`FindPurchasePriceAndReserveEx` and compares. Only a difference of exactly ±1 (floating-point
rounding) is tolerated; any larger difference fails with `FailedStockChange`.

---

## P6 — Purchase confirmation flow: reserve → stock → money → spawn → Save

**Path:line**: `Scripts/4_World/DayZExpansion_Market/Systems/Market/ExpansionMarketModule.c:3007-3044`
and `:3089-3150`
Confidence: high (one read, verified).

```
if (!player.IsMarketItemReserved(itemClassName)) → FailedReserveTime
if (distance > MAX_TRADER_INTERACTION_DISTANCE) → FailedTooFarAway
...
zone.RemoveStock(currentReservedItem.ClassName, currentReservedItem.Amount, false);
int removed = RemoveMoney(player, reserve.Price);
SpawnMoney(player, parent, removed - reserve.Price, ...);  // change
ClearReserved(player);
zone.Save();  // durable state AFTER the real mutation
```

Confirmation re-validates reserve, trader zone, and distance before touching anything.
Durable state (`zone.Save()`) is written only after successful mutations (spawn + charge).
Invariant order: validate → mutate → persist.

---

## P7 — Temporary stock reserve: ReservedStock separate from real Stock

**Path:line**: `Scripts/3_Game/DayZExpansion_Market/Settings/ExpansionMarketTraderZone.c:424-455`
and `Scripts/4_World/DayZExpansion_Market/Systems/Market/ExpansionMarketReserveItem.c:56-82`
Confidence: high (one read, verified).

```
int GetStock(string className, bool actual = false) {
    int stock = Stock.Get(className);
    if (!actual) {
        int reservedStock;
        ReservedZone.ReservedStock.Find(className, reservedStock);
        stock = stock - reservedStock;  // client sees stock - reserves
    }
    return stock;
}
...
void AddReservedEx(zone, item, amt, pce) {
    zone.RemoveStock(item.ClassName, amt, true);  // deducts from real stock
    Reserved.Insert(new ExpansionMarketReserveItem(...));
}
void ClearReserved(zone) { zone.ClearReservedStock(...); Reserved.Clear(); }
```

Stock has two layers. `actual=true` returns real stock; `actual=false` (default) returns
stock minus active reserves. Buying first reserves; if cancelled or expired, `ClearReserved`
restores it. Prevents race conditions between simultaneous buyers.

---

## P8 — Trader as permissions entity: currencies + per-item buy/sell rights

**Path:line**: `Scripts/3_Game/DayZExpansion_Market/Settings/ExpansionMarketTrader.c:56-58` and `:449-459`
Confidence: high (one read, verified).

```
autoptr TStringArray Currencies;
int DisplayCurrencyValue;
string DisplayCurrencyName;
...
bool CanSellItem(string item) { return Items.Get(item) != ExpansionMarketTraderBuySell.CanOnlyBuy; }
bool CanBuyItem(string item)  { return Items.Get(item) != ExpansionMarketTraderBuySell.CanOnlySell; }
bool IsAttachmentBuySell(string item) { ... }
```

The trader is not just a positioned NPC. It defines accepted currencies, display currency,
categories/items, and granular per-item permissions (`CanOnlyBuy`, `CanOnlySell`,
`CanBuyAndSell`, attachment-only). The UI queries the trader before rendering action buttons
(`ExpansionMarketMenuItem.c:225-226`).

---

## P9 — RPC handshake: 4-step server/client sequence

**Path:line**: `Scripts/4_World/DayZExpansion_Market/Classes/UserActionsComponent/Actions/Interact/ExpansionActionOpenTraderMenu.c:104`
and `ExpansionMarketModule.c:3788-3864`
Confidence: high (two independent reads).

```
/**
 * Client/server handshake
 *
 * Server: StartTrading
 * Client: RPC_LoadTraderData       ← zone BuyPricePercent/SellPricePercent
 * Client: RequestTraderItems
 * Server: RPC_RequestTraderItems
 * Server: LoadTraderItems          ← item batches
 * Client: RPC_LoadTraderItems
 **/
ExpansionMarketModule.s_Instance.StartTrading(trader, player.GetIdentity());
```

Confirmed in module: `rpc = Expansion_CreateRPC("RPC_LoadTraderData")`, then client calls
`RequestTraderItems(trader, 0, stockOnly)`, final batch fires
`SI_SetTraderInvoker.Invoke(trader, true)` (lines 4083/4091/4099/4107).

`SI_SetTraderInvoker` (static ScriptInvoker, line 205) acts as a module→menu event bus when
loading completes.

---

## P10 — RPC registration: Expansion_Register*RPC helpers

**Path:line**: `Scripts/4_World/DayZExpansion_Market/Systems/Market/ExpansionMarketModule.c:290`
Confidence: high (two independent reads).

```
Expansion_EnableRPCManager();
Expansion_RegisterClientRPC("RPC_CustomTraderNetworkIDs");
Expansion_RegisterBothRPC("RPC_TraderObject");
Expansion_RegisterClientRPC("RPC_Callback");
Expansion_RegisterServerRPC("RPC_RequestPurchase");
Expansion_RegisterServerRPC("RPC_RequestSell");
Expansion_RegisterServerRPC("RPC_RequestTraderData");
Expansion_RegisterClientRPC("RPC_LoadTraderData");
```

Mutable intents (purchase, sell, trader data requests) are server RPCs; callbacks and
snapshots are client RPCs. This makes authority explicit. To send:
`Expansion_CreateRPC("name")` + `.Write()` + `.Expansion_Send(entity, true [, identity])`.

---

## P11 — Client-side attachment presets: UI state persisted locally

**Path:line**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenuItemManagerPreset.c:13-18`
and `:34-42`
Confidence: high (one read, verified).

```
class ExpansionMarketMenuItemManagerPreset
{
    string ClassName;
    string PresetName;
    ref array<string> ItemAttachments;
    void SaveItemPreset(string path) {
        JsonFileLoader<ExpansionMarketMenuItemManagerPreset>.JsonSaveFile(path + PresetName + ".json", this);
    }
    static ExpansionMarketMenuItemManagerPreset LoadItemPreset(string presetName, string path) { ... }
}
// Paths: EXPANSION_MARKET_WEAPON_PRESETS_FOLDER, EXPANSION_MARKET_CLOTHING_PRESETS_FOLDER
```

Not all state belongs to the server. Attachment preferences are saved locally under
`MarketPresets\Weapons\` and `MarketPresets\Clothing\`. Correct separation: economy to server,
UI preferences to client. Same `JsonFileLoader<T>` pattern but client-side.

---

## P12 — Persistence routes: JsonFileLoader per entity with constant paths

**Path:line**: `Scripts/3_Game/DayZExpansion_Market/Expansion_Market_Constants.c:14-21`
Confidence: high (two independent reads).

```
static const string EXPANSION_TRADER_ZONES_FOLDER = EXPANSION_MISSION_FOLDER + "traderzones\\";
static const string EXPANSION_ATM_FOLDER           = EXPANSION_FOLDER + "ATM\\";
static const string EXPANSION_MARKET_SETTINGS      = EXPANSION_MISSION_SETTINGS_FOLDER + "MarketSettings.json";
static const string EXPANSION_MARKET_PRESETS_FOLDER = EXPANSION_FOLDER + "MarketPresets\\";  // client

// TraderZone.Save():
JsonFileLoader<ExpansionMarketTraderZone>.JsonSaveFile(EXPANSION_TRADER_ZONES_FOLDER + m_FileName + ".json", this);
// ATM_Data.Save():
JsonFileLoader<ExpansionMarketATM_Data>.JsonSaveFile(EXPANSION_ATM_FOLDER + m_FileName + ".json", this);
```

Persistence separated by responsibility: global settings, categories, traders, zones/stock,
and ATM. Pattern `JsonFileLoader<T>.JsonSaveFile/JsonLoadFile` for per-entity persistence.
`zone.Save()` is called post-transaction (purchase line 3147, sell line 3725).

---

## Open assumptions (not verified)

- Batch pagination: `next < 0` appears to signal end of batches, but exact batch size
  and reconnect-on-timeout mechanism not verified. Confirm with `grep -n "BATCH_SIZE\|next < 0\|RequestTraderItems"` in module.
- `ExpansionMath.PowerConversion` with exponent 6.0 infers a convex curve (price drops
  fast as stock rises), but the `PowerConversion` implementation lives in Core, not Market.
  Not verified.
- Base implementation of `ExpansionScriptViewMenu`, `ExpansionViewController`, and
  binding runtime are in `DayZExpansion/Core/`, outside the Market code that was read.
  Verify before implementing exact binding compatibility.

---

## Settings files, item fields and related names (later snapshot)

A later snapshot of the DayZ Expansion scripts than the one above: commit `14fd692` (2026-10-15). Read from the
mod's source, not measured on a server.

- Settings live under `$profile:ExpansionMod\Settings\` (`EXPANSION_FOLDER`, `EXPANSION_SETTINGS_FOLDER`,
  `DayZExpansion/Core/Scripts/3_Game/DayZExpansion_Core/ExpansionConstants.c:75`, `:78`) or under
  `$mission:expansion\settings\` (`:85`). The file names have no `Expansion` prefix: `AISettings.json`,
  `TerritorySettings.json`, `VehicleSettings.json` in the profile folder (`ExpansionConstants.c:98`, `:106-107`),
  `QuestSettings.json` likewise (`DayZExpansion/Quests/Scripts/3_Game/DayZExpansion_Quests/DayZExpansion_Quest_Constants.c:45`),
  but `MarketSettings.json` in the **mission** settings folder. Traders are in
  `$profile:ExpansionMod\Traders\`, the market categories in `$profile:ExpansionMod\Market\`, the trader zones
  in `$mission:expansion\traderzones\`
  (`DayZExpansion/Market/Scripts/3_Game/DayZExpansion_Market/Expansion_Market_Constants.c:14-18`).
- Fields of a market item (`.../DayZExpansion_Market/Settings/ExpansionMarketItem.c:30-48`): `ClassName`,
  `MaxPriceThreshold` / `MinPriceThreshold` (int), `SellPricePercent` (float), `MaxStockThreshold` /
  `MinStockThreshold`, `QuantityPercent` (int), `SpawnAttachments[]`, `Variants[]`.
- `ExpansionQuestObjectiveType` starts at `NONE = 1`, then `TARGET`, `TRAVEL`, `COLLECT`, `DELIVERY`,
  `TREASUREHUNT`, `AIPATROL`, `AICAMP`, `AIESCORT`, `ACTION`, `CRAFTING`
  (`DayZExpansion/Quests/Scripts/4_World/DayZExpansion_Quests/Systems/Quests/ExpansionQuestObjectiveType.c:13-26`).
  Use the names: the numbers do not start at 0.
- AI settings include `MaxRecruitableAI`, `OverrideClientWeaponFiring` and `RecreateWeaponNetworkRepresentation`
  (`DayZExpansion/AI/Scripts/3_Game/DayZExpansion_AI/Settings/ExpansionAISettings.c:53`, `:67-68`).
- Detecting Expansion from a mod that does not depend on it: the Core patch is `CfgPatches DayZExpansion_Core`
  (`DayZExpansion/Core/Stub/config.cpp:3`), so `g_Game.ConfigIsExisting("CfgPatches DayZExpansion_Core")` works at
  run time; a module's scripts patch is `DayZExpansion_<Module>_Scripts` (`DayZExpansion/Market/Scripts/config.cpp:3`).
