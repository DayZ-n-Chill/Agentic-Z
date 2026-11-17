# Traps when fixing and auditing again

What goes wrong in steps 5 and 6: a hardened contract that misses a sibling call-site, a fix that trusts another actor's id, two correct fixes that break each other, a fix applied to generated output, and a corrective that is never audited itself. Open this before applying fixes and before the second audit pass.

These are process lessons from third-party projects and cite no vanilla code of their own. For the DayZ facts an audit assumes, see `dayz-persistence-facts.md`.

## Delta-contract propagation: a step 1 check when the trigger is "make it fail-closed"

Origin: LF_VStorage 1.5.0 pre-release audit. The change under review hardened durability contracts (signature -> bool + gate on it; "verify sidecar before declaring persisted"). 5 of ~9 real findings, including BOTH release blockers, were not the fix being wrong but the fix MISSING at a sibling call-site: `HandleRestoreFailure` didn't clear the flag+sidecar its 3 sibling terminal paths cleared; `MigrateLegacyTmp` got the `isCanonicalTmp` filter but `PromoteOrphanTmp` didn't; retry/recover got the checked `ClearFor` gate but `reset` didn't; DropQueue's success branch untracked but its 2 fail-closed branches didn't. The 8 structural angle-auditors under-weight this, each reads its own layer's canonical path, yet the whole point of a fail-closed delta is that it touches MANY sites.

Add to Step 1 (mechanical pre-checks) whenever the delta changes a signature to bool, introduces a "verify-before-durable" contract, or propagates a fail-closed gate:
- Grep EVERY call-site of the changed symbol AND its sibling/opposite operation that should now share the contract: the success path, EVERY failure/early-return branch, the sync/shutdown shortcut, the admin variant, the boot-reconcile variant.
- For each, confirm it consumes the new contract (checks the bool / clears the same flag+sidecar / runs the same gate). Dominant failure mode is asymmetry: N-1 of N branches updated, one missed. Enumerate the branches mechanically, do not eyeball.
- This is a DELTA check (enumerate the changed symbol's fan-out), complementary to the 5 structural checks; run it FIRST when the audit trigger is "someone hardened contracts".

Corollary (contradiction resolution): when two auditors disagree whether an orphaned on-disk artifact (stale sidecar/marker) is dangerous or inert, the decisive question is whether the boot/recovery scan ENUMERATES it. A sidecar whose primary enumerator glob (e.g. `*.lfv`) is gone is inert even though it survives on disk, check the enumerator before rating severity.

Caveat when applying the propagation (step 5): if the missing call-site transitions to a terminal/admin-blocking state (QUARANTINE, quarantine-orphaned) and its failure branch contains a HARD-GATE (marker/payload preservation that prevents data loss), do NOT reorder the flow to gate the durable write on the newly-checked contract. Reordering can route the fail path into a marker-deleting / payload-purging branch and CREATE a worse data-loss than the one you were closing. Prefer consume+retry of the contract with the durable write kept in its ORIGINAL position. Verify the ENTIRE `else`/failure branch of the site you touch, not just the happy path. Origin: a reorder of a degraded-partial handler introduced an `.lfv`-deleting path at MAX failures; the adversarial reviewer caught it on the round after the "fix", the first apply attempt did not. Corollary: after a propagation fix, re-run the adversarial verify pass (Step 3/4) on the CHANGED handler, because an apply can regress worse than the finding.

## Two things the audit must check that no single angle covers

Origin: the GameMaster project (a dual cross-family review plus this skill). The code entered with two independent UNSOUND verdicts and emerged with 19 fixes. The two most severe findings of the day **were not in the code being audited**: they were in the fixes written that very day. None of the 8 angles would have found them, because all 8 angles look at the system, not the patch.

### 1. A reused identifier is verified by its lifecycle, not by its equality

The basic check is that the symbol exists. Lesson LL-222 extended it to the semantics of a helper you reuse. Missing is the third step, which is the one that bites in two-process systems: when a fix uses an identifier emitted by ANOTHER actor, verifying that equality exists **is not enough**; one must verify **how long** that equality lives and **who resets the counter**.

Real case: to delete an orphaned entity, `command_id` returned by enqueue was reused, after verifying in server code that `object_id == command.id`, true, cited, with `path:line`. What was not verified: issuer of those IDs **resets its counter on every startup** (`self._next_id = 1`) and auto-reaps on idle at 30 min, while map indexing them on other side **is never cleared** as long as host process lives. Recycled IDs ⇒ "compensatory" deletion points to an entity from another session. A fix intended to leave no garbage could destroy work in progress.

**Mandatory questions before accepting a foreign ID as key for a destructive operation**: who generates it and with which counter · does that counter reset (process, session, mission, reboot) · who maintains map resolving it and when is it cleared · can those two lifecycles get desynchronized · what happens if ID no longer means what it meant. If any lacks a cited answer, **the destructive operation is not performed**: log and report, never delete blindly. A fixture never assigns ownership fields (LL-446): grep for assignments to `owner_*` in helpers must yield zero; the only path to owner in tests is product operation with real lease.

Corollary of same case: also verify **execution order** on other actor. There, a `spawn` is always deferred to a queue and a `delete` of a batch without spawn is dispatched immediately, so compensation could outrun spawn it intended to undo and create the permanent orphan it came to prevent.

### 2. Step 6 looks for interactions between fixes, not just defects in each fix

Step 6 says "re-run angles whose code changed most". Insufficient as it sounds: it invites re-auditing each fix separately, and defect appears in the **product** of two correct fixes.

Real case, two fixes both correct and both with proven failing test: (a) "in dry-run do not call sweep", correct, sweep mutated the world in a mode advertised as safe; (b) "on startup, guarantee trailing newline on ledger", correct, a merged append caused loss of contract for a live entity. Together: only broken-tail repair lived INSIDE sweep, which (a) had just disabled in dry-run, and (b) closed broken line without discarding it, so next append fell behind it and that line ceased being last. Result: `replay()` always raised and ledger remained **permanently unreadable**. No subsequent startup could even sweep.

**Add to Step 6, explicitly**: for each pair of fixes in batch, ask if one **disables a path that the other depends on**. Especially when one fix adds a guard (`if not X: ...`) and another touches the resource that path repaired or cleaned. Enumerate pairs mechanically if batch exceeds four fixes; guilty pair is rarely the one suspected.

## When the audited tree is the output of a generator, step 5 does not edit the tree

Origin: the LFPowerGrid mod (entry SP-367). Audit produced 3 fixes of 3 lines within a delta of 24. Applying them seemed trivial. It was not: candidate tree was output of a fail-closed transformer with tree manifest and contract pinned by SHA-256, and lines to touch were its Python literals, gated by exact counts (`count('"key"') != 2 -> fail`). Editing tree would have broken manifest and made fix irreproducible.

**Add to Step 1 (mechanical pre-checks), as question zero**: first of all, determine if audited tree is output of a tool (transformer, codegen, build, migration) with manifest, contract, or pinned hashes. Look for `*-receipt.json`, `contract*.json`, `*manifest*.json` alongside tree, and a `--verify` in tool that produced it. If present, the tree is NOT the edit surface.

**Consequences, in order**:

1. **The fix is applied to generator literal**, not artifact. Next: regenerate contract and its SHA, re-run `analyze -> apply -> verify` from clean tree, and re-seal artifact (PBO/package). Previous artifact is preserved separately as evidence.
2. **Re-anchoring gates is the failure mode this skill exists to prevent.** A gate that is touched so it accepts your fix is a loosened gate. Rule: ALWAYS re-anchor stricter (two exact counts of 1 instead of count of 2), add a non-regression gate for each check the fix removes, and **test every touched gate in red on the same day**, tamper the literal, run tool, require exit != 0 with expected token, restore, and verify that restore is byte-identical.
3. **State cost BEFORE user approves scope of fixes.** Real cost is not "editing N lines": it is contract + SHA + re-run + re-sealing + possible re-measurement. It changes which findings are worth fixing. In origin case, two of four approved fixes changed shape once cost became known, and one became inapplicable.
4. **A finding whose fix would require touching a hash-pinned region in contract is not fixed.** It is documented, or turned into a procedural note. In origin case, relocated body was byte-identical by design and pinned: finding "debug hook was left duplicated in two files and tester may edit the one that does not compile" was closed with a line in test procedure, not code.

## A corrective is unaudited input: audit its new code again, never only the delta

**Step 3 says "re-audit until zero critical/major". It did not say that the corrective's own code must be audited as if it were a fresh round.** It must.

**Evidence.** A corrective bundle passed its receiver, a crash-recovery walk and the compile gate, and closed the findings of six review lanes. Re-running the multi-angle audit against **its own new code** then found two new criticals and one blocker, all of them **defects in the corrective's design rather than its implementation**: a clear-after-reapply that broke the guarantee of an alternate path, and an alias in the canonical buy/withdraw/restart flow that left the in-game ATM permanently blocked. Four of five independently re-launched auditors converged on the same alias without contact. It was the fourth instance of the same shape in one campaign, which is what makes it a rule rather than an anecdote.

**Apply, appended to Step 3:**

1. **Re-launch every applicable angle over the NEW code**, not "check that the fixes landed". The round-two findings were in the corrective's design, so a delta-only check could not have seen them. Resumed agents work here and cost roughly 30% of a fresh run, provided they are told explicitly that their cached content is STALE.
2. **The corrective's prompt carries its own counter-scenarios** -- the scenarios that would refute its design -- and the implementer verifies and documents them as part of RED->GREEN. Treat the arbitration's design as unaudited input. In the case above, the counter-scenarios that were embedded got verified; the one that was not embedded is the one the re-audit had to catch.
3. **Use the single loop budget established before review.** Follow the stop rule of step 6: executable product criteria, bounded rounds and an explicit escalation outcome. Do not substitute a zero-new-findings requirement.
