"""Standalone CLI for the DayZ RAG index. Bypasses the MCP server / model entirely.

Usage:
    dayz-search <query>                  # source corpus, top 5
    dayz-search -k 3 <query>             # top 3
    dayz-search -t c <query>             # filter to file_type=c (Enforce Script)
    dayz-search -s 800 <query>           # snippet preview length (default 400)
    dayz-search -j <query>               # raw JSON output

Reuses search_dayz_source_impl from the MCP server module so behavior matches
what agents see. A missing index, a missing VOYAGE_API_KEY or a bad argument
prints one 'error:' line and exits 2.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_DIR = REPO_ROOT / ".claude" / "mcp" / "dayz-rag"
sys.path.insert(0, str(MCP_DIR))

from server import VALID_FILE_TYPES, search_dayz_source_impl  # noqa: E402


def _print_hits(hits: list[dict], snippet_chars: int) -> None:
    if not hits:
        print("(no hits)")
        return
    for i, h in enumerate(hits, 1):
        path = h.get("path", "")
        ls = h.get("line_start", 0)
        le = h.get("line_end", 0)
        distance = h.get("distance", 0.0)
        ctx = h.get("parent_context", "")
        stale = " [STALE]" if h.get("is_stale") else ""
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
    p.add_argument("-d", "--max-distance", type=float, default=None, help="drop hits with distance above this")
    p.add_argument("-s", "--snippet-chars", type=int, default=400, help="snippet preview length (0 = full)")
    p.add_argument("-j", "--json", action="store_true", help="print raw JSON instead of formatted output")
    args = p.parse_args(argv)

    query = " ".join(args.query).strip()
    if not query:
        print("error: empty query", file=sys.stderr)
        return 2

    try:
        hits = search_dayz_source_impl(
            query, top_k=args.top_k, file_type=args.file_type, max_distance=args.max_distance,
        )
    except (RuntimeError, ValueError, OSError) as e:  # no index, no API key, unreadable index files
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(hits, indent=2))
    else:
        _print_hits(hits, args.snippet_chars)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
