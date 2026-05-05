"""DayZ wiki RAG indexer.

Crawls community.bistudio.com Category:DayZ recursively via the MediaWiki API,
chunks page content per section, embeds via Voyage AI, stores in LanceDB
alongside the source index.

The Bohemia wiki sits behind Cloudflare. First run requires a cf_clearance
cookie + matching User-Agent harvested from a real browser session. These
are cached at .claude/local-memory/dayz-wiki-cookie.json and reused.

Run:
    python .claude/skills/dayz-search-wiki-index/index.py --setup-cookie
    python .claude/skills/dayz-search-wiki-index/index.py --full
    python .claude/skills/dayz-search-wiki-index/index.py --status
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Iterator, Optional

# Reuse Voyage embedding logic + manifest from the source indexer
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_HERE.parent / "dayz-search-index"))
# Lazy import — only needed in main flow, avoids hard dep at module load

INDEX_ROOT = Path.home() / ".claude" / "dayz-search-index"
WIKI_TABLE = "wiki_chunks"
WIKI_MANIFEST = INDEX_ROOT / "wiki-manifest.json"
COOKIE_PATH = _REPO_ROOT / ".claude" / "local-memory" / "dayz-wiki-cookie.json"

API_BASE = "https://community.bistudio.com/wikidata/api.php"
ROOT_CATEGORY = "Category:DayZ"

DEFAULT_EMBED_MODEL = "voyage-code-3"
EMBED_DIM = 1024
EMBED_MAX_CHARS = 6000

# MediaWiki API call cadence — be a polite citizen
REQUEST_DELAY_SEC = 1.0
MAX_REQUEST_RETRIES = 4

# Chunking — sections split by `==` headings in wikitext
SECTION_RE = re.compile(r"^(=+)\s*(.*?)\s*\1\s*$", re.MULTILINE)
MIN_CHUNK_CHARS = 80           # skip near-empty sections (boilerplate, see-also)
MAX_CHUNK_CHARS = 4000         # cap section size; oversize sections get split

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "
INFO = "[INFO] "


# --------------- deps ---------------

def _ensure_deps() -> None:
    try:
        import lancedb  # noqa: F401
        import tqdm  # noqa: F401
        import voyageai  # noqa: F401
        import dotenv  # noqa: F401
        import requests  # noqa: F401
        return
    except ImportError:
        pass
    req = _HERE / "requirements.txt"
    print(f"{INFO} Installing wiki-indexer dependencies (one-time)...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        check=True,
    )
    print(f"{INFO} Restarting indexer to pick up newly installed deps...", flush=True)
    result = subprocess.run([sys.executable, *sys.argv], check=False)
    sys.exit(result.returncode)


# --------------- cookie ---------------

def _load_cookie() -> dict:
    """Resolution order, first hit wins:
    1. env vars WIKI_CF_CLEARANCE + WIKI_USER_AGENT (loaded from .env or shell)
    2. JSON cache at .claude/local-memory/dayz-wiki-cookie.json
    Either source works; the env var path is preferred when the value won't
    paste cleanly into a TTY.
    """
    # Load .env first so env var path picks up values written there.
    try:
        from dotenv import find_dotenv, load_dotenv
        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path)
    except ImportError:
        pass

    # Accept either WIKI_-prefixed or unprefixed names — first non-empty wins.
    env_cf = (
        os.environ.get("WIKI_CF_CLEARANCE")
        or os.environ.get("CF_CLEARANCE")
        or ""
    ).strip().strip('"').strip("'")
    env_ua = (
        os.environ.get("WIKI_USER_AGENT")
        or os.environ.get("USER_AGENT")
        or ""
    ).strip().strip('"').strip("'")
    if env_cf and env_ua:
        return {"cf_clearance": env_cf, "user_agent": env_ua, "extra_cookies": {}, "source": "env"}

    if COOKIE_PATH.exists():
        try:
            data = json.loads(COOKIE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"{FAIL} cookie file unreadable: {e}", file=sys.stderr)
            sys.exit(1)
        if data.get("cf_clearance") and data.get("user_agent"):
            data["source"] = "json"
            return data
        print(f"{FAIL} cookie file missing cf_clearance or user_agent", file=sys.stderr)
        sys.exit(1)

    print(
        f"{FAIL} no wiki cookie configured.\n"
        f"        Either set in .env at the repo root:\n"
        f"            WIKI_CF_CLEARANCE=<value>\n"
        f"            WIKI_USER_AGENT=<value>\n"
        f"        Or run: python {Path(__file__).relative_to(_REPO_ROOT)} --setup-cookie",
        file=sys.stderr,
    )
    sys.exit(1)


def _save_cookie(cf_clearance: str, user_agent: str, extra_cookies: dict | None = None) -> None:
    COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cf_clearance": cf_clearance.strip(),
        "user_agent": user_agent.strip(),
        "extra_cookies": extra_cookies or {},
        "saved_at": int(time.time()),
    }
    COOKIE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"{OK} Cookie cached at {COOKIE_PATH}")


def setup_cookie_interactive() -> int:
    print("DayZ wiki cookie setup\n")
    print("Step 1: open https://community.bistudio.com/wiki/Category:DayZ in a real browser")
    print("        (Firefox/Chrome). Wait for the Cloudflare 'Just a moment...' to clear.\n")
    print("Step 2: open devtools (F12) -> Storage/Application -> Cookies -> community.bistudio.com")
    print("        Copy the 'cf_clearance' value (long token).\n")
    print("Step 3: Network tab -> any request to community.bistudio.com -> Headers ->")
    print("        copy the 'User-Agent' value EXACTLY (must match the UA that solved CF).\n")
    if not sys.stdin.isatty():
        print(f"{FAIL} not running in a TTY — cannot prompt. Run interactively.", file=sys.stderr)
        return 1
    cf = input("Paste cf_clearance: ").strip()
    if not cf:
        print(f"{FAIL} cf_clearance is empty", file=sys.stderr)
        return 1
    ua = input("Paste User-Agent: ").strip()
    if not ua:
        print(f"{FAIL} User-Agent is empty", file=sys.stderr)
        return 1
    _save_cookie(cf, ua)
    print(f"\n{INFO} Test the cookie with: python {Path(__file__).relative_to(_REPO_ROOT)} --probe")
    return 0


# --------------- HTTP ---------------

def _make_session(cookie: dict):
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": cookie["user_agent"],
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    })
    s.cookies.set("cf_clearance", cookie["cf_clearance"], domain="community.bistudio.com")
    for k, v in (cookie.get("extra_cookies") or {}).items():
        s.cookies.set(k, v, domain="community.bistudio.com")
    return s


def _api_get(session, params: dict) -> dict:
    """Single API GET with rate limit, retries, and CF-block detection."""
    import requests
    params = {**params, "format": "json", "formatversion": "2"}
    delay = 2.0
    last_err: Optional[str] = None
    for attempt in range(MAX_REQUEST_RETRIES):
        time.sleep(REQUEST_DELAY_SEC)
        try:
            r = session.get(API_BASE, params=params, timeout=30)
        except requests.RequestException as e:
            last_err = str(e)
            time.sleep(delay)
            delay *= 2
            continue
        ct = r.headers.get("content-type", "")
        body = r.text
        if r.status_code == 200 and ct.startswith("application/json"):
            try:
                return r.json()
            except json.JSONDecodeError as e:
                last_err = f"json decode: {e}"
        elif "<title>Just a moment" in body or "challenge-platform" in body:
            print(
                f"\n{FAIL} Cloudflare challenge — cookie is stale or UA mismatch.\n"
                f"        Re-run: python {Path(__file__).relative_to(_REPO_ROOT)} --setup-cookie",
                file=sys.stderr,
            )
            sys.exit(2)
        else:
            last_err = f"status {r.status_code}, ct={ct}, body[:200]={body[:200]!r}"
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"API call failed after {MAX_REQUEST_RETRIES} attempts: {last_err}")


def probe(cookie: dict) -> int:
    s = _make_session(cookie)
    print(f"{INFO} probing API with cached cookie (UA={cookie['user_agent'][:40]}...)")
    data = _api_get(s, {"action": "query", "meta": "siteinfo", "siprop": "general"})
    general = (data.get("query") or {}).get("general") or {}
    print(f"{OK} sitename: {general.get('sitename')}")
    print(f"{OK} mainpage: {general.get('mainpage')}")
    print(f"{OK} generator: {general.get('generator')}")
    return 0


# --------------- crawl ---------------

def _list_category_members(session, category: str) -> Iterator[dict]:
    """Yield {pageid, ns, title} for every direct member of a category, paginated."""
    cmcontinue = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "max",
            "cmtype": "page|subcat",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        data = _api_get(session, params)
        for m in (data.get("query") or {}).get("categorymembers", []):
            yield m
        cont = data.get("continue") or {}
        cmcontinue = cont.get("cmcontinue")
        if not cmcontinue:
            return


def _walk_categories(session, root: str, max_depth: int = 6) -> tuple[list[str], list[str]]:
    """BFS walk Category:Foo, returning (page_titles, subcategory_titles_visited)."""
    seen_cats: set[str] = set()
    pages: dict[str, dict] = {}  # title -> member dict
    queue: list[tuple[str, int]] = [(root, 0)]
    while queue:
        cat, depth = queue.pop(0)
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        if depth > max_depth:
            print(f"{WARN} max_depth hit at {cat}")
            continue
        try:
            members = list(_list_category_members(session, cat))
        except RuntimeError as e:
            print(f"{WARN} failed to list {cat}: {e}")
            continue
        cat_pages = 0
        cat_subs = 0
        for m in members:
            ns = m.get("ns")
            title = m.get("title", "")
            # ns 14 = Category. Everything else returned by cmtype=page|subcat
            # is a content page. Bohemia's wiki uses custom per-game namespaces
            # (e.g. ns 5020 for DayZ:* titles), not just ns 0.
            if ns == 14:
                cat_subs += 1
                queue.append((title, depth + 1))
            else:
                pages[title] = m
                cat_pages += 1
        print(f"  {cat}: {cat_pages} pages, {cat_subs} subcats (depth {depth})")
    return sorted(pages.keys()), sorted(seen_cats)


def _fetch_page_wikitext(session, title: str) -> str | None:
    data = _api_get(session, {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "redirects": "1",
    })
    parse = data.get("parse") or {}
    wikitext = parse.get("wikitext")
    if isinstance(wikitext, dict):  # formatversion=1 returns {"*": "..."}
        wikitext = wikitext.get("*", "")
    return wikitext or None


# --------------- chunk ---------------

def _strip_wikitext_noise(text: str) -> str:
    """Light normalization — drop templates that don't add semantic value."""
    text = re.sub(r"\{\{[Nn]avbox.*?\}\}", "", text, flags=re.DOTALL)
    text = re.sub(r"\[\[Category:[^\]]+\]\]", "", text)
    return text


def _split_sections(wikitext: str, page_title: str) -> list[tuple[str, str]]:
    """Yield (section_path, section_content) tuples. The lead (before first ==
    heading) becomes a section under the page title alone."""
    text = _strip_wikitext_noise(wikitext)
    matches = list(SECTION_RE.finditer(text))
    sections: list[tuple[str, str]] = []
    if not matches:
        sections.append((page_title, text.strip()))
        return sections

    # Lead
    lead = text[: matches[0].start()].strip()
    if lead:
        sections.append((page_title, lead))

    # Track heading stack for nested context
    stack: list[tuple[int, str]] = []  # (level, title)
    for i, m in enumerate(matches):
        level = len(m.group(1))
        heading = m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        # Pop stack until we find a level less than current
        while stack and stack[-1][0] >= level:
            stack.pop()
        path_parts = [page_title] + [t for _, t in stack] + [heading]
        stack.append((level, heading))
        if not body:
            continue
        sections.append((" > ".join(path_parts), body))
    return sections


def _chunk_section(path: str, body: str) -> list[dict]:
    """Split oversize sections into MAX_CHUNK_CHARS-bounded slices."""
    body = body.strip()
    if len(body) < MIN_CHUNK_CHARS:
        return []
    if len(body) <= MAX_CHUNK_CHARS:
        return [{"parent_context": path, "content": body}]
    chunks = []
    start = 0
    n = len(body)
    while start < n:
        end = min(start + MAX_CHUNK_CHARS, n)
        # try to split on a paragraph boundary near end
        if end < n:
            last_para = body.rfind("\n\n", start, end)
            if last_para > start + MIN_CHUNK_CHARS:
                end = last_para
        chunks.append({"parent_context": path, "content": body[start:end].strip()})
        start = end
    return [c for c in chunks if len(c["content"]) >= MIN_CHUNK_CHARS]


def _build_chunks_for_page(title: str, wikitext: str) -> list[dict]:
    url = f"https://community.bistudio.com/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
    out: list[dict] = []
    for section_path, body in _split_sections(wikitext, title):
        for c in _chunk_section(section_path, body):
            out.append({
                "path": url,
                "file_type": "wiki",
                "parent_context": c["parent_context"],
                "line_start": 1,
                "line_end": c["content"].count("\n") + 1,
                "content": c["content"][:EMBED_MAX_CHARS],
            })
    return out


# --------------- embed (reuse from source indexer) ---------------

def _embed_module():
    """Import the source-indexer module so we reuse _embed_all + cost table."""
    src_dir = _HERE.parent / "dayz-search-index"
    sys.path.insert(0, str(src_dir))
    import index as src_indexer  # type: ignore
    return src_indexer


# --------------- main ---------------

def _print_status() -> int:
    if WIKI_MANIFEST.exists():
        print(WIKI_MANIFEST.read_text(encoding="utf-8"))
        return 0
    print(f"No wiki index. Run: python {Path(__file__).relative_to(_REPO_ROOT)} --full",
          file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="DayZ wiki RAG indexer")
    parser.add_argument("--full", action="store_true", help="Crawl + embed; replaces existing wiki_chunks table")
    parser.add_argument("--status", action="store_true", help="Print wiki manifest and exit")
    parser.add_argument("--setup-cookie", action="store_true", help="Interactive cookie capture")
    parser.add_argument("--probe", action="store_true", help="Hit the API once with the cached cookie to verify it's still good")
    parser.add_argument("--max-depth", type=int, default=6, help="Max category recursion depth (default 6)")
    parser.add_argument("--limit", type=int, default=0, help="Limit pages crawled (0 = no limit, for testing)")
    parser.add_argument("--ignore-tier-warning", action="store_true", help="Skip the Voyage free-tier prompt (CI / scripted use)")
    args = parser.parse_args()

    if args.status:
        return _print_status()

    if args.setup_cookie:
        return setup_cookie_interactive()

    _ensure_deps()

    cookie = _load_cookie()
    src = cookie.get("source", "json")

    if args.probe:
        print(f"{INFO} cookie source: {src} (UA={cookie['user_agent'][:50]}...)")
        return probe(cookie)

    if not args.full:
        print(f"{FAIL} pass --full to build/rebuild the wiki index, or --status to inspect.",
              file=sys.stderr)
        return 1

    print("DayZ wiki RAG indexer\n")

    src_indexer = _embed_module()
    api_key = src_indexer._load_env_and_key()
    embed_model = os.environ.get("VOYAGE_MODEL", DEFAULT_EMBED_MODEL).strip() or DEFAULT_EMBED_MODEL
    cost_per_m = src_indexer.COST_PER_MTOKEN.get(embed_model)

    print(f"{OK} VOYAGE_API_KEY loaded ({api_key[:6]}...{api_key[-4:]})")
    print(f"{OK} cookie cached at {COOKIE_PATH}")
    print(f"{INFO} Embedding model: {embed_model} (1024D, via Voyage cloud)")
    if cost_per_m is not None:
        print(f"{INFO} Pricing: ${cost_per_m:.2f} per 1M tokens")
    print()

    import requests  # noqa: F401  (just to surface import error early)
    session = _make_session(cookie)

    # 1. probe
    print(f"{INFO} probing API...")
    probe_data = _api_get(session, {"action": "query", "meta": "siteinfo", "siprop": "general"})
    sitename = ((probe_data.get("query") or {}).get("general") or {}).get("sitename")
    print(f"{OK} connected: {sitename}\n")

    # 2. crawl categories
    started = time.time()
    print(f"{INFO} walking {ROOT_CATEGORY} (max_depth={args.max_depth})...\n")
    titles, cats = _walk_categories(session, ROOT_CATEGORY, max_depth=args.max_depth)
    print(f"\n{OK} {len(titles)} pages across {len(cats)} categories")

    if args.limit and args.limit < len(titles):
        titles = titles[: args.limit]
        print(f"{INFO} limited to {len(titles)} pages for this run")

    # 3. fetch each page, chunk
    from tqdm import tqdm
    chunks: list[dict] = []
    failures: list[str] = []
    for title in tqdm(titles, desc="  fetching", unit="page"):
        try:
            wt = _fetch_page_wikitext(session, title)
        except RuntimeError as e:
            failures.append(f"{title}: {e}")
            continue
        if not wt:
            continue
        chunks.extend(_build_chunks_for_page(title, wt))

    if failures:
        print(f"{WARN} {len(failures)} page fetch failures")

    if not chunks:
        print(f"{FAIL} no chunks produced.", file=sys.stderr)
        return 1
    print(f"{OK} {len(chunks)} chunks from {len(titles)} pages\n")

    # 4. embed
    nonempty = [c for c in chunks if (c.get("content") or "").strip()]
    dropped = len(chunks) - len(nonempty)
    if dropped:
        print(f"{INFO} dropped {dropped} empty chunks before embed")
    chunks = nonempty
    texts = [(c["content"] or " ")[:EMBED_MAX_CHARS] for c in chunks]

    # Voyage free-tier projection check (shared helper from source indexer).
    chars_per_token = getattr(src_indexer, "CHARS_PER_TOKEN_EST", 1.8)
    estimated_tokens = int(sum(max(1, len(t) // chars_per_token) for t in texts))
    if not src_indexer._check_voyage_tier(estimated_tokens, args.ignore_tier_warning):
        print(f"{FAIL} Cancelled by user. No tokens consumed.", file=sys.stderr)
        return 1

    print(f"{INFO} embedding {len(chunks)} chunks via Voyage ({embed_model})...")
    t0 = time.time()
    embeddings, total_tokens = src_indexer._embed_all(texts, embed_model, api_key)
    embed_elapsed = time.time() - t0

    if len(embeddings) != len(chunks):
        print(f"{FAIL} embedding count mismatch", file=sys.stderr)
        return 1
    for c, vec in zip(chunks, embeddings):
        c["vector"] = vec

    cost_estimate_usd = round((total_tokens / 1_000_000) * (cost_per_m or 0), 4)

    # 5. store in LanceDB (separate table in same DB as source index)
    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    import lancedb
    db_path = INDEX_ROOT / "lancedb"
    db = lancedb.connect(str(db_path))
    if WIKI_TABLE in db.table_names():
        db.drop_table(WIKI_TABLE)
    db.create_table(WIKI_TABLE, data=chunks)

    # 6. write manifest
    manifest = {
        "indexed_at": int(time.time()),
        "indexed_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "community.bistudio.com",
        "root_category": ROOT_CATEGORY,
        "max_depth": args.max_depth,
        "embed_model": embed_model,
        "embed_dim": EMBED_DIM,
        "embed_provider": "voyage",
        "categories_visited": len(cats),
        "pages_crawled": len(titles),
        "chunks_indexed": len(chunks),
        "fetch_failures": len(failures),
        "total_tokens": total_tokens,
        "cost_estimate_usd": cost_estimate_usd,
        "embed_seconds": round(embed_elapsed, 1),
        "total_seconds": round(time.time() - started, 1),
    }
    WIKI_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Track this run in the local Voyage usage log (shared with source indexer).
    src_indexer._append_usage_entry(total_tokens, cost_estimate_usd, "dayz-search-wiki-index")

    print(f"\n{OK} wiki index built: {len(chunks)} chunks at {INDEX_ROOT}/lancedb/{WIKI_TABLE}")
    print(f"{INFO} tokens: {total_tokens:,}  |  cost: ${cost_estimate_usd:.4f}")
    print(f"{INFO} elapsed: crawl+embed = {time.time() - started:.1f}s")
    print(f"{INFO} restart Claude Code so the dayz-rag MCP picks up the new wiki table")
    return 0


if __name__ == "__main__":
    sys.exit(main())
