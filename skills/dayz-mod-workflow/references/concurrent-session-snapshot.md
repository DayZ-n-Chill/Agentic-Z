# Concurrent session snapshot

What a session that uses `dayz-mod-workflow` does when the skill files may be rewritten or promoted by another session while it runs, or when it must survive a later promote to the live copy. Load this reference only in that situation.

It is the consumer's procedure only. Nothing in this file is a game fact, so it cites no vanilla file.

## What a session pin is

At session start, copy the **whole** skill tree (`SKILL.md` and every file under `references/`) from an **immutable** snapshot of the commit in use. Take it from a detached worktree added at that verified commit (`git worktree add --detach <path> <commit-ish>`) and copy the whole `skills/dayz-mod-workflow/` tree from it. When the maintenance tool's promote step has written a per-commit snapshot folder, prefer that folder. Hash each copied file (SHA-256) and read those copies for the rest of the session.

If a later step needs a reference that was not opened at the start, take it from **that same snapshot**. Do not read the live copy after a later promote.

Dependencies outside this skill are not resolved by this procedure. If there are any, choose a version (a commit or a digest) and record it.

A hash or a copied folder does not make an agent load those bytes. A later live promote does not freeze what an agent already holds in memory.

A **new** session reads the newer version only when the host is configured **and verified** to load the current copy or that snapshot. Having both versions as files is not that verification.

## How to capture

1. Identify the commit.
2. Copy the whole `skills/dayz-mod-workflow/` tree from that commit's immutable snapshot (a detached worktree added at that commit, as above).
3. Hash every copied file. Hash again before trusting the copy.
4. Do not edit the snapshot in place.

## Limits

This pin is a closure over files. It does not configure Claude Code, Codex, Gemini, Cursor or any other agent host; wiring each runtime needs its own evidence. In this repo `/sync-skills` links the repo's skill folders into each agent's home, so a linked skill follows the working tree, not a pinned commit.

Recovering a broken promote transaction (the maintenance tool's `--recover`) restores it to its recorded state before the promote. Going back to an older commit after a later apply is something else: a full check and then apply of that commit, in which you inspect every destination in the plan, and destinations that must not change keep their digest.
