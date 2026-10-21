---
name: dayz-search-download
description: Downloads the prebuilt DayZ RAG vector index (Voyage voyage-code-3 embeddings in LanceDB) from the repo's GitHub releases, verifies the SHA-256 digest GitHub publishes for it, and installs it to ~/.claude/dayz-search-index/ for the dayz-rag MCP server. Skips the download when the installed release tag already matches, unless --force. Use when setting up a fresh machine instead of building the index locally with /dayz-search-index.
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-search-download

Pull the prebuilt vanilla-source vector index from the repo's GitHub releases instead of building it locally with `/dayz-search-index`, skipping the local build and its Voyage API embedding cost.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## When to use this vs. `/dayz-search-index`

| Scenario | Use |
|---|---|
| Fresh clone, just want DayZ agents to work | `/dayz-search-download` |
| You re-extracted vanilla data after a DayZ update | `/dayz-search-index --full` (rebuild against your local data) |
| You changed embed model in `.env` | `/dayz-search-index --full` |

The downloaded index is built against vanilla DayZ at the release-tagged version. If your local DayZ install is on a newer patch and you need precise recall against your installed source, rebuild locally.

## Where it lands

`~/.claude/dayz-search-index/`, the same path `/dayz-search-index` writes to. Per-user, outside the repo, survives clones.

Releases have published the index under two asset names, `dayz-rag-index-v0.1.0.tar.gz` (most releases, including the latest, 1.4.0) and `dayz-search-index-<version>.tar.gz` (1.2.0 and 1.2.1). The skill accepts either, and either top-level folder name inside the archive (`dayz-rag-index/` or `dayz-search-index/`), and always installs to `~/.claude/dayz-search-index/`. A release with neither asset (1.2.2, for example) exits non-zero.

After download the folder holds what `/dayz-search-index` writes (`lancedb/`, `manifest.json`, `config.json`), plus `release-tag.txt`, the release tag that was installed (written by this skill). The release index was built before oversize class blocks were split into windows, so very long classes are only partly searchable; run `/dayz-search-index --full` if you need full coverage.

## How to run

Latest release (default):
```cmd
python "<skill-dir>\download.py"
```

Specific version:
```cmd
python "<skill-dir>\download.py" --tag 1.2.1
```

Overwrite an existing index without the prompt (this also reinstalls when the installed tag already matches):
```cmd
python "<skill-dir>\download.py" --force
```

Install an asset that has no published SHA-256 digest (every current release asset has one, so this is only for an asset uploaded without it):
```cmd
python "<skill-dir>\download.py" --allow-unverified
```

## Output

Each line is a `[LEVEL]` tag, a tab, then the message:

```
DayZ RAG index downloader

[INFO]	Repo: DayZ-n-Chill/Agentic-Z
[INFO]	Resolving latest release...
[OK]	Release: 1.4.0
[INFO]	Asset: dayz-rag-index-v0.1.0.tar.gz (206 MB)
[INFO]	Target: C:\Users\you\.claude\dayz-search-index
[INFO]	Downloading... 206.3/206.3 MB (100%)
[OK]	Downloaded 206 MB
[OK]	SHA-256 verified.
[INFO]	Extracting...
[OK]	Indexed source chunks: <count>
[OK]	Embed model: voyage-code-3
[OK]	Done. Restart Claude Code to reconnect the dayz-rag MCP server.
```

## Idempotency

- After each install the skill writes `release-tag.txt` into the index folder. If that file names the same release tag, the skill skips the download and exits 0, unless `--force` is passed, which downloads and reinstalls the same tag (useful to repair a damaged index).
- Otherwise, if an index already exists, it asks before overwriting (after the checksum-availability check below, so an unverifiable asset is refused without a prompt). `--force` skips the prompt; a declined or non-interactive prompt exits 1.
- The download lands in a temp folder. The existing index is replaced only after the checksum passes and the archive extracts cleanly, and it is restored if the final swap fails.

## Integrity checks

- **Checksum:** GitHub publishes a SHA-256 `digest` for release assets it stores. The download must match it, or the skill exits non-zero and leaves the existing index untouched. This catches corrupted or truncated downloads only: the digest comes from the same GitHub release as the file, so it does not prove who published the asset. An asset with no digest is refused before downloading unless you pass `--allow-unverified`, which installs it with a warning.
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
