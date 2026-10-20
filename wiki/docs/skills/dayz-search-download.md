---
name: dayz-search-download
---

## Overview

Downloads the prebuilt DayZ RAG vector index (Voyage voyage-code-3 embeddings in LanceDB) from the repo's GitHub releases, verifies the SHA-256 digest GitHub publishes for it, and installs it to ~/.claude/dayz-search-index/ for the dayz-rag MCP server. Skips the download when the installed release tag already matches. Use when setting up a fresh machine instead of building the index locally with /dayz-search-index.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-search-download

Pull the prebuilt vanilla-source + wiki vector index from the repo's GitHub releases instead of building it locally. Same on-disk result as `/dayz-search-index` + `/dayz-search-wiki-index`, without the local build or its Voyage API embedding cost.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## When to use this vs. `/dayz-search-index`

| Scenario | Use |
|---|---|
| Fresh clone, just want DayZ agents to work | `/dayz-search-download` |
| You re-extracted vanilla data after a DayZ update | `/dayz-search-index --full` (rebuild against your local data) |
| You changed embed model in `.env` | `/dayz-search-index --full` |
| You want the wiki index too | This skill (release bundles both) |

The downloaded index is built against vanilla DayZ at the release-tagged version. If your local DayZ install is on a newer patch and you need precise recall against your installed source, rebuild locally.

## Where it lands

`~/.claude/dayz-search-index/`, the same path `/dayz-search-index` writes to. Per-user, outside the repo, survives clones.

After download:
- `lancedb/`: vector store
- `manifest.json`: source corpus manifest
- `wiki-manifest.json`: wiki corpus manifest
- `config.json`: embed model the MCP server should use at query time
- `release-tag.txt`: the release tag that was installed (written by this skill)

## How to run

Latest release (default):
```cmd
python "<skill-dir>\download.py"
```

Specific version:
```cmd
python "<skill-dir>\download.py" --tag v0.1.0
```

Overwrite an existing index without the prompt:
```cmd
python "<skill-dir>\download.py" --force
```

Install an asset that has no published SHA-256 digest (older releases):
```cmd
python "<skill-dir>\download.py" --allow-unverified
```

## Output

Each line is a `[LEVEL]` tag, a tab, then the message:

```
DayZ RAG index downloader

[INFO]	Repo: DayZ-n-Chill/Agentic-Z
[INFO]	Resolving latest release...
[OK]	Release: v0.1.0
[INFO]	Asset: dayz-search-index-v0.1.0.tar.gz (<size> MB)
[INFO]	Target: C:\Users\you\.claude\dayz-search-index
[INFO]	Downloading... <size>/<size> MB (100%)
[OK]	Downloaded <size> MB
[OK]	SHA-256 verified.
[INFO]	Extracting...
[OK]	Indexed source chunks: <count>
[OK]	Embed model: voyage-code-3
[OK]	Done. Restart Claude Code to reconnect the dayz-rag MCP server.
```

## Idempotency

- After each install the skill writes `release-tag.txt` into the index folder. If that file names the same release tag, the skill skips the download and exits 0.
- Otherwise, if an index already exists, it asks before overwriting (after the checksum-availability check below, so an unverifiable asset is refused without a prompt). `--force` skips the prompt; a declined or non-interactive prompt exits 1.
- The download lands in a temp folder. The existing index is replaced only after the checksum passes and the archive extracts cleanly, and it is restored if the final swap fails.

## Integrity checks

- **Checksum:** GitHub publishes a SHA-256 `digest` for release assets it stores. The download must match it, or the skill exits non-zero and leaves the existing index untouched. An asset with no digest (older releases) is refused before downloading unless you pass `--allow-unverified`, which installs it with a warning.
- **Safe extraction:** archive entries that would land outside the extract folder (absolute paths, `..` traversal, links pointing outside) are refused. On Python 3.12+ this uses the `tarfile` `data` filter.
- **Network errors** (offline, DNS, proxy, HTTP errors) exit non-zero with the URL and the reason.

## After downloading

The dayz-rag MCP server reads the index when it starts. Restart Claude Code (or reconnect with `/mcp`) to pick up the new index. Downloading needs no `VOYAGE_API_KEY`, but the server embeds each search query with Voyage, so add the key to `.env` before searching.

## Dependencies

- Python 3.8+ (stdlib only: `urllib`, `tarfile`, `hashlib`, `json`)
- No `gh` CLI required; uses GitHub's public REST API for release metadata

## Do not

- Don't run this if you've already built a local index against your specific DayZ install: the release index is built against the maintainer's snapshot and may drift from your installed version.
- Don't commit the downloaded index. It lives at `~/.claude/dayz-search-index/` (outside the repo) by design.
