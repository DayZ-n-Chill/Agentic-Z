"""dayz-ask: gather checked evidence from vanilla DayZ for a plain English question.

  ask.py "<question>" [--top-k N] [--file-type T] [--folder F ...] [--grep] [--json]

The script does the searching and the checking; the AI only reads the
evidence and writes the answer.

1. RAG search (search_dayz_source_impl from the dayz-rag server) when the
   index is built and VOYAGE_API_KEY is set.
2. Every hit is checked against the file on P:\\: the cited lines must still
   hold the indexed text. A hit whose text moved is re-cited at its new line;
   one whose text is gone is dropped.
3. A checked hit longer than EXCERPT_LINES (often a whole config class) is
   re-cited at its best term lines, as the Grep fallback picks lines in a
   file; one with no term line inside it is dropped as off topic.
4. A checked hit is kept only when it is on topic: its distance is at most
   RAG_MAX_DISTANCE and its text or class holds a search term from the question.
5. With no key, no index, a search error or no kept hit, a keyword scan
   of the vanilla folders on P:\\ (the Grep fallback) gives the evidence.

The first output line is the verdict: EVIDENCE (exit 0), NONE (exit 1, nothing
found) or ERROR (exit 2: empty question, no search terms, bad argument, P:\\
not mounted, or the script crashed or could not load the dayz-rag server).
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
RAG_DIR = REPO / ".claude" / "mcp" / "dayz-rag"
sys.path.insert(0, str(SKILLS_DIR / "_shared"))
sys.path.insert(0, str(RAG_DIR))
# A failed import is reported by main() as an ERROR line with exit 2, not a traceback.
try:
    import skill_helpers as h  # noqa: E402
    import voyage_common  # noqa: E402  same key lookup as the server
except Exception as _exc:  # noqa: BLE001
    h = voyage_common = None
    IMPORT_ERROR: Optional[str] = f"{type(_exc).__name__}: {_exc}"
else:
    IMPORT_ERROR = None

P_DRIVE = Path("P:\\")
DEFAULT_TOP_K = 5
MAX_TOP_K = 25
DEFAULT_EXCERPT_LINES = 60
EXCERPT_LINES = DEFAULT_EXCERPT_LINES  # longest excerpt printed per citation; --excerpt-lines sets it
MAX_EXCERPT_LINES = 300
LINES_PER_FILE = 3  # matching lines kept per file in the Grep fallback
CONTEXT = 2  # lines shown around a Grep match
# Grep score multiplier for debug and GUI code (a folder named gui, or "debug" in any
# folder or file name, e.g. scripts\5_mission\gui\scriptshuddebug). Those files name
# gameplay terms in widgets and debug readouts, so they rank below the gameplay classes.
DEBUG_GUI_WEIGHT = 0.5
# Farthest RAG hit kept (LanceDB L2 squared distance, voyage-code-3 index). Calibrated on
# live runs: on-topic hits for bleeding, stamina and CanDecay questions sat at 0.70 to 1.06;
# nonsense questions ("make pizza fly to the moon", "banana republic stock market tax")
# returned nothing closer than 1.24.
RAG_MAX_DISTANCE = 1.15

# A class or function declaration: "class FoodStage", "override void ProcessDecay(".
_KEYWORDS = {"return", "if", "while", "for", "foreach", "switch", "else", "new", "delete", "case"}
_CLASS_DECL = re.compile(r"^\s*(?:modded\s+)?class\s+(\w+)")
_FUNC_DECL = re.compile(r"^\s*((?:[\w<>,\[\]]+\s+)+)(\w+)\s*\(")

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

# Two-letter words kept as search terms even when written in lower case. Any other
# two-letter word is kept only when written in capitals ("HP", "NV"), so "is" and
# "it" are still dropped. Stop words are dropped in any case ("IT", "IS").
SHORT_TERMS = {"ai", "hp", "ui", "id", "nv", "uv"}
_short_re_cache: dict[str, re.Pattern] = {}


def _short_re(term: str) -> re.Pattern:
    """Pattern for a two-letter term as its own word or name part, never inside a word.

    "AI" matches EntityAI, DayZCreatureAI and a lone "ai", but not FAIL, MAIN_MENU,
    RAISED or UAInput; "HP" matches zoneHP and HPTypes but not THROUGHPUT.
    """
    pat = _short_re_cache.get(term)
    if pat is None:
        up = re.escape(term.upper())
        low = re.escape(term)
        pat = re.compile(rf"(?<![A-Z]){up}(?![a-z])|(?<![A-Za-z]){low}(?![A-Za-z])")
        _short_re_cache[term] = pat
    return pat


def _has_term(term: str, text: str, low: Optional[str] = None) -> bool:
    """True when text holds the search term.

    A term of three letters or more is a lower-case substring match, so "spoil"
    finds "SpoilTime". A two-letter term would match inside too many words that
    way ("ai" in "main", "fail"), so it is matched by case on its own word or name
    part instead (see _short_re). Pass low (text.lower()) when it is already known.
    """
    if len(term) < 3:
        return _short_re(term).search(text) is not None
    return term in (low if low is not None else text.lower())


def search_terms(question: str) -> list[str]:
    """Lower-case search terms from a question, stop words dropped, light stemming.

    Terms are matched as substrings, so "spoilage" becomes "spoil" and still
    finds "spoiled" and "SpoilTime". Words shorter than three letters are dropped,
    except a two-letter word written in capitals or listed in SHORT_TERMS
    ("AI", "HP", "ui"), which is matched as its own word (see _has_term).
    """
    terms: list[str] = []
    for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", question):
        w = word.lower()
        if w in STOPWORDS or len(w) < 2:
            continue
        if len(w) == 2 and not (word.isupper() or w in SHORT_TERMS):
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


# A quoted asset path such as "\dz\gear\food\BoxCereal.p3d". A search term inside one
# ("food" in a model path) says where the asset sits, not what the class does.
_QUOTED_PATH = re.compile(r'"[^"\n]*[\\/][^"\n]*"')


def _topic_text(text: str) -> str:
    """Text for term matching on RAG hits, quoted asset paths removed (case kept for _has_term)."""
    return _QUOTED_PATH.sub('""', text)


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


def _term_windows(line_scores: list[tuple], n_lines: int, lo: int = 1,
                  hi: Optional[int] = None) -> list[list]:
    """Windows of CONTEXT lines around the best LINES_PER_FILE scored lines.

    line_scores holds (weight, 0-based line index), best first. Returns
    [start, end, best line, its weight] lists (1-based, kept inside lo..hi);
    overlapping windows merge. Shared by the Grep fallback and narrow_hit.
    """
    hi = min(hi or n_lines, n_lines)
    spans: list[list] = []
    for w, i in sorted(line_scores[:LINES_PER_FILE], key=lambda x: x[1]):
        start, end = max(lo, i + 1 - CONTEXT), min(hi, i + 1 + CONTEXT)
        if spans and start <= spans[-1][1] + 1:
            spans[-1][1] = end
            if w > spans[-1][3]:
                spans[-1][2:] = [i + 1, w]
        else:
            spans.append([start, end, i + 1, w])
    return spans


def narrow_hit(cite: dict, terms: list[str]) -> Optional[list[dict]]:
    """Re-cite a checked RAG hit longer than EXCERPT_LINES at its best term lines.

    The index can return a whole config class (the CfgVehicles chunk of
    P:\\dz\\gear\\food\\config.cpp spans some 14,000 lines) while the excerpt shows
    only the first EXCERPT_LINES of it. Lines inside the span are scored as the
    Grep fallback scores a file's lines (a term on fewer lines weighs more;
    quoted asset paths do not count), and each window becomes its own citation,
    with "within" naming the whole span. A short hit comes back unchanged.
    Returns None when no line inside the span holds a search term.
    """
    start, end = cite["line_start"], cite["line_end"]
    if end - start + 1 <= EXCERPT_LINES:
        return [cite]
    lines = _read_lines(Path(cite["path"])) or []
    end = min(end, len(lines))
    body = [_topic_text(lines[i]) for i in range(start - 1, end)]
    body_low = [x.lower() for x in body]
    df = {t: sum(1 for x, xl in zip(body, body_low) if _has_term(t, x, xl)) for t in terms}
    weight = {t: math.log((len(body) + 1) / df[t]) for t in terms if df[t]}
    line_scores = []
    for k, (text, low) in enumerate(zip(body, body_low)):
        w = sum(wt for t, wt in weight.items() if _has_term(t, text, low))
        if w:
            line_scores.append((w, start - 1 + k))
    if not line_scores:
        return None
    line_scores.sort(key=lambda x: (-x[0], x[1]))
    within = f"{cite['path']}:{cite['line_start']}-{cite['line_end']}"
    return [{**cite, "line_start": s, "line_end": e, "within": within, "excerpt": _excerpt(lines, s, e)}
            for s, e, _m, _w in _term_windows(line_scores, len(lines), start, end)]


def too_far(cite: dict) -> Optional[str]:
    """Why a RAG hit is farther than RAG_MAX_DISTANCE, or None when it is close enough."""
    dist = cite.get("distance")
    if dist is not None and dist > RAG_MAX_DISTANCE:
        return f"off topic: distance {dist:.3f} is above {RAG_MAX_DISTANCE}"
    return None


def off_topic(cite: dict, terms: list[str]) -> Optional[str]:
    """Why a checked RAG hit is off topic, or None when it is kept.

    Off topic means farther than RAG_MAX_DISTANCE, or no search term in its
    excerpt or class context (a hit can match by meaning and still be about
    something else, e.g. a cooking config class for a food spoilage question).
    """
    if why := too_far(cite):
        return why
    text = _topic_text(f"{cite.get('excerpt', '')}\n{cite.get('context') or ''}")
    low = text.lower()
    if terms and not any(_has_term(t, text, low) for t in terms):
        return "off topic: holds no search term from the question"
    return None


def _declared_names(lines: list[str]) -> list[str]:
    """Lower-case class and function names declared in a script file."""
    names = []
    for line in lines:
        m = _CLASS_DECL.match(line)
        if m:
            names.append(m.group(1).lower())
            continue
        m = _FUNC_DECL.match(line)
        if m and m.group(1).split()[0] not in _KEYWORDS:
            names.append(m.group(2).lower())
    return names


def _name_holds(term: str, name: str) -> bool:
    """True when a lower-case declared name holds the term.

    A two-letter term counts only at the start or end of the name ("entityai",
    "uiscriptedmenu"), not inside it ("main", "fail").
    """
    if len(term) < 3:
        return name.startswith(term) or name.endswith(term)
    return term in name


def _is_debug_or_gui(path: Path, root: Path) -> bool:
    """True for a file under a gui folder, or with "debug" in a folder or file name.

    The vanilla folder scanned (scripts, dz, gui, ...) is not counted, so a
    --folder gui scan is not down-weighted as a whole.
    """
    parts = [x.lower() for x in path.relative_to(root).parts[1:]]
    return "gui" in parts[:-1] or any("debug" in x for x in parts)


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
                whole = "\n".join(lines)
                low = whole.lower()
                present = [t for t in terms if _has_term(t, whole, low)]
                if present:
                    found.append((str(path), lines, present))
    df = {t: sum(1 for _p, _l, present in found if t in present) for t in terms}
    weight = {t: math.log((scanned + 1) / df[t]) for t in terms if df[t]}
    scored = []
    for path, lines, present in found:
        line_scores = []
        for i, line in enumerate(lines):
            ll = line.lower()
            w = sum(weight[t] for t in present if _has_term(t, line, ll))
            if w:
                line_scores.append((w, i))
        line_scores.sort(key=lambda x: (-x[0], x[1]))
        score = sum(weight[t] for t in present) + line_scores[0][0]
        names = _declared_names(lines)
        score += sum(weight[t] for t in present if any(_name_holds(t, n) for n in names))
        if _is_debug_or_gui(Path(path), root):
            score *= DEBUG_GUI_WEIGHT
        scored.append((score, len(lines), path, lines, line_scores, len(present)))
    scored.sort(key=lambda s: (-s[0], s[1], s[2]))
    cites = []
    for _score, _n, path, lines, line_scores, n_terms in scored[:top_k]:
        for start, end, match, _w in _term_windows(line_scores, len(lines)):
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
    terms = search_terms(question)
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
                stale = unrelated = narrowed = 0
                for hit in hits:
                    c = verify_hit(hit)
                    if c["status"] == "changed":
                        stale += 1
                        dropped.append(c)
                        continue
                    # Distance first, so a far whole-class hit is dropped once, whole,
                    # instead of once per re-cited window.
                    if why_far := too_far(c):
                        unrelated += 1
                        dropped.append({**c, "reason": why_far})
                        continue
                    parts = narrow_hit(c, terms)
                    if parts is None:
                        unrelated += 1
                        n_lines = c["line_end"] - c["line_start"] + 1
                        dropped.append({**c, "reason": f"off topic: none of its {n_lines} lines "
                                                       "holds a search term from the question"})
                        continue
                    narrowed += parts[0] is not c
                    for part in parts:
                        if why_off := off_topic(part, terms):
                            unrelated += 1
                            dropped.append({**part, "reason": why_off})
                        else:
                            cites.append(part)
                if narrowed:
                    notes.append(f"{narrowed} hit(s) longer than {EXCERPT_LINES} lines re-cited at their "
                                 "best term lines; 'within' names the whole span")
                if stale:
                    notes.append(f"{stale} hit(s) dropped: the file no longer holds the indexed text; "
                                 "rebuild with /dayz-search-index --full")
                if unrelated:
                    notes.append(f"{unrelated} hit(s) dropped as off topic (distance above "
                                 f"{RAG_MAX_DISTANCE}, or no search term in the hit)")
                if not cites:
                    notes.append("no RAG hit survived the checks; used Grep")
    if not cites:
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
        if c.get("within"):
            print(f"    (within {c['within']})")
        for line in c["excerpt"].splitlines():
            print(f"    | {line}")


def main(argv: Optional[list[str]] = None) -> int:
    # A deep dive wants whole functions, not their first lines; the excerpt and
    # re-cite helpers all read this one limit.
    global EXCERPT_LINES
    p = argparse.ArgumentParser(prog="dayz-ask", description="Checked vanilla DayZ evidence for a question.")
    p.add_argument("question", nargs="+", help="plain English question about vanilla DayZ")
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help=f"hits or files to keep (1-{MAX_TOP_K})")
    p.add_argument("--file-type", choices=sorted(FILE_TYPES), help="only this file type")
    p.add_argument("--folder", action="append", choices=VANILLA_FOLDERS,
                   help="vanilla folder for the Grep fallback (repeatable; default scripts and dz)")
    p.add_argument("--grep", action="store_true", help="skip RAG and use the Grep fallback")
    p.add_argument("--excerpt-lines", type=int, default=DEFAULT_EXCERPT_LINES,
                   help=f"longest excerpt printed per citation (1-{MAX_EXCERPT_LINES})")
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

    if IMPORT_ERROR:
        print(f"ERROR\n  could not load the script's helpers ({IMPORT_ERROR})")
        return 2
    question = " ".join(" ".join(args.question).split())
    if not question:
        print("ERROR\n  empty question")
        return 2
    if not 1 <= args.top_k <= MAX_TOP_K:
        print(f"ERROR\n  --top-k must be 1 to {MAX_TOP_K}")
        return 2
    if not 1 <= args.excerpt_lines <= MAX_EXCERPT_LINES:
        print(f"ERROR\n  --excerpt-lines must be 1 to {MAX_EXCERPT_LINES}")
        return 2
    EXCERPT_LINES = args.excerpt_lines
    if not search_terms(question):
        print("ERROR\n  no search terms left once common words are dropped; "
              "name a class, function or config value")
        return 2
    if not P_DRIVE.exists():
        print("ERROR\n  P:\\ is not mounted, so vanilla files can't be read. Run /dayz-workdrive.")
        return 2

    try:
        report = ask(question, args.top_k, args.file_type, args.folder, args.grep)
    except Exception as exc:  # noqa: BLE001  a crash (e.g. server.py fails to load) is ERROR, never NONE
        print(f"ERROR\n  {type(exc).__name__}: {exc}")
        return 2
    if args.json:
        print(report["verdict"])
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return 0 if report["citations"] else 1


if __name__ == "__main__":
    sys.exit(main())
