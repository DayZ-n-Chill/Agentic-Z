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

# ADR 001 — Canonical Git source and immutable baseline

- **Date:** 2026-07-24
- **Status:** accepted

## Context

The pack existed solely as three byte-identical copies of a published ZIP.
Editing installed skills, vault notes, and the ZIP separately would reproduce the
drift already observed: the fourteen skills in the archive diverge from their
current local sources.

## Decision

This repository becomes the sole editable source of the pack. The contents of the
previous ZIP were imported unchanged in the root commit
`d48e2c1a02dacc97645a9e70d8bc1058e6dae9a5`.

The source ZIP remains as an immutable fixture:

- SHA-256:
  `E63C26C5C385E3037B4AFE9C918B3A9DE9E12CC0AF876316214518BF852735E5`.
- Extracted files: 138.
- ZIP ↔ tree comparison: 138 present, 0 differing hashes, 0 extras.

Installed copies and the vault are inputs that are reconciled through an
explicit inventory; one source is never overwritten with another by date or
name alone.

## Consequences

- Every release will be built from a clean commit of this repository.
- Every pack↔source conflict will have a durable adjudication.
- Planning artifacts can live in Git, but the public builder
  will use an explicit allowlist.
- No remote will be published or pushed during this initiative without a
  separate request from the user.
