# Audit escalation: severity discipline and independent auditors

How to label the severity of an audit finding on a DayZ mod, how to label the severity of something that is missing, and how to keep parallel auditors independent. `dayz-mod-workflow` points here. To run a data-critical audit use `skills/_shared/persistence/deep-audit.md` (its seven steps and parallel auditors) and `skills/_shared/persistence/data-audit.md`; this file is only the note on labels and independence.

The cases were measured on mod projects (a power-grid mod, a virtual-storage mod, a quad vehicle mod). The vanilla facts are cited on `P:\`.

## 1. Severity inflation in audit reports

The pattern, seen in audits of a power-grid mod: findings labelled "P1, crash" that were really "P2, recoverable VM exception, the server keeps running". The cause: going from a log message (`String CORRUPTED`) to a behaviour (the process dies) without checking.

Before writing audit findings:

1. Reproduce the bug on a local server (`/dayz-launch-test`; depth in its `references/` folder).
2. Log one complete cycle of the bug: load, execute, autosave, reload.
3. Tell these apart:
   - **crash**: the process dies, the server drops, a restart is needed.
   - **VM exception**: an Enforce Script VM exception, log spam, execution continues.
   - **corruption**: bad data persists and the code runs with it.
   - **degradation**: the feature works worse but runs.
   - **cosmetic**: visual only, no functional effect.
4. The finding's label uses the concrete term from step 3, never "crash" as a catch-all.

Measured case: in a review of audit findings, "Server boots: NO" in a before-and-after table was corrected by the user to "the server does boot, it just throws an error".

`/dayz-gate` already separates these in its own reports: a `crash*.log` or a process exit is a crash, and a script error line is triaged on its own.

## 2. Severity of absence, and the engine's minimums

Section 1 grades a bug that was observed. This section grades something that is missing. "The feature is incomplete" is not the same as "its absence crashes".

**Rule.** In any gap audit, label each finding by the severity of its absence: does lacking it crash or stop loading, or does it only leave a feature incomplete? An engine minimum deferred as a "high-level feature" can be a hidden P1 crash. Measured on a quad vehicle mod: `DamageSystem` was filed as a deferred "damage feature", and its absence gives `[Object::GetMaxHealth] No DamageSystemData` (a crash) as soon as health is touched (admin tools, damage, collision, sync).

**Engine minimums (anti-crash). Validate them early, apart from the feature tiers:**

- **Vehicle (`CarScript`).** `class DamageSystem { class GlobalHealth { class Health { hitpoints; healthLevels[]; }; }; }`. Without it any `GetMaxHealth` or `SetHealth` crashes (measured in game). Full `DamageZones` are a feature; `GlobalHealth` is the anti-crash baseline. Vanilla `OffroadHatchback` declares `class DamageSystem` with `class GlobalHealth` first and `class DamageZones` after it (`P:\DZ\vehicles\wheeled\config.cpp:1540-1577`). Check the part classes (wheels) too if their health is touched. Pack file: `skills/_shared/vehicles/damage.md`.
- **Vehicle.** A constructor that sets the engine sound strings (`m_EngineStart*`); left empty they give broken audio and possibly an exception from an empty sound set name.
- **Model `.p3d`.** A Geometry LOD with convex components and mass (without it the object does not simulate), and the action selections (`seat_*`, `refill`, doors) in the LOD the cursor resolves (View Geometry for actions, measured in game). Pack files: `skills/_shared/models/lods.md` and `skills/_shared/physics/collision-lods.md`; `/dayz-p3d-audit` checks the model.
- **Generic.** When an engine baseline is "deferred", put it in the plan as a **P1 anti-crash** item apart from the full feature, not in the late-phase bucket.

Process: a parity audit includes a pass over "engine baselines per subsystem" on top of the feature checklist, so crashes are not discovered one at a time in game.

## 3. Multi-agent audits: context isolation is mandatory

From a post-mortem on a virtual-storage mod: four auditor agents "converged" on confabulated findings because they had read the same conventions document and inherited the same bias. The convergence was read as rigour; it was coupling.

Rules for a multi-agent audit of DayZ code:

- Each agent verifies from an independent vanilla source or `path:line`.
- Two agents may not cite "X says the same thing" as cross-evidence when both read the same document.
- At least one agent runs **adversarially**: with no access to the conventions document, only to the real code, checking the others' findings.
- **Randomly sample at least 20% of the findings before applying them.** If they fail the adversarial recheck, discard the whole audit, not only the suspicious items. Confabulation is systemic, not per item.

Signs of a confabulated audit that call for a recheck:

- Large absolute numbers ("47 issues found") with no `path:line` per item.
- Defensive OR branches labelled as bugs when they are designed tolerance. Measured case: a `classify_lod()` helper with both Arma 3 and DayZ bands, where the OR branch is the design.
- Inflated severity (P1 on items that are P2 or P3). Cross-check with section 1.
- Convergence between agents that should be independent: if four agents "find" the same thing and read the same conventions document, it is shared bias, not triangulation.

A finding counts as **verified**, and may be applied, only when:

1. It has a concrete `path:line` in real code (not in a document).
2. The snippet that breaks the rule is quoted.
3. The fix is quoted as a diff that applies.
4. At least one agent without the shared context verified it separately.

Without all four the finding is marked "possible confabulation" and is not applied.

In this repo the review gates are separate agents for the same reason: `dayz-mod-reviewer` checks and does not fix, and `dayz-mod-debugger` diagnoses from the logs and names an owner. Verify while you work, not only at the end, and report honestly what was and was not checked.
