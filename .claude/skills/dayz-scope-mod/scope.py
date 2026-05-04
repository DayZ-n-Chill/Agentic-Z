"""Scope the agent to a single DayZ mod.

Adds deny rules to .claude/settings.local.json that block Edit/Write to OTHER
mods' workspace folders, P:\\<other>\\ junctions, and P:\\Mods\\@<other>\\
deploy dirs. Reads stay broad. Records the exact rules added in
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
import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parent.parent.parent
WORKSPACE = REPO_ROOT / "workspace"
SETTINGS_LOCAL = REPO_ROOT / ".claude" / "settings.local.json"
SCOPE_STATE = REPO_ROOT / ".claude" / "local-memory" / "dayz-active-scope.json"

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "
INFO = "[INFO] "

# Folders under workspace/ that are NEVER mods (don't deny these).
NON_MOD_DIRS = {"_server"}

# Per-other-mod deny templates. {} substituted with the other mod's name.
DENY_TEMPLATES = (
    "Edit(workspace/{name}/**)",
    "Write(workspace/{name}/**)",
    "Edit(P:\\{name}\\**)",
    "Write(P:\\{name}\\**)",
    "Edit(P:\\Mods\\@{name}\\**)",
    "Write(P:\\Mods\\@{name}\\**)",
)


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
        if p.name in NON_MOD_DIRS:
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

    print(f"{INFO} Sibling mods detected: {len(siblings)} ({', '.join(siblings)})")

    new_rules: list[str] = []
    for other in siblings:
        for tmpl in DENY_TEMPLATES:
            new_rules.append(tmpl.format(name=other))

    perms = settings.setdefault("permissions", {})
    deny = perms.setdefault("deny", [])
    for r in new_rules:
        if r not in deny:
            deny.append(r)

    _save_settings(settings)
    _save_state(mod_name, new_rules)

    print(f"{OK} Added {len(new_rules)} deny rules to .claude\\settings.local.json")
    print(f"{OK} Active scope recorded at .claude\\local-memory\\dayz-active-scope.json")
    print()
    print("Reads remain broad. Edit/Write to other mods is blocked.")
    print("Run /dayz-scope-clear (or scope.py --clear) to lift.")
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scope the agent to a single DayZ mod by adding deny rules for sibling mods."
    )
    parser.add_argument("mod", nargs="?", help="Mod name under workspace/")
    parser.add_argument("--clear", action="store_true", help="Remove the active scope")
    parser.add_argument("--status", action="store_true", help="Show current scope")
    args = parser.parse_args()

    if args.clear and args.status:
        print(f"{FAIL} --clear and --status are mutually exclusive", file=sys.stderr)
        return 2
    if args.clear and args.mod:
        print(f"{FAIL} --clear takes no mod argument", file=sys.stderr)
        return 2
    if args.status and args.mod:
        print(f"{FAIL} --status takes no mod argument", file=sys.stderr)
        return 2

    if args.clear:
        return cmd_clear()
    if args.status:
        return cmd_status()
    if not args.mod:
        parser.print_help(sys.stderr)
        return 2
    return cmd_scope(args.mod)


if __name__ == "__main__":
    sys.exit(main())
