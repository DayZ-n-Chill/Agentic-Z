"""The plugin copy of each hook steps aside when the project has its own copy.

A clone with the agentic-z plugin enabled wires every hook twice: once from
.claude/settings.json ($CLAUDE_PROJECT_DIR) and once from hooks/hooks.json
(${CLAUDE_PLUGIN_ROOT}). Only the project copy may answer, or each prompt and
each edit gets the same context or report twice.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HOOKS = ["paste_router.py", "edit_check.py", "scope_guard.py"]

BROKEN_CONFIG = "class CfgPatches\n{\n\tclass MyVest\n\t{\n\t\tunits[] = {}\n\t};\n};\n"


def _setup(project: Path, hook: str, mod: str = "MyVest", other: str = "OtherMod") -> dict:
    """Make the project state that makes `hook` answer, and return its hook input."""
    if hook == "paste_router.py":
        return {"prompt": f"can you work on https://github.com/Owner/{mod}?"}
    if hook == "edit_check.py":
        cfg = project / "workspace" / mod / "config.cpp"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(BROKEN_CONFIG, encoding="utf-8")
        return {"tool_name": "Edit", "tool_input": {"file_path": str(cfg)}}
    for m in (mod, other):
        (project / "workspace" / m).mkdir(parents=True)
        (project / "workspace" / m / "config.cpp").write_text("", encoding="utf-8")  # marks the folder as a mod
    state = project / ".claude" / "local-memory" / "dayz-active-scope.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"active_mod": mod, "denied_rules": []}), encoding="utf-8")
    return {"tool_name": "Edit", "tool_input": {"file_path": str(project / "workspace" / other / "a.c")}}


EVENTS = {"paste_router.py": "UserPromptSubmit", "scope_guard.py": "PreToolUse", "edit_check.py": "PostToolUse"}


def _wire(project: Path, hooks: list[str]) -> None:
    """Write .claude/settings.json wiring `hooks` from $CLAUDE_PROJECT_DIR, as the repo's own settings do."""
    events: dict = {}
    for hook in hooks:
        command = f'python "$CLAUDE_PROJECT_DIR/hooks/{hook}"'
        events.setdefault(EVENTS[hook], []).append({"hooks": [{"type": "command", "command": command}]})
    settings = project / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"hooks": events}, indent=2), encoding="utf-8")


def test_wire_matches_the_repo_settings():
    # the fixture must wire hooks the same way the shipped .claude/settings.json does
    shipped = (HERE.parent / ".claude" / "settings.json").read_text(encoding="utf-8")
    for hook in HOOKS:
        assert f'python \\"$CLAUDE_PROJECT_DIR/hooks/{hook}\\"' in shipped


def _run(script: Path, project: Path, payload: dict) -> subprocess.CompletedProcess:
    """Run a hook the way Claude Code does: UTF-8 JSON on stdin, non-ASCII left unescaped."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    payload = {"session_id": "s", "cwd": str(project), **payload}
    done = subprocess.run([sys.executable, str(script)], input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          capture_output=True, env=env, timeout=30)
    done.stdout = done.stdout.decode("utf-8", "replace")
    return done


@pytest.mark.parametrize("names", [("project", "MyVest", "OtherMod"), ("projékt Ünï", "MyVëst", "ÖtherMöd")],
                         ids=["ascii", "non-ascii"])
@pytest.mark.parametrize("hook", HOOKS)
def test_plugin_copy_is_silent_when_the_project_has_the_hook(tmp_path, hook, names):
    folder, mod, other = names
    project = tmp_path / folder
    project.mkdir()
    plugin = tmp_path / "plugin" / "hooks"
    plugin.mkdir(parents=True)
    plugin_copy = Path(shutil.copy(HERE / hook, plugin / hook))
    payload = _setup(project, hook, mod, other)

    alone = _run(plugin_copy, project, payload)  # plugin only: the plugin copy must still work
    assert alone.returncode == 0 and alone.stdout.strip()
    answer = json.dumps(json.loads(alone.stdout), ensure_ascii=False)
    assert mod in answer or other in answer  # the non-ASCII name survived stdin intact

    (project / "hooks").mkdir()
    shutil.copy(HERE / hook, project / "hooks" / hook)
    unwired = _run(plugin_copy, project, payload)  # hooks/<name> kept but not wired: nothing else would check
    assert unwired.returncode == 0 and unwired.stdout == alone.stdout

    _wire(project, [h for h in HOOKS if h != hook])  # settings.json wires the other hooks, not this one
    dropped = _run(plugin_copy, project, payload)
    assert dropped.returncode == 0 and dropped.stdout == alone.stdout

    _wire(project, HOOKS)
    shadowed = _run(plugin_copy, project, payload)
    assert shadowed.returncode == 0 and shadowed.stdout == ""

    project_copy = _run(project / "hooks" / hook, project, payload)  # the project copy answers once
    assert project_copy.returncode == 0 and project_copy.stdout.strip()


def _load(hook: str):
    name = f"_shadow_{Path(hook).stem}"
    spec = importlib.util.spec_from_file_location(name, HERE / hook)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look the module up while the class is built
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("hook", HOOKS)
def test_a_failing_shadow_check_exits_0_silently(tmp_path, hook, monkeypatch, capsys):
    module = _load(hook)
    payload = _setup(tmp_path, hook)

    def boom():
        raise OSError("bad project path")

    monkeypatch.setattr(module, "shadowed_by_project", boom)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode("utf-8")), encoding="utf-8"))
    code = module.main([]) if hook == "edit_check.py" else module.main()
    assert code == 0
    assert capsys.readouterr().out == ""
