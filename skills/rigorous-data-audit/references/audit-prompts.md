# Audit prompts: eight angles, independent verifier, implementer-grade pass

The text to paste into each review of a data audit: a shared preamble, one prompt per audit angle (step 2), the independent verifier prompt (step 3b) and the implementer-grade prompt (step 4). Open this when a step of `SKILL.md` says "full prompt".

The prompts were written for the LF_VStorage audit, so they name its states, its file suffixes (`.lfv`, `.virtualizing`, `.restoring`) and its helper `IsVirtualized()`. Replace those with the audited mod's own names before pasting. The file and hook names the prompts list are checked against the vanilla scripts in the last section.

Each angle review gets a fresh context, no output from another review, and the same shared preamble. `SKILL.md` step 2 treats the eight angles as coverage dimensions, so one reviewer may cover several, and the orchestrator decides how many reviewers run. The independent verifier prompt runs after the angle reviews report, on a reviewer that has **not** seen their context: it is the adversarial check that turns a reported finding into a verified one. The implementer-grade pass runs after consolidation, in step 4.

## Shared preamble (paste into every angle prompt)

```
You are auditing a data-critical DayZ mod. A bug here means lost player
progression. Your job is to find bugs, not to write fixes.

Codebase root: <absolute path>
README / spec: <path or contents>
Mechanical pre-check findings (already known, do not re-find):
<bullet list from step 1>

Constraints on your report:
- ≤700 words
- Every finding pastes the literal code snippet it is about, with
  path:line_start-line_end. Show, don't tell: a claim of the form "this
  code has bug X" must include the actual code. A finding without a pasted
  snippet is a hypothesis, not a finding: it will be dropped in verification.
- Severity per finding: P0 (data loss possible) / P1 (recovery required) /
  P2 (degraded behavior) / P3 (code smell). Be honest, do not inflate.
- Distinguish a defect from a possible improvement. Defensive coding (a
  tolerant parser, a redundant guard, an OR branch that accepts two formats)
  is robustness, not a bug. Do not report it as a finding.
- No narrative, no "I noticed". Findings are bullets with title + pasted
  snippet + location + reasoning + severity.
- If you find nothing in your angle, say so plainly. Do not pad.
```

## Angle 1: persistence and atomic flow

```
Focus only on the persistence module(s) and atomic write flow. Audit:

1. Write barrier ordering: tmp → fsync → rename. Any place that skips
   fsync, or renames before fsync, is a finding.
2. Backup rotation correctness: bak1 → bak2 must happen before tmp →
   primary, otherwise a crash during rotation loses both backups.
3. Footer/header verification on read: every reader must verify both
   before trusting the body.
4. PromoteBackup label-based dispatch: each label (tmp/bak1/bak2) must
   route to the appropriate verification depth. Full file verification
   for tmp; header-only is acceptable for bak1/bak2 only if the backups
   themselves were verified at write time.
5. Partial-write recovery: what does the boot scan do when it finds a
   tmp without a primary? A primary smaller than the header? A bak1
   newer than the primary?

Report findings as bullets with severity.
```

Point 1 names the general pattern. Enforce Script has no rename and no fsync (see "What the vanilla scripts offer" below), so in a DayZ mod read it as: close the temp file, verify it, back up the old primary, then `DeleteFile` and `CopyFile`, then verify the copy. Any code or comment that calls that replace atomic is a finding (`dayz-persistence-facts.md`).

## Angle 2: state machine

```
Focus only on the container state machine. Audit:

1. Every defined state (IDLE / VIRTUALIZING / VIRTUALIZED / RESTORING /
   RESTORED / QUARANTINE / QUARANTINE_ORPHANED: adapt to actual states).
2. Every transition: which function performs it? Is it guarded?
3. For each "should never happen" branch: can it actually never happen?
   Identify the precondition that prevents it; if you cannot identify a
   precondition, treat it as a finding.
4. Re-entry: can the same sid enter the same state twice without an
   intervening reset? If yes, what happens to the previous state's
   in-flight work?
5. Compare the implemented transitions against the documented ones in
   the spec. Any divergence is a finding.

Report findings as bullets with severity.
```

## Angle 3: async queues and cross-tick safety

```
Focus only on multi-tick work queues (virtualize, restore, drop, batch).
Audit:

1. Re-entry on the same sid: can sid X be queued twice? What happens?
2. Cancellation: can a queued item be cancelled mid-batch? Does
   cancellation leave on-disk state consistent?
3. Iteration mutation: any place that iterates a queue while a callback
   inserts into it. Look specifically at shutdown drain code and admin-
   triggered queue flushes.
4. Shutdown drain: does the server-stop path actually wait for the queue
   to empty, or does it kill mid-batch and rely on recovery?
5. Tick budget: each tick of work must be bounded. Any unbounded loop
   inside a per-tick handler is a finding.

Report findings as bullets with severity.
```

## Angle 4: engine hooks (EE*)

```
Focus only on engine event hooks (EEInit, EEDelete, EEKilled, EECargoIn,
EECargoOut, EEItemAttached, EEItemDetached, EEItemLocationChanged,
OnStoreSave, OnStoreLoad). Audit:

1. Pre-super gate placement: every hook that should gate before vanilla
   super must check IsVirtualized() (or equivalent) BEFORE calling super.
   Any hook calling super first then gating is a finding.
2. EEDelete vs EEKilled symmetry: cleanup obligations must match
   between the two. Any cleanup only on one path is a finding.
3. OnStoreSave/OnStoreLoad cadence: when exactly does the engine call
   these? If your code assumes "once per shutdown" but the engine fires
   per-container at unpredictable times, that is a finding.
4. Any hook that mutates m_State or persists data without acquiring
   the mod's gating: finding.

Report findings as bullets with severity.
```

## Angle 5: admin commands

```
Focus only on admin command handlers (RPC entrypoints, debug menus, server
console commands). Audit:

1. Input validation: every sid argument must pass a strict regex (no
   path traversal, no shell metachars, length cap).
2. Path construction: any admin command that builds a file path from
   user input must use the path helper, not concatenate inline.
3. Race with running queues: if admin issues "reset" while sid is
   mid-virtualize, what happens? Is the queued work cancelled cleanly?
4. Sidecar ↔ in-memory consistency: if the command clears one store,
   does it clear the other? See `flag-lifecycle-audit.md`.
5. Authorization: who can run each command? Is the check enforced
   server-side, not just hidden in the UI?

Report findings as bullets with severity.
```

## Angle 6: recovery paths

```
Focus only on crash-recovery / boot-scan paths. Audit:

1. Crash matrix: for each on-disk file (.lfv, .tmp, .bak1, .bak2,
   .virtualizing, .restoring, .manifest.json, .quarantine.json),
   enumerate every combination of "present / absent / corrupt". For each
   combination, what does the recovery path do?
2. Orphan markers: a marker file with no matching primary. Boot scan
   must handle this without wedging the slot.
3. Degraded modes: if recovery cannot fully reconstruct, does it
   quarantine cleanly? Does the quarantined data remain readable for
   admin recovery?
4. Idempotency: running recovery twice on the same on-disk state must
   produce the same result.
5. Time-since-crash: any path that uses mtime/ctime as ground truth
   (DST, NTP slew, OS clock changes can break this) is a finding.

Report findings as bullets with severity.
```

## Angle 7: action layer (pre-super gates in action handlers)

```
Focus only on action handlers: the player-action layer that fires while
a container is virtualized but its proxy is in the world. Audit:

1. Every action class that targets a container or its contents: ActionTakeItem,
   ActionDropItem, ActionAttach, ActionMoveItem, ActionPickupContainer, etc.
   For each, find the OnAction / OnFinish / OnExecute method.
2. Pre-super gate: every action method must check
   IsVirtualized()/IsBusy() BEFORE the action body runs and BEFORE any
   super call that mutates the container. Action body runs after super =
   bug class VULN-004.
3. Network-action symmetry: if an action has a server-side and client-
   side variant, the gate must run server-side. Client-side gates are
   advisory only.
4. UI menu actions: right-click context menu entries that bypass the
   action layer entirely. Each such bypass is a finding.

Report findings as bullets with severity.
```

The action class names in point 1 are examples of the kind of action to look for. Of the five, only `ActionTakeItem` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakeitem.c:6`), `ActionDropItem` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actiondropitem.c:30`) and `ActionAttach` (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionattach.c:7`) are vanilla class names; a search of `P:\scripts` finds no `ActionMoveItem` and no `ActionPickupContainer`, so list the audited mod's real action classes with a search for `class Action` before pasting.

## Angle 8: threat model and input bounds

```
Focus only on what happens when on-disk state or network input is
malformed or hostile. Audit:

1. Sanity caps: every count read from disk (item count, slot count,
   string length, blob size) must be capped before allocating. A
   corrupt 4-byte length saying "4 GB" must not crash the server or
   spend 30s allocating.
2. Magic-byte validation: the file header magic must be checked before
   parsing the body.
3. Footer validation: the file footer (MAGIC_FILE_END or equivalent)
   must be checked before trusting the body.
4. UTF-8 / encoding: any string read from disk must be tolerated for
   invalid encoding without crashing the parser.
5. Network input: any RPC handler that accepts a sid or path. Apply the
   same cap-then-parse rule.

Report findings as bullets with severity.
```

## Independent verifier pass (step 3b)

This runs after the angle reviews report, before consolidation. It is the adversarial check that turns "an agent reported it" into "it is real".

Use **one** reviewer with a **fresh context** (`SKILL.md` step 3b asks for a reviewer from another model family when one is assigned). It must NOT have seen the angle reports, the spec, or the conventions and reference documents the angle reviewers read: shared context is how convergence becomes contagion. Hand it only the codebase path and the bare list of claims: each claim is a one-line statement plus a `path:line_start-line_end`, with no reasoning, no severity, no "found by".

```
You are verifying claims about a codebase. You have not seen the audit that
produced these claims, and you should not try to reconstruct it. Judge each
claim from the code alone.

Codebase root: <absolute path>

For each claim below:
1. Open the file at the cited path:line range.
2. Paste the actual lines you find there, verbatim, with line numbers.
3. Give the first verdict, snippet_matches_file, exactly one of:
   - CONFIRMED: the cited lines say what the claim says.
   - WRONG LOCATION: the claimed content exists in the file but at
     different lines. Give the correct lines.
   - NOT FOUND: the cited lines do not say what the claim says, and you
     could not find the claimed content elsewhere in the file.
4. Give the second verdict, inference_holds, exactly one of:
   - HOLDS: the code you pasted, plus any code you opened to follow it,
     really has the consequence the claim states (for example, data can
     be lost on that path).
   - DOES NOT HOLD: the lines exist but the consequence does not follow.
     A deliberate defensive branch (an OR that accepts two formats, a
     redundant guard, a tolerant parser) is DOES NOT HOLD when the claim
     calls it a bug.
   - CANNOT TELL: deciding needs code or runtime facts you could not
     reach. Say what is missing.
   Paste any extra lines you used for this verdict.
5. Do not soften. "Mostly matches" is WRONG LOCATION or NOT FOUND, never
   CONFIRMED.

Output: one block per claim: claim id, pasted lines, snippet_matches_file,
inference_holds, nothing else. No summary, no narrative, no
recommendations, no severity.

Claims to verify:
<numbered list: id + one-line claim + path:line_start-line_end>
```

A claim with CONFIRMED and HOLDS goes into the consolidated table. A WRONG LOCATION claim is re-cited with the corrected lines and then treated like CONFIRMED. Every other claim (NOT FOUND, DOES NOT HOLD or CANNOT TELL) is not actionable yet: the orchestrator re-reads the cited code itself and then either keeps it with its own pasted evidence or drops it with a one-line reason in the table. Never drop a claim silently. If more than about 10% of claims come back NOT FOUND, treat the whole step 2 batch as untrustworthy (`SKILL.md` step 3c).

## Implementer-grade pass (step 4)

This runs **once**, after the step 3 consolidation, with a fresh-context reviewer capable of cross-actor reasoning. The framing is critical: it explicitly demands cross-actor tracing, which the eight angle prompts do not.

```
You are auditing a data-critical DayZ mod for release readiness. Six prior
reasoning agents reviewed this code and signed off, and an external
implementer-grade auditor then found 12 bugs they missed. Your job is to be
that external auditor.

Codebase root: <absolute path>
README / spec: <path or contents>

Find every way this code can lose, corrupt, or silently misroute player
data. Specifically:

1. Trace each writer (every site that touches a file or sidecar) to every
   reader (recovery, cleanup, admin command, boot scan). Where the writer
   produces output the reader does not consume, or vice versa, that is a
   bug.
2. Trace each sidecar/marker/flag to every cleanup site (delete, reset,
   admin recovery). Where any cleanup site is missing an obligation, that
   is a bug.
3. Trace each admin flag to every consumer in the runtime. Where one
   store can hold a value the other does not, that is a bug.
4. Where the canonical async path enforces an invariant and an alternative
   entry point (sync, admin, mission-restart) does not, that is a bug.
5. Where on-disk state is not bounded against malformed input, that is a
   bug.

Constraints:
- Output ≤1500 words
- Every finding cites path:line_start-line_end
- Severity P0 / P1 / P2 / P3
- Do NOT trust prior agent reports. Do NOT defer to existing comments
  saying "this is safe because X". Re-verify X.

If you find nothing, say so. If you find one bug, after it is fixed, this
audit must run again with fresh context: chains of bugs unblock when the
first link is fixed.
```

The last paragraph of the prompt asks for a fresh run after each fix. The stop rule in `SKILL.md` step 6 bounds that: two rounds, and a finding blocks only with an executable repro.

## Notes on running the reviews

- When several angle reviewers are assigned, start them in **one** parallel batch. Running them one after another costs eight times the wall-clock time for no gain in quality.
- The implementer-grade pass goes in its own turn after consolidation, not in the same batch.
- On model size: the angle reviews tolerate a smaller model (Sonnet) for cost reasons, but the implementer-grade pass should run on the strongest model available (Opus). Cross-actor reasoning is where smaller models drop bugs.
- Do not feed one angle reviewer the output of another. The prompts are designed so that each angle finds bugs in its scope without needing context from the others.

## What the vanilla scripts offer

Checked on `P:\` (game storage version 144), so the prompts are read against the real API:

- File functions in Enforce Script: `FileExist` (`P:\scripts\1_core\proto\ensystem.c:397`), `OpenFile` (`ensystem.c:417`), `CloseFile` (`ensystem.c:443`), `FPrint` (`ensystem.c:462`), `FPrintln` (`ensystem.c:481`), `MakeDirectory` (`ensystem.c:525`), `DeleteFile` (`ensystem.c:528`) and `CopyFile` (`ensystem.c:531`). There is no rename, no move and no flush call.
- The hooks angle 4 lists are all methods of `EntityAI`: `EEInit` (`P:\scripts\3_game\entities\entityai.c:905`), `EEDelete` (`entityai.c:946`), `EEItemLocationChanged` (`entityai.c:976`), `EEKilled` (`entityai.c:1104`), `EEItemAttached` (`entityai.c:1159`), `EEItemDetached` (`entityai.c:1199`), `EECargoIn` (`entityai.c:1234`), `EECargoOut` (`entityai.c:1248`), `OnStoreSave` (`entityai.c:2910`) and `OnStoreLoad` (`entityai.c:2978`).
