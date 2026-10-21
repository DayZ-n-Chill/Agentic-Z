# Persistence pack

Reference for saving mod data across server restarts: the store save and load chain, save versions and upgrade paths, base building parts, and the data loss audit run before a release. Written for `dayz-persistence-specialist`; any worker that touches `OnStoreSave` or `OnStoreLoad` may load the file it needs.

Every fact here was checked in the vanilla scripts and configs on `P:\` and cites the file and line it came from. Line numbers are from game storage version 144 (`P:\scripts\3_game\global\game.c:5`); after a game update, search for the method name if a line has moved.

The short pattern file `_shared/enscript/patterns/persistence.md` shows the basic version header. This pack goes deeper.

## Which file to open

| Question | File |
|---|---|
| What does the engine save for me, and what must my script save? In which order do the load hooks run? | `save-load-contract.md` |
| How do I stamp my own version, add or remove a field, and keep old saves loading? | `versioning-and-migration.md` |
| How do base building parts, territory flags and locks survive a restart? | `base-building.md` |
| How do I run the audit before release, and what does the report look like? | `data-audit.md` |
| Data that is not tied to one object (server wide stats, player lists) | `versioning-and-migration.md`, section "Data outside the object store" |
