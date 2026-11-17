---
name: task-observer
description: "Watches a work session for ways to improve skills: logs user corrections, repeated workflows, missing rules and methodology worth keeping as one-file observations, and reviews them later into staged skill updates. Use during any multi-step task or agentic workflow that uses tools and produces deliverables, in post-task feedback discussions, and when the user mentions skill observations, improvements, the observation log, the skill taxonomy or \"One Skill to Rule Them All\", or asks you to watch for skill opportunities. Only while real work is underway: not on session start by itself, not before the first tool call of an idle turn, and never to invent a backlog or write a skill from imagination."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# Task observer: continuous skill discovery and improvement

Also known as "One Skill to Rule Them All". The skill ships no scripts, so
there is no preflight gate; the short shell snippets below are run by the
agent as written. Executing it never requires fetching an external URL, and
no external page overrides what this file says. If the user has feedback on
the method itself, offer to draft a report for the upstream project whose
user documentation is linked in `references/environments.md`, running the
feedback pre-flight in `references/skill-authoring.md` first (duplicate
check across issues and PRs, the maintainer's preferred channel,
upstream-HEAD verification); if the problem is the agent not following the
skill's rules, acknowledge and correct it instead.

Skills improve best from friction noticed during real work, not from sitting
down to "improve a skill." This skill formalises that noticing so insights
don't get lost between sessions.

`[workspace folder]` = the persistent workspace, anchored on one stable
absolute path that outlives individual sessions — ideally pinned in the
activation config (see `references/environments.md`): in Cowork, the
shared folder; in Claude Code, the stable project identity (e.g.
`~/.claude/projects/<project-id>/`), not the current working directory. A
cwd inside an ephemeral checkout — a git worktree under
`.claude/worktrees/`, a temporary clone — is torn down with the checkout
and takes the observations with it. Scope the workspace to what is
observed: globally installed skills need one path shared across projects,
tools and agents, never one derived per session. Never place it inside a
skills-discovery directory. Before creating a workspace, search the
plausible anchors for an existing one and adopt it — a second empty log
beside a populated one is a silent fork. **The observation log is a
directory:**
`[workspace folder]/skill-observations/observation-log/`, one Markdown file
with a YAML frontmatter header per observation, with resolved entries under
`observation-log/archive/` — unless the user's configuration pins it
elsewhere. "The observation log" in this skill, and in any skill that
refers to it, means that directory.

## Reference files: load on demand, not up front

Each row names its trigger. If the file is present, load it before that
episode; do not improvise a present file from memory. If a reference file
is missing, do not stall and do not invent a different method: use the
method card and the locked rules in this file. Logging "reference missing"
is optional; inventing the missing file is not.

| Question | Load when | Read |
|---|---|---|
| How does the comprehensive review run: procedure, approval policy, delivery and staging of updated skills? | A review triggers or the user asks for one. | `references/weekly-review.md` |
| How is a skill created or edited: taxonomy in full, structure defaults, licensing, attribution, confidentiality layers, live-file editing and relocation-verification rules? | Before creating or editing any skill. | `references/skill-authoring.md` |
| How is the log stored: layout, frontmatter fields, helper snippets, archival details, and the reasoning behind the rules? | Setting up the log for the first time, archiving, when an id or frontmatter looks wrong, or before changing how anything reads the log. | `references/observation-log.md` |
| What is and isn't worth logging (the full catalogue)? | Unsure whether something is an observation, or sorting many candidates. | `references/signals.md` |
| How is the skill activated and configured, what happens at compaction, what is in the bundle, and how does handoff-doc mode work where there is no storage? | Setup questions, after compaction, or when there is no filesystem. | `references/environments.md` |
| How is a pre-3.0 single-file `log.md` converted, once, by script? | Only when the Session Start Protocol detects a legacy log. Fresh installs never read it. | `references/migration.md` |

## In an Agentic-Z clone

The method below is written for any environment. In this repo, Tier 1
(`.claude/CLAUDE.md`) and the points here win where they differ from it.

- **Workspace folder.** Unless the user pinned another path,
  `[workspace folder]` is `.claude/local-memory/` in the project's main
  checkout (gitignored, one per clone), so the observation log is
  `.claude/local-memory/skill-observations/observation-log/`. A git
  worktree of the repo is an ephemeral checkout: never anchor there.
- **Live skill files.** The live files are `skills/<name>/` and
  `.claude/skills/<name>/` in the repo. The entries `/sync-skills` creates
  in an agent's home skills folder are links to them, so a write through a
  link is a write to the live file. In a plugin install the plugin's files
  are replaced on every update: treat them as the "writable but volatile"
  case in `references/weekly-review.md`, Step 2.
- **Rules live in the repo, never in the log.** `.claude/local-memory/`
  holds notes, not rules. A correction the user states goes to
  `/dayz-record-correction` first: it asks for their yes and writes the
  rule into its tier. Log an observation only for what that leaves open,
  such as a skill gap the correction revealed. When a review confirms an
  observation or a cross-cutting principle
  as a rule for the team, write it through `/dayz-record-correction` into
  its tier, then mark the observation `actioned` and name the file the
  rule went into.
- **Skill shape.** A skill written or edited in this repo follows
  `docs/prompt-conventions.md` and the shape of the skills already here.
  The open-source skill template in `references/skill-authoring.md`
  (author block, licence statement) is for a skill published outside this
  repo.
- **After a staged update is installed.** Run the checks Tier 1 names:
  `python -m pytest -q .claude skills scripts/dev hooks scripts/tools`, then `/docs-sync`.
- **Activation.** The activation block in `references/environments.md` is
  a Tier 1 rule here: it goes into `.claude/CLAUDE.md`, `AGENTS.md` and
  `GEMINI.md` with the same text, and only with the user's yes.
- **Shell snippets.** They are POSIX shell. On Windows run them in Git
  Bash (the Bash tool), from the workspace folder.

## When to use

Use during a real work session that will use tools or produce
deliverables: multi-step tasks, agentic workflows, post-task feedback,
and talk about skills or methodology. Also use when the user names the
observation log, the skill taxonomy, or asks the agent to watch for
skill opportunities. Invoke before the first tool call of the session.

**Do not use this to:**

- Invent a backlog or a set of "likely" observations with no work underway
- Write or rewrite a skill from imagination
- Sit down to "improve skills" as a generation task with no live friction
- Replace a missing or unreadable log with fabricated entries
- Answer a casual or one-shot factual question that uses no tools and
  produces no deliverable

## Intake: before any write

You need three things. Nothing else starts. Do not create
`skill-observations/`, do not mint an observation, do not invent a date.

1. **A workspace you can observe.** One stable absolute path that outlives
   this session. An ephemeral checkout (`.claude/worktrees/`, a temporary
   clone) is not a workspace. A path you cannot read is not a workspace.
2. **A work session, or an explicit watch request.** Tools will be used or
   a deliverable will be produced, or the user asked you to watch for
   skill opportunities. "Improve the skills" with no session is not enough.
3. **A way to record.** Either `skill-observations/` is reachable, or you
   may set it up on the stable path, or (no filesystem) you will keep a
   handoff note in-session and not pretend a log exists. If you can
   neither read nor write a log and the user did not accept handoff-doc
   mode, you cannot observe.

If any of those is missing, stop. Say what is missing and what you need.
Do not invent observations. Do not invent dates. Do not create a second
empty log beside a populated one.

Then, and only then, enter the Session Start Protocol.

## HOLD: stop and return this, not a log entry

When you cannot proceed, return the gap. Do not fill it with a polished
observation, a guessed date, or a generated skill.

| Condition | What is missing | What it needs | Return instead of a log entry |
|---|---|---|---|
| No stable workspace | A path that outlives the session | The pinned workspace, or a re-anchor off the ephemeral checkout | "Workspace is ephemeral or unreadable. I will not write a log here." |
| No work session and no watch request | Something to observe | A task that uses tools, or an explicit "watch for skill opportunities" | Nothing. Do not activate a backlog. |
| Empty probe of a log known to be non-empty | A working scan | Re-derived literal path, independent file count, headers that parse | "SCAN COMMAND BROKEN — N files present, 0 headers parsed." Do not conclude "no observations." |
| Directory or id-check empty where this session already wrote | The live structure | Re-probe: is there `observation-log/`? a `log.md.migrated`? | Halt. Do not recreate the missing target. |
| Clock unavailable when a date field would be written | A real calendar date from the environment | The harness clock, or no date field written | HOLD. Do not write "today", yesterday, or a remembered date. |
| `last-review-date.txt` missing or unreadable | The review truth file | Recreate it with the literal `never` | The file containing `never`. Do not write a date. |
| Writes denied after one retry and one alternate interface | A writable log | A reachable workspace, or handoff-doc mode | "Failed N times on path P." Do not invent an in-memory log as if it were written. |
| User asked to invent observations or a backlog | Live friction | A real correction, pattern, or workflow from this session | Refuse. "I will not invent observations." |
| One unvalidated observation would become a live skill rule | Recurrence or review confirmation | A later session seeing the same pattern, or a review that confirms it | Keep it `open`. Do not edit the skill. |
| Acting on observations outside the three contexts | Authorization | Review, explicit user request, or in-session correction of wrong output | Log-and-defer. Do not stage or apply. |
| Open-source Principle would identify a client | A generalised takeaway | Strip names, domains, project traces — or type `internal` | HOLD the write until the Principle is clean, or mark `internal`. |
| Companion / `references/` file missing | Nothing — those files are optional | The method card in this file | Do not stall. Do not create the missing file. |
| Interactive review would gate the user's task | Nothing | A one-line offer, then their task | Offer once. Do not start the review unless they opt in. |

A HOLD is a return value, not a delay before you guess.

## Defaults: cut first

This operation defaults to less, not more.

- Adopt an existing workspace and log. Search plausible anchors first. Do
  not create a second empty `skill-observations/` beside a populated one.
- Do not mint a new skill, a new `proposes_skill` name, or a new family
  from a single unvalidated observation. Reuse a fitting candidate.
- Do not invent an observation to satisfy a checkpoint. If nothing
  accumulated, the write is a one-line `no observations` acknowledgement
  on `checkpoints.log` — not a dated observation file.
- Do not invent a date. Setup writes `never` into
  `last-review-date.txt`. A date in that file means a review actually
  finished. An observation `date:` is the environment clock at the moment
  *that file* is written. `resolved:` is written only when the status
  becomes `actioned`, `declined`, or `superseded`.
- Do not recreate a retired `log.md` or a missing directory that this
  session already used. Re-probe; then HOLD.
- Do not add a rule to a skill from one session. A single observation
  stays a candidate (`status: open`) until a later session sees the same
  pattern or a review confirms it.
- Do not rewrite the observation directory. One new file, or a
  frontmatter edit of one file, or one `mv` to `archive/`.
- Do not archive without a `resolved:` date that is *before* today. A
  missing `resolved:` gets today's clock written to that field — only
  then, and only because the status is already resolved — and the file
  waits until a later day.
- If a `references/` file is missing, do not create it. Use this file.
- Prefer simplify (remove an unvalidated single-observation rule) over
  adding a louder rule.

## Will not produce

Do not return any of the following:

- An invented observation, an invented backlog, or a "likely" insight
  with no event in this session
- An invented date (`last-review-date.txt` written as today at setup;
  an observation dated from memory; a backdated `resolved:`; a review
  date for a review that did not run)
- "No observations" as a *finding* after an empty parse of a non-empty log
- A recreated retired `log.md` or a second empty log beside a live one
- A skill rule, staged skill, or live edit from one unvalidated observation
- A skill written from imagination with no logged friction
- An open-source Principle that names a client, domain, or real project
- Id `1` proposed against a populated log
- An in-session skill rewrite outside the three acting contexts
- A stall, or a newly created companion file, because `references/` is missing
- A review that gates the user's interactive task
- A claim that the log is empty when the independent file count is not zero

## Method card: same family every run

A later agent runs this from this file alone. Files under `references/`
(`weekly-review.md`, `skill-authoring.md`, `observation-log.md`,
`signals.md`, `environments.md`, `migration.md`) are optional extras. If
they are missing, do not stall and do not invent a different observer —
use the card below. Do not skip, reorder, or replace these steps. Do not
substitute a brainstorm, a skill-authoring session, or a generated
backlog.

1. **Intake.** Stable workspace + a work session (or an explicit watch
   request) + a way to record (reachable log, permission to create it on
   the stable path, or accepted handoff-doc mode). Any gap → HOLD.
2. **Anchor.** Resolve one stable absolute path. If the path is ephemeral,
   warn and re-anchor before any write. Search existing
   `skill-observations/` on plausible anchors and adopt the populated
   one. Never derive a per-session workspace.
3. **Session start — structure.** If a legacy `skill-observations/log.md`
   exists and `observation-log/` does not, convert with the migration
   script as `references/migration.md` describes; if that file or the
   script is missing (the script is not bundled with this skill), HOLD
   and say the legacy file needs the script — do not hand-split it. If
   the per-file log is already the live form: create only what is absent
   (`observation-log/`, `archive/`, `cross-cutting-principles.md`,
   `last-review-date.txt` containing `never`). Do not write a date at
   setup.
4. **Session start — scan.** Read only YAML frontmatter (`status`,
   `skill`, `proposes_skill`, `title`, `siblings_checked`) plus active
   principles. Count files on a literal path independently of the parse.
   Files exist and nothing parsed → stop, not "no observations." Hold
   what you scanned; do not surface unprompted.
5. **Session start — review trigger.** Read `last-review-date.txt`.
   Missing/unreadable → recreate as `never`. Compare the file's value to
   the environment clock (never to a remembered or invented date). If
   the value is `never` or older than 7 calendar days and there are OPEN
   observations: interactive → one-line offer, then their task;
   scheduled/autonomous → run the review from this card (step 10).
   Mention missing skill targets and staged `PENDING.md` in one line each.
6. **Observe.** Whole session, including feedback. New skill / improve /
   simplify as named in this file. Do not log one-offs, already-captured
   prefs, tool bugs, or open-source items that need proprietary context.
   Generisability test: another project, another task, a missing rule or
   principle, likely to recur. Mostly no → not an observation. One
   unvalidated sighting stays a candidate; it does not become a rule.
7. **Log, same turn.** One file `NNNN-short-slug.md`. Id = max(active
   prefixes, archive prefixes, `archive/.id-floor`) + 1; re-derive before
   each file in a batch. Guard: log non-empty but no ids extracted →
   stop. Frontmatter mandatory: `status: open`, non-empty
   `siblings_checked:`. `date:` = environment clock at this write, or
   omit the field and HOLD rather than invent. Body is Issue →
   Improvement → Principle. Validate `skill:` exists now or use
   `proposes_skill`. Silent write. Denied write → one retry + one
   alternate interface, then report "failed N times."
8. **Checkpoints (tool-record only).** After every 3rd completed todo,
   on a major deliverable, and on any project-completing command
   (deploy, release, publish, push): write pending observation files, or
   a one-line `no observations` on `checkpoints.log`. A remembered
   "ask whether" is not a write. Sessions with no todos still flush on
   deliverable or completing command. End of session is the last flush.
9. **Surface and act.** Default: log-and-defer. End-of-session grouped
   summary only. Act only in three contexts — (a) the comprehensive
   review, (b) an explicit user request, (c) in-session correction when
   a skill is producing wrong output. Read the full body before
   resolving. Set `status` / `resolved` / `resolution` in the same turn
   you act. Substantial edits and new skills stay staged; additive
   clarifications may be staged-and-handed, never live-edited as an
   exception the user has to remember.
10. **Review (when step 5 fires or the user opts in).** Group OPEN
    observations by `skill:`. Read bodies, not titles. Apply only
    clearly-additive, low-risk changes, still on a staged copy from a
    fresh read of the live file. Escalate new skills, restructures, and
    judgment calls. After the review actually finishes, write today's
    environment-clock date — and only that — into
    `last-review-date.txt`. If the review did not finish, leave the
    file untouched.
11. **Return.** New or updated observation files, a HOLD, a one-line
    review offer, or a staged update. Not a generated skill. Not an
    invented date. Not an empty-scan "no observations" finding.

## Recurrence: same structure, no rot, no invented dates

A later agent must produce the same family of files, not a parallel
history. The lock is the structure plus the clock, not session memory.

**Cadence (locked):**

| Event | When it fires | What is written | What is never written |
|---|---|---|---|
| Session start | Every session, before the first tool call of the work | Structure that is absent; a scan; maybe a one-line review offer | A date in `last-review-date.txt`; an invented observation |
| Observation | Same turn as the friction, or the next | One `NNNN-slug.md` with clock `date:` | A backdated file; a mental note; a batch of pre-assigned ids |
| Checkpoint | 3rd/6th/9th todo, major deliverable, project-completing command, session end | Pending observation files, or one line on `checkpoints.log` | A dated observation that says nothing happened |
| Review offer | `last-review-date.txt` is `never` or older than 7 calendar days, and OPEN observations exist | The one-line offer (interactive) or the review (scheduled) | A review date for an offer that was declined |
| Review complete | The review actually finished | `last-review-date.txt` ← environment clock YYYY-MM-DD | Yesterday, tomorrow, "should have reviewed", a remembered date |
| Archive | On write, per already-resolved file whose `resolved:` is before today | `mv` of that one file to `archive/` | A rewrite of the directory; archive of `parked` or of today |

**Dates (locked):**

- Source of truth for "what day is it" is the environment clock of the
  write, never conversation memory, never a date in an old file copied
  forward, never "today" typed from habit.
- `last-review-date.txt` has two legal values: the literal `never`, or
  one `YYYY-MM-DD` of a review that finished. Setup always writes
  `never`. A missing file is recreated as `never`. A garbage value is
  replaced with `never`. Do not "fix" it to today.
- Observation `date:` is the clock at that file's creation. If the clock
  cannot be read, omit `date:` and HOLD rather than guess.
- `resolved:` is written only in the turn the status becomes `actioned`,
  `declined`, or `superseded`, and only from the clock. Do not backdate
  to the observation's `date:`.
- `parked_until:` is a condition a later session can test, not a
  decorative date. A date is allowed only when the condition *is* a
  date ("when tool X ships") — still not invented.
- Do not copy dates between files. Do not stamp a batch with one date
  computed up front.

**Single-observation rules stay candidates:**

A rule that exists because one session saw one event is unvalidated.
Leave the observation `open`. Do not edit the target skill. A later
session that sees the same pattern logs a new observation citing the
first id, or a review confirms it. Simplifying (removing a rule that
came from one unvalidated observation) is the default at review, not
adding a louder version of the same rule.

**Rot the log will not do:**

- Empty parse ≠ empty log.
- Missing structure this session already used ≠ create.
- Adopt, do not fork.
- Id space is monotonic across `observation-log/`, `archive/`, and
  `.id-floor`.
- `parked` stays in the active directory until its condition is met or
  it is genuinely resolved — it never archives on age.
- Compaction or a new agent does not restart the method. Re-read this
  card. Re-scan frontmatter. Do not replay session memory as history.

## Session Start Protocol

1. **Storage.** If `skill-observations/observation-log/` (with its
   `archive/` subdirectory) or
   `skill-observations/cross-cutting-principles.md` don't exist,
   create them (principles template: `references/skill-authoring.md`).
   Create `skill-observations/last-review-date.txt` containing the literal
   value `never` if it doesn't exist — never write a date into it at setup;
   a date means a review actually ran. If a legacy single-file
   `skill-observations/log.md` exists and `observation-log/` does not, this
   is an upgrade from a pre-3.0 install: load `references/migration.md` and
   run the scripted conversion before writing anything else (the script
   is not bundled with this skill; without it, HOLD). Before
   creating or writing anything: if the resolved workspace folder sits
   under an ephemeral path (e.g. `.claude/worktrees/`, a temporary clone),
   warn the user and re-anchor on the stable project path first — state
   written to an ephemeral checkout is lost at teardown.
2. **Scan.** Read only the frontmatter of each file in `observation-log/`
   — the header block between the first two `---` lines, never the bodies
   — and build awareness from `status`, `skill`, `proposes_skill` and
   `title`; also read the active principles. Hold them in awareness, don't
   surface unprompted. Frontmatter-only is the whole point of the per-file
   format: the scan stays cheap once hundreds of observations exist.

   **An empty scan in a log known to be non-empty is a broken command
   until proven otherwise**, never the finding "no relevant observations".
   Count the files independently of the parse — a literal path, not the
   variable the loop uses — and halt if files exist but nothing parsed.
   Re-derive every path inside the same tool call: shell state does not
   carry between calls in most harnesses, and a path variable that
   silently resolves to empty turns a filter into a match-nothing glob
   rather than an error.

   ```bash
   d=skill-observations/observation-log                                # re-derive in every call
   n=$(ls skill-observations/observation-log/*.md 2>/dev/null | wc -l) # literal path: independent of $d
   parsed=0
   for f in "$d"/*.md; do
     [ -e "$f" ] || continue
     hdr=$(awk 'NR==1 && /^---[[:space:]]*$/ {fm=1; next}
                fm && /^---[[:space:]]*$/ {exit}
                fm' "$f")
     [ -n "$hdr" ] && parsed=$(( parsed + 1 ))
     printf '%s\n---\n' "$hdr"
   done
   if [ "$n" -gt 0 ] && [ "$parsed" -eq 0 ]; then
     echo "SCAN COMMAND BROKEN — $n files present, 0 headers parsed"; exit 1
   fi
   ```
3. **Review trigger.** Read `skill-observations/last-review-date.txt`. The
   value carries the truth: a date = when the last review actually ran;
   `never` = no review has run yet. A missing file is abnormal (step 1
   creates it) — recreate it with `never`, don't invent a date. If the
   value is `never` or older than 7 days and there are OPEN observations:
   in an interactive session, offer the review in one line ("the
   observation backlog hasn't been reviewed [in N days / yet] — run it now,
   or carry on with your task?") and proceed with the user's task unless
   they opt in; never gate their work on the review. Only a
   scheduled/autonomous run loads `references/weekly-review.md` and runs
   the review unprompted.
4. **Activation.** Once per session: if no CLAUDE.md (or equivalent)
   activation instruction for this skill exists, briefly suggest adding one
   (see `references/environments.md`). Skip if already configured.
5. **Concurrency.** There is no shared log file to guard: each observation
   is its own file, so creating one never collides with or overwrites
   another session's entry. Before changing the *status* of an existing
   observation, re-read that one file first (a parallel review may have
   resolved it).
6. **Targets and staged work.** Resolve each distinct `skill:` value in
   the scanned frontmatter against the installed skill set and mention, in
   one line, any that no longer resolve — a deleted skill can accumulate
   dozens of observations before a review discovers the target is gone.
   If `skill-updates/PENDING.md` lists staged updates, say "N staged
   updates awaiting review" in one line.
7. **First run.** If the log is empty and the project has history
   (handover or decision docs, commit history, test scripts, an existing
   CLAUDE.md — which is largely a record of corrections nobody logged),
   offer a one-off backfill pass over those artefacts. Backfilled entries
   cite the durable artefact (file and section) in `session_context`
   instead of a session, and the same-turn immediacy rule is satisfied by
   one batched write. The pass is one-off; the scheduled review takes
   over afterwards.

## When to Observe

Active for the entire task session — execution, post-task feedback, review
discussion, meta-discussion about skills or methodology, and strategy
conversations about how work should be done. **The observation mindset
does not deactivate when the conversation shifts from doing the work to
discussing it**; review-phase feedback is often the highest-signal input.
Inactive only for casual conversation and quick factual questions with no
tools or deliverables involved.

## What to Watch For

**New skill:** a reusable multi-step workflow, a methodology the user
explains that no skill captures, a recurring task type, a process the user
describes as "I always do it this way". **Improve a skill:** the agent
violates a documented rule (the skill needs enforcement, not louder rules);
a user correction reveals a missing rule or edge case; a better workflow or
technique emerges than the skill recommends; a wrong assumption; new
tooling obsoletes a step; a principle that applies to other skills too.
**Simplify a skill:** a section never relevant across many sessions, a rule
from a single unvalidated observation, contradictory rules, a rule the
agent consistently fails to follow — convert to structural enforcement or
remove. Full catalogue with examples: `references/signals.md`.

**Do not log:** one-off corrections that don't generalise; preferences
already captured in a skill; tool bugs unrelated to methodology;
observations that would need proprietary client information to be useful
in an open-source skill (unless an internal skill is the right home). The
generalisability test, when unsure: would this still make sense in another
project, and for another task using the same skill? Does it name a missing
rule, step or principle rather than fix this task? Is it likely to recur?
Mostly no → task context, not an observation. Before minting a
`proposes_skill` name, check the existing candidates and reuse a fitting
one — independently logged proposals for one skill rarely share a name.

**Validate the target at write time.** A name in `skill:` must be a skill
that exists now; if it doesn't, the observation proposes a skill instead.
Checking is cheap at write time and expensive forty entries later.

**Check the target's siblings at write time, and record that you did.**
Libraries accumulate *families* — several skills implementing one
methodology for different tools, one structure for different subjects, one
companion pattern for different base skills. An insight found while using
one member usually applies to the rest, but nothing in the workflow asks,
so `skill:` collapses to a single entry and the family silently diverges.
Before writing, resolve the target against the family registry
(`skill-observations/skill-families.md`; spec, coherence models and the
no-registry fallback in `references/observation-log.md`), and for each
sibling either add it to `skill:` or state in the body why it does not
apply. Fast test: **could this sentence survive having the tool's or
subject's name removed?** If yes it belongs to every sibling — and a rule
that declares itself generic inside one artefact ("this applies to any
file-writing script, not just X") is the cheapest possible propagation
signal, so treat that phrasing as an automatic multi-skill flag. Then
record the outcome in the mandatory `siblings_checked:` frontmatter field,
including the verdict "checked — instance-specific, no propagation": a
one-entry `skill:` list is byte-identical whether the siblings were
evaluated or never considered, and only the recorded field makes the
*absence* of the judgement visible to a review or a drift audit.

## How to Log

Write the observation file **silently, within the same turn or the next** —
never batch mentally for later; the act of writing is the enforcement
mechanism.

**Mandatory checkpoint after every 3rd completed todo item.** After marking
the 3rd, 6th, 9th (etc.) item complete, you must **write to disk** — not
merely ask yourself whether anything is pending. Either write any pending
observation files, or, if genuinely none have accumulated, append a
one-line `no observations` acknowledgement to
`skill-observations/checkpoints.log`. The required action is a concrete
write; a remembered "ask whether" is not enforcement. The count need not be
precise; roughly every third completion is the rule. (Exception: where the
workspace is a shared hosted document store in which every write is priced
and invalidates other sessions' context, suppress the empty marker and
keep only the check — see `references/environments.md`.)

**A denied or failed write is not a read-only log.** Retry once before
concluding the workspace is unwritable, and try a second tool that reaches
the same path — a permission classifier can deny one interface while
allowing another, and consecutive denials from a probabilistic gatekeeper
are noise, not a wall. Report "failed N times", never "cannot be done",
unless retries and alternate interfaces are actually exhausted; otherwise
observations are silently lost for the rest of the session.

**Deliverable-event flush.** Whenever you present or render a major
deliverable — a file handed to the user, a deck or PDF render, a staged
skill file — or complete a task/todo batch, write any pending observation
files at that moment, before moving on. These checkpoints already involve a
tool call; piggy-backing the flush onto them makes the write a side effect
of work you were doing anyway. (Why both checkpoints are writes rather than
questions: `references/observation-log.md`.)

**Two gaps this pairing still leaves — both observed across full working days
in which nothing was logged at all.**

1. *A session can contain no todo items whatsoever.* The 3rd-completion
   checkpoint is bound to one tool; work driven entirely through direct tool
   calls and shell commands never trips it. It is armed only in sessions that
   happen to use todos, so it is not a safety net that is always present. When
   a session runs without them, the deliverable flush is the only enforcement
   left and must be applied deliberately.
2. *"Is this a major deliverable?" is a self-assessment, and self-assessment is
   what fails under load.* Prefer triggers unmistakable in the tool record over
   ones needing a judgement call. In particular, treat any **project-completing
   command** — a deploy, release, publish, or push — as a flush point: it is a
   concrete tool call, as hard a trigger as a completed todo, and it reliably
   marks the end of a unit of work where insights have accumulated.

The rule behind both: an enforcement trigger must hang on an event objectively
visible in the tool record, never on the agent noticing that a moment qualifies.
And a counter bound to a single tool is silently inert in every session that does
not use it — such triggers always need a second, independent path.

**Id and filename.** Each observation is `NNNN-short-slug.md` (zero-padded
id + a kebab-case slug from the title). The id is the highest of three
values, plus one: the highest numeric prefix in `observation-log/`, the
highest in `observation-log/archive/`, and the number in
`observation-log/archive/.id-floor` (the highest id ever issued — update it
whenever you issue an id above it, so the counter can never restart from 1
when the active directory is empty):

```bash
d=skill-observations/observation-log
hi=$( { ls "$d" "$d/archive" 2>/dev/null | grep -oE '^[0-9]+'; cat "$d/archive/.id-floor" 2>/dev/null; } \
     | sort -n | tail -1); : "${hi:=0}"
[ "$hi" -eq 0 ] && [ -n "$(ls "$d"/*.md 2>/dev/null)" ] && { echo "ID COMMAND BROKEN — log is non-empty but no ids extracted"; exit 1; }
next_id=$(( hi + 1 )); echo "$next_id" > "$d/archive/.id-floor"
```

The guard line distinguishes "the log says zero" from "I could not read
the log": a command that fails to empty rather than to error would
otherwise propose id 1 in a populated log. A new file never touches another entry's bytes, so it cannot truncate,
overwrite or renumber anyone else's work. If two parallel sessions pick the
same id, two files share a number — harmless; the next review renumbers one
and logs a meta-observation.

**Batch writes: resolve each id at its own write time.** When logging more
than one observation in a session that may overlap a scheduled review or
another writer, run the id snippet before each file — never pre-compute a
range and hardcode sequential numbers into a batch. A batch append is N
separate races, not one; pre-baked numbers collapse N independent
max-checks into a single stale read (observed: a hardcoded id collided
with one a parallel review issued between the check and the write).

**A structural probe that comes back empty where content existed before is
a stop signal, not a create.** If the directory or file you logged to
earlier in the session is suddenly missing, or the id check returns empty
in a log you know is populated, halt and re-probe the structure (is there
an `observation-log/`? a `log.md.migrated`?) — a parallel session may have
migrated or reorganised the storage. Never let an append silently recreate
a missing target: that converts a migration signal into corruption
(observed: a stale session recreated the retired `log.md` with a fresh
"Observation 1" after the per-file migration renamed it).

**File format.** YAML frontmatter (the metadata every scan reads) followed
by the Issue → Improvement → Principle body. **The frontmatter is mandatory;
always write `status: open` and a non-empty `siblings_checked:` at creation
time** — an observation without a `status` field is treated as OPEN by
reviews, never as nonexistent, and one without `siblings_checked:` counts
as logged without a sibling check.

```markdown
---
id: [N]
title: [Short descriptive title]
status: open            # open | actioned | declined | superseded | parked
type: open-source       # open-source | internal
skill: [list of existing skills this improves — always a list, even with
       one entry; first entry is primary; may be empty]
proposes_skill: [list of new skills this argues for, by working name;
       may be empty — an observation can fill either list or both]
siblings_checked: [mandatory, never blank: the family name and the members
       evaluated, plus the verdict — e.g. "family-name: a, b — shared, both
       added" or "family-name: a, b — instance-specific, no propagation";
       the literal `none` only where the target belongs to no family]
area: [which part of the skill or workflow]
date: [YYYY-MM-DD]
session_context: [what task was being worked on]
parked_until:           # mandatory when status is parked, empty otherwise:
                        #   one line naming the condition that unparks it
resolved:               # date resolved; leave empty while OPEN
resolution:             # what was done — set only when actioned/declined
reference:              # optional: path to saved session-local evidence
---

**Issue:** [What happened — specific enough to understand weeks later
without the original conversation.]

**Suggested improvement:** [Concrete change. For existing skills, name the
section or rule; for new skills, scope and key components.]

**Principle:** [The generalisable takeaway — the most important field.]
```

**`parked` means decided, not pending.** Use it when an observation is sound
but cannot be acted on until an external precondition is met — the scheduled
task that produced it is disabled, the tool it describes is out of use, a
dependency has not landed. A parked entry is out of the work queue: reviews
must not re-escalate it, and the decision belongs in `status:`, not in a
free-text note beside a `status: open` (a note nothing classifies on leaves
the entry in the queue and it gets re-raised at every review). It is not
resolved either, so it never archives — archival needs a resolved status plus
a `resolved:` date. It stays in `observation-log/` indefinitely until either
its `parked_until:` condition is met — set it back to `open` and queue it — or
it is genuinely resolved. `parked_until:` is mandatory whenever status is
`parked`: one line stating the condition, phrased so a later session can
actually answer whether it has happened.

**Context preservation:** if an observation depends on session-local data
(uploads, API output), save that context into the workspace first and set
`reference:` to its path — an observation whose evidence dies with the
session is incomplete.

**Confidentiality at logging time:** for `type: open-source` observations,
the Issue/Improvement fields may reference specifics for context, but the
Principle must be fully generalised — no client names, domains, or details
traceable to a real project. Full confidentiality layers:
`references/skill-authoring.md`.

**Changing an existing observation:** re-read that one file, edit only the
frontmatter fields you are changing (`status`, `parked_until`, `resolved`,
`resolution`),
never batch-rewrite the directory. Archival is a plain `mv` (below).

## Referencing Observations

Cite an observation by the `id` field in its frontmatter (= the `NNNN-`
filename prefix). Never cite a `grep -n` line number as if it were the id —
search-tool line numbers are positional metadata, not identifiers. A cited
id must fall within the range that exists across `observation-log/`,
`archive/` and `.id-floor`; a number far outside it is almost certainly a
line number misread as an id.

## Taxonomy (quick version)

**Open-source** — client-agnostic, methodology-driven, useful to other
practitioners. **Internal** — contains user/client/project specifics or
personal preferences. Default to open-source when it could go either way,
stripping specifics. The boundary is also a confidentiality boundary, and
the two errors are not symmetric: over-classifying as internal costs only
reach, under-classifying can leak — when genuinely uncertain, prefer
internal and promote later. Full requirements (attribution, licensing,
structure): `references/skill-authoring.md`.

## Archival on Write

On every write, first `mv` already-resolved files from `observation-log/`
to `observation-log/archive/`. "Already resolved" is read from the file's
own frontmatter: `status: actioned`, `declined` or `superseded` and a
`resolved:` date **before today**. Files resolved today stay until the next
day, whichever session resolved them — the grace period lives in the file,
never in session memory. A resolved file with no readable `resolved:` date
gets today's date written to that field instead of being archived. One
file per `mv`; no rewrite of anything else. Helper and rationale:
`references/observation-log.md`.

## Surfacing Protocol

Default: at end of session, as a grouped summary — improvements grouped by
skill, new-skill candidates listed separately; for each, one sentence plus
suggested type; ask which to act on. Surface earlier when an observation
needs user input to be complete, when a skill is actively producing wrong
output, or when observations cluster on one skill.

**Deferral wears a second disguise: not a promise, but an argument.** "Let's
wait until this has seen a few days of real use", "we should gather more data
first" — this reads as diligence, which is exactly why it goes unchallenged,
including by the person saying it. It is not an announcement, so a rule about
executing rather than announcing does not catch it. So before writing *any*
"later" into a recommendation, name two things: **which specific observation
would change the decision, and when it could realistically arrive.** If you
cannot name one, the evidence is either already conclusive (act now) or waiting
adds nothing (act now). Then ask what the delay costs — if a known-defective
state stays live meanwhile, the burden of proof is on deferring, not on acting.
A deferral is a decision and needs the same justification as acting; "more
evidence would be better" is not one, because the question is whether more
evidence could change the outcome.

**Default to log-and-defer.** Surfacing an observation is not an invitation
to act on it: state that it is logged for the next review, and stop.
Reserve in-session application strictly for the triggers under "Acting on
Observations". Do not routinely offer a binary "apply now vs leave for next
review" choice; for users who run regular reviews that offer is unwanted
friction, and if a user has said they always defer, suppress it entirely.

**Self-check before surfacing:** observations were logged throughout the
whole session (including discussion phases); logged silently; each follows
Issue → Improvement → Principle; each is typed; existing-skill items name
the section; no open-source Principle contains client-identifying info;
every observation file carries `status:` (`status: open` at write time) and
a non-empty `siblings_checked:` — if any lacks one, do the sibling check
now and record it rather than back-filling the field with `none`.

## Acting on Observations

Act only in three contexts: (1) the comprehensive review (load
`references/weekly-review.md`); (2) an explicit user request ("update X
skill", "act on observation #N"); (3) in-session correction when a skill is
producing wrong output the user should know about. Otherwise: log, don't
act.

**Read the full body before resolving, dismissing, fixing, or citing.** A
tracked item's title (observation, GitHub issue, ticket) is an index entry,
not its content — it compresses away the failure story, the reporter's
context, and often the proposed fix. Dismissal is the path with no
downstream checkpoint: a resolved or cited item gets reviewed later, a
dismissed one silently disappears. Harvest fix designs from issue bodies —
reporters frequently include the correct solution, which also settles
attribution. When a parallel agent logs a finding that appears to duplicate
your own, diff the two bodies, not the titles: two entries about the same
mechanism can carry opposite operational conclusions, and the second is
often the refinement, not the echo. Apparent agreement suppresses
verification more effectively than disagreement does, so this rule binds
hardest exactly where it feels least necessary.

When acting: small, clearly-additive, low-risk changes (a new rule, a
clarification, a factual fix) may be applied without waiting for the next
review — "directly" means *now*, not *in place*: the edit is still made on
a staged copy based on a fresh read of the live file and handed to the user
to install, in every environment and every context. Staging-only has no
interactive exception; an exception the user has to remember is a gate
that eventually gets left open. Substantial changes (restructuring, new
capabilities, changed methodology) and all new-skill creation: load
`references/skill-authoring.md` first and follow its editing and staging
rules. A principle that applies to skills generally goes to the
cross-cutting principles file (same reference).

**Set the status in the same turn you act.** An observation acted on
in-session must have its frontmatter updated — `status: actioned`,
`resolved: YYYY-MM-DD`, `resolution: what was done` — before the turn
ends. The work and the bookkeeping are two acts, and the second is the one
that gets dropped; a stale `open` entry then invites redoing finished work
over a section that has since moved on. The write is the enforcement,
exactly as it is for logging.

## Before you return

Run this check on the output. If any item fails, fix or HOLD — do not
hand over a log entry, a date, or a skill edit.

- Intake was complete, or you HOLDed on the missing item
- The workspace is the stable path, not an ephemeral checkout
- You scanned frontmatter only; an empty parse of a non-empty log stopped
- You did not invent an observation or a backlog
- You did not invent a date (`last-review-date.txt` is `never` or a
  finished-review day; observation `date:` is the write-time clock or omitted)
- A single unvalidated observation was not promoted into a live skill rule
- Writes that failed were retried once and tried on one other interface
- You did not recreate a retired `log.md` or a second empty log
- Acting happened only in a review, an explicit request, or a wrong-output
  correction — otherwise you logged and deferred
- Open-source Principles name no client, domain, or real project
- You did not stall because a `references/` file was missing
- An interactive review did not gate the user's task

## What this process changes

The recipe is not a neutral mirror. Running it changes the work:

- **Frontmatter-only scan becomes the object.** Later agents act on
  `title`, `skill`, and `status`. The failure story in the body is
  invisible until someone reads it. A review that buckets from titles
  will split the corpus wrong, and the recipe's cheap scan is what
  licensed that.
- **Same-turn logging is a tool call that interrupts the task.** The
  observer spends a write on every insight. Under load the agent either
  skips the write (lost insight) or pauses the user's work to keep the
  log honest. The recipe chooses the pause. That is not free observation.
- **Default log-and-defer leaves a known-defective skill live.** An
  observation that names a wrong rule waits for the next review. The
  recipe treats delay as diligence. The user keeps hitting the defect.
- **The 7-day batch can rot or over-apply.** Insights age in `open`
  until a review fires; then they land in bulk on a staged copy. A
  week-old correction may no longer match the live file. The cadence
  the recipe chose is the distortion.
- **A single observation wants to become a rule.** The write itself
  feels like progress. The recipe now forbids promoting it, but the
  pressure to "do something" with a logged file remains — and a later
  agent who skips the candidate-lock will bake one session into the
  library.
- **Sibling / family propagation over-applies.** "Could this sentence
  survive without the tool name?" flags generic insights across a
  family. A locally true note becomes a rule on siblings it was never
  seen on. The family registry is the recipe's spreading mechanism.
- **Self-assessment of "major deliverable" fails under load.** The
  recipe already names this. Prefer tool-record triggers. The remaining
  distortion: sessions with neither todos nor a completing command have
  only session-end, and session-end is itself a self-assessment.
- **Watching for skill opportunities changes what the agent attends to.**
  The task becomes a source of log lines. Corrections get framed as
  methodology. A one-off preference can be stretched to pass the
  generalisability test because the observer is looking for a pass.
- **Backfill from git history, handover docs, or CLAUDE.md invents a
  past the observer did not live.** Those artefacts are durable, so the
  recipe allows one batched write. They are not live friction. The log
  then contains observations no session actually had.
- **Dates, if invented, become a false history.** A setup `today` in
  `last-review-date.txt` hides that no review has run. A remembered
  observation date makes recurrence look older than it is. The recipe's
  clock lock exists because the observer is the thing that would fake
  the timeline.
- **The observer is itself a skill.** It accumulates observations about
  other skills, including this one. Run long enough and the library
  over-fits this agent's habits. That is the observer writing itself
  into the corpus.

What still needs a human, and cannot be supplied by this recipe: whether
to act on an observation now or wait for review; whether one sighting
is enough to change a skill; whether to approve a staged substantial
edit or a new skill; open-source vs internal when the line is unclear;
whether a `parked_until:` condition has been met; whether to run the
review this session; whether a backfill artefact was real friction or
just a leftover file; and any live install of a staged skill. The output
is observation files, a HOLD, or a staged copy. It is not permission to
change how the user works.

## Quick Reference

| Question | Answer |
|----------|--------|
| When do I observe? | The whole session, including feedback and reflection phases |
| How do I log? | Silently, immediately, as one file per observation named `NNNN-slug.md`; id = max(active, archive, `.id-floor`) + 1 |
| When do I surface? | End of session, or earlier if needed |
| Status field? | Mandatory `status: open` frontmatter on every new observation; reviews treat a missing status as OPEN, never as nonexistent. Five values: `open`, `actioned`, `declined`, `superseded`, `parked` — `parked` = decided but blocked on an external precondition, so it leaves the queue, requires `parked_until:`, and never archives |
| Does the target skill have siblings? | Resolve it against `skill-observations/skill-families.md` before writing; add every sibling the insight applies to to `skill:`, and record the verdict in the mandatory `siblings_checked:` field — including "checked, no propagation" |
| A scan or query came back empty? | Two possibilities, only one is a finding: guard every retrieval meant to prevent duplicate work with an independent existence check, and treat empty output over known content as a broken command |
| Citing an observation number? | From the `id:` frontmatter field (= the `NNNN-` filename prefix); never a `grep -n` line number; sanity-check against the known id range |
| Open-source or internal? | Default open-source; the boundary is confidential |
| Small fix or substantial? | Additive → apply directly; restructuring/new skill → `references/skill-authoring.md` |
| Changing an observation (status/archival)? | Re-read that one file, edit only its frontmatter, or `mv` it to `observation-log/archive/` — no shared-file rewrite |
| Upgrading from a single-file `log.md`? | Scripted, once — `references/migration.md` |
| Weekly review? | Trigger check at session start; procedure in `references/weekly-review.md` |
| No filesystem? | Handoff-doc mode — `references/environments.md` if present; otherwise keep an in-session note and do not pretend a log exists |
| Companion file missing? | Use the method card in this file. Do not stall. Do not create the file. |
| May I invent a date? | No. Clock at write, or omit the field and HOLD. Setup writes `never`. |
| One observation → a skill rule? | No. It stays `open` until a later session or a review confirms it. |
