---
name: dayz-search-index
---

## Overview

Index vanilla DayZ source (Enforce Script, .layout, config.cpp, .rvmat) into a per-user vector database so DayZ agents can do semantic search via the dayz-rag MCP server. One-time setup; rerun with --full after a DayZ update. Required before agents can use the search_dayz_source tool.

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-search-index

Build a semantic-search index over vanilla DayZ source so DayZ specialist agents stop flying blind through `P:\` with `Grep`. Backs the `dayz-rag` MCP server.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## What it indexes

| Source | Files | Chunking |
|---|---|---|
| `P:\scripts\**\*.c` | Enforce Script (~2,800 files) | per class/method |
| `P:\gui\**\*.layout` | UI layouts (~210 files) | per top-level Widget block |
| `P:\dz\**\config.cpp` | Vanilla configs (~200 files) | per `class X &#123; ... &#125;` block |
| `P:\**\*.rvmat` | Materials (~35,000 files) | whole file, **content-deduped** by SHA-256 |
| `P:\**\*.xml` | XML (types, etc.) | batched 50 elements/chunk |

`model.cfg` is intentionally skipped — vanilla extracted data doesn't ship them.

## Where the index lives

`~/.claude/dayz-search-index/` (= `C:\Users\<you>\.claude\dayz-search-index\`)

- `lancedb/` — vector store
- `manifest.json` — embed model used, per-source chunk counts, indexed-at, **token usage + $ estimate**
- `config.json` — model name the MCP server should use at query time

Per-user, gitignored (lives outside the repo). Survives clones.

## Embedding via Voyage AI (cloud)

Embedding runs through Voyage AI's hosted API. Code-tuned model, much higher retrieval quality than local CPU options for our DayZ corpus. The trade-off is a network call per batch and an API key.

**Default model: `voyage-code-3`** — code-tuned, 32k context, 1024-dim. $0.18 per 1M tokens with **200M tokens free** (Series-4 free allowance, doesn't expire when payment method is added).

**Cost reality:** a full vanilla rebuild is **~65M tokens** (measured, not estimated — dominated by ~34k unique rvmats and ~10k XML chunks from types.xml batches). At `voyage-code-3`'s $0.18/M that's ~$12, but the **200M free tier covers ~3 rebuilds**. After that, switch to `voyage-4-lite` ($0.02/M ≈ $1.30/rebuild) via `VOYAGE_MODEL` env var if cost matters. Live token + $ counter prints during the embed loop, and final totals are saved to `manifest.json`.

**Free-tier projection check:** before kicking off the embed phase, the skill estimates this build's tokens (sum of chunk text lengths ÷ chars-per-token) and projects what the cumulative monthly usage would be after this run. If the projection exceeds 80% of the 200M free tier, you get a prompt to confirm. Cumulative usage is tracked locally in `~/.claude/dayz-search-index/usage.log` (one JSONL entry per build). **Caveats:** the local counter only sees builds run via these skills — it does NOT see usage by other apps sharing your `VOYAGE_API_KEY`. The authoritative usage view is at [dash.voyageai.com](https://dash.voyageai.com). Free tier resets monthly per Voyage's billing cycle. Pass `--ignore-tier-warning` to skip the prompt (CI / scripted use). Override the budget with `VOYAGE_FREE_TIER_TOKENS=<int>` env var if you're on a non-default plan.

### One-time setup

1. Get a key at [dash.voyageai.com](https://dash.voyageai.com).
2. Add it to `.env` at the repo root (gitignored — never commits):
   ```
   VOYAGE_API_KEY=pa-xxxxxxxxxxxx
   ```
3. (Optional) override the model via env var if you want a cheaper or higher-quality variant:
   ```
   VOYAGE_MODEL=voyage-4-lite      # cheapest ($0.02/M, 16M TPM)
   VOYAGE_MODEL=voyage-code-3      # default, code-tuned
   VOYAGE_MODEL=voyage-4-large     # best general quality
   ```

The indexer auto-installs `voyageai` + `python-dotenv` on first run.

## How to run

**First time / after DayZ update:**
```cmd
python "<skill-dir>\index.py" --full
```

**Status only:**
```cmd
python "<skill-dir>\index.py" --status
```

## When to run

- After a fresh clone, before using any DayZ specialist agent that needs vanilla source recall.
- After a DayZ update (vanilla source on `P:\` may have changed).
- After re-extracting vanilla data via DayZ Tools.

## Output

```
DayZ RAG indexer

[OK]    P:\ mounted
[OK]    Vanilla data: P:\dz
[OK]    VOYAGE_API_KEY loaded (pa-GRJ...edF)
[INFO]  Index: C:\Users\you\.claude\dayz-search-index\
[INFO]  Embedding model: voyage-code-3 (1024D, via Voyage cloud)
[INFO]  Pricing: $0.18 per 1M tokens (Series-4 includes 200M free)

Walking vanilla folders: scripts, gui, dz, core, graphics, languagecore
  scripts/  c=28432c/2805f
  gui/      layout=1842c/214f
  dz/       cpp=3201c/206f
  core/     ...
  rvmat dedup: 33800 duplicates (97.6%)

Embedding 34322 chunks via Voyage (voyage-code-3, document mode)...
  embedding: 100%|██| 34322/34322 [03:42<00:00] 12,847,231 tok / ~$2.312

[OK]    Index built: 34322 chunks
[INFO]  Tokens used: 12,847,231  |  Estimated cost: $2.3125
[INFO]  Embed time: 222.4s
```

## Performance expectations

- Full index: ~25-30 min (network-bound, ~52k chunks at ~75 chunks/s).
- Index disk size: ~200-400 MB for the vector store + manifest.
- Tokens consumed: ~65M (covered by Voyage's 200M free tier for the first ~3 rebuilds).

## Safety rails

- Hard-fails if `VOYAGE_API_KEY` is missing — no silent partial runs.
- Refuses to embed >150k chunks without `--force` (cost/runtime backstop).
- Retries on 429 / transient network errors with exponential backoff.
- Live token counter + $ estimate so an unexpected blow-up surfaces instantly.

## Dependencies

`pip install -r requirements.txt` (the indexer auto-installs on first run if missing).

- `lancedb` — file-based vector store
- `tqdm` — progress bars
- `voyageai` — Voyage embedding SDK
- `python-dotenv` — load `VOYAGE_API_KEY` from `.env`

## Do not

- Don't gate this skill on `/dayz-preflight`'s warnings (Tools, Workshop) — only `P:\` mounted is mandatory.
- Don't index per clone. The index reflects the user's *machine* (their DayZ install), not the project. It lives at `~/.claude/dayz-search-index/`.
- Don't commit `.env`. It's in `.gitignore`; keep it there.
- Don't switch models without re-running `--full` — the LanceDB table is fixed-dim and switching providers/models will mismatch query and document vectors.
