# Wearables pack

Reference for clothing, gear and survivor characters: which vanilla class to inherit, slots and cargo, protection and insulation, color variants, and the models and proxies behind them. It is written for `dayz-wearables-specialist`, and any DayZ worker may open one file of it when a task needs it.

Every fact cites the vanilla file on `P:\` it came from. Line numbers are from the copy on `P:\` when the pack was written; if a line has moved, Grep the class or key name in the same file. A note marked **engine** describes behavior that no vanilla file shows, so treat it as a rule of thumb and confirm it in game.

## Which file to open

| Question | File |
|---|---|
| Which vanilla class do I inherit, and which addon goes in `requiredAddons[]`? | `references/classes-and-parents.md` |
| Which slot does it use, how much does it hold, what can attach to it, what blocks it? | `references/slots-and-cargo.md` |
| How warm is it, how wet does it get, how much does it protect, how is it repaired? | `references/protection-and-insulation.md` |
| How do I make one model carry several colors? | `references/color-variants.md` |
| Which models does a wearable need, how do proxies work, what goes to Object Builder? | `references/models-and-proxies.md` |
| How do I add a new survivor character? | `references/characters.md` |

Related packs: `_shared/container-base.md` for an item with cargo that is not clothing (a vest pouch is one), and `_shared/enscript/references/item_api.md` for `ItemBase` script calls.
