# Why this skill exists: the LF_VStorage 1.4.6 retrospective

The case study behind the audit procedure: six reasoning agents signed off a virtual storage mod as release-safe, and an outside auditor then found 12 vulnerabilities they had missed. Open this to see what each `VULN-nnn` label in the other files refers to and why each step of the procedure is there.

LF_VStorage is a third-party virtual storage mod. Everything below describes that mod's code and its audit; none of it is a fact about vanilla DayZ and none of it can be checked on `P:\`.

## What happened

LF_VStorage 1.4.6 went through an audit of several rounds before the user asked for a "release-safe?" verdict:

1. An external auditor handed in 6 P1 findings (lost-items class). Fixed.
2. The user asked for a second audit with several Opus agents to catch what was missed. Six parallel Opus agents were started from independent angles (persistence, state machine, async, hooks, admin, recovery). Each agent produced a coherent report. None found anything new.
3. The mod was declared "release-safe pending in-game test".
4. The user then handed in `AUDIT_HARDENING_IMPLEMENTER.md` from an external implementer-grade auditor. **12 VULNs (P0 to P3) the agents had missed.**

## The 12 VULNs

Listed here so the patterns are concrete:

| ID | Severity | Class |
|---|---|---|
| VULN-001 | P0 | Kill switch for an external virtual storage (VS) mod not durable across mission entry points |
| VULN-002 | P1 | `m_HasItems` not hydrated from disk on TrackContainer |
| VULN-003 | P0 | Path-helper inconsistency: `.tmp` against `.lfv.tmp` between writer and recovery |
| VULN-004 | P0 | Pre-super gate runs after vanilla super in EE hooks |
| VULN-005 | P1 | Shutdown queue mutated during iteration |
| VULN-006 | P1 | `migrate-all` admin command blocked by its own restore queue |
| VULN-007 | P1 | Degraded recovery deletes `.lfv` after a partial recovery: destroys recoverable data |
| VULN-008 | P0 | `DeleteContainerFiles` missing `.restoring` and `.manifest.json` |
| VULN-009 | P1 | `VirtualizeSynchronous` leaves a stale `.virtualizing` marker |
| VULN-010 | P0 | Admin recovery flags in memory only while the sidecar is removed |
| VULN-011 | P1 | LFV2 count fields lack sanity caps |
| VULN-012 | P2 | Non-authoritative JSON writes still best-effort |

## Why the agents missed each one

| VULN | Class | Why six agents missed it |
|---|---|---|
| VULN-003 | Path-helper inconsistency | Each helper looked correct in isolation. The bug is the **inconsistency**, not any one site. Reasoning agents trace happy paths. |
| VULN-008 | Sidecar cleanup missing | `DeleteContainerFiles` looked thorough: it deleted 6 of 8 file types. Reasoning agents check what is present, not what is missing. |
| VULN-009 | Sync entry-point divergence | The async path had been audited heavily. The sync path was "obviously similar". It was not. |
| VULN-001 | Mission entry-point divergence | `OnMissionStart` and `OnMissionLoaded` looked correct as a pair. The third entry point (server reload) was not in the agent's mental model. |
| VULN-010 | Two-store divergence | Admin recovery flags lived in `m_AdminRecoveryFlags`, separate from `m_QuarantineMap`. Each map looked consistent internally. |
| VULN-004 | Pre-super gate placement | The gate was present. The order within the EE hook was not visible from "is the gate there?". |
| VULN-011 | Threat model out of scope | Agents prompted "audit persistence" did not ask "what if the disk is hostile?". |
| VULN-002 | Initial-state hydration | The agent saw the field set on save and did not check that load restored it from disk. |
| VULN-005 | Iteration during mutation | The shutdown drain code was short and "obvious". Agents skipped the careful read. |
| VULN-006 | Self-blocking queue | The admin command queued itself behind work it was supposed to flush. It required cross-actor tracing (admin, queue, admin). |
| VULN-007 | Wrong cleanup action | "Delete after partial recovery" looked like cleanup; it was actually data destruction. It required understanding intent, not just code. |
| VULN-012 | Best-effort write | Easy to miss because "best-effort" feels like a reasonable error mode. The audit asks "is this state critical?"; if yes, best-effort is wrong. |

## The five lessons that drove this skill's design

### 1. Reasoning is bad at enumeration

Five of the twelve VULNs (003, 008, 009, 010, 011) were **mechanically enumerable**: a search plus a table walk finds each in under a minute. Reasoning agents underweight bookkeeping. The skill fixes this by running mechanical pre-checks **before** any reasoning review starts (workflow step 1).

### 2. Cross-actor tracing is the agent's weak spot

Three of the twelve VULNs (006, 008, 010) required tracing across modules: admin command to queue to state machine, or writer to cleanup to boot scan. A reasoning agent prompted "audit module X" looks within X. The skill fixes this by adding a dedicated **implementer-grade pass** in step 4 that explicitly demands cross-actor tracing.

### 3. Alternative entry points always diverge

Two of the twelve VULNs (001, 009) were alternative-entry-point bugs. Sync shortcuts, admin commands, mission-reload paths: they always skip something. The skill fixes this by adding a dedicated mechanical check (the entry-point audit) and a dedicated angle prompt (the action layer).

### 4. Confidence in good-looking code propagates between agents

Once one agent said "this module is fine", later agents implicitly trusted that reading. The skill fixes this by prompting agents to **not trust prior reports** (implementer-grade pass) and by starting the reviews in parallel so they cannot read each other's output.

### 5. Severity self-reporting is unreliable

The agents reported many P2 and P3 findings and zero P0. The implementer-grade auditor reported 6 P0 or P1. Agents systematically under-rate severity. The skill fixes this by having the user (or the main thread) assign severity during the step 3 consolidation, not the agent.

## What the skill is and is not

**This skill is not a guarantee.** Twelve VULNs is a snapshot of one auditor's findings. A more thorough auditor on the same code would find more. The skill makes the audit phase more rigorous, but in-game testing on real save data remains the final filter.

**This skill is a forcing function.** It exists because the user and the agent both know that an "audit" is easy to perform shallowly and hard to perform deeply. The seven-step workflow makes the deep version the default.

## Reading list

- `audit-prompts.md`: the eight angle prompts, the verifier prompt and the implementer-grade pass
- `path-naming-matrix.md`: finds the VULN-003 class
- `sidecar-cleanup-symmetry.md`: finds the VULN-008 class
- `entry-point-audit.md`: finds the VULN-001 and VULN-009 classes
- `flag-lifecycle-audit.md`: finds the VULN-010 class
- `state-machine-matrix.md`: the structural state-transition check
- `fact-audit-postmortem.md`: the second failure, an audit that was about 55% confabulated, which added step 3
