"""Scope the agent to a single DayZ mod.

Adds Edit deny rules to .claude/settings.local.json for OTHER mods' workspace
folders, P:\\<other>\\ junctions, and P:\\Mods\\@<other>\\ deploy dirs. Claude
Code checks Edit rules for both the Edit and Write tools. Reads stay broad.
Records the exact rules added in .claude/local-memory/dayz-active-scope.json
so --clear is precise. Before settings.local.json is changed, the old file is
copied to .claude/local-memory/settings.local.json.<timestamp>.bak, a new
name each time, so no older backup is ever replaced. Every write goes through
a temp file in .claude/local-memory/ that replaces the target in one step; if a
write fails (file locked, disk full) the temp file is removed and the run
prints a [FAIL] line saying what state each file is in, then exits 1.

Run:
    python .claude/skills/dayz-scope-mod/scope.py <ModName>
    python .claude/skills/dayz-scope-mod/scope.py --status
    python .claude/skills/dayz-scope-mod/scope.py --clear
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

# PROJECT_DIR = user's project, where workspace/, settings.local.json, and
# local-memory/ all live. Resolved by dayz-init/state.py: $CLAUDE_PROJECT_DIR,
# else the nearest folder at or above the current directory that holds the
# /dayz-init project cache (so a run from workspace/<mod>/ finds the project),
# else the current directory.
PROJECT_DIR = h.load_module("dayz_scope_mod_state", h.DAYZ_INIT_STATE).find_project_dir()
WORKSPACE = PROJECT_DIR / "workspace"
SETTINGS_LOCAL = PROJECT_DIR / ".claude" / "settings.local.json"
SCOPE_STATE = PROJECT_DIR / ".claude" / "local-memory" / "dayz-active-scope.json"

OK = "[OK]   "
FAIL = "[FAIL] "
INFO = "[INFO] "
WARN = "[WARN] "

# Per-other-mod deny templates in Claude Code permission-rule syntax:
# - File writes are checked against Edit(path) rules only; one Edit rule
#   blocks both the Edit and Write tools. A Write(path) rule is never matched.
# - "/path" in .claude/settings.local.json anchors at the primary working
#   directory (the project root).
# - "//path" is absolute. Windows paths are normalized to POSIX form before
#   matching (P:\Foo becomes /p/Foo), so P:\Foo\** is written //p/Foo/**.
DENY_TEMPLATES = (
    "Edit(/workspace/{name}/**)",
    "Edit(//p/{name}/**)",
    "Edit(//p/Mods/@{name}/**)",
)

# Rule paths use gitignore syntax. * ? [ are wildcards anywhere in a name.
# ! (negation) and # (comment) are special only at the start of a pattern, so
# they are fine mid-name (the real <game>\!Workshop rule relies on that); they
# are refused only as a name's first character, to stay clear of that edge.
GITIGNORE_WILDCARDS = frozenset("*?[")
GITIGNORE_LEADING = frozenset("!#")
META_HINT = "* ? [ anywhere, or a leading ! or #"


def _has_meta(name: str) -> bool:
    return any(c in GITIGNORE_WILDCARDS for c in name) or name[:1] in GITIGNORE_LEADING


def _posix_rule_path(path: Path) -> str:
    """C:\\Games\\DayZ -> //c/Games/DayZ (the absolute form Claude Code matches)."""
    drive, rest = os.path.splitdrive(str(path))
    return "//" + drive.rstrip(":").lower() + rest.replace("\\", "/")


def _game_workshop_dir() -> Optional[Path]:
    """<DayZ game>\\!Workshop, the real folder behind the P:\\Mods junction, or None."""
    game = h.preflight.find_dayz_game()
    return game / "!Workshop" if game is not None else None


class WriteError(Exception):
    """A file could not be written; the message names the file and the OS error."""


def _write_atomic(path: Path, text: str) -> None:
    """Write text to path through a temp file that replaces it in one step.

    The temp file lives in .claude/local-memory/ (gitignored, same volume as
    .claude/), so a leftover never shows up as an untracked file. On any OS
    error the temp file is removed and WriteError is raised; path is unchanged.
    """
    tmp = SCOPE_STATE.parent / f"{path.name}.tmp"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise WriteError(f"Could not write {path}: {e}") from e


LOCK_HINT = "(a lock held by an editor, antivirus or a sync tool, or a full disk)"


def _fail(err: object, *lines: str) -> int:
    """Print a [FAIL] block for a failed write and return exit code 1."""
    print(f"{FAIL} {err}", file=sys.stderr)
    for line in lines:
        print(f"        {line}", file=sys.stderr)
    return 1


def _load_settings() -> dict:
    """settings.local.json as a dict ({} if missing). Exits 1 if it cannot be used."""
    if not SETTINGS_LOCAL.exists():
        return {}
    try:
        data = json.loads(SETTINGS_LOCAL.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        print(f"{FAIL} Could not read {SETTINGS_LOCAL}: {e}", file=sys.stderr)
        print("        Fix the JSON by hand, then run this again. Nothing was changed.", file=sys.stderr)
        sys.exit(1)
    perms = data.get("permissions", {}) if isinstance(data, dict) else None
    if not isinstance(perms, dict) or not isinstance(perms.get("deny", []), list):
        print(
            f"{FAIL} {SETTINGS_LOCAL} must be a JSON object whose \"permissions\" is an object\n"
            "        and whose \"permissions.deny\" is a list. Fix it by hand, then run this again.\n"
            "        Nothing was changed.",
            file=sys.stderr,
        )
        sys.exit(1)
    return data


def _backup_path() -> Path:
    """A local-memory/settings.local.json.<timestamp>.bak path that does not exist yet.

    Backups go in .claude/local-memory/ (gitignored) so they never show up as
    untracked files next to the settings file.
    """
    folder = SCOPE_STATE.parent
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = folder / f"{SETTINGS_LOCAL.name}.{stamp}.bak"
    n = 1
    while candidate.exists():
        candidate = folder / f"{SETTINGS_LOCAL.name}.{stamp}-{n}.bak"
        n += 1
    return candidate


def _save_settings(data: dict) -> None:
    """Write settings.local.json only if it changes, backing up the old file first.

    The new text goes to a temp file that replaces the original in one step, so
    a failed write never leaves a half-written settings file. Raises WriteError
    (settings unchanged) if the backup or the write fails.
    """
    text = json.dumps(data, indent=2) + "\n"
    if SETTINGS_LOCAL.exists():
        if json.loads(SETTINGS_LOCAL.read_text(encoding="utf-8")) == data:
            return
        backup = _backup_path()
        try:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SETTINGS_LOCAL, backup)
        except OSError as e:
            raise WriteError(f"Could not back up {SETTINGS_LOCAL} to {backup}: {e}") from e
        print(f"{INFO} Backed up settings to .claude\\local-memory\\{backup.name}")
    _write_atomic(SETTINGS_LOCAL, text)


def _load_state() -> Optional[dict]:
    """The recorded scope, or None if there is none. Exits 1 if the file is unusable.

    A corrupt state file is never treated as "no scope": the rules it recorded
    may still be in settings.local.json, and ignoring it would orphan them.
    """
    if not SCOPE_STATE.exists():
        return None
    try:
        state = json.loads(SCOPE_STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        problem = f"cannot be read ({e})"
    else:
        rules = state.get("denied_rules") if isinstance(state, dict) else None
        if isinstance(rules, list) and all(isinstance(r, str) for r in rules):
            return state
        problem = 'is not an object with a "denied_rules" list of strings'
    print(
        f"{FAIL} The scope record {SCOPE_STATE} {problem}.\n"
        "        The deny rules it recorded may still be in .claude\\settings.local.json.\n"
        "        Remove the Edit(...) rules for other mods from permissions.deny by hand,\n"
        "        delete the scope record, then run this again. Nothing was changed.",
        file=sys.stderr,
    )
    sys.exit(1)


def _save_state(active_mod: str, rules: list[str]) -> None:
    """Write the scope record in one step. Raises WriteError (record unchanged) on failure."""
    text = json.dumps(
        {
            "active_mod": active_mod,
            "scoped_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "denied_rules": rules,
        },
        indent=2,
    ) + "\n"
    _write_atomic(SCOPE_STATE, text)


def _commit(active_mod: str, settings: dict, prior: list[str], added: list[str]) -> int:
    """Record the scope, then write the settings, so a deny rule is never unrecorded.

    The first record lists the prior run's rules as well as the new ones: if the
    settings write fails, every rule that may still be in settings.local.json is
    recorded and --clear can remove it. Once the settings are written the record
    is narrowed to the rules this run added. Returns 0, or 1 after a [FAIL]
    message that says what state the files were left in.
    """
    try:
        _save_state(active_mod, list(dict.fromkeys(prior + added)))
    except WriteError as e:
        return _fail(
            e,
            "Nothing was changed: settings.local.json and the scope record are as they were.",
            f"Fix the cause {LOCK_HINT}, then run this again.",
        )
    try:
        _save_settings(settings)
    except WriteError as e:
        return _fail(
            e,
            "settings.local.json was not changed. The scope record lists every rule that",
            f"may be in it. Fix the cause {LOCK_HINT}, then run this again,",
            "or run --clear to remove the recorded rules.",
        )
    try:
        _save_state(active_mod, added)
    except WriteError as e:
        return _fail(
            e,
            "settings.local.json was updated, but the scope record still also lists the",
            "previous scope's rules. --clear removes them all; or fix the cause",
            f"{LOCK_HINT} and run this again to correct the record.",
        )
    return 0


def _clear_state() -> None:
    if SCOPE_STATE.exists():
        SCOPE_STATE.unlink()


# A workspace folder gets deny rules only when it has one of these at its
# root, so helper folders such as workspace/_archive/ get none. /dayz-new-mod
# writes both. hooks/scope_guard.py is stricter: while a scope is active it
# treats every other folder as a mod unless its name starts with '_'.
MOD_MARKERS = ("config.cpp", "$PBOPREFIX$")


def _list_mods() -> list[str]:
    """Every non-dotted folder under workspace/: the names the active mod may take."""
    if not WORKSPACE.exists():
        return []
    return [p.name for p in sorted(WORKSPACE.iterdir()) if p.is_dir() and not p.name.startswith(".")]


def _is_mod_dir(name: str) -> bool:
    return any((WORKSPACE / name / m).is_file() for m in MOD_MARKERS)


def _remove_prior_rules(settings: dict, state: Optional[dict]) -> int:
    """Strip the deny rules a previous run recorded. Returns count removed."""
    if not state:
        return 0
    prior = set(state.get("denied_rules", []))
    if not prior:
        return 0
    deny = settings.get("permissions", {}).get("deny", [])
    kept = [r for r in deny if r not in prior]
    removed = len(deny) - len(kept)
    if removed:
        settings.setdefault("permissions", {})["deny"] = kept
    return removed


def cmd_scope(mod_name: str) -> int:
    if _has_meta(mod_name):
        print(
            f"{FAIL} Mod name {mod_name!r} contains {META_HINT}, which permission "
            "rules treat as pattern syntax. Rename the mod folder.",
            file=sys.stderr,
        )
        return 1
    # Match the folder on disk case-insensitively (Windows paths are), then use
    # its real name everywhere, so the active mod is never listed as its own sibling.
    known = _list_mods()
    on_disk = mod_name if mod_name in known else next(
        (m for m in known if m.lower() == mod_name.lower()), None
    )
    if on_disk is None:
        print(f"{FAIL} workspace\\{mod_name} does not exist.", file=sys.stderr)
        if known:
            print("        Known mods:", file=sys.stderr)
            for k in known:
                print(f"          - {k}", file=sys.stderr)
        else:
            print(f"        No mods scaffolded yet under {WORKSPACE}.", file=sys.stderr)
        print(
            f"        Scaffold first: /dayz-new-mod {mod_name}  or  "
            "/dayz-import-mod --source <path>",
            file=sys.stderr,
        )
        return 1
    mod_name = on_disk

    others = [m for m in known if m != mod_name]
    siblings = [m for m in others if _is_mod_dir(m)]
    not_mods = [m for m in others if m not in siblings]
    bad = [m for m in siblings if _has_meta(m)]
    if bad:
        print(
            f"{FAIL} Sibling mod folder(s) {', '.join(bad)} contain {META_HINT},\n"
            "        so no exact deny rule can be written for them. Rename them first.",
            file=sys.stderr,
        )
        return 1

    # Read both files before printing or writing anything, so a corrupt one
    # stops the run with nothing changed.
    state = _load_state()
    settings = _load_settings()

    print(f"DayZ scope: {mod_name}\n")
    print(f"{OK} Mod found: workspace\\{mod_name}")
    if not_mods:
        print(f"{INFO} Not mods (no config.cpp or $PBOPREFIX$), left writable: {', '.join(not_mods)}")

    prior = list(state.get("denied_rules", [])) if state else []
    removed = _remove_prior_rules(settings, state)
    if removed:
        print(f"{INFO} Removed {removed} rule(s) from a prior scope")

    if not siblings:
        # Still record state so --clear is consistent and re-runs are idempotent.
        if _commit(mod_name, settings, prior, []):
            return 1
        print(f"{INFO} No sibling mods to deny. Scope is set, but no rules were needed.")
        return 0

    print(f"{INFO} Sibling mods detected: {len(siblings)} ({', '.join(siblings)})")

    # P:\Mods is a junction, so also deny the real folder it points at.
    workshop = _game_workshop_dir()
    if workshop is None:
        print(f"{INFO} DayZ game install not found: no rule for <game>\\!Workshop\\@<other>")

    new_rules: list[str] = []
    for other in siblings:
        for tmpl in DENY_TEMPLATES:
            new_rules.append(tmpl.format(name=other))
        if workshop is not None:
            new_rules.append(f"Edit({_posix_rule_path(workshop)}/@{other}/**)")

    perms = settings.setdefault("permissions", {})
    deny = perms.setdefault("deny", [])
    # Record only the rules this run appended: a rule the user already had stays
    # theirs, so --clear must not remove it.
    added = [r for r in new_rules if r not in deny]
    deny.extend(added)

    if _commit(mod_name, settings, prior, added):
        return 1

    print(f"{OK} Added {len(added)} Edit deny rules to .claude\\settings.local.json")
    skipped = len(new_rules) - len(added)
    if skipped:
        print(f"{INFO} {skipped} matching rule(s) were already present; they stay yours and --clear keeps them")
    print(f"{OK} Active scope recorded at .claude\\local-memory\\dayz-active-scope.json")
    print()
    print("Reads remain broad. Edit and Write to other mods are blocked.")
    print("Run /dayz-scope-mod --clear (or scope.py --clear) to lift.")
    return 0


def cmd_clear() -> int:
    state = _load_state()
    if not state:
        print(f"{INFO} No active scope. Nothing to clear.")
        return 0

    recorded = set(state.get("denied_rules", []))
    if SETTINGS_LOCAL.exists():
        settings = _load_settings()
        present = set(settings.get("permissions", {}).get("deny", []))
        removed = _remove_prior_rules(settings, state)
        try:
            _save_settings(settings)
        except WriteError as e:
            return _fail(
                e,
                "Nothing was changed: the rules are still in settings.local.json and the",
                f"scope record still lists them. Fix the cause {LOCK_HINT},",
                "then run --clear again.",
            )
    else:
        # Nothing to remove the rules from: do not create an empty settings file.
        present, removed = set(), 0
    try:
        _clear_state()
    except OSError as e:
        return _fail(
            f"Could not delete {SCOPE_STATE}: {e}",
            "The recorded rules were removed from settings.local.json, but the scope",
            "record remains, so the scope guard hook still enforces it. Delete the",
            "record by hand once the cause is fixed.",
        )

    active = state.get("active_mod", "<unknown>")
    print(f"{OK} Cleared scope (was: {active}). Removed {removed} deny rule(s).")
    missing = len(recorded - present)
    if missing:
        where = (
            "were not in .claude\\settings.local.json"
            if SETTINGS_LOCAL.exists()
            else "were not found: .claude\\settings.local.json does not exist"
        )
        print(
            f"{WARN} {missing} recorded rule(s) {where}. They were removed or changed\n"
            "        outside this skill; check permissions.deny by hand."
        )
    return 0


def cmd_status() -> int:
    state = _load_state()
    if not state:
        print(f"{INFO} No active scope. Edit/Write are unrestricted across mods.")
        return 0
    active = state.get("active_mod", "<unknown>")
    rules = state.get("denied_rules", [])
    when = state.get("scoped_at", "<unknown>")
    print(f"Active scope: {active}")
    print(f"Scoped at:    {when}")
    print(f"Deny rules:   {len(rules)}")
    if rules:
        for r in rules:
            print(f"  - {r}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scope the agent to a single DayZ mod by adding deny rules for sibling mods."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("mod", nargs="?", help="Mod name under workspace/")
    group.add_argument("--clear", action="store_true", help="Remove the active scope")
    group.add_argument("--status", action="store_true", help="Show current scope")
    args = parser.parse_args(argv)

    if args.clear:
        return cmd_clear()
    if args.status:
        return cmd_status()
    return cmd_scope(args.mod)


if __name__ == "__main__":
    sys.exit(main())
