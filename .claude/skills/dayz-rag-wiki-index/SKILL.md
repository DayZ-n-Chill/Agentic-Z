---
name: dayz-rag-wiki-index
description: Index the Bohemia community wiki (community.bistudio.com Category:DayZ + sub-categories) into the same vector DB as /dayz-rag-index, so DayZ agents can semantic-search official docs alongside vanilla source. One-time setup per cookie cycle; rerun with --full when content drifts.
---

# /dayz-rag-wiki-index

Build a semantic-search index over the **Bohemia DayZ wiki** so agents have access to the official docs/tutorials/class references that aren't present in vanilla source. Stored in the same LanceDB as the source index, queried via a sibling MCP tool.

Companion to `/dayz-rag-index` (which indexes vanilla source on `P:\`). Two indexes, one DB, one MCP server, two search tools.

## Why a separate skill

The Bohemia wiki sits behind Cloudflare's bot challenge. The crawl path needs:
- A `cf_clearance` cookie + matching User-Agent harvested from a real browser session
- MediaWiki API calls (not HTML scraping) for clean content extraction
- Politeness rate-limiting (1 req/sec)

These don't share much with the source-file walker, so it's a separate skill. Embedding/storage *do* share — this skill imports `_embed_all` and the cost table from `/dayz-rag-index/index.py`.

## Where the index lives

Same root as the source index: `~/.claude/dayz-rag-index/`

- `lancedb/wiki_chunks` — wiki vector table (sibling to `lancedb/chunks`)
- `wiki-manifest.json` — pages crawled, sections chunked, tokens, cost
- Reuses `config.json` from the source index (same embed model)

The source rebuild (`/dayz-rag-index --full`) drops the `chunks` table only, leaving `wiki_chunks` intact. The wiki rebuild (this skill, `--full`) drops `wiki_chunks` only.

## One-time setup

### 1. Voyage API key

Same `.env` at the repo root as `/dayz-rag-index`:
```
VOYAGE_API_KEY=pa-xxxxxxxx
```

### 2. Cloudflare cookie

Run:
```cmd
python .claude\skills\dayz-rag-wiki-index\index.py --setup-cookie
```

This walks you through:
1. Open `https://community.bistudio.com/wiki/Category:DayZ` in Firefox or Chrome.
2. Wait for the Cloudflare "Just a moment..." page to clear (a few seconds).
3. Devtools (F12) → Storage/Application → Cookies → `community.bistudio.com` → copy `cf_clearance` value.
4. Network tab → any request to community.bistudio.com → Headers → copy the `User-Agent` exactly.
5. Paste both into the prompt.

The cookie + UA are saved to `.claude/local-memory/dayz-wiki-cookie.json` (gitignored). They typically last 24-48 hours. When stale, the indexer hard-fails with a clear "re-run --setup-cookie" message.

### 3. Verify cookie works

```cmd
python .claude\skills\dayz-rag-wiki-index\index.py --probe
```

Hits the API once with the cached cookie and prints the wiki sitename. If you get a Cloudflare challenge instead, the cookie/UA pair didn't match — re-run setup.

## How to run

**Build / rebuild the wiki index:**
```cmd
python .claude\skills\dayz-rag-wiki-index\index.py --full
```

**Test crawl (limit pages):**
```cmd
python .claude\skills\dayz-rag-wiki-index\index.py --full --limit 25
```

**Status:**
```cmd
python .claude\skills\dayz-rag-wiki-index\index.py --status
```

| Argument | Notes |
|---|---|
| `--full` | Crawl + embed; replaces existing `wiki_chunks` table. |
| `--status` | Print the wiki manifest (counts, tokens, cost). |
| `--setup-cookie` | Interactive cookie capture. |
| `--probe` | One-shot API check using the cached cookie. |
| `--max-depth N` | Category recursion depth, default 6. The wiki's DayZ tree is shallow; bumping rarely helps. |
| `--limit N` | Only crawl the first N pages (alphabetic). For testing. 0 = unlimited. |

## Crawl scope

- Root: `Category:DayZ` on `community.bistudio.com`
- BFS through subcategories up to `--max-depth`
- Only main-namespace pages (ns=0) are indexed. Talk pages, user pages, and category description pages are skipped.
- Pages reached via multiple categories are deduplicated by title.

## Chunking

Per wikitext section (split on `==` headings). Each chunk gets `parent_context` like `"Page Title > Section > Subsection"` so search hits are self-locating. Sections under `MIN_CHUNK_CHARS` are dropped (boilerplate, stub See-Also lists). Sections over `MAX_CHUNK_CHARS` are split on paragraph boundaries.

## Cost expectations

- Wiki size: ~500-1500 pages depending on what's filed under Category:DayZ.
- Chunks: ~3-10k typical (each page → 3-15 sections).
- Tokens: ~5-15M for a full crawl.
- Cost via `voyage-code-3`: ~$1-3 per rebuild. Comfortably inside the 200M Voyage free tier.

## After indexing

Restart Claude Code so the dayz-rag MCP server picks up the new `wiki_chunks` table. The new search tool is `mcp__dayz-rag__search_dayz_wiki(query, top_k)` (added to the MCP server alongside the existing source-search tool).

## Refuses to run if

- `VOYAGE_API_KEY` is missing.
- Cookie cache is missing (run `--setup-cookie`).
- The API returns a Cloudflare challenge body instead of JSON (cookie stale).

## Do not

- Don't scrape rendered HTML pages — Cloudflare challenges those harder than the API. Always go through `/wikidata/api.php`.
- Don't crank `--max-depth` past ~8. Wiki categories form cycles in places; the BFS dedupe handles cycles, but very deep walks pull in tangentially-related content.
- Don't commit `.claude/local-memory/dayz-wiki-cookie.json` — it's in `.gitignore` for a reason. Cookies are user-specific and short-lived.
- Don't share your `cf_clearance` cookie. It's bound to your IP + UA; rotating it through someone else's session can invalidate it for everyone.
- Don't run this concurrently with `/dayz-rag-index --full` — both write to the same LanceDB. Sequence them.
