"""PreToolUse hook: block edits to other mods while /dayz-scope-mod is active.

/dayz-scope-mod <Mod> records the active mod in
<project>/.claude/local-memory/dayz-active-scope.json (written by
.claude/skills/dayz-scope-mod/scope.py) and adds Edit deny rules for the
sibling mods that existed at that moment. This hook backs those rules up with
a reason Claude can act on, and also covers mod folders created after the
scope was set:

  - <project>/workspace/<Other>/...   any folder other than the active mod
  - P:\\<Other>\\... and P:\\Mods\\@<Other>\\...   when <Other> is a mod in workspace/

The hook matches Edit, Write and MultiEdit only. Shell commands are not
checked: a Bash or PowerShell copy, redirect, sed -i or Set-Content into
another mod's folder is not seen here (the Edit deny rules from scope.py
cover some of those).

No scope file means no scope: the hook exits silently. A malformed hook input
or state file also exits silently, so the hook never blocks on its own bug.
Output format: https://code.claude.com/docs/en/hooks#pretooluse-decision-control
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

SCOPE_STATE = Path(".claude") / "local-memory" / "dayz-active-scope.json"


def _parts(path: str) -> list[str]:
    """Split on both separators; 'P:\\A\\b' and '/p/A/b' both give ['p:', 'A', 'b']."""
    s = path.replace("\\", "/")
    m = re.match(r"^/([A-Za-z])/(.*)$", s)  # Git Bash form /p/Foo
    if m:
        s = f"{m.group(1)}:/{m.group(2)}"
    return [p for p in s.split("/") if p not in ("", ".")]


def _norm(path: str) -> list[str]:
    return [p.lower() for p in _parts(path)]


def workspace_mods(project: Path) -> list[str]:
    ws = project / "workspace"
    if not ws.is_dir():
        return []
    return [p.name for p in ws.iterdir() if p.is_dir() and not p.name.startswith(".")]


def target_mod(file_path: str, project: Path, mods: list[str]) -> Optional[str]:
    """The mod a path belongs to, as spelled in the path, or None if it isn't inside a mod folder."""
    parts = _parts(file_path)
    low = [p.lower() for p in parts]
    ws = _norm(str(project / "workspace"))
    if len(low) > len(ws) + 1 and low[: len(ws)] == ws:
        name = parts[len(ws)]
        return None if name.startswith(".") else name
    if low and low[0] == "p:":
        known = {m.lower() for m in mods}
        if len(low) > 3 and low[1] == "mods" and low[2].startswith("@") and low[2][1:] in known:
            return parts[2][1:]
        if len(low) > 2 and low[1] in known:
            return parts[1]
    return None


def decide(data: dict, project: Path) -> Optional[str]:
    """Return a deny reason, or None to let the edit through."""
    state_file = project / SCOPE_STATE
    if not state_file.is_file():
        return None
    active = json.loads(state_file.read_text(encoding="utf-8")).get("active_mod")
    file_path = (data.get("tool_input") or {}).get("file_path")
    if not active or not file_path:
        return None
    other = target_mod(file_path, project, workspace_mods(project))
    if other is None or other.lower() == active.lower():
        return None
    return (
        f"Blocked by /dayz-scope-mod: the active scope is {active}, and this edit targets "
        f"the mod {other} ({file_path}). Edit only files of {active} (workspace/{active}/, "
        f"P:\\{active}\\). If {other} really needs this change, ask the user to run "
        f"/dayz-scope-mod {other} or /dayz-scope-mod --clear first."
    )


def shadowed_by_project() -> bool:
    """True when this is the plugin copy and the project has its own copy of the hook.

    A clone with the agentic-z plugin enabled wires each hook twice: once from
    .claude/settings.json and once from the plugin's hooks.json. The plugin
    copy then steps aside so the project copy runs alone.
    """
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project:
        return False
    here = Path(__file__).resolve()
    root = Path(project).resolve()
    if here.is_relative_to(root):
        return False
    return (root / "hooks" / here.name).is_file()


def main() -> int:
    if shadowed_by_project():
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
        reason = decide(data, project)
    except Exception:  # a guard bug must not block unrelated edits
        return 0
    if reason:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
