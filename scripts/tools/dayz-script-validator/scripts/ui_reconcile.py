"""
UI-RECONCILE -- cross-file reconciliation gate for DayZ UI (renderer/skill §6.2).

Two checks that the per-file linter (script_validator.py) cannot do because they
span files:

  A. UI-FINDANYWIDGET-UNRESOLVED
     Every FindAnyWidget("X") / FindWidget("A/B/C") string-literal in .c must name
     a widget that exists in some .layout of the addon. A rename on one side leaves
     a silent null -> crash on the next Cast. Case-sensitive (runtime lookup is).

  B. UI-STR-KEY-UNRESOLVED
     Every #STR_... referenced in a .layout `text` or a .c string literal must exist
     as <Key Id="STR_..."> in the addon's stringtable. Missing keys render as the raw
     key in-game (or fail translation mods). Case-insensitive (DayZ resolves so).

Severity:
  FAIL  = a close match exists in the addon -> almost certainly a typo/rename.
  WARN  = no match at all -> could be a vanilla widget/key or a dynamically built
          name; the tool cannot know, so it asks you to verify (not a hard bug).

Only string-literal references are checked; names/keys built from variables or
concatenation are a known, deliberate false negative (cannot be resolved statically).

Usage:
    python ui_reconcile.py <addon_root> [<addon_root> ...] [--json] [--strict]
Exit: 0 clean, 1 any FAIL (typo-likely), 2 WARN only (verify). --strict makes WARN -> exit 1.

Standalone by design (reconciliation is cross-file); pairs with script_validator.py.
"""
from __future__ import annotations
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

# --- extraction regexes --------------------------------------------------------

# `Class Name {`  or  `Class "Name" {`  (widget declaration; over-collecting names is safe)
_WIDGET_DECL_RE = re.compile(r'([A-Za-z_]\w*)\s+(?:"([^"\r\n]+)"|([A-Za-z_][\w.]*))\s*\{')
# FindAnyWidget("X") and FindWidget("A/B/C")  (string literal only)
_FIND_ANY_RE = re.compile(r'\bFindAnyWidget\s*\(\s*"([^"\r\n]+)"')
_FIND_PATH_RE = re.compile(r'\bFindWidget\s*\(\s*"([^"\r\n]+)"')
# #STR_KEY references (in layouts and .c string literals)
_STR_REF_RE = re.compile(r'#(STR_[A-Za-z0-9_]+)', re.IGNORECASE)
# <Key Id="STR_..."> / Id='...'  (stringtable.xml)
_KEY_ID_RE = re.compile(r'<Key\b[^>]*\bId\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
# first CSV column = key id (stringtable.csv legacy format), quoted or bare
_KEY_CSV_RE = re.compile(r'^\s*"?(STR_[A-Za-z0-9_]+)"?\s*,', re.MULTILINE | re.IGNORECASE)

_BLOCK_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)


def _strip_block_comments(text: str) -> str:
    return _BLOCK_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _match_not_in_line_comment(text: str, start: int) -> bool:
    """True if the match at `start` is not preceded by // earlier on its own line."""
    line_start = text.rfind("\n", 0, start) + 1
    prefix = text[line_start:start]
    return "//" not in prefix


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        try:
            return path.read_text(encoding="latin-1")
        except OSError:
            return ""


# --- collection ----------------------------------------------------------------

def collect_widget_names(layouts: list[Path]) -> set[str]:
    names: set[str] = set()
    for lp in layouts:
        text = _strip_block_comments(_read(lp))
        for m in _WIDGET_DECL_RE.finditer(text):
            name = m.group(2) if m.group(2) is not None else m.group(3)
            if name:
                names.add(name)
    return names


def collect_widget_refs(sources: list[Path], root: Path) -> list[dict]:
    refs: list[dict] = []
    for sp in sources:
        raw = _read(sp)
        text = _strip_block_comments(raw)
        rel = _rel(sp, root)
        for m in _FIND_ANY_RE.finditer(text):
            if not _match_not_in_line_comment(text, m.start()):
                continue
            refs.append({"name": m.group(1), "file": rel, "line": _line_of(text, m.start()), "kind": "FindAnyWidget"})
        for m in _FIND_PATH_RE.finditer(text):
            if not _match_not_in_line_comment(text, m.start()):
                continue
            leaf = m.group(1).replace("\\", "/").rstrip("/").split("/")[-1]
            if leaf:
                refs.append({"name": leaf, "file": rel, "line": _line_of(text, m.start()), "kind": "FindWidget(leaf)"})
    return refs


def collect_str_keys(stringtables: list[Path]) -> set[str]:
    keys: set[str] = set()
    for sp in stringtables:
        text = _read(sp)
        if sp.suffix.lower() == ".csv":
            for m in _KEY_CSV_RE.finditer(text):
                keys.add(m.group(1))
        else:
            for m in _KEY_ID_RE.finditer(text):
                keys.add(m.group(1))
    return keys


def collect_str_refs(sources: list[Path], root: Path) -> list[dict]:
    refs: list[dict] = []
    seen: set[tuple] = set()
    for sp in sources:
        text = _strip_block_comments(_read(sp))
        rel = _rel(sp, root)
        for m in _STR_REF_RE.finditer(text):
            key = m.group(1)
            k = (rel, _line_of(text, m.start()), key.upper())
            if k in seen:
                continue
            seen.add(k)
            refs.append({"key": key, "file": rel, "line": _line_of(text, m.start())})
    return refs


def _rel(p: Path, root: Path) -> str:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


# --- reconciliation ------------------------------------------------------------

def _suggest(target: str, universe: set[str], ci: bool = False) -> str | None:
    if not universe:
        return None
    if ci:
        lower = {u.lower(): u for u in universe}
        got = difflib.get_close_matches(target.lower(), list(lower.keys()), n=1, cutoff=0.8)
        return lower[got[0]] if got else None
    got = difflib.get_close_matches(target, list(universe), n=1, cutoff=0.8)
    return got[0] if got else None


def reconcile(root: Path) -> dict:
    layouts = sorted(root.rglob("*.layout"))
    sources = sorted(root.rglob("*.c"))
    stringtables = [p for p in root.rglob("*.xml") if p.name.lower() == "stringtable.xml"]
    stringtables += [p for p in root.rglob("*.csv") if p.name.lower() == "stringtable.csv"]

    widget_names = collect_widget_names(layouts)
    widget_refs = collect_widget_refs(sources, root)
    str_keys = collect_str_keys(stringtables)
    str_refs = collect_str_refs(sources + layouts, root)

    findings: list[dict] = []

    # Check A: FindAnyWidget -> layout (case-sensitive)
    names_ci = {n.lower(): n for n in widget_names}
    for r in widget_refs:
        name = r["name"]
        if name in widget_names:
            continue
        if name.lower() in names_ci:
            findings.append(_f("UI-FINDANYWIDGET-CASE", "FAIL", r["file"], r["line"],
                f"{r['kind']}(\"{name}\") differs only in CASE from layout widget "
                f"'{names_ci[name.lower()]}'. Widget lookup is case-sensitive at runtime -> "
                f"returns null -> crash on Cast. Fix the case."))
            continue
        sug = _suggest(name, widget_names)
        if sug:
            findings.append(_f("UI-FINDANYWIDGET-UNRESOLVED", "FAIL", r["file"], r["line"],
                f"{r['kind']}(\"{name}\") names no widget in this addon's .layout files. "
                f"Closest is '{sug}' -> likely a typo/rename (silent null -> crash on Cast)."))
        else:
            findings.append(_f("UI-FINDANYWIDGET-UNRESOLVED", "WARN", r["file"], r["line"],
                f"{r['kind']}(\"{name}\") names no widget in this addon's .layout files and has no "
                f"close match. Could be a vanilla widget or a dynamically-created one -- verify."))

    # Check B: #STR -> stringtable (case-insensitive)
    keys_ci = {k.lower() for k in str_keys}
    if str_refs and not str_keys:
        if stringtables:
            findings.append(_f("UI-STR-STRINGTABLE-EMPTY", "WARN", _rel(stringtables[0], root), 0,
                f"{len(str_refs)} #STR references found and a stringtable exists, but 0 keys were parsed "
                f"from it -- the stringtable format may be unrecognized or empty. Check {stringtables[0].name}."))
        else:
            findings.append(_f("UI-STR-NO-STRINGTABLE", "WARN", "(addon)", 0,
                f"{len(str_refs)} #STR references found but no stringtable.xml/csv exists under the addon "
                f"root. If these keys are your own, add a stringtable; if vanilla, ignore."))
    else:
        for r in str_refs:
            key = r["key"]
            if key.lower() in keys_ci:
                continue
            sug = _suggest(key, str_keys, ci=True)
            if sug:
                findings.append(_f("UI-STR-KEY-UNRESOLVED", "FAIL", r["file"], r["line"],
                    f"#{key} is not defined in this addon's stringtable. Closest is '#{sug}' -> likely a typo."))
            else:
                findings.append(_f("UI-STR-KEY-UNRESOLVED", "WARN", r["file"], r["line"],
                    f"#{key} is not in this addon's stringtable and has no close match. Could be a vanilla "
                    f"key -- verify (raw key renders in-game if undefined)."))

    return {
        "addon": str(root),
        "stats": {
            "layouts": len(layouts), "sources": len(sources), "stringtables": len(stringtables),
            "widgetNames": len(widget_names), "widgetRefs": len(widget_refs),
            "strKeys": len(str_keys), "strRefs": len(str_refs),
            "fail": sum(1 for f in findings if f["severity"] == "FAIL"),
            "warn": sum(1 for f in findings if f["severity"] == "WARN"),
        },
        "findings": findings,
    }


def _f(rule_id: str, severity: str, file: str, line: int, message: str) -> dict:
    return {"check": rule_id, "rule_id": rule_id, "severity": severity,
            "file": file, "line": line, "message": message}


# --- cli -----------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cross-file DayZ UI reconciliation (FindAnyWidget + #STR).")
    ap.add_argument("roots", nargs="+", help="addon root(s) to scan")
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    ap.add_argument("--strict", action="store_true", help="treat WARN as failure (exit 1)")
    a = ap.parse_args(argv)

    reports = []
    worst = 0  # 0 clean, 1 FAIL, 2 WARN
    for r in a.roots:
        root = Path(r)
        if not root.is_dir():
            print(f"ERROR: not a directory: {r}", file=sys.stderr)
            return 3
        rep = reconcile(root)
        reports.append(rep)
        if rep["stats"]["fail"]:
            worst = 1
        elif rep["stats"]["warn"] and worst == 0:
            worst = 2

    if a.json:
        print(json.dumps(reports if len(reports) > 1 else reports[0], indent=2, ensure_ascii=False))
    else:
        for rep in reports:
            s = rep["stats"]
            print(f"== {rep['addon']}")
            print(f"   layouts={s['layouts']} sources={s['sources']} stringtables={s['stringtables']} | "
                  f"names={s['widgetNames']} findRefs={s['widgetRefs']} keys={s['strKeys']} strRefs={s['strRefs']}")
            if not rep["findings"]:
                print("   [PASS] all FindAnyWidget names and #STR keys reconcile")
            for f in rep["findings"]:
                loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
                print(f"   [{f['severity']}] {f['check']}  {loc}\n         {f['message']}")
            print(f"   -> {s['fail']} FAIL, {s['warn']} WARN")

    if a.strict and worst == 2:
        worst = 1
    return worst


if __name__ == "__main__":
    sys.exit(main())
