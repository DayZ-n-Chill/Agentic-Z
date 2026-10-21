---
name: dayz-search-index
---

## Overview

Builds the semantic-search index over vanilla DayZ source on P:\ (Enforce Script, configs, layouts, rvmats, XML, JSON, CSV) by embedding chunks with Voyage AI voyage-code-3 into LanceDB, which the dayz-rag MCP server queries. Use when setting up a new machine, after a DayZ update or re-extraction of vanilla data, or when search_dayz_source reports no index.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-search-index

Builds the vector index behind the `dayz-rag` MCP server's `search_dayz_source` tool. Follow `.claude/skills/_shared/dayz-conventions.md`.

If you only need the index and don't want to spend Voyage tokens, `/dayz-search-download` installs a prebuilt one.

## Before you run

1. The indexer runs `/dayz-preflight` first and stops if it fails (`P:\` not mounted). Preflight warnings (Tools, Workshop) don't block it. `--status` skips the gate.
2. Install the dependencies once: `pip install -r "<skill-dir>\requirements.txt"` (`lancedb`, `tqdm`, `voyageai`, `python-dotenv`). The indexer exits with that command if any are missing.
3. Put a Voyage key in `.env` at the repo root (gitignored): `VOYAGE_API_KEY=pa-...`. Get one at [dash.voyageai.com](https://dash.voyageai.com). The key is found the same way the `dayz-rag` MCP server finds it (both use `.claude/mcp/dayz-rag/voyage_common.py`): a variable already set in the environment wins, then the nearest `.env` at or above the working directory, then the one at the repo (or plugin) root.

## How to run

```cmd
python "<skill-dir>\index.py" --full
```

Builds (or rebuilds) the whole index. Without `--full` it refuses to overwrite an existing index.

```cmd
python "<skill-dir>\index.py" --status
```

Prints `manifest.json` and exits; exits 1 if there is no index. It creates nothing on disk.

Other flags: `--ignore-tier-warning` skips the free-tier prompt (needed in non-interactive shells), `--force` overrides the 150,000-chunk ceiling (`CHUNK_CEILING`). Both are explained in [reference/cost-and-free-tier.md](reference/cost-and-free-tier.md).

After a build, restart Claude Code so the MCP server opens the new index.

## What it indexes

The indexer walks `P:\scripts`, `P:\gui`, `P:\dz`, `P:\core`, `P:\graphics` and `P:\languagecore` and picks up `.c .cpp .hpp .h .cfg .layout .rvmat .xml .json .csv`. The live index holds about 52,000 chunks from about 38,000 files (about 66M tokens); `--status` shows the current numbers.

Indexes built before oversize class blocks were split into windows stored only the first 8,000 characters of each block. Run `--full` once to rebuild with windowing; expect the chunk count to rise.

| File type | Chunking |
|---|---|
| `.c .cpp .hpp .h .cfg .layout` | one chunk per top-level `class X { ... }` block, whole file if there are none. A block or file over 6,000 characters (`EMBED_MAX_CHARS`) is split into windows of at most that size, cut at member boundaries (a method or field starting at the class's top level) where possible, otherwise at the last whole line that fits. Each window keeps the class name as parent context and its own real line range, so no script text is dropped |
| `.rvmat` | whole file, deduplicated by SHA-256 of the content |
| `.xml` | whole file under 4 KB, otherwise batches of 50 top-level elements (line range = first to last element in the batch) |
| `.json .csv` | whole file |

The other types are not windowed: an `.rvmat` chunk stores at most 4,000 characters, and `.xml .json .csv` chunks store at most 8,000 characters, of which the first 6,000 are embedded.

Each chunk stores path, file type, parent context (class name, XML range, or rvmat hash), line range and content.

## Where the index lives

`~/.claude/dayz-search-index/`, per user and outside the repo:

- `lancedb/` holds the `chunks` table (1024-dim vectors).
- `manifest.json` records model, per-folder counts, rvmat duplicates skipped, total chunks, tokens used and estimated cost.
- `config.json` tells the MCP server which model to embed queries with.
- `usage.log` is the local token ledger used by the free-tier check.

## Output

```
DayZ RAG indexer

DayZ preflight

[OK]    P:\ is mounted
...     (rest of the /dayz-preflight report)

Preflight complete.

[OK]    Vanilla data: P:\dz
[OK]    VOYAGE_API_KEY loaded (pa-abc...wxyz)
[INFO]  Index: C:\Users\you\.claude\dayz-search-index
[INFO]  Embedding model: voyage-code-3 (1024D, via Voyage cloud)
[INFO]  Estimate rate: $0.18 per 1M tokens (Voyage pricing page is authoritative)

Walking vanilla folders: scripts, gui, dz, core, graphics, languagecore
Indexed extensions: .c, .cfg, .cpp, .csv, .h, .hpp, .json, .layout, .rvmat, .xml

  scripts/  c=<chunks>c/<files>f
  ...
  rvmat dedup:    <n> duplicates (<pct>%)

Embedding <n> chunks via Voyage (voyage-code-3, document mode)...
  embedding: 100%|...| <n>/<n> [<time>] <tokens> tok / ~$<cost>

[OK]    Index built: <n> chunks at C:\Users\you\.claude\dayz-search-index
[INFO]  Tokens used: <tokens>  |  Estimated cost: $<cost>
[INFO]  Embed time: <seconds>s
[INFO]  Restart Claude Code so the dayz-rag MCP server picks up the new index.
```

## Failure modes

- Missing dependency, missing `VOYAGE_API_KEY`, `P:\` not mounted, or no chunks produced: exits 1 before any tokens are spent.
- Transient Voyage errors (the SDK's `RateLimitError`, `Timeout`, `APIConnectionError`, `TryAgain`, `ServiceUnavailableError` and `ServerError`) are retried with exponential backoff, 5 attempts per batch. Any other embed failure, such as a bad key aborts the run before LanceDB is touched. The new rows are written to a `chunks_staging` table first and only then swapped into `chunks`, so a failed write also leaves the previous index usable.

## Do not

- Don't index per clone. The index reflects this machine's DayZ install, not the project.
- Don't commit `.env`.
- Don't change `VOYAGE_MODEL` without a `--full` rebuild; query and document vectors must come from the same model.
