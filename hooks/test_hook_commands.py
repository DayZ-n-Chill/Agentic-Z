"""The hook commands in hooks/hooks.json and .claude/settings.json find a Python that runs.

Claude Code runs each hook command with a POSIX shell (Git Bash on Windows). A
bare `python` fails on a machine that has only the py launcher, or whose only
`python` is the Microsoft Store alias (it prints a hint and exits 9009), so no
hook would run. Each command therefore tries `python` first and falls back to
`py`, the same way the scripts/ .bat wrappers do.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PREFIX = """P=python; python -c '' >/dev/null 2>&1 || P=py; "$P" """
CONFIGS = {"hooks/hooks.json": "${CLAUDE_PLUGIN_ROOT}", ".claude/settings.json": "$CLAUDE_PROJECT_DIR"}
HOOKS = ("paste_router.py", "scope_guard.py", "edit_check.py")
PROMPT = {"session_id": "s", "prompt": "can you work on https://github.com/Owner/MyVest?"}
def _posix_shell() -> str | None:
    """The shell Claude Code runs hook commands with: Git Bash on Windows, bash elsewhere.

    On Windows a bare `bash` on PATH is often C:\\Windows\\System32\\bash.exe (WSL), which
    does not see the Windows PATH or environment, so look for Git Bash the way Claude Code does.
    """
    if os.name != "nt":
        return shutil.which("bash")
    if os.environ.get("CLAUDE_CODE_GIT_BASH_PATH"):
        return os.environ["CLAUDE_CODE_GIT_BASH_PATH"]
    git = shutil.which("git")
    for folder in Path(git).resolve().parents if git else ():
        if (folder / "bin" / "bash.exe").is_file():
            return str(folder / "bin" / "bash.exe")
    return None


BASH = _posix_shell()


def _commands(config: str) -> list[str]:
    events = json.loads((REPO / config).read_text(encoding="utf-8"))["hooks"]
    return [h["command"] for groups in events.values() for g in groups for h in g["hooks"]]


def _hook_command(config: str, hook: str) -> str:
    found = [c for c in _commands(config) if f"/hooks/{hook}" in c]
    assert len(found) == 1, found
    return found[0]


@pytest.mark.parametrize("config", CONFIGS)
def test_every_python_command_falls_back_to_py(config):
    for command in _commands(config):
        if ".py" in command:
            assert command.startswith(PREFIX), command


@pytest.mark.parametrize("config, root", CONFIGS.items())
@pytest.mark.parametrize("hook", HOOKS)
def test_hook_command_runs_the_repo_hook(config, root, hook):
    assert _hook_command(config, hook) == f'{PREFIX}"{root}/hooks/{hook}"'


def _shim(folder: Path, name: str, body: str) -> None:
    path = folder / name
    path.write_text(f"#!/bin/sh\necho {name} >> '{(folder / 'calls.log').as_posix()}'\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


REAL = f'exec "{Path(sys.executable).as_posix()}" "$@"'
STORE_ALIAS = "echo 'Python was not found; run without arguments to install from the Microsoft Store'; exit 9009"
MACHINES = {
    "only-py": {"py": REAL},
    "store-alias-and-py": {"python": STORE_ALIAS, "py": REAL},
    "python": {"python": REAL, "py": "exit 7"},
}


def _run(command: str, env: dict, stdin: dict) -> subprocess.CompletedProcess:
    return subprocess.run([BASH, "-c", command], input=json.dumps(stdin).encode("utf-8"), capture_output=True,
                          env=env, timeout=60)


@pytest.mark.skipif(BASH is None, reason="Claude Code runs hook commands with a POSIX shell (Git Bash on Windows)")
@pytest.mark.parametrize("machine", MACHINES)
@pytest.mark.parametrize("config", CONFIGS)
@pytest.mark.parametrize("hook", HOOKS)
def test_hook_runs_on_every_machine(tmp_path, config, hook, machine):
    shims = tmp_path / "bin"
    shims.mkdir()
    for name, body in MACHINES[machine].items():
        _shim(shims, name, body)
    project = tmp_path / "project"
    project.mkdir()
    base = {k: v for k, v in os.environ.items() if k not in ("PATH", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR")}
    if config == "hooks/hooks.json":
        base.update(CLAUDE_PLUGIN_ROOT=str(REPO), CLAUDE_PROJECT_DIR=str(project))
    else:
        base["CLAUDE_PROJECT_DIR"] = str(REPO)
    stdin = PROMPT if hook == "paste_router.py" else {"session_id": "s", "tool_name": "Edit", "tool_input": {}}

    direct = subprocess.run([sys.executable, str(REPO / "hooks" / hook)], input=json.dumps(stdin).encode("utf-8"),
                            capture_output=True, env=base, timeout=60)
    via_shell = _run(_hook_command(config, hook), {**base, "PATH": str(shims)}, stdin)

    assert via_shell.returncode == 0, via_shell.stderr
    assert via_shell.stdout == direct.stdout  # no alias hint leaks into the hook's JSON
    if hook == "paste_router.py":
        assert json.loads(via_shell.stdout)["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    calls = (shims / "calls.log").read_text(encoding="utf-8").split()
    assert calls[-1] == ("python" if machine == "python" else "py")
