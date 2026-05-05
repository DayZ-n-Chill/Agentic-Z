# dayz-rag MCP server

Semantic search over vanilla DayZ source. Backs three tools that any DayZ
specialist agent can call:

- `search_dayz_source(query, top_k=5, file_type=None)` — vector search over
  the index built by `/dayz-search-index`
- `get_dayz_file(path, line_start=None, line_end=None)` — fetch full content
  for follow-up (paths must live under `P:\`)
- `list_indexed_sources()` — manifest summary

## How it works

1. **Indexer** (`/dayz-search-index`) walks vanilla DayZ source on `P:\`, chunks per file type, embeds via Voyage AI, stores in LanceDB at `~/.claude/dayz-search-index/`.
2. **MCP server** (this) loads the LanceDB index lazily, embeds incoming search queries via Voyage, returns top-K matches.

Both halves use **Voyage AI** (`voyage-code-3` by default — code-tuned, 1024D). Asymmetric encoding: documents at index time use `input_type="document"`; queries at search time use `input_type="query"`. Voyage docs say this materially improves retrieval quality.

## One-time setup

### 1. Get a Voyage API key

Sign up at <https://dash.voyageai.com>. Series-4 models (incl. `voyage-code-3`) include **200M tokens free** — full DayZ rebuilds are ~5-20M tokens, so you'll likely never pay.

Add the key to `.env` at the repo root (gitignored, won't commit):
```
VOYAGE_API_KEY=pa-xxxxxxxxxxxx
```

### 2. Install Python deps for the MCP server

```cmd
pip install -r .claude\mcp\dayz-rag\requirements.txt
```

(`mcp` SDK + `lancedb` + `voyageai` + `python-dotenv`. The indexer has its own — same set plus `tqdm`.)

### 3. Build the index

```cmd
python .claude\skills\dayz-search-index\index.py --full
```

Walks `P:\`, chunks ~30k entries, embeds via Voyage (network-bound), writes to LanceDB. ~3-10 min total. Live token + $ counter prints during the embed loop.

### 4. MCP wiring (already in place)

`.mcp.json` at the repo root declares the server with a relative path:
```json
{
  "mcpServers": {
    "dayz-rag": {
      "command": "python",
      "args": [".claude/mcp/dayz-rag/server.py"]
    }
  }
}
```
And `.claude/settings.local.json` opts it in via `"enabledMcpjsonServers": ["dayz-rag"]`.

### 5. Restart Claude Code

On next start, Claude Code reads `.mcp.json`, sees `dayz-rag` is opted in, and launches the server. Verify with `/mcp` slash command.

## Verify it loaded

In Claude Code, run `/mcp`. `dayz-rag` should be listed and connected. If it failed to start, run the server manually to see the error:

```cmd
python .claude\mcp\dayz-rag\server.py
```

(It expects MCP stdio traffic, so it'll hang silently when run directly with no input — that's fine. An ImportError, "no index", or missing-API-key message exits immediately.)

## When the index is stale

After a DayZ update, vanilla source on `P:\` may have changed. Rebuild:

```cmd
python .claude\skills\dayz-search-index\index.py --full
```

The MCP server picks up the new LanceDB on the next process start (restart Claude Code).

## Index location

`~/.claude/dayz-search-index/` (= `C:\Users\<you>\.claude\dayz-search-index\`).
Per-user, gitignored, survives across clones.

## Environment variables

| Variable | Default | What it does |
|---|---|---|
| `VOYAGE_API_KEY` | *(required)* | Voyage AI key. Read from `.env` at repo root. Indexer hard-fails without it. |
| `VOYAGE_MODEL` | `voyage-code-3` | Override the embed model. Options: `voyage-code-3` (default), `voyage-4-large`, `voyage-4`, `voyage-4-lite`. **Switching requires `--full` re-index.** |

## Cost

| Model | $/1M tokens | Free tier | Notes |
|---|---|---|---|
| `voyage-code-3` (default) | $0.18 | 200M | Code-tuned, best for DayZ corpus |
| `voyage-4-large` | $0.12 | 200M | Best general quality |
| `voyage-4` | $0.06 | 200M | Balanced |
| `voyage-4-lite` | $0.02 | 200M | Cheapest, 16M TPM |

Full DayZ rebuild ≈ **65M tokens** (measured — dominated by ~34k unique rvmats and ~10k XML chunks). Per-query at search time ≈ a few hundred tokens. The 200M free tier covers **~3 full rebuilds** plus thousands of queries on `voyage-code-3`. For more aggressive re-indexing, set `VOYAGE_MODEL=voyage-4-lite` ($0.02/M ≈ $1.30/rebuild).

`manifest.json` records `total_tokens` and `cost_estimate_usd` after each rebuild — verifiable, not estimated retroactively.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `No index at ~/.claude/dayz-search-index` | Index not built | Run `python .claude\skills\dayz-search-index\index.py --full` |
| `VOYAGE_API_KEY not set` | Key missing from `.env` | Add `VOYAGE_API_KEY=pa-...` to `.env` at repo root |
| `mcp SDK not installed` | Missing pip deps | `pip install -r .claude\mcp\dayz-rag\requirements.txt` |
| Server starts but search returns nothing | Wrong embed model loaded | Check `~/.claude/dayz-search-index/config.json` matches the model used at index time |
| Path outside `P:\` refused | `get_dayz_file` is sandboxed | Only paths returned by `search_dayz_source` are valid |
| 429 rate-limit errors | Burst beyond Voyage tier | Indexer auto-retries with backoff; query-side does too. If persistent, raise your Voyage tier or switch to `voyage-4-lite` (16M TPM). |
