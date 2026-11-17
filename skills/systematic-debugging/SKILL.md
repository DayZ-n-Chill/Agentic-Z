---
name: systematic-debugging
description: "Finds the root cause of a bug, test failure, build failure or unexpected behavior before any fix is proposed: observe the failure, trace it to its source, test one hypothesis, then make one change. Use when you meet any technical failure you can name, and before proposing a fix. Not for implementing an approved design, adding a feature with no failing behavior, or guessing a cause from a one-line complaint."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# Systematic debugging

Find the root cause before you attempt a fix. A fix for a symptom is a failure. This skill is reference only: it runs no scripts, so there is no preflight gate.

Following the letter of this process and breaking its spirit is still breaking it.

## The iron law

```
No fixes without root cause investigation first.
```

If you have not completed Phase 1, you cannot propose a fix.

## What to read

The method is complete in this file. The files below are optional extras for one kind of episode each. If one is missing, do not stall and do not create it: use the method card and the quick versions in this file.

| Question | Read |
|---|---|
| The error is deep in a call stack: how do I trace the bad value back to where it came from? How do I find which test leaves a stray file behind? | `references/root-cause-tracing.md` |
| I found the root cause: how do I make the same bug impossible, not just fixed? | `references/defense-in-depth.md` |
| A test is flaky because it sleeps for a guessed time: how do I wait for the real condition? | `references/condition-based-waiting.md` |
| What does a full set of condition-based wait helpers look like in code? | `references/condition-based-waiting-example.ts` |

## When to use

Use it for a technical failure you can name: test failures, production bugs, unexpected behavior, performance problems, build failures, integration issues.

Use it most of all when:

- You are under time pressure (emergencies make guessing tempting).
- "Just one quick fix" seems obvious.
- You have already tried several fixes.
- The previous fix did not work.
- You do not fully understand the issue.

Do not skip it when:

- The issue seems simple (simple bugs have root causes too).
- You are in a hurry (rushing guarantees rework).
- Someone wants it fixed now (systematic is faster than thrashing).

Do not use it to:

- Implement an already-approved design (that is implementation, not debugging).
- Add a feature that has no failing behavior.
- Rewrite architecture on the first failure.
- Produce a postmortem, a status update or a blame assignment.

## In a DayZ mod

The method is the same; these are the places the evidence and the reproduction come from in this repo.

- **The named failure** is a line the tools already quote: a `/dayz-lint` finding, a `/dayz-gate` failure (its file and line, its `context` stack trace, the mod files in `points_to`, and its triage verdict), or a line flagged by `/dayz-logwatch`.
- **The observable system** is the mod source in `workspace/<ModName>/` plus the session logs: the server's in `.server/<instance>/Profiles/`, the client's in `.server/!ClientDiagLogs/`.
- **The component boundaries** for Phase 1 step 4 run in this order: mod source, `/dayz-lint`, `/dayz-build-pbo`, the PBO under `P:\Mods\@<ModName>\Addons\`, server start, client join, then the in-game behavior. Find the first boundary where the output is wrong before reading any deeper.
- **The failing reproduction** for Phase 4 is the gate that failed, run again: `/dayz-gate build`, `/dayz-gate ingame`, or the one check in `output/<ModName>-plan/behavior-checks.json` that names the broken behavior (format in `skills/dayz-gate/checks-file.md`). The fix is done when that gate passes and the others still pass.
- **Who does what.** The `dayz-mod-debugger` agent diagnoses a failure that triage marks new and names the worker who owns the fix; it changes no file. Failures triage marks known already carry their fix and owner.
- **Recent changes** (Phase 1 step 3) include the game itself: when a mod broke after a DayZ update, `/dayz-upgrade-guard check` lists the mod classes whose vanilla parents changed.

## Intake: before Phase 1

You need three things. Nothing else starts until you have them. Do not form a hypothesis, do not add instrumentation, do not propose a fix.

1. **A named failure.** An error message, a failing test, a broken behavior, a measured regression. "Something's wrong" or "the app is weird" is not enough.
2. **A system you can observe.** Repo, logs, stack, environment, or a reproduction the user can run. A screenshot of a symptom with no access is not enough.
3. **A way to gather evidence.** Either a consistent reproduction, or a next measurement you can take. If you can neither reproduce nor measure, you cannot investigate.

If any of those is missing, stop. Say what is missing and what you need. Do not invent a root cause. Do not propose a "likely" fix to keep moving.

Then, and only then, enter Phase 1.

## HOLD: stop and return this, not a fix

When you cannot proceed, return the gap. Do not fill it with a polished patch.

| Condition | What is missing | What it needs | Return instead of a fix |
|---|---|---|---|
| No named failure | The object of investigation | Error, failing test, broken behavior, or measured regression | "I need the failure itself: an error, a test, or the broken behavior. I will not invent one." |
| No observable system | Access to code, logs, stack, or environment | A path, a log, a repo, or a reproduction the user can run | "I cannot observe the system, so I cannot investigate. Holding." |
| Neither reproducible nor measurable | A next fact | Steps that trigger it, or one measurement to take | "Not reproducible and I have no next measurement. I will not guess." |
| Phase 1 not done | A stated root cause with evidence | Completed investigation: error read, reproduced or measured, recent changes checked | The investigation so far. No patch. |
| Hypothesis is vague | A single testable claim | "I think X is the root cause because Y" | Write the claim or HOLD. Do not change code. |
| Fix would ship without a failing reproduction | A test or script that fails the same way | Simplest reproduction that fails first | The reproduction. No production change. |
| 3 or more fixes already failed | A decision on the pattern, not another patch | A discussion with the user: keep this architecture or change it | The three failures, the coupling they revealed, the question. Do not attempt fix 4. |
| The user said "stop guessing", "is that not happening?" or "we're stuck?" | A return to evidence | Phase 1 restarted, with what you assumed named | Stop. Name the assumption. Return to Phase 1. |
| Production, data-loss, or security blast radius | The user's authority to touch that surface | An explicit yes from the user | The risk and the question. No change. |
| A companion file is missing (a file under `references/`, a test-driven-development skill, a verification skill) | Nothing: those files are optional | The methods already in this file | Do not stall. Use the quick versions below. |

A HOLD is a return value, not a delay before you guess.

## Defaults: cut first

This operation defaults to less, not more.

- Do not add a component, wrapper, retry, timeout, or feature flag to work around a failure you have not named.
- Do not keep code from a failed hypothesis. Revert it before the next test.
- Do not bundle a refactor with the fix. "While I'm here" is a new request.
- Do not add a second layer of instrumentation after the failing boundary is already visible.
- Prefer reverting the recent change that introduced the failure over a new branch of logic.
- Prefer deleting the bad path over adding a guard that leaves the bad path alive.
- The smallest change is allowed only after a root cause is named. Smallest-change is not a license to patch a symptom.
- Extra files, extra tests beyond the one reproduction, or extra logging in the shipped fix need a reason from the failure, not from a habit of completeness.
- If a companion technique file is missing, do not create it. Use the method card in this file.

## Will not produce

Do not return any of the following:

- A patch before Phase 1 is complete.
- A "probably X" guess dressed as a root cause.
- A symptom workaround (retry, catch-and-ignore, sleep, default value) presented as the fix.
- Multiple unrelated changes in one attempt.
- A failing-test skip, a deleted assertion, or "I'll verify manually".
- Code kept from a failed hypothesis.
- An architecture rewrite on the first or second failure.
- A claim of "no root cause" before the investigation in this file is finished.
- A fourth fix attempt after three failures, without the architecture question.
- A stall because a companion file or another skill is missing.
- A root cause invented because the failure is not reproducible.

## Method card: same family every run

A later agent runs this from this file alone. The files under `references/` and any test-driven-development or verification skill are optional extras. If they are missing, do not stall and do not invent a different method: use the card below. Do not skip, reorder, or replace these phases.

1. **Intake.** Named failure, observable system, and a way to gather evidence. Any gap: HOLD.
2. **Phase 1: root cause.** Read the error completely. Reproduce or take the next measurement. Check recent changes. If the system has component boundaries, instrument each boundary once, then read where it breaks. If the error is deep in a call stack, trace backward to the original bad value (quick version in Phase 1). Stop when you can say what fails and why. No patch in this phase.
3. **Phase 2: pattern.** Find a working example of the same kind. Read the reference completely if you are implementing a pattern. List every difference. Name the dependencies and assumptions.
4. **Phase 3: one hypothesis.** Write one claim: "I think X is the root cause because Y." Change one variable to test it. If it fails, revert and write a new claim. Do not stack changes.
5. **Phase 4: fix.** Write the simplest failing reproduction first. Then one change at the named root. Verify the reproduction now passes and neighbors still pass. If the change fails and you have tried fewer than three: return to Phase 1. If three have failed: HOLD for architecture, do not attempt a fourth.
6. **Return.** Root cause stated, reproduction that failed then passed, single change, or a HOLD. Nothing else.

## The four phases

Complete each phase before you go on to the next.

### Phase 1: Root cause investigation

Before attempting any fix:

1. **Read error messages carefully.**
   - Don't skip past errors or warnings.
   - They often contain the exact solution.
   - Read stack traces completely.
   - Note line numbers, file paths, error codes.

2. **Reproduce consistently.**
   - Can you trigger it reliably?
   - What are the exact steps?
   - Does it happen every time?
   - If it is not reproducible, gather more data; don't guess.

3. **Check recent changes.**
   - What changed that could cause this?
   - Git diff, recent commits.
   - New dependencies, config changes.
   - Environmental differences.

4. **Gather evidence in multi-component systems.**

   When the system has multiple components (CI to build to signing, API to service to database), add diagnostic instrumentation before proposing fixes:

   ```
   For each component boundary:
     - Log what data enters the component
     - Log what data exits the component
     - Verify environment/config propagation
     - Check state at each layer

   Run once to gather evidence showing where it breaks
   Then analyze the evidence to identify the failing component
   Then investigate that specific component
   ```

   Example (multi-layer system):

   ```bash
   # Layer 1: Workflow
   echo "=== Secrets available in workflow: ==="
   echo "IDENTITY: ${IDENTITY:+SET}${IDENTITY:-UNSET}"

   # Layer 2: Build script
   echo "=== Env vars in build script: ==="
   env | grep IDENTITY || echo "IDENTITY not in environment"

   # Layer 3: Signing script
   echo "=== Keychain state: ==="
   security list-keychains
   security find-identity -v

   # Layer 4: Actual signing
   codesign --sign "$IDENTITY" --verbose=4 "$APP"
   ```

   This reveals which layer fails (secrets to workflow passes, workflow to build fails).

5. **Trace data flow.**

   When the error is deep in the call stack, use `references/root-cause-tracing.md` if it is present. If it is missing, use this quick version; do not stall.

   Quick version:
   - Where does the bad value originate?
   - What called this with the bad value?
   - Keep tracing up until you find the source.
   - Fix at the source, not at the symptom.

### Phase 2: Pattern analysis

Find the pattern before fixing:

1. **Find working examples.**
   - Locate similar working code in the same codebase.
   - What works that is similar to what is broken?

2. **Compare against references.**
   - If you are implementing a pattern, read the reference implementation completely.
   - Don't skim: read every line.
   - Understand the pattern fully before applying it.

3. **Identify differences.**
   - What is different between working and broken?
   - List every difference, however small.
   - Don't assume "that can't matter".

4. **Understand dependencies.**
   - What other components does this need?
   - What settings, config, environment?
   - What assumptions does it make?

### Phase 3: Hypothesis and testing

Scientific method:

1. **Form a single hypothesis.**
   - State it clearly: "I think X is the root cause because Y."
   - Write it down.
   - Be specific, not vague.

2. **Test minimally.**
   - Make the smallest possible change to test the hypothesis.
   - One variable at a time.
   - Don't fix multiple things at once.

3. **Verify before continuing.**
   - Did it work? Yes: Phase 4.
   - Didn't work? Form a new hypothesis.
   - Don't add more fixes on top.

4. **When you don't know.**
   - Say "I don't understand X."
   - Don't pretend to know.
   - Ask for help.
   - Research more.

### Phase 4: Implementation

Fix the root cause, not the symptom:

1. **Create a failing test case.**
   - Simplest possible reproduction.
   - Automated test if possible.
   - One-off test script if there is no framework.
   - You must have it before fixing.
   - If a test-driven-development skill is present you may use it for the reproduction. If it is missing, write the simplest failing reproduction here. Do not stall.

2. **Implement a single fix.**
   - Address the root cause identified.
   - One change at a time.
   - No "while I'm here" improvements.
   - No bundled refactoring.

3. **Verify the fix.**
   - Does the test pass now?
   - Are no other tests broken?
   - Is the issue actually resolved?
   - If a verification skill is present you may use it. If it is missing, run the reproduction and the neighboring tests yourself. Do not stall.

4. **If the fix doesn't work.**
   - Stop.
   - Count: how many fixes have you tried?
   - Fewer than 3: return to Phase 1 and re-analyze with the new information.
   - 3 or more: stop and question the architecture (step 5 below).
   - Don't attempt fix 4 without an architectural discussion.

5. **If 3 or more fixes failed: question the architecture.**

   Patterns that indicate an architectural problem:
   - Each fix reveals new shared state, coupling or a problem in a different place.
   - Fixes require "massive refactoring" to implement.
   - Each fix creates new symptoms elsewhere.

   Stop and question the fundamentals:
   - Is this pattern fundamentally sound?
   - Are we "sticking with it through sheer inertia"?
   - Should we refactor the architecture instead of continuing to fix symptoms?

   Discuss with the user before attempting more fixes.

   This is not a failed hypothesis: it is a wrong architecture.

## Red flags: stop and follow the process

If you catch yourself thinking:

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- "One more fix attempt" (when you have already tried 2 or more)
- Each fix reveals a new problem in a different place

All of these mean: stop and return to Phase 1.

If 3 or more fixes failed, question the architecture (Phase 4, step 5).

## The user's signals that you are doing it wrong

Watch for these redirections:

- "Is that not happening?": you assumed without verifying.
- "Will it show us...?": you should have added evidence gathering.
- "Stop guessing": you are proposing fixes without understanding.
- "Ultra-think this": question fundamentals, not just symptoms.
- "We're stuck?" (frustrated): your approach isn't working.

When you see these, stop and return to Phase 1.

## Common rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. The process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is faster than guess-and-check thrashing. |
| "Just try this first, then investigate" | The first fix sets the pattern. Do it right from the start. |
| "I'll write the test after confirming the fix works" | Untested fixes don't stick. A test written first proves it. |
| "Multiple fixes at once saves time" | You can't isolate what worked, and it causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms is not understanding the root cause. |
| "One more fix attempt" (after 2 or more failures) | 3 or more failures means an architectural problem. Question the pattern; don't fix again. |

## Quick reference

| Phase | Key activities | Success criteria |
|-------|---------------|------------------|
| **1. Root cause** | Read errors, reproduce, check changes, gather evidence | Understand what and why |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed, or a new hypothesis |
| **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

## When the process reveals "no root cause"

If a systematic investigation shows the issue is truly environmental, timing-dependent, or external:

1. You have completed the process.
2. Document what you investigated.
3. Implement appropriate handling (retry, timeout, error message).
4. Add monitoring or logging for future investigation.

But 95% of "no root cause" cases are incomplete investigation.

## Before you return

Run this check on the output. If any item fails, fix it or HOLD; do not hand over a patch.

- Intake was complete, or you returned a HOLD on the missing item.
- Phase 1 named a root cause with evidence, or you returned a HOLD.
- You did not propose a fix before that root cause.
- A single hypothesis was tested; failed-hypothesis code was reverted.
- A failing reproduction existed before the production change.
- The change is one change, at the source, not a symptom workaround.
- Neighboring tests still pass, or you said which ones you could not run.
- You did not attempt a fourth fix after three failures.
- You did not stall because a companion file was missing.
- Production, data-loss and security surfaces still need the user's yes if you touched them.

## What this process changes

The recipe is not a neutral mirror. Running it changes the work:

- **The first failing test can become the whole object.** Phase 4 requires a reproduction before the fix. That test then defines "done". A production failure that is wider than the first test you wrote will be treated as fixed when that test goes green. The recipe narrows the bug to whatever you happened to encode first.
- **The architecture gate can delay a simple fix.** After three failed attempts the recipe forbids a fourth and asks whether the pattern is sound. The third failure may have been a bad hypothesis, not a bad architecture. The gate will hold a one-line fix hostage to an architecture conversation the user did not ask for.
- **Smallest-change can hide a bad root.** Phase 3 says change one variable. A tiny patch that makes the reproduction pass can confirm a local symptom while the real source sits one layer up. "It went green" is not "we found the source". The recipe rewards the smallest change that silences the current test.
- **Instrumentation is not free observation.** Boundary logs, extra env dumps, and stack prints change timing, payload shape, and which path runs. The failure you then "see" may be the instrumented system, not the original one. Investigator fixation follows the first layer that looks wrong.
- **Working-example comparison makes "match the working one" the goal.** Phase 2 will pull the broken path toward the nearest similar code, including its accidents. Differences you listed become the fix list even when the working example is itself wrong for this case.
- **Completing Phase 1 before any patch delays an already-named one-line root.** When the error, the line, and the recent commit already name the cause, the ceremony still forbids the patch until the rest of the checklist is ticked. That is the recipe spending time the failure does not need.
- **Companion files, if used, pull the work onto their objects** (a tracing writeup, a test-first loop, a verification ritual). This file is enough. Using them changes what gets discussed.

What still needs a person, and cannot be supplied by this recipe: whether the first failing test is the right object; whether three failed fixes are architecture or three bad hypotheses; whether to ship the smallest confirmed change or keep looking; whether "no root cause" is truly environmental; any production, data-loss, or security change; and whether to refactor the pattern instead of fixing it. The output is an investigation plus one change, or a HOLD. It is not a decision to ship.
