# Expansion Market menu

How the DayZ Expansion Market menu works end to end, as a model for any UI that trades with the server: the MVC menu, its state machine, confirming before the RPC, the server's price recheck, reserved stock and the RPC handshake. Read `expansion-mvc-patterns.md` first for the base view classes; where the Market saves its files is in `expansion-settings-and-persistence.md`.

DayZ Expansion is a third party mod. Every path here is inside the DayZ Expansion scripts (the `release` branch of its source), not vanilla, and none of it is on `P:\`. Line numbers move between releases, so search for the symbol in your copy. The vanilla menu stack it rests on is `UIScriptedMenu` (`P:\scripts\3_game\tools\uiscriptedmenu.c:66`).

## The flow

The UI sends intents and the server decides. The menu never assumes a price or stock count is right; it waits for the server before it changes what it shows.

1. The server module's `StartTrading()` sends `RPC_LoadTraderData`. The client opens `CreateSVMenu("ExpansionMarketMenu")`.
2. The server sends items in batches (`RPC_LoadTraderItems`); the client inserts them into `ObservableCollection`s and the bindings update the widgets. The last batch fires `SI_SetTraderInvoker.Invoke()`.
3. The player clicks Buy. `OnBuyButtonClick()` sets the menu state to `DIALOG`, or straight to `REQUESTING_PURCHASE` when confirmations are off, and calls `m_MarketModule.RequestPurchase(itemID, qty, price_seen, ...)`.
4. The server RPC `RPC_RequestPurchase` recalculates the price with `FindPurchasePriceAndReserveEx()` and reserves the stock with `zone.RemoveStock(..., true)`.
5. The client RPC `RPC_Callback(PurchaseSuccess)` sets the state back to `NONE` and confirms the purchase.
6. The confirming `RPC_RequestPurchase` removes the stock for real, takes the money, spawns the item and calls `zone.Save()`. A final callback refreshes the UI.

## Menu, controller and layout

`class ExpansionMarketMenu: ExpansionScriptViewMenu` is at `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenu.c:19` and its controller at `:3620`:

```c
class ExpansionMarketMenuController: ExpansionViewController
{
    ref ObservableCollection<ref ExpansionMarketMenuCategory> MarketCategories = new ObservableCollection<ref ExpansionMarketMenuCategory>(this);
    ref ObservableCollection<ref ExpansionMarketMenuDropdownElement> DropdownElements;
    string MarketName;
    string PlayerTotalMoney;
    override void PropertyChanged(string property_name);
}
```

The controller is a state hub: when `ShowSellables` changes it updates the client settings, filters, categories, preview and skins in turn (`:3648`, `:3655` to `:3664`). The module opens the menu with `CreateSVMenu("ExpansionMarketMenu")` after `MoneyCheck()` (`ExpansionMarketModule.c:4587`), never straight from an RPC.

The layout is the binding contract (`GUI/layouts/market/expansion_market_menu.layout:12` for the root, `:77` for a text binding):

```c
FrameWidgetClass ExpansionMarketMenu {
 scriptclass "ExpansionMarketMenuController"
 ...
      TextWidgetClass market_text {
       scriptclass "ViewBinding"
       Binding_Name "MarketName"
       Two_Way_Binding 1
```

The root names the controller; each child declares a `ViewBinding` with a `Binding_Name`. Check boxes use `Two_Way_Binding 1`. `MarketCategories`, `DropdownElements` and `SkinsDropdownElements` render from collections.

## The state machine

`ExpansionMarketMenuState` (`Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenuState.c:15`):

| State | Value |
|---|---|
| `INVALID` | -1 |
| `NONE` | 0 |
| `LOADING` | 1 |
| `DIALOG` | 2 |
| `REQUESTING_SELECTED_ITEM` | 3 |
| `REQUESTING_PURCHASE` | 4 |
| `REQUESTING_SELL` | 5 |
| `COUNT` | 6 |

The state blocks input while an RPC is in flight. The menu moves from `LOADING` to `NONE`, then to `DIALOG`, then to `REQUESTING_PURCHASE` or `REQUESTING_SELL`. Setting the blocking state before the RPC is what stops a double click buying twice; copy that into any menu that waits on the server.

## Confirming before the RPC

`OnBuyButtonClick` (`ExpansionMarketMenu.c:2591`) and its confirm path (`:2637`):

```c
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

// in OnConfirmBuyButtonClick
SetMenuState(ExpansionMarketMenuState.REQUESTING_PURCHASE);
m_MarketModule.RequestPurchase(GetSelectedMarketItem().ItemID, m_Quantity, m_BuyPrice, ...);
```

The client setting `MarketMenuSkipConfirmations` skips the dialog.

## The server rechecks the price

The price the client sends is only a proposal (`Scripts/4_World/DayZExpansion_Market/Systems/Market/ExpansionMarketModule.c:2862`):

```c
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

A difference of exactly 1, from rounding, is accepted; anything more fails with `FailedStockChange`.

The confirmation (`ExpansionMarketModule.c:3007` to `:3044` and `:3089` to `:3150`) checks again before touching anything: the item must still be reserved (`FailedReserveTime` otherwise) and the player within `MAX_TRADER_INTERACTION_DISTANCE` (`FailedTooFarAway`). Then it removes the stock, takes the money with `RemoveMoney`, pays back change with `SpawnMoney`, clears the reservation and calls `zone.Save()`. The order is check, change, then save; the file is written only after the item and the charge have succeeded.

## Reserved stock

Stock has two layers (`Scripts/3_Game/DayZExpansion_Market/Settings/ExpansionMarketTraderZone.c:424` to `:455`):

```c
int GetStock(string className, bool actual = false)
{
    int stock = Stock.Get(className);
    if (!actual)
    {
        int reservedStock;
        ReservedZone.ReservedStock.Find(className, reservedStock);
        stock = stock - reservedStock; // what the client sees
    }
    return stock;
}
```

`actual = true` gives the real stock; the default gives stock minus active reservations. A purchase reserves first with `AddReservedEx`, which calls `zone.RemoveStock(item.ClassName, amt, true)`; a cancel or timeout runs `ClearReserved`, which gives it back (`Scripts/4_World/DayZExpansion_Market/Systems/Market/ExpansionMarketReserveItem.c:56` to `:82`). Two players buying the last item at once can't both get it.

## The trader decides what can be traded

A trader is more than a placed NPC (`Scripts/3_Game/DayZExpansion_Market/Settings/ExpansionMarketTrader.c:56` to `:58` and `:449` to `:459`). It holds the accepted `Currencies`, the `DisplayCurrencyValue` and `DisplayCurrencyName`, its categories and items, and a right per item: `CanOnlyBuy`, `CanOnlySell`, `CanBuyAndSell` or attachment only.

```c
bool CanSellItem(string item) { return Items.Get(item) != ExpansionMarketTraderBuySell.CanOnlyBuy; }
bool CanBuyItem(string item) { return Items.Get(item) != ExpansionMarketTraderBuySell.CanOnlySell; }
```

The menu asks the trader before it draws the buy and sell buttons (`ExpansionMarketMenuItem.c:225` and `:226`).

## The RPC handshake

The action that opens the trader calls `ExpansionMarketModule.s_Instance.StartTrading(trader, player.GetIdentity())` (`Scripts/4_World/DayZExpansion_Market/Classes/UserActionsComponent/Actions/Interact/ExpansionActionOpenTraderMenu.c:104`). The module's own comment lists the sequence (`ExpansionMarketModule.c:3788` to `:3864`):

| Step | Side | Call |
|---|---|---|
| 1 | Server | `StartTrading` |
| 2 | Client | `RPC_LoadTraderData` (the zone's buy and sell percentages) |
| 3 | Client | `RequestTraderItems(trader, 0, stockOnly)` |
| 4 | Server | `RPC_RequestTraderItems`, then `LoadTraderItems` in batches |
| 5 | Client | `RPC_LoadTraderItems`; the last batch fires `SI_SetTraderInvoker.Invoke(trader, true)` (`:4083` to `:4107`) |

`SI_SetTraderInvoker` is a static `ScriptInvoker` (`:205`) that tells the menu loading is done.

RPCs are registered once (`ExpansionMarketModule.c:290`):

```c
Expansion_EnableRPCManager();
Expansion_RegisterClientRPC("RPC_CustomTraderNetworkIDs");
Expansion_RegisterBothRPC("RPC_TraderObject");
Expansion_RegisterClientRPC("RPC_Callback");
Expansion_RegisterServerRPC("RPC_RequestPurchase");
Expansion_RegisterServerRPC("RPC_RequestSell");
Expansion_RegisterServerRPC("RPC_RequestTraderData");
Expansion_RegisterClientRPC("RPC_LoadTraderData");
```

Requests that change things (buy, sell, trader data) are server RPCs; callbacks and snapshots are client RPCs, so authority is plain from the registration. To send: `Expansion_CreateRPC("name")`, then `.Write()`, then `.Expansion_Send(entity, true [, identity])`.

## Not checked

- `next < 0` appears to end the item batches; the batch size and what happens on a timeout are not checked. Search the module for `BATCH_SIZE`, `next < 0` and `RequestTraderItems`.
- `ExpansionMath.PowerConversion` with exponent 6.0 suggests a convex curve, where the price drops fast as stock rises, but the function lives in Expansion's Core module and was not read.
- `ExpansionScriptViewMenu`, `ExpansionViewController` and the binding runtime live in `DayZExpansion/Core/`, outside the Market code; check them before you depend on exact binding behaviour.
