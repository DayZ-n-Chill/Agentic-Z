"""dayz-upgrade-guard: see which mod classes a DayZ update affects.

  upgrade_guard.py snapshot [--label <text>]
  upgrade_guard.py check [<ModName> ...] [--mod-dir <folder>] [--label <text>] [--reindex] [--json]
  upgrade_guard.py diff [--old <snapshot> --new <snapshot>] [<ModName> ...] [--mod-dir <folder>] [--json]

A snapshot records every vanilla class on P:\\: script classes from the .c
files (parent and method signatures) and config classes from config.cpp
(parent and the names of the properties and subclasses they set). Take one
before a DayZ update. After the update, `check` takes a new snapshot, diffs it
with the newest earlier one and lists the mod classes whose vanilla parents
changed: a parent that is gone, a class higher up the chain that now extends
something else, an overridden method that is gone or has a new signature, a
config property a parent no longer sets. `--reindex` then rebuilds the search
index so the RAG answers match the new game files.

The first output line is the verdict: PASS (exit 0, no mod class affected),
FAIL (exit 1, at least one) or ERROR (exit 2: bad arguments, P:\\ not mounted,
no snapshot to diff). `snapshot` prints the saved path instead. See SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent
REPO = SKILLS_DIR.parents[1]
sys.path.insert(0, str(SKILLS_DIR / "_shared"))
import skill_helpers as h  # noqa: E402

sys.path.insert(0, str(REPO / "hooks"))
import edit_check  # noqa: E402  (the config tokenizer the edit hook and /dayz-lint use)

P_DRIVE = Path("P:\\")
STORE = Path.home() / ".claude" / "dayz-upgrade-guard"
INDEXER = SKILLS_DIR / "dayz-search-index" / "index.py"
FORMAT = 1

# Vanilla script files live under P:\scripts\ and a few DLC folders under P:\DZ\ (data_sakhal/scripts/4_World).
SCRIPT_ROOTS = ("scripts", "DZ")
CONFIG_ROOT = "DZ"


class GuardError(Exception):
    """The guard cannot run (exit 2); not a verdict on any mod."""


# --- Enforce Script -----------------------------------------------------------

CLASS_RE = re.compile(
    r"(?P<mods>(?:(?:modded|sealed)\s+)*)class\s+(?P<name>[A-Za-z_]\w*)\s*(?:<[^>{;]*>)?\s*"
    r"(?:(?:extends|:)\s*(?P<parent>[A-Za-z_]\w*)\s*(?:<[^>{;]*>)?\s*)?(?P<end>[{;])"
)
METHOD_NAME_RE = re.compile(r"(~?\s*[A-Za-z_]\w*)\s*$")
SPACE_RE = re.compile(r"\s+")
OPEN_SPACE_RE = re.compile(r"\s*([<(\[])\s*")
CLOSE_SPACE_RE = re.compile(r"\s*([>)\]])")


def clean_script(text: str) -> str:
    """Blank out comments, string contents and preprocessor lines, keeping every newline and offset."""
    out = list(text)
    i, n = 0, len(text)
    at_line_start = True

    def blank(a: int, b: int) -> None:
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        c = text[i]
        if c == "\n":
            at_line_start = True
            i += 1
            continue
        if c in " \t\r":
            i += 1
            continue
        if c == "#" and at_line_start:
            end = text.find("\n", i)
            end = n if end < 0 else end
            blank(i, end)
            i = end
            continue
        at_line_start = False
        if text.startswith("//", i):
            end = text.find("\n", i)
            end = n if end < 0 else end
            blank(i, end)
            i = end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            blank(i, end)
            i = end
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            blank(i + 1, min(j, n))
            i = j + 1
        else:
            i += 1
    return "".join(out)


def _matching_brace(text: str, start: int) -> int:
    """Index just past the '}' that closes the '{' at start (end of text if unclosed)."""
    depth = 0
    for k in range(start, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return k + 1
    return len(text)


def _strip_attributes(segment: str) -> str:
    """Drop leading [Attribute(...)] groups from a declaration."""
    segment = segment.lstrip()
    while segment.startswith("["):
        depth = 0
        for k, ch in enumerate(segment):
            depth += ch == "["
            depth -= ch == "]"
            if depth == 0:
                segment = segment[k + 1:].lstrip()
                break
        else:
            return ""
    return segment


def _split_params(params: str) -> list[str]:
    parts, depth, cur = [], 0, []
    for ch in params:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return parts


def _normalise(text: str) -> str:
    return CLOSE_SPACE_RE.sub(r"\1", OPEN_SPACE_RE.sub(r"\1", SPACE_RE.sub(" ", text).strip()))


def parse_method(segment: str) -> Optional[tuple[str, str, bool]]:
    """(name, signature, is_override) for one class body declaration, or None for a field."""
    segment = _strip_attributes(segment)
    paren = segment.find("(")
    if paren < 0 or "=" in segment[:paren]:
        return None
    m = METHOD_NAME_RE.search(segment[:paren])
    if not m:
        return None
    prefix = segment[:m.start()].split()
    if not prefix:
        return None
    depth, close = 0, -1
    for k in range(paren, len(segment)):
        depth += segment[k] == "("
        depth -= segment[k] == ")"
        if depth == 0:
            close = k
            break
    if close < 0:
        return None
    is_override = "override" in prefix
    # Defaults and the override keyword do not change what a subclass must match.
    params = ", ".join(_normalise(p.split("=", 1)[0]) for p in _split_params(segment[paren + 1:close]))
    name = m.group(1).replace(" ", "")
    head = _normalise(" ".join(w for w in prefix if w != "override"))
    return name, f"{head} {name}({params})", is_override


def class_methods(body: str) -> dict[str, tuple[str, bool]]:
    """Methods declared directly in a class body (between its braces)."""
    flat, depth, k = [], 0, 0
    while k < len(body):
        ch = body[k]
        if ch == "{":
            end = _matching_brace(body, k)
            flat.append(";")
            k = end
            continue
        flat.append(ch)
        k += 1
    methods: dict[str, tuple[str, bool]] = {}
    for segment in "".join(flat).split(";"):
        parsed = parse_method(segment)
        if parsed:
            methods[parsed[0]] = (parsed[1], parsed[2])
    return methods


def parse_script(text: str) -> list[dict]:
    """Top level class declarations in one .c file: name, parent, modded, line, methods."""
    clean = clean_script(text)
    found, depth, k, n = [], 0, 0, len(clean)
    while k < n:
        ch = clean[k]
        if ch == "{":
            k = _matching_brace(clean, k)
            continue
        if ch in "cms" and (k == 0 or not (clean[k - 1].isalnum() or clean[k - 1] == "_")):
            m = CLASS_RE.match(clean, k)
            if m:
                if m.group("end") == ";":  # forward declaration
                    k = m.end()
                    continue
                brace = m.end() - 1
                end = _matching_brace(clean, brace)
                found.append({
                    "name": m.group("name"),
                    "parent": m.group("parent"),
                    "modded": "modded" in m.group("mods").split(),
                    "line": clean.count("\n", 0, m.start()) + 1,
                    "methods": class_methods(clean[brace + 1:end - 1]),
                })
                k = end
                continue
        k += 1
    return found


# --- config.cpp ---------------------------------------------------------------

def parse_config(text: str) -> list[dict]:
    """Classes one level inside each top level Cfg class: container, name, parent, line, members.

    A forward declaration (`class Foo;`) is skipped. Members are the property
    and subclass names set directly in the class body.
    """
    toks = edit_check.tokenize(text)
    found: list[dict] = []
    stack: list[Optional[dict]] = []  # one entry per open class body; dict for a recorded class
    containers: list[str] = []
    i, n = 0, len(toks)

    def punct(k: int, value: str) -> bool:
        return k < n and toks[k].kind == "punct" and toks[k].text == value

    while i < n:
        tok = toks[i]
        if punct(i, "{"):
            stack.append(None)
            i += 1
        elif punct(i, "}"):
            if stack:
                stack.pop()
                if len(stack) == 0 and containers:
                    containers.pop()
            i += 1
        elif tok.kind == "ident" and tok.text == "class" and i + 1 < n and toks[i + 1].kind == "ident":
            name = toks[i + 1].text
            j, parent = i + 2, None
            if punct(j, ":") and j + 1 < n:
                parent = toks[j + 1].text
                j += 2
            if not punct(j, "{"):
                if len(stack) == 2 and stack[1] is not None:
                    stack[1]["members"].add(name)
                i = j + 1
                continue
            depth = len(stack)
            entry = None
            if depth == 0:
                containers.append(name)
            elif depth == 1 and containers:
                entry = {"container": containers[-1], "name": name, "parent": parent, "line": tok.line, "members": set()}
                found.append(entry)
            elif depth == 2 and stack[1] is not None:
                stack[1]["members"].add(name)
            stack.append(entry)
            i = j + 1
        elif tok.kind == "ident" and len(stack) == 2 and stack[1] is not None and (
                punct(i + 1, "=") or punct(i + 1, "+=") or (punct(i + 1, "[") and punct(i + 2, "]"))):
            stack[1]["members"].add(tok.text)
            i += 1
        else:
            i += 1
    for entry in found:
        entry["members"] = sorted(entry["members"], key=str.lower)
    return found


# --- snapshot -----------------------------------------------------------------

def _files(root: Path, pattern: str) -> Iterable[Path]:
    try:
        yield from sorted(p for p in root.rglob(pattern) if p.is_file())
    except OSError:
        return


def take_snapshot(p_root: Path, label: str = "") -> dict:
    """Read every vanilla class on p_root. Raises GuardError when there are no vanilla scripts."""
    if not (p_root / "scripts").is_dir():
        raise GuardError(f"{p_root} has no scripts folder. Mount the work drive with /dayz-workdrive and unpack the game data first.")
    script: dict[str, dict] = {}
    config: dict[str, dict] = {}
    skipped: list[str] = []
    from_modded: set[str] = set()  # entries so far seen only as `modded class`
    for top in SCRIPT_ROOTS:
        for path in _files(p_root / top, "*.c"):
            rel = path.relative_to(p_root).as_posix()
            try:
                decls = parse_script(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                skipped.append(rel)
                continue
            for d in decls:
                methods = {name: sig for name, (sig, _) in d["methods"].items()}
                entry = script.get(d["name"])
                if entry is None:
                    script[d["name"]] = {"parent": d["parent"], "file": rel, "line": d["line"], "methods": methods}
                    if d["modded"]:
                        from_modded.add(d["name"])
                    continue
                # A vanilla modded class, or the class itself after its modded part: merge.
                if not d["modded"]:
                    entry["parent"] = d["parent"]
                    if d["name"] in from_modded:
                        entry["file"], entry["line"] = rel, d["line"]
                        from_modded.discard(d["name"])
                entry["methods"].update(methods)
    for path in _files(p_root / CONFIG_ROOT, "config.cpp"):
        rel = path.relative_to(p_root).as_posix()
        try:
            decls = parse_config(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, edit_check.TokenizeError):
            skipped.append(rel)
            continue
        for d in decls:
            key = f"{d['container']}/{d['name']}"
            entry = config.get(key)
            if entry is None:
                config[key] = {"parent": d["parent"], "file": rel, "line": d["line"], "members": d["members"]}
            else:  # vanilla addons extend the same class from many config.cpp files
                if d["parent"]:
                    entry["parent"] = d["parent"]
                entry["members"] = sorted(set(entry["members"]) | set(d["members"]), key=str.lower)
    return {
        "format": FORMAT,
        "created": datetime.now().isoformat(timespec="seconds"),
        "label": label,
        "p_root": str(p_root),
        "script": dict(sorted(script.items())),
        "config": dict(sorted(config.items())),
        "skipped": skipped,
    }


def same_classes(a: dict, b: dict) -> bool:
    return a["script"] == b["script"] and a["config"] == b["config"]


def stored_snapshots(store: Path) -> list[Path]:
    """Saved snapshots, oldest first. File names sort in time order (see save_snapshot)."""
    return sorted(store.glob("*.json")) if store.is_dir() else []


def save_snapshot(snap: dict, store: Path) -> Path:
    """Save as <stamp>[_NN][-<label>].json.

    A second snapshot in the same second gets a counter right after the
    stamp. '_' sorts after both '.' and '-', so the names still sort in the
    order the snapshots were taken, whatever their labels.
    """
    store.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    label = re.sub(r"[^\w.-]+", "-", snap.get("label") or "").strip("-")
    k, head = 1, stamp
    while any(store.glob(f"{head}.json")) or any(store.glob(f"{head}-*.json")):
        k += 1
        head = f"{stamp}_{k:02d}"
    path = store / (f"{head}-{label}.json" if label else f"{head}.json")
    path.write_text(json.dumps(snap, separators=(",", ":")), encoding="utf-8")
    return path


def load_snapshot(ref: str, store: Path) -> tuple[dict, Path]:
    path = Path(ref)
    if not path.is_file():
        path = store / (ref if ref.endswith(".json") else f"{ref}.json")
    if not path.is_file():
        raise GuardError(f"No snapshot {ref} (looked in {store}).")
    try:
        snap = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise GuardError(f"Cannot read snapshot {path}: {e}") from e
    if snap.get("format") != FORMAT or "script" not in snap or "config" not in snap:
        raise GuardError(f"{path} is not an upgrade guard snapshot.")
    return snap, path


# --- diff ---------------------------------------------------------------------

def diff_snapshots(old: dict, new: dict) -> dict:
    """What changed in vanilla, per class kind: removed, added, parent, methods, members."""
    out: dict = {}
    for kind, field in (("script", "methods"), ("config", "members")):
        a, b = old[kind], new[kind]
        changes = {"removed": sorted(set(a) - set(b)), "added": sorted(set(b) - set(a)), "parent": [], field: []}
        for name in sorted(set(a) & set(b)):
            if a[name]["parent"] != b[name]["parent"]:
                changes["parent"].append({"class": name, "old": a[name]["parent"], "new": b[name]["parent"]})
            if kind == "script":
                gone = sorted(set(a[name]["methods"]) - set(b[name]["methods"]))
                changed = sorted(m for m in set(a[name]["methods"]) & set(b[name]["methods"])
                                 if a[name]["methods"][m] != b[name]["methods"][m])
                if gone or changed:
                    changes[field].append({"class": name, "removed": gone, "changed": changed})
            else:
                gone = sorted(set(a[name]["members"]) - set(b[name]["members"]), key=str.lower)
                if gone:
                    changes[field].append({"class": name, "removed": gone})
        out[kind] = changes
    return out


def diff_is_empty(diff: dict) -> bool:
    return not any(v for changes in diff.values() for v in changes.values())


def _chain(table: dict, start: str, prefix: str = "") -> list[str]:
    """start and its vanilla ancestors, nearest first. Config keys carry a 'CfgX/' prefix."""
    chain, seen, cur = [], set(), start
    while cur and prefix + cur in table and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        cur = table[prefix + cur]["parent"]
    return chain


def _find_method(table: dict, chain: list[str], method: str) -> Optional[tuple[str, str]]:
    for cls in chain:
        sig = table[cls]["methods"].get(method)
        if sig is not None:
            return cls, sig
    return None


def _chain_changes(old_t: dict, new_t: dict, start: str, prefix: str = "") -> list[dict]:
    """Reasons from start's old vanilla chain: a class removed or one that now has another parent."""
    reasons = []
    for cls in _chain(old_t, start, prefix):
        key = prefix + cls
        if key not in new_t:
            reasons.append({"reason": "parent-removed", "class": cls,
                            "message": f"vanilla {cls} no longer exists"})
            break
        if old_t[key]["parent"] != new_t[key]["parent"]:
            reasons.append({"reason": "parent-changed", "class": cls,
                            "message": f"vanilla {cls} now extends {new_t[key]['parent'] or 'nothing'} (was {old_t[key]['parent'] or 'nothing'})"})
    return reasons


def scan_mod(mod_dir: Path) -> dict:
    """Script and config classes a mod declares. Files that cannot be read are skipped."""
    scripts, configs = [], []
    for path in _files(mod_dir, "*.c"):
        if any(part.startswith(".") for part in path.relative_to(mod_dir).parts):
            continue
        try:
            for d in parse_script(path.read_text(encoding="utf-8", errors="replace")):
                scripts.append({**d, "file": path})
        except OSError:
            continue
    for path in _files(mod_dir, "config.cpp"):
        try:
            for d in parse_config(path.read_text(encoding="utf-8", errors="replace")):
                configs.append({**d, "file": path})
        except (OSError, edit_check.TokenizeError):
            continue
    return {"script": scripts, "config": configs}


def check_mod(name: str, mod_dir: Path, old: dict, new: dict, display_root: Optional[Path] = None) -> dict:
    """Mod classes whose vanilla parents changed between old and new."""
    if not mod_dir.is_dir():
        raise GuardError(f"Mod folder {mod_dir} does not exist.")
    mod = scan_mod(mod_dir)
    old_s, new_s, old_c, new_c = old["script"], new["script"], old["config"], new["config"]
    findings, checked = [], 0
    # The mod's own (not modded) classes, so a class two or more steps below vanilla
    # (MyVest extends MyVest_Base extends Clothing) is still checked against Clothing.
    own_classes = {d["name"]: d for d in mod["script"] if not d["modded"]}

    def first_vanilla(name: Optional[str]) -> Optional[str]:
        seen = set()
        while name and name not in old_s and name in own_classes and name not in seen:
            seen.add(name)
            name = own_classes[name]["parent"]
        return name

    def where(d: dict) -> str:
        path = d["file"]
        if display_root:
            try:
                path = path.relative_to(display_root)
            except ValueError:
                pass
        return f"{Path(path).as_posix()}:{d['line']}"

    for d in mod["script"]:
        # modded class X depends on X itself; class Y extends X depends on X.
        start = first_vanilla(d["name"] if d["modded"] else d["parent"])
        if not start or start not in old_s:
            continue
        checked += 1
        reasons = _chain_changes(old_s, new_s, start)
        old_chain, new_chain = _chain(old_s, start), _chain(new_s, start)
        for method, (_, is_override) in sorted(d["methods"].items()):
            if not is_override:
                continue
            was = _find_method(old_s, old_chain, method)
            if was is None:
                continue
            now = _find_method(new_s, new_chain, method)
            if now is None:
                reasons.append({"reason": "override-removed", "class": was[0], "method": method,
                                "message": f"{method} is overridden but vanilla {was[0]} no longer has it"})
            elif now[1] != was[1]:
                reasons.append({"reason": "override-changed", "class": now[0], "method": method,
                                "message": f"vanilla {now[0]}.{method} is now `{now[1]}` (was `{was[1]}`)"})
        if reasons:
            findings.append({"kind": "script", "class": d["name"], "modded": d["modded"], "vanilla": start,
                             "where": where(d), "reasons": reasons})

    for d in mod["config"]:
        prefix = d["container"] + "/"
        reasons, start = [], d["parent"]
        if d["parent"] is None and prefix + d["name"] in old_c:
            start = d["name"]  # the mod adds to a vanilla class without restating its parent
        own = prefix + d["name"]
        if d["parent"] and own in old_c and own in new_c and new_c[own]["parent"] != d["parent"] \
                and old_c[own]["parent"] != new_c[own]["parent"]:
            reasons.append({"reason": "redeclared-parent", "class": d["name"],
                            "message": f"the mod declares {d['name']} with parent {d['parent']} but vanilla now gives it {new_c[own]['parent'] or 'none'}"})
        on_vanilla = bool(start) and prefix + start in old_c
        if not on_vanilla and not reasons:
            continue
        if on_vanilla:
            reasons += _chain_changes(old_c, new_c, start, prefix)
            for cls in _chain(old_c, start, prefix):
                key = prefix + cls
                if key in new_c:
                    gone = sorted(set(old_c[key]["members"]) - set(new_c[key]["members"]), key=str.lower)
                    if gone:
                        reasons.append({"reason": "members-removed", "class": cls, "members": gone,
                                        "message": f"vanilla {cls} no longer sets {', '.join(gone)}"})
        checked += 1
        if reasons:
            findings.append({"kind": "config", "class": f"{d['container']}/{d['name']}", "modded": False,
                             "vanilla": start, "where": where(d), "reasons": reasons})
    return {"mod": name, "mod_dir": str(mod_dir), "classes_checked": checked, "findings": findings}


def build_report(old: dict, new: dict, old_path: Path, new_path: Path, mods: list[tuple[str, Path]],
                 display_root: Optional[Path] = None) -> dict:
    diff = diff_snapshots(old, new)
    results = [check_mod(name, path, old, new, display_root) for name, path in mods]
    affected = sum(len(r["findings"]) for r in results)
    return {
        "verdict": "FAIL" if affected else "PASS",
        "old": str(old_path), "new": str(new_path),
        "vanilla_changed": not diff_is_empty(diff),
        "affected": affected,
        "diff": diff,
        "mods": results,
    }


def render_text(report: dict) -> str:
    diff = report["diff"]
    lines = [f"  old: {report['old']}", f"  new: {report['new']}"]
    s, c = diff["script"], diff["config"]
    if not report["vanilla_changed"]:
        lines.append("  Vanilla classes did not change.")
    else:
        lines.append(
            f"  Vanilla: script classes {len(s['added'])} added, {len(s['removed'])} removed, "
            f"{len(s['parent'])} new parents, {len(s['methods'])} with removed or changed methods; "
            f"config classes {len(c['added'])} added, {len(c['removed'])} removed, "
            f"{len(c['parent'])} new parents, {len(c['members'])} with removed members.")
        for kind, changes in (("script", s), ("config", c)):
            for p in changes["parent"]:
                lines.append(f"    {kind} {p['class']} now extends {p['new'] or 'nothing'} (was {p['old'] or 'nothing'})")
            for name in changes["removed"]:
                lines.append(f"    {kind} {name} removed")
    if not report["mods"]:
        lines.append("  No mods checked. Name one, pass --mod-dir, or run /dayz-init so workspace mods are found.")
    for r in report["mods"]:
        lines.append(f"  {r['mod']}: {r['classes_checked']} class(es) built on vanilla, {len(r['findings'])} affected")
        for f in r["findings"]:
            what = f"modded class {f['class']}" if f["modded"] else f"{f['class']} (from {f['vanilla']})"
            lines.append(f"  - {f['where']}  {what}")
            for reason in f["reasons"]:
                lines.append(f"      {reason['reason']}: {reason['message']}")
    if report["affected"]:
        lines.append("  Owners: script findings go to dayz-script-specialist, config findings to dayz-config-specialist.")
    return "\n".join(lines)


# --- mods and CLI -------------------------------------------------------------

def resolve_mods(names: list[str], mod_dirs: list[Path]) -> tuple[list[tuple[str, Path]], Optional[Path]]:
    """Named mods under the cached project's workspace/, plus any --mod-dir folders.

    With neither, every mod folder in workspace/ when a project is cached, else none.
    """
    mods = [(p.absolute().name, p.absolute()) for p in mod_dirs]
    if names or not mod_dirs:
        try:
            project = h.resolve_project_dir() if names else _cached_project()
        except SystemExit as e:  # resolve_project_dir printed why on stderr
            raise GuardError("no usable project: run /dayz-init, or pass --mod-dir") from e
        if project is None:
            return mods, None
        workspace = project / "workspace"
        if names:
            mods += [(n, workspace / n) for n in names]
        elif workspace.is_dir():
            mods += [(p.name, p) for p in sorted(workspace.iterdir()) if p.is_dir() and not p.name.startswith(".")]
        return mods, project
    return mods, None


def _cached_project() -> Optional[Path]:
    state = h.load_module("dayz_upgrade_guard_state", SKILLS_DIR / "dayz-init" / "state.py")
    project = state.cached_project_root()
    return project.resolve() if project is not None and project.is_dir() else None


def run_reindex() -> int:
    """Rebuild the vanilla search index (dayz-search-index --full). Returns its exit code."""
    print(f"  Rebuilding the search index: {INDEXER} --full")
    sys.stdout.flush()
    return subprocess.run([sys.executable, str(INDEXER), "--full"]).returncode


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Snapshot vanilla DayZ classes and list mod classes a game update affects.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--store", type=Path, default=STORE, help=f"Snapshot folder (default {STORE}).")
    common.add_argument("--p-root", type=Path, default=P_DRIVE, help="Vanilla game data root (default P:\\).")
    sub = parser.add_subparsers(dest="command", required=True)
    snap_p = sub.add_parser("snapshot", parents=[common], help="Save a snapshot of the vanilla classes on P:\\.")
    snap_p.add_argument("--label", default="", help="Text added to the file name, for example the game version.")
    for name, text in (("check", "Snapshot now, diff with the newest earlier snapshot and check mods."),
                       ("diff", "Diff two saved snapshots (default: the two newest) and check mods.")):
        p = sub.add_parser(name, parents=[common], help=text)
        if name == "diff":
            p.add_argument("--old", help="Older snapshot: a file or a name in the store.")
            p.add_argument("--new", help="Newer snapshot: a file or a name in the store.")
        p.add_argument("mods", nargs="*", help="Mod names under workspace/ (default: every mod there).")
        p.add_argument("--mod-dir", type=Path, action="append", default=[], help="Check this folder too. Repeatable.")
        p.add_argument("--json", action="store_true", help="Print the report as JSON after the verdict line.")
        if name == "check":
            p.add_argument("--label", default="", help="Text added to the new snapshot's file name.")
            p.add_argument("--reindex", action="store_true", help="Rebuild the search index when vanilla changed.")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    as_json = getattr(args, "json", False)

    try:
        if args.command == "snapshot":
            path = save_snapshot(take_snapshot(args.p_root, args.label), args.store)
            snap = json.loads(path.read_text(encoding="utf-8"))
            print(f"Snapshot saved: {path}")
            print(f"  {len(snap['script'])} script classes, {len(snap['config'])} config classes, {len(snap['skipped'])} file(s) skipped")
            return 0

        mods, project = resolve_mods(args.mods, args.mod_dir)
        # Before any snapshot is saved, so a mistyped mod name never leaves a new snapshot behind.
        for _, mod_dir in mods:
            if not mod_dir.is_dir():
                raise GuardError(f"Mod folder {mod_dir} does not exist.")
        if args.command == "diff":
            saved = stored_snapshots(args.store)
            if args.old and args.new:
                old, old_path = load_snapshot(args.old, args.store)
                new, new_path = load_snapshot(args.new, args.store)
            elif args.old or args.new:
                raise GuardError("give both --old and --new, or neither for the two newest snapshots")
            elif len(saved) < 2:
                raise GuardError(f"need two snapshots in {args.store}; take one before and one after the update")
            else:
                old, old_path = load_snapshot(str(saved[-2]), args.store)
                new, new_path = load_snapshot(str(saved[-1]), args.store)
        else:
            saved = stored_snapshots(args.store)
            new = take_snapshot(args.p_root, args.label)
            if not saved:
                path = save_snapshot(new, args.store)
                print("PASS")
                if as_json:
                    print(json.dumps({"verdict": "PASS", "baseline": str(path)}, indent=2))
                else:
                    print(f"  No earlier snapshot, so this one is the baseline: {path}")
                    print("  Run check again after the next DayZ update.")
                return 0
            old, old_path = load_snapshot(str(saved[-1]), args.store)
            if same_classes(old, new):
                new_path = old_path  # nothing changed; keep the baseline instead of a copy
            else:
                new_path = save_snapshot(new, args.store)
        report = build_report(old, new, old_path, new_path, mods, project or Path.cwd())
    except GuardError as e:
        print("ERROR")
        print(json.dumps({"verdict": "ERROR", "error": str(e)}, indent=2) if as_json else f"  {e}")
        return 2

    print(report["verdict"])
    print(json.dumps(report, indent=2) if as_json else render_text(report))
    if args.command == "check" and report["vanilla_changed"]:
        if args.reindex:
            code = run_reindex()
            if code != 0:
                print(f"  The search index rebuild exited with {code}; the old index is still in place.")
        else:
            print("  Vanilla changed: rebuild the search index with check --reindex or /dayz-search-index --full.")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
