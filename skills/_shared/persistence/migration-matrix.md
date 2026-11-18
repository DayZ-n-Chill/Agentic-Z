# Migration matrix

Which seven kinds of input a reader must classify when a saved format changes, what each must return, how to prove the tests can fail, and how vanilla handled its own new fields on 1.30. Open it before changing any saved format and when writing its tests. The basic rules for adding and removing a field are in `versioning-and-migration.md`, "Changing what you save".

## The seven cells

Every reader result states four things: the verdict, the bytes it accepted, the state it kept, and the action it takes.

| Input | Verdict | Bytes accepted | State kept | Action |
|---|---|---:|---|---|
| Fresh: no record | ok | 0 | defaults | write the current header at the next save |
| Legacy with no version header | ok, legacy | all bytes of the old layout | fully migrated | read the old layout; rewrite only after a backup |
| Known version | ok | the bytes the header declares | complete | none |
| Future version, saved by a newer mod | reject | 0 | unchanged | write nothing; log once per rate limit window |
| Truncated or damaged | reject | 0 applied | unchanged | discard the partial read; keep the source as evidence |
| Same game build, new mod version | ok, migrate | the bytes the old header declares | migrated | migrate by the mod's version, never the game's |
| Old reader meets new data (rollback) | reject forward | 0 | unchanged | the old reader rejects; delete nothing |

"Bytes accepted" counts what reached the result, not how far a low level cursor moved before it found a problem. A reader that read a valid prefix of a cut record still accepted 0.

## What each cell means

* **Fresh.** No record exists. Do not call broken or empty bytes fresh.
* **Legacy.** Recognise the old layout on purpose, read all of it into locals, check it, then migrate. A parse failure is not a legacy success.
* **Known version.** Read exactly the fields and lengths that version declares. Missing, extra or wrongly typed bytes are not a success.
* **Future version.** Reject before applying anything, keep the bytes, write nothing over them, and log one reasoned line per rate limit window. A future record is an incompatible version, not proof of damage.
* **Truncated.** Reject the whole record, drop every staged value, keep the state from before the load, and keep the source.
* **Same game build, new mod version.** The game build can stay the same while the mod's data changes. Pick the migration by the mod's own version (or Community Framework's `storageVersion`, `cf-modstorage.md`).
* **Rollback.** Say what the old reader does with the new writer's data. It applies nothing, keeps the new record, and deletes or rewrites nothing. A format change without this is incomplete.

## The write rule

A rejecting verdict never writes: no defaults saved over the record, no repair in place, no delete, no overwrite with the current version. A legacy or migrate result may schedule a rewrite only after the whole migration checked out and a recoverable backup exists (`sidecar-files.md`).

Before proposing a format change, look for a design that leaves the format alone and gives the same result, and present it first. If the change is still needed, state the legacy read and the rollback behaviour in the same proposal.

## Prove the tests can fail

A fixture is evidence only if the test can be made to fail:

1. Record the four expected outputs for each of the seven cells.
2. Change one byte that decides the classification, the version, a length or the payload's validity.
3. Run the same reader with the same expected results.
4. Confirm all seven changed fixtures now give a different verdict.
5. Read each changed result, to be sure the change reached the reader and did not just break the test.

A result of exactly zero difference against an unchanged fixture is suspicious, not proof: the fixture and the expected values may come from the same source, the change may never have reached the reader, or the check may have measured nothing.

## Release checklist

- All seven cases exist, once each.
- Every case checks verdict, bytes accepted, state kept and action.
- Future, truncated and rollback cases apply nothing and write nothing.
- The future version log line is rate limited.
- Legacy and migrate rewrites wait for a full check and a backup.
- The mod's data version is independent of the game build.
- Seven deliberate byte changes give seven changed verdicts.

## How vanilla classified its own 1.30 inputs

The seven cells are the rule for mod data. Vanilla does not follow all of them; classify each case on its own, and never assume a migration from a version bump. A record saved on 1.29 arrives with game storage version 142 (`versioning-and-migration.md`, "Two version numbers").

| Input | Cell | What happens | Source |
|---|---|---|---|
| `CombinationLock` saved on 1.29 | legacy relative to the third value | reads two values after `super`; `m_CombinationInside` stays at its default because `version >= 143` is false | `P:\scripts\4_world\entities\itembase\combinationlock.c:169` to `:177` |
| `CombinationLock` saved on 1.30 | known version | reads three values; the save always writes the third | `combinationlock.c:128` to `:136` |
| A 1.29 lock reader meets a 1.30 save | rollback | the old reader stops after two values, so the subclass's next read takes the third and every later read in that entity's record is off by one value. Whether the separate records of attachments and cargo are affected is engine behaviour not checked on `P:\` | 1.29 scripts are not on `P:\`; not checked |
| `PlayerBase` saved on 1.29, loaded on a 1.30 multiplayer server | truncated, because vanilla does not gate the new value | the thermal read fails and prints `---- failed to load ThermalBiasHandler, read fail  ----`; stats, modifiers, agents, bleeding, the stomach and the other values read before it stay applied on the live player | `P:\scripts\4_world\entities\manbase\playerbase.c:7430` to `:7524` |
| `PlayerBase` saved on 1.30 multiplayer | known version | one float after the arrow manager, written by `ThermalBiasHandler.OnStoreSave` | `P:\scripts\4_world\classes\thermalbiashandler.c:67` to `:77` |
| `DigitalCodeLock` on a 1.29 world | fresh | the class did not exist, so there is no old record; its `OnStoreSave` and `OnStoreLoad` are new | `P:\scripts\4_world\entities\itembase\codelock.c:484` to `:500` |
| A 1.29 `BaseBuildingBase` fence | known version | three ints and a bool after `super`, unchanged | `P:\scripts\4_world\entities\itembase\basebuildingbase.c:420` to `:430` |
| `Rebuilding` with a stored version lower than its own | vanilla logs and goes on | `DeserializeConstructionData` returns `false` after reading only the version; `HandleStoreLoad` only logs, and `EntityAI.OnStoreLoad` ignores the result and reads the energy block next, so every later read is ten ints off | `P:\scripts\4_world\classes\rebuilding\rebuilding.c:518` to `:524`, `:483` to `:497`; `P:\scripts\3_game\entities\entityai.c:2981` to `:2991` |
| `Rebuilding` with a stored version higher than its own | vanilla accepts it, which breaks the future version cell | the check is `m_LastStorageVersion < REBUILDING_STORAGE_VERSION` only | `rebuilding.c:520` |
| `$mission:BunkerBroadcastPersistenceStorage.bin` missing | fresh | `Load` returns `false` and the defaults stay | `P:\scripts\4_world\classes\bunkerbroadcasthandler.c:29` to `:34`, `:56` to `:68` |
| The bunker file present | known version with no header | `Load` returns `true` after `Open` even when a `Read` fails | `bunkerbroadcasthandler.c:61` to `:65`; `P:\scripts\1_core\proto\serializer.c:58` |

Do not copy the `Rebuilding` or bunker file handling into mod code.
