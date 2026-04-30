"""dayz-rag MCP server.

Exposes semantic search over the LanceDB index built by /dayz-rag-index.
Communicates with Claude Code over stdio.

Tools:
  - search_dayz_source(query, top_k=5, file_type=None)
  - get_dayz_file(path, line_start=None, line_end=None)
  - list_indexed_sources()

Embedding: Voyage AI cloud (default voyage-code-3, 1024D). Uses input_type="query"
for asymmetric retrieval — matches the "document" mode used at index time.

Run (manually, for debugging):
    python .claude/mcp/dayz-rag/server.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

INDEX_ROOT = Path.home() / ".claude" / "dayz-rag-index"
TABLE_NAME = "chunks"
WIKI_TABLE_NAME = "wiki_chunks"
DEFAULT_EMBED_MODEL = "voyage-code-3"
MAX_TOP_K = 25
MAX_FILE_BYTES = 200_000

VALID_FILE_TYPES = {"c", "cpp", "hpp", "h", "layout", "cfg", "rvmat", "xml", "json", "csv"}


def _load_env_and_key() -> str:
    """Find repo .env, load it, return the Voyage API key. Hard-fail if missing."""
    try:
        from dotenv import find_dotenv, load_dotenv
        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path)
    except ImportError:
        pass
    key = os.environ.get("VOYAGE_API_KEY", "").strip()
    if key.startswith("export "):
        key = key.split("=", 1)[-1].strip().strip('"').strip("'")
    if not key:
        raise RuntimeError(
            "VOYAGE_API_KEY not set. Add it to .env at the repo root: VOYAGE_API_KEY=pa-xxxxxxxx"
        )
    return key


def _load_embed_model_name() -> str:
    """Read model from index config. Falls back to env override, then default."""
    cfg = INDEX_ROOT / "config.json"
    if cfg.exists():
        try:
            return json.loads(cfg.read_text(encoding="utf-8")).get("embed_model", DEFAULT_EMBED_MODEL)
        except (json.JSONDecodeError, OSError):
            pass
    return os.environ.get("VOYAGE_MODEL", DEFAULT_EMBED_MODEL).strip() or DEFAULT_EMBED_MODEL


# Lazy globals — loaded once on first call
_voyage_client = None
_embed_model: Optional[str] = None
_table = None
_wiki_table = None


def _get_client():
    global _voyage_client, _embed_model
    if _voyage_client is None:
        import voyageai
        api_key = _load_env_and_key()
        _voyage_client = voyageai.Client(api_key=api_key)
        _embed_model = _load_embed_model_name()
    return _voyage_client


def _embed_query(text: str) -> list[float]:
    """Embed a search query via Voyage. Retries on transient errors."""
    client = _get_client()
    text = text or " "
    delay = 1.0
    last_exc: Optional[Exception] = None
    for attempt in range(4):
        try:
            resp = client.embed(
                texts=[text],
                model=_embed_model,
                input_type="query",
                truncation=True,
            )
            if not resp.embeddings:
                raise RuntimeError("Voyage returned empty embeddings")
            return resp.embeddings[0]
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            transient = any(s in msg for s in ("rate", "429", "quota", "timeout", "connection"))
            if attempt == 3 or not transient:
                raise
            time.sleep(delay)
            delay *= 2
    raise last_exc  # type: ignore[misc]


def _get_table():
    global _table
    if _table is None:
        import lancedb
        db_path = INDEX_ROOT / "lancedb"
        if not db_path.exists():
            raise RuntimeError(
                f"No index at {INDEX_ROOT}. Run: python .claude/skills/dayz-rag-index/index.py --full"
            )
        db = lancedb.connect(str(db_path))
        if TABLE_NAME not in db.table_names():
            raise RuntimeError(f"Index table '{TABLE_NAME}' missing. Re-run /dayz-rag-index --full.")
        _table = db.open_table(TABLE_NAME)
    return _table


def _get_wiki_table():
    global _wiki_table
    if _wiki_table is None:
        import lancedb
        db_path = INDEX_ROOT / "lancedb"
        if not db_path.exists():
            raise RuntimeError(
                f"No index at {INDEX_ROOT}. Run: python .claude/skills/dayz-rag-wiki-index/index.py --full"
            )
        db = lancedb.connect(str(db_path))
        if WIKI_TABLE_NAME not in db.table_names():
            raise RuntimeError(
                f"Wiki index table '{WIKI_TABLE_NAME}' missing. Run /dayz-rag-wiki-index --full."
            )
        _wiki_table = db.open_table(WIKI_TABLE_NAME)
    return _wiki_table


def _format_hit(row: dict) -> dict:
    return {
        "path": row.get("path", ""),
        "file_type": row.get("file_type", ""),
        "parent_context": row.get("parent_context", ""),
        "line_start": int(row.get("line_start", 0)),
        "line_end": int(row.get("line_end", 0)),
        "score": float(row.get("_distance", 0.0)),
        "snippet": (row.get("content", "") or "")[:1500],
    }


def search_dayz_source_impl(query: str, top_k: int = 5, file_type: Optional[str] = None) -> list[dict]:
    """Semantic search over indexed vanilla DayZ source. Returns top_k chunks."""
    if not query or not query.strip():
        return []
    top_k = max(1, min(int(top_k), MAX_TOP_K))
    if file_type is not None and file_type not in VALID_FILE_TYPES:
        raise ValueError(f"file_type must be one of {sorted(VALID_FILE_TYPES)} or None")

    table = _get_table()
    vec = _embed_query(query)

    q = table.search(vec).limit(top_k * 4 if file_type else top_k)
    results = q.to_list()
    if file_type:
        results = [r for r in results if r.get("file_type") == file_type][:top_k]
    else:
        results = results[:top_k]
    return [_format_hit(r) for r in results]


def get_dayz_file_impl(path: str, line_start: Optional[int] = None, line_end: Optional[int] = None) -> dict:
    """Fetch a file (or line range) from disk for follow-up after a search hit.

    `path` should be one returned by search_dayz_source. Limited to paths under P:\\
    to prevent arbitrary file read.
    """
    p = Path(path)
    try:
        resolved = p.resolve()
    except OSError as e:
        return {"error": f"path resolution failed: {e}"}
    drive = str(resolved)[:2].upper()
    if drive != "P:":
        return {"error": f"refusing to read outside P:\\ (got {drive})"}
    if not resolved.exists() or not resolved.is_file():
        return {"error": f"not a file: {resolved}"}
    try:
        size = resolved.stat().st_size
        if size > MAX_FILE_BYTES and line_start is None:
            return {
                "error": f"file is {size} bytes (>{MAX_FILE_BYTES}); pass line_start/line_end to fetch a slice",
                "path": str(resolved),
                "size_bytes": size,
            }
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"error": f"read failed: {e}"}

    lines = text.splitlines()
    if line_start is not None or line_end is not None:
        s = max(1, int(line_start or 1))
        e = min(len(lines), int(line_end or len(lines)))
        slice_text = "\n".join(lines[s - 1 : e])
        return {"path": str(resolved), "line_start": s, "line_end": e, "content": slice_text}
    return {"path": str(resolved), "line_start": 1, "line_end": len(lines), "content": text}


def search_dayz_wiki_impl(query: str, top_k: int = 5) -> list[dict]:
    """Semantic search over indexed Bohemia wiki pages (community.bistudio.com Category:DayZ)."""
    if not query or not query.strip():
        return []
    top_k = max(1, min(int(top_k), MAX_TOP_K))
    table = _get_wiki_table()
    vec = _embed_query(query)
    results = table.search(vec).limit(top_k).to_list()
    return [_format_hit(r) for r in results]


def list_indexed_sources_impl() -> dict:
    """Return both index manifests (source + wiki) when present."""
    out: dict = {}
    src_manifest = INDEX_ROOT / "manifest.json"
    wiki_manifest = INDEX_ROOT / "wiki-manifest.json"
    if src_manifest.exists():
        try:
            out["source"] = json.loads(src_manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            out["source"] = {"error": f"manifest unreadable: {e}"}
    if wiki_manifest.exists():
        try:
            out["wiki"] = json.loads(wiki_manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            out["wiki"] = {"error": f"wiki manifest unreadable: {e}"}
    if not out:
        return {"error": f"no index at {INDEX_ROOT}", "hint": "run /dayz-rag-index --full and/or /dayz-rag-wiki-index --full"}
    # Backwards compat: when only source is present, return source manifest at top level
    # so existing callers see the same shape.
    if "source" in out and "wiki" not in out:
        return out["source"]
    return out


# --------------- MCP wiring ---------------

def main() -> int:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print(
            "mcp SDK not installed. Run: pip install -r "
            f"{Path(__file__).parent / 'requirements.txt'}",
            file=sys.stderr,
        )
        return 1

    mcp = FastMCP("dayz-rag")

    @mcp.tool()
    def search_dayz_source(query: str, top_k: int = 5, file_type: Optional[str] = None) -> list[dict]:
        """Semantic search over vanilla DayZ source (Enforce Script, layouts, configs, materials).

        Use this INSTEAD of Grep when looking for vanilla code by meaning rather than
        exact symbol name. e.g. "how does inventory drag-and-drop work", "what controls
        food spoilage timing", "show me a vanilla rvmat for camo cloth".

        Args:
            query: natural-language question or description
            top_k: max results (1-25, default 5)
            file_type: filter to one of "c", "layout", "config.cpp", "rvmat" (default: all)

        Returns: list of {path, file_type, parent_context, line_start, line_end, score, snippet}.
        Use get_dayz_file to fetch full content of a hit.
        """
        return search_dayz_source_impl(query, top_k, file_type)

    @mcp.tool()
    def get_dayz_file(path: str, line_start: Optional[int] = None, line_end: Optional[int] = None) -> dict:
        """Fetch a vanilla DayZ source file (or line range) from P:\\ for follow-up.

        Args:
            path: a path returned by search_dayz_source (must be under P:\\)
            line_start: 1-based start line (optional)
            line_end: 1-based end line, inclusive (optional)
        """
        return get_dayz_file_impl(path, line_start, line_end)

    @mcp.tool()
    def search_dayz_wiki(query: str, top_k: int = 5) -> list[dict]:
        """Semantic search over the indexed Bohemia community wiki (Category:DayZ + sub-categories).

        Use this for questions about the official DayZ docs / tutorials / class references —
        engine API explanations, modding how-tos, scripting tutorials. Complements
        search_dayz_source (which queries vanilla source code on P:\\).

        Args:
            query: natural-language question or description
            top_k: max results (1-25, default 5)

        Returns: list of {path, file_type, parent_context, line_start, line_end, score, snippet}
        where `path` is the wiki page URL and `parent_context` is "Page Title > Section > Subsection".
        """
        return search_dayz_wiki_impl(query, top_k)

    @mcp.tool()
    def list_indexed_sources() -> dict:
        """Return both index manifests when present: source (vanilla DayZ files on P:\\) and
        wiki (community.bistudio.com pages). Includes per-source-type counts, embed model,
        indexed-at timestamp, token usage, and cost estimate.

        Useful to verify either index is fresh, or to confirm what was indexed.
        """
        return list_indexed_sources_impl()

    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
