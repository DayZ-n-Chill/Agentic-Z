# The player's underground state

What "underground" means for a player, who decides it, how the server learns it, and which server check reads it. The triggers that set it are in `underground-triggers.md`; how it shelters a player from a sandstorm is in `sandstorm.md`.

## The four values

`EUndergroundPresence` has `NONE`, `OUTER`, `TRANSITIONING` and `FULL` (`P:\scripts\4_world\classes\undergroundhandlerclient.c:1` to `:7`). The client works the value out from the trigger it stands in (`SetUndergroundPresence`, `undergroundhandlerclient.c:464` to `:476`).

## How the server learns it

- `SetUnderground` writes `INPUT_UDT_UNDERGROUND_SYNC` (`P:\scripts\4_world\entities\manbase\playerbase.c:2853` to `:2865`), and the server takes it in `OnInputUserDataProcess` with only a range check (`playerbase.c:6557` to `:6564`).
- In 1.29 the value existed only on the client, and a server side check that read it always saw `NONE` (not on `P:\`). From 1.30 the server has it.
- The client decides the value and the server does not work it out again. Never rely on it alone for anything a cheating client should not control.

## Building is restricted underground

`CanPlaceItem` (`playerbase.c:2834` to `:2846`, called from `P:\scripts\4_world\classes\hologram.c:438`) refuses, inside a trigger, the types listed in `disallowedTypesInUnderground`:

- The defaults are `FenceKit`, `TerritoryFlagKit` and `WatchtowerKit` (`P:\scripts\3_game\cfggameplaydatajson.c:229` to `:232`).
- Servers change the list in `cfggameplay.json` under `BaseBuildingData` > `HologramData` (`GetDisallowedTypesInUnderground`, `P:\scripts\3_game\cfggameplayhandler.c:372` to `:374`).

The base building parts themselves are in `_shared/persistence/base-building.md`.
