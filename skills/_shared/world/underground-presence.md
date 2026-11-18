# The player's underground state (DayZ 1.30)

What "underground" means for a player, who decides it, how it reaches the server in 1.30, and which server check reads it. Checked on `P:\` (DayZ 1.30). The triggers that set it are in `underground-triggers.md`; how it shelters a player from a sandstorm is in `sandstorm.md`.

## The values

`EUndergroundPresence` has `NONE`, `OUTER`, `TRANSITIONING` and `FULL` (`P:\scripts\4_world\classes\undergroundhandlerclient.c:1` to `:7`). The client works it out from the trigger it is in (`SetUndergroundPresence`, `undergroundhandlerclient.c:464` to `:476`).

## Sent to the server since 1.30

- `SetUnderground` writes `INPUT_UDT_UNDERGROUND_SYNC` (`P:\scripts\4_world\entities\manbase\playerbase.c:2853` to `:2865`), and the server takes it in `OnInputUserDataProcess` with only a range check (`P:\scripts\4_world\entities\manbase\playerbase.c:6557` to `:6564`). In 1.29 the value existed only on the client (not on `P:\`).
- Consequence: the server now knows the presence. Before, a server side check that read it saw `NONE`.
- The client decides the value; the server does not work it out again. Do not use it alone for anything a cheating client should not control.

## Building restrictions underground

`CanPlaceItem` (`P:\scripts\4_world\entities\manbase\playerbase.c:2834` to `:2846`, called from `P:\scripts\4_world\classes\hologram.c:438`) refuses, inside a trigger, the types in `disallowedTypesInUnderground`:

- The defaults are `FenceKit`, `TerritoryFlagKit` and `WatchtowerKit` (`P:\scripts\3_game\cfggameplaydatajson.c:229` to `:232`).
- The setting is in `cfggameplay.json` under `BaseBuildingData` > `HologramData` (`GetDisallowedTypesInUnderground`, `P:\scripts\3_game\cfggameplayhandler.c:372` to `:374`).

The base building parts themselves are in `_shared/persistence/base-building.md`.
