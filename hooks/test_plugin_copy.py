"""The plugin copy of each hook steps aside when the project has its own copy.

A clone with the agentic-z plugin enabled wires every hook twice: once from
.claude/settings.json ($CLAUDE_PROJECT_DIR) and once from hooks/hooks.json
(${CLAUDE_PLUGIN_ROOT}). Only the project copy may answer, or each prompt and
each edit gets the same context or report twice.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

BROKEN_CONFIG = "class CfgPatches\n{\n\tclass MyVest\n\t{\n\t\tunits[] = {}\n\t};\n};\n"


def _setup(project: Path, hook: str) -> dict:
    """Make the project state that makes `hook` answer, and return its hook input."""
    if hook == "paste_router.py":
        return {"prompt": "can you work on https://github.com/Owner/MyVest?"}
    if hook == "edit_check.py":
        cfg = project / "workspace" / "MyVest" / "config.cpp"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(BROKEN_CONFIG, encoding="utf-8")
        return {"tool_name": "Edit", "tool_input": {"file_path": str(cfg)}}
    for mod in ("MyVest", "OtherMod"):
        (project / "workspace" / mod).mkdir(parents=True)
    state = project / ".claude" / "local-memory" / "dayz-active-scope.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"active_mod": "MyVest", "denied_rules": []}), encoding="utf-8")
    return {"tool_name": "Edit", "tool_input": {"file_path": str(project / "workspace" / "OtherMod" / "a.c")}}


def _run(script: Path, project: Path, payload: dict) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    payload = {"session_id": "s", "cwd": str(project), **payload}
    return subprocess.run([sys.executable, str(script)], input=json.dumps(payload), capture_output=True,
                          text=True, env=env, timeout=30)


@pytest.mark.parametrize("hook", ["paste_router.py", "edit_check.py", "scope_guard.py"])
def test_plugin_copy_is_silent_when_the_project_has_the_hook(tmp_path, hook):
    project = tmp_path / "project"
    project.mkdir()
    plugin = tmp_path / "plugin" / "hooks"
    plugin.mkdir(parents=True)
    plugin_copy = Path(shutil.copy(HERE / hook, plugin / hook))
    payload = _setup(project, hook)

    alone = _run(plugin_copy, project, payload)  # plugin only: the plugin copy must still work
    assert alone.returncode == 0 and alone.stdout.strip()

    (project / "hooks").mkdir()
    shutil.copy(HERE / hook, project / "hooks" / hook)
    shadowed = _run(plugin_copy, project, payload)
    assert shadowed.returncode == 0 and shadowed.stdout == ""

    project_copy = _run(project / "hooks" / hook, project, payload)  # the project copy answers once
    assert project_copy.returncode == 0 and project_copy.stdout.strip()
