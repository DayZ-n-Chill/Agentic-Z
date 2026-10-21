"""Tests for the PreToolUse /dayz-scope-mod guard (scope_guard.py)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "scope_guard.py"


def _project(tmp_path: Path, active: str | None = "MyVest", mods=("MyVest", "OtherMod", ".git")) -> Path:
    for m in mods:
        (tmp_path / "workspace" / m).mkdir(parents=True)
    if active:
        state = tmp_path / ".claude" / "local-memory" / "dayz-active-scope.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({"active_mod": active, "denied_rules": []}), encoding="utf-8")
    return tmp_path


def _run(project: Path, file_path: str, tool: str = "Edit", env_project: bool = True) -> subprocess.CompletedProcess:
    payload = {
        "session_id": "s",
        "cwd": str(project),
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": file_path, "content": "x"},
    }
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if env_project:
        env["CLAUDE_PROJECT_DIR"] = str(project)
    return subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=30
    )


def _denied(r: subprocess.CompletedProcess) -> str | None:
    assert r.returncode == 0
    if not r.stdout:
        return None
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert out["permissionDecision"] == "deny"
    return out["permissionDecisionReason"]


def test_blocks_other_mod_in_workspace(tmp_path):
    p = _project(tmp_path)
    reason = _denied(_run(p, str(p / "workspace" / "OtherMod" / "config.cpp")))
    assert reason and "active scope is MyVest" in reason and "OtherMod" in reason
    assert "/dayz-scope-mod --clear" in reason


def test_blocks_mod_folder_created_after_scoping(tmp_path):
    p = _project(tmp_path)
    assert _denied(_run(p, str(p / "workspace" / "BrandNew" / "config.cpp"), tool="Write"))


@pytest.mark.parametrize("rel", [r"workspace\MyVest\config.cpp", r"workspace\myvest\data\x.rvmat", r"workspace\README.md", r"docs\notes.md"])
def test_allows_active_mod_and_non_mod_paths(tmp_path, rel):
    p = _project(tmp_path)
    assert _denied(_run(p, str(p / rel))) is None


@pytest.mark.parametrize(
    "path, blocked",
    [
        (r"P:\OtherMod\config.cpp", True),
        (r"p:/othermod/scripts/4_World/x.c", True),
        ("/p/OtherMod/config.cpp", True),
        (r"P:\Mods\@OtherMod\Addons\OtherMod.pbo", True),
        (r"P:\MyVest\config.cpp", False),
        (r"P:\DZ\data\config.cpp", False),  # vanilla data, not a mod in workspace/
        (r"P:\Mods\@CF\Addons\x.pbo", False),
    ],
)
def test_p_drive_paths(tmp_path, path, blocked):
    p = _project(tmp_path)
    assert (_denied(_run(p, path)) is not None) is blocked


def test_no_scope_means_no_output(tmp_path):
    p = _project(tmp_path, active=None)
    assert _denied(_run(p, str(p / "workspace" / "OtherMod" / "config.cpp"))) is None


def test_falls_back_to_cwd_without_project_env(tmp_path):
    p = _project(tmp_path)
    assert _denied(_run(p, str(p / "workspace" / "OtherMod" / "x.c"), env_project=False))


@pytest.mark.parametrize("stdin", ["", "garbage", json.dumps({"tool_input": None})])
def test_bad_input_never_blocks(stdin):
    r = subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, text=True, timeout=30)
    assert (r.returncode, r.stdout) == (0, "")


def test_corrupt_state_file_never_blocks(tmp_path):
    p = _project(tmp_path)
    (p / ".claude" / "local-memory" / "dayz-active-scope.json").write_text("{not json", encoding="utf-8")
    assert _denied(_run(p, str(p / "workspace" / "OtherMod" / "config.cpp"))) is None
