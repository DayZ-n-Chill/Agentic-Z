---
name: dayz-rag-download
---

# /dayz-rag-download

Pull the prebuilt vanilla-source + wiki vector index from the repo's GitHub releases instead of building it locally. Same on-disk result as `/dayz-rag-index` + `/dayz-rag-wiki-index`, but downloads in a minute instead of 25-30.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## When to use this vs. `/dayz-rag-index`

| Scenario | Use |
|---|---|
| Fresh clone, just want DayZ agents to work | **`/dayz-rag-download`** |
| You re-extracted vanilla data after a DayZ update | `/dayz-rag-index --full` (rebuild against your local data) |
| You changed embed model in `.env` | `/dayz-rag-index --full` |
| You want the wiki index too | This skill (release bundles both) |

The downloaded index is built against vanilla DayZ at the **release-tagged version**. If your local DayZ install is on a newer patch and you need precise recall against your installed source, rebuild locally.

## Where it lands

`~/.claude/dayz-rag-index/` — same path `/dayz-rag-index` writes to. Per-user, gitignored, survives clones.

After download:
- `lancedb/` — vector store
- `manifest.json` — source corpus manifest
- `wiki-manifest.json` — wiki corpus manifest
- `config.json` — embed model the MCP server should use at query time

## How to run

**Latest release (default):**
```cmd
python .claude\skills\dayz-rag-download\download.py
```

**Specific version:**
```cmd
python .claude\skills\dayz-rag-download\download.py --tag v0.1.0
```

**Force overwrite an existing index:**
```cmd
python .claude\skills\dayz-rag-download\download.py --force
```

## Output

```
DayZ RAG index downloader

[INFO]  Repo: DayZ-n-Chill/Agentic-Z
[INFO]  Resolving latest release...
[OK]    Latest: v0.1.0
[INFO]  Asset: dayz-rag-index-v0.1.0.tar.gz (207 MB)
[INFO]  Target: C:\Users\you\.claude\dayz-rag-index\
[INFO]  Downloading... 207/207 MB
[OK]    Extracted 34322 source chunks + wiki entries
[OK]    Embed model: voyage-code-3 (1024D)
[OK]    Done. Restart Claude Code to reconnect the dayz-rag MCP server.
```

## Idempotency

- If `~/.claude/dayz-rag-index/manifest.json` already exists and was sourced from the same release tag, the skill skips download and exits clean.
- Otherwise it asks before overwriting (use `--force` to skip the prompt).
- Partial downloads land in a temp file; the existing index is only replaced after a successful extract.

## After downloading

The dayz-rag MCP server reads the index at MCP-server start. **Restart Claude Code** (or run `/mcp` reconnect) to pick up the freshly downloaded index. The `search_dayz_source` and `search_dayz_wiki` tools should then return results without you having to set `VOYAGE_API_KEY` for indexing — but **query-time embedding still needs the key**, so add it to `.env` before searching.

## Dependencies

- Python 3.8+ (stdlib only — `urllib`, `tarfile`, `json`)
- No `gh` CLI required; uses GitHub's public REST API for release metadata

## Do not

- Don't run this if you've already built a local index against your specific DayZ install — the release index is built against the maintainer's snapshot and may drift from your installed version.
- Don't commit the downloaded index. It lives at `~/.claude/dayz-rag-index/` (outside the repo) by design.
- Don't use this without `VOYAGE_API_KEY` in `.env` — query-time embedding still requires it.
