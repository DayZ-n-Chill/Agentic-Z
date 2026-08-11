---
title: Security Model
---

# Security Model

Agentic-Z hands AI agents real power over your machine — they build files, delete build artifacts, and launch game processes. That only works if the blast radius is controlled. This page explains the guardrails, layer by layer, so you know exactly what an agent in this stack can and cannot do.

The philosophy is three tiers, applied in order:

1. **Allow** a short list of known-safe, repo-versioned operations to run without friction.
2. **Prompt** for everything else — the default for any command not on the list.
3. **Hard-deny** the catastrophic, so it can't even be approved by accident.

No security theater. Every rule below exists because it blocks a real failure mode, not to look thorough.

## Layer 1 — the permission wall

The repo ships a `permissions` block in `.claude/settings.json` that every clone inherits.

**What's allowed to run without asking:** only scripts that live inside the repo itself — `python .claude/skills/...`, `python scripts/...`, the `scripts/*.bat` wrappers, and the read-only `dayz-rag` search tools. Everything an agent can auto-run is code you can read, version, and diff. Nothing outside the repo is pre-approved.

**What's explicitly denied — even if you try to approve it:**

| Denied | Why |
|---|---|
| `python -c` / `python -m`, `node -e` / `node -p` | Arbitrary inline code evaluation — the escape hatch around the "only repo scripts" rule. Skills ship real script files instead. |
| `npm install <package>`, `npx` | Supply-chain guard. An agent can restore the lockfile (`npm ci`), but it cannot pull new packages onto your machine. |
| `format`, `diskpart`, `Format-Volume`, `Clear-Disk` | Disk-destroying commands. These have no legitimate use in a modding workflow, so they are un-approvable — a tired misclick at 2 a.m. cannot green-light them. |

**Everything else prompts you.** An agent that tries `Remove-Item` on some random path, a `git push --force`, or any command not on the allow list stops and asks. The deny list is short on purpose: prompting already covers the long tail, and denies are reserved for commands where even an accidental approval would be unrecoverable.

## Layer 2 — guarded destructive operations

The skills that delete things don't trust themselves. Four independent guards:

**Ownership markers.** Every folder the tooling deploys to `P:\Mods\` gets a marker file (`.agentic-z-scaffold`) recording which mod owns it. The cleanup skills (`/dayz-clean-workspace`, `/clean-repo`) and the deploy skill refuse to touch any folder without a matching marker — your subscribed Workshop mods and hand-placed folders are structurally undeletable by the tooling. If it didn't create it, it won't remove it.

**Junction-aware deletion.** Mods imported from elsewhere on disk are linked, not copied. Every delete path in the tooling removes the *link* without recursing into the folder behind it — so cleaning your workspace can never reach into an external mod's real source directory.

**Confirmation and dry-runs.** The wipers require an interactive yes (or an explicit `--yes` flag) and offer `--dry-run` so you can see the exact removal list before anything happens.

**The model can't self-invoke the heavy skills.** `/dayz-clean-workspace`, `/clean-repo`, and `/dayz-cot-bootstrap` (which kills processes and edits server permission files) are flagged `disable-model-invocation` — they run only when a human types the slash command. An agent reasoning its way toward "I should clean up" cannot pull that trigger itself.

Process control is scoped the same way: the test-session killer targets only `DayZDiag_x64.exe` by exact image name. It cannot sweep processes by pattern or PID.

## Layer 3 — agent containment

**Minimal tool grants.** Each specialist agent declares exactly the tools its job needs. The reviewer and debugger — read-only roles — have no file-writing tools. The asset specialist has no process-launching tools. An agent can't misuse a capability it was never handed.

**Per-mod fencing.** `/dayz-scope-mod` adds deny rules that block an agent from editing any *other* mod's workspace folder, `P:\` junction, or deploy directory. Working on Mod A with an agent that hallucinates about Mod B? Mod B is untouchable. Reads stay broad so context isn't crippled; only writes are fenced.

**Local-first knowledge.** The `dayz-rag` semantic search runs against a local vector index of vanilla DayZ source on your own disk. Queries don't leave your machine except for the embedding call, and search results are game source code — not live web content that could smuggle instructions to the agent.

## What this does — and doesn't — protect against

This model is built to stop **accidents and runaway automation**: an agent misjudging a path, a destructive command approved on reflex, a cleanup that reaches further than intended, a skill invoked in a context its author never imagined.

It is not a sandbox against a malicious operator, and it doesn't make third-party code trustworthy. If you add your own skills or pull someone else's fork, read what you're running — the permission wall only vouches for scripts it can see in this repo.

Found a hole? Open an issue on the repo — security reports get priority.
