"""Repo-wide checks: agent team and plugin manifest, the references in agents, skills and packs,
no-token .bat wrappers, the knowledge-pack index and citations (and, with P:\\ mounted, that each
cited vanilla line exists and holds a symbol the citing line names), the preflight gate list, the Tier 1 files and the panel's skill scripts.

Run with: py -m pytest scripts/dev/test_repo_integrity.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO / ".claude" / "agents"
SKILLS_DIR = REPO / ".claude" / "skills"
PLUGIN = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

# Skills that maintain the template repo itself; plugin installs don't need them.
TEMPLATE_ONLY_SKILLS = {"agentic-z-update", "clean-repo", "docs-sync", "sync-skills"}

AGENT_FILES = sorted(AGENTS_DIR.glob("*.md"))
AGENT_NAMES = {p.stem for p in AGENT_FILES}


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    block = text.split("---", 2)[1]
    out = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip().strip('"')
    return out


def _tools(path: Path) -> list[str]:
    raw = _frontmatter(path).get("tools", "")
    return [t.strip() for t in raw.split(",") if t.strip()]


def test_every_agent_is_registered_in_the_plugin():
    registered = {Path(p).stem for p in PLUGIN["agents"]}
    assert registered == AGENT_NAMES, (
        f"agents missing from .claude-plugin/plugin.json: {sorted(AGENT_NAMES - registered)}; "
        f"registered but not on disk: {sorted(registered - AGENT_NAMES)}"
    )


def test_every_user_skill_is_registered_in_the_plugin():
    registered = {Path(p).name for p in PLUGIN["skills"]}
    on_disk = {p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")}
    assert registered == on_disk - TEMPLATE_ONLY_SKILLS, (
        f"every user skill must be registered in .claude-plugin/plugin.json; missing: "
        f"{sorted(on_disk - TEMPLATE_ONLY_SKILLS - registered)}; registered but not on disk: "
        f"{sorted(registered - (on_disk - TEMPLATE_ONLY_SKILLS))}"
    )


def test_registered_paths_exist():
    for rel in PLUGIN["agents"] + PLUGIN["skills"]:
        assert (REPO / rel).exists(), rel


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_agent_name_matches_filename(path):
    assert _frontmatter(path)["name"] == path.stem, f"agent name must match its filename: {path.name}"


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_search_tools_work_in_clones_and_plugin_installs(path):
    # A clone exposes the server as mcp__dayz-rag__*, a plugin install as
    # mcp__plugin_agentic-z_dayz-rag__*. Unknown names are dropped silently,
    # so an agent needs both to reach search in either setup.
    tools = set(_tools(path))
    for tool in tools:
        if tool.startswith("mcp__dayz-rag__"):
            assert tool.replace("mcp__dayz-rag__", "mcp__plugin_agentic-z_dayz-rag__") in tools, (
                f"{path.stem}: every clone search tool needs its plugin twin: {tool}"
            )
        if tool.startswith("mcp__plugin_agentic-z_dayz-rag__"):
            assert tool.replace("mcp__plugin_agentic-z_dayz-rag__", "mcp__dayz-rag__") in tools, (
                f"{path.stem}: every plugin search tool needs its clone twin: {tool}"
            )


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_rag_agents_fall_back_to_rag_after_failed_greps(path):
    # The wiki (team.md) says every RAG-equipped specialist turns to RAG search
    # after two or three failed greps; an agent that drops that fallback keeps
    # grepping blindly.
    if "mcp__dayz-rag__search_dayz_source" not in _tools(path):
        return
    text = path.read_text(encoding="utf-8")
    assert "after two or three failed greps" in text, (
        f"{path.stem}: Search line must use RAG after two or three failed greps"
    )


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_agents_have_no_machine_specific_paths(path):
    # P:\ is the DayZ Tools work drive every user mounts; any other drive letter
    # is one person's machine.
    text = path.read_text(encoding="utf-8")
    found = re.findall(r"\b[A-OQ-Z]:\\", text)
    assert not found, f"{path.name} has machine-specific drive paths {found}; only P:\\ is shared"


# Every file an agent follows: the agents, the skills and the knowledge packs.
# A dead script, agent or skill name in any of them sends a user nowhere.
REF_FILES = sorted(
    set(AGENT_FILES)
    | set(SKILLS_DIR.glob("*/SKILL.md"))
    | set((SKILLS_DIR / "_shared").rglob("*.md"))
    | set(SKILLS_DIR.glob("*/reference*/**/*.md"))
)


def _ref_id(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


@pytest.mark.parametrize("path", REF_FILES, ids=_ref_id)
def test_referenced_repo_files_exist(path):
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r"(?:\.claude/(?:skills|agents|mcp)|scripts)/[\w./-]+\.(?:md|py|bat)", text):
        assert (REPO / ref).exists(), f"{_ref_id(path)} points at missing {ref}"


@pytest.mark.parametrize("path", REF_FILES, ids=_ref_id)
def test_referenced_agents_exist(path):
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r"`((?:dayz|figma)-[a-z-]+)`", text):
        if ref == "dayz-rag":
            continue
        assert ref in AGENT_NAMES or (SKILLS_DIR / ref).exists(), f"{_ref_id(path)} names unknown agent {ref}"


@pytest.mark.parametrize("path", REF_FILES, ids=_ref_id)
def test_referenced_slash_skills_exist(path):
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r"(?<![\w/.])/((?:dayz|agentic|docs|sync|clean)-[a-z0-9-]+)", text):
        assert (SKILLS_DIR / ref / "SKILL.md").exists(), f"{_ref_id(path)} names unknown skill /{ref}"


def _lead_workers():
    text = (AGENTS_DIR / "dayz-lead.md").read_text(encoding="utf-8")
    section = text.split("## Your workers", 1)[1].split("\n## ", 1)[0]
    table = "\n".join(line for line in section.splitlines() if line.startswith("|"))
    assert table, "dayz-lead.md must have a workers table under ## Your workers"
    return set(re.findall(r"`([a-z-]+)`", table))


def test_lead_workers_are_agents():
    for ref in _lead_workers():
        assert ref in AGENT_NAMES, f"lead lists unknown worker {ref}"


# Gatekeepers check and report; they must not be able to change what they judge.
READ_ONLY_GATES = {
    "dayz-mod-reviewer",
    "dayz-mod-debugger",
    "dayz-build-checker",
    "dayz-ingame-tester",
    "dayz-layout-validator",
}

# Agents a lead never starts: they plan, route or run the leads.
NOT_LEAD_WORKERS = {"dayz-lead", "dayz-orchestrator", "dayz-router", "dayz-mod-architect"}


def test_every_dayz_worker_is_in_the_lead_table():
    workers = _lead_workers()
    for name in sorted(AGENT_NAMES):
        if name.startswith("dayz-") and name not in READ_ONLY_GATES | NOT_LEAD_WORKERS:
            assert name in workers, f"{name} is missing from dayz-lead's worker table"


def _docs_routing_agents(text: str) -> set[str]:
    section = text.split("## Superpowers ↔ DayZ specialist routing", 1)[1].split("\n## ", 1)[0]
    table = "\n".join(line for line in section.splitlines() if line.startswith("|"))
    assert table, "docs/dayz-modding.md must have a routing table under its Superpowers routing heading"
    return set(re.findall(r"`([a-z-]+)`", table))


def test_every_lead_worker_and_gate_is_in_the_docs_routing_table():
    # Superpowers workflows dispatch from this table, so a worker missing here is never routed to.
    routed = _docs_routing_agents((REPO / "docs" / "dayz-modding.md").read_text(encoding="utf-8"))
    for name in sorted(_lead_workers() | READ_ONLY_GATES):
        assert name in routed, f"{name} is missing from the routing table in docs/dayz-modding.md"


def test_docs_routing_check_reads_only_the_routing_table():
    text = "## Superpowers ↔ DayZ specialist routing\n\n| a | b |\n|---|---|\n| x | `dayz-x` |\n\n## Next\n| y | `dayz-y` |\n"
    assert _docs_routing_agents(text) == {"dayz-x"}


ROUTE = json.loads((SKILLS_DIR / "dayz-route" / "rules.json").read_text(encoding="utf-8"))

# Lead workers reached only through another agent, never straight from /dayz-route.
NOT_ROUTE_TARGETS = {"figma-to-dayz-layout"}  # stage 2 of the Figma pipeline, started by figma-node-normalizer


def test_every_lead_worker_is_a_route_target():
    # /dayz-route and dayz-router send work only to the targets in rules.json.
    for name in sorted(_lead_workers() - NOT_ROUTE_TARGETS):
        assert name in ROUTE["targets"], f"{name} is missing from the targets in .claude/skills/dayz-route/rules.json"


# Lead workers that own no mod source file, so the debugger never names them as the Owner.
NOT_DEBUGGER_OWNERS = {
    "dayz-build-engineer",  # builds and launches; environment faults go to dayz-orchestrator
    "figma-node-normalizer",  # Figma pipeline; dayz-ui-specialist owns the .layout afterwards
    "figma-to-dayz-layout",
}


def _debugger_owners(text: str) -> set[str]:
    section = text.split("## Who fixes what", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"`([a-z-]+)`", section))


def test_every_file_owning_worker_is_a_debugger_owner():
    owners = _debugger_owners((AGENTS_DIR / "dayz-mod-debugger.md").read_text(encoding="utf-8"))
    for name in sorted(_lead_workers() - NOT_DEBUGGER_OWNERS):
        assert name in owners, f"{name} is missing from 'Who fixes what' in dayz-mod-debugger.md"


def test_debugger_owner_check_reads_only_its_section():
    text = "## Who fixes what\n\n`dayz-x` for files.\n\n## Report\n**Owner:** `dayz-y`\n"
    assert _debugger_owners(text) == {"dayz-x"}


def _explicit_tools(path: Path) -> set[str]:
    # With no `tools:` line a subagent inherits every tool, Edit and Write
    # included, so a read-only role must list its tools.
    tools = set(_tools(path))
    assert tools, f"{path.name} has no tools: line, so it inherits Edit and Write"
    return tools


@pytest.mark.parametrize("name", sorted(READ_ONLY_GATES))
def test_gates_cannot_edit(name):
    path = AGENTS_DIR / f"{name}.md"
    write_tools = _explicit_tools(path) & {"Edit", "Write", "NotebookEdit"}
    assert not write_tools, f"gate {name} must not change what it judges, but has {sorted(write_tools)}"
    # Setting `memory` auto-enables Write and Edit for any path.
    assert "memory" not in _frontmatter(path), f"gate {name} sets memory, which enables Write and Edit"


# Roles that run others or only diagnose, and write nothing themselves. Setting
# `memory` auto-enables Read, Write and Edit, so these must also carry no memory.
NO_WRITE_ROLES = {"dayz-lead", "dayz-physics-specialist"}


@pytest.mark.parametrize("name", sorted(NO_WRITE_ROLES))
def test_no_write_roles_have_no_write_tools_or_memory(name):
    path = AGENTS_DIR / f"{name}.md"
    write_tools = _explicit_tools(path) & {"Edit", "Write", "NotebookEdit"}
    assert not write_tools, f"{name} writes nothing itself, but has {sorted(write_tools)}"
    assert "memory" not in _frontmatter(path), f"{name} sets memory, which enables Write and Edit"


def test_a_role_with_no_tools_line_fails_the_read_only_checks(tmp_path):
    agent = tmp_path / "dayz-gate-x.md"
    agent.write_text("---\nname: dayz-gate-x\ndescription: d\n---\nbody\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="inherits Edit and Write"):
        _explicit_tools(agent)


def test_ingame_tester_matches_gate():
    # dayz-ingame-tester is the fallback for `/dayz-gate ingame`, so its ready line,
    # settle time and client timeout must match the script's defaults.
    agent = (AGENTS_DIR / "dayz-ingame-tester.md").read_text(encoding="utf-8")
    gate = (SKILLS_DIR / "dayz-gate" / "gate.py").read_text(encoding="utf-8")
    ready_re = re.search(r'^DEFAULT_READY_RE = r"(.+)"$', gate, re.M).group(1)
    settle = int(re.search(r"^DEFAULT_SETTLE_S = (\d+)", gate, re.M).group(1))
    timeout = int(re.search(r"^DEFAULT_TIMEOUT_S = (\d+)", gate, re.M).group(1))
    assert 'add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S' in gate, "gate.py --timeout must default to DEFAULT_TIMEOUT_S"
    ready_line = re.search(r"log line matching `([^`]+)`", agent).group(1)
    assert re.search(ready_re, ready_line), "dayz-ingame-tester ready line must match gate.py DEFAULT_READY_RE"
    assert (settle, timeout) == (30, 300), "gate.py settle and timeout defaults must stay 30 s and 300 s, as dayz-ingame-tester states"
    assert "keep reading 30 more seconds" in agent, "dayz-ingame-tester must state the 30 second settle time"
    assert "Give up after five minutes" in agent, "dayz-ingame-tester must state the five minute client timeout"
    # judge_entries: NULL pointer and Can't find lines that don't name the mod never fail.
    assert re.search(r'^MOD_QUALIFIED = \{"null_pointer", "cant_find"\}$', gate, re.M), "gate.py MOD_QUALIFIED must be null_pointer and cant_find"
    assert (
        "A `NULL pointer` or `Can't find` line that names nothing of the mod is never a failure: "
        "report it as a warning when it is not in the vanilla-only run." in agent
    ), "dayz-ingame-tester must state that unqualified NULL pointer and Can't find lines are warnings"
    # A payload-only bundle is deployed under its PBOs' own names, never as <ModName>.pbo, and
    # ingame_session skips the missing --deps error for a bundle (bundle_layout payload).
    assert r"Addons\<ModName>.pbo`" not in agent, "dayz-ingame-tester must not require <ModName>.pbo: a bundle deploys its PBOs under their own names"
    assert r"for a bundle at least one `.pbo`, exists under `P:\Mods\@<ModName>\Addons\`" in agent, "dayz-ingame-tester step 1 must accept any .pbo for a bundle"
    # stop_session stops a session the gate did not start only with --yes; the agent must ask too.
    assert "if not started_by_gate and not rt.confirm(pids):" in gate, "gate.py must stop a session it did not start only on confirm"
    step0 = re.search(r"^0\. .+$", agent, re.M).group(0)
    assert "ask the caller" in step0 and "Don't stop it" in step0, "dayz-ingame-tester step 0 must ask the caller, not stop a session it did not start"
    conv = (SKILLS_DIR / "_shared" / "dayz-conventions.md").read_text(encoding="utf-8")
    config_row = next(l for l in conv.splitlines() if l.startswith("| `conventions/config.md` |"))
    assert "conventions/config.md" in agent and "ingame-tester" in config_row.rsplit("|", 2)[1], "conventions/config.md Read by must list ingame-tester, which cites it"
    session = gate.split("def ingame_session(", 1)[1].split("\ndef ", 1)[0]
    assert "not bundle_layout(mod_dir)[1]" in session, "gate.py ingame_session must exempt a bundle from the missing --deps error"
    assert "A bundle is exempt: when no dependencies are named" in agent, "dayz-ingame-tester must give a bundle the same dependency exemption as gate.py"


def test_build_checker_matches_gate():
    # dayz-build-checker is the fallback for `/dayz-gate build`: lint first, then stop the
    # session and build, and a bundle's payload is checked with /dayz-deploy-pbo.
    agent = (AGENTS_DIR / "dayz-build-checker.md").read_text(encoding="utf-8")
    gate = (SKILLS_DIR / "dayz-gate" / "gate.py").read_text(encoding="utf-8")
    build = gate.split("def gate_build(", 1)[1].split("\ndef ", 1)[0]
    assert build.index("run_lint(") < build.index("stop_session(") < build.index("BUILD_PY"), "gate_build must lint, then stop the session, then build"
    for needle in ("/dayz-lint", "/dayz-deploy-pbo", ".bisign"):
        assert needle in agent, f"dayz-build-checker must mention {needle}"
    assert agent.index("/dayz-lint") < agent.index("/dayz-stop-test") < agent.index("`/dayz-build-pbo <ModName>` succeeds"), (
        "dayz-build-checker must lint, then stop the session, then build, in the same order as gate_build"
    )


def test_build_checker_never_stops_an_unstarted_session_unasked():
    # gate.py stops a DayZDiag session it did not start only with --yes or a terminal yes,
    # because it may be the user's own play session. The fallback agent never launches the
    # game, so every running session is one it did not start: it must report BLOCKED and
    # stop the session only when the user agreed.
    gate = (SKILLS_DIR / "dayz-gate" / "gate.py").read_text(encoding="utf-8")
    stop = gate.split("def stop_session(", 1)[1].split("\ndef ", 1)[0]
    assert "if not started_by_gate and not rt.confirm(pids):" in stop, "gate.py stop_session must ask before stopping a session it did not start"
    agent = (AGENTS_DIR / "dayz-build-checker.md").read_text(encoding="utf-8")
    step = agent.split("\n2. ", 1)[1].split("\n3. ", 1)[0]
    assert "BLOCKED: step 2" in step, "dayz-build-checker step 2 must report BLOCKED for a session it did not start"
    assert "only when the brief or your caller says the user agreed" in step, (
        "dayz-build-checker may run /dayz-stop-test only when the user agreed"
    )
    assert "BLOCKED: step 2" in agent.split("## Report", 1)[1], "dayz-build-checker's report must allow a BLOCKED verdict"


def test_orchestrator_runs_every_gate_mode():
    # The orchestrator gates each wave with /dayz-gate. Every mode gate.py offers must be in its
    # gate step, and the plan files that switch the behavior and visual gates on must be ones
    # the architect writes, at the names the gate reads by default.
    gate = (SKILLS_DIR / "dayz-gate" / "gate.py").read_text(encoding="utf-8")
    modes = re.findall(r'sub\.add_parser\("(\w+)"', gate)
    assert modes == ["build", "ingame", "behavior", "visual"], f"gate.py modes changed: {modes}"
    orchestrator = (AGENTS_DIR / "dayz-orchestrator.md").read_text(encoding="utf-8")
    step = orchestrator.split("5. **Gate the wave.**", 1)[1].split("6. **Next wave.**", 1)[0]
    for mode in modes:
        assert f"`/dayz-gate {mode} <ModName>" in step, f"dayz-orchestrator's gate step must run /dayz-gate {mode}"
    architect = (AGENTS_DIR / "dayz-mod-architect.md").read_text(encoding="utf-8")
    behavior_src = (SKILLS_DIR / "dayz-gate" / "behavior.py").read_text(encoding="utf-8")
    visual_src = (SKILLS_DIR / "dayz-gate" / "visual.py").read_text(encoding="utf-8")
    for source in (behavior_src, visual_src):
        name = re.search(r'^\w+_FILENAME = "([\w.-]+\.json)"', source, re.M).group(1)
        assert f"output/<ModName>-plan/{name}" in step, f"dayz-orchestrator must gate on output/<ModName>-plan/{name}"
        assert f"output/<ModName>-plan/{name}" in architect, f"dayz-mod-architect must write output/<ModName>-plan/{name}"


BAT_FILES = sorted((REPO / "scripts").glob("*/*.bat"))


@pytest.mark.parametrize("path", BAT_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_bat_wrapper_targets_exist(path):
    # Each wrapper runs a script relative to its own folder (%~dp0); a moved or
    # renamed script would break the no-token path silently.
    text = path.read_text(encoding="utf-8", errors="replace")
    for target in re.findall(r'%~dp0([^"\s]+\.(?:py|bat))', text):
        assert (path.parent / target.replace("\\", "/")).resolve().exists(), f"{path.name} runs missing {target}"


SETUP_WRAPPERS = [
    "preflight.bat",
    "workdrive.bat",
    "setup-objectbuilder.bat",
    "statusline.bat",
    "sync-skills.bat",
    "agentic-z-update.bat",
]


@pytest.mark.skipif(sys.platform != "win32", reason="runs cmd.exe")
@pytest.mark.parametrize("has_python", [False, True], ids=["py-only", "python"])
@pytest.mark.parametrize("name", SETUP_WRAPPERS)
def test_setup_wrapper_falls_back_to_py_launcher(name, has_python, tmp_path):
    # A machine with only the py launcher used to get the Store alias (exit 9009)
    # from a bare `python` call. PATH holds only fake launchers and System32.
    # PY must stay inside the wrapper (setlocal), not leak into the caller's terminal.
    for exe in ["py"] + (["python"] if has_python else []):
        (tmp_path / f"{exe}.bat").write_text(f"@echo off\r\necho RAN-{exe} %*\r\n", encoding="ascii")
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    env = {k: v for k, v in os.environ.items() if k.upper() != "PY"}
    env["PATH"] = f"{tmp_path};{system32}"
    bat = REPO / "scripts" / "setup" / name
    line = f'call "{bat}" --help & if defined PY (echo PY-LEAKED) else (echo PY-CLEAN)'
    result = subprocess.run(f'cmd /d /s /c "{line}"', env=env, capture_output=True, text=True, timeout=30)
    launcher = "RAN-python " if has_python else "RAN-py "
    lines = [out.strip() for out in result.stdout.splitlines()]
    assert any(out.startswith(launcher) and out.endswith(".py\" --help") for out in lines), (
        f"{name} output: {result.stdout!r}"
    )
    assert "PY-CLEAN" in lines, f"{name} left PY set in the calling terminal: {result.stdout!r}"


DAYZ_WRAPPERS = sorted(
    p.name for p in (REPO / "scripts" / "dayz").glob("*.bat") if ".py" in p.read_text(encoding="utf-8", errors="replace")
)


@pytest.mark.skipif(sys.platform != "win32", reason="runs cmd.exe")
@pytest.mark.parametrize("has_python", [False, True], ids=["py-only", "python"])
@pytest.mark.parametrize("name", DAYZ_WRAPPERS)
def test_dayz_wrapper_falls_back_to_py_launcher(name, has_python, tmp_path):
    # The scripts\dayz wrappers called bare `python`, so a machine with only the py
    # launcher got the Store alias (exit 9009) while the setup wrappers worked.
    # PATH holds only fake launchers and System32; PY must not leak to the caller.
    for exe in ["py"] + (["python"] if has_python else []):
        (tmp_path / f"{exe}.bat").write_text(f"@echo off\r\necho RAN-{exe} %*\r\n", encoding="ascii")
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    env = {k: v for k, v in os.environ.items() if k.upper() != "PY"}
    env["PATH"] = f"{tmp_path};{system32}"
    bat = REPO / "scripts" / "dayz" / name
    line = f'call "{bat}" --help & if defined PY (echo PY-LEAKED) else (echo PY-CLEAN)'
    result = subprocess.run(f'cmd /d /s /c "{line}"', env=env, capture_output=True, text=True, timeout=30)
    launcher = "RAN-python " if has_python else "RAN-py "
    lines = [out.strip() for out in result.stdout.splitlines()]
    assert any(out.startswith(launcher) and out.endswith(".py\" --help") for out in lines), (
        f"{name} output: {result.stdout!r}"
    )
    assert "PY-CLEAN" in lines, f"{name} left PY set in the calling terminal: {result.stdout!r}"


def test_dayz_wrapper_list_is_complete():
    # Every scripts\dayz wrapper except stop-test.bat (a taskkill .bat, no Python) is covered above.
    assert len(DAYZ_WRAPPERS) == len(list((REPO / "scripts" / "dayz").glob("*.bat"))) - 1


DEV_WRAPPERS = ["evals.bat", "clean-repo.bat", "docs-sync.bat"]


@pytest.mark.skipif(sys.platform != "win32", reason="runs cmd.exe")
@pytest.mark.parametrize("has_python", [False, True], ids=["py-only", "python"])
@pytest.mark.parametrize("name", DEV_WRAPPERS)
def test_dev_wrapper_falls_back_to_py_and_keeps_py_local(name, has_python, tmp_path):
    # evals.bat and clean-repo.bat called bare `python` (Store alias, exit 9009, on a
    # py-only machine); docs-sync.bat had the fallback but no setlocal, so PY leaked
    # into the caller's terminal. PATH holds only fake launchers and System32.
    for exe in ["py"] + (["python"] if has_python else []):
        (tmp_path / f"{exe}.bat").write_text(f"@echo off\r\necho RAN-{exe} %*\r\n", encoding="ascii")
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    env = {k: v for k, v in os.environ.items() if k.upper() != "PY"}
    env["PATH"] = f"{tmp_path};{system32}"
    bat = REPO / "scripts" / "dev" / name
    line = f'call "{bat}" --help & if defined PY (echo PY-LEAKED) else (echo PY-CLEAN)'
    result = subprocess.run(f'cmd /d /s /c "{line}"', env=env, capture_output=True, text=True, timeout=30)
    launcher = "RAN-python " if has_python else "RAN-py "
    lines = [out.strip() for out in result.stdout.splitlines()]
    ran = [out for out in lines if out.startswith(launcher) and out.endswith("--help")]
    assert ran, f"{name} output: {result.stdout!r}"
    assert "PY-CLEAN" in lines, f"{name} left PY set in the calling terminal: {result.stdout!r}"


def test_readme_says_evals_bat_costs_tokens():
    # The intro said every .bat costs no tokens, but evals.bat runs `claude -p` per question.
    readme = (REPO / "scripts" / "README.md").read_text(encoding="utf-8")
    evals_row = next(row for row in readme.splitlines() if row.startswith("| `evals.bat`"))
    assert "Costs tokens" in evals_row, "the evals.bat row must say it costs tokens"
    assert "exception is `evals.bat`" in readme, "the no-token intro must name evals.bat as the exception"


RUNNABLE_WITHOUT_BAT = {"dayz-particles", "dayz-record-correction"}  # reference-only skills, no script


def test_every_runnable_skill_has_a_bat_wrapper():
    wrapped = set()
    for bat in BAT_FILES:
        wrapped.update(re.findall(r"skills\\([a-z0-9-]+)\\", bat.read_text(encoding="utf-8", errors="replace")))
    skills = {p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")}
    assert skills - wrapped - RUNNABLE_WITHOUT_BAT == set(), (
        f"every runnable skill needs a .bat wrapper under scripts/: {sorted(skills - wrapped - RUNNABLE_WITHOUT_BAT)}"
    )


SHARED_DIR = SKILLS_DIR / "_shared"
PACK_INDEX = SHARED_DIR / "README.md"
NOT_PACKS = {"README.md", "dayz-conventions.md"}  # the index itself and the Tier 2 core


def _pack_folders() -> list[Path]:
    folders = [p for p in SHARED_DIR.iterdir() if p.is_dir() and p.name not in {"conventions", "__pycache__"}]
    for folder in list(folders):
        folders += [p for p in folder.rglob("*") if p.is_dir() and p.name != "__pycache__"]
    folders += [p for p in SKILLS_DIR.glob("*/reference*") if p.is_dir()]
    return sorted(folders)


def _pack_files() -> list[Path]:
    files = [p for p in SHARED_DIR.glob("*.md") if p.name not in NOT_PACKS]
    for folder in _pack_folders():
        files += [p for p in folder.glob("*.md") if p.name != "README.md"]
    return sorted(files)


def test_every_pack_is_in_the_index():
    index = PACK_INDEX.read_text(encoding="utf-8")
    listed = set(re.findall(r"`([\w./-]+)`", index))
    for path in _pack_folders() + _pack_files():
        rel = path.relative_to(SKILLS_DIR).as_posix()
        assert rel in listed, f"pack index does not list {rel}"


def test_pack_index_paths_exist():
    index = PACK_INDEX.read_text(encoding="utf-8")
    for ref in re.findall(r"`((?:_shared|dayz-[\w-]+)/[\w./-]+)`", index):
        assert (SKILLS_DIR / ref).exists(), f"pack index names missing {ref}"


# _shared/README.md: "Facts about the game cite the vanilla file on P:\". These files
# hold no game facts of their own (style, answer format, tool notes, repo layout).
CITATION_EXEMPT = {
    "enscript-style.md",              # style guide index; facts live in enscript/references/
    "enscript/integrations/expansion_style.md",  # style for Expansion mods; no vanilla facts
    "answer-formatting.md",           # how to format answers
    "py3d-mlod-notes.md",             # notes on a Python library, not the game
    "conventions/server.md",          # the .server/ test-server layout of this repo
    "dayz-conventions.md",            # environment and workflow rules; facts live in the topic files
    "textures/checking-the-look.md",  # what to look at in Object Builder and in game
}
CITATION_EXEMPT_FOLDERS = {"enscript-style"}  # the style guide's section files
# A citation names a vanilla file, not just the drive: a path with a line
# (P:\scripts\...\x.c:12, x.c:12, config.cpp:40), a file on P:\ (binary .p3d
# and .paa have no lines), or a scripts-relative file such as 3_game/global/game.c.
CITATION_RE = re.compile(
    r"P:[\\/][^\s`]+:\d+|\.c:\d+|config\.cpp:\d+"
    r"|P:[\\/][^\s`]*[\\/][\w.-]+\.\w+"
    r"|\b[1-5]_\w+[/\\][^\s`]*\.c\b"
)


def test_pack_files_cite_vanilla_at_least_once():
    missing = []
    for path in sorted(SHARED_DIR.rglob("*.md")):
        rel = path.relative_to(SHARED_DIR).as_posix()
        if path.name == "README.md" or rel in CITATION_EXEMPT or rel.split("/")[0] in CITATION_EXEMPT_FOLDERS:
            continue
        if not CITATION_RE.search(path.read_text(encoding="utf-8")):
            missing.append(rel)
    assert not missing, f"pack files with no path:line citation of vanilla: {missing}"


# P:\...\file.ext:N or :N-M, with backslashes or forward slashes (the eval questions'
# "verified" fields write P:/DZ/.../config.cpp:822). A cited file must exist and reach the cited line.
CITED_LINE_RE = re.compile(r"(P:[\\/][^\s`:*?\"<>|()]+\.\w+):(\d+)(?:-(\d+))?")

EVAL_QUESTION_FILES = sorted((REPO / "evals" / "questions").glob("*.json"))


def _json_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return [s for v in value for s in _json_strings(v)]
    return []


def _citation_texts():
    """(id, text) for each file whose P: line citations are checked: the reference files,
    the skills' .c files and the eval questions (their JSON strings, unescaped)."""
    for path in REF_FILES + sorted(SKILLS_DIR.rglob("*.c")):
        yield _ref_id(path), path.read_text(encoding="utf-8", errors="replace")
    for path in EVAL_QUESTION_FILES:
        yield _ref_id(path), "\n".join(_json_strings(json.loads(path.read_text(encoding="utf-8"))))


def _missing_cited_lines(text: str, line_count) -> list[str]:
    """Each citation in text whose file is missing (line_count gives None) or ends before the cited line."""
    bad = []
    for m in CITED_LINE_RE.finditer(text):
        count = line_count(m.group(1))
        if count is None or int(m.group(3) or m.group(2)) > count:
            bad.append(f"{m.group(0)} ({'missing' if count is None else f'has {count} lines'})")
    return bad


def test_cited_line_check_reads_forward_slash_citations_and_eval_questions():
    # CITED_LINE_RE matched only P:\..., so the P:/...:N citations in every eval
    # question's "verified" field were never checked against P:.
    counts = {r"P:\scripts\a.c": 10, "P:/DZ/b/config.cpp": 10}
    text = r"P:\scripts\a.c:12, P:/DZ/b/config.cpp:822 (class GlowPlug) and P:/DZ/b/config.cpp:3-4"
    assert _missing_cited_lines(text, counts.get) == [
        r"P:\scripts\a.c:12 (has 10 lines)",
        "P:/DZ/b/config.cpp:822 (has 10 lines)",
    ]
    assert _missing_cited_lines("P:/DZ/gone/config.cpp:1", counts.get) == ["P:/DZ/gone/config.cpp:1 (missing)"]
    assert EVAL_QUESTION_FILES, "evals/questions holds no question files"
    eval_ids = {_ref_id(p) for p in EVAL_QUESTION_FILES}
    eval_texts = [text for rel, text in _citation_texts() if rel in eval_ids]
    assert len(eval_texts) == len(eval_ids)
    assert any(m.group(1).startswith("P:/") for t in eval_texts for m in CITED_LINE_RE.finditer(t)), (
        "no P:/ citation read from evals/questions"
    )


@pytest.mark.skipif(not Path("P:/scripts").is_dir(), reason="P:\\ is not mounted with vanilla scripts")
def test_cited_vanilla_lines_exist_on_p():
    cache: dict[str, int | None] = {}

    def line_count(cited: str) -> int | None:
        if cited not in cache:
            file = Path(cited)
            cache[cited] = len(file.read_bytes().splitlines()) if file.is_file() else None
        return cache[cited]

    bad = [f"{rel}: {miss}" for rel, text in _citation_texts() for miss in _missing_cited_lines(text, line_count)]
    assert not bad, "citations of vanilla lines that do not exist:\n" + "\n".join(bad)


# A line count alone passes every stale citation once a DayZ update shifts the
# file, so each cited line must also hold, within SYMBOL_WINDOW lines, one of the
# symbols backticked on the line that cites it. "`:N` to `:M`" right after a
# citation widens it to a range. A citing line with no backticked symbol is not checked.
SYMBOL_WINDOW = 3
_CITED_RANGE_END_RE = re.compile(r"`? to `:(\d+)`")
_BACKTICKED_RE = re.compile(r"`([^`\n]+)`")
_IDENT_RE = re.compile(r"[A-Za-z_]\w{2,}")
# A backticked file name or bare line number names no symbol.
_NOT_A_SYMBOL_RE = re.compile(
    r"[\w./\\-]*\.(?:c|cpp|hpp|h|md|xml|json|layout|p3d|paa|rvmat|py|txt|imageset|edds)(?::\d+)?|:\d+(?:-\d+)?"
)
# Keywords and types that appear on almost every line, so they prove nothing.
_GENERIC_WORDS = {
    "and", "array", "auto", "bool", "class", "const", "else", "extends", "false", "float", "for", "inout",
    "int", "map", "native", "new", "notnull", "null", "out", "private", "protected", "proto", "ref", "return",
    "set", "static", "string", "the", "this", "true", "typename", "vector", "void",
}


def _cited_symbols(doc_line: str) -> tuple[set[str], set[str]]:
    """The identifiers and the literal snippets backticked on a citing line, lower case."""
    spans = [s.strip() for s in _BACKTICKED_RE.findall(doc_line)]
    spans = [s for s in spans if "P:\\" not in s and "P:/" not in s and not _NOT_A_SYMBOL_RE.fullmatch(s)]
    words = {w.lower() for s in spans for w in _IDENT_RE.findall(s) if w.lower() not in _GENERIC_WORDS}
    return words, {s.lower() for s in spans if len(s) >= 2 and s.lower() not in _GENERIC_WORDS}


def _symbol_mismatches(text: str, lines_of) -> list[str]:
    """Each citation in text whose cited lines hold none of its line's backticked symbols.
    lines_of(path) gives the vanilla file's lines, or None when it is missing; missing
    files and lines past the end are the line test's to report."""
    bad = []
    for m in CITED_LINE_RE.finditer(text):
        first = int(m.group(2))
        last = int(m.group(3) or first)
        to = _CITED_RANGE_END_RE.match(text, m.end())
        if to and int(to.group(1)) >= first:
            last = int(to.group(1))
        lines = lines_of(m.group(1))
        if lines is None or last > len(lines):
            continue
        start = text.rfind("\n", 0, m.start()) + 1
        end = text.find("\n", m.end())
        words, snippets = _cited_symbols(text[start : end if end >= 0 else len(text)])
        if not words and not snippets:
            continue
        window = "\n".join(lines[max(0, first - 1 - SYMBOL_WINDOW) : last + SYMBOL_WINDOW]).lower()
        if not any(w in window for w in words | snippets):
            bad.append(m.group(0))
    return bad


def _vanilla_lines_of():
    cache: dict[str, list[str] | None] = {}

    def lines_of(cited: str) -> list[str] | None:
        if cited not in cache:
            file = Path(cited)
            raw = file.read_bytes().splitlines() if file.is_file() else None
            cache[cited] = None if raw is None else [b.decode("utf-8", errors="replace") for b in raw]
        return cache[cited]

    return lines_of


# Checked by hand against P:\ (game storage version 144): each cites a value, a
# statement or a member deep inside a class the line names (a config value, an
# OnStoreSave override of the named class), or a built-in type such as `int` whose
# name is a keyword. Keyed by citing file under .claude/skills/.
CITED_SYMBOL_EXEMPT: dict[str, set[str]] = {
    "_shared/ai/perception.md": {
        r"P:\scripts\3_game\playerconstants.c:263",
    },
    "_shared/ai/spawning-and-performance.md": {
        r"P:\scripts\4_world\entities\creatures\infected\zombiebase.c:29",
    },
    "_shared/animation/README.md": {
        r"P:\scripts\4_world\entities\itembase\barrel_colorbase.c:144",
    },
    "_shared/animation/animation-sources.md": {
        r"P:\DZ\structures\residential\config.cpp:7385",
    },
    "_shared/audio-fx/sound-script.md": {
        r"P:\scripts\3_game\effect.c:336",
    },
    "_shared/container-base.md": {
        r"P:\DZ\gear\camping\config.cpp:10261-10266",
    },
    "_shared/enscript/patterns/actions.md": {
        r"P:\scripts\4_world\entities\building\underground\powergeneratorstatic.c:143",
    },
    "_shared/enscript/references/api_game.md": {
        r"P:\scripts\3_game\global\game.c:5",
    },
    "_shared/enscript/references/api_network.md": {
        r"P:\scripts\3_game\entities\entityai.c:3518",
        r"P:\scripts\4_world\entities\itembase.c:190",
    },
    "_shared/enscript/references/api_player.md": {
        r"P:\scripts\3_game\global\game.c:5",
    },
    "_shared/enscript/references/api_scheduling.md": {
        r"P:\scripts\2_gamelib\tools.c:52",
    },
    "_shared/enscript/references/language_memory.md": {
        r"P:\scripts\1_core\proto\enscript.c:10",
        r"P:\scripts\2_gamelib\tools.c:56",
    },
    "_shared/enscript/references/language_types.md": {
        r"P:\scripts\1_core\proto\enconvert.c:109",
        r"P:\scripts\1_core\proto\enconvert.c:22",
        r"P:\scripts\1_core\proto\enconvert.c:556",
    },
    "_shared/persistence/data-audit.md": {
        r"P:\scripts\3_game\entities\entityai.c:1393",
    },
    "_shared/persistence/save-load-contract.md": {
        r"P:\scripts\3_game\entities\entityai.c:3041",
        r"P:\scripts\4_world\classes\codelockcomponent.c:257",
        r"P:\scripts\4_world\entities\itembase\basebuildingbase\totem.c:101",
        r"P:\scripts\4_world\entities\itembase\combinationlock.c:128",
        r"P:\scripts\4_world\entities\manbase\playerbase.c:7353",
    },
    "_shared/persistence/versioning-and-migration.md": {
        r"P:\scripts\3_game\entities\entityai.c:2910",
        r"P:\scripts\4_world\entities\manbase\playerbase.c:7366",
    },
    "_shared/physics/drop-and-throw.md": {
        r"P:\scripts\4_world\entities\dayzplayerimplementthrowing.c:187",
    },
    "_shared/textures/surface-recipes.md": {
        r"P:\DZ\characters\glasses\config.cpp:598",
    },
    "_shared/vehicles/simulation.md": {
        r"P:\DZ\vehicles\water\config.cpp:124",
    },
    "_shared/wearables/references/color-variants.md": {
        r"P:\DZ\characters\tops\config.cpp:2269",
        r"P:\DZ\characters\vests\config.cpp:578",
    },
    "_shared/wearables/references/protection-and-insulation.md": {
        r"P:\DZ\characters\tops\config.cpp:2263",
        r"P:\DZ\characters\vests\config.cpp:892",
        r"P:\DZ\gear\consumables\config.cpp:259",
        r"P:\DZ\gear\tools\config.cpp:1016",
        r"P:\DZ\gear\tools\config.cpp:5365",
        r"P:\scripts\3_game\constants.c:821",
        r"P:\scripts\4_world\entities\itembase\clothing\gp5gasmask.c:13",
    },
}


def _all_symbol_mismatches() -> dict[str, list[str]]:
    lines_of = _vanilla_lines_of()
    found = {}
    for path in REF_FILES + sorted(SKILLS_DIR.rglob("*.c")):
        bad = _symbol_mismatches(path.read_text(encoding="utf-8", errors="replace"), lines_of)
        if bad:
            found[_ref_id(path).removeprefix(".claude/skills/")] = bad
    return found


@pytest.mark.skipif(not Path("P:/scripts").is_dir(), reason="P:\\ is not mounted with vanilla scripts")
def test_cited_vanilla_lines_hold_a_cited_symbol():
    bad = [
        f"{rel}: {cited}"
        for rel, cites in _all_symbol_mismatches().items()
        for cited in cites
        if cited not in CITED_SYMBOL_EXEMPT.get(rel, set())
    ]
    assert not bad, (
        f"citations whose vanilla lines (within {SYMBOL_WINDOW}) hold none of the symbols backticked beside "
        "them; the line probably moved in a DayZ update:\n" + "\n".join(bad)
    )


@pytest.mark.skipif(not Path("P:/scripts").is_dir(), reason="P:\\ is not mounted with vanilla scripts")
def test_cited_symbol_exemptions_are_still_needed():
    found = _all_symbol_mismatches()
    stale = [f"{rel}: {c}" for rel, cites in CITED_SYMBOL_EXEMPT.items() for c in cites if c not in found.get(rel, [])]
    assert not stale, "exemptions that now pass or no longer exist; remove them:\n" + "\n".join(stale)


_FAKE_VANILLA = ["class Foo", "{", "\tint m_Count;", "", "\tvoid Bar()", "\t{", "\t}"] + [""] * 30 + ["\tvoid Baz()"]


def _fake_lines_of(cited: str) -> list[str] | None:
    return _FAKE_VANILLA if cited == r"P:\scripts\foo.c" else None


def test_symbol_check_flags_a_citation_whose_line_moved():
    assert _symbol_mismatches(r"`Foo.Bar` is at (`P:\scripts\foo.c:5`).", _fake_lines_of) == []
    # Same symbol, line shifted past the window: the line count alone would still pass this.
    assert _symbol_mismatches(r"`Foo.Bar` is at (`P:\scripts\foo.c:30`).", _fake_lines_of) == [r"P:\scripts\foo.c:30"]


def test_symbol_check_reads_ranges_and_skips_what_it_cannot_check():
    # "to `:N`" widens the cited range to reach Baz.
    assert _symbol_mismatches(r"`Baz` (`P:\scripts\foo.c:20` to `:38`)", _fake_lines_of) == []
    assert _symbol_mismatches(r"`Baz` (`P:\scripts\foo.c:20`)", _fake_lines_of) == [r"P:\scripts\foo.c:20"]
    # File names and line numbers are not symbols; no symbol means nothing to check.
    assert _symbol_mismatches(r"See `creatures.md` and `:12` (`P:\scripts\foo.c:30`).", _fake_lines_of) == []
    # Generic keywords prove nothing, a missing file is the line test's to report.
    assert _symbol_mismatches(r"`int` (`P:\scripts\foo.c:30`)", _fake_lines_of) == []
    assert _symbol_mismatches(r"`Bar` (`P:\scripts\gone.c:5`)", _fake_lines_of) == []


def test_citation_exemptions_exist():
    for rel in CITATION_EXEMPT:
        assert (SHARED_DIR / rel).is_file(), f"stale citation exemption {rel}"
    for folder in CITATION_EXEMPT_FOLDERS:
        assert (SHARED_DIR / folder).is_dir(), f"stale citation exemption {folder}/"


CONVENTIONS = SHARED_DIR / "dayz-conventions.md"


def _preflight_exceptions() -> set[str]:
    """The skills named in Tier 2's 'Exceptions to the preflight gate' list."""
    text = CONVENTIONS.read_text(encoding="utf-8")
    block = text.split("Exceptions to the preflight gate", 1)[1].split("Every other skill that does work", 1)[0]
    return set(re.findall(r"`/(dayz-[a-z0-9-]+)`", block))


def test_every_dayz_skill_script_gates_on_preflight_or_is_an_exception():
    exceptions = _preflight_exceptions()
    ungated = []
    for skill in sorted(SKILLS_DIR.glob("dayz-*/")):
        scripts = [p for p in skill.rglob("*.py") if not p.name.startswith("test_") and "__pycache__" not in p.parts]
        if not scripts:
            continue  # a reference or meta skill with no script
        if any("gate_on_preflight" in p.read_text(encoding="utf-8", errors="replace") for p in scripts):
            continue
        if skill.name not in exceptions:
            ungated.append(skill.name)
    assert not ungated, f"no gate_on_preflight and no stated exception in {CONVENTIONS.name}: {ungated}"


def test_preflight_exceptions_are_real_skills():
    for name in _preflight_exceptions():
        assert (SKILLS_DIR / name / "SKILL.md").exists(), f"exception list names unknown skill /{name}"


def test_tier_one_files_match():
    texts = {name: (REPO / name).read_text(encoding="utf-8") for name in ("CLAUDE.md", "AGENTS.md", "GEMINI.md")}
    assert len(set(texts.values())) == 1, "CLAUDE.md, AGENTS.md and GEMINI.md must hold the same text"


PANEL = REPO / "mods" / "agentic-z-panel" / "hooks" / "register.tsx"


def test_panel_buttons_name_existing_skill_scripts():
    """CI runs pytest only, so this catches a renamed script that would silently break a panel button."""
    text = PANEL.read_text(encoding="utf-8")
    block = text.split("const SKILL = {", 1)[1].split("} as const", 1)[0]
    pairs = re.findall(r"\w+:\s*\['([\w-]+)',\s*'([\w.]+)'\]", block)
    assert len(pairs) >= 10, "could not read the SKILL map in register.tsx"
    pairs += re.findall(r"join\(current\.root, '\.claude', 'skills', '([\w-]+)', '([\w.]+)'\)", text)
    missing = [f"{skill}/{script}" for skill, script in pairs if not (SKILLS_DIR / skill / script).is_file()]
    assert not missing, f"panel buttons name missing scripts: {missing}"


def test_physics_specialist_reports_to_main_session_on_direct_call():
    # dayz-router sends physics requests straight from the main session, so the
    # Report must name the main session as recipient and tell it to start each owner.
    assert "dayz-physics-specialist" in (AGENTS_DIR / "dayz-router.md").read_text(encoding="utf-8")
    text = (AGENTS_DIR / "dayz-physics-specialist.md").read_text(encoding="utf-8")
    report = text.split("## Report", 1)[1]
    assert "main session" in report, "Report names only a lead; a direct call has no lead"
    assert "start each owner" in report, "Report must tell the main session to start each named owner"


def test_orchestrator_agent_list_covers_every_agent_the_leads_start():
    # Run as the main session (claude --agent), the orchestrator's Agent(...) list limits which
    # agents its subagents can start too. The live run's leads got "Agent type not found" for
    # dayz-wearables-specialist and dayz-mod-reviewer until both were on this list.
    text = (AGENTS_DIR / "dayz-orchestrator.md").read_text(encoding="utf-8")
    allowed = {n.strip() for n in re.search(r"^tools:.*?Agent\(([^)]*)\)", text, re.M).group(1).split(",")}
    lead = (AGENTS_DIR / "dayz-lead.md").read_text(encoding="utf-8")
    started = {n for n in re.findall(r"`([a-z-]+)`", lead) if n in AGENT_NAMES} - {"dayz-orchestrator"}
    missing = sorted(n for n in started for name in (n, f"agentic-z:{n}") if name not in allowed)
    assert not missing, f"agents the leads start but the orchestrator's Agent list leaves out: {missing}"
