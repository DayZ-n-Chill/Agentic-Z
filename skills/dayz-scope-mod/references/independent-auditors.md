# Independent auditors

How to keep parallel auditor agents on a DayZ mod from agreeing on the same mistake, and when a finding counts as verified. How to name what a fault does and which missing engine minimums crash is in `skills/dayz-launch-test/references/debug-protocol.md`, "Name what the fault actually does" and "Engine minimums to check early". To run a data critical audit use `skills/_shared/persistence/deep-audit.md` and `skills/_shared/persistence/data-audit.md`.

## Keep parallel auditors independent

Four auditor agents on a virtual storage mod agreed on invented findings because they had all read the same conventions document and carried the same bias. The agreement looked like rigour and was coupling.

For a multi-agent audit of DayZ code:

- Each agent checks against its own vanilla source or `path:line`.
- Two agents that read the same document may not cite each other as confirmation.
- At least one agent works adversarially: no access to the conventions document, only the real code, checking the others' findings.
- Recheck a random 20 percent or more of the findings before applying any. If they fail, discard the whole audit, not just the doubtful items; invention is systemic, not per item.

Signs that an audit invented its findings:

- Large round counts ("47 issues found") with no `path:line` per item.
- Defensive OR branches reported as bugs when they are deliberate tolerance, such as a `classify_lod()` helper that accepts both Arma 3 and DayZ LOD bands by design.
- Inflated severity: a VM exception or a cosmetic fault reported as a crash; compare with the terms in `debug-protocol.md`.
- Agreement between agents that should be independent but read the same document: shared bias, not triangulation.

## When a finding counts as verified

A finding counts as verified, and may be applied, only when all four hold:

1. It has a concrete `path:line` in real code, not in a document.
2. The code that breaks the rule is quoted.
3. The fix is quoted as a diff that applies.
4. At least one agent without the shared context checked it separately.

Otherwise mark it "possible invention" and do not apply it.

In this repo the review gates are separate agents for the same reason: `dayz-mod-reviewer` checks and does not fix, and `dayz-mod-debugger` diagnoses from the logs and names an owner. Check while you work, not only at the end, and report plainly what was and was not checked.
