"""Standalone CLI for the DayZ RAG index. Bypasses the MCP server / model entirely.

Usage:
    dayz-search <query>                  # source corpus, top 5
    dayz-search -k 3 <query>             # top 3
    dayz-search -t c <query>             # filter to file_type=c (Enforce Script)
    dayz-search -d 0.9 <query>           # drop hits with distance above 0.9
    dayz-search -s 800 <query>           # snippet preview length (default 400)
    dayz-search -j <query>               # raw JSON output

Without -d, the server's DAYZ_RAG_MAX_DISTANCE env var, when set, still drops
the far hits, as it does for agents; '(no hits)' then names that limit.

Reuses search_dayz_source_impl from the MCP server module so behavior matches
what agents see. An empty query, a -k below 1, a -d of 0 or below, a negative
-s, a missing index, a missing VOYAGE_API_KEY, a missing package or a Voyage
API error prints one 'error:' line and exits 2. A bad argument
exits 2 with argparse's usage line and a 'dayz-search: error:' line.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_DIR = REPO_ROOT / ".claude" / "mcp" / "dayz-rag"
sys.path.insert(0, str(MCP_DIR))

from server import (  # noqa: E402
    DEFAULT_MAX_DISTANCE, INDEX_ROOT, MAX_TOP_K, VALID_FILE_TYPES, search_dayz_source_impl,
)

NO_HASHES_NOTE = (
    "note: this index has no file_hashes.json, so a file's freshness can only be judged by its date and every "
    "P:\\ file changed after the build shows as [STALE]; a rebuild with /dayz-search-index clears it."
)


def _print_hits(hits: list[dict], snippet_chars: int, threshold: Optional[float] = None,
                from_flag: bool = False) -> None:
    if not hits:
        if threshold is None:
            print("(no hits)")
        elif from_flag:
            print(f"(no hits within distance {threshold:g}; raise it with -d or drop the -d flag)")
        else:
            print(f"(no hits within distance {threshold:g}; raise it with -d, or unset DAYZ_RAG_MAX_DISTANCE)")
        return
    if any(h.get("is_stale") for h in hits) and not (INDEX_ROOT / "file_hashes.json").is_file():
        print(NO_HASHES_NOTE)
    for i, h in enumerate(hits, 1):
        path = h.get("path", "")
        ls = h.get("line_start", 0)
        le = h.get("line_end", 0)
        distance = h.get("distance", 0.0)
        ctx = h.get("parent_context", "")
        reason = h.get("stale_reason")
        stale = (f" [STALE: {reason}]" if reason else " [STALE]") if h.get("is_stale") else ""
        print(f"\n[{i}] {path}:{ls}-{le}  distance={distance:.3f}{stale}")
        if ctx:
            print(f"    {ctx}")
        snippet = (h.get("snippet", "") or "").rstrip()
        if snippet_chars > 0 and len(snippet) > snippet_chars:
            snippet = snippet[:snippet_chars].rstrip() + " ..."
        for line in snippet.splitlines():
            print(f"    | {line}")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="dayz-search", description="Search the DayZ RAG index from the terminal.")
    p.add_argument("query", nargs="+", help="natural-language query")
    p.add_argument("-k", "--top-k", type=int, default=5, help="max hits (default 5, max 25)")
    p.add_argument("-t", "--file-type", default=None, choices=sorted(VALID_FILE_TYPES),
                   help="source filter: " + " | ".join(sorted(VALID_FILE_TYPES)))
    default_limit = f"{DEFAULT_MAX_DISTANCE:g} from DAYZ_RAG_MAX_DISTANCE" if DEFAULT_MAX_DISTANCE else "no limit"
    p.add_argument("-d", "--max-distance", type=float, default=None,
                   help=f"drop hits with distance above this (default: DAYZ_RAG_MAX_DISTANCE if set, else no "
                        f"limit; now {default_limit})")
    p.add_argument("-s", "--snippet-chars", type=int, default=400, help="snippet preview length (0 = the whole snippet, which the server caps at 1500 characters)")
    p.add_argument("-j", "--json", action="store_true", help="print raw JSON instead of formatted output")
    args = p.parse_args(argv)

    query = " ".join(args.query).strip()
    if not query:
        print("error: empty query", file=sys.stderr)
        return 2
    if args.top_k < 1:
        print(f"error: -k must be 1 or more, got {args.top_k}", file=sys.stderr)
        return 2
    if args.max_distance is not None and args.max_distance <= 0:
        print(f"error: -d must be above 0, got {args.max_distance:g}", file=sys.stderr)
        return 2
    if args.snippet_chars < 0:
        print(f"error: -s must be 0 or more, got {args.snippet_chars}", file=sys.stderr)
        return 2
    if args.top_k > MAX_TOP_K:
        print(f"note: -k {args.top_k} is above the maximum; showing at most {MAX_TOP_K} hits", file=sys.stderr)

    try:
        hits = search_dayz_source_impl(
            query, top_k=args.top_k, file_type=args.file_type, max_distance=args.max_distance,
        )
    except ImportError as e:  # lancedb or voyageai not installed
        print(f"error: {e}; run pip install -r .claude\\mcp\\dayz-rag\\requirements.txt", file=sys.stderr)
        return 2
    except (RuntimeError, ValueError, OSError) as e:  # no index, no API key, unreadable index files
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # a Voyage API error such as an invalid or expired key
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(hits, indent=2))
    else:
        from_flag = args.max_distance is not None
        threshold = args.max_distance if from_flag else DEFAULT_MAX_DISTANCE
        _print_hits(hits, args.snippet_chars, threshold, from_flag)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
