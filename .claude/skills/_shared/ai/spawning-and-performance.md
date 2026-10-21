# Spawning and server performance

How AI creatures enter the world from script and from the Central Economy, what the server lead needs from you, and how to keep AI cheap on the server.

## Spawning from script

- `CreateObjectEx(string type, vector pos, int iFlags, int iRotation = RF_DEFAULT)` (`P:\scripts\3_game\global\game.c:703`). The flags are in `P:\scripts\3_game\ce\centraleconomy.c`.
- `ECE_INITAI` (2048, `centraleconomy.c:18`) starts the creature's AI. Without it the creature stands still until you call `InitAIAgent(group)` yourself (see `patrols-and-guards.md`).
- Vanilla's own AI spawn uses `ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_EQUIP_ATTACHMENTS` (`P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:454`) and first checks `g_Game.IsKindOf(object_name, "DZ_LightAI")` (`:451`).
- `ECE_PLACE_ON_SURFACE` (`:38`) is `ECE_CREATEPHYSICS|ECE_UPDATEPATHGRAPH|ECE_TRACE`. `ECE_EQUIP_ATTACHMENTS` (`:21`) equips configured attachments. `ECE_NOLIFETIME` (`:30`) skips the lifetime the economy would set.
- The older `CreateObject(string type, vector pos, bool create_local = false, bool init_ai = false, ...)` (`game.c:691`) takes `init_ai` as its fourth parameter.
- Spawn on the server only. Keep a list of what you spawned so you can delete it and so the count stays bounded.

## Spawning from the Central Economy

These files ship with DayZ Server in `mpmissions\dayzOffline.chernarusplus\` (copied into `.server/<instance>/mission/` by `/dayz-add-server`). They are not on `P:\`. The server lead and `dayz-server-admin` own them; you hand over the entries.

- Infected events: `db\events.xml`, for example `InfectedArmy` (`:222`) with `nominal`, `min`, `max`, `lifetime`, `position` set to `player`, and `children` listing the classes and their weights (`ZmbM_SoldierNormal` and others at `:236` to `:241`).
- Infected zones: `env\zombie_territories.xml`. Each `zone` has the event name, counts, a position (`x`, `z`) and a radius `r`, for example `InfectedArmy` at `:258`.
- Event positions: `cfgeventspawns.xml` lists each event, for example `InfectedArmy` at `:1587`.
- Animals: `db\events.xml` events such as `AnimalWolf` (`:204`) with `Animal_CanisLupus_Grey` (`:218`), and herd territories in `cfgenvironment.xml`, for example `Wolf` with behaviour `DZWolfGroupBeh` (`:36`).
- Every spawnable creature also needs a `db\types.xml` entry, for example `ZmbM_SoldierNormal` (`:28615`) with `nominal` 0 and `lifetime` 1800.
- Server wide caps in `db\globals.xml`: `AnimalMaxCount` 200 (`:3`) and `ZombieMaxCount` 1000 (`:31`).

What you hand the server lead for a new creature: the class name, which event or territory it joins (or a new one), the weight or count you expect, the zone positions, and a `types.xml` entry. For a scripted spawner, say where it spawns, how many at most, and when it despawns.

## Server performance

- The command handler runs every simulation step for every creature it simulates (see `creatures.md`). Code in `ModCommandHandlerBefore`, `Inside` and `After` must not allocate, read config, search the world or print. Vanilla keeps its target arrays as members for this reason (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:29`, `:30`).
- Do slow work on a timer, not per step: path planning with `FindPath`, target scans, and spawn checks. Read `_shared/enscript/patterns/scheduler.md` before using `CallLater` or `Timer` for long running loops.
- Plan a route once per leg and store the waypoints. Never call `FindPath` inside the command handler.
- Sync as little as possible. Vanilla infected sync four values: mind state, orientation, movement speed and crawling (`zombiebase.c:54` to `:57`), and orientation only after it changes by 30 degrees (`ORIENTATION_SYNC_THRESHOLD`, `:5`). Every extra sync variable is sent for every creature.
- Give every scripted spawner its own cap. Do not assume the economy caps in `globals.xml` also limit what your script creates.
- `AIAgent.SetKeepInIdle(true)` stops the AI simulating; vanilla uses it while a stealth kill plays (`zombiebase.c:1067`, `:1068`) and turns it back off in `OnRecoverFromDeath` (`:1099`). Pausing distant guards this way is an idea to test, not a vanilla pattern.
- In the in game test, compare the server with and without your AI loaded, with the same number of creatures, and report the difference with the behaviour result.
