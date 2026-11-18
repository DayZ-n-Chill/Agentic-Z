# Persistence pack

Reference for saving mod data across server restarts: the store save and load chain, save versions and upgrade paths, base building parts, and the data loss audit run before a release. Written for `dayz-persistence-specialist`; any worker that touches `OnStoreSave` or `OnStoreLoad` may load the file it needs.

Every fact here was checked in the vanilla scripts and configs on `P:\` and cites the file and line it came from, except lines marked as measured in game or as third-party mod behaviour (Community Framework and other mods), which say so. Line numbers are from game storage version 144 (`P:\scripts\3_game\global\game.c:5`); after a game update, search for the method name if a line has moved.

The short pattern file `_shared/enscript/patterns/persistence.md` shows the basic version header. This pack goes deeper.

## Which file to open

| Question | File |
|---|---|
| Where should this data live: the entity stream, Community Framework ModStorage or a file of my own? What must stop a persistence change from shipping? | `where-to-save.md` |
| What does the engine save for me, and what must my script save? In which order do the load hooks run? | `save-load-contract.md` |
| How do I stamp my own version, add or remove a field, and keep old saves loading? | `versioning-and-migration.md` |
| Which seven inputs must a format change classify, and how do I prove the tests can fail? | `migration-matrix.md` |
| How does Community Framework frame each mod's block, and which version does it hand my mod? | `cf-modstorage.md` |
| How do I keep data in a file of my own and replace it so that every step can be recovered? | `sidecar-files.md` |
| What happens when `OnStoreLoad` returns false? In which order do my structures and stored entities come back? How do I keep a registry of my entities or capture live cargo? | `load-and-restore.md` |
| What did 1.30 change in the vanilla streams, and what breaks in a 1.29 mod? | `dayz-1-30-persistence.md` |
| Why do placed objects vanish after a restart, and what does a copied storage folder need to load? | `lifetime-and-storage.md` |
| What do `types.xml`, `cfgspawnabletypes.xml`, `events.xml`, `globals.xml`, `economy.xml` and `cfglimitsdefinition.xml` look like on 1.30? | `central-economy-files.md` |
| Data that is not tied to one object (server wide stats, player lists) | `versioning-and-migration.md`, section "Data outside the object store" |

### Base building

| Question | File |
|---|---|
| How do base building parts, territory flags and locks survive a restart? | `base-building.md` |
| Which classes make up a buildable object, what is the kit to base flow, and what breaks silently? Quick triage of build, dismantle and save symptoms. | `base-building-structures.md` |
| Which config fields does a buildable object need, and which code reads each one? Tool masks, materials, damage zones. | `base-building-config.md` |
| What is the exact call chain from crafting the kit to a base that survives a restart? Which hook do I override? | `base-building-lifecycle.md` |
| How does the vanilla Fence add a gate, a lock, barbed wire damage and extra saved fields? | `base-building-fence-gate.md` |
| How are parts saved, what is the 93 part cap, and what must be checked before a save change ships? | `base-building-save-checklist.md` |
| What did 1.30 change (class hierarchy, `*ServerEx`, Rebuilding on map buildings, masonry, code lock), and how do I port a 1.29 mod? | `base-building-1-30.md` |
| Why does the build action never appear, why is the hologram not tinted, why is my item carried in one hand, how do I place on a wall? | `base-building-placement.md` |

### Data loss audit

| Question | File |
|---|---|
| How do I run the audit before release, and what does the report look like? | `data-audit.md` |
| A bug would lose player progression: what is the full audit, step by step? | `deep-audit.md` |
| What do I paste into each of the eight angle reviews and the cross-actor pass? | `deep-audit-prompts.md` |
| Mechanical check 1: do all path helpers agree on file names and suffixes? | `deep-audit-path-naming.md` |
| Mechanical check 2: does every written file or marker have a cleanup on delete and reset? | `deep-audit-sidecar-cleanup.md` |
| Mechanical check 3: does every entry point (sync shortcut, admin, shutdown, boot) keep the invariant? | `deep-audit-entry-points.md` |
| Mechanical check 4: do a flag and the file it mirrors always move together? | `deep-audit-flag-lifecycle.md` |
| Which state transitions are legal, and is any state counted twice? | `deep-audit-state-machine.md` |
| How do I audit evidence indexes and bundles published across several roots for crash safety? | `deep-audit-evidence-bundles.md` |
| How do I audit durable authority publication and authenticated localhost calls? | `deep-audit-authority-loopback.md` |
| What goes wrong when an atomic operation is rebuilt in phases? | `deep-audit-incremental-rebuild.md` |
| Does this engine event deliver what the code assumes, and does every class in the chain call `super`? | `deep-audit-hooks-and-super.md` |
| A fix hardened a contract, reuses another actor's id, or was applied to generated output: what must be checked again? | `deep-audit-fix-traps.md` |
| Is this evidence real: deployed build against source, log lines, positive and negative controls, inventories? | `deep-audit-evidence-controls.md` |

Offline Python models of the three contracts, with tests, are in `scripts/tools/persistence-contracts/`.
