---
name: dayz-persistence
description: "Reference for designing, writing, debugging and auditing DayZ persistence: OnStoreSave and OnStoreLoad entity streams, Community Framework ModStorage and storageVersion, saved format changes and rollback, sidecar JSON files and recoverable file replacement, player data that corrupts after a save or restart, and placed objects that vanish after a restart (central economy lifetime, types.xml entries). Use for deprecated JSON loading calls, future or truncated versions, mod data that must survive uninstall, the 1.30 changes (CombinationLock stream version 143, code lock, ThermalBiasHandler, GAME_STORAGE_VERSION, BunkerBroadcastPersistenceStorage.bin) and the central economy file formats. Spanish triggers: persistencia, los objetos desaparecen tras reiniciar, se corrompen los datos del jugador."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-persistence

Reference only: this skill has no script. It is the deep material behind the persistence pack (`skills/_shared/persistence/`), written for `dayz-persistence-specialist`; any worker that designs saved data may open the one file it needs.

Follow `skills/_shared/dayz-conventions.md`. Line numbers are from the vanilla scripts on `P:\` (game storage version 144, `GAME_STORAGE_VERSION` at `P:\scripts\3_game\global\game.c:5`). Three kinds of evidence appear in the references and are labelled where they occur: vanilla code read on `P:\`; measurements made in game with test mods, which cannot be checked on `P:\`; and Community Framework source, which is third-party and not unpacked on `P:\`.

## Which file answers which question

Deep material lives in `<skill-dir>\references\`. Open only the file the task needs.

| Question | File |
|---|---|
| My mod saves fields on its own entity. What order, what version, what fails? | `references/vanilla-stream.md` |
| The data sits on an entity I do not own, or must survive my mod being removed and added back. | `references/cf-modstorage.md` |
| The data belongs to no entity, or an admin must read and repair it. How do I replace a file safely? | `references/sidecar-files.md` |
| I am changing a saved format. Which inputs must the reader classify, and how do I test it? | `references/migration-matrix.md` |
| What did 1.30 change in the vanilla streams, and what breaks in a 1.29 mod? | `references/dayz-1-30-persistence.md` |
| Placed objects vanish after a restart though the save code is right. What does a storage copy need to load? | `references/lifetime-and-storage.md` |
| What happens when `OnStoreLoad` returns false? In which order do my structures and stored entities come back? How do I keep a registry of my entities? | `references/load-and-restore.md` |
| What do `types.xml`, `cfgspawnabletypes.xml`, `events.xml`, `globals.xml`, `economy.xml` and `cfglimitsdefinition.xml` look like on 1.30? | `references/central-economy-files.md` |

The short rules every script worker needs are in the pack: `skills/_shared/persistence/save-load-contract.md` and `skills/_shared/persistence/versioning-and-migration.md`.

## Router: choose one contract first

Answer four questions before choosing a mechanism: is the data attached to an entity, does the mod own that entity, must the data survive uninstall, and must an admin inspect it outside the game. Each matching rule below adds a candidate. Exactly one candidate is needed; with none or several, ask for clarification instead of quietly preferring one.

| What you can observe | Candidate |
|---|---|
| The data is not attached to an entity, or an administrator must inspect or repair it outside the game | Sidecar file |
| The mod does not own the entity, or the data must survive uninstall and reinstall | CF ModStorage |
| The data is attached to an entity the mod owns, need not survive uninstall, and need not be inspected outside the game | Vanilla entity stream |

This is a routing decision, not a ranking. Data outside an entity that must also survive uninstall matches two rules, so it needs a decision about ownership and the recovery surface first.

## Contract 1: vanilla entity stream

Use the stream for data owned by the entity's own mod when it need not survive uninstall. The hooks are `OnStoreSave` and `OnStoreLoad` on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:2910` and `:2978`). Save and load the same fields in the same order and type, call `super`, and return `false` on any failed `ctx.Read`; partial state is never valid.

The hook's `version` is the game's storage version from `SaveVersion()`, not the mod's own format version (`game.c:435`). The base class data has no fixed width: the energy component writes eight values or none (`entityai.c:2917-2948`), and since 1.30 construction data comes before it, so never skip a fixed number of values after `super`. If the mod is removed, nothing reads or writes its values any more.

Full contract: `references/vanilla-stream.md`.

## Contract 2: CF ModStorage

Use Community Framework ModStorage for data on another mod's entity, or data that must survive uninstall and reinstall. CF writes a framework version, a mod count and one framed stream per mod, hands each mod the `storageVersion` from its `CfgMods` entry, and writes an unloaded mod's block back byte for byte. It does not define the mod's migrations, check the mod's staged state, give admins an editable file or make file replacement atomic. Third-party: the CF line references are in `references/cf-modstorage.md` and are not checked on `P:\`.

## Contract 3: sidecar files

Use a file of your own when the data belongs to no entity or must be inspected and repaired outside the game. The file carries its own version header. Load JSON with `JsonFileLoader<T>.LoadFile(filename, out data, out errorMessage)` and check its `bool` return (`P:\scripts\3_game\tools\jsonfileloader.c:7`); `JsonLoadFile` is deprecated and returns nothing (`jsonfileloader.c:105`).

Script has `DeleteFile` and `CopyFile` but no rename or move (`P:\scripts\1_core\proto\ensystem.c:528` and `:531`). So "write a temp file, verify, replace" is not atomic: the replace deletes the destination and then copies the temp file, and between the two the destination does not exist. Back up before that window, verify after the copy, and keep the finished temp file until the copy is verified.

Full flow and the nine I/O boundaries to test: `references/sidecar-files.md`.

## Migration gate

Any change to a saved format classifies seven inputs: fresh, legacy, known version, future version, truncated, same game build with a new mod version, and an old reader meeting new data. Each result states the verdict, the bytes consumed, the state preserved and the action. Rejecting a record never writes. Run a mutation check: a perfect result against a fixture that was never changed proves nothing.

Compatibility is more than the stream. An entity also has to still exist: compare class name, parent, `scope` and its entry in `CfgPatches` `units[]` against the last release. The table and the checklist are in `references/migration-matrix.md`.

## Hard stops

Stop and fix the problem before recommending or shipping persistence work when:

1. An API, method, hook, field or signature is written without a checked `path:line`.
2. A format change leaves out what happens to old saves, or what the old reader does with new data. When a design with no format change gives the same result, present it first.
3. A migration saves rewritten data on its own with no backup and no verification.
4. A future version is accepted silently instead of being rejected without writing, with a rate limited message.
5. A failed `ctx.Read` leaves partly applied state that is treated as valid.
6. A test covers only the happy path; future, truncated, rollback and injected I/O failures are not exercised.
7. Live cargo is walked by a frozen index across ticks while items can be removed during the walk (`references/load-and-restore.md`).
8. An entry of the mod's own registry of world entities is removed by proximity, bound on restore to an entity that does not carry its id, or given a new entity while one it already had may still live; no rule for that restore has come out of review sound (`references/load-and-restore.md`).

## What the measurements showed

Short forms of the findings in the references; the evidence and its limits are in the files named.

- A class with no `types.xml` entry gets a lifetime of about 30 to 60 minutes of server time, and the next restart deletes it. Ship every placed class in the mod's own `types.xml` with an explicit lifetime (`references/lifetime-and-storage.md`).
- A copy of a storage folder without the economy's own files (`types.bin`, `events.bin` and the rest) loads nothing, and counting class names in the `.bin` files finds nothing even in a world that holds them (`references/lifetime-and-storage.md`).
- When `OnStoreLoad` returns false the engine keeps the entity with default script state; it does not delete it (`references/load-and-restore.md`).
- Stored entities are created after `OnMissionStart` returns, so a structure they rest on is rebuilt inside `OnMissionStart`, not in a later call (`references/load-and-restore.md`).

## DayZ 1.30 in short

- `GAME_STORAGE_VERSION` is 144 (`game.c:5`); it was 142 on 1.29 (the 1.29 value is not yet checked on P:\, which holds only the 1.30 scripts).
- `EntityAI.OnStoreSave` lets the construction component write first (`entityai.c:2912-2914`), and the load reads that block only from version 143 (`entityai.c:2981`). It is empty for `BaseBuildingBase`; `Rebuilding` on map buildings writes its own version and ten ints.
- `PlayerBase` saves a thermal value through `m_ThermalBiasHandler` after the arrow manager (`P:\scripts\4_world\entities\manbase\playerbase.c:7395`) and reads it with no version check (`playerbase.c:7520-7524`), so a 1.29 player record fails to load on a 1.30 multiplayer server.
- `CombinationLock` writes a third value, `m_CombinationInside`, read only from version 143 (`P:\scripts\4_world\entities\itembase\combinationlock.c:169-177`).
- `DigitalCodeLock` is new and saves through the `OnStoreSave` of its `CodeLockComponent` (`P:\scripts\4_world\classes\codelockcomponent.c:257`).
- `$mission:BunkerBroadcastPersistenceStorage.bin` is a new mission file written with `FileSerializer`, with no header and no check of its reads (`P:\scripts\4_world\classes\bunkerbroadcasthandler.c:16-18`). Do not copy it as a pattern.

What breaks in a 1.29 mod and the migration checklist: `references/dayz-1-30-persistence.md`.

## Who does what

| Concern | Owner |
|---|---|
| Save and load code, version headers, upgrade paths | `dayz-persistence-specialist` |
| The audit before release | `dayz-persistence-specialist` with the `rigorous-data-audit` skill and `skills/_shared/persistence/data-audit.md` |
| Base building parts and their bit masks | the `dayz-basebuilding` skill |
| `types.xml` entries and other economy files on the test server | `dayz-server-admin`, `/dayz-edit-types` |
| Build and test in game | `/dayz-build-pbo`, `/dayz-launch-test`, `/dayz-gate` |
