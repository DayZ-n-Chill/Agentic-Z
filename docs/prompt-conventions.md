# Prompt conventions

Why agent and skill files in this repo look the way they do. Read this before writing or editing anything in `agents/`, `skills/` or `.claude/skills/`.

## TL;DR

- **Agent file shape** follows the lean standard in `agents/agent-creator.md` ("What a good agent file looks like"): frontmatter, a role sentence, then only the sections the role needs, with plain sentence-case headings.
- **Inline caps directives** (`MUST`, `NEVER`, `ALWAYS`, `DO NOT`, `CRITICAL`) are behavioral — they can help a hard rule stand out, but only when used sparingly, and overuse makes recent models over-apply rules.
- **Lowercase prose for everything else.** Caps are a finite signal; spending them on decoration burns the budget you need for real rules.
- **Content rules** follow the caps rules below: check borrowed facts on `P:\`, write descriptions in the user's words, answer at the scope that was asked, and list a skill's copies before editing it.

## Why caps directives work

Capitalized directives like `MUST`, `MUST NOT`, `SHALL`, `SHOULD`, and `MAY` come from **RFC 2119**, the IETF's "Key words for use in RFCs to Indicate Requirement Levels." That convention is everywhere in the training data: protocol specs, security standards, API contracts, compliance docs. Whenever a document needed an unambiguous rule that a reader couldn't talk themselves out of, the author capitalized the verb.

LLMs have absorbed that pattern. Use caps rarely. Anthropic's prompting guide warns that recent Claude models follow the system prompt closely, so heavy emphasis ("CRITICAL: You MUST...") makes them over-apply a rule. Where a rule really is absolute, a capped verb can still help it stand out:

- *"you must not delete files"* — gets rationalized away ("the user clearly wants this resolved, deleting seems necessary…")
- *"you MUST NOT delete files"* — held to as a hard rule

Treat this as a writing habit, not a measured result.

## Why caps work *only when rare*

Caps function as a salience boost. The boost exists **because most surrounding text is lowercase** — caps stand out against the baseline. If a file is wall-to-wall `EVERY AGENT MUST ALWAYS DO X AND NEVER DO Y`, the model treats that as the author's normal voice and the emphasis evaporates. You end up with noisy prose AND no compliance lift — worst of both.

The signal is finite. Spend it on rules that, if violated, would mean the agent failed its job.

## How to decide whether to cap something

Apply this test to any directive you're tempted to capitalize:

> If I remove the caps and read the sentence aloud, does it still feel like an absolute rule?

- **Yes** → leave it lowercase. The grammar already carries the weight.
- **No, removing the caps would let the model rationalize an exception** → keep it capped.

Examples from the existing agents:

- `all code you write MUST conform to it` (the style-guide rule in `dayz-script-specialist.md`, `dayz-ai-specialist.md` and `dayz-persistence-specialist.md`; non-negotiable, blocks the work otherwise) — kept capped
- `You check; you don't fix. Never edit any file.` (`dayz-mod-reviewer.md`) — left in plain sentence case; read aloud, it is already absolute

Examples that would *fail* the test (and should stay lowercase):

- `you must read the file before editing` — already enforced by tooling, no rationalization risk
- `you should always be helpful` — vague, not actionable, no specific failure mode
- `IMPORTANT: this is a tip about formatting` — decoration; the word "tip" already framed it

## Agent file shape

The structure of an agent file is set by `agent-creator` (`agents/agent-creator.md`, section "What a good agent file looks like"). In short:

- Frontmatter: `name` and a third-person `description` that works as the delegation contract, with 1 to 3 short `<example>` blocks. Descriptions load into every session, so keep them short.
- Minimal `tools`. When the role needs memory, use `memory: project` and add no memory section in the body. Gate agents get no memory, and read-only roles get it only when they need it.
- Body: a role sentence, then only load-bearing sections (workflow, domain rules, constraints, handoffs, report), usually 10 to 60 lines.
- No `## NAME` heading and no PURPOSE / CAPABILITIES / INPUT / OUTPUT scaffolding. Use plain sentence-case headings such as `## Workflow` or `## Report`.
- Point at shared docs (`skills/_shared/...`) instead of pasting their rules.

Headings are for the reader, not the model; their case doesn't change behavior. The caps budget above applies to inline directives only.

## Quick checklist for writing a new agent or skill

1. Shape: match the `agent-creator` standard (role sentence, load-bearing sections only, references over inlining).
2. Inline caps: reserve `MUST` / `NEVER` / `ALWAYS` / `DO NOT` for actual hard rules. Apply the "remove the caps and re-read" test.
3. Default to lowercase prose. Trust the grammar.
4. If half the bullets in a section are capped, you've over-spent the signal — demote some to lowercase.
5. Facts: before writing a number, a base class list or a language restriction, check it on `P:\` and cite `path:line` (see "Facts borrowed from a related engine or language").
6. Description: name the system, the names a user would search for, the verbs they would type and the symptoms they would describe (see "Descriptions use the user's words").

## Facts borrowed from a related engine or language

When a skill documents a system that shares a family with a better documented one (Arma 3 and DayZ, SQF and Enforce Script, Python 2 and 3, Vue 2 and 3, React classes and hooks), the main risk is carrying knowledge over from the better documented relative without checking it again. The author assumes the two share values when they only share a lineage.

Cases recorded on 2026-05-12, each checked against the files rather than against a written audit:

- LOD type values. Earlier versions of a `.p3d` audit script classified ViewGeometry and FireGeometry with `2e13`, `3e13` and `7e13`, values quoted in Arma guides; they were wrong for DayZ and were corrected. The DayZ values and their vanilla evidence are in `skills/_shared/conventions/assets.md`.
- Base class lists. A validation list mixed base classes that DayZ has with names taken from Arma 3. Checked on `P:\` (2026-11-17): `HouseNoDestruct` exists (`P:\DZ\data\config.cpp:3119`); `Helicopter` exists too, as an engine config class (`P:\bin\config.cpp:1563`), although an earlier note called it Arma 3 only; no `class Motorcycle` is declared in `P:\bin\config.cpp`, and the vanilla motorbike script class is `Motorbike` (`P:\scripts\3_game\vehicles\motorbike.c:30`). A list like that is checked name by name against the vanilla configs before it goes into a skill.
- The audit that went looking for this contamination made the same mistake in the other direction. It reported concrete findings (a ShadowVolume range of `9e9..1.1e10`, a line in the audit script) that did not exist in the code it named; the bug it described belonged to an older version that was already fixed. Audits invent details too, so check an audit finding against the file it names before acting on it.

Before writing a number, a base class list or a language restriction into a skill for a poorly documented system:

1. Does it come from the system itself (the vanilla files on `P:\`, Bohemia's own repositories, the vanilla scripts)? Cite the `path:line` or the URL.
2. Or does it come from a related engine (Arma 3, SQF, an older version) and is assumed to apply? Then mark it "needs DayZ verification" until it is confirmed.
3. For a language such as Enforce Script, the authority is the compiler and the vanilla scripts. Cite them. Do not trust a community post without checking it against a real `.c` file.

A case that was "refuted" and then corrected (2026-05-12, updated 2026-07-06): an audit claimed that `?:`, `++`, `foreach` and `+=` are valid Enforce Script. The first check concluded that none of the four is supported, because four or five skills said so. The final result was split:

- `?:` (the ternary operator) does not compile. It stays forbidden (`skills/_shared/enscript/patterns/language_workarounds.md`).
- `++`, `foreach` and `+=` are valid. Vanilla uses them, for example `foreach (string s: types)` at `P:\scripts\3_game\billboardset.c:108`. The skills that listed them as forbidden were wrong and were corrected.

The lesson: several skills that repeat one claim are not several independent sources when they all inherited it from the same older note. Agreement between skills is not verification. One vanilla `.c` file that uses `foreach` outweighs five skills that say it does not exist.

## Descriptions use the user's words

The `name` and `description` of a skill decide whether it is picked when a user asks about its subject. A skill named in internal jargon, or after a technical name the user would never say, exists but is never found.

Example: a skill called `japm-pbo-recovery`. "JAPM" is the tool's internal identifier; the name people know is "PBO Tools". A user who writes "decompile PBO Tools", "recover PBO source" or "obfuscated PBO" does not reach that skill.

A `description` includes:

1. The technical name of the system, for precision.
2. The commercial or public product names tied to it: what the user would search for.
3. The verbs a user types, in the imperative: "decompile", "recover", "fix", "audit".
4. The symptoms of the problem, in the words a user has before they know the solution: "lost my source", "no source available", "obfuscated".

A description that follows the rule, for that skill:

> Recover source code from DayZ PBO files obfuscated with JAPM (also known as "PBO Tools"). Use whenever the user mentions "PBO Tools", "JAPM", "obfuscated PBO", "lost my source", "recover PBO source", "decompile PBO", ...

Trigger phrases in another language that a user might type stay in the description as extra entries next to the English ones. Keep the whole description to at most 1024 characters: move caveats and notes on how skills combine into the body instead of cutting the triggers (`scripts/dev/pack_skill.py` refuses a longer one).

## Depth of an answer

Recent models already tend to widen the scope and lengthen the answer on their own, and their harness already tells them to deliver what was asked at the scope it was asked. An earlier version of this rule said to go one level deeper by default, and that pushed the very failure that now has to be held back. The default is the scope that was asked for.

- A scoped task ("look up X for me", "what do you think of Y") is answered at that level. When the subject is complex and something substantial is left unsaid, offer it in one closing sentence: "I can go into alternatives, criteria and risks if you want."
- Do not pad the first turn with sections nobody asked for (matrices, five or more options, side audits), unless leaving them out would cost something that cannot be undone, such as a choice baked into a persistent format.
- Recommend before listing: at most three options, with the recommendation first, not a catalogue.

Words the user sets the level with:

| Word | Depth |
|---|---|
| "fast", "brief" | 2 to 4 sentences at most |
| (none) | the scope asked for, without going a level up |
| "deep", "in depth", "with math", "audit" | exhaustive |

Once the level is set, keep it for the whole session unless the user changes it.

Where the rule came from: in a session on 2026-05-12 a "look this up for me" request got an answer that was too shallow, and the user had to ask for a broader search and a mathematical analysis. That failure was real, but the fix is not a deeper default everywhere. It is reading the context the session has built up: a complex subject with a history of iteration calls for depth, and a scoped request with no history does not.

## Editing skills: list the copies first

In this repo the source of a skill is its folder under `skills/` or `.claude/skills/`. Sessions edit that folder directly; nothing is packaged and handed over for each change. What replaces a permission step is a count of the copies.

### Count the copies before you edit

A skill can be visible from several places, and writing to one of them leaves a difference nobody sees until someone reads the stale copy. Before you change a skill, list where it lives and sort links from real copies before you count:

```
<repo>\skills\<name>                 the source in this repo
~\.claude\skills\<name>              read by Claude Code; a link when /sync-skills --agents claude made it
~\.agents\skills\<name>              read by Codex; a link made by /sync-skills
~\.gemini\skills\<name>              read by Gemini; a link made by /sync-skills
a plugin install or app copy         a real copy of its own; it does not follow the repo
```

`/sync-skills` makes symlinks, or junctions when symlinks need elevation, so those entries follow the repo by themselves. Write to every real copy; the links are already covered. When you finish, compare by sha256, not by modification time. Check that an entry is a link; do not assume it.

Measured in the Claude desktop app (2026-09-01), for skills installed there instead of in a repo:

- The app keeps its skills in a plugin tree (`...\skills-plugin\<guid>\<guid>\skills\<name>`). There can be several GUIDs, and they are different plugins. A projection for another tool (`~\.grok\skills\<name>` on that machine) was a junction into the plugin copy, so one write covered both views, but that was checked, not assumed.
- A folder does not say what governs it. The plugin's `manifest.json` does: for each skill it holds a `skillId`, `enabled`, `creatorType` and `updatedAt`. Open it before concluding that a skill is orphaned. On that date six skills were taken for orphans that were registered and enabled, and the "rescue" left the fix in a copy nothing read while the served copy stayed broken.
- An edit to the plugin copy stays on disk (the sha stayed the same for minutes) but does not change the registry's `updatedAt`. The edit is local: if the app syncs from the server again, it is lost. When a change has to survive that, tell the user.

### Guardrails that still apply

1. In the app's plugin tree, write straight to disk with PowerShell, never with the harness's Edit or Write tools: there they go to an overlay view that drifts from the real disk. Reading through the harness to package a skill is fine.
2. Make a backup before the write, and read the file back after it, every time.
3. Give a sweep a positive control. When your final check finds nothing, run it on the version from before the fix. If it finds nothing there either, the detector is broken, not the file clean.
4. In PowerShell, text you write goes in single quotes (`'...'` or a here-string `@'...'@`), never in double quotes. Inside `"..."` and `@"..."@` the backtick is the escape character and `$` interpolates, so a Markdown code span whose text starts with `0`, `a`, `b`, `e`, `f`, `n`, `r`, `t` or `v` is corrupted with no error: writing `` "see `references/x.md` and" `` puts a carriage return followed by `eferences/x.md` in the file, and the closing backtick disappears. Measured on 2026-09-15 with PowerShell 7.6.5: `` "[`0][`a][`b][`e][`f][`n][`r][`t][`v]" `` gives the bracketed codes 0, 7, 8, 27, 12, 10, 13, 9 and 11; `` "`q" `` gives just `q`; `` 'x`ry' `` is written as it stands. It has happened: a section written that way on 2026-09-02 carried two stray carriage returns where the source said `` `references/routing.md` ``, and they stayed for 13 days. For a whole file, use `Copy-Item` from a checked copy. Reading the file back does not catch this, because the sha only proves the disk holds what you sent, not that you sent the right thing; also search for carriage returns that are not followed by a line feed (`\r(?!\n)`).

### When a `.skill` is packaged

Packaging is not the normal way to deliver a change. It is for taking a skill to a machine or a store that has no copy of it. When you package:

1. Run `python scripts/dev/pack_skill.py <skill folder> <destination directory>`. The second argument is a directory; without it the package goes to `output/skill-packages/`. Do not use skill-creator's `package_skill.py` on Windows: it reads `SKILL.md` without an encoding, falls back to cp1252 and stops with `UnicodeDecodeError` on any em dash, arrow or accent (3 of 8 skills failed there on 2026-07-27).
2. Installing a package replaces the whole folder; it does not merge. Package from the most complete copy, or the install deletes what the package lacks. In one measured case, a skill's app copy held six scripts that its own `SKILL.md` calls and that another copy did not have.
3. Package the whole skill: `SKILL.md`, `references/`, `scripts/` and `assets/`. A `SKILL.md` on its own installs a skill with its references missing, and a loose `.md` fragment does not install at all (`SKILL.md must start with YAML frontmatter (---)`).
4. The script leaves out `__pycache__`, `.git`, `.ipynb_checkpoints`, `.pyc` and `.pyo` (`EXCLUDE_DIRS` and `EXCLUDE_EXT` in the script), but not backup files such as `SKILL.md.bak`. When the folder holds backups, package from a scratch copy with the same folder name and delete them there.

`pack_skill.py` also checks that the frontmatter and its `name` are present, that the `description` is at most 1024 characters (shorten it by moving text that triggers nothing into the body, never by cutting it off), and it reopens the zip to check that entries use `/` and not `\`: PowerShell 5.1's `CreateFromDirectory` writes backslashes, and the installer then cannot find `<name>/SKILL.md`.
