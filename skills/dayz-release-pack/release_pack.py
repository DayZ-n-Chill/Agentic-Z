"""dayz-release-pack: write the release texts for a mod in one go.

  release_pack.py <ModName> [--version 1.2.0] [--since <git ref>] [--deps CF ...] [--out <folder>] [--json]
  release_pack.py --mod-dir <folder> [same options]

Reads workspace/<ModName>/ and writes four files to output/<ModName>-release/
(the project's output/ for <ModName>, this repository's output/ for --mod-dir):

  workshop-description.txt  Steam Workshop text in Steam's BBCode
  changelog.md              one changelog entry built from the git history of the mod folder
  classnames.md             every spawnable class in the mod's config.cpp files, for types.xml
  server-install.md         install steps for server owners

Every fact comes from the mod's files: classes and their scope from every
config.cpp under the mod (the root one and sub-folders such as data/, not
Addons/, Keys/ or dot folders), dependencies from CfgPatches requiredAddons
less the mod's own patch classes, the title and summary from mod.cpp
or README.md, keys from Keys/*.bikey, the changes from git. Anything the script
cannot know (a summary, which Workshop mod ships a dependency) becomes a warning
for the AI or the user to settle. /dayz-server-kit reuses mod_facts().

It also writes .release-pack.json there, the hash of each text it wrote, so a
rerun backs up only the files someone edited by hand.

Exit codes: 0 written (warnings allowed), 2 error (bad arguments, no project,
no mod folder, no config.cpp, a config.cpp that does not parse, a --since ref
that is not in the history, an output folder inside the mod folder).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent
REPO = SKILLS_DIR.parent
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
# A commit marked breaking ("feat!:" or a BREAKING CHANGE footer) goes under this
# heading, whatever its type, so server owners see it before they update.
BREAKING_GROUP = "Breaking changes"
# Work a player never sees. It stays in changelog.md under this heading and is
# left out of the Workshop "Changes" list.
INTERNAL_TYPES = ("docs", "test", "ci", "build", "style", "refactor", "chore")
INTERNAL_GROUP = "Internal"
GROUP_ORDER = (BREAKING_GROUP, "Added", "Fixed", OTHER_GROUP, INTERNAL_GROUP)
CONVENTIONAL_RE = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]*\))?(?P<bang>!?):\s*(?P<rest>.+)$", re.IGNORECASE)
BREAKING_FOOTER_RE = re.compile(r"(?m)^BREAKING[ -]CHANGE:")
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


# Folders that never hold the mod's source config: built PBOs, signing keys, git
# data and other dot folders (.vscode, .idea).
SKIP_DIRS = {"addons", "keys"}


def config_files(mod_dir: Path) -> list[Path]:
    """Every config.cpp in the mod source, the root one first, then by path.

    Imported mods often keep CfgPatches at the root and the items in a sub-folder
    such as data/config.cpp, and each one packs into the same PBO.
    """
    found = []
    for path in mod_dir.rglob("config.cpp"):
        rel = path.relative_to(mod_dir).parts[:-1]
        if any(p.startswith(".") or p.lower() in SKIP_DIRS for p in rel) or not path.is_file():
            continue
        found.append(path)
    return sorted(found, key=lambda p: (len(p.relative_to(mod_dir).parts) > 1, p.relative_to(mod_dir).as_posix().lower()))


def item_classes(trees: list[tuple[str, object]]) -> tuple[list[dict], list[str]]:
    """Every class in the item sections with its scope worked out through its parents in the mod's configs.

    trees is (config path relative to the mod, parsed tree) per config.cpp. scope
    is None when the class and its parents in the mod never set one, so the value
    comes from a vanilla or other mod's parent the script does not read. A class
    defined in more than one config.cpp is listed once, from the first file, and
    its name is returned in the second list.
    """
    nodes: dict[str, object] = {}
    rows = []
    duplicates: list[str] = []
    for rel, tree in trees:
        for section in ITEM_SECTIONS:
            block = tree.child(section)
            if block is None:
                continue
            for node in block.classes:
                key = node.name.lower()
                if key in nodes:
                    if node.name not in duplicates:
                        duplicates.append(node.name)
                    continue
                nodes[key] = node
                rows.append((section, rel, node))

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
    for section, rel, node in rows:
        scope, source = effective(node, {node.name.lower()})
        out.append({
            "name": node.name,
            "section": section,
            "parent": node.parent,
            "scope": scope,
            "scope_from": source,
            "display_name": _prop(node, "displayName"),
            "config": rel,
            "line": node.line,
        })
    return out, duplicates


def patch_classes(trees: list[tuple[str, object]]) -> list[str]:
    out: list[str] = []
    for _, tree in trees:
        patches = tree.child("CfgPatches")
        out += [p.name for p in patches.classes if p.name not in out] if patches else []
    return out


def required_addons(trees: list[tuple[str, object]]) -> list[str]:
    """requiredAddons of every CfgPatches class, without the mod's own patch classes.

    A sub-folder config.cpp usually requires the root one's patch class, which
    is part of this mod and not a dependency.
    """
    own = {p.lower() for p in patch_classes(trees)}
    out: list[str] = []
    for _, tree in trees:
        patches = tree.child("CfgPatches")
        for patch in patches.classes if patches else []:
            prop = patch.props.get("requiredaddons")
            for value, _ in prop[3] if prop else []:
                if value not in out and value.lower() not in own:
                    out.append(value)
    return out


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
    configs = config_files(mod_dir)
    if not configs:
        raise ReleaseError(f"no config.cpp under {mod_dir} (Addons, Keys and dot folders are not searched): "
                           "the classname list and dependencies come from config.cpp")
    trees = [(cfg.relative_to(mod_dir).as_posix(), read_config(cfg)) for cfg in configs]
    classes, duplicates = item_classes(trees)
    required = required_addons(trees)
    meta = mod_cpp(mod_dir)
    summary = meta.get("overview") or readme_summary(mod_dir)
    non_vanilla = [a for a in required if not a.upper().startswith("DZ_")]
    deps = [d.lstrip("@") for d in deps or []]
    if any(d.lower() == mod.lower() for d in deps):
        raise ReleaseError(f"--deps {deps} names the mod itself ({mod}). --deps takes every name after it, so put "
                           "<ModName> before --deps, or end the list with --")
    keys = find_keys(mod, mod_dir, p_mods)
    warnings = []
    if not summary:
        warnings.append("summary-missing: no overview in mod.cpp and no first paragraph in README.md, "
                        "so the Workshop text has a placeholder line to replace")
    if non_vanilla and not deps:
        warnings.append(f"deps-unmapped: config.cpp requires non-vanilla addons {non_vanilla}. "
                        "Map each to the Workshop mod that ships it and rerun with --deps in load order, for example --deps CF")
    elif non_vanilla:
        # The script cannot know which Workshop mod ships which addon, so a wrong or
        # incomplete --deps would otherwise ship silently.
        warnings.append(f"deps-unmapped: config.cpp requires non-vanilla addons {non_vanilla} and --deps names "
                        f"{deps}. The script cannot tell which mod ships which addon: check that every listed addon "
                        "is shipped by one of those mods, and rerun with the missing mods added to --deps if not")
    unresolved = [c["name"] for c in classes if c["scope"] is None]
    if unresolved:
        warnings.append(f"scope-unknown: {unresolved} set no scope here and take it from a parent outside this mod; "
                        "set an explicit scope in config.cpp for each listed class (scope = 2 for spawnable items, "
                        "otherwise 0 or 1) and rerun")
    if duplicates:
        warnings.append(f"class-duplicate: {duplicates} are defined in more than one config.cpp; the texts use the "
                        "first definition. Keep each class in one config.cpp and rerun")
    if not keys["public"] and p_mods is not None and not p_mods.parent.is_dir():
        # The key usually sits only in the deployed @mod, so an unmounted drive is
        # the likely cause, not an unsigned PBO.
        warnings.append(f"no-bikey: no .bikey in the mod's Keys/ folder, and {p_mods.parent} is not mounted, so "
                        f"{p_mods / ('@' + mod) / 'Keys'} could not be checked; mount it (/dayz-workdrive) and rerun. "
                        "If the key is not there either, sign the PBO before release")
    elif not keys["public"]:
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
        "configs": [rel for rel, _ in trees],
        "patches": patch_classes(trees),
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


def _git_installed() -> bool:
    return shutil.which("git") is not None


def git_changes(mod_dir: Path, since: Optional[str], version: Optional[str] = None) -> dict:
    """Commits that touched the mod folder since `since`.

    The default is the latest tag when the mod folder is its own repository. A mod
    inside a bigger repository (an Agentic-Z clone) cannot use that repository's
    tags, so it starts after the newest chore(release) commit that touched the mod
    folder, or takes the whole folder history when there is none.
    When that tag is this release (it points at HEAD, or it is `version` or
    v<version>), the user tagged before writing the notes, so the entry starts
    after the tag before it instead; `skipped` names the tag passed over.
    `from` says where the start came from: "option", "tag", "release-commit" or None.
    Without history, `no_git` says why: "missing" (git is not installed) or "no-repo".
    """
    if not _git_installed():
        return {"git": False, "no_git": "missing", "since": None, "from": None, "commits": []}
    top = _git(mod_dir, "rev-parse", "--show-toplevel")
    if top is None:
        return {"git": False, "no_git": "no-repo", "since": None, "from": None, "commits": []}
    own_repo = Path(top.strip()).resolve() == mod_dir.resolve()
    origin = skipped = None
    if since is None and own_repo:
        tag = (_git(mod_dir, "describe", "--tags", "--abbrev=0") or "").strip() or None
        if tag:
            head = _git(mod_dir, "rev-parse", "HEAD")
            at_tag = _git(mod_dir, "rev-parse", f"{tag}^{{commit}}")
            if (head is not None and head == at_tag) or (version and tag in (version, f"v{version}")):
                skipped = tag
                tag = (_git(mod_dir, "describe", "--tags", "--abbrev=0", f"{tag}^{{commit}}~1") or "").strip() or None
        since = tag
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
    # %x1e ends each record, because the body (read for a BREAKING CHANGE footer)
    # spans lines.
    args = ["log", "--no-merges", "--format=%h%x1f%as%x1f%s%x1f%b%x1e"]
    if since:
        args.append(f"{since}..HEAD")
    out = _git(mod_dir, *args, "--", ".")
    commits = []
    for record in (out or "").split("\x1e"):
        parts = record.strip("\r\n").split("\x1f")
        if len(parts) == 4 and not SKIP_SUBJECT_RE.match(parts[2]):
            commits.append({"hash": parts[0], "date": parts[1], "subject": parts[2], "body": parts[3]})
    return {"git": True, "since": since, "from": origin, "commits": commits, "own_repo": own_repo,
            "skipped": skipped}


def group_changes(commits: list[dict]) -> dict[str, list[str]]:
    """Commit subjects by changelog heading, in GROUP_ORDER, empty headings left out.

    A breaking commit goes under BREAKING_GROUP whatever its type; docs, test, ci,
    build, style, refactor and chore go under INTERNAL_GROUP.
    """
    groups: dict[str, list[str]] = {name: [] for name in GROUP_ORDER}
    for c in commits:
        m = CONVENTIONAL_RE.match(c["subject"])
        kind, text = (m.group("type").lower(), m.group("rest")) if m else ("", c["subject"])
        text = text[:1].upper() + text[1:]
        if (m and m.group("bang")) or BREAKING_FOOTER_RE.search(c.get("body") or ""):
            name = BREAKING_GROUP
        elif kind in INTERNAL_TYPES:
            name = INTERNAL_GROUP
        else:
            name = next((g for g, types in CHANGE_GROUPS if kind in types), OTHER_GROUP)
        groups[name].append(text)
    return {k: v for k, v in groups.items() if v}


# --- the four texts -----------------------------------------------------------

SUMMARY_PLACEHOLDER = "Write one or two sentences here on what the mod adds."
KIT_LINK_PLACEHOLDER = "[url=SERVER_KIT_LINK]server kit[/url]"


def bb(text: str) -> str:
    """text as literal Steam BBCode: a [ or ] in it is shown, not read as a tag.

    Steam BBCode has no escape character; [noparse]...[/noparse] shows its content
    as typed (Steam's formatting help, steamcommunity.com/comment/Guide/formattinghelp;
    a Steam fact, not a DayZ file, so not checked against P:). A [/noparse] inside
    the text would end it early, so its slash is spaced out.
    """
    if "[" not in text and "]" not in text:
        return text
    return "[noparse]" + re.sub(r"(?i)\[/noparse\]", "[/ noparse]", text) + "[/noparse]"


def _label(c: dict) -> str:
    name = c["display_name"]
    if name and not name.startswith("$"):
        return f"{bb(name)} ({c['name']})"
    return c["name"]


def workshop_text(facts: dict, version: str, groups: dict[str, list[str]], since: Optional[str] = None) -> str:
    out = [f"[h1]{bb(facts['title'])}[/h1]", "", bb(facts["summary"] or SUMMARY_PLACEHOLDER), ""]
    if facts["spawnable"]:
        out += ["[h2]What it adds[/h2]", "[list]"]
        out += [f"[*]{_label(c)}" for c in facts["spawnable"]]
        out += ["[/list]", ""]
    out.append("[h2]Requirements[/h2]")
    if facts["deps"]:
        out += ["Load these mods before this one:", "[list]"] + [f"[*]@{bb(d)}" for d in facts["deps"]] + ["[/list]"]
    elif facts["non_vanilla_addons"]:
        out.append("This mod needs: " + bb(", ".join(facts["non_vanilla_addons"])) + ".")
    else:
        out.append("No other mods are needed.")
    out += [
        "",
        "[h2]Server owners[/h2]",
        "Copy the key from the mod's Keys folder into your server's keys folder. "
        f"Download the server kit for the types.xml entries, the cfgeconomycore.xml lines and the load order: {KIT_LINK_PLACEHOLDER}",
        "",
        "[h2]Changes[/h2]" if version == "Unreleased" else f"[h2]Changes in {version}[/h2]",
    ]
    # Players read this list, so internal work (INTERNAL_GROUP) stays in changelog.md only.
    lines = [("[b]Breaking:[/b] " if name == BREAKING_GROUP else "") + bb(item)
             for name, items in groups.items() if name != INTERNAL_GROUP for item in items]
    if lines:
        out += ["[list]"] + [f"[*]{line}" for line in lines] + ["[/list]"]
    elif groups:
        out.append("No player-facing changes" + (f" since {since}." if since else "."))
    elif since:
        out.append(f"No changes since {since}.")
    else:
        out.append("First release.")
    return "\n".join(out) + "\n"


def changelog_entry(facts: dict, version: str, date: str, changes: dict, groups: dict[str, list[str]]) -> str:
    out = [f"## {version} ({date})", ""]
    if not changes["git"] and changes.get("no_git") == "missing":
        out += ["git is not installed, so the changes could not be read. Write them by hand.", ""]
    elif not changes["git"]:
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
            "Every class with `scope = 2` in the mod's `config.cpp` files. Each one needs a `types.xml` entry to "
            "spawn as loot.",
            "",
            "| Classname | Section | Parent | Display name | Config |",
            "|---|---|---|---|---|",
        ]
        for c in facts["spawnable"]:
            out.append(f"| `{c['name']}` | {c['section']} | {c['parent'] or ''} | {c['display_name'] or ''} "
                       f"| `{c['config']}` |")
        out.append("")
    else:
        files = ", ".join(f"`{rel}`" for rel in facts["configs"])
        out += [f"No class in {files} has `scope = 2`, so there is nothing to add to `types.xml`.", ""]
    if facts["unresolved"]:
        out += [
            "## Scope not set",
            "",
            "These classes set no scope here and take it from a parent outside this mod. "
            "Set an explicit scope in config.cpp for each (scope = 2 for spawnable items, otherwise 0 or 1) and rerun.",
            "",
        ]
        out += [f"- `{c['name']}` (parent `{c['parent']}`) in `{c['config']}`" for c in facts["unresolved"]]
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

# The hash of each text the last run wrote, so a rerun can tell hand edits from
# its own output (whose changelog date, classes or commits may since have changed).
STATE_FILE = ".release-pack.json"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_state(out_dir: Path) -> dict[str, str]:
    try:
        data = json.loads((out_dir / STATE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}


def _backup_if_edited(path: Path, text: str, written: Optional[str]) -> Optional[Path]:
    """Copy path to a free <name>.bak (then <name>.2.bak, ...) when it holds hand edits.

    The user edits workshop-description.txt by hand (SERVER_KIT_LINK, the summary
    line), so a rerun must not drop those edits. `written` is the hash of the text
    the last run wrote to path: a file that still matches it holds no hand edits
    and is replaced without a backup. With no hash on record, any text other than
    `text` is backed up. An older backup is never replaced.
    """
    if not path.is_file():
        return None
    old = path.read_text(encoding="utf-8", errors="replace")
    if old == text or (written is not None and _hash(old) == written):
        return None
    backup = path.with_name(f"{path.name}.bak")
    n = 2
    while backup.exists():
        backup = path.with_name(f"{path.name}.{n}.bak")
        n += 1
    backup.write_text(old, encoding="utf-8", newline="\n")
    return backup


def release_pack(mod: str, mod_dir: Path, out_dir: Path, version: str = "Unreleased", since: Optional[str] = None,
                 deps: Optional[list[str]] = None, p_mods: Optional[Path] = P_MODS, date: Optional[str] = None) -> dict:
    facts = mod_facts(mod, mod_dir, deps, p_mods)
    changes = git_changes(mod_dir, since, version)
    facts["warnings"].append("server-kit-link: the Workshop text links the server kit as SERVER_KIT_LINK; replace it "
                             "with the address where the kit is published (for example a GitHub release)")
    if not changes["git"] and changes.get("no_git") == "missing":
        facts["warnings"].append("no-git: git is not installed or not on PATH, so the changelog entry is empty; "
                                 "install Git and rerun, or write the changes by hand")
    elif not changes["git"]:
        facts["warnings"].append("no-git: the mod folder is not in a git repository, so the changelog entry is empty")
    else:
        if changes["since"] is None and changes.get("skipped"):
            facts["warnings"].append(f"changelog-full-history: {changes['skipped']} is this release and there is no "
                                     "tag before it, so the entry lists the whole history; pass --since <ref> to "
                                     "limit the entry")
        elif changes["since"] is None and changes["own_repo"]:
            facts["warnings"].append("changelog-full-history: the mod's repository has no tag, so the entry lists its "
                                     "whole history; tag the release (git tag v<version>) so the next run starts "
                                     "after it, or pass --since <ref> to limit the entry")
        elif changes["since"] is None:
            facts["warnings"].append("changelog-full-history: no chore(release) commit touched the mod folder, so the "
                                     "entry lists its whole history; pass --since <ref> to limit the entry")
        if not changes["commits"]:
            since_text = f" since {changes['since']}" if changes["since"] else ""
            facts["warnings"].append(f"changelog-empty: no commits touched the mod folder{since_text}, "
                                     "so the changelog entry lists no changes")
    groups = group_changes(changes["commits"])
    if date is None:
        date = datetime.date.today().isoformat()
    files = {
        "workshop-description.txt": workshop_text(facts, version, groups, changes["since"]),
        "changelog.md": changelog_entry(facts, version, date, changes, groups),
        "classnames.md": classnames_md(facts),
        "server-install.md": install_md(facts),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    state = _read_state(out_dir)
    backups = []
    for name, text in files.items():
        backup = _backup_if_edited(out_dir / name, text, state.get(name))
        if backup is not None:
            backups.append(backup.name)
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    hashes = {name: _hash(text) for name, text in files.items()}
    (out_dir / STATE_FILE).write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8", newline="\n")
    if backups:
        facts["warnings"].append(f"kept-backup: {backups} hold the previous texts, which were edited after the last "
                                 "run wrote them (for example the SERVER_KIT_LINK address or the summary line); "
                                 "copy the edits you still want into the new files, then delete the backups")
    return {
        "mod": mod,
        "version": version,
        "out": str(out_dir),
        "files": sorted(files),
        "configs": facts["configs"],
        "spawnable": [c["name"] for c in facts["spawnable"]],
        "unresolved": [c["name"] for c in facts["unresolved"]],
        "load_order": load_order(facts),
        "keys": facts["keys"],
        "changes": {"since": changes["since"], "from": changes["from"], "commits": len(changes["commits"]),
                    **({"skipped": changes["skipped"]} if changes.get("skipped") else {})},
        "warnings": facts["warnings"],
    }


def resolve_mod(mod: Optional[str], mod_dir: Optional[Path], out: Optional[Path]) -> tuple[str, Path, Path]:
    """(mod name, mod folder, output folder) from <ModName> or --mod-dir.

    The default output is output/<ModName>-release/ in the project, or in this
    repository for --mod-dir (never the current folder, which may be the mod's own).
    An output folder inside the mod folder is refused: AddonBuilder would pack it
    and git would commit it with the mod source.
    """
    if mod_dir:
        mod_dir = mod_dir.resolve()
        name = mod or mod_dir.name
        base = REPO
    else:
        try:
            base = h.resolve_project_dir()
        except SystemExit as e:  # resolve_project_dir printed why on stderr
            raise ReleaseError("no usable project: run /dayz-init, or pass --mod-dir") from e
        name, mod_dir = mod, base / "workspace" / mod
    out_dir = out.resolve() if out else (base / "output" / f"{name}-release").resolve()
    if out_dir.is_relative_to(mod_dir.resolve()):
        raise ReleaseError(f"output folder {out_dir} is inside the mod folder {mod_dir}, where it would be packed "
                           "into the PBO and committed with the source; pass --out with a folder outside the mod")
    return name, mod_dir, out_dir


def render_text(report: dict) -> str:
    out = [f"[OK]   Wrote {len(report['files'])} files to {report['out']}"]
    out += [f"       {name}" for name in report["files"]]
    out.append(f"       {len(report['spawnable'])} spawnable classes from {', '.join(report['configs'])}, "
               f"{report['changes']['commits']} commits, load order {';'.join(report['load_order'])}")
    if report["changes"]["from"] == "release-commit":
        out.append(f"       changelog starts after {report['changes']['since']}, "
                   "the newest chore(release) commit in the mod folder")
    elif report["changes"]["from"] == "tag" and report["changes"].get("skipped"):
        out.append(f"       changelog starts after {report['changes']['since']}, the tag before "
                   f"{report['changes']['skipped']} (that tag is this release)")
    elif report["changes"]["from"] == "tag":
        out.append(f"       changelog starts after {report['changes']['since']}, the latest tag in the mod's repository")
    out += [f"[WARN] {w}" for w in report["warnings"]]
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Write the Workshop text, changelog, classname list and install notes for a mod.")
    parser.add_argument("mod", nargs="?", help="Mod name under workspace/ in the project cached by /dayz-init.")
    parser.add_argument("--mod-dir", type=Path, help="Use this folder instead (its name is the mod name unless "
                        "<ModName> is given too).")
    parser.add_argument("--version", default="Unreleased", help="Version for the changelog and Workshop text.")
    parser.add_argument("--since", help="Git ref the changelog starts after. Default: the latest tag in the mod's own "
                        "repository, else the newest chore(release) commit in the mod folder, else all history.")
    # extend, so a second --deps adds to the list instead of replacing it.
    parser.add_argument("--deps", nargs="+", action="extend", default=[], metavar="MOD",
                        help="Dependency mods in load order (CF or @CF). Takes every name after it, so give "
                        "<ModName> first.")
    parser.add_argument("--out", type=Path, help="Output folder outside the mod folder. Default output/<ModName>-release/ "
                        "in the project, or in this repository with --mod-dir.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON.")
    try:
        args = parser.parse_args(argv)
        if not args.mod and not args.mod_dir and args.deps:
            parser.error(f"give a <ModName> or --mod-dir. --deps takes every name after it, so {args.deps[-1]!r} "
                         "was read as a dependency: put <ModName> before --deps, or end the list with --")
        if not args.mod and not args.mod_dir:
            parser.error("give a <ModName> or --mod-dir")
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    try:
        mod, mod_dir, out_dir = resolve_mod(args.mod, args.mod_dir, args.out)
        report = release_pack(mod, mod_dir, out_dir, args.version, args.since, args.deps)
    except (ReleaseError, OSError, ValueError) as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"[FAIL] {e}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2) if args.json else render_text(report))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
