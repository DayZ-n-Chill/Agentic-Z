"""Scope the agent to a single DayZ mod.

Adds Edit deny rules to .claude/settings.local.json for OTHER mods' workspace
folders, P:\\<other>\\ junctions, and P:\\Mods\\@<other>\\ deploy dirs. Claude
Code checks Edit rules for both the Edit and Write tools. Reads stay broad. Records the exact rules added in
.claude/local-memory/dayz-active-scope.json so --clear is precise.

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
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

# PROJECT_DIR = user's project, where workspace/, settings.local.json, and
# local-memory/ all live.
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
WORKSPACE = PROJECT_DIR / "workspace"
SETTINGS_LOCAL = PROJECT_DIR / ".claude" / "settings.local.json"
SCOPE_STATE = PROJECT_DIR / ".claude" / "local-memory" / "dayz-active-scope.json"

OK = "[OK]   "
FAIL = "[FAIL] "
INFO = "[INFO] "

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

# Rule paths use gitignore syntax. A mod name containing one of these would
# turn its deny rule into a wildcard, negation or comment, so such names are refused.
GITIGNORE_META = frozenset("*?[!#")


def _has_meta(name: str) -> bool:
    return any(c in GITIGNORE_META for c in name)


def _posix_rule_path(path: Path) -> str:
    """C:\\Games\\DayZ -> //c/Games/DayZ (the absolute form Claude Code matches)."""
    drive, rest = os.path.splitdrive(str(path))
    return "//" + drive.rstrip(":").lower() + rest.replace("\\", "/")


def _game_workshop_dir() -> Optional[Path]:
    """<DayZ game>\\!Workshop, the real folder behind the P:\\Mods junction, or None."""
    game = h.preflight.find_dayz_game()
    return game / "!Workshop" if game is not None else None


def _load_settings() -> dict:
    if not SETTINGS_LOCAL.exists():
        return {}
    try:
        return json.loads(SETTINGS_LOCAL.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"{FAIL} Could not read {SETTINGS_LOCAL}: {e}", file=sys.stderr)
        sys.exit(1)


def _save_settings(data: dict) -> None:
    SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_LOCAL.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _load_state() -> Optional[dict]:
    if not SCOPE_STATE.exists():
        return None
    try:
        return json.loads(SCOPE_STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_state(active_mod: str, rules: list[str]) -> None:
    SCOPE_STATE.parent.mkdir(parents=True, exist_ok=True)
    SCOPE_STATE.write_text(
        json.dumps(
            {
                "active_mod": active_mod,
                "scoped_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "denied_rules": rules,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _clear_state() -> None:
    if SCOPE_STATE.exists():
        SCOPE_STATE.unlink()


def _list_mods() -> list[str]:
    if not WORKSPACE.exists():
        return []
    out = []
    for p in sorted(WORKSPACE.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith("."):
            continue
        out.append(p.name)
    return out


def _remove_prior_rules(settings: dict) -> int:
    """Strip any deny rules that match a previous run's pattern. Returns count removed."""
    state = _load_state()
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
            f"{FAIL} Mod name {mod_name!r} contains one of * ? [ ! # , which permission "
            "rules treat as pattern syntax. Rename the mod folder.",
            file=sys.stderr,
        )
        return 1
    target = WORKSPACE / mod_name
    if not target.exists() or not target.is_dir():
        known = _list_mods()
        print(f"{FAIL} workspace\\{mod_name} does not exist.", file=sys.stderr)
        if known:
            print("        Known mods:", file=sys.stderr)
            for k in known:
                print(f"          - {k}", file=sys.stderr)
        else:
            print("        No mods scaffolded yet.", file=sys.stderr)
        print(
            f"        Scaffold first: /dayz-new-mod {mod_name}  or  "
            "/dayz-import-mod --source <path>",
            file=sys.stderr,
        )
        return 1

    print(f"DayZ scope: {mod_name}\n")
    print(f"{OK} Mod found: workspace\\{mod_name}")

    settings = _load_settings()
    removed = _remove_prior_rules(settings)
    if removed:
        print(f"{INFO} Removed {removed} rule(s) from a prior scope")

    siblings = [m for m in _list_mods() if m != mod_name]
    if not siblings:
        # Still record state so --clear is consistent and re-runs are idempotent.
        _save_settings(settings)
        _save_state(mod_name, [])
        print(f"{INFO} No sibling mods to deny. Scope is set, but no rules were needed.")
        return 0

    bad = [m for m in siblings if _has_meta(m)]
    if bad:
        print(
            f"{FAIL} Sibling mod folder(s) {', '.join(bad)} contain one of * ? [ ! # ,\n"
            "        so no exact deny rule can be written for them. Rename them first.",
            file=sys.stderr,
        )
        return 1

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
    for r in new_rules:
        if r not in deny:
            deny.append(r)

    _save_settings(settings)
    _save_state(mod_name, new_rules)

    print(f"{OK} Added {len(new_rules)} Edit deny rules to .claude\\settings.local.json")
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

    settings = _load_settings()
    removed = _remove_prior_rules(settings)
    _save_settings(settings)
    _clear_state()

    active = state.get("active_mod", "<unknown>")
    print(f"{OK} Cleared scope (was: {active}). Removed {removed} deny rule(s).")
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
