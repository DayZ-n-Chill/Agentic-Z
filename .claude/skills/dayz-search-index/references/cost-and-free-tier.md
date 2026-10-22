# Voyage cost and free-tier check

Embedding goes through Voyage AI's hosted API, so a rebuild consumes tokens on your `VOYAGE_API_KEY`. Rates and free allowances change; [Voyage's pricing page](https://docs.voyageai.com/docs/pricing) and your [dashboard](https://dash.voyageai.com) are authoritative. The numbers in `index.py` (`COST_PER_MTOKEN`, `VOYAGE_FREE_TIER_BUDGET`) only drive local estimates.

## How big a rebuild is

A class-block windowed vanilla build comes to 58,658 chunks (counted on 2026-10-22 without embedding). The indexer's local estimate for it is about 89M tokens, but that estimate runs high: the last embedded build (2026-08-10, before windowing) was 52,048 chunks and Voyage reported about 66M tokens. Most of the tokens come from unique `.rvmat` files and XML. `--status` shows the real chunk and token totals after your build. A search query costs a few hundred tokens.

## What the indexer reports

- A live token count and cost estimate during the embed loop.
- `total_tokens` and `cost_estimate_usd` in `~/.claude/dayz-search-index/manifest.json` after each build (tokens are what Voyage reported; cost is tokens times the local rate table).
- One JSONL line per build in `~/.claude/dayz-search-index/usage.log`.

## The pre-build projection check

Before embedding, the indexer estimates this build's tokens (total characters divided by `CHARS_PER_TOKEN_EST`) and adds this calendar month's total from `usage.log`. If the projection reaches 80% of the budget, it shows the numbers (with an overage estimate at the selected model's rate from `COST_PER_MTOKEN`) and asks to continue. In a non-interactive shell it refuses unless you pass `--ignore-tier-warning`.

- Override the budget with `VOYAGE_FREE_TIER_TOKENS=<int>` if your plan differs from the default.
- The counter is local: it only sees builds run through `/dayz-search-index`, not other apps sharing the same key.

## The chunk ceiling

The indexer refuses to embed more than `CHUNK_CEILING` (150,000) chunks without `--force`. A normal vanilla build is well under that, so hitting it means the walk scope grew unexpectedly. The refusal message estimates the tokens and cost the same way as the projection check, from the chunk text at `CHARS_PER_TOKEN_EST` characters per token.

## Choosing a model

`VOYAGE_MODEL` overrides `voyage-code-3`. The LanceDB table is fixed at 1024 dimensions and the MCP server embeds queries with the model recorded in `config.json`, so any switch needs a `--full` rebuild and a model that emits 1024-dim vectors.
