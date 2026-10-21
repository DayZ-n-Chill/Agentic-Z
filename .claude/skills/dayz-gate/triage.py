"""dayz-gate triage: match DayZ log and build-output lines against known errors.

Each line is fingerprinted (timestamps, absolute paths, addresses and numbers
normalized, lowercased) and matched against two catalogs:

  known-errors.json (next to this file)  regex entries shipped with the repo
  <project>/.claude/local-memory/dayz-gate-known-errors.json
                                         fingerprints a reviewer learned with
                                         --learn (per project, gitignored)

A matched line is "known" and carries the fix and the owning agent; anything
else is "new" and goes to dayz-mod-debugger. Entries with "scope": "scripts" or
"config" are checked against the mod's source files instead of log lines.

Usage:
  python triage.py <log-file> [<log-file> ...] [--mod <ModName>] [--mod-dir DIR] [--json]
  python triage.py --learn <id> --fingerprint "<fp>" [--meaning ... --fix ... --owner ...]

See SKILL.md for details.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

HERE = Path(__file__).resolve().parent
KNOWN_ERRORS = HERE / "known-errors.json"
LEARNED_FILENAME = "dayz-gate-known-errors.json"

# Order matters: timestamps first (they contain numbers), then addresses and
# absolute paths, then every remaining number.
_TIMESTAMP_RE = re.compile(r"^\s*\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\s*")
_ADDRESS_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")
_ABS_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\)[^\s'\"<>|]*")
_NUMBER_RE = re.compile(r"\d+")
_SPACE_RE = re.compile(r"\s+")

# Error lines the engine and the pipeline scripts write, by category, first match
# wins. Formats are taken from real DayZ Diag RPT, script and crash logs.
ERROR_CATEGORIES: list[tuple[str, re.Pattern]] = [
    ("crash", re.compile(r"(?i)unhandled exception|access violation")),
    # `Can't compile "World" script module!`, `SCRIPT    (E): @"MyMod/scripts/4_World/x.c,12": ...`
    # and the RPT form `MyMod/scripts/4_World/x.c(12): Unknown type 'Foo'`.
    ("compile", re.compile(r"Can't compile \"\w+\" script module|SCRIPT\s+\(E\):\s*@\"[^\"]+,\d+\"|\.c\(\d+\):")),
    ("null_pointer", re.compile(r"NULL pointer to instance")),
    ("cant_find", re.compile(r"Can't find\b")),
    ("connection", re.compile(r"0x00020005|does not support the client's current filePatching setting")),
    ("mission", re.compile(r"Mission script has no main function")),
    ("missing_config", re.compile(r"No entry '")),
    ("missing_texture", re.compile(r"Cannot load texture")),
    ("missing_model", re.compile(r"Cannot open object")),
    ("script_fail", re.compile(r"^\[FAIL\]")),
]


def classify(line: str) -> Optional[str]:
    """The error category of a line, or None for a line that reports no error."""
    for name, regex in ERROR_CATEGORIES:
        if regex.search(line):
            return name
    return None


def fingerprint(line: str) -> str:
    """A stable identity for a log line: same error, different run, same fingerprint."""
    text = _TIMESTAMP_RE.sub("", line)
    text = _ADDRESS_RE.sub("<addr>", text)
    text = _ABS_PATH_RE.sub("<path>", text)
    text = _NUMBER_RE.sub("<n>", text)
    text = text.replace("\\", "/")
    return _SPACE_RE.sub(" ", text).strip().lower()


def learned_path(project_dir: Path) -> Path:
    return project_dir / ".claude" / "local-memory" / LEARNED_FILENAME


def cached_project_dir() -> Optional[Path]:
    """The project cached by /dayz-init, or None (triage then skips learned entries)."""
    state = h.load_module("dayz_init_state_for_triage", h.DAYZ_INIT_STATE)
    project = state.cached_project_root()
    return project if project is not None and project.is_dir() else None


def _read_json_list(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must hold a JSON list of entries")
    return data


def load_known(shipped: Path = KNOWN_ERRORS, learned: Optional[Path] = None) -> list[dict]:
    """Shipped regex entries (compiled) followed by learned fingerprint entries."""
    entries = []
    for entry in _read_json_list(shipped):
        entry = dict(entry)
        entry["_re"] = re.compile(entry["pattern"])
        entries.append(entry)
    if learned is not None:
        entries.extend(dict(e) for e in _read_json_list(learned))
    return entries


def _fill(text: str, context: dict) -> str:
    for key, value in context.items():
        if value:
            text = text.replace(f"<{key}>", str(value))
    return text


def match_line(line: str, known: list[dict], context: Optional[dict] = None) -> dict:
    """Triage one line: {"status": "known", id, meaning, fix, owner_agent, fingerprint} or "new"."""
    fp = fingerprint(line)
    for entry in known:
        if entry.get("scope", "log") != "log":
            continue
        regex = entry.get("_re")
        hit = regex.search(line) if regex is not None else entry.get("fingerprint") == fp
        if hit:
            return {
                "status": "known",
                "id": entry["id"],
                "meaning": entry["meaning"],
                "fix": _fill(entry["fix"], context or {}),
                "owner_agent": entry["owner_agent"],
                "fingerprint": fp,
            }
    return {"status": "new", "fingerprint": fp}


def check_sources(mod_dir: Path, known: list[dict], context: Optional[dict] = None) -> list[dict]:
    """Run the source-scoped entries against the mod's files.

    scope "scripts": the regex is searched in every scripts/**/*.c line; each hit
    is reported with file and line. scope "config": checked against config.cpp;
    with "match": "absent" the entry fires when the regex is NOT found there.
    A mod without config.cpp (a payload bundle) skips the config entries.
    """
    findings = []
    for entry in known:
        scope = entry.get("scope", "log")
        if scope == "scripts":
            for path in sorted((mod_dir / "scripts").rglob("*.c")):
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                for number, text in enumerate(lines, 1):
                    if entry["_re"].search(text):
                        findings.append(_finding(entry, path, number, text, context))
        elif scope == "config":
            cfg = mod_dir / "config.cpp"
            if not cfg.is_file():
                continue
            found = entry["_re"].search(cfg.read_text(encoding="utf-8", errors="replace"))
            if entry.get("match", "present") == "absent" and not found:
                findings.append(_finding(entry, cfg, None, "", context))
            elif entry.get("match", "present") == "present" and found:
                number = cfg.read_text(encoding="utf-8", errors="replace").count("\n", 0, found.start()) + 1
                findings.append(_finding(entry, cfg, number, found.group(0), context))
    return findings


def _finding(entry: dict, path: Path, number: Optional[int], text: str, context: Optional[dict]) -> dict:
    return {
        "status": "known",
        "id": entry["id"],
        "file": str(path),
        "line": number,
        "text": text.strip(),
        "meaning": entry["meaning"],
        "fix": _fill(entry["fix"], context or {}),
        "owner_agent": entry["owner_agent"],
    }


def learn(
    entry_id: str,
    fp: str,
    learned: Path,
    known: list[dict],
    meaning: Optional[str] = None,
    fix: Optional[str] = None,
    owner: Optional[str] = None,
) -> dict:
    """Append a reviewed fingerprint to the per-project learned file.

    An id that already exists (shipped or learned) lends its meaning, fix and
    owner unless they are given; a new id needs all three.
    """
    fp = fingerprint(fp)  # accept a raw log line as well as a fingerprint
    base = next((e for e in known if e["id"] == entry_id), None)
    meaning = meaning or (base or {}).get("meaning")
    fix = fix or (base or {}).get("fix")
    owner = owner or (base or {}).get("owner_agent")
    if not (meaning and fix and owner):
        raise ValueError(f"'{entry_id}' is not a known id; pass --meaning, --fix and --owner")
    entries = _read_json_list(learned)
    if any(e.get("fingerprint") == fp for e in entries):
        raise ValueError(f"fingerprint already learned: {fp}")
    entry = {"id": entry_id, "fingerprint": fp, "meaning": meaning, "fix": fix, "owner_agent": owner}
    entries.append(entry)
    learned.parent.mkdir(parents=True, exist_ok=True)
    learned.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    return entry


def triage_files(paths: Iterable[Path], known: list[dict], context: Optional[dict] = None) -> list[dict]:
    """Triage the error lines of the given files, deduplicated by fingerprint.

    A line counts when classify() gives it a category or a known entry matches it.
    """
    seen: dict[str, dict] = {}
    for path in paths:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for number, text in enumerate(lines, 1):
            category = classify(text)
            result = match_line(text, known, context)
            if category is None and result["status"] == "new":
                continue
            result["category"] = category
            fp = result["fingerprint"]
            if fp in seen:
                seen[fp]["count"] += 1
                continue
            seen[fp] = {"file": str(path), "line": number, "text": text.strip(), "count": 1, **result}
    return list(seen.values())


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Match DayZ log lines against known errors.")
    parser.add_argument("files", nargs="*", type=Path, help="Log or build-output files to triage.")
    parser.add_argument("--mod", help="Mod name, filled into fixes that mention <ModName>.")
    parser.add_argument("--mod-dir", type=Path, help="workspace/<ModName>/ to run the source checks on.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    parser.add_argument("--learn", metavar="ID", help="Record --fingerprint under ID in the project's learned file.")
    parser.add_argument("--fingerprint", help="With --learn: the fingerprint (or raw log line) to record.")
    parser.add_argument("--meaning", help="With --learn on a new id: what the error means.")
    parser.add_argument("--fix", help="With --learn on a new id: how to fix it.")
    parser.add_argument("--owner", help="With --learn on a new id: the agent that owns the fix.")
    args = parser.parse_args(argv)

    project = cached_project_dir()
    learned = learned_path(project) if project else None
    try:
        known = load_known(KNOWN_ERRORS, learned)
    except (ValueError, json.JSONDecodeError, re.error) as e:
        print(f"{h.FAIL} Could not load known errors: {e}", file=sys.stderr)
        return 2

    if args.learn:
        if learned is None:
            print(f"{h.FAIL} No project cached; run /dayz-init so --learn has a project to write to.", file=sys.stderr)
            return 2
        if not args.fingerprint:
            parser.error("--learn needs --fingerprint")
        try:
            entry = learn(args.learn, args.fingerprint, learned, known, args.meaning, args.fix, args.owner)
        except ValueError as e:
            print(f"{h.FAIL} {e}", file=sys.stderr)
            return 2
        print(f"{h.OK} Learned {entry['id']}: {entry['fingerprint']}")
        print(f"       Written to {learned}")
        return 0

    if not args.files and not args.mod_dir:
        parser.error("give log files to triage, --mod-dir, or --learn")
    missing = [str(p) for p in args.files if not p.is_file()]
    if missing:
        print(f"{h.FAIL} Not found: {', '.join(missing)}", file=sys.stderr)
        return 2

    context = {"ModName": args.mod}
    results = triage_files(args.files, known, context)
    sources = check_sources(args.mod_dir, known, context) if args.mod_dir else []
    if args.json:
        print(json.dumps({"lines": results, "source_findings": sources}, indent=2))
        return 0
    for r in results + sources:
        where = f"{r['file']}:{r['line']}" if r.get("line") else r["file"]
        if r["status"] == "known":
            print(f"known {r['id']} -> {r['owner_agent']}  {where}")
            print(f"      {r['text']}")
            print(f"      fix: {r['fix']}")
        else:
            print(f"new   {where}  {r['text']}")
    return 0


if __name__ == "__main__":
    # Log lines can hold characters a cp1252 console can't print.
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
