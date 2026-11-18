# Deep data audit

The full audit for a mod where a bug means lost player progression (saved data, state machines, async queues, recovery paths): mechanical checks first, eight review angles, verification of every finding against the real file, a cross-actor pass, fixes, a re-audit and four tests in game. Open this when `data-audit.md` says to run the deep audit, or when asked whether such a mod is release-safe. Labels such as `VULN-003` are the finding numbers of the worked example used in the check files. The agent runs the checks with its own search tools; there is no script.

## When to invoke

Trigger automatically when any of these are true:

- Mod touches persistence, save files, state machines, or async work queues
- A bug would cause **silent data loss** (lost items, wrong sids, money loss)
- User asks for an audit or a deep review, asks "release-safe?", or says a change could break progression
- User just applied multiple fixes and wants verification before rebuild/test
- User hands you findings from an external auditor and asks you to verify

If the change is cosmetic or UI-only, this procedure is overkill; skip it.

## Why reasoning alone is insufficient

The reasoning agents that signed off on the virtual storage mod were not lazy. Each read the relevant code and produced a coherent argument. They missed bugs anyway. Looking at the 12 VULNs the implementer-grade audit caught:

| Failure mode | VULN examples | Why reasoning misses it |
|---|---|---|
| Path-helper inconsistency | VULN-003 (`.tmp` vs `.lfv.tmp`) | Bug is enumerable, not deducible, reasoning agents trace happy paths and see helpers used in isolation |
| Sidecar/marker not cleaned | VULN-008 (`.restoring`/`.manifest.json` survive `DeleteContainerFiles`) | Symmetric obligation, every Write needs a Delete. Reasoning agents check the writer side, not the cleanup side |
| Alternative entry point skips invariant | VULN-009 (sync path leaves stale marker), VULN-001 (kill-switch not durable) | Agent fixates on the canonical async path; the synchronous shortcut is "obviously similar" so gets a glance |
| Flag lifecycle asymmetry | VULN-010 (admin clears flag while sidecar still references stale state) | Two state stores must move together; reasoning agents check each store internally |
| Pre-super gate placement | VULN-004 (gate runs after vanilla super) | Order of operations within an EE hook is invisible from "is the gate present?" |
| Sanity caps missing | VULN-011 (count fields read from disk uncapped) | Threat model not in scope of the agent's prompt |

Five of those are **enumerable mechanically**, a search plus a table walk finds them in minutes (the per-check time budgets in the reference files), with no reasoning needed. Three are **cross-actor**, one writer + a different deleter + admin override. Reasoning across 3+ files is where reasoning agents thin out.

And separately: agents *report* findings convincingly whether or not the findings are real. The fix is three-pronged: cheap mechanical pre-checks first, then reasoning agents specifically prompted on the gaps reasoning is bad at, then an adversarial verification pass before any finding is trusted.

## Workflow

Seven steps in two phases.

- **Phase A (steps 1 to 6)** is the audit. It runs entirely from the codebase and ends with a verified findings list and fixes applied.
- **Phase B (step 7)** is in-game validation. A clean audit is necessary but not sufficient for "release-safe".

Skipping early steps makes later ones less effective, do not skip. Each step below carries two annotations in a quote block: **Assignment** (who runs the step's work and under which budget) and **Done when** (the explicit exit criterion, do not advance until it holds).

## Phase A: audit (steps 1 to 6)

### Step 1: Mechanical pre-checks (cheap, deterministic, fast)

> **Assignment:** run deterministic checks directly; delegate only if assigned and useful.
> **Done when:** a written list of mechanical findings exists (zero items if
> clean), each citing `path:line_start-line_end`, ready to paste into step 2.

Run before spawning any agents. Each check is a grep + table walk; on a mod of that size they take about two hours together (the four mechanical-check files, `deep-audit-state-machine.md` and `deep-audit-hooks-and-super.md` each give a time budget; the other three step-1 files give none), and they catch the bookkeeping-style bugs reasoning misses.

These reference files give the procedures. Read the ones that apply before running:

- `deep-audit-path-naming.md`: catches path-helper drift (VULN-003 class)
- `deep-audit-sidecar-cleanup.md`: catches missing cleanup on delete/reset (VULN-008 class)
- `deep-audit-entry-points.md`: catches alternative entry points skipping invariants (VULN-009, VULN-001 class)
- `deep-audit-flag-lifecycle.md`: catches flag/sidecar state-store divergence (VULN-010 class)
- `deep-audit-evidence-bundles.md`: authoritative evidence indexes and multi-root publication
- `deep-audit-authority-loopback.md`: durable authority publication and authenticated-localhost provenance
- `deep-audit-incremental-rebuild.md`: atomic-to-phased conversion hazards

Plus the existing structural check:

- `deep-audit-state-machine.md`: catches illegal transitions and double-counted state
- **Full-ancestry super-chain walk**: whenever an invariant depends on "leaf class chains super" (physical Open/Close failsafes, EE* hook propagation, modded-base overrides), grep the override in every class of the inheritance chain up to the modded base, never just the leaf. See `deep-audit-hooks-and-super.md`.

Two DayZ facts every audit assumes, both found with a search rather than by reading the happy path: script has no rename or move, so a temp, verify and replace sequence is not atomic (`sidecar-files.md`), and `EntityAI.OnStoreSave` (`P:\scripts\3_game\entities\entityai.c:2910`) writes a varying number of values before a subclass's own (`save-load-contract.md`, "The base class data has no fixed width"). Where they combine: on a save simulator, the normal save path deleted a destination that failed its check after the copy, while the recovery path left the corrupt bytes in place as the live file. When a codebase has a save and a recover, compare their verify branches line by line.

This list goes into step 2's agent prompts as known-context so agents do not waste cycles re-finding.

### Step 2: Cover the relevant audit angles

> **Assignment:** the orchestrator chooses reviewer family, effort and lane count
> from risk and available budget; this procedure does not authorize extra agents.
> **Done when:** relevant angles are covered; every finding pastes the literal
> code snippet it is about (not just a line citation) plus severity. A
> "finding" that only describes code without pasting it is bounced back as
> SUSPECT, not accepted.

The eight angles below are coverage dimensions, not eight required agents or reports. Use one reviewer for a bounded audit; distribute independent angles only when delegated and useful. Bound delegated reports (≤700 words, no narrative).

**Show, don't tell.** A claim of the form "this code has bug X" must include a copy-paste of the actual code, with `path:line`. A description without the snippet is a hypothesis, not a finding, the next step cannot verify it and it will be dropped. This requirement is what makes "verified" something grep-able rather than narrative.

Coverage dimensions; mark non-applicable angles with a reason:

1. **Persistence & atomic flow**: write barriers, fsync semantics, `.tmp`/`.bak1`/`.bak2` rotation, header/footer verification, partial-write recovery
2. **State machine**: every transition, every gate, every "should never happen" branch
3. **Async queues & cross-tick safety**: re-entry on the same sid, cancellation, queue-during-iteration, shutdown drain
4. **Engine hooks (EE*)**, entry-point gating placement, super-call ordering, EEDelete vs EEKilled symmetry, OnStoreSave/OnStoreLoad cadence
5. **Admin commands**: input validation, path traversal, race with running queues, sidecar ↔ in-memory consistency
6. **Recovery paths**: what crash leaves on disk, what boot consumes, degraded modes, partial-state quarantine
7. **Action layer (pre-super gates)**: every action handler that might fire while a container is virtualized; gates run **before** vanilla super
8. **Threat model & input bounds**: sanity caps on counts, sizes, lengths from disk; bound check before allocation

Full prompts are in `deep-audit-prompts.md`. The implementer-grade prompt for step 4 is also there.

### Step 3: Adversarial verification + consolidate

> **Assignment:** follow the orchestrator's review budget. Citation checking and
> judging whether an inference follows are different checks; neither model brand proves them.
> **Done when:** every row in the deduped table has been confirmed against
> the real file (by the independent verifier or by you); the 20% self-sample
> passed (<10% confabulation); each row is labelled defect vs improvement.

This is the step that turns "agents reported it" into "it is real". It exists because skipping it once produced an audit in which about 45% of the findings were invented. Three sub-steps, in order:

**3a, Verify every cited snippet against the real file.** Open the file at the cited range and confirm it says what the agent's pasted snippet claims. Reasoning agents drift on line numbers, copy citations from sibling files, and occasionally invent plausible ranges wholesale. A finding whose snippet does not match the file is not a finding, re-derive it or drop it. Before a cause is written into lasting notes or memory, record three things: the file, the search pattern, and the number of matches it returned, which must be more than zero. A cause without those three is a hypothesis. To choose between two competing explanations, find a prediction that only the new explanation makes and check it.

**3b, Independent verifier pass.** When an independent pass is assigned, use a reviewer from another family with a **fresh context that has not seen the angle reports**. If it is unavailable, declare that limitation; do not silently claim independence. Hand it only the bare list of claims (claim + location, no reasoning, no severity). Its task: for each claim, open the cited file and return TWO separate verdicts, "does the file actually say this" (`snippet_matches_file`) and "does the conclusion follow from that code" (`inference_holds`, judged without seeing the auditor's reasoning), pasting the relevant lines. A claim the independent verifier cannot confirm on either verdict is NOT actionable until the orchestrator re-reads it, dropping it silently is how a real finding disappears. And a refutation rate of 0% is a reason to distrust the verifier, not to trust the batch: the run that produced this rule refuted 0 of 67 claims, and one claim arrived `CONFIRMED` on a false inheritance premise. This is adversarial on purpose, convergence between agents that *shared* context (the same spec, the same conventions doc) is contagion, not confirmation. The verifier must not share that context.

**3c, 20% self-sample gate.** Before trusting the consolidated table, pick 20% of the findings at random and verify them yourself by opening the files. If more than 10% of the sample is confabulated, the audit is not trustworthy, re-run step 2 with stricter prompts, or discard it. Do not act on an audit that fails this gate.

Then build the single deduped table:

| ID | Severity | Title | File:Lines | Found by | Verified by | Defect/Improvement | Status |
|---|---|---|---|---|---|---|---|

- Severity is yours to assign, do not trust the agent's self-reported severity. P0 = data-loss possible. P1 = recovery required. P2 = degraded behavior. P3 = code smell.
- **Defect vs improvement.** Defensive coding is not a bug. An `OR` branch that accepts two input formats, a tolerant parser, a redundant guard, those are robustness, not defects. Label them "improvement" at most; do not file them as findings or inflate their severity. Calling tolerance a bug was the biggest error class of an audit that skipped step 3.

### Step 4: Implementer-grade cross-actor pass

> **Assignment:** an independently assigned reviewer capable of cross-actor reasoning.
> **Done when:** the agreed product checks and review budget are satisfied. A new
> finding needs executable evidence to block. The one stop rule is in step 6;
> do not create an until-clean loop here.

This is the step that, in retrospect, would have caught the 12 VULNs.

Give the assigned reviewer a fresh context, no audit history, no agent output, no priors. Hand it the codebase, the README/spec, and this single prompt: *"Find every way this code can lose, corrupt, or silently misroute player data. Trace each writer to every reader, each sidecar to every cleanup site, each admin flag to every consumer. Where any of those triples is incomplete, that is a bug."*

Full prompt: `deep-audit-prompts.md` § "Implementer-grade pass".

The cross-actor framing matters. Reasoning agents prompted "audit this layer" look within the layer; they do not chase across actors. The implementer-grade prompt explicitly says "trace across actors".

If this agent finds nothing, that is the signal that the audit is converging. If it finds a defect, reproduce it, classify its impact, and recheck the affected path within the agreed budget. Escalate remaining work when that budget is exhausted.

### Step 5: Apply fixes

> **Assignment:** use the execution route authorized by the orchestrator.
> **Done when:** every applied fix names the check or angle that caught it;
> a re-grep confirms the pattern is gone everywhere; no fix exceeds the
> minimum verified change.

Standard editing flow, with five specifics:

- For every fix, write down which mechanical check or which agent angle caught it. If a fix has no source, it is a hunch, re-verify before shipping.
- After each fix, re-grep to confirm the bug pattern is gone everywhere (not just at the cited line). VULN-003-class bugs often have siblings.
- **Minimum verifiable patch.** Apply only what step 3 verified. When the verified instruction is "add bands X before the else", add bands X, do not also add Y, Z, W because a sibling (unverified) finding suggested them. "While I'm here" is exactly how a patch gets bloated with confabulation-derived changes.
- **Close the audit with a fix tracker.** When the audit produced findings to act on, keep a tracker file next to the findings file: one row per closeable item with its ID, severity, `file:line`, the issue, the proposed fix, the owner and a status (`open`, `in-progress`, `closed (commit, date)` or `wont-fix (reason)`). Keep the file after the last item closes. Do not create tasks in a tracker tool without asking the user.
- **Do not ship artifacts from an un-reverified audit.** Packaging a `.skill`, cutting a release, or handing the user a patch file based on findings that did not pass step 3 is how false confidence propagates. Applying a patch costs minutes; the bad release it enables costs hours.

### Step 6: Re-audit subset

> **Assignment:** mechanical checks directly; targeted reasoning under the
> same review budget and family-independence contract.
> **Done when:** mechanical pre-checks plus the two most-changed angles run
> clean (every applicable angle over the new code when a fix added new design, see below). A new finding loops back to step 5 **once**; a second reappearance stops
> the loop (hand the backlog back to the orchestrator).

Re-run mechanical pre-checks (cheap) plus the two angles whose code changed most. That is the rule for fixes that patch existing code. When a fix adds new design (a new flow, a new state, a new recovery or cleanup path), run every applicable angle over that new code as well, because its defects are in the design and a check of the changed lines cannot see them (`deep-audit-fix-traps.md`, last section). Either way the round counts toward the two-round budget below. If a new finding appears, loop back to step 5 once. If a finding of the same family reappears, the defect is design, not patching: stop, file the remainder as numbered backlog and escalate. Stop rule: the product gate closes the loop, a finding blocks only with an executable repro, and the budget is two rounds (this replaced "until zero critical or major"). When a value passes through several layers, write a test for each pair of adjacent layers that runs both real layers, with no fakes or stubs in between. Check the test by deleting the code that connects the two layers: the test must then fail. Accept the fix only when the person or agent who receives it repeats that same deletion and sees the test fail too.

## Phase B: in-game validation (step 7)

### Step 7: In-game test gate

> **Assignment:** the user runs these; the agent cannot.
> **Done when:** all four scenarios below pass in-game. Only then is
> "release-safe" earned.

A clean audit is not yet release-safe. Before declaring release-safe:

- Player connects with a virtualized container, server restart, container intact (basic round-trip)
- Crash in the middle of a virtualize (kill the server), then reboot: recovery completes, no data loss, no orphan markers
- Admin reset on a container that is virtualizing: stable state after the reset
- All sids on disk after a long session match player intent (no orphans, no ghosts)

The agent cannot run these tests for the user. The audit's contribution is to make the audit phase trustworthy enough that the in-game test phase is short.

## Anti-patterns

Watching for these saves rounds:

- **Declaring "release-safe" after step 2.** Steps 3 to 7 are not optional. Phase A alone is never "release-safe", Phase B is the gate.
- **Using eight identical agents instead of eight different angles.** Eight reasoning agents prompted "audit this code" produce eight redundant reports. The angles must differ.
- **Skipping step 1 because "the agents will catch it".** They demonstrably do not.
- **Treating defensive coding as a bug.** A tolerant `OR` branch, a redundant guard, a parser that accepts two formats, robustness, not defects. Calling tolerance a bug is the most common false finding.
- **Trusting consolidated metrics without drill-down.** "34 VERIFIED, 9 CONFABULATED" is smoke if it is a summed number with no per-finding click-through. Metrics without traceable findings are sums of guesses.
- **Acting on an audit that has not passed step 3.** The agents' report is a set of hypotheses. Adversarial verification (independent verifier + 20% self-sample) is what makes it a set of facts. No verification = do not act.
- **Trusting "convergence" between agents that shared context.** Four agents citing the same bug because they all read the same conventions doc is contagion, not confirmation. The step 3 verifier must have fresh context.
- **Re-running the same audit after fixes.** Step 6 re-runs the cheap checks plus the two angles whose code changed most; re-running all eight angles over code the fixes did not touch wastes budget. Only new design added by a fix gets every applicable angle, and only over that new code.
- **Serializing independent work after parallel delegation was authorized.** If multiple lanes are assigned, dispatch them together so they run concurrently.
- **Shipping a `.skill` / release / patch file from un-reverified findings.** Cheap to apply, expensive to walk back.
- **Reading a short-circuit finding as green.** A gate skipped on PRECONDITION (dirty tree, unreadable config) wears the same face as a pass: verify the gate evaluated what changed, and count exit codes, not findings. Verification on a dirty tree is not verification.

## On Linux

Everything above is the Windows workflow and stays valid there. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in the shared Linux and Proton notes (`skills/_shared/linux-proton.md`); this section only says what changes for this procedure.

- The search lines in the code blocks of the `deep-audit-*.md` files (`Grep "<pattern>" --type c --output_mode content -n true`) are recipes for the agent's own search tool, not shell commands, so they work the same on Linux. Outside the agent, `rg -n --type c "<pattern>"` runs the same search; build the tables by hand or with Python. Paths: forward slashes, case-sensitive file system (see the guide).
