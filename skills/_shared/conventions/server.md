# DayZ server, economy and test-server notes (Tier 2 topic)

Part of Tier 2. Server economy files, the `.server/<instance>/` test-server layout, and mission / DayZ Server install notes. Read it together with the core rules in `skills/_shared/dayz-conventions.md`, which still apply.

## Server / economy

- `types.xml`: Central Economy spawn rates, lifetimes, locations.
- `cfgeconomycore.xml`, `cfgspawnabletypes.xml`, `events.xml`: economy structure.
- `cfggameplay.json`: runtime tuning.
- `mission/init.c`: server-side world init logic.
- Loot numbers (`nominal`, `min`, `lifetime`, `restock`, `cost`) live only in the mission's `types.xml`. No config.cpp class sets them: there is no `CfgSpawnablesTypes` or `CfgRandomPresence` in any `config.cpp` under `P:\DZ` or in `P:\scripts`, so a mod that adds one changes nothing. The script side only reads them back (`CEItemProfile` getters, `P:\scripts\3_game\ce\centraleconomy.c:754-765`).
- `<lifetime>` is how long an item lies untouched on the ground before cleanup deletes it; `<restock>` is the wait before a missing item may respawn when the economy needs it (`centraleconomy.c:762` and `:763`).
- Fixed props without `init.c` code: list spawner JSON files in `cfggameplay.json` under `WorldsData.objectSpawnersArr` (`P:\scripts\3_game\cfggameplaydatajson.c:17` and `:195`). Each file's top-level key is `Objects`, an array of `{ name, pos, ypr, scale, enableCEPersistency, customString }` (`P:\scripts\3_game\objectspawner.c:95-108`). The paths are relative to the mission folder (`objectspawner.c:18` prefixes `$mission:`), and `cfggameplay.json` is only read when the server config sets `enableCfgGameplayFile = 1;` (`P:\scripts\3_game\cfggameplayhandler.c:53`).
- `$mission:` is the path prefix for a file in the running mission folder (`P:\scripts\3_game\cfgbunkerbroadcasthandler.c:23`).
- To keep an object made with `CreateObjectEx` out of the world save, add `ECE_NOPERSISTENCY_WORLD` (`P:\scripts\3_game\ce\centraleconomy.c:31`).

## Test server instances (`.server/`)

- Server runtime lives at `.server/<instance>/` at the project root (not under `workspace/`). Each instance is self-contained:
  - `.server/<instance>/mission/`: editable copy of the mission folder, created by `/dayz-add-server` from DayZ Server's `mpmissions/<template>/` and edited by the user after that (the server runs with `-filePatching`, so edits are live). Never edit the original DayZ Server install. The folder is named `mission/` whatever the template; the launcher passes `-mission=<abspath>`.
  - `.server/<instance>/serverDZ.cfg`: per-instance server config. Its `template = "..."` line links the instance to its mission base, so instances can differ in player count, persistence or time of day.
  - `.server/<instance>/Profiles/`: server `-profiles=` dir (RPT, script.log, BattlEye state).
  - `.server/!ClientDiagLogs/`: client `-profiles=` dir, shared by all instances.
- The instance, not the map, is the unit of identity: two instances can run variants of the same map (chernarus and chernarus-hardcore).
- Setup and run are separate skills. `/dayz-add-server <instance>` copies the mission, writes the cfg and creates the profile dirs. `/dayz-launch-test <mod> --server <instance>` verifies and launches; it never copies missions or writes cfgs from scratch, and refuses with a hint to run `/dayz-add-server` when state is missing. It never edits the cfg: a cfg without an active `allowFilePatching = 1;` is refused with the `/dayz-add-server <instance>` hint.
- The legacy `workspace/_server/` layout is not supported. `/dayz-add-server`, `/dayz-launch-test` and `/dayz-clean-workspace --include-server` refuse to run while it exists; the user deletes it manually.
- `.server/` is gitignored as a whole; `/dayz-add-server` recreates it on each machine. A clone that wants its `serverDZ.cfg` or `mission/` edits versioned adds `!` exceptions to its own `.gitignore`.

## Mission and DayZ Server install notes

- The launch skill passes `-mission=<absolute path to .server/<instance>/mission>` to pin the mission folder (otherwise the engine looks in the diag binary's local `mpmissions/`, which does not exist in the game install).
- DayZ Server (Steam appid 223350) is only needed for the initial mission copy. After that it can be uninstalled; the `.server/<instance>/mission/` copy is the source of truth.
