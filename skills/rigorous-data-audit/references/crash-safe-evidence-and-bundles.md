# Crash-safe evidence indexes and multi-root bundle publication

Audit rules for a long-running evidence campaign, a generated final index, or a release that publishes into more than one physical root (client, server, profiles, persistence, config). Open this in step 1 when the audited work writes an authoritative index or installs a bundle across several folders.

These are audit invariants; they do not by themselves prove that a particular runtime has passed them. They concern tooling around a mod (test harnesses, installers, promotion scripts), not Enforce Script, so nothing here can be checked on `P:\`. The `CLAIM-...` ids are the source pack's claim labels, kept only for tracing.

## Authoritative evidence index

Rule `CLAIM-R21-RDA-CRASH-EVIDENCE`: a crash-sensitive runtime MUST NOT append directly to its authoritative final index.

Audit for this sequence:

1. Give each logical event a stable logical identity and each physical write a distinct attempt ID.
2. Materialize a create-only temporary event file, durably write it, re-read and verify it, then atomically rename it to an absent final path.
3. Aggregate event files order-independently and fail closed when duplicate logical identities disagree.
4. Publish the final JSONL or index create-only once, after a quiescent close. It must represent `FAIL` and `INCOMPLETE`, not only successful completion.
5. Fault both sides of every write, flush, re-read and rename boundary.

An append-only final file without a verifiable event set can be truncated, duplicated or left internally plausible after termination.

## Publication across physical roots

Rule `CLAIM-R21-RDA-MULTIROOT-PUBLISH`: a bundle spanning client, server, profiles, persistence or config roots is not one atomic filesystem update.

Require:

- exact PRE and POST manifests;
- same-volume staging and archive capacity for every root;
- an append-only `PENDING` / `COMMIT` / `ABORT` journal;
- launch refusal while a transaction is `PENDING`;
- `COMMIT` only after every POST hash matches;
- `ABORT` only after every PRE hash, or first-install absence, is restored;
- termination injection at each materialize, archive, publish, verify and receipt boundary, in both forward and rollback directions.

If the product contract fixes canonical launch paths, generation directories are staging and archive only; they must not silently replace the active arguments.

## Crash-recovery audit refinements

Rule `CLAIM-R21-RDA-PROMOTION-RECOVERY-REFINEMENTS`: for a recoverable multi-root publisher, also audit these less obvious boundaries:

1. Publish the transaction root only after its sealed plan and first durable `PENDING` event exist. A visible directory without authoritative evidence is not a recoverable transaction.
2. Define digest identity per artifact kind. A standalone file digest must represent its bytes, not a source basename that can legitimately change at the destination.
3. Separate historical terminal validation from live-target adjudication. Verify every old chain and receipt, but do not require current targets to remain forever at an older committed generation.
4. Give each retry a distinct attempt or transaction ID. Reusing the same ID after a clean `ABORT` turns valid terminal evidence into a permanent retry poison.
5. Revalidate sealed contracts and logical and physical bindings after acquiring all locks. Repeat the compare-and-swap check on the target before backup, before moving the target, and immediately before `COMMIT`.
6. Treat unknown target content as foreign evidence. Never delete, archive or restore over a digest that is neither the sealed PRE nor POST.
7. Do not write a diagnostic report inside a transaction root until its path, sealed plan and event chain are trusted.
8. Reject or explicitly preserve nested symlink and junction semantics in payload, backup and recovery sidecars; materializing a link target is not equivalent to restoring the link.
9. Keep lock metadata outside the protected content boundary. If an allowed physical root can equal the promoted target, `root/.lock` changes the digest it is meant to protect and an exclusive lock may make its own readback fail.
10. Use one path-ordering rule for the sealed source projection and the materialized tree readback. Host path semantics can order `SKILL.md` and `references/...` differently from raw string sorting, making a valid source impossible to verify after staging.
11. Treat platform rename denials as an adjudicated boundary. Retry only known transient codes, for a bounded interval, and only while source and destination still prove the prior attempt did not create an ambiguous state. Preserve a path-free OS error code for diagnosis; never turn a retry into a second blind mutation.
12. Preserve read-only payloads without making durability depend on a permanent metadata change. On Windows, `fsync` requires a write-capable descriptor: make only the unpublished copy temporarily writable, flush it, and restore its original mode even when the flush fails. Never mutate the source to make backup creation succeed.
13. Make residue cleanup obey the same adjudication boundary. Verify that a stage, archive or recovery sidecar has an allowed digest before deletion; then clear read-only only on the path being removed. Retry neither unrelated permission denials nor unknown content.

These checks need fixtures for successive generations, retry after `ABORT`, failure during transaction initialization, contract mutation while waiting for locks, mutation after backup, renamed standalone-file snapshots, a lock root equal to its target, mixed-case projected paths, transient and ambiguous renames, read-only copies, read-only sidecar cleanup, and invalid transaction roots.

## Evidence

Verification level: the mechanism was cross-checked against its source contract and exercised by offline termination and recovery tests, 2026-07-24.

The anchors were:

- two plans of the source author's private Utopia PC Suite project (the phase 0a foundation plan and the phase 0b dedicated persistence plan, both dated 2026-07-22), which are not part of this repo;
- the source pack's own promotion tool, `packctl` (its `common` and `promotion` modules and its promotion tests). Workstream 7 of the import brings that tool into this repo; the rules above are the audit invariants its recovery code was written against.
