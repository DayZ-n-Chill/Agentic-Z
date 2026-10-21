"""dayz-ask: gather checked evidence from vanilla DayZ for a plain English question.

  ask.py "<question>" [--top-k N] [--file-type T] [--folder F ...] [--grep] [--json]

The script does the searching and the checking; the AI only reads the
evidence and writes the answer.

1. RAG search (search_dayz_source_impl from the dayz-rag server) when the
   index is built and VOYAGE_API_KEY is set.
2. Every hit is checked against the file on P:\\: the cited lines must still
   hold the indexed text. A hit whose text moved is re-cited at its new line;
   one whose text is gone is dropped.
3. With no key, no index, a search error or no checked hit, a keyword scan
   of the vanilla folders on P:\\ (the Grep fallback) gives the evidence.

The first output line is the verdict: EVIDENCE (exit 0), NONE (exit 1, nothing
found) or ERROR (exit 2: empty question, bad argument, P:\\ not mounted).
Each citation is path:line_start-line_end with the lines read from disk.
See SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent
REPO = SKILLS_DIR.parents[1]
sys.path.insert(0, str(SKILLS_DIR / "_shared"))
import skill_helpers as h  # noqa: E402

RAG_DIR = REPO / ".claude" / "mcp" / "dayz-rag"
sys.path.insert(0, str(RAG_DIR))
import voyage_common  # noqa: E402  same key lookup as the server

P_DRIVE = Path("P:\\")
DEFAULT_TOP_K = 5
MAX_TOP_K = 25
EXCERPT_LINES = 60  # longest excerpt printed per citation
LINES_PER_FILE = 3  # matching lines kept per file in the Grep fallback
CONTEXT = 2  # lines shown around a Grep match

# The vanilla folders /dayz-search-index walks (index.py VANILLA_FOLDERS).
VANILLA_FOLDERS = ("scripts", "dz", "gui", "core", "graphics", "languagecore")
DEFAULT_FOLDERS = ("scripts", "dz")

# file_type value -> file extension, as in the index (index.py EXT_TYPE_MAP).
FILE_TYPES = {t: "." + t for t in ("c", "cpp", "hpp", "h", "layout", "cfg", "rvmat", "xml", "json", "csv")}

# Words that say nothing about where in vanilla to look.
STOPWORDS = set("""
a about after all also an and any are as at be been before being but by can could did do does doing done
dayz each else for from game get gets got had has have how i if in into is it its just like make makes
many may me more most much my need needs not of off on once one only or other our out over own same see
set should show so some such than that the their them then there these they this those through to too
under until up use used uses using vanilla very was way we were what when where which while who why will
with work works would you your
""".split())

_SUFFIXES = ("ing", "age", "ed", "es", "s")


def search_terms(question: str) -> list[str]:
    """Lower-case search terms from a question, stop words dropped, light stemming.

    Terms are matched as substrings, so "spoilage" becomes "spoil" and still
    finds "spoiled" and "SpoilTime".
    """
    terms: list[str] = []
    for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", question):
        w = word.lower()
        if len(w) < 3 or w in STOPWORDS:
            continue
        for suffix in _SUFFIXES:
            if w.endswith(suffix) and len(w) - len(suffix) >= 4:
                w = w[: -len(suffix)]
                break
        if w not in terms:
            terms.append(w)
    return terms


def _norm(line: str) -> str:
    return " ".join(line.split())


def _read_lines(path: Path) -> Optional[list[str]]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None


def _excerpt(lines: list[str], start: int, end: int) -> str:
    end = min(end, start + EXCERPT_LINES - 1, len(lines))
    return "\n".join(lines[start - 1 : end])


def _on_p(path: str) -> bool:
    """True for a path on the P: drive (the only place vanilla files are read from)."""
    norm = os.path.normcase(os.path.normpath(path)) if path else ""
    return norm.startswith(os.path.normcase(str(P_DRIVE)))


def _probe(snippet: str) -> list[str]:
    """The first lines of a snippet worth checking: three with some text, not lone braces."""
    lines = [_norm(x) for x in snippet.splitlines() if _norm(x)]
    return [x for x in lines if len(x) >= 4][:3] or lines[:3]


def _holds(window: list[str], probe: list[str]) -> bool:
    """True when the probe lines appear in the window in order.

    A file line matches when it starts with the probe line: the indexer can
    drop a class block's closing ";" and slices very long lines.
    """
    it = iter(_norm(x) for x in window)
    return all(any(line.startswith(p) for line in it) for p in probe)


def verify_hit(hit: dict) -> dict:
    """Check one search hit against the file on disk.

    Returns the hit as a citation with status "verified" (the cited lines hold
    the indexed text), "moved" (the text is in the file at another line, and
    the citation points there now) or "changed" (the text is gone, or the file
    is missing or off P:\\).
    """
    path = hit.get("path", "")
    start, end = int(hit.get("line_start") or 1), int(hit.get("line_end") or 1)
    cite = {
        "source": "rag",
        "path": path,
        "line_start": start,
        "line_end": end,
        "context": hit.get("parent_context", ""),
        "distance": hit.get("distance"),
    }
    lines = _read_lines(Path(path)) if _on_p(path) else None
    if lines is None:
        return {**cite, "status": "changed", "reason": "file missing or not on P:\\"}
    probe = _probe(hit.get("snippet") or "")
    if not probe:
        return {**cite, "status": "changed", "reason": "hit has no text to check"}
    span = end - start
    if _holds(lines[start - 1 : end], probe):
        return {**cite, "status": "verified", "excerpt": _excerpt(lines, start, end)}
    for i, line in enumerate(lines):
        if _norm(line).startswith(probe[0]) and _holds(lines[i : i + span + 1], probe):
            new_start = i + 1
            new_end = min(new_start + span, len(lines))
            return {
                **cite,
                "line_start": new_start,
                "line_end": new_end,
                "status": "moved",
                "reason": f"indexed at line {start}; rebuild with /dayz-search-index --full",
                "excerpt": _excerpt(lines, new_start, new_end),
            }
    return {**cite, "status": "changed", "reason": "cited lines no longer match the index"}


def grep_vanilla(terms: list[str], folders: list[str], file_type: Optional[str], top_k: int,
                 root: Optional[Path] = None) -> list[dict]:
    """Keyword scan of the vanilla folders: the Grep fallback.

    A term found in few files weighs more than one found everywhere (log of
    files scanned over files holding it). A file scores the weight of the terms
    it holds plus that of its best line; each of the top_k files gives up to
    LINES_PER_FILE citations around its best lines.
    """
    if not terms:
        return []
    root = root or P_DRIVE
    exts = {FILE_TYPES[file_type]} if file_type else set(FILE_TYPES.values()) - {".rvmat"}
    scanned = 0
    found = []  # (path, lines, terms present)
    for folder in folders:
        base = root / folder
        if not base.is_dir():
            continue
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                if os.path.splitext(name)[1].lower() not in exts:
                    continue
                path = Path(dirpath) / name
                lines = _read_lines(path)
                if not lines:
                    continue
                scanned += 1
                low = "\n".join(lines).lower()
                present = [t for t in terms if t in low]
                if present:
                    found.append((str(path), lines, present))
    df = {t: sum(1 for _p, _l, present in found if t in present) for t in terms}
    weight = {t: math.log((scanned + 1) / df[t]) for t in terms if df[t]}
    scored = []
    for path, lines, present in found:
        line_scores = []
        for i, line in enumerate(lines):
            ll = line.lower()
            w = sum(weight[t] for t in present if t in ll)
            if w:
                line_scores.append((w, i))
        line_scores.sort(key=lambda x: (-x[0], x[1]))
        score = sum(weight[t] for t in present) + line_scores[0][0]
        scored.append((score, len(lines), path, lines, line_scores, len(present)))
    scored.sort(key=lambda s: (-s[0], s[1], s[2]))
    cites = []
    for _score, _n, path, lines, line_scores, n_terms in scored[:top_k]:
        spans: list[list] = []  # [start, end, best line, its weight]; overlapping windows merge
        for w, i in sorted(line_scores[:LINES_PER_FILE], key=lambda x: x[1]):
            start, end = max(1, i + 1 - CONTEXT), min(len(lines), i + 1 + CONTEXT)
            if spans and start <= spans[-1][1] + 1:
                spans[-1][1] = end
                if w > spans[-1][3]:
                    spans[-1][2:] = [i + 1, w]
            else:
                spans.append([start, end, i + 1, w])
        for start, end, match, _w in spans:
            cites.append({
                "source": "grep",
                "path": path,
                "line_start": start,
                "line_end": end,
                "match_line": match,
                "terms_in_file": n_terms,
                "status": "verified",
                "excerpt": _excerpt(lines, start, end),
            })
    return cites


def _load_server():
    return h.load_module("dayz_ask_rag_server", RAG_DIR / "server.py")


def rag_unavailable(server) -> Optional[str]:
    """Why RAG search can't run here, or None when it can."""
    if not (server.INDEX_ROOT / "lancedb").exists():
        return "no search index; run /dayz-search-download or /dayz-search-index --full"
    try:
        voyage_common.load_api_key()
    except RuntimeError:
        return "VOYAGE_API_KEY not set; add it to .env at the repo root"
    return None


def ask(question: str, top_k: int = DEFAULT_TOP_K, file_type: Optional[str] = None,
        folders: Optional[list[str]] = None, force_grep: bool = False, server=None) -> dict:
    """Gather checked citations for a question. Returns the report dict."""
    folders = list(folders or DEFAULT_FOLDERS)
    notes: list[str] = []
    cites: list[dict] = []
    dropped: list[dict] = []
    mode = "grep"
    if force_grep:
        notes.append("Grep forced with --grep")
    else:
        server = server or _load_server()
        why = rag_unavailable(server)
        if why:
            notes.append(f"RAG search skipped: {why}")
        else:
            try:
                hits = server.search_dayz_source_impl(question, top_k=top_k, file_type=file_type)
            except Exception as exc:  # any search failure falls back to Grep, with the reason
                notes.append(f"RAG search failed: {exc}")
            else:
                mode = "rag"
                for hit in hits:
                    c = verify_hit(hit)
                    (cites if c["status"] != "changed" else dropped).append(c)
                if dropped:
                    notes.append(f"{len(dropped)} hit(s) dropped: the file no longer holds the indexed text; "
                                 "rebuild with /dayz-search-index --full")
                if not cites:
                    notes.append("no RAG hit survived the check; used Grep")
    if not cites:
        terms = search_terms(question)
        cites = grep_vanilla(terms, folders, file_type, top_k)
        mode = "grep" if mode == "grep" or not cites else "rag+grep"
        where = ", ".join(str(P_DRIVE / f) for f in folders)
        notes.append(f"Grep terms: {', '.join(terms) or '(none)'} in {where}")
    for c in cites:
        c["cite"] = f"{c['path']}:{c['line_start']}-{c['line_end']}"
    return {
        "verdict": "EVIDENCE" if cites else "NONE",
        "question": question,
        "mode": mode,
        "notes": notes,
        "citations": cites,
        "dropped": [{"cite": f"{d['path']}:{d['line_start']}-{d['line_end']}", "reason": d["reason"]}
                    for d in dropped],
    }


def print_report(report: dict) -> None:
    n = len(report["citations"])
    print(report["verdict"] if not n else f"EVIDENCE {n} citation(s) via {report['mode']}")
    for note in report["notes"]:
        print(f"  note: {note}")
    for i, c in enumerate(report["citations"], 1):
        extra = f"  distance={c['distance']:.3f}" if c.get("distance") is not None else ""
        ctx = f"  {c['context']}" if c.get("context") else ""
        print(f"\n[{i}] {c['cite']}  {c['status']}{extra}{ctx}")
        if c.get("reason"):
            print(f"    ({c['reason']})")
        for line in c["excerpt"].splitlines():
            print(f"    | {line}")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="dayz-ask", description="Checked vanilla DayZ evidence for a question.")
    p.add_argument("question", nargs="+", help="plain English question about vanilla DayZ")
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help=f"hits or files to keep (1-{MAX_TOP_K})")
    p.add_argument("--file-type", choices=sorted(FILE_TYPES), help="only this file type")
    p.add_argument("--folder", action="append", choices=VANILLA_FOLDERS,
                   help="vanilla folder for the Grep fallback (repeatable; default scripts and dz)")
    p.add_argument("--grep", action="store_true", help="skip RAG and use the Grep fallback")
    p.add_argument("--json", action="store_true", help="print the report as JSON after the verdict line")

    def arg_error(message: str) -> None:
        # Bad arguments get the same ERROR first line as every other refusal.
        print(f"ERROR\n  {message}")
        raise SystemExit(2)

    p.error = arg_error
    try:
        args = p.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2

    question = " ".join(" ".join(args.question).split())
    if not question:
        print("ERROR\n  empty question")
        return 2
    if not 1 <= args.top_k <= MAX_TOP_K:
        print(f"ERROR\n  --top-k must be 1 to {MAX_TOP_K}")
        return 2
    if not P_DRIVE.exists():
        print("ERROR\n  P:\\ is not mounted, so vanilla files can't be read. Run /dayz-workdrive.")
        return 2

    report = ask(question, args.top_k, args.file_type, args.folder, args.grep)
    if args.json:
        print(report["verdict"])
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return 0 if report["citations"] else 1


if __name__ == "__main__":
    sys.exit(main())
