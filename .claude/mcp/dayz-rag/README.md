# dayz-rag MCP server

Semantic search over vanilla DayZ source, for any DayZ specialist agent. Three read-only tools (each carries the MCP `readOnlyHint` annotation; `search_dayz_source` also carries `openWorldHint`, since an uncached search calls the Voyage API, while the two local tools set `openWorldHint` to false, because the MCP spec defaults it to true):

- `search_dayz_source(query, top_k=5, file_type=None, max_distance=None)`: vector search over the index built by `/dayz-search-index`.
- `get_dayz_file(path, line_start=None, line_end=None)`: fetch a file or line range for follow-up. Paths must be on `P:\`; files over 200 KB need a range, and any range that returns more than 200 KB is refused, so pass both `line_start` and `line_end` on big files. Lines are counted at newline (`\n`) characters only, the same way the indexer numbers search hits. The check is lexical (the path is normalised, not resolved), so a junction or symlink under `P:\`, such as `P:\Mods` or a `P:\<ModName>` junction into `workspace/`, can still lead to a file stored elsewhere.
- `list_indexed_sources()`: returns `{"source": <manifest or null>}`; null means the index hasn't been built.

Agents use these after Grep, per the search rule in `.claude/skills/_shared/dayz-conventions.md`: Grep for known symbols, `search_dayz_source` for questions by meaning, then verify a hit with `get_dayz_file` or Read before relying on it. Each search hit has `path`, `file_type`, `parent_context`, `line_start`, `line_end`, `distance` (LanceDB L2² distance, lower is closer), `snippet` and `is_stale`. `snippet` is the chunk's text cut to its first 1500 characters, while `line_start` and `line_end` cover the whole chunk, so fetch that range with `get_dayz_file` to read all of it. Hits carry `is_stale: true`, plus a `stale_reason` of `modified` or `missing` that is present only on stale hits, when the file on `P:\` changed after the index was built. A file counts as modified only when its mtime is newer than the build and its content hash differs from the one in `file_hashes.json`, so re-extracting `P:\` or downloading the index does not flag unchanged files. An index built before `file_hashes.json` existed compares mtime alone, and then every hit on a re-extracted drive reads stale until the index is rebuilt.

Installed as a plugin, the tools appear as `mcp__plugin_agentic-z_dayz-rag__<tool>`; from a clone via `.mcp.json`, as `mcp__dayz-rag__<tool>`.

## How it works

1. The indexer walks the vanilla source, chunks it, embeds each chunk with Voyage AI `voyage-code-3` (1024-dim) using `input_type="document"`, and stores the chunks in LanceDB at `~/.claude/dayz-search-index/` (table `chunks`).
2. This server opens LanceDB lazily, embeds each query with the same model using `input_type="query"`, and returns the nearest chunks. A repeated search is answered from an in-memory cache of up to 256 searches, keyed on the query, `top_k`, `file_type` and the index build time. The cache keeps the raw rows, so `max_distance` and the `is_stale` check still run on every answer. A rebuilt index empties the cache. A `file_type` filter is a LanceDB prefilter (`where`), so `top_k` hits of that type come back even when other types rank nearer. The query model comes from `embed_model` in the index's `manifest.json`, the same file whose change signals a rebuild, so the model can never lag behind a rebuild; an index whose manifest lacks the field falls back to `config.json`.
3. Every tool is async and runs its blocking work (the Voyage call and its retries, the LanceDB search, file reads) in a worker thread, so a slow or unreachable Voyage API stalls only that search, never `get_dayz_file`, `list_indexed_sources` or the MCP session.

`list_indexed_sources` reports the current chunk and token counts. Indexed types: `.c .cpp .hpp .h .cfg .layout .rvmat .xml .json .csv`, which are also the accepted `file_type` filter values.

## Errors

Every tool reports failures the same way: it raises, and the MCP client receives a result with `isError: true` and the message. Bad arguments (unknown `file_type`, a `max_distance` of 0 or below, a path outside `P:\`, an invalid line range, a large file without a range, a range that returns more than 200 KB) raise `ValueError`. A missing index raises `RuntimeError` naming `/dayz-search-download` and `/dayz-search-index`, and a missing `chunks` table raises `RuntimeError` naming `/dayz-search-index --full`. A missing file raises `FileNotFoundError` naming the path. A blank query returns an empty list.

## Setup

1. Add a Voyage key to `.env` at the repo root (gitignored): `VOYAGE_API_KEY=pa-...`. The server reads the nearest `.env` at or above its working directory, then the one at the repo (or plugin) root; a variable already set in the environment wins. The indexer uses the same lookup: both import `voyage_common.py` from this folder. Get one at <https://dash.voyageai.com>.
2. Install the server's dependencies (`mcp`, `lancedb`, `voyageai`, `python-dotenv`):
   ```cmd
   pip install -r .claude\mcp\dayz-rag\requirements.txt
   ```
3. Install the prebuilt index with `/dayz-search-download`, or build it against your own DayZ install with `/dayz-search-index`.
4. Wiring: in a clone, `.mcp.json` at the repo root declares the server, and the committed `.claude/settings.json` already sets `"enabledMcpjsonServers": ["dayz-rag"]`, so a clone needs no local opt in. The plugin registers it in `.claude-plugin/plugin.json`.
5. Restart Claude Code and check `/mcp` shows `dayz-rag` connected.

If it fails to start, run it directly to see the error:

```cmd
python .claude\mcp\dayz-rag\server.py
```

It waits silently for MCP traffic on stdin when healthy; a missing `mcp` package prints the install command and exits. A missing index or API key surfaces on the first tool call, not at startup.

## Rebuilding

After a DayZ update, rebuild with `python .claude\skills\dayz-search-index\index.py --full`. The server sees the new `manifest.json` on its next search, reopens the index and reads the embed model again from that manifest, so no restart is needed. Changing `VOYAGE_MODEL` also needs a `--full` rebuild; after it, queries use the new model. Token costs and the free-tier check are covered in `.claude/skills/dayz-search-index/references/cost-and-free-tier.md`.

## Environment variables

| Variable | Default | What it does |
|---|---|---|
| `VOYAGE_API_KEY` | required | Voyage key, read from the environment or `.env` (working directory, then repo/plugin root). |
| `VOYAGE_MODEL` | `voyage-code-3` | Query model only if neither the index's `manifest.json` nor its `config.json` names one; normally the indexer's choice wins. |
| `DAYZ_RAG_MAX_DISTANCE` | unset | Default `max_distance` cutoff (on each hit's `distance`) for `search_dayz_source`. Calibrate by running unfiltered queries first. |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `No index at ~/.claude/dayz-search-index` | Index not built | Run `/dayz-search-index` or `/dayz-search-download` |
| `VOYAGE_API_KEY not set` | Key missing from `.env` | Add `VOYAGE_API_KEY=pa-...` at the repo root |
| `mcp SDK not installed` | Missing dependencies | `pip install -r .claude\mcp\dayz-rag\requirements.txt` |
| Results look unrelated | Query model differs from index model | Check `embed_model` in `~/.claude/dayz-search-index/manifest.json`; rebuild with `--full` if you changed models |
| 429 rate-limit errors | Burst beyond your Voyage limits | Queries retry transient Voyage errors (rate limit, timeout, connection, server) up to 4 times with backoff; if it persists, check your Voyage dashboard |

## Tests

```cmd
py -m pytest -q .claude\mcp\dayz-rag
```

The tests stub LanceDB and Voyage, so they need no index or key. File-read tests point the allowed drive at a temporary folder; one test checks that `P:\..\..\Windows` stays on `P:`.
