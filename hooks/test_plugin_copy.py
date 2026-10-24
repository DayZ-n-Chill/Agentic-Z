"""The plugin copy of each hook steps aside when the project has its own copy.

A clone with the agentic-z plugin enabled wires every hook twice: once from
.claude/settings.json ($CLAUDE_PROJECT_DIR) and once from hooks/hooks.json
(${CLAUDE_PLUGIN_ROOT}). Only the project copy may answer, or each prompt and
each edit gets the same context or report twice.

Project wiring is any settings command naming hooks/<name>, with forward or
back slashes, that is not the plugin-root command. A copy that sits anywhere
under CLAUDE_PROJECT_DIR is by design the project's own copy and always
answers, so the project copy can never silence itself.
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


def _wire(project: Path, hooks: list[str], settings_name: str = "settings.json") -> None:
    """Write .claude/<settings_name> wiring `hooks` from $CLAUDE_PROJECT_DIR, as the repo's own settings do."""
    events: dict = {}
    for hook in hooks:
        command = f"""P=python; python -c '' >/dev/null 2>&1 || P=py; "$P" "$CLAUDE_PROJECT_DIR/hooks/{hook}\""""
        events.setdefault(EVENTS[hook], []).append({"hooks": [{"type": "command", "command": command}]})
    settings = project / ".claude" / settings_name
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"hooks": events}, indent=2), encoding="utf-8")


def test_wire_matches_the_repo_settings():
    # the fixture must wire hooks the same way the shipped .claude/settings.json does
    shipped = json.loads((HERE.parent / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [h["command"] for groups in shipped["hooks"].values() for g in groups for h in g["hooks"]]
    for hook in HOOKS:
        assert f"""P=python; python -c '' >/dev/null 2>&1 || P=py; "$P" "$CLAUDE_PROJECT_DIR/hooks/{hook}\"""" in commands


def _plugin_command(hook: str) -> str:
    return f"""P=python; python -c '' >/dev/null 2>&1 || P=py; "$P" "${{CLAUDE_PLUGIN_ROOT}}/hooks/{hook}\""""


def test_plugin_manifest_wires_each_hook_from_the_plugin_root():
    # the plugin side: hooks/hooks.json runs each hook through ${CLAUDE_PLUGIN_ROOT} for its event
    manifest = json.loads((HERE / "hooks.json").read_text(encoding="utf-8"))
    for hook in HOOKS:
        commands = [h["command"] for g in manifest["hooks"][EVENTS[hook]] for h in g["hooks"]]
        assert _plugin_command(hook) in commands


def _run(script: Path, project: Path, payload: dict, project_dir: bool = True) -> subprocess.CompletedProcess:
    """Run a hook the way Claude Code does: UTF-8 JSON on stdin, non-ASCII left unescaped."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8", "CLAUDE_PROJECT_DIR")}
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = str(project)
    payload = {"session_id": "s", "cwd": str(project), **payload}
    done = subprocess.run([sys.executable, str(script)], input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          capture_output=True, env=env, timeout=30)
    done.stdout = done.stdout.decode("utf-8", "replace")
    return done


@pytest.mark.parametrize("names", [("project", "MyVest", "OtherMod"), ("projékt Ünï", "MyVëst", "ÖtherMöd")],
                         ids=["ascii", "non-ascii"])
@pytest.mark.parametrize("settings_name", ["settings.json", "settings.local.json"])
@pytest.mark.parametrize("hook", HOOKS)
def test_plugin_copy_is_silent_when_the_project_has_the_hook(tmp_path, hook, settings_name, names):
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

    _wire(project, [h for h in HOOKS if h != hook], settings_name)  # the settings wire the other hooks, not this one
    dropped = _run(plugin_copy, project, payload)
    assert dropped.returncode == 0 and dropped.stdout == alone.stdout

    _wire(project, HOOKS, settings_name)  # either settings file is enough to shadow the plugin copy
    shadowed = _run(plugin_copy, project, payload)
    assert shadowed.returncode == 0 and shadowed.stdout == ""

    project_copy = _run(project / "hooks" / hook, project, payload)  # the project copy answers once
    assert project_copy.returncode == 0 and project_copy.stdout.strip()


@pytest.mark.parametrize("hook", HOOKS)
def test_backslash_project_command_shadows_the_plugin_copy(tmp_path, hook):
    # a hand-written Windows settings.local.json may name the project hook with backslashes and no
    # $CLAUDE_PROJECT_DIR; that still counts as project wiring, or every answer would show twice
    project = tmp_path / "project"
    project.mkdir()
    plugin = tmp_path / "plugin" / "hooks"
    plugin.mkdir(parents=True)
    plugin_copy = Path(shutil.copy(HERE / hook, plugin / hook))
    payload = _setup(project, hook)
    (project / "hooks").mkdir()
    shutil.copy(HERE / hook, project / "hooks" / hook)
    command = "py " + str(project).replace("/", "\\") + "\\hooks\\" + hook
    assert "/" not in command and "$CLAUDE_PROJECT_DIR" not in command
    group = {"hooks": [{"type": "command", "command": command}]}
    settings = project / ".claude" / "settings.local.json"
    settings.parent.mkdir(parents=True, exist_ok=True)  # the scope_guard setup already made .claude/
    settings.write_text(json.dumps({"hooks": {EVENTS[hook]: [group]}}), encoding="utf-8")

    shadowed = _run(plugin_copy, project, payload)
    assert shadowed.returncode == 0 and shadowed.stdout == ""


@pytest.mark.parametrize("hook", HOOKS)
def test_a_copy_inside_the_project_folder_always_answers(tmp_path, hook):
    # Intended: any copy under CLAUDE_PROJECT_DIR counts as the project's own copy and never steps
    # aside, even when hooks/<name> exists and is wired. Otherwise the project copy would shadow
    # itself, and a plugin installed inside the project (or the plugin's own source repo opened as
    # the project) would leave no copy answering.
    project = tmp_path / "project"
    project.mkdir()
    payload = _setup(project, hook)
    (project / "hooks").mkdir()
    shutil.copy(HERE / hook, project / "hooks" / hook)
    _wire(project, HOOKS)
    nested = project / ".claude" / "plugins" / "agentic-z" / "hooks"
    nested.mkdir(parents=True)
    nested_copy = Path(shutil.copy(HERE / hook, nested / hook))

    answered = _run(nested_copy, project, payload)
    assert answered.returncode == 0
    assert ANSWERS[hook](json.loads(answered.stdout))


def _settings(project: Path, text: str) -> None:
    settings = project / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(text, encoding="utf-8")


def _plugin_root_wiring(project: Path, hook: str) -> None:
    group = {"hooks": [{"type": "command", "command": _plugin_command(hook)}]}
    _settings(project, json.dumps({"hooks": {EVENTS[hook]: [group]}}))


# Project states where the project copy cannot answer, so the plugin copy must.
UNSHADOWED = {
    # the shipped settings wire the project hook, but hooks/ was deleted: that command fails
    "wired-without-hooks-dir": (False, lambda project, hook: _wire(project, HOOKS), True),
    "invalid-json": (True, lambda project, hook: _settings(project, "{not json"), True),
    "hooks-not-a-dict": (True, lambda project, hook: _settings(project, json.dumps({"hooks": ["x"]})), True),
    "settings-not-a-dict": (True, lambda project, hook: _settings(project, json.dumps(["hooks"])), True),
    "groups-and-entries-malformed": (True, lambda project, hook: _settings(project, json.dumps(
        {"hooks": {"PreToolUse": "x", "PostToolUse": ["x", {"hooks": ["x", {"command": None}]}]}})), True),
    # a settings command naming the plugin's own copy is not project wiring
    "plugin-root-command": (True, _plugin_root_wiring, True),
    # no CLAUDE_PROJECT_DIR: the shadow check cannot find the project, so this copy runs
    "no-project-dir": (True, lambda project, hook: _wire(project, HOOKS), False),
}


@pytest.mark.parametrize("case", list(UNSHADOWED))
@pytest.mark.parametrize("hook", HOOKS)
def test_plugin_copy_answers_when_the_project_copy_cannot(tmp_path, hook, case):
    keep_hooks_dir, make_settings, project_dir = UNSHADOWED[case]
    project = tmp_path / "project"
    project.mkdir()
    plugin = tmp_path / "plugin" / "hooks"
    plugin.mkdir(parents=True)
    plugin_copy = Path(shutil.copy(HERE / hook, plugin / hook))
    payload = _setup(project, hook)
    alone = _run(plugin_copy, project, payload)
    assert alone.returncode == 0 and alone.stdout.strip()

    if keep_hooks_dir:
        (project / "hooks").mkdir()
        shutil.copy(HERE / hook, project / "hooks" / hook)
    make_settings(project, hook)
    answered = _run(plugin_copy, project, payload, project_dir=project_dir)
    assert answered.returncode == 0
    assert ANSWERS[hook](json.loads(answered.stdout))


def _load(hook: str):
    name = f"_shadow_{Path(hook).stem}"
    spec = importlib.util.spec_from_file_location(name, HERE / hook)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look the module up while the class is built
    spec.loader.exec_module(module)
    return module


ANSWERS = {
    "paste_router.py": lambda out: out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit",
    "scope_guard.py": lambda out: out["hookSpecificOutput"]["permissionDecision"] == "deny",
    "edit_check.py": lambda out: out["decision"] == "block",
}


@pytest.mark.parametrize("hook", HOOKS)
def test_a_failing_shadow_check_still_runs_the_hook(tmp_path, hook, monkeypatch, capsys):
    # a plugin-only install must keep checking when the shadow check itself breaks
    module = _load(hook)
    payload = _setup(tmp_path, hook)

    def boom():
        raise OSError("bad project path")

    monkeypatch.setattr(module, "shadowed_by_project", boom)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode("utf-8")), encoding="utf-8"))
    code = module.main([]) if hook == "edit_check.py" else module.main()
    assert code == 0
    assert ANSWERS[hook](json.loads(capsys.readouterr().out))
