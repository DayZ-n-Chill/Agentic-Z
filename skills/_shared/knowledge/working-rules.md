# Working rules for DayZ modding with an AI agent

Tier 3 pack: the process rules for any DayZ worker. Load it when planning how to verify, test or record DayZ work. Tier 1 (`.claude/CLAUDE.md`) and Tier 2 (`skills/_shared/dayz-conventions.md`) still apply and win where they are more specific.

The rules are process rules learned while shipping mods. They are not checked on `P:\` as game facts; the vanilla lines cited below are examples, each opened on `P:\` for this file.

## The four rules

Keep these even when everything else is adapted.

1. **Never invent an API.** DayZ punishes a made-up name with a silent failure: a class that never binds, an action that never appears, a model that loads white. Before writing any Enforce Script call, config class, `.p3d` selection or memory point, grep the vanilla source (`P:\scripts\`, folders `1_core`, `3_game`, `4_world`) or a pack file, and cite `path:line`. Semantic search and memory are hints; open the file. Two examples of why: the vanilla recipe hook really is spelled `RegisterRecipies` (`P:\scripts\4_world\classes\recipes\recipes\pluginrecipesmanagerbase.c:14`), and the old JSON loader `JsonLoadFile` still exists but is marked DEPRECATED in favour of `JsonFileLoader.LoadFile` (`P:\scripts\3_game\tools\jsonfileloader.c:99` to `:105`; `LoadFile` is at `:7` of the same file).
2. **Respect the client/server split.** Decide which side owns each value before writing the feature. Most "it doesn't work" bugs are a value read on the wrong side. The RPC call itself says which way it travels: called on a client it runs on the server, called on the server it runs on all clients unless a recipient is given (`P:\scripts\3_game\gameplay.c:111-117`).
3. **In-game tests cost 3 to 10 minutes each.** Exhaust offline analysis, batch every pending change into one test, and have a plan B (and C) before asking for a rebuild. Two rebuilds with no progress mean the strategy is wrong, not the fix.
4. **Be honest about verification.** Say what was checked, how (grep, checksum, repro, in game) and what was not. "It compiles" is not "it works". An error of exactly 0.000 in a test is a tautology, not a triumph, and a catastrophic result indicts the instrument just as loudly as a perfect one.

## Three more working conventions

5. **Trace an invariant to every call site.** When a change alters a system invariant, not just a local bug, grep all the sites that assumed the old one and propagate the fix. The classic bug is "fixed it here, forgot the adjacent site".
6. **Walk it end to end before declaring it done.** Compiling is not correct. Mentally run the happy path, then kill the process between each pair of I/O steps (crash recovery), then re-check the admin and reset flows. Data-critical code (persistence, state machines, admin commands) gets a data audit before release.
7. **Keep a durable memory outside the agent.** An assistant's context dies at the end of the session. Without somewhere to put what was learned, every session re-derives the same facts, re-proposes hypotheses that were already refuted and pays again for the same in-game cycles.
   - What earns a note is narrow: a verified API with its `path:line`, an assumption that turned out false and why, a decision and the alternative it rejected, a bug and the measurement that found it. Not transcripts and not summaries of what was done; those are recoverable from git.
   - Convert relative dates to absolute ones. "Last week" ages badly.
   - Before real, multi-session work, ask the human which durable memory they will use, and offer to create the skeleton: project brief, verified APIs, assumptions, decision log, bug ledger, session handoffs. An Obsidian vault (plain Markdown files, `[[wikilink]]` links between notes) works; any plain-Markdown folder in version control works the same way. In this repo, user and machine notes go in `.claude/local-memory/` and agent memory in `.claude/agent-memory/` (Tier 1).
   - Three surfaces, three jobs: git is the distributable source, the notes vault is durable memory and full evidence, installed skills are the operational copy. Knowledge flows outward from the notes into skills; a release is never built from an installed copy.

## Evidence rules

- Verify a DayZ or Enforce Script API in the real source for the targeted build and cite `path:line`. A search result alone is not evidence.
- Record unknowns as unknowns. Project history is not a current runtime guarantee.
- Keep crash, exception, corruption, degradation and cosmetic findings distinct.
- A persistent or network-format change documents how legacy data is read, what rollback does with data written after the change, and an alternative that does not change the format when one exists. The entity stream hooks are `OnStoreSave` and `OnStoreLoad(ctx, version)` (`P:\scripts\3_game\entities\entityai.c:2910` and `:2978`).
- Label examples. `[EXACT]` only for content verified against the cited source; `[DESIGN]` for pseudocode or a proposal that still needs checking for the implementation at hand.
- Discover before generating: search the packs, the vanilla scripts and the official documentation before writing a competing rule or tool.
- Test the smallest contract first: positive and negative fixtures before the implementation.

### Verification levels

The compatibility matrix (`docs/compatibility-matrix.md`) and the skills use these words with these meanings.

| Level | Meaning |
|---|---|
| `runtime_verified` | Observed in a real DayZ run. Needs a dated, reproducible test artifact. |
| `source_verified` | Exact contracts checked against local vanilla or project source for the target build. |
| `offline_tested` | Exercised with deterministic local tests, without DayZ. |
| `cross_checked` | Reconciled against more than one source or project corpus. |
| `historical` | Kept from dated project evidence; needs revalidation when reused. |
| `unverified` | No sufficient evidence. Never read it as compatible. |

Absence of a listed breaking change means unknown, not none.

## When the game updates

- Before adopting a DayZ stable update: pin the exact build, diff the relevant vanilla contracts, rerun the offline checks, then run the smallest representative batch of in-game tests. Record evidence and unknowns in `docs/compatibility-matrix.md`.
- A vanilla line number belongs to one build. Measurements keep the build they were made on: something measured in game on one build is evidence for that build only.
- The skills and packs target DayZ 1.30 or later. Single-track vehicles are a 1.30 feature: `MotorbikeScript` is at `P:\scripts\4_world\entities\vehicles\motorbikescript.c:53`, and the 1.29 stable scripts have no reference to it (checked on the 1.29 scripts on 2026-10-01; not re-checked here because `P:\` holds 1.30).
- Dependencies with their own release cycles are pinned per project. Nothing here promises compatibility with an unpinned VPP, Expansion, TraderPlus, TraderX, Blender or ML-tool version.

## Using tools

- Propose the tool before the expensive step, not after it fails. `docs/knowledge-pack-tools.md` has the tables: which tool for which symptom and which task.
- When a tool reports clean, say which check ran clean. "Preflight passed" without naming the contract does not say what was verified.
- A green offline check predicts that a module compiles and an asset loads. It does not predict that the engine behaves. Behaviour is the in-game step.

## Loading knowledge

- Load on demand, never wholesale. Route from the skill's `name` and `description`, load the one skill that matches, and open a `references/` file only when the procedure names it. Loading everything buries the answer under what is not needed.
- A knowledge note is consulted, not routed: open it when a skill points at it or when a fact the skill assumes is needed. Notes are still cite-then-verify against the vanilla source for the game version in use, because the engine moves.
- Mod names in the skills (`LFQuad`, `SUB_BRZ`/`BRZ`, `MercedesAMGLF`, `A6_SR2M`, `LF_VStorage`, `LFPowerGrid`, `KT-Roadkill`) name the mod a rule was measured on. The rules are general; the mod source is not in this repo. Treat the names as case-study labels.
- Angle-bracket tokens such as `<notes>`, `<research-notes>`, `<skills>`, `<claude-home>` and `<tmp>` in the skills stand for local paths that differ per machine; substitute your own. `P:\` is the standard DayZ work drive and is written as is.
