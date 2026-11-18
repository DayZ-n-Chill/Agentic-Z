# Traps when fixing and auditing again

What goes wrong in steps 5 and 6: a hardened contract that misses a sibling call-site, a fix that trusts another actor's id, two correct fixes that break each other, a fix applied to generated output, and a corrective that is never audited itself. Open this before applying fixes and before the second audit pass.

These are process lessons from third-party projects and cite no vanilla code of their own. For the DayZ facts an audit assumes, see `deep-audit.md`, step 1; the base class data width is at `P:\scripts\3_game\entities\entityai.c:2912-2948`.

## Delta-contract propagation: a step 1 check when the trigger is "make it fail-closed"

Case: the pre-release audit of a virtual storage mod. The change under review hardened durability contracts: a signature changed to return a bool with a gate on it, and "verify the sidecar before declaring the data persisted". Five of about nine real findings, including both release blockers, were not cases of the fix being wrong but of the fix missing at a sibling call-site. `HandleRestoreFailure` did not clear the flag and sidecar that its three sibling terminal paths cleared. `MigrateLegacyTmp` got the `isCanonicalTmp` filter but `PromoteOrphanTmp` did not. Retry and recover got the checked `ClearFor` gate but `reset` did not. The success branch of DropQueue was untracked but its two fail-closed branches were not. The eight structural angle auditors under-weight this, because each one reads its own layer's canonical path, while the whole point of a fail-closed delta is that it touches many sites.

Add this to step 1 (mechanical pre-checks) whenever the delta changes a signature to return a bool, introduces a "verify before durable" contract, or propagates a fail-closed gate:
- Grep every call-site of the changed symbol and of its sibling or opposite operation that should now share the contract: the success path, every failure or early-return branch, the sync or shutdown shortcut, the admin variant and the boot-reconcile variant.
- For each one, confirm that it consumes the new contract: it checks the bool, clears the same flag and sidecar, or runs the same gate. The dominant failure mode is asymmetry: N-1 of N branches are updated and one is missed. Enumerate the branches mechanically; do not eyeball them.
- This is a delta check (it enumerates the fan-out of the changed symbol) and complements the five structural checks. Run it first when the audit trigger is "someone hardened contracts".

Corollary (resolving a contradiction): when two auditors disagree about whether an orphaned on-disk artifact (a stale sidecar or marker) is dangerous or inert, the decisive question is whether the boot or recovery scan enumerates it. A sidecar whose primary enumerator glob (for example `*.lfv`) is gone is inert even though it survives on disk, so check the enumerator before rating severity.

Caveat when applying the propagation (step 5): if the missing call-site moves to a terminal or admin-blocking state (QUARANTINE, quarantine-orphaned) and its failure branch contains a hard gate (preservation of a marker or payload that prevents data loss), do not reorder the flow to gate the durable write on the newly checked contract. A reorder can route the failure path into a branch that deletes the marker or purges the payload, and so create a worse data loss than the one you were closing. Prefer to consume and retry the contract while keeping the durable write in its original position. Verify the whole `else` or failure branch of the site you touch, not just the happy path. Case: a reorder of a degraded-partial handler introduced a path that deleted the `.lfv` file at the maximum failure count; the adversarial reviewer caught it in the round after the "fix", and the first apply attempt did not. Corollary: after a propagation fix, re-run the adversarial verify pass (steps 3 and 4) on the changed handler, because an apply can introduce a regression worse than the finding.

## Two things the audit must check that no single angle covers

Case: an admin tool mod (a dual cross-family review plus this procedure). The code entered with two independent UNSOUND verdicts and emerged with 19 fixes. The two most severe findings of the day **were not in the code being audited**: they were in the fixes written that very day. None of the 8 angles would have found them, because all 8 angles look at the system, not the patch.

### 1. A reused identifier is verified by its lifecycle, not by its equality

The first check is that the symbol exists. The second is the meaning of a helper you reuse. The missing third check is the one that bites in two-process systems: when a fix uses an identifier issued by another actor, verifying that the equality holds is not enough; you must also verify how long that equality lives and who resets the counter.

Real case: to delete an orphaned entity, a fix reused the `command_id` returned by enqueue, after verifying in the server code that `object_id == command.id`. That was true and cited with `path:line`. What was not verified: the issuer of those IDs resets its counter on every startup (`self._next_id = 1`) and reaps itself after 30 minutes idle, while the map that indexes them on the other side is never cleared as long as the host process lives. With recycled IDs, the "compensating" deletion points to an entity from another session. A fix meant to leave no garbage could destroy work in progress.

**Mandatory questions before accepting a foreign ID as the key for a destructive operation**: who generates it and with which counter; whether that counter resets (per process, session, mission or reboot); who maintains the map that resolves it and when that map is cleared; whether those two lifecycles can drift apart; and what happens if the ID no longer means what it meant. If any of these lacks a cited answer, **do not perform the destructive operation**: log and report it, and never delete blindly. A fixture never assigns ownership fields: a grep for assignments to `owner_*` in test helpers must find nothing, and the only way a test gets an owner is through the product operation with a real lease.

A corollary from the same case: also verify the execution order on the other actor. There, a `spawn` was always deferred to a queue while a `delete` of a batch without a spawn was dispatched immediately, so the compensation could run before the spawn it was meant to undo and create the permanent orphan it was meant to prevent.

### 2. Step 6 looks for interactions between fixes, not just defects in each fix

Step 6 says "re-run the angles whose code changed most". That is not enough: it invites re-auditing each fix on its own, while the defect appears in the combination of two correct fixes.

Real case, with two fixes that were both correct and both had a proven failing test: (a) "in dry-run, do not call sweep", which was correct because sweep changed the world in a mode advertised as safe; (b) "on startup, guarantee a trailing newline on the ledger", which was correct because a merged append had broken the contract for a live entity. Together they failed: the only repair of a broken tail lived inside sweep, which fix (a) had just disabled in dry-run, and fix (b) closed the broken line without discarding it, so the next append landed after it and that line was no longer the last. The result: `replay()` always raised and the ledger stayed **permanently unreadable**. No later startup could even run sweep.

**Add this to step 6 explicitly**: for each pair of fixes in the batch, ask whether one **disables a path that the other depends on**, especially when one fix adds a guard (`if not X: ...`) and another touches the resource that the guarded path repaired or cleaned. Enumerate the pairs mechanically if the batch has more than four fixes; the guilty pair is rarely the one you suspect.

## When the audited tree is the output of a generator, step 5 does not edit the tree

Case: a power grid mod. The audit produced 3 fixes of 3 lines within a delta of 24, and applying them seemed trivial. It was not: the candidate tree was the output of a fail-closed transformer, with a tree manifest and a contract pinned by SHA-256, and the lines to change were the transformer's Python literals, gated by exact counts (`count('"key"') != 2 -> fail`). Editing the tree would have broken the manifest and made the fix impossible to reproduce.

**Add this to step 1 (mechanical pre-checks) as question zero**: first determine whether the audited tree is the output of a tool (a transformer, code generator, build or migration) with a manifest, a contract or pinned hashes. Look for `*-receipt.json`, `contract*.json` or `*manifest*.json` next to the tree, and for a `--verify` option in the tool that produced it. If they are present, the tree is not the surface to edit.

**Consequences, in order**:

1. **The fix is applied to the generator's literal**, not to the artifact. Then regenerate the contract and its SHA, re-run `analyze -> apply -> verify` from a clean tree, and re-seal the artifact (PBO or package). Keep the previous artifact separately as evidence.
2. **Re-anchoring gates is the failure mode this procedure exists to prevent.** A gate changed so that it accepts your fix is a loosened gate. Rule: always re-anchor more strictly (two exact counts of 1 instead of one count of 2), add a non-regression gate for each check the fix removes, and **turn every touched gate red on the same day**: tamper with the literal, run the tool, require an exit code other than 0 with the expected token, restore the literal, and verify that the restore is byte-identical.
3. **State the cost before the user approves the scope of the fixes.** The real cost is not "editing N lines": it is the contract, the SHA, the re-run, the re-sealing and possibly a new measurement. It changes which findings are worth fixing. In the original case, two of the four approved fixes changed shape once the cost was known, and one could not be applied at all.
4. **A finding whose fix would require touching a hash-pinned region of the contract is not fixed.** It is documented, or turned into a procedural note. In the original case, the relocated body was byte-identical by design and pinned, so the finding "a debug hook was left duplicated in two files and a tester may edit the one that does not compile" was closed with a line in the test procedure, not with code.

## A corrective is unaudited input: audit its new code again, never only the delta

**For a fix that patches existing code, step 6 re-runs the mechanical checks and the two most-changed angles. A corrective that adds new design (a new flow, state or recovery path) is the exception `deep-audit.md` step 6 names: its new code is audited as if it were a fresh round, within the same two-round budget.**

**Evidence.** A corrective bundle passed its receiver, a crash-recovery walk and the compile gate, and closed the findings of six review lanes. Re-running the multi-angle audit against **its own new code** then found two new criticals and one blocker, all of them **defects in the corrective's design rather than its implementation**: a clear-after-reapply that broke the guarantee of an alternate path, and an alias in the canonical buy/withdraw/restart flow that left the in-game ATM permanently blocked. Four of five independently re-launched auditors converged on the same alias without contact. It was the fourth instance of the same shape in one campaign, which is what makes it a rule rather than an anecdote.

**Apply in step 6:**

1. **Re-launch every applicable angle over the new code** of a corrective that adds design, rather than only checking that the fixes landed. The round-two findings were in the corrective's design, so a delta-only check could not have seen them. Resumed agents work here and cost roughly 30% of a fresh run, provided they are told explicitly that their cached content is stale.
2. **The corrective's prompt carries its own counter-scenarios** -- the scenarios that would refute its design -- and the implementer verifies and documents them as part of RED->GREEN. Treat the arbitration's design as unaudited input. In the case above, the counter-scenarios that were embedded got verified; the one that was not embedded is the one the re-audit had to catch.
3. **Use the single loop budget established before review.** Follow the stop rule of step 6: executable product criteria, bounded rounds and an explicit escalation outcome. Do not substitute a zero-new-findings requirement.
