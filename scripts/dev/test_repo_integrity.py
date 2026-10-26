"""Repo-wide checks: agent team and plugin manifest, the references in agents, skills and packs,
no-token .bat wrappers, the knowledge-pack index and citations (and, with P:\\ mounted, that each
cited vanilla line, in the packs and in the eval questions' verified fields, exists and holds a symbol
the citation names), the preflight gate list, the Tier 1 files and the panel's skill scripts.

Run with: py -m pytest scripts/dev/test_repo_integrity.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO / "agents"
SKILLS_DIR = REPO / "skills"
REPO_SKILLS_DIR = REPO / ".claude" / "skills"
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
    on_disk = {p.parent.name for d in (SKILLS_DIR, REPO_SKILLS_DIR) for p in d.glob("*/SKILL.md")}
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
    | set(REPO_SKILLS_DIR.glob("*/SKILL.md"))
    | set((SKILLS_DIR / "_shared").rglob("*.md"))
    | set(SKILLS_DIR.glob("*/reference*/**/*.md"))
    | set(REPO_SKILLS_DIR.glob("*/reference*/**/*.md"))
)


def _ref_id(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


@pytest.mark.parametrize("path", REF_FILES, ids=_ref_id)
def test_referenced_repo_files_exist(path):
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r"(?:\.claude/(?:skills|mcp)|(?<![\w./])(?:skills|agents)|scripts)/[\w./-]+\.(?:md|py|bat)", text):
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
        assert (SKILLS_DIR / ref / "SKILL.md").exists() or (REPO_SKILLS_DIR / ref / "SKILL.md").exists(), (
            f"{_ref_id(path)} names unknown skill /{ref}"
        )


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
        assert name in ROUTE["targets"], f"{name} is missing from the targets in skills/dayz-route/rules.json"


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


def _load_gate():
    spec = importlib.util.spec_from_file_location("dayz_gate_for_integrity", SKILLS_DIR / "dayz-gate" / "gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


class _SessionRuntime:
    """A DayZDiag session the gate did not start: running until stop_test.bat ends it."""

    def __init__(self, confirm: bool, results: dict[str, tuple[int, str]] | None = None):
        self.running = [4242]
        self.calls: list[str] = []
        self.asked = 0
        self.answer = confirm
        self.results = results or {}
        self.now = 0.0

    def runtime(self):
        return GATE.Runtime(run=self.run, diag_pids=lambda: list(self.running), pid_alive=lambda p: p in self.running,
                            sleep=self.sleep, clock=lambda: self.now, confirm=self.confirm)

    def confirm(self, pids):
        self.asked += 1
        return self.answer

    def sleep(self, seconds):
        self.now += seconds

    def run(self, cmd):
        joined = " ".join(cmd)
        if "stop_test.bat" in joined:
            self.calls.append("stop")
            self.running = []
            return 0, "SUCCESS"
        for key, result in self.results.items():
            if key in joined:
                self.calls.append(key)
                return result
        raise AssertionError(f"unexpected command {cmd}")


def _assert_stop_session_asks_first():
    # A session the gate did not start is stopped only when confirm says yes; one it started never asks.
    refused = _SessionRuntime(confirm=False)
    with pytest.raises(GATE.GateError, match="--yes"):
        GATE.stop_session(refused.runtime())
    assert refused.asked == 1 and refused.calls == [], "gate.py stop_session must ask before stopping a session it did not start"
    agreed = _SessionRuntime(confirm=True)
    GATE.stop_session(agreed.runtime())
    assert agreed.calls == ["stop"], "gate.py stop_session must stop a session it did not start once confirmed"
    own = _SessionRuntime(confirm=False)
    GATE.stop_session(own.runtime(), started_by_gate=True)
    assert own.asked == 0 and own.calls == ["stop"], "gate.py stop_session must not ask about a session it started"


def _write_mod(mod_dir: Path, required_addons: str, bundle: bool) -> None:
    mod_dir.mkdir(parents=True)
    (mod_dir / "config.cpp").write_text(
        f"class CfgPatches\n{{\n\tclass M\n\t{{\n\t\trequiredAddons[] = {{{required_addons}}};\n\t}};\n}};\n", encoding="utf-8"
    )
    if bundle:
        (mod_dir / "Addons").mkdir()
        (mod_dir / "Addons" / "payload.pbo").write_bytes(b"")


def test_ingame_tester_matches_gate(tmp_path, monkeypatch):
    # dayz-ingame-tester is the fallback for `/dayz-gate ingame`, so its ready line, settle time,
    # client timeout and pass/fail rules must match what gate.py does. Each rule is checked by
    # running gate.py's own functions, not by searching its source text.
    agent = (AGENTS_DIR / "dayz-ingame-tester.md").read_text(encoding="utf-8")
    # The ingame CLI passes the module defaults to gate_ingame.
    seen = {}

    def fake_gate_ingame(mod, project_dir, rt, deps, server, port, timeout, settle, ready_pattern):
        seen.update(timeout=timeout, settle=settle, ready=ready_pattern)
        return {"verdict": "PASS"}

    monkeypatch.setattr(GATE, "gate_ingame", fake_gate_ingame)
    monkeypatch.setattr(GATE.h, "resolve_project_dir", lambda: tmp_path)
    monkeypatch.setattr(GATE, "save_health", lambda report, project_dir: None)
    monkeypatch.setattr(GATE, "emit", lambda report, as_json: None)
    assert GATE.main(["ingame", "M"], rt=_SessionRuntime(confirm=False).runtime()) == 0
    assert seen == {"timeout": GATE.DEFAULT_TIMEOUT_S, "settle": GATE.DEFAULT_SETTLE_S, "ready": GATE.DEFAULT_READY_RE}, (
        "gate.py ingame must default --timeout, --settle and --ready-pattern to its DEFAULT_* constants"
    )
    ready_line = re.search(r"log line matching `([^`]+)`", agent).group(1)
    assert re.search(GATE.DEFAULT_READY_RE, ready_line), "dayz-ingame-tester ready line must match gate.py DEFAULT_READY_RE"
    assert (GATE.DEFAULT_SETTLE_S, GATE.DEFAULT_TIMEOUT_S) == (30, 300), "gate.py settle and timeout defaults must stay 30 s and 300 s, as dayz-ingame-tester states"
    assert "keep reading 30 more seconds" in agent, "dayz-ingame-tester must state the 30 second settle time"
    assert "Give up after five minutes" in agent, "dayz-ingame-tester must state the five minute client timeout"
    # judge_entries: a line naming the mod fails; NULL pointer and Can't find lines that name nothing
    # of the mod are warnings; any other such line fails once a vanilla-only run exists and is a
    # warning without one; a line found in the vanilla-only run is noise.
    identity = GATE.ModIdentity("M", re.compile(r"@M\b"), None, [])

    def entry(category, text):
        return {"category": category, "text": text, "context": []}

    named = entry("compile", "@M/scripts/x.c(3): Unknown type 'Foo'")
    null_ptr = entry("null_pointer", "NULL pointer to instance")
    cant_find = entry("cant_find", "Can't find thing")
    other = entry("missing_config", "No entry 'bin\\config.bin/CfgVehicles.Foo'")
    known = entry("missing_texture", "Cannot load texture dz\\x.paa")
    baseline = {GATE.triage.fingerprint(known["text"])}
    entries = [named, null_ptr, cant_find, other, known]
    assert GATE.judge_entries(entries, identity, baseline, True) == ([named, other], [null_ptr, cant_find], [known]), (
        "gate.py judge_entries must fail unqualified non-vanilla lines when a baseline exists"
    )
    assert GATE.judge_entries(entries, identity, set(), False) == ([named], [null_ptr, cant_find, other, known], []), (
        "gate.py judge_entries must only warn about lines naming nothing of the mod when no baseline exists"
    )
    assert (
        "A `NULL pointer` or `Can't find` line that names nothing of the mod is never a failure: "
        "report it as a warning when it is not in the vanilla-only run." in agent
    ), "dayz-ingame-tester must state that unqualified NULL pointer and Can't find lines are warnings"
    assert "Any other error line that names nothing of the mod and is not in an existing vanilla-only run fails the gate." in agent, (
        "dayz-ingame-tester must state that other unqualified lines not in the vanilla-only run fail, as judge_entries does"
    )
    # A payload-only bundle is deployed under its PBOs' own names, never as <ModName>.pbo, and the
    # missing --deps error exempts a bundle.
    assert r"Addons\<ModName>.pbo`" not in agent, "dayz-ingame-tester must not require <ModName>.pbo: a bundle deploys its PBOs under their own names"
    assert r"for a bundle at least one `.pbo`, exists under `P:\Mods\@<ModName>\Addons\`" in agent, "dayz-ingame-tester step 1 must accept any .pbo for a bundle"
    plain, bundle = tmp_path / "workspace" / "Plain", tmp_path / "workspace" / "Bundle"
    _write_mod(plain, '"DZ_Data", "JM_CF_Scripts"', bundle=False)
    _write_mod(bundle, '"DZ_Data", "JM_CF_Scripts"', bundle=True)
    assert GATE.required_deps(GATE.mod_identity("Bundle", bundle), bundle, []) == [], (
        "gate.py required_deps must exempt a bundle from the missing --deps error"
    )
    assert GATE.required_deps(GATE.mod_identity("Plain", plain), plain, ["@CF"]) == ["CF"], "gate.py required_deps must strip '@' from --deps"
    no_launch = _SessionRuntime(confirm=False)
    with pytest.raises(GATE.GateError, match="no --deps were given"):
        GATE.ingame_session("Plain", tmp_path, no_launch.runtime(), [], "chernarus", 2302, 1, 1, GATE.DEFAULT_READY_RE)
    assert no_launch.calls == [], "gate.py ingame_session must refuse missing --deps before it stops or launches anything"
    assert "A bundle is exempt: when no dependencies are named" in agent, "dayz-ingame-tester must give a bundle the same dependency exemption as gate.py"
    # stop_session stops a session the gate did not start only on confirm; the agent must ask too.
    _assert_stop_session_asks_first()
    step0 = re.search(r"^0\. .+$", agent, re.M).group(0)
    assert "ask the caller" in step0 and "Don't stop it" in step0, "dayz-ingame-tester step 0 must ask the caller, not stop a session it did not start"
    conv = (SKILLS_DIR / "_shared" / "dayz-conventions.md").read_text(encoding="utf-8")
    config_row = next(l for l in conv.splitlines() if l.startswith("| `conventions/config.md` |"))
    assert "conventions/config.md" in agent and "ingame-tester" in config_row.rsplit("|", 2)[1], "conventions/config.md Read by must list ingame-tester, which cites it"
    # find_baseline: a vanilla-only RPT plus the script logs created 0 to 30 s after it.
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "DayZDiag_x64_2026-01-01_10-00-00.RPT").write_text('CLI params: "-mod=@CF"\n', encoding="utf-8")
    for name in ("script_2026-01-01_09-59-55.log", "script_2026-01-01_10-00-20.log", "script_2026-01-01_10-00-45.log"):
        (logs / name).write_text("x\n", encoding="utf-8")
    _, used = GATE.find_baseline([logs], GATE.snapshot([logs]), "M")
    assert sorted(Path(p).name for p in used) == ["DayZDiag_x64_2026-01-01_10-00-00.RPT", "script_2026-01-01_10-00-20.log"], (
        "gate.py find_baseline must pair script logs created within 30 s after the RPT"
    )
    assert "plus the script logs created within 30 seconds after that RPT" in agent, "dayz-ingame-tester vanilla-only run must include the script logs created within 30 s after the RPT"
    assert GATE.POLL_S == 2 and "every 2 seconds, the gate's interval" in agent, "dayz-ingame-tester step 3 must poll every POLL_S (2) seconds, like gate.py"


def test_build_checker_matches_gate(tmp_path, monkeypatch):
    # dayz-build-checker is the fallback for `/dayz-gate build`: lint first, then stop the
    # session and build, and a bundle's payload is checked with /dayz-deploy-pbo.
    agent = (AGENTS_DIR / "dayz-build-checker.md").read_text(encoding="utf-8")
    _write_mod(tmp_path / "workspace" / "M", '"DZ_Data"', bundle=False)
    session = _SessionRuntime(confirm=True, results={"build.py": (0, "")})

    def fake_lint(report, mod, mod_dir, project_dir):
        session.calls.append("lint")
        return True

    monkeypatch.setattr(GATE, "run_lint", fake_lint)
    assert GATE.gate_build("M", tmp_path, session.runtime())["verdict"] == "PASS"
    assert session.calls == ["lint", "stop", "build.py"], "gate_build must lint, then stop the session, then build"
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
    _assert_stop_session_asks_first()
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


def test_orchestrator_sets_up_the_gate_server_instance_before_gating():
    # The in-game gates run with --server <instance>. Without a step that picks the instance and
    # runs /dayz-add-server when .server/<instance>/ is missing, a new mod's first in-game gate
    # fails on a missing instance and uses up one of its three rounds.
    orchestrator = (AGENTS_DIR / "dayz-orchestrator.md").read_text(encoding="utf-8")
    setup = orchestrator.split("3. **Approval", 1)[1].split("4. **Run a wave.**", 1)[0]
    assert "`/dayz-add-server <instance>" in setup, "step 3 must run /dayz-add-server for a missing instance"
    assert ".server/<instance>/" in setup, "step 3 must check .server/<instance>/ before adding it"
    gate_default = re.search(r"default `(\w+)`", (SKILLS_DIR / "dayz-gate" / "SKILL.md").read_text(encoding="utf-8"))
    assert gate_default and f"`{gate_default.group(1)}`" in setup, "step 3's default instance must match /dayz-gate's --server default"
    gate_step = orchestrator.split("5. **Gate the wave.**", 1)[1].split("6. **Next wave.**", 1)[0]
    assert "--server <instance>" in gate_step and "step 3" in gate_step, "the gate step must use the instance from step 3"


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


@pytest.mark.skipif(sys.platform != "win32", reason="runs cmd.exe")
@pytest.mark.parametrize("broken_py", [False, True], ids=["no-launcher", "py-without-python"])
@pytest.mark.parametrize("name", [n for n in DAYZ_WRAPPERS if n != "dayz-search.bat"])
def test_dayz_wrapper_says_python_is_missing(name, broken_py, tmp_path):
    # With neither python nor py working, the wrappers printed only "'py' is not
    # recognized as an internal or external command". py-without-python is the py
    # launcher on a machine with no Python 3 left (it runs but exits non-zero).
    if broken_py:
        (tmp_path / "py.bat").write_text("@echo off\r\necho RAN-py %*\r\nexit /b 103\r\n", encoding="ascii")
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    env = {k: v for k, v in os.environ.items() if k.upper() != "PY"}
    env["PATH"] = f"{tmp_path};{system32}"
    bat = REPO / "scripts" / "dayz" / name
    result = subprocess.run(f'cmd /d /c ""{bat}" --help"', env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 9009, f"{name} exit {result.returncode}: {result.stdout!r} {result.stderr!r}"
    assert result.stderr.strip() == (
        "[FAIL] Python 3 not found: install it from python.org or add python/py to PATH"
    ), f"{name} stderr: {result.stderr!r}"
    assert "--help" not in result.stdout, f"{name} still ran the script: {result.stdout!r}"


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


def test_readme_names_the_wrappers_that_call_paid_apis():
    # The intro said no wrapper but evals.bat spends tokens, yet ask, dayz-search and
    # search-index embed through Voyage AI and route asks TypeSafe's Jev when keyed.
    readme = (REPO / "scripts" / "README.md").read_text(encoding="utf-8")
    intro = readme.split("## Daily DayZ work", 1)[0]
    for script, api in [
        ("skills/dayz-ask/ask.py", "voyage"),
        ("scripts/dayz/dayz-search.py", "voyage"),
        ("skills/dayz-search-index/index.py", "voyage"),
        ("skills/dayz-route/jev.py", "typesafe"),
    ]:
        assert api in (REPO / script).read_text(encoding="utf-8").lower(), f"{script} no longer calls {api}"
    for bat in ("ask.bat", "dayz-search.bat", "search-index.bat", "route.bat"):
        assert f"`{bat}`" in intro, f"the intro must say {bat} calls a paid API"
    assert "Voyage" in intro and "TYPESAFE_API_KEY" in intro
    assert "`search-download.bat`" in intro, "the intro must point to search-download.bat as the free path"


def test_readme_python_fallback_claims_match_the_wrappers():
    # The intro said every wrapper falls back to py, but stop-test.bat only calls a taskkill .bat,
    # and dayz-search.bat has the fallback without the [FAIL] Python 3 not found line.
    readme = (REPO / "scripts" / "README.md").read_text(encoding="utf-8")
    intro = readme.split("## Daily DayZ work", 1)[0]
    bats = sorted((REPO / "scripts").glob("*/*.bat"))
    no_fallback = {b.name for b in bats if 'set "PY=py"' not in b.read_text(encoding="utf-8")}
    dayz_no_fail = {
        b.name for b in bats
        if b.parent.name == "dayz" and "Python 3 not found" not in b.read_text(encoding="utf-8")
    }
    fallback_line = next(line for line in intro.splitlines() if "falls back to the `py` launcher" in line)
    for name in no_fallback:
        assert f"except `{name}`" in fallback_line, f"the intro must name {name} as having no py fallback"
    for name in dayz_no_fail - no_fallback:
        assert f"other than `{name}`" in fallback_line, f"the intro must name {name} as lacking the [FAIL] line"


def test_readme_clean_rows_say_what_they_delete():
    # The clean-repo.bat row said "Clear generated files before a push", but it deletes managed
    # mod folders under workspace\, their P:\ junctions and deployed copies, and all of .server\.
    readme = (REPO / "scripts" / "README.md").read_text(encoding="utf-8")
    flags = (REPO / ".claude" / "skills" / "clean-repo" / "clean.py").read_text(encoding="utf-8")
    assert '"--dry-run"' in flags and '"--keep-server"' in flags
    row = next(r for r in readme.splitlines() if r.startswith("| `clean-repo.bat`"))
    for needle in ("`workspace\\`", "`P:\\Mods\\@<ModName>\\`", "`.server\\`", "`--dry-run`", "`--keep-server`"):
        assert needle in row, f"the clean-repo.bat row must mention {needle}"
    row = next(r for r in readme.splitlines() if r.startswith("| `clean-workspace.bat`"))
    for needle in ("`workspace\\`", "`P:\\Mods\\@<ModName>\\`", "`--dry-run`"):
        assert needle in row, f"the clean-workspace.bat row must mention {needle}"


def test_readme_clean_rows_say_deployed_copies_need_the_ownership_marker():
    # Both rows said the deployed P:\Mods\@<ModName>\ copy is deleted, but clean.py removes it
    # only when owns_deploy_dir finds the toolkit's ownership marker; any other copy stays.
    readme = (REPO / "scripts" / "README.md").read_text(encoding="utf-8")
    code = (REPO / "skills" / "dayz-clean-workspace" / "clean.py").read_text(encoding="utf-8")
    helpers = (SHARED_DIR / "skill_helpers.py").read_text(encoding="utf-8")
    assert "h.owns_deploy_dir(deployed, name)" in code
    marker = re.search(r'^SCAFFOLD_MARKER = "([^"]+)"', helpers, re.M).group(1)
    for bat in ("clean-workspace.bat", "clean-repo.bat"):
        row = next(r for r in readme.splitlines() if r.startswith(f"| `{bat}`"))
        assert "ownership marker" in row and f"`{marker}`" in row, f"the {bat} row must name the {marker} marker"


def test_readme_sync_skills_row_matches_the_default_agent_list():
    # The row said `--agents claude` adds Claude Code, but --agents replaces the default list,
    # so that command links only Claude Code and drops Codex and Gemini.
    readme = (REPO / "scripts" / "README.md").read_text(encoding="utf-8")
    cfg = json.loads((REPO_SKILLS_DIR / "sync-skills" / "agents.json").read_text(encoding="utf-8"))
    names = [a["name"] for a in cfg["agents"]]
    off_by_default = [a["name"] for a in cfg["agents"] if a.get("default", True) is False]
    assert off_by_default == ["claude"], f"agents.json defaults changed: {off_by_default}"
    sync = (REPO_SKILLS_DIR / "sync-skills" / "sync.py").read_text(encoding="utf-8")
    assert 'a["name"] in args.agents if args.agents else a.get("default", True)' in sync
    row = next(r for r in readme.splitlines() if r.startswith("| `sync-skills.bat`"))
    assert f"`--agents {' '.join(names)}` links all three" in row
    assert "`--agents claude` alone links only Claude Code" in row


def test_readme_says_what_unguarded_wrappers_print_without_python():
    # Only the scripts\dayz wrappers print [FAIL] Python 3 not found; the setup and dev
    # wrappers (preflight.bat first among them) fail with cmd's bare "not recognized" error.
    readme = (REPO / "scripts" / "README.md").read_text(encoding="utf-8")
    intro = readme.split("## Daily DayZ work", 1)[0]
    unguarded = [
        b for b in sorted((REPO / "scripts").glob("*/*.bat"))
        if b.parent.name in ("setup", "dev") and "Python 3 not found" not in b.read_text(encoding="utf-8")
    ]
    assert unguarded, "every setup/dev wrapper now has the [FAIL] guard; update the README intro"
    for folder in sorted({b.parent.name for b in unguarded}):
        assert f"`scripts\\{folder}`" in intro, f"the intro must say scripts\\{folder} wrappers have no [FAIL] guard"
    assert "is not recognized as an internal or external command" in intro


def test_readme_ask_note_names_the_free_grep_fallback():
    # The note said every ask.bat question goes to Voyage, but ask.py falls back to Grep on its
    # own when VOYAGE_API_KEY is unset or no index is installed.
    readme = (REPO / "scripts" / "README.md").read_text(encoding="utf-8")
    code = (REPO / "skills" / "dayz-ask" / "ask.py").read_text(encoding="utf-8")
    assert "VOYAGE_API_KEY not set" in code and "no search index" in code
    line = next(r for r in readme.splitlines() if r.startswith("- `ask.bat`"))
    assert "`VOYAGE_API_KEY` is not set" in line and "no search index" in line


# dayz-particles is reference-only (no script). dayz-record-correction ships check.py, but only
# the agent running the skill calls it (root, baseline, compare steps in its SKILL.md), never a user.
RUNNABLE_WITHOUT_BAT = {"dayz-particles", "dayz-record-correction"}


def test_every_runnable_skill_has_a_bat_wrapper():
    wrapped = set()
    for bat in BAT_FILES:
        wrapped.update(re.findall(r"skills\\([a-z0-9-]+)\\", bat.read_text(encoding="utf-8", errors="replace")))
    skills = {p.parent.name for d in (SKILLS_DIR, REPO_SKILLS_DIR) for p in d.glob("*/SKILL.md")}
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
# name is a keyword. Keyed by citing file under skills/, or by the
# evals/questions/ file whose verified note names a function the cited body sits in.
CITED_SYMBOL_EXEMPT: dict[str, set[str]] = {
    # object.c:1251-1255 is the loop branch inside PlaySoundSet, declared at :1247.
    "evals/questions/dayz-audio-fx-specialist.json": {
        "P:/scripts/3_game/entities/object.c:1251-1255",
    },
    # basebuildingbase.c:420 opens OnStoreSave, which writes m_SyncParts01 at :425;
    # entityai.c:1393 is GetEntityByPersitentID inside EEOnAfterLoad (:1381) and
    # :3041 its "cannot be called here" comment inside OnStoreLoad.
    # plugindiagmenumodding.c:21 is "modded class PluginDiagMenu"; its note is an aside about another file.
    "evals/questions/dayz-script-specialist.json": {
        "P:/scripts/4_world/plugins/pluginbase/plugindiagmenu/plugindiagmenumodding.c:21",
    },
    "evals/questions/dayz-persistence-specialist.json": {
        "P:/scripts/4_world/entities/itembase/basebuildingbase.c:420",
        "P:/scripts/3_game/entities/entityai.c:1393",
        "P:/scripts/3_game/entities/entityai.c:3041",
    },
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
    # particlelist.c:316 registers "contaminated_area_gas_around_tiny"; the citing line backticks only that effect's .ptc path.
    "dayz-particles/SKILL.md": {
        r"P:\scripts\3_game\particles\particlelist.c:316",
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


# The eval questions' "verified" fields cite without backticks, as
# "P:/x.c:12 (Symbol) and :16 (OTHER_SYMBOL)": a bare ":N" continues the last P:
# file (a non-P "name.ext:N" ends that), " to :M" widens a citation to a range, and
# the parenthesized note right after a citation, or else the one around it, names its symbols.
_EVAL_CITE_RE = re.compile(
    r"(?P<file>P:[\\/][^\s`:*?\"<>|()]+\.\w+):(?P<a>\d+)(?:-(?P<b>\d+))?(?: to :(?P<c>\d+))?"
    r"|(?P<other>[\w.\\/-]+\.\w+):\d+"
    r"|(?<![\w.\\/:]):(?P<na>\d+)(?:-(?P<nb>\d+))?(?: to :(?P<nc>\d+))?"
)
# Paths and file names in a note name no symbol.
_NOTE_FILE_RE = re.compile(r"\S*[\\/]\S*|[\w-]+\.(?:c|cpp|hpp|h|md|json|layout|p3d|paa|rvmat|py|xml)\b")
# A note's symbols: code-like identifiers (a capital, a digit or an underscore after the
# first letter, or a leading capital), a lower-case config key written key=value, and "quoted" text.
_NOTE_CODE_WORD_RE = re.compile(r"\b(?:[A-Za-z_]\w*[A-Z0-9_]\w*|[A-Z]\w+)\b|\b[a-z]\w+(?==)")
_NOTE_QUOTED_RE = re.compile(r'"([^"\n]{2,})"')


def _paren_body(text: str, start: int) -> str:
    """The text from start up to the ")" that closes the "(" just before start, on the same line."""
    depth = 1
    for i in range(start, len(text)):
        if text[i] == "\n":
            return text[start:i]
        depth += {"(": 1, ")": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i]
    return text[start:]


def _citation_note(text: str, start: int, end: int) -> str:
    """The parenthesized note right after text[start:end], else the one on its line enclosing it, else ""."""
    after = re.compile(r"[ \t]*\(").match(text, end)
    if after:
        return _paren_body(text, after.end())
    depth = 0
    for i in range(start - 1, text.rfind("\n", 0, start), -1):
        if text[i] == ")":
            depth += 1
        elif text[i] == "(":
            if depth == 0:
                return _paren_body(text, i + 1)
            depth -= 1
    return ""


def _note_symbols(note: str) -> set[str]:
    snippets = {s.lower() for s in _NOTE_QUOTED_RE.findall(note)}
    note = _NOTE_FILE_RE.sub(" ", note)
    words = {w.lower() for w in _NOTE_CODE_WORD_RE.findall(note) if len(w) >= 3}
    return (words | snippets) - _GENERIC_WORDS


def _eval_citations(text: str) -> list[tuple[str, str, int, int, set[str]]]:
    """(label, P: file, first line, last line, symbols) for each citation in an eval question's text."""
    found = []
    current = None
    for m in _EVAL_CITE_RE.finditer(text):
        if m.group("other"):
            current = None
            continue
        if m.group("file"):
            current, label, (a, b, c) = m.group("file"), m.group(0), m.group("a", "b", "c")
        elif current is None:
            continue
        else:
            label, (a, b, c) = current + m.group(0), m.group("na", "nb", "nc")
        first = int(a)
        found.append((label, current, first, int(c or b or first), _note_symbols(_citation_note(text, m.start(), m.end()))))
    return found


def _eval_symbol_mismatches(text: str, lines_of) -> list[str]:
    """Each eval citation whose cited lines (within SYMBOL_WINDOW) hold none of its note's symbols.
    A missing file or a line past the end is _missing_eval_lines' to report; no symbol, nothing to check."""
    bad = []
    for label, file, first, last, symbols in _eval_citations(text):
        lines = lines_of(file)
        if lines is None or last > len(lines) or not symbols:
            continue
        window = "\n".join(lines[max(0, first - 1 - SYMBOL_WINDOW) : last + SYMBOL_WINDOW]).lower()
        if not any(s in window for s in symbols):
            bad.append(label)
    return bad


def _missing_eval_lines(text: str, line_count) -> list[str]:
    """Each eval citation, bare ":N" continuations and " to :M" ends included, whose file is missing or too short."""
    bad = []
    for label, file, _first, last, _symbols in _eval_citations(text):
        count = line_count(file)
        if count is None or last > count:
            bad.append(f"{label} ({'missing' if count is None else f'has {count} lines'})")
    return bad


def _eval_question_texts():
    for path in EVAL_QUESTION_FILES:
        yield _ref_id(path), "\n".join(_json_strings(json.loads(path.read_text(encoding="utf-8"))))


def _all_symbol_mismatches() -> dict[str, list[str]]:
    lines_of = _vanilla_lines_of()
    found = {}
    for path in REF_FILES + sorted(SKILLS_DIR.rglob("*.c")):
        bad = _symbol_mismatches(path.read_text(encoding="utf-8", errors="replace"), lines_of)
        if bad:
            found[_ref_id(path).removeprefix("skills/")] = bad
    for rel, text in _eval_question_texts():
        bad = _eval_symbol_mismatches(text, lines_of)
        if bad:
            found[rel] = bad
    return found


@pytest.mark.skipif(not Path("P:/scripts").is_dir(), reason="P:\\ is not mounted with vanilla scripts")
def test_eval_continued_citations_exist_on_p():
    # The line test reads only full P: citations, so ":16" in "P:/x.c:1 (A) and :16 (B)"
    # and the end of "P:/x.c:3 to :6" were never checked against P:.
    cache: dict[str, int | None] = {}

    def line_count(cited: str) -> int | None:
        if cited not in cache:
            file = Path(cited)
            cache[cited] = len(file.read_bytes().splitlines()) if file.is_file() else None
        return cache[cited]

    bad = [f"{rel}: {miss}" for rel, text in _eval_question_texts() for miss in _missing_eval_lines(text, line_count)]
    assert not bad, "eval question citations of vanilla lines that do not exist:\n" + "\n".join(bad)


def test_eval_citation_check_follows_continuations_notes_and_ranges():
    # The eval questions' verified citations had only a line count, so a citation
    # that drifted inside its file still passed.
    text = r"P:\scripts\foo.c:5 (Foo.Bar) and :38 (Baz); P:\scripts\foo.c:3 to :6 (m_Count)"
    assert [c[:4] for c in _eval_citations(text)] == [
        (r"P:\scripts\foo.c:5", r"P:\scripts\foo.c", 5, 5),
        (r"P:\scripts\foo.c:38", r"P:\scripts\foo.c", 38, 38),
        (r"P:\scripts\foo.c:3 to :6", r"P:\scripts\foo.c", 3, 6),
    ]
    assert _eval_symbol_mismatches(text, _fake_lines_of) == []
    # The same symbols, each line moved: the line count alone passes both.
    assert _eval_symbol_mismatches(r"P:\scripts\foo.c:30 (Foo.Bar) and :20 (Baz)", _fake_lines_of) == [
        r"P:\scripts\foo.c:30",
        r"P:\scripts\foo.c:20",
    ]
    # A ":N" inside a note takes the note's symbols; a non-P file:N ends the P: file it continues.
    assert _eval_symbol_mismatches(r"P:\scripts\foo.c:38 (Baz, in class Foo at :1)", _fake_lines_of) == []
    # A note never reaches across lines: each JSON string of a question is its own line.
    assert _eval_citations("(Foo\n" + r"see P:\scripts\foo.c:30")[0][4] == set()
    assert _eval_citations(r"P:\scripts\foo.c:30 (Bar" + "\nFoo)")[0][4] == {"bar"}
    assert _eval_citations(r"P:\scripts\foo.c:5 (Bar); lint.py:30 and :31") == [
        (r"P:\scripts\foo.c:5", r"P:\scripts\foo.c", 5, 5, {"bar"}),
    ]
    # key=value names its key, "quoted" text is a snippet, plain words and file names are not symbols.
    assert _note_symbols('range=100 on "usti hlavne" in weight grams, see creatures.md') == {"range", "usti hlavne"}
    assert _eval_symbol_mismatches(r"P:\scripts\foo.c:30 (weight in grams)", _fake_lines_of) == []
    # Ends past the file are reported as missing lines, not as symbol mismatches.
    assert _eval_symbol_mismatches(r"P:\scripts\foo.c:5 to :99 (Bar)", _fake_lines_of) == []
    counts = {r"P:\scripts\foo.c": 38}
    assert _missing_eval_lines(r"P:\scripts\foo.c:5 (Bar) and :39; P:\scripts\gone.c:1", counts.get) == [
        r"P:\scripts\foo.c:39 (has 38 lines)",
        r"P:\scripts\gone.c:1 (missing)",
    ]


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
    pairs += re.findall(r"join\(current\.root, (?:'\.claude', )?'skills', '([\w-]+)', '([\w.]+)'\)", text)
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


def test_physics_specialist_listed_as_reader_of_assets_conventions():
    # The agent follows conventions/assets.md (LOD table); the 'Read by' column must
    # list it so an edit to assets.md flags this agent as a reader.
    agent = (AGENTS_DIR / "dayz-physics-specialist.md").read_text(encoding="utf-8")
    assert "conventions/assets.md" in agent
    core = (REPO / "skills" / "_shared" / "dayz-conventions.md").read_text(encoding="utf-8")
    row = next(line for line in core.splitlines() if line.startswith("| `conventions/assets.md`"))
    assert "physics-specialist" in row.rsplit("|", 2)[1], "conventions/assets.md Read by must list physics-specialist"


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


def test_no_read_text_with_newline():
    # Path.read_text(newline=...) is Python 3.13+. CI runs 3.12 (.github/workflows/tests.yml), so
    # docs-sync's apply.py failed every CI run while passing on a 3.14 machine.
    import ast

    hits = []
    for path in REPO.rglob("*.py"):
        if any(part in {".git", "node_modules", "archive", "__pycache__"} for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "read_text"
                    and any(k.arg == "newline" for k in node.keywords)):
                hits.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert not hits, f"Path.read_text(newline=) needs Python 3.13; use open(..., newline=...) instead: {hits}"
