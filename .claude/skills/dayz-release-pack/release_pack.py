"""dayz-release-pack: write the release texts for a mod in one go.

  release_pack.py <ModName> [--version 1.2.0] [--since <git ref>] [--deps CF ...] [--out <folder>] [--json]
  release_pack.py --mod-dir <folder> [same options]

Reads workspace/<ModName>/ and writes four files to output/<ModName>-release/:

  workshop-description.txt  Steam Workshop text in Steam's BBCode
  changelog.md              one changelog entry built from the git history of the mod folder
  classnames.md             every spawnable class in config.cpp, for types.xml
  server-install.md         install steps for server owners

Every fact comes from the mod's files: classes and their scope from config.cpp,
dependencies from CfgPatches requiredAddons, the title and summary from mod.cpp
or README.md, keys from Keys/*.bikey, the changes from git. Anything the script
cannot know (a summary, which Workshop mod ships a dependency) becomes a warning
for the AI or the user to settle. /dayz-server-kit reuses mod_facts().

Exit codes: 0 written (warnings allowed), 2 error (bad arguments, no project,
no mod folder, config.cpp that does not parse).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent
REPO = SKILLS_DIR.parents[1]
sys.path.insert(0, str(SKILLS_DIR / "_shared"))
import skill_helpers as h  # noqa: E402

sys.path.insert(0, str(REPO / "hooks"))
import edit_check  # noqa: E402

lint = h.load_module("dayz_release_pack_lint", SKILLS_DIR / "dayz-lint" / "lint.py")

# The config sections whose classes a server owner lists in types.xml.
ITEM_SECTIONS = ("CfgVehicles", "CfgWeapons", "CfgMagazines")
# Named scope values some configs use instead of the number.
SCOPE_WORDS = {"private": 0, "protected": 1, "public": 2}
P_MODS = Path("P:\\Mods")

# Conventional commit types and the changelog heading each one goes under.
CHANGE_GROUPS = (("Added", ("feat",)), ("Fixed", ("fix",)))
OTHER_GROUP = "Changed"
CONVENTIONAL_RE = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]*\))?!?:\s*(?P<rest>.+)$")
# Release bookkeeping commits say nothing a player needs.
SKIP_SUBJECT_RE = re.compile(r"^(?:chore\(release\)|Merge )", re.IGNORECASE)
RELEASE_SUBJECT_RE = re.compile(r"^chore\(release\)", re.IGNORECASE)


class ReleaseError(Exception):
    """The pack cannot be written (exit 2)."""


# --- facts from the mod's files -----------------------------------------------

def _scope(value: str) -> Optional[int]:
    value = value.strip().lower()
    if value in SCOPE_WORDS:
        return SCOPE_WORDS[value]
    return int(value) if re.fullmatch(r"-?\d+", value) else None


def _prop(node, name: str) -> Optional[str]:
    prop = node.props.get(name.lower())
    if not prop or prop[2] or not prop[3]:
        return None
    return prop[3][0][0]


def read_config(cfg: Path) -> object:
    text = cfg.read_text(encoding="utf-8", errors="replace")
    problems = edit_check.check_config(text)
    if problems:
        first = problems[0]
        raise ReleaseError(f"{cfg}:{first.line}: {first.message} Run /dayz-lint and fix the config first.")
    return lint.parse_tree(edit_check.tokenize(text))


def item_classes(tree) -> list[dict]:
    """Every class in the item sections with its scope worked out through its parents in this file.

    scope is None when the class and its parents in this file never set one, so
    the value comes from a vanilla or other mod's parent the script does not read.
    """
    nodes: dict[str, object] = {}
    rows = []
    for section in ITEM_SECTIONS:
        block = tree.child(section)
        if block is None:
            continue
        for node in block.classes:
            nodes.setdefault(node.name.lower(), node)
            rows.append((section, node))

    def effective(node, seen: set) -> tuple[Optional[int], Optional[str]]:
        raw = _prop(node, "scope")
        if raw is not None:
            return _scope(raw), node.name
        parent = nodes.get((node.parent or "").lower())
        if parent is None or parent.name.lower() in seen:
            return None, node.parent
        seen.add(parent.name.lower())
        return effective(parent, seen)

    out = []
    for section, node in rows:
        scope, source = effective(node, {node.name.lower()})
        out.append({
            "name": node.name,
            "section": section,
            "parent": node.parent,
            "scope": scope,
            "scope_from": source,
            "display_name": _prop(node, "displayName"),
            "line": node.line,
        })
    return out


def required_addons(tree) -> list[str]:
    patches = tree.child("CfgPatches")
    out: list[str] = []
    for patch in patches.classes if patches else []:
        prop = patch.props.get("requiredaddons")
        for value, _ in prop[3] if prop else []:
            if value not in out:
                out.append(value)
    return out


def patch_classes(tree) -> list[str]:
    patches = tree.child("CfgPatches")
    return [p.name for p in patches.classes] if patches else []


def mod_cpp(mod_dir: Path) -> dict[str, str]:
    """name, overview and author from mod.cpp, when the mod has one."""
    path = mod_dir / "mod.cpp"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    out = {}
    for key in ("name", "overview", "author"):
        m = re.search(rf'(?im)^\s*{key}\s*=\s*"((?:[^"]|"")*)"\s*;', text)
        if m and m.group(1).strip():
            out[key] = m.group(1).replace('""', '"').strip()
    return out


def readme_summary(mod_dir: Path) -> Optional[str]:
    """The first paragraph of README.md that is not a heading, badge or list."""
    path = mod_dir / "README.md"
    if not path.is_file():
        return None
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8", errors="replace")):
        lines = [line.strip() for line in block.strip().splitlines()]
        if not lines or lines[0].startswith(("#", "!", "|", "-", "*", "<", "```", ">")):
            continue
        return " ".join(lines)
    return None


def find_keys(mod: str, mod_dir: Path, p_mods: Optional[Path]) -> dict[str, list[Path]]:
    """Public .bikey files, and any .biprivatekey sitting where keys are looked for."""
    folders = [mod_dir / "Keys", mod_dir / "keys"]
    if p_mods is not None:
        folders.append(p_mods / f"@{mod}" / "Keys")
    public: dict[str, Path] = {}
    private: list[Path] = []
    seen: set[str] = set()
    for folder in folders:
        try:
            if not folder.is_dir() or str(folder.resolve()).lower() in seen:
                continue
            seen.add(str(folder.resolve()).lower())
            files = sorted(folder.iterdir())
        except OSError:
            continue
        for f in files:
            suffix = f.suffix.lower()
            if suffix == ".bikey":
                public.setdefault(f.name.lower(), f)
            elif suffix == ".biprivatekey":
                private.append(f)
    for f in mod_dir.rglob("*.biprivatekey"):
        if f not in private:
            private.append(f)
    return {"public": list(public.values()), "private": private}


def mod_facts(mod: str, mod_dir: Path, deps: Optional[list[str]] = None, p_mods: Optional[Path] = P_MODS) -> dict:
    """Everything the release texts and the server kit are built from."""
    if not mod_dir.is_dir():
        raise ReleaseError(f"{mod_dir} not found")
    cfg = mod_dir / "config.cpp"
    if not cfg.is_file():
        raise ReleaseError(f"{cfg} not found: the classname list and dependencies come from config.cpp")
    tree = read_config(cfg)
    classes = item_classes(tree)
    required = required_addons(tree)
    meta = mod_cpp(mod_dir)
    summary = meta.get("overview") or readme_summary(mod_dir)
    non_vanilla = [a for a in required if not a.upper().startswith("DZ_")]
    deps = [d.lstrip("@") for d in deps or []]
    keys = find_keys(mod, mod_dir, p_mods)
    warnings = []
    if not summary:
        warnings.append("summary-missing: no overview in mod.cpp and no first paragraph in README.md, "
                        "so the Workshop text has a placeholder line to replace")
    if non_vanilla and not deps:
        warnings.append(f"deps-unmapped: config.cpp requires non-vanilla addons {non_vanilla}. "
                        "Map each to the Workshop mod that ships it and rerun with --deps in load order, for example --deps CF")
    unresolved = [c["name"] for c in classes if c["scope"] is None]
    if unresolved:
        warnings.append(f"scope-unknown: {unresolved} set no scope here and take it from a parent outside this mod; "
                        "check each and list the spawnable ones by hand")
    if not keys["public"]:
        warnings.append("no-bikey: no .bikey in Keys/ or the deployed @mod Keys folder; sign the PBO before release "
                        "so servers with verifySignatures can load it")
    if keys["private"]:
        warnings.append(f"private-key-in-mod: {[str(p) for p in keys['private']]} is a private key. It is never packed; "
                        "move it out of the mod folder so it can never ship")
    return {
        "mod": mod,
        "mod_dir": str(mod_dir),
        "title": meta.get("name") or mod,
        "author": meta.get("author"),
        "summary": summary,
        "patches": patch_classes(tree),
        "required_addons": required,
        "non_vanilla_addons": non_vanilla,
        "deps": deps,
        "classes": classes,
        "spawnable": [c for c in classes if c["scope"] == 2],
        "unresolved": [c for c in classes if c["scope"] is None],
        "keys": [str(p) for p in keys["public"]],
        "private_keys": [str(p) for p in keys["private"]],
        "warnings": warnings,
    }


def load_order(facts: dict) -> list[str]:
    return [f"@{d}" for d in facts["deps"]] + [f"@{facts['mod']}"]


# --- changelog from git -------------------------------------------------------

def _git(mod_dir: Path, *args: str) -> Optional[str]:
    try:
        r = subprocess.run(["git", "-C", str(mod_dir), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def git_changes(mod_dir: Path, since: Optional[str]) -> dict:
    """Commits that touched the mod folder since `since`.

    The default is the latest tag when the mod folder is its own repository. A mod
    inside a bigger repository (an Agentic-Z clone) cannot use that repository's
    tags, so it starts after the newest chore(release) commit that touched the mod
    folder, or takes the whole folder history when there is none.
    `from` says where the start came from: "option", "tag", "release-commit" or None.
    """
    top = _git(mod_dir, "rev-parse", "--show-toplevel")
    if top is None:
        return {"git": False, "since": None, "from": None, "commits": []}
    own_repo = Path(top.strip()).resolve() == mod_dir.resolve()
    origin = None
    if since is None and own_repo:
        tag = _git(mod_dir, "describe", "--tags", "--abbrev=0")
        since = tag.strip() if tag and tag.strip() else None
        origin = "tag" if since else None
    elif since is None:
        log = _git(mod_dir, "log", "--no-merges", "--format=%h%x1f%s", "--", ".") or ""
        since = next((ref for ref, _, s in (line.partition("\x1f") for line in log.splitlines())
                      if RELEASE_SUBJECT_RE.match(s)), None)
        origin = "release-commit" if since else None
    elif _git(mod_dir, "rev-parse", "--verify", "--quiet", f"{since}^{{commit}}") is None:
        raise ReleaseError(f"--since {since!r} is not a commit or tag in the git history of {mod_dir}")
    else:
        origin = "option"
    args = ["log", "--no-merges", "--format=%h%x1f%as%x1f%s"]
    if since:
        args.append(f"{since}..HEAD")
    out = _git(mod_dir, *args, "--", ".")
    commits = []
    for line in (out or "").splitlines():
        parts = line.split("\x1f")
        if len(parts) == 3 and not SKIP_SUBJECT_RE.match(parts[2]):
            commits.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
    return {"git": True, "since": since, "from": origin, "commits": commits, "own_repo": own_repo}


def group_changes(commits: list[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {name: [] for name, _ in CHANGE_GROUPS}
    groups[OTHER_GROUP] = []
    for c in commits:
        m = CONVENTIONAL_RE.match(c["subject"])
        kind, text = (m.group("type"), m.group("rest")) if m else ("", c["subject"])
        text = text[:1].upper() + text[1:]
        name = next((g for g, types in CHANGE_GROUPS if kind in types), OTHER_GROUP)
        groups[name].append(text)
    return {k: v for k, v in groups.items() if v}


# --- the four texts -----------------------------------------------------------

SUMMARY_PLACEHOLDER = "Write one or two sentences here on what the mod adds."


def _label(c: dict) -> str:
    name = c["display_name"]
    if name and not name.startswith("$"):
        return f"{name} ({c['name']})"
    return c["name"]


def workshop_text(facts: dict, version: str, groups: dict[str, list[str]], since: Optional[str] = None) -> str:
    out = [f"[h1]{facts['title']}[/h1]", "", facts["summary"] or SUMMARY_PLACEHOLDER, ""]
    if facts["spawnable"]:
        out += ["[h2]What it adds[/h2]", "[list]"]
        out += [f"[*]{_label(c)}" for c in facts["spawnable"]]
        out += ["[/list]", ""]
    out.append("[h2]Requirements[/h2]")
    if facts["deps"]:
        out += ["Load these mods before this one:", "[list]"] + [f"[*]@{d}" for d in facts["deps"]] + ["[/list]"]
    elif facts["non_vanilla_addons"]:
        out.append("This mod needs: " + ", ".join(facts["non_vanilla_addons"]) + ".")
    else:
        out.append("No other mods are needed.")
    out += [
        "",
        "[h2]Server owners[/h2]",
        "Copy the key from the mod's Keys folder into your server's keys folder. "
        "The server kit has the types.xml entries, the cfgeconomycore.xml lines and the load order.",
        "",
        "[h2]Changes[/h2]" if version == "Unreleased" else f"[h2]Changes in {version}[/h2]",
    ]
    lines = [item for items in groups.values() for item in items]
    if lines:
        out += ["[list]"] + [f"[*]{line}" for line in lines] + ["[/list]"]
    elif since:
        out.append(f"No changes since {since}.")
    else:
        out.append("First release.")
    return "\n".join(out) + "\n"


def changelog_entry(facts: dict, version: str, date: str, changes: dict, groups: dict[str, list[str]]) -> str:
    out = [f"## {version} ({date})", ""]
    if not changes["git"]:
        out += ["No git history was found for this mod folder. Write the changes by hand.", ""]
    elif not groups:
        since = f" since {changes['since']}" if changes["since"] else ""
        out += [f"No commits touched the mod folder{since}.", ""]
    for name, items in groups.items():
        out += [f"### {name}", ""] + [f"- {item}" for item in items] + [""]
    return "\n".join(out)


def classnames_md(facts: dict) -> str:
    out = [f"# {facts['mod']} classnames", ""]
    if facts["spawnable"]:
        out += [
            "Every class with `scope = 2` in `config.cpp`. Each one needs a `types.xml` entry to spawn as loot.",
            "",
            "| Classname | Section | Parent | Display name |",
            "|---|---|---|---|",
        ]
        for c in facts["spawnable"]:
            out.append(f"| `{c['name']}` | {c['section']} | {c['parent'] or ''} | {c['display_name'] or ''} |")
        out.append("")
    else:
        out += ["`config.cpp` declares no class with `scope = 2`, so there is nothing to add to `types.xml`.", ""]
    if facts["unresolved"]:
        out += [
            "## Check by hand",
            "",
            "These classes set no scope here and take it from a parent outside this mod.",
            "",
        ]
        out += [f"- `{c['name']}` (parent `{c['parent']}`)" for c in facts["unresolved"]]
        out.append("")
    return "\n".join(out)


def install_md(facts: dict) -> str:
    mod = facts["mod"]
    order = ";".join(load_order(facts))
    keys = [Path(k).name for k in facts["keys"]]
    out = [f"# Installing {mod} on a server", ""]
    out.append(f"1. Copy the `@{mod}` folder into your server folder, next to `DayZServer_x64.exe`.")
    if keys:
        out.append(f"2. Copy {', '.join(f'`{k}`' for k in keys)} from `@{mod}\\Keys\\` into the server's `keys\\` folder.")
    else:
        out.append(f"2. Copy the `.bikey` from `@{mod}\\Keys\\` into the server's `keys\\` folder.")
    out.append(f"3. Add the mod to the launch line in this order: `-mod={order}`.")
    if facts["non_vanilla_addons"] and not facts["deps"]:
        out.append(f"   The mod also needs the mods that ship {', '.join(facts['non_vanilla_addons'])}. Load them first.")
    if facts["spawnable"]:
        out.append(f"4. Copy the `{mod}_ce` folder from the server kit into your mission folder, and add the lines "
                   "from `cfgeconomycore-lines.xml` inside `<economycore>` in the mission's `cfgeconomycore.xml`.")
        out.append("   Tune the `types.xml` values before you go live. Entries marked as placeholders do not spawn yet.")
        out.append("5. Restart the server.")
    else:
        out.append("4. Restart the server. The mod has no loot entries to add.")
    out.append("")
    if facts["spawnable"]:
        out += ["## Classnames", ""] + [f"- `{c['name']}`" for c in facts["spawnable"]] + [""]
    return "\n".join(out)


# --- run ----------------------------------------------------------------------

def release_pack(mod: str, mod_dir: Path, out_dir: Path, version: str = "Unreleased", since: Optional[str] = None,
                 deps: Optional[list[str]] = None, p_mods: Optional[Path] = P_MODS, date: Optional[str] = None) -> dict:
    facts = mod_facts(mod, mod_dir, deps, p_mods)
    changes = git_changes(mod_dir, since)
    if not changes["git"]:
        facts["warnings"].append("no-git: the mod folder is not in a git repository, so the changelog entry is empty")
    else:
        if changes["since"] is None and not changes["own_repo"]:
            facts["warnings"].append("changelog-full-history: no chore(release) commit touched the mod folder, so the "
                                     "entry lists its whole history; pass --since <ref> to limit the entry")
        if not changes["commits"]:
            since_text = f" since {changes['since']}" if changes["since"] else ""
            facts["warnings"].append(f"changelog-empty: no commits touched the mod folder{since_text}, "
                                     "so the changelog entry lists no changes")
    groups = group_changes(changes["commits"])
    if date is None:
        import datetime as _dt
        date = _dt.date.today().isoformat()
    files = {
        "workshop-description.txt": workshop_text(facts, version, groups, changes["since"]),
        "changelog.md": changelog_entry(facts, version, date, changes, groups),
        "classnames.md": classnames_md(facts),
        "server-install.md": install_md(facts),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    return {
        "mod": mod,
        "version": version,
        "out": str(out_dir),
        "files": sorted(files),
        "spawnable": [c["name"] for c in facts["spawnable"]],
        "unresolved": [c["name"] for c in facts["unresolved"]],
        "load_order": load_order(facts),
        "keys": facts["keys"],
        "changes": {"since": changes["since"], "from": changes["from"], "commits": len(changes["commits"])},
        "warnings": facts["warnings"],
    }


def resolve_mod(mod: Optional[str], mod_dir: Optional[Path], out: Optional[Path]) -> tuple[str, Path, Path]:
    """(mod name, mod folder, output folder) from <ModName> or --mod-dir."""
    if mod_dir:
        mod_dir = mod_dir.resolve()
        name = mod or mod_dir.name
        base = Path.cwd()
    else:
        try:
            base = h.resolve_project_dir()
        except SystemExit as e:  # resolve_project_dir printed why on stderr
            raise ReleaseError("no usable project: run /dayz-init, or pass --mod-dir") from e
        name, mod_dir = mod, base / "workspace" / mod
    return name, mod_dir, (out.resolve() if out else base / "output" / f"{name}-release")


def render_text(report: dict) -> str:
    out = [f"[OK]   Wrote {len(report['files'])} files to {report['out']}"]
    out += [f"       {name}" for name in report["files"]]
    out.append(f"       {len(report['spawnable'])} spawnable classes, {report['changes']['commits']} commits, "
               f"load order {';'.join(report['load_order'])}")
    if report["changes"]["from"] == "release-commit":
        out.append(f"       changelog starts after {report['changes']['since']}, "
                   "the newest chore(release) commit in the mod folder")
    out += [f"[WARN] {w}" for w in report["warnings"]]
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Write the Workshop text, changelog, classname list and install notes for a mod.")
    parser.add_argument("mod", nargs="?", help="Mod name under workspace/ in the project cached by /dayz-init.")
    parser.add_argument("--mod-dir", type=Path, help="Use this folder instead (its name is the mod name).")
    parser.add_argument("--version", default="Unreleased", help="Version for the changelog and Workshop text.")
    parser.add_argument("--since", help="Git ref the changelog starts after. Default: the latest tag in the mod's own "
                        "repository, else the newest chore(release) commit in the mod folder, else all history.")
    parser.add_argument("--deps", nargs="+", default=[], metavar="MOD", help="Dependency mods in load order (CF or @CF).")
    parser.add_argument("--out", type=Path, help="Output folder. Default output/<ModName>-release/.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON.")
    try:
        args = parser.parse_args(argv)
        if not args.mod and not args.mod_dir:
            parser.error("give a <ModName> or --mod-dir")
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    try:
        mod, mod_dir, out_dir = resolve_mod(args.mod, args.mod_dir, args.out)
        report = release_pack(mod, mod_dir, out_dir, args.version, args.since, args.deps)
    except (ReleaseError, OSError, ValueError) as e:
        print(json.dumps({"error": str(e)}, indent=2) if args.json else f"[FAIL] {e}")
        return 2
    print(json.dumps(report, indent=2) if args.json else render_text(report))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
