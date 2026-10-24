"""dayz-rag MCP server.

Exposes semantic search over the LanceDB index of vanilla DayZ source built
by /dayz-search-index. Communicates with Claude Code over stdio.

Tools (all read-only):
  - search_dayz_source(query, top_k=5, file_type=None, max_distance=None)
  - get_dayz_file(path, line_start=None, line_end=None)
  - list_indexed_sources()

Errors: bad arguments raise ValueError, a missing index or file raises
RuntimeError / FileNotFoundError. FastMCP turns any raised exception into a
tool result with isError=True, so clients always see failures the same way.

Repeated searches are answered from an in-memory cache keyed on the query,
its filters and the index build time. A rebuilt index (a new manifest.json)
empties the cache and reopens the table on the next search.

The tools are async and run their blocking work (the Voyage call with its
retries, the LanceDB search, file reads) in a worker thread, so a slow or
hung Voyage call never stalls the other tools or the MCP session.

Embedding: Voyage AI cloud (default voyage-code-3, 1024D). Uses input_type="query"
for asymmetric retrieval — matches the "document" mode used at index time.

Run (manually, for debugging):
    python .claude/mcp/dayz-rag/server.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voyage_common  # noqa: E402  .env/API-key loading and the retry rule, shared with the indexer

INDEX_ROOT = Path.home() / ".claude" / "dayz-search-index"
TABLE_NAME = "chunks"
DEFAULT_EMBED_MODEL = "voyage-code-3"
MAX_TOP_K = 25
MAX_FILE_BYTES = 200_000
ALLOWED_DRIVE = "P:"  # get_dayz_file reads only this drive (tests point it at a temp drive)
SNIPPET_MAX_CHARS = 1500  # each search hit's snippet is cut to this many characters
CACHE_MAX = 256  # repeated search answers kept in memory, oldest dropped first

# Optional distance ceiling for search results. LanceDB returns L2² distance
# (lower = closer match). Useful thresholds depend on the embed model and the
# corpus, so calibrate by running representative queries with no filter, then
# set a threshold just above the worst on-topic hit you saw. Default OFF (None)
# so callers see everything ranked; opt in via the DAYZ_RAG_MAX_DISTANCE env
# var or the per-call max_distance argument.
def _load_default_max_distance() -> Optional[float]:
    raw = os.environ.get("DAYZ_RAG_MAX_DISTANCE", "").strip()
    if not raw:
        return None
    try:
        v = float(raw)
        return v if v > 0 else None
    except ValueError:
        return None

DEFAULT_MAX_DISTANCE = _load_default_max_distance()

# Must match EXT_TYPE_MAP in .claude/skills/dayz-search-index/index.py (test_server.py checks).
VALID_FILE_TYPES = {"c", "cpp", "hpp", "h", "layout", "cfg", "rvmat", "xml", "json", "csv"}


def _load_embed_model_name() -> str:
    """Return the model the index was built with.

    manifest.json's embed_model comes first: it is the file whose change tells
    the server the index was rebuilt, so the model and the rebuild signal
    always arrive together. config.json is next (for an index whose manifest
    lacks the field), then the VOYAGE_MODEL env var, then the default.
    """
    for name in ("manifest.json", "config.json"):
        try:
            data = json.loads((INDEX_ROOT / name).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            continue
        model = data.get("embed_model") if isinstance(data, dict) else None
        if isinstance(model, str) and model.strip():
            return model.strip()
    return os.environ.get("VOYAGE_MODEL", DEFAULT_EMBED_MODEL).strip() or DEFAULT_EMBED_MODEL


# Lazy globals — loaded once on first call
_voyage_client = None
_embed_model: Optional[str] = None
_table = None
_index_built_at: Optional[float] = None  # epoch seconds; set on first manifest load
_file_hashes: Optional[dict] = None  # path -> sha256 the indexer recorded; set on first load
# Raw rows per (query, top_k, file_type, build time), most recently used last.
# Rows are cached before the distance filter and formatting, so a hit's
# is_stale flag is still checked against the file on every answer.
_search_cache: "OrderedDict[tuple, list[dict]]" = OrderedDict()
_manifest_stamp: Optional[int] = None  # manifest.json mtime the cache and open table belong to
# Searches run in worker threads (see build_app), so the cache and the index
# sync are guarded. The lock is never held across the Voyage call.
_state_lock = threading.Lock()


def _get_index_built_at() -> Optional[float]:
    """Return the source-index build time as epoch seconds, or None if unavailable."""
    global _index_built_at
    if _index_built_at is not None:
        return _index_built_at
    manifest = INDEX_ROOT / "manifest.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        ts = data.get("indexed_at")
        _index_built_at = float(ts) if ts is not None else None
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        _index_built_at = None
    return _index_built_at


def _manifest_mtime() -> Optional[int]:
    try:
        return (INDEX_ROOT / "manifest.json").stat().st_mtime_ns
    except OSError:
        return None


def _sync_with_index() -> None:
    """Forget cached answers, the open table, the build time and the embed model once the index is rebuilt.

    A changed manifest.json mtime means a new index. Checking it costs one
    stat per search. A --full rebuild may use a different VOYAGE_MODEL, so the
    query model is read again, from manifest.json itself (see
    _load_embed_model_name), so it can never lag behind the rebuild signal.
    """
    global _manifest_stamp, _table, _index_built_at, _file_hashes, _embed_model
    stamp = _manifest_mtime()
    if stamp != _manifest_stamp:
        _search_cache.clear()
        _table = None
        _index_built_at = None
        _file_hashes = None
        _embed_model = None
        _manifest_stamp = stamp


def _get_file_hashes() -> dict:
    """Return the {path: sha256} map the indexer wrote, or {} for an index built without one."""
    global _file_hashes
    if _file_hashes is None:
        try:
            data = json.loads((INDEX_ROOT / "file_hashes.json").read_text(encoding="utf-8"))
            _file_hashes = data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError, ValueError):
            _file_hashes = {}
    return _file_hashes


def _get_client():
    global _voyage_client
    if _voyage_client is None:
        import voyageai
        api_key = voyage_common.load_api_key()
        # timeout is mandatory: without it a network hang never raises, so the
        # retry loop in _embed_query never fires and searches hang forever (#51)
        _voyage_client = voyageai.Client(api_key=api_key, timeout=30)
    return _voyage_client


QUERY_ATTEMPTS = 4


def _embed_query(text: str) -> list[float]:
    """Embed a search query via Voyage, retrying transient Voyage errors with backoff."""
    global _embed_model
    client = _get_client()
    if _embed_model is None:  # first query, or the index was rebuilt (see _sync_with_index)
        _embed_model = _load_embed_model_name()
    text = text or " "
    delay = 1.0
    for attempt in range(QUERY_ATTEMPTS):
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
            if attempt == QUERY_ATTEMPTS - 1 or not voyage_common.is_transient(exc):
                raise
            time.sleep(delay)
            delay *= 2


def _get_table():
    global _table
    if _table is None:
        db_path = INDEX_ROOT / "lancedb"
        if not db_path.exists():
            raise RuntimeError(
                f"No index at {INDEX_ROOT}. Download the prebuilt one with /dayz-search-download, "
                "or build it with: python .claude/skills/dayz-search-index/index.py --full"
            )
        import lancedb

        db = lancedb.connect(str(db_path))
        if TABLE_NAME not in db.table_names():
            raise RuntimeError(f"Index table '{TABLE_NAME}' missing. Re-run /dayz-search-index --full.")
        _table = db.open_table(TABLE_NAME)
    return _table


def _check_stale(path_str: str) -> tuple[bool, Optional[str]]:
    """For local file paths under P:\\, check the file against the index.

    A file newer than the index build counts as modified only when its content
    hash also differs from the one the indexer recorded. Re-extracting P:\\ or
    downloading the index gives every file a newer mtime, so mtime alone would
    flag every hit. An index built without file_hashes.json falls back to
    mtime alone.

    Returns (is_stale, reason). For paths not on P:\\, returns (False, None):
    there's no local file to check against.
    """
    if not path_str or not path_str.startswith(("P:\\", "P:/")):
        return False, None
    built = _get_index_built_at()
    if built is None:
        return False, None
    try:
        st = Path(path_str).stat()
    except OSError:
        return True, "missing"
    if st.st_mtime <= built:
        return False, None
    recorded = _get_file_hashes().get(path_str)
    if recorded:
        try:
            if hashlib.sha256(Path(path_str).read_bytes()).hexdigest() == recorded:
                return False, None
        except OSError:
            return True, "missing"
    return True, "modified"


def _format_hit(row: dict) -> dict:
    path_str = row.get("path", "")
    is_stale, stale_reason = _check_stale(path_str)
    out = {
        "path": path_str,
        "file_type": row.get("file_type", ""),
        "parent_context": row.get("parent_context", ""),
        "line_start": int(row.get("line_start", 0)),
        "line_end": int(row.get("line_end", 0)),
        "distance": float(row.get("_distance", 0.0)),
        "snippet": (row.get("content", "") or "")[:SNIPPET_MAX_CHARS],
        "is_stale": is_stale,
    }
    if stale_reason:
        out["stale_reason"] = stale_reason
    return out


def search_dayz_source_impl(
    query: str,
    top_k: int = 5,
    file_type: Optional[str] = None,
    max_distance: Optional[float] = None,
) -> list[dict]:
    """Semantic search over indexed vanilla DayZ source. Returns top_k chunks."""
    if file_type is not None and file_type not in VALID_FILE_TYPES:
        raise ValueError(f"file_type must be one of {sorted(VALID_FILE_TYPES)} or None")
    # Distances are L2² (never negative) and a perfect match is rare, so a
    # cutoff of 0 or below would silently return nothing: reject it instead.
    if max_distance is not None and not float(max_distance) > 0:
        raise ValueError(f"max_distance must be greater than 0 (got {max_distance})")
    if not query or not query.strip():
        return []
    top_k = max(1, min(int(top_k), MAX_TOP_K))

    threshold = max_distance if max_distance is not None else DEFAULT_MAX_DISTANCE
    query = " ".join(query.split())

    with _state_lock:
        _sync_with_index()
        key = (query, top_k, file_type, _get_index_built_at())
        rows = _search_cache.get(key)
        if rows is not None:
            _search_cache.move_to_end(key)
    if rows is not None:
        return _finish(rows, threshold)

    table = _get_table()
    vec = _embed_query(query)

    q = table.search(vec)
    if file_type:
        # file_type is checked against VALID_FILE_TYPES above, so quoting it is safe.
        q = q.where(f"file_type = '{file_type}'", prefilter=True)
    rows = q.limit(top_k).to_list()
    with _state_lock:
        _search_cache[key] = rows
        if len(_search_cache) > CACHE_MAX:
            _search_cache.popitem(last=False)
    return _finish(rows, threshold)


def _finish(results: list[dict], threshold: Optional[float]) -> list[dict]:
    """Drop hits farther than threshold and format the rest.

    Results arrive nearest first, so anything past the top_k fetched is
    farther still: no over-fetch is needed for the threshold.
    """
    if threshold is not None:
        results = [r for r in results if float(r.get("_distance", 0.0)) <= threshold]
    return [_format_hit(r) for r in results]


def _slice_lines(path: str, text: str, line_start: Optional[int], line_end: Optional[int]) -> dict:
    """Return the whole text, or the inclusive 1-based line range, as a result dict.

    line_end past the end of the file is clamped; a start past the end or an
    inverted range is a bad argument. Lines are split on "\n" only, the same
    way the indexer (dayz-search-index/index.py _split_lines) numbers them:
    str.splitlines also breaks at \f, \v, \x1c-\x1e, \x85 and \u2028, which
    would put search hit line numbers out of step with this tool.
    """
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    if line_start is None and line_end is None:
        return {"path": path, "line_start": 1, "line_end": len(lines), "content": text}
    s = 1 if line_start is None else int(line_start)
    e = len(lines) if line_end is None else int(line_end)
    if s < 1:
        raise ValueError(f"line_start must be >= 1 (got {s})")
    if e < s:
        raise ValueError(f"line_end ({e}) is before line_start ({s})")
    if s > len(lines):
        raise ValueError(f"line_start {s} is past the end of the file ({len(lines)} lines)")
    e = min(e, len(lines))
    return {"path": path, "line_start": s, "line_end": e, "content": "\n".join(lines[s - 1 : e])}


def get_dayz_file_impl(path: str, line_start: Optional[int] = None, line_end: Optional[int] = None) -> dict:
    """Fetch a file (or line range) from disk for follow-up after a search hit.

    `path` should be one returned by search_dayz_source. Only paths on the P:
    drive (ALLOWED_DRIVE) are accepted, to stop arbitrary file reads.

    The check is lexical: os.path.normpath collapses `..` and `.` without
    touching the filesystem, and the drive must still be P: afterwards, so
    `P:\\..\\Windows` normalises to `P:\\Windows` and never leaves the drive.
    Path.resolve() is deliberately not used because P:\\ is usually a `subst`
    drive and resolve() would map it back to the host folder. The flip side is
    that junctions and symlinks under P:\\ (for example P:\\Mods or the
    P:\\<ModName> junctions to workspace/) are followed when the file is opened,
    so a path under P:\\ can read a file that physically lives elsewhere.
    """
    p = Path(path)
    if not p.is_absolute():
        raise ValueError(f"path must be absolute (got {path!r})")
    if p.drive.upper() != ALLOWED_DRIVE.upper():
        raise ValueError(f"refusing to read outside P:\\ (got {p.drive or '<no drive>'})")
    normalized = Path(os.path.normpath(str(p)))
    if normalized.drive.upper() != ALLOWED_DRIVE.upper():
        raise ValueError(f"refusing to read outside P:\\ (normalized to {normalized})")
    if not normalized.is_file():
        raise FileNotFoundError(f"not a file: {normalized}")
    size = normalized.stat().st_size
    if size > MAX_FILE_BYTES and line_start is None and line_end is None:
        raise ValueError(
            f"{normalized} is {size} bytes (>{MAX_FILE_BYTES}); pass line_start/line_end to fetch a slice"
        )
    text = normalized.read_text(encoding="utf-8", errors="replace")
    out = _slice_lines(str(normalized), text, line_start, line_end)
    # A range can be open-ended (only line_start) or simply wide, so the cap
    # applies to what is returned, not only to whole-file reads.
    returned = len(out["content"].encode("utf-8"))
    if returned > MAX_FILE_BYTES:
        raise ValueError(
            f"lines {out['line_start']}-{out['line_end']} of {normalized} are {returned} bytes "
            f"(>{MAX_FILE_BYTES}); pass a narrower line_start/line_end"
        )
    return out


def _read_manifest(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        raise RuntimeError(f"{path} is unreadable ({e}); rebuild that index with --full") from e


def list_indexed_sources_impl() -> dict:
    """Return {"source": manifest|None}.

    None means the index has not been built; it is a status answer, not an error.
    """
    return {"source": _read_manifest(INDEX_ROOT / "manifest.json")}


# --------------- MCP wiring ---------------

def build_app():
    """Build the FastMCP app with its three read-only tools. Raises ImportError
    when the mcp SDK is missing."""
    import anyio
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations

    mcp = FastMCP("dayz-rag")
    # The MCP spec defaults openWorldHint to true, so the local-only tools
    # (they read only P:\ and the local index) must set it to False explicitly.
    read_only = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
    # Every uncached search calls the Voyage API, so it reaches outside this machine.
    read_only_remote = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

    # Each tool is async and runs its blocking body in a worker thread. FastMCP
    # calls a sync tool directly on the event loop, so a search stuck in
    # Voyage retries (4 attempts, 30 s timeout each) would freeze every other
    # tool and the session until it gave up.
    @mcp.tool(annotations=read_only_remote)
    async def search_dayz_source(
        query: str,
        top_k: int = 5,
        file_type: Optional[str] = None,
        max_distance: Optional[float] = None,
    ) -> list[dict]:
        """Semantic search over vanilla DayZ source (Enforce Script, layouts, configs, materials).

        Use this for questions by meaning rather than exact symbol name (Grep is
        better for a known symbol), or after 2-3 greps found nothing. e.g. "how does
        inventory drag-and-drop work", "what controls food spoilage timing", "show me
        a vanilla rvmat for camo cloth".

        Args:
            query: natural-language question or description
            top_k: max results (1-25, default 5)
            file_type: filter to one of "c", "cpp", "hpp", "h", "layout", "cfg", "rvmat",
                "xml", "json", "csv" (default: all). Use "cpp" for config.cpp blocks.
            max_distance: drop hits whose `distance` (LanceDB L2² distance) is
                above this threshold. Lower = closer match. Thresholds are model
                and corpus dependent; calibrate by running unfiltered queries
                first. Must be greater than 0. Default None = no filter (or env
                var DAYZ_RAG_MAX_DISTANCE if set).

        Returns: list of {path, file_type, parent_context, line_start, line_end,
        distance, snippet, is_stale}, plus stale_reason ("modified" or
        "missing") only on hits where is_stale is true. `snippet` is the chunk's
        text cut to its first 1500 characters, while line_start/line_end span
        the whole chunk: fetch those lines with get_dayz_file to see all of it.
        `is_stale=True` means the file
        changed since the index was built (newer mtime and a different content
        hash) or is missing; the snippet may not match what's currently on disk.
        An index built without content hashes compares mtime only, so after
        re-extracting P:\\ every hit reads stale until the index is rebuilt.
        Verify with get_dayz_file or Read before grounding claims on a hit
        (see cite-then-verify rule in
        .claude/skills/_shared/dayz-conventions.md). A repeated search is
        answered from a cache until the index is rebuilt.
        """
        return await anyio.to_thread.run_sync(search_dayz_source_impl, query, top_k, file_type, max_distance)

    @mcp.tool(annotations=read_only)
    async def get_dayz_file(path: str, line_start: Optional[int] = None, line_end: Optional[int] = None) -> dict:
        """Fetch a vanilla DayZ source file (or line range) from P:\\ for follow-up.

        Files over 200 KB need a line range, and a range whose lines add up
        to more than 200 KB is refused: ask for a narrower one.

        Args:
            path: a path returned by search_dayz_source (must be under P:\\)
            line_start: 1-based start line (optional)
            line_end: 1-based end line, inclusive (optional; clamped to the file length)

        Returns: {path, line_start, line_end, content}.
        """
        return await anyio.to_thread.run_sync(get_dayz_file_impl, path, line_start, line_end)

    @mcp.tool(annotations=read_only)
    async def list_indexed_sources() -> dict:
        """Return {"source": manifest} for the vanilla source index (P:\\). The
        value is null when the index has not been built. The manifest includes
        per-type counts, embed model, indexed-at timestamp, token usage, and cost
        estimate.

        Useful to verify the index is fresh, or to confirm what was indexed.
        """
        return await anyio.to_thread.run_sync(list_indexed_sources_impl)

    return mcp


def main() -> int:
    try:
        mcp = build_app()
    except ImportError:
        print(
            "mcp SDK not installed. Run: pip install -r "
            f"{Path(__file__).parent / 'requirements.txt'}",
            file=sys.stderr,
        )
        return 1
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
