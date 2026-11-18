# Deep data audit

How to audit a mod where a bug loses player progression (saved data, state machines, queues that work across ticks, recovery paths): mechanical checks first, eight review angles, every finding checked against the real file, a pass that traces data across actors, fixes, a short re-audit and four tests in game. Open it when `data-audit.md` says to run the deep audit, or when asked whether such a mod is safe to release. The agent runs the checks with its own search tools; there is no script.

## When to run it

Run it when any of these is true:

- The mod touches saved data, save files, state machines or queues of work that runs across ticks.
- A bug would lose data without a message: lost items, wrong storage ids, lost money.
- The user asks for an audit or a deep review, asks whether a release is safe, or says a change could break progression.
- The user applied several fixes and wants them checked before a rebuild and test.
- The user hands over findings from another auditor to verify.

Skip it for a cosmetic or UI only change.

## Why reading the code is not enough

A reviewer that reads the code and follows the normal path produces a sound argument and still misses whole classes of bug. These are the classes a reading review misses, each with the mechanical check that finds it:

| Bug class | Example | Why reading misses it | Check |
|---|---|---|---|
| Path helpers disagree | one helper writes `.tmp`, another looks for `.lfv.tmp` | it is a list to compare, not a chain to follow; each helper looks right alone | `deep-audit-path-naming.md` |
| A file or marker has no cleanup | `.restoring` and `.manifest.json` survive the container delete | every write needs a delete; reviewers check the writer, not the cleanup | `deep-audit-sidecar-cleanup.md` |
| Another entry point skips the rule | the synchronous shutdown path leaves a marker; a kill switch set in memory is lost on a reload | reviewers follow the main path and glance at the shortcut | `deep-audit-entry-points.md` |
| A flag and its file drift apart | an admin clears a flag while the file still holds the old state | two stores must move together; each is checked alone | `deep-audit-flag-lifecycle.md` |
| A gate runs after `super` | an `EE` hook checks its gate after vanilla already changed the cargo | "is the gate there?" does not show the order | `deep-audit-hooks-and-super.md` |
| Counts read from disk have no cap | a count field sizes an array with no upper bound | the threat model was not in the review's scope | angle 8 below |

Most of these are found by a search and a table walk in minutes. The rest need one writer, another deleter and an admin override held in mind together, across three or more files, which is where reading reviews thin out. Reviewers also report invented findings as confidently as real ones, so the audit pairs cheap mechanical checks, reviews aimed at those gaps, and a hostile check of every finding before anything is trusted.

## Steps

Phase one, steps 1 to 6, runs from the code and ends with verified findings and applied fixes. Phase two, step 7, is the test in game; a clean audit alone does not make a release safe. Do the steps in order, and do not start a step until the one before meets its exit condition.

1. Mechanical checks.
2. Cover the eight review angles.
3. Verify every finding and build one table.
4. Trace data across actors.
5. Apply fixes.
6. Re-audit what changed.
7. Test in game.

## Mechanical checks (step 1)

Run these before any review starts. Each is a search plus a table. They catch bookkeeping bugs that reading misses. Done when a written list of mechanical findings exists, empty if clean, each citing `path:line_start-line_end`, ready to hand to step 2.

- `deep-audit-path-naming.md`: helpers that build file paths disagree.
- `deep-audit-sidecar-cleanup.md`: a file or marker is never deleted on delete or reset.
- `deep-audit-entry-points.md`: another entry point skips a rule the main path keeps.
- `deep-audit-flag-lifecycle.md`: a flag and the file it mirrors drift apart.
- `deep-audit-incremental-rebuild.md`: an operation that used to be one step now runs in phases.
- `deep-audit-state-machine.md`: illegal state changes and state counted twice.
- The whole inheritance chain: when a rule depends on every class calling `super` (open and close failsafes, `EE` hook chains, overrides on a modded base), search for the override in every class up to the modded base, not only the leaf (`deep-audit-hooks-and-super.md`).

Two DayZ facts every audit assumes, both found by search rather than by reading the normal path:

- Script has no rename or move, so a write to a temp file, a check and a replace is not atomic (`sidecar-files.md`).
- `EntityAI.OnStoreSave` (`P:\scripts\3_game\entities\entityai.c:2910`) writes a varying number of values before a subclass's own (`save-load-contract.md`, "The base class data has no fixed width").

Where the two meet: in one save simulator the normal save deleted a copy that failed its check, while the recovery path left the bad bytes in place as the live file. When a mod has both a save and a recovery, compare their check branches line by line.

Hand this list to the step 2 reviews so they do not find the same things again.

## The eight review angles (step 2)

The angles are areas to cover, not eight reviewers. One reviewer can cover a bounded audit; split angles across reviewers only when that is useful. Mark an angle that does not apply, with the reason. Keep each report short and free of narrative.

Every finding pastes the code it is about, with `path:line`, plus a severity. A description without the pasted code is a guess, not a finding; step 3 cannot check it, and it goes back to the reviewer.

1. Saved data and atomic writes: write order, `.tmp`, `.bak1` and `.bak2` rotation, header and footer checks, recovery from a half written file.
2. State machine: every change of state, every gate, every branch that "should never happen".
3. Queues across ticks: running twice for the same storage id, cancelling, adding to a queue while it is walked, draining on shutdown.
4. Engine hooks: where the gate sits, the order of `super` calls, `EEDelete` against `EEKilled`, how often `OnStoreSave` and `OnStoreLoad` run.
5. Admin commands: input checks, path traversal, races with running queues, files that disagree with memory.
6. Recovery: what a crash leaves on disk, what the next boot reads, reduced modes, setting half finished state aside.
7. Actions: every action handler that may fire while a container is stored away; gates run before vanilla `super`.
8. Input bounds: caps on counts, sizes and lengths read from disk, checked before anything is allocated.

What each angle looks for, how the claims are checked and what the cross-actor pass traces are in `deep-audit-angles.md`.

## Verify every finding (step 3)

This step turns "a reviewer reported it" into "it is real". Done when every row of the table was checked against the real file, the sample in 3c passed, and each row is labelled defect or improvement.

3a. Open the file at each cited range and confirm it says what the pasted code claims. Reviewers drift on line numbers, copy citations from a sibling file, and sometimes invent a likely looking range. A finding whose code does not match the file is dropped or worked out again. Before a cause goes into lasting notes, record the file, the search pattern and how many matches it returned, which must be more than zero; without those it is a guess. To choose between two explanations, find a prediction only the new one makes and check it.

3b. When an independent check is assigned, give it to a reviewer of another model family with a fresh context that has not seen the angle reports. If none is available, say so; never claim independence you did not have. Hand it only the claims and their locations, with no reasoning and no severity. For each claim it returns two separate answers with the lines pasted: does the file say this, and does the conclusion follow from that code, judged without the auditor's reasoning. A claim it cannot confirm on either answer is not acted on until you read it yourself; never drop it silently, because that is how a real finding disappears. A verifier that refutes nothing is a reason to distrust the verifier, not to trust the batch; one claim can arrive confirmed on a false premise about inheritance. Agreement between reviewers that read the same spec or conventions is shared error, not confirmation, so the verifier must not share that context.

3c. Pick a fifth of the findings at random and check them yourself in the files. If more than a tenth of that sample is invented, the audit cannot be trusted: run step 2 again with stricter instructions, or drop it. Never act on an audit that fails this check.

Then build one table without duplicates:

| ID | Severity | Title | File and lines | Found by | Verified by | Defect or improvement | Status |
|---|---|---|---|---|---|---|---|

- You set the severity, not the reviewer, by what the bug does to player data: data loss possible, recovery needed, degraded behaviour, or untidy code.
- Defensive code is not a bug. A branch that accepts two formats, a tolerant parser or a redundant guard is robustness. Label it an improvement at most; never file it as a defect or raise its severity. Calling tolerance a bug is the most common false finding.

## Trace data across actors (step 4)

Give one reviewer that can reason across actors a fresh context: no audit history, no review output. Hand it the code, the README or spec, and one instruction: "Find every way this code can lose, corrupt, or silently misroute player data. Trace each writer to every reader, each sidecar to every cleanup site, each admin flag to every consumer. Where any of those triples is incomplete, that is a bug." More on this pass is in `deep-audit-angles.md`, section "The cross-actor pass".

Reviewers told to audit one layer stay in that layer; this instruction makes the reviewer follow data from one actor to the next. If it finds nothing, the audit is converging. If it finds a defect, reproduce it, rate it and check the affected path again within the agreed budget; hand back what is left when the budget runs out. A new finding blocks only with evidence that can be run.

## Apply fixes (step 5)

Done when every fix names the check or angle that caught it, a new search shows the pattern is gone everywhere, and no fix is larger than the verified change.

- Write down which check or angle caught each fix. A fix with no source is a hunch; check it again before it ships.
- After each fix, search again for the bug pattern everywhere, not only at the cited line. Path helper bugs often have siblings.
- Apply only what step 3 verified. When the verified fix is "add X before the else", add X, not also Y and Z because an unverified sibling finding suggested them.
- When the audit produced work, keep a tracker file next to the findings file: one row per item with its id, severity, `file:line`, the issue, the fix, the owner and a status (open, in progress, closed with the commit, or won't fix with the reason). Keep the file after the last item closes. Do not create tasks in a tracker tool without asking the user.
- Never ship a release, a packed skill or a patch file built on findings that did not pass step 3.

## Re-audit what changed (step 6)

Run the mechanical checks again, plus the two angles whose code changed most. When a fix adds new design (a new flow, state, recovery or cleanup path), also run every angle that applies over that new code, because its defects are in the design and a check of the changed lines cannot see them (`deep-audit-fix-traps.md`).

A new finding goes back to step 5 once. If a finding of the same kind comes back a second time, the defect is in the design, not the patch: stop, list the rest as numbered work for later and hand it back. The budget is two rounds, and a finding blocks only with a reproduction that can be run.

When a value passes through several layers, write a test for each pair of neighbouring layers that runs both real layers, with no fakes between them. Check each test by deleting the code that joins the two layers: the test must then fail. Accept the fix only when whoever receives it repeats that deletion and sees the failure too.

## Test in game (step 7)

The user runs these; the agent cannot. Only when all four pass is the release safe:

- A player connects with a stored container, the server restarts, and the container is intact.
- The server is killed in the middle of storing a container, then rebooted: recovery finishes, nothing is lost, and no marker files are left.
- An admin resets a container while it is being stored: the state is stable afterwards.
- After a long session every storage id on disk matches what players did: no orphans and no ghosts.

The audit's job is to make the code phase trustworthy enough that this phase is short.

## Mistakes that cost rounds

- Calling a mod release safe after step 2. Steps 3 to 7 are not optional, and only step 7 earns "release safe".
- Running eight identical reviews instead of eight different angles. Identical reviews give redundant reports.
- Skipping step 1 because the reviews will catch it. They do not.
- Treating defensive code as a bug.
- Trusting totals without the rows behind them. "34 verified, 9 invented" means nothing unless each finding can be opened.
- Acting on an audit that has not passed step 3. Reports are guesses until verified.
- Trusting agreement between reviewers that shared context.
- Running all eight angles again after fixes. Step 6 covers what changed, plus every angle over new design only.
- Running independent reviews one after another when running them together was allowed.
- Reading a skipped check as a pass. A gate skipped on a precondition (a dirty work tree, an unreadable config) looks like a pass. Confirm the gate checked what changed, and count exit codes, not findings.

## On Linux

The procedure is the same. The search lines in the `deep-audit-*.md` files are recipes for the agent's own search tool, so they work on Linux too; outside the agent, `rg -n --type c "<pattern>"` runs the same search, and the tables are built by hand or with Python. Use forward slashes and expect a case sensitive file system. The Proton setup and its traps are in `_shared/linux-proton.md`.
