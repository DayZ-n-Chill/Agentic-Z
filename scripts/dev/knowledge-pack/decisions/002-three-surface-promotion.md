> **SUPERSEDED 2026-08-18.** This ADR declared the Git repository as the only
> editable source. That is no longer the policy.
>
> - `~\.claude\skills\` is the **working copy**. It is where skills are
>   edited. The copy the agent loads is the one that is written.
> - The public MIT repository `DayZ-Modding-Knowledge-Pack` is the
>   **publication snapshot**. It receives harvest by UNION, never a wipe of
>   the destination.
> - The Cowork skills-plugin tree is an ephemeral projection. Neither source
>   nor destination.
> - Layer split: the pack is the OFFLINE layer; DayZ-MCP is the ONLINE/in-game
>   layer.
>
> The body below is kept for traceability.

# ADR 002 — Mandatory promotion to repo, Obsidian and skills

- **Date:** 2026-07-24
- **Status:** accepted

## Context

The user requires that all gathered knowledge also remain in Obsidian and
in the skills, in addition to being incorporated into the repository. Treating those three
surfaces as equivalent editable sources would repeat BUG-001: today the
fourteen baseline skills already diverge from their local copies.

## Decision

Each surface has a distinct role:

1. **Git** is the sole source of the distributable pack and of any ZIP/release.
2. **Obsidian** preserves the complete durable memory: evidence, local paths,
   research, decisions, unknowns, and the private version of each invariant.
3. **Installed skills** are operational deployments generated from a validated
   commit; they are not edited as independent sources.

All accepted knowledge must have durable routing:

- repo and Obsidian are mandatory;
- a domain invariant must also reach its active skill;
- `not_applicable` is only permitted for governance or tooling without a skill
  consumer, with an explicit reason;
- the public variant is sanitized; private evidence remains in Obsidian.

Promotion uses versioned logical targets and physical roots in unversioned
local configuration. It executes only after gates via
staging, full-tree validation, replace on allowlisted targets, and
hash readback. Each promotion produces a receipt with source commit, hashes,
destination IDs, and date, without private paths.

## Consequences

- No phase closes with `PROMOTION-UNROUTED` or `PROMOTION-DRIFT`.
- Phase 01 reconciles existing copies before the first promotion.
- A private finding may retain more detail in Obsidian, but its
  depersonalized invariant must reach the repo and applicable skill.
- Governance documents are not forced into a skill; they remain
  explicitly `not_applicable`.
- A partial promotion or unverified target is not presented as a success.
