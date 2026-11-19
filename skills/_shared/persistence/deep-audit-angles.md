# Audit angles and claim checks

What each of the eight review angles of the deep audit looks for, how a reviewer reports, how the claims are checked, and what the cross-actor pass traces. `deep-audit.md` says when each part runs.

The examples name the states, file suffixes (`.lfv`, `.virtualizing`, `.restoring`) and helper (`IsVirtualized()`) of a third-party virtual storage mod. Put the audited mod's own names in their place before handing a reviewer the list. The vanilla file functions and hooks the angles rely on are cited in the last section.

## What every reviewer gets and returns

Each angle reviewer starts with a fresh context and sees no other reviewer's output. Give it the code root, the README or spec, and the list of findings step 1 already made, so it does not find them again. Its job is to find bugs, not to write fixes.

The report:

- Every finding pastes the code it is about, with `path:line` start and end. A finding with no pasted code is a guess and is dropped at the claim check.
- Each finding has a title, the pasted code, the location, the reasoning and a severity from `deep-audit.md`, rated honestly.
- Defensive code is not a bug: a tolerant parser, a redundant guard, an `OR` branch that accepts two formats. It is not reported.
- No story, no "I noticed". An angle with nothing to report says so plainly.
- Keep it short; an angle report is a list of findings, not an essay.

## The eight angles

### Saving and the replace sequence

- The write order. In a DayZ mod: close the temp file, check it, back up the old file, then `DeleteFile` and `CopyFile`, then check the copy. Any step skipped or done early is a finding. Enforce Script has no rename and no flush, so any code or comment that calls this replace atomic is a finding too (`sidecar-files.md`).
- Backup rotation: `.bak1` moves to `.bak2` before the temp file replaces the main file, or a crash during rotation loses both backups.
- Every reader checks the header and the footer before it trusts the body.
- Recovery that picks a backup by label checks each label deeply enough: the whole file for the temp file; the header alone is enough for `.bak1` and `.bak2` only when they were checked when written.
- What the boot scan does with a temp file and no main file, a main file shorter than its header, and a `.bak1` newer than the main file.

### The state machine

- Every state the mod defines, with every change between them: which function makes it, and is it guarded (`deep-audit-state-machine.md`).
- Every "should never happen" branch: name the condition that stops it, or report it.
- Can the same id enter the same state twice with no reset between? What happens to the work the first entry started?
- Every difference between the code and the states the spec documents.

### Work queues across ticks

- Can the same id be queued twice, and what happens then?
- Can a queued item be cancelled in the middle of a batch, and is the disk consistent afterwards?
- Code that walks a queue while a callback adds to it, especially in the shutdown drain and in queue flushes an admin starts.
- Does server shutdown wait for the queue to empty, or stop mid batch and rely on recovery?
- Each tick does a bounded amount of work; an unbounded loop in a per tick handler is a finding.

### Engine hooks

The hooks are `EEInit`, `EEDelete`, `EEKilled`, `EECargoIn`, `EECargoOut`, `EEItemAttached`, `EEItemDetached`, `EEItemLocationChanged`, `OnStoreSave` and `OnStoreLoad`.

- A hook that must block before vanilla runs checks `IsVirtualized()`, or its equivalent, before it calls `super`. Calling `super` first and checking after is a finding.
- `EEDelete` and `EEKilled` clean up the same things; cleanup on only one of them is a finding.
- When the engine calls `OnStoreSave` and `OnStoreLoad`: code that assumes once per shutdown, when the engine calls them per entity at times script does not choose, is a finding.
- A hook that changes `m_State` or saves data without the mod's own guard is a finding.

Check what each event delivers, not only its signature (`deep-audit-hooks-and-super.md`).

### Admin commands

Admin commands are RPC handlers, debug menus and server console commands.

- Every id argument passes a strict pattern: no path traversal, no shell characters, a length limit.
- A command that builds a file path from input uses the path helper, never an inline string.
- A reset sent while the id is mid virtualize: is the queued work cancelled cleanly?
- A command that clears one store also clears the other (`deep-audit-flag-lifecycle.md`).
- Who may run each command, and is that checked on the server, not only hidden in the UI?

### Recovery paths

- For each file the mod keeps (`.lfv`, `.tmp`, `.bak1`, `.bak2`, `.virtualizing`, `.restoring`, `.manifest.json`, `.quarantine.json`), every mix of present, missing and corrupt, and what recovery does with each.
- A marker with no main file: the boot scan handles it without blocking the slot.
- When recovery cannot rebuild everything, it quarantines cleanly and the quarantined data stays readable for an admin.
- Running recovery twice on the same files gives the same result.
- A path that trusts a file's modification or creation time is a finding; daylight saving, clock sync and clock changes break it.

### Player actions

These are the action handlers that can fire while a container is virtualized but its stand-in is in the world.

- Every action that targets a container or its contents, and its `OnAction`, `OnFinish` or `OnExecute` method. `ActionTakeItem` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakeitem.c:6`), `ActionDropItem` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actiondropitem.c:30`) and `ActionAttach` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionattach.c:7`) are vanilla examples. `P:\scripts` has no `ActionMoveItem` or `ActionPickupContainer`, so list the audited mod's real action classes by searching for `class Action`.
- Each action method checks `IsVirtualized()` or `IsBusy()` before its body runs and before any `super` call that changes the container. A body that runs after `super` is the gate placed too late.
- When an action has a server and a client side, the check runs on the server; a client check is only advice.
- Context menu entries that skip the action layer are each a finding.

### Bad input from disk or network

- Every count read from disk (items, slots, string length, blob size) is capped before anything is allocated. A corrupt length that says "4 GB" must not crash the server or spend 30 seconds allocating.
- The header's magic value is checked before the body is parsed.
- The footer (`MAGIC_FILE_END` or its equivalent) is checked before the body is trusted.
- A string read from disk with broken encoding does not crash the parser.
- Every RPC handler that takes an id or a path caps before it parses.

## Checking the claims

The claim check runs after the angle reports and before they are merged. Use one reviewer with a fresh context that has not seen the angle reports, the spec, or the reference files the angle reviewers read, because shared context makes reviewers agree on the same mistake. Give it only the code root and a numbered list of bare claims: a one line statement and a `path:line` range each, with no reasoning, no severity and no author.

For each claim the reviewer opens the file, pastes the lines it finds with their numbers, and gives two separate verdicts, judged from the code alone:

| Verdict | Values |
|---|---|
| Does the file say this | Confirmed: the lines say what the claim says. Wrong location: the content is in the file at other lines, which it gives. Not found: the lines do not say it and the content is nowhere else in the file. |
| Does the conclusion follow | Holds: the code, and any code followed from it, has the stated consequence. Does not hold: the lines exist but the consequence does not follow; a deliberate defensive branch called a bug is this. Cannot tell: the decision needs code or runtime facts it could not reach, and it says which. |

"Mostly matches" is wrong location or not found, never confirmed. The output is one block per claim: the id, the pasted lines and the two verdicts, with no summary, advice or severity.

A claim that is confirmed and holds goes into the merged table. A wrong location claim is cited again at the right lines and then counts as confirmed. Any other claim is not yet actionable: the lead auditor reads the code itself and either keeps the claim with its own pasted evidence or drops it with a one line reason in the table. Never drop a claim silently. When more than about 10% of the claims come back not found, distrust the whole batch of angle reports.

## The cross-actor pass

This runs once, after the merge, on a reviewer with a fresh context and the strongest model available, because cross-actor reasoning is where smaller models drop bugs. Give it the code root and the README or spec, and tell it to find every way the code can lose, corrupt or quietly misroute player data, and that earlier reviews passed code that had real bugs:

1. Trace each writer (every site that touches a file or a marker) to every reader (recovery, cleanup, admin commands, the boot scan). Output one side does not consume is a bug.
2. Trace each marker, side file and flag to every cleanup site (delete, reset, admin recovery). A missing cleanup is a bug.
3. Trace each admin flag to every reader at run time. A value one store holds and the other does not is a bug.
4. An invariant the main path keeps and another entry point (synchronous, admin, mission restart) does not is a bug.
5. Data read from disk with no bound against malformed input is a bug.

Every finding cites a `path:line` range and a severity. The reviewer trusts no earlier report and no comment that says "this is safe because X": it checks X. One fix can expose the next bug in a chain, so the pass runs again after a fix, within the two round limit of `deep-audit.md`.

## Running the reviews

- Start all assigned angle reviewers at once. Running them one after another takes eight times as long and finds nothing more.
- Run the cross-actor pass on its own, after the merge.
- Angle reviews can run on a smaller model to save cost; the cross-actor pass cannot.
- Never feed one angle reviewer another's output. Each angle finds the bugs in its own scope.

## What the vanilla scripts offer

| What | Source |
|---|---|
| File functions: `FileExist`, `OpenFile`, `CloseFile` | `P:\scripts\1_core\proto\ensystem.c:397`, `:417`, `:443` |
| `FPrint`, `FPrintln` | `ensystem.c:462`, `:481` |
| `MakeDirectory`, `DeleteFile`, `CopyFile` | `ensystem.c:525`, `:528`, `:531` |
| `EEInit`, `EEDelete`, `EEItemLocationChanged`, `EEKilled` | `P:\scripts\3_game\entities\entityai.c:905`, `:946`, `:976`, `:1104` |
| `EEItemAttached`, `EEItemDetached`, `EECargoIn`, `EECargoOut` | `entityai.c:1159`, `:1199`, `:1234`, `:1248` |
| `OnStoreSave`, `OnStoreLoad` | `entityai.c:2910`, `:2978` |

There is no rename, no move and no flush call. All the hooks the engine hooks angle lists are methods of `EntityAI`.
