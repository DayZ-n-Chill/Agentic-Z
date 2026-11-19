# Where to save: entity stream, ModStorage or a file

Which of three places saved data belongs in, what each one costs, and what must stop persistence work from shipping. Decide before writing any code; open it when a task says "keep this after a restart" and it is not yet clear where the data lives.

## Four questions

Answer these four first:

1. Is the data attached to one entity?
2. Does the mod own that entity's class?
3. Must the data survive the mod being removed and added back?
4. Must a server admin read or repair it outside the game?

Each matching row below adds a candidate. Exactly one candidate is the answer. With none or with several, ask the caller which property matters more instead of quietly picking one.

| What is true | Candidate | File |
|---|---|---|
| The data is not attached to an entity, or an admin must read or repair it outside the game | A file of the mod's own under the server profile | `sidecar-files.md` |
| The mod does not own the entity, or the data must survive uninstall and reinstall | Community Framework ModStorage | `cf-modstorage.md` |
| The data is attached to an entity the mod owns, need not survive uninstall, and need not be read outside the game | The entity's own `OnStoreSave` and `OnStoreLoad` stream | `save-load-contract.md` |

This is a routing decision, not a ranking. Data with no entity that must also survive uninstall matches two rows, so decide who owns it and how an admin recovers it before choosing.

## What each choice costs

* **The entity stream.** The hooks are `EntityAI.OnStoreSave` and `OnStoreLoad` (`P:\scripts\3_game\entities\entityai.c:2910` and `:2978`). The stream has no field names, so correctness is the exact order and type of every write and read. When the mod is removed, nothing reads or writes its values any more, and on a vanilla class the leftover values shift every class after them (`versioning-and-migration.md`, "Adding saved fields to a vanilla class").
* **ModStorage.** Needs Community Framework as a dependency. It frames each mod's block and keeps the block of a mod that is not loaded, but it does not write the mod's upgrade paths for it (`cf-modstorage.md`).
* **A file.** Script has no rename and no move, so a replace is never atomic and needs a backup and a read back (`sidecar-files.md`). In return an admin can open, back up and repair it.

## Hard stops

Stop and fix the problem before recommending or shipping persistence work when:

1. An API, method, hook, field or signature is written without a checked `path:line`.
2. A format change leaves out what happens to old saves, or what the old reader does with new data. When a design with no format change gives the same result, present it first.
3. A migration saves rewritten data on its own with no backup and no verification.
4. A future version is accepted silently instead of being rejected without writing, with a rate limited message.
5. A failed `ctx.Read` leaves partly applied state that is treated as valid.
6. A test covers only the happy path; future, truncated, rollback and injected I/O failures are not exercised.
7. Live cargo is walked by a frozen index across ticks while items can be removed during the walk (`load-and-restore.md`).
8. An entry of the mod's own registry of world entities is removed by proximity, bound on restore to an entity that does not carry its id, or given a new entity while one it already had may still live; no rule for that restore has held up under review (`load-and-restore.md`).
