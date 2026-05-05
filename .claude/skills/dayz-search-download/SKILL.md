---
name: dayz-search-download
description: Download a prebuilt DayZ RAG vector index from the repo's GitHub releases and extract it to `~/.claude/dayz-search-index/`, so a fresh clone can use the dayz-rag MCP server without running `/dayz-search-index` (skipping the ~25-30 min build and Voyage API token cost). Idempotent — checks the existing index's manifest and skips re-download if it matches the release. Use this in place of `/dayz-search-index` on a fresh machine.
---

# /dayz-search-download

Pull the prebuilt vanilla-source + wiki vector index from the repo's GitHub releases instead of building it locally. Same on-disk result as `/dayz-search-index` + `/dayz-search-wiki-index`, but downloads in a minute instead of 25-30.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## When to use this vs. `/dayz-search-index`

| Scenario | Use |
|---|---|
| Fresh clone, just want DayZ agents to work | **`/dayz-search-download`** |
| You re-extracted vanilla data after a DayZ update | `/dayz-search-index --full` (rebuild against your local data) |
| You changed embed model in `.env` | `/dayz-search-index --full` |
| You want the wiki index too | This skill (release bundles both) |

The downloaded index is built against vanilla DayZ at the **release-tagged version**. If your local DayZ install is on a newer patch and you need precise recall against your installed source, rebuild locally.

## Where it lands

`~/.claude/dayz-search-index/` — same path `/dayz-search-index` writes to. Per-user, gitignored, survives clones.

After download:
- `lancedb/` — vector store
- `manifest.json` — source corpus manifest
- `wiki-manifest.json` — wiki corpus manifest
- `config.json` — embed model the MCP server should use at query time

## How to run

**Latest release (default):**
```cmd
python .claude\skills\dayz-search-download\download.py
```

**Specific version:**
```cmd
python .claude\skills\dayz-search-download\download.py --tag v0.1.0
```

**Force overwrite an existing index:**
```cmd
python .claude\skills\dayz-search-download\download.py --force
```

## Output

```
DayZ RAG index downloader

[INFO]  Repo: DayZ-n-Chill/Agentic-Z
[INFO]  Resolving latest release...
[OK]    Latest: v0.1.0
[INFO]  Asset: dayz-search-index-v0.1.0.tar.gz (207 MB)
[INFO]  Target: C:\Users\you\.claude\dayz-search-index\
[INFO]  Downloading... 207/207 MB
[OK]    Extracted 34322 source chunks + wiki entries
[OK]    Embed model: voyage-code-3 (1024D)
[OK]    Done. Restart Claude Code to reconnect the dayz-rag MCP server.
```

## Idempotency

- If `~/.claude/dayz-search-index/manifest.json` already exists and was sourced from the same release tag, the skill skips download and exits clean.
- Otherwise it asks before overwriting (use `--force` to skip the prompt).
- Partial downloads land in a temp file; the existing index is only replaced after a successful extract.

## After downloading

The dayz-rag MCP server reads the index at MCP-server start. **Restart Claude Code** (or run `/mcp` reconnect) to pick up the freshly downloaded index. The `search_dayz_source` and `search_dayz_wiki` tools should then return results without you having to set `VOYAGE_API_KEY` for indexing — but **query-time embedding still needs the key**, so add it to `.env` before searching.

## Dependencies

- Python 3.8+ (stdlib only — `urllib`, `tarfile`, `json`)
- No `gh` CLI required; uses GitHub's public REST API for release metadata

## Do not

- Don't run this if you've already built a local index against your specific DayZ install — the release index is built against the maintainer's snapshot and may drift from your installed version.
- Don't commit the downloaded index. It lives at `~/.claude/dayz-search-index/` (outside the repo) by design.
- Don't use this without `VOYAGE_API_KEY` in `.env` — query-time embedding still requires it.
