# Traps when fixing saved data code

What goes wrong when fixes to a mod's save, load and recovery code are applied (steps 5 and 6 of `deep-audit.md`): a hardened contract that misses a sibling call site, a fix that trusts another process's id, two correct fixes that break each other, a fix applied to generated output, and a fix whose new design is never checked. Open it before applying fixes and before the second pass.

These traps come from mod code, not vanilla. For the DayZ facts an audit assumes, see `deep-audit.md`, step 1; the base class save and load hooks and their data width are at `P:\scripts\3_game\entities\entityai.c:2912` to `:2948`.

## A hardened contract must reach every sibling call site

When a change makes a function return a bool with a gate on it, adds a "verify before durable" rule (check the sidecar before calling the data saved), or makes a path fail closed, the usual defect is not a wrong fix but a missed site. N-1 of N branches get the new contract and one does not: a restore failure handler that does not clear the flag and sidecar its sibling terminal paths clear, a migration that gets a file filter its orphan promotion lacks, a reset that skips the checked gate that retry and recover use.

Add this to the mechanical checks whenever a change hardens a contract:

- Grep every call site of the changed symbol and of its sibling or opposite operation: the success path, every failure or early return branch, the synchronous or shutdown shortcut, the admin variant and the boot reconcile variant.
- Confirm each one consumes the new contract: it checks the bool, clears the same flag and sidecar, or runs the same gate. List the branches mechanically; do not judge them by eye.

A leftover file on disk (a stale sidecar or marker) is dangerous only if the boot or recovery scan lists it. A sidecar whose enumerating glob no longer matches it is inert, so check the enumerator before rating the finding.

When the missed site moves to a terminal or admin blocking state (quarantine) and its failure branch protects a marker or payload against loss, do not reorder the flow to gate the durable write on the newly checked contract. A reorder can route the failure path into a branch that deletes the marker or purges the payload, a worse loss than the one being closed. Consume and retry the contract and keep the durable write where it was. Read the whole failure branch of the site you touch, and check the changed handler again after the fix.

## An id from another process: check its lifetime, not only its value

When a fix uses an id issued by another process as the key for a destructive operation, proving that two ids are equal today is not enough. Answer each of these with a cited line first:

- Who issues the id, and from which counter?
- Does that counter reset (per process, session, mission or restart)?
- Who keeps the map that resolves it, and when is that map cleared?
- Can the two lifetimes drift apart, and what happens when the id no longer means what it meant?

An issuer that restarts its counter at 1 on every start, paired with a map on the other side that lives as long as the host process, makes a "compensating" delete hit an entity from another session. If any answer lacks a citation, do not run the destructive operation: log and report it. A test fixture never assigns ownership fields directly; a test gets an owner only through the product operation with a real lease.

Check the order on the other process too. A spawn that is always queued while a delete without a spawn is dispatched at once lets the compensation run before the spawn it undoes, and creates the orphan it was meant to prevent.

## Check pairs of fixes, not only each fix

Two fixes that are each right can fail together. A dry run that stops calling sweep is right, and a startup step that adds a trailing newline to a ledger is right; but if the only repair of a broken ledger tail lives inside sweep, the newline closes the broken line without discarding it, the next append lands after it, `replay()` always raises, and the ledger stays unreadable for good.

In the second pass, for each pair of fixes ask whether one disables a path the other depends on, above all when one adds a guard (`if not X: ...`) and the other touches the resource the guarded path repaired or cleaned. Above four fixes, list the pairs mechanically.

## Generated output is not the place to fix

First decide whether the tree under audit was produced by a tool (a transformer, code generator, build or migration) with a manifest, a contract or pinned hashes. Look for `*-receipt.json`, `contract*.json` or `*manifest*.json` next to it, and a `--verify` option on the tool. If they are there:

1. Apply the fix to the generator's source, then regenerate the contract and its hash, run the tool again from a clean tree, and repack the PBO. Keep the previous artifact apart as evidence.
2. Never loosen a gate so the fix passes. Tighten it instead (two exact counts of 1 rather than one count of 2), add a check for anything the fix removes, and prove each touched gate can fail: break the source, run the tool, require a non-zero exit with the expected message, restore the source, and confirm the restore is byte-identical.
3. Tell the user the full cost before they approve which fixes to make: the contract, the hash, the rerun, the repack and possibly a new measurement. The cost changes which findings are worth fixing.
4. A finding whose fix would touch a hash-pinned region is not fixed in code. Document it, or close it with a line in the test procedure.

## A fix that adds design is checked like new code

A fix that patches existing lines gets the mechanical checks and the two angles whose code changed most. A fix that adds design (a new flow, state, recovery or cleanup path) is the exception `deep-audit.md` step 6 names: run every angle that applies over its new code, within the same two-round budget. Its defects sit in the design, such as a clear after reapply that breaks another path's guarantee, or an alias in a buy, withdraw and restart flow that leaves an in-game terminal blocked for good, and a check of the changed lines cannot see them.

Write down, with such a fix, the scenarios that would prove its design wrong, and check each one before calling it done. Keep the stop rule of step 6: runnable criteria, bounded rounds and a stated way to hand back what is left; never "no new findings" as the bar.
