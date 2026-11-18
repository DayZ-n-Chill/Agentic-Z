# The player's underground state

What "underground" means for a player, who decides it, how the server learns it, and which server check reads it. The triggers that set it are in `underground-triggers.md`; how it shelters a player from a sandstorm is in `sandstorm.md`.

## The four values

`EUndergroundPresence` has `NONE`, `OUTER`, `TRANSITIONING` and `FULL` (`P:\scripts\4_world\classes\undergroundhandlerclient.c:1` to `:7`). The client works the value out from the trigger it stands in (`SetUndergroundPresence`, `undergroundhandlerclient.c:464` to `:476`).

## What each value changes on the client

`UndergroundHandlerClient.OnUndergroundPresenceUpdate(newPresence, oldPresence)` reacts to every change (`P:\scripts\4_world\classes\undergroundhandlerclient.c:541` onward):

| Change | Effect |
|---|---|
| from `NONE` to any other value | underground lights on, ambient sound starts |
| above `OUTER` for the first time | lightning suppressed with `SuppressLightningSimulation(true)`, ambient sound |
| to `FULL` | the light blend runs in at `LIGHT_BLEND_SPEED_IN` 5 (`undergroundhandlerclient.c:11`) |
| out of `FULL` | the light blend runs out at `LIGHT_BLEND_SPEED_OUT` 1.75 (`:12`) |
| back to `OUTER` or `NONE` from deeper | lightning allowed again |
| to `NONE` | ambient sound stops |

The method is `protected`, so a `modded class UndergroundHandlerClient` that wants its own client effect underground overrides it and calls `super` first. Other readers: ground and cloud dust stop for any value but `NONE` (`P:\scripts\4_world\classes\dust\dusteffectsmanager.c:164` to `:169`), and the sandstorm counts `TRANSITIONING` and `FULL` as shelter (`sandstorm.md`).

## How the server learns it

- `SetUnderground` writes `INPUT_UDT_UNDERGROUND_SYNC` (`P:\scripts\4_world\entities\manbase\playerbase.c:2853` to `:2865`), and the server takes it in `OnInputUserDataProcess` with only a range check (`playerbase.c:6557` to `:6564`).
- `SetUnderground` sends only in multiplayer and only when the value changes (`playerbase.c:2855` to `:2865`). `GetUndergroundPresence()` reads the stored value on either side (`playerbase.c:2848` to `:2851`).
- In 1.29 the value existed only on the client, and a server side check that read it always saw `NONE` (not checked on `P:\`). From 1.30 the server has it.
- The client decides the value and the server does not work it out again: the trigger box exists only on the client (`underground-triggers.md`). The server's storm agent dose reads it too (`sandstorm.md`). Never rely on it alone for anything a cheating client should not control.

## Building is restricted underground

`CanPlaceItem` (`playerbase.c:2834` to `:2846`, called from `P:\scripts\4_world\classes\hologram.c:438`) refuses, at any presence above `NONE`, the types listed in `disallowedTypesInUnderground`, matched with `IsKindOf` so child classes are refused too:

- The defaults are `FenceKit`, `TerritoryFlagKit` and `WatchtowerKit` (`P:\scripts\3_game\cfggameplaydatajson.c:229` to `:232`).
- Servers change the list in `cfggameplay.json` under `BaseBuildingData` > `HologramData` (`GetDisallowedTypesInUnderground`, `P:\scripts\3_game\cfggameplayhandler.c:372` to `:375`). The Nasdara mission lists the same three under `disallowedTypesInUnderground` (`P:\DZ\worlds\nasdara\ce\cfggameplay.json:76` to `:80`).

The base building parts themselves are in `_shared/persistence/base-building.md`.
