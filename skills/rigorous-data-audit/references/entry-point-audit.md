# Entry-point audit: mechanical check 3

Catches the bug class where the canonical path enforces an invariant but an alternative entry point (a synchronous shortcut, an admin command, an early mission hook) skips it. Open this in step 1 for every invariant the mod states about its saved data.

Reasoning agents miss this because they fixate on the canonical async flow and treat the shortcut as "obviously similar". The shortcut is rarely similar enough.

The worked examples are the mods LF_VStorage and SecretRock (third-party mod behaviour, read in their code or measured in game, not checkable on `P:\`). Function names and `file:line` values in the tables are those mods' and show the shape of each table. The vanilla hooks the procedure names are cited where they are listed. The search lines in the code blocks are recipes for the agent's search tool.

## Worked examples

### VULN-009: synchronous virtualize leaves a stale marker

`Virtualize_Async` wrote `.virtualizing`, did the work across ticks, then removed the marker. `VirtualizeSynchronous` (used during shutdown) wrote `.virtualizing` but never removed it, because the shutdown path skipped the cleanup branch that runs after completion. The next boot saw the marker, treated the container as crashed during virtualize, and entered recovery on a fully virtualized container. Recovery merged duplicates.

### VULN-001: kill switch not durable across mission entry points

`OnMissionStart` set the in-memory flag `m_ExternalVSDetected`. `OnMissionLoaded` read it and gated work. It looked correct. The bug: a separate boot path (a server reload after an admin command) skipped `OnMissionStart` and went straight to `OnMissionLoaded`; the flag was still false and the gate did not fire. The fix was to persist the detection result on disk so any entry point could read it again.

### VULN-004: pre-super gate runs after vanilla super

`EEItemAttached` called `super.EEItemAttached(item, slot)` first, then checked `IsVirtualized()`. The vanilla super had already changed the cargo before the gate fired, leaving inconsistent state.

### SecretRock data audit: an unregister by proximity deletes a neighbour's entry

SecretRock keeps the rocks it placed in its own registry (`placed.json`: class, position and id per entry). The canonical removal went by id: `EEDelete` called `UnregisterEntity`, which looked the rock up by id. When the rock had no id it fell back to the nearest entry of the same class within 0.75 m and saved the file without it. Two entry points delete a rock that never got an id: the placement that creates the rock, checks the site and deletes it on refusal, and an admin who spawns one from the console and deletes it. Both removed the entry of a registered rock nearby, which did not come back after the next restart. Fix: removal needs a matching id, and an entity without one never touches the file. Found by reading the code (audit of 2026-10-03); with the fix, a console rock spawned 0.3 m from a registered one (horizontally) and then deleted left the file's SHA-256 unchanged in game (DayZDiag 1.29), and the registered rock came back after the restart.

Another finding of the same audit is the shutdown face of this invariant: a restore pass still in the `CALL_CATEGORY_SYSTEM` queue after `OnMissionFinish` cleared the shutdown flag again, so the deletions of the shutdown unregistered entries. `OnMissionFinish` now removes the pass before setting the flag (the shutdown order in game is not confirmed). Both rules, and the restore that binds by id before position, are in the `dayz-persistence` skill: hard stop 8 in its `SKILL.md`, and the section "A registry entry leaves by its id, never by proximity" in its `references/load-and-restore.md`.

## Procedure

### Step 1: inventory the entry points per invariant

For each invariant the mod enforces, list every entry point that should honour it. Common invariants and their entry points:

**Invariant: a container must end a virtualize with no marker on disk**

- `Virtualize_Async` (canonical, multi-tick)
- `VirtualizeSynchronous` (shutdown)
- `Virtualize_FromAdminCommand` (`migrate-all`)
- `Virtualize_FromMigrationStub` (legacy, one-shot)

**Invariant: detection of an external virtual storage mod must gate work on every boot**

- `OnMissionStart`
- `OnMissionLoaded`
- Server reload after an admin command
- World load after a rare crash recovery

The vanilla `Mission` class declares `OnInit`, `OnMissionStart` (`P:\scripts\3_game\gameplay.c:701`), `OnMissionFinish` (`gameplay.c:702`) and `OnUpdate` (`gameplay.c:703`). A search of `P:\scripts` finds no `OnMissionLoaded`: that hook comes from a framework or from the mod itself (Community Framework modules have one; not yet checked on `P:\`). List the mission hooks the audited mod really overrides, vanilla and framework, as separate entry points.

**Invariant: the pre-super gate must precede the vanilla super in EE hooks**

- `EEInit` (`P:\scripts\3_game\entities\entityai.c:905`)
- `EEDelete` (`entityai.c:946`)
- `EEKilled` (`entityai.c:1104`)
- `EECargoIn` (`entityai.c:1234`) and `EECargoOut` (`entityai.c:1248`)
- `EEItemAttached` (`entityai.c:1159`) and `EEItemDetached` (`entityai.c:1199`)
- `EEItemLocationChanged` (`entityai.c:976`)
- `OnStoreSave` (`entityai.c:2910`) and `OnStoreLoad` (`entityai.c:2978`)

**Invariant: an entry of the mod's own registry leaves only by its own id**

- `EEDelete` of a registered entity (pickup, dismantle, destruction)
- Placement refused after the entity was created (create, check the site, delete)
- Admin console spawn, then delete (the entity never got an id)
- `EEDelete` of every entity while the mission shuts down
- A restore pass still queued (`CallLater`) when `OnMissionFinish` runs

### Step 2: for each invariant, walk every entry point

Search for the entry-point name; open each match; verify that the invariant is enforced. Build the table:

| Invariant | Entry point | File:Line | Honoured? | Notes |
|---|---|---|---|---|
| End virtualize without marker | `Virtualize_Async` | persistence.c:340 | yes | Removes `.virtualizing` on success |
| End virtualize without marker | `VirtualizeSynchronous` | persistence.c:480 | **no: VULN-009** | Skips the cleanup branch |
| End virtualize without marker | `Virtualize_FromAdminCommand` | admin.c:120 | yes | Calls the async path |
| Pre-super gate | `EEItemAttached` | events.c:88 | **no: VULN-004** | Gate after super |
| Pre-super gate | `EECargoIn` | events.c:102 | yes | |

### Step 3: specific patterns to search

**Synchronous shortcuts of an async operation**:

```text
Grep "Synchronous|_Sync\b|Force\w+|_Now\b|ImmediateMode" --type c --output_mode content -n true
```

For each hit, find the corresponding async function and compare the two by hand. The difference should be limited to scheduling and yielding, not invariants.

**Admin command handlers**:

```text
Grep "OnAdminCommand|HandleAdmin|RegisterCommand|admin_|Cmd_" --type c --output_mode content -n true
```

For each handler, ask: does this short-circuit the async queue? If yes, does it acquire the same gates and clean up the same markers as the queue would?

**Mission entry points**:

```text
Grep "OnMissionStart|OnMissionLoaded|OnMissionFinish|OnUpdate" --type c --output_mode content -n true
```

For state set in `OnMissionStart` and read in `OnMissionLoaded`: is there a path that reaches `OnMissionLoaded` without `OnMissionStart`? Server reload, world reload, mission script reload. If yes, the state must be **on disk**, not in memory.

**EE hook ordering**:

```text
Grep "override\s+void\s+EE" --type c --output_mode content -n true
```

For each EE override that gates: read the body. The gate must run before the `super` call in every such hook. A hook that calls `super` first and gates afterwards is a finding (VULN-004), even when every hook does it in the same order.

**Proximity used as identity**:

```text
Grep "Closest|Nearest|GetObjectsAtPosition" --type c --output_mode content -n true
```

For each hit, ask whether it decides which registry entry an entity owns. If it does:

- a matching id must win;
- an entity without an id must not remove an entry;
- on restore, a candidate in the radius that does not carry the entry's id is not a match. The first candidate is not guaranteed to be the nearest one: `GetObjectsAtPosition3D` promises no order (`P:\scripts\3_game\global\game.c:930`; its comment says only that it returns all objects in the sphere);
- an empty radius does not prove that the entry's entity is gone, so a restore that creates on it can make a second one.

How a restore should bind and create is an open problem: no rule for it has come out of review sound (the `dayz-persistence` skill, hard stop 8, and point 2 of the registry section in its `references/load-and-restore.md`).

### Step 4: output

A findings table with three columns: invariant, offending entry point, fix sketch. Group by invariant so the user sees "this invariant is honoured in 3 of 4 entry points". One wrong entry point is enough for a finding; rate it by what the break does to player data, as with any other finding: P0 when data loss is possible, P1 when recovery is required. VULN-009 above is P1: the stale marker sends a complete container into recovery.

## Heuristics

- An entry-point inventory of fewer than 4 items per invariant is suspicious: go and look harder, you missed one.
- "Synchronous", "Sync", "Force", "Immediate" or "Now" in a function name means a shortcut, which means high suspicion.
- Admin commands almost always skip something. Default to "untrusted, audit individually".
- Server-reload and mission-reload paths are easy to forget; ask the user explicitly which entry points exist if unsure.

## Time budget

About 3 to 5 minutes per invariant. LF_VStorage has about 6 invariants of this shape, so about 30 minutes. Slow, but cheap relative to a P0 that escapes.
