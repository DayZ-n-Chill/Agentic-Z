"""Repo-wide checks: agent team and plugin manifest, the references in agents, skills and packs,
no-token .bat wrappers, the knowledge-pack index and citations (and, with P:\\ mounted, that each
cited vanilla line exists), the preflight gate list, the Tier 1 files and the panel's skill scripts.

Run with: py -m pytest scripts/dev/test_repo_integrity.py
"""
from __future__ import annotations

import json
import re
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
    r"P:\\[^\s`]+:\d+|\.c:\d+|config\.cpp:\d+"
    r"|P:\\[^\s`]*\\[\w.-]+\.\w+"
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


# P:\...\file.ext:N or :N-M. A cited file must exist and reach the cited line.
CITED_LINE_RE = re.compile(r"(P:\\[^\s`:*?\"<>|()]+\.\w+):(\d+)(?:-(\d+))?")


@pytest.mark.skipif(not Path("P:/scripts").is_dir(), reason="P:\\ is not mounted with vanilla scripts")
def test_cited_vanilla_lines_exist_on_p():
    lines: dict[str, int | None] = {}
    bad = []
    for path in REF_FILES + sorted(SKILLS_DIR.rglob("*.c")):
        for m in CITED_LINE_RE.finditer(path.read_text(encoding="utf-8", errors="replace")):
            cited, last = m.group(1), int(m.group(3) or m.group(2))
            if cited not in lines:
                file = Path(cited)
                lines[cited] = len(file.read_bytes().splitlines()) if file.is_file() else None
            if lines[cited] is None or last > lines[cited]:
                found = "missing" if lines[cited] is None else f"has {lines[cited]} lines"
                bad.append(f"{_ref_id(path)}: {m.group(0)} ({found})")
    assert not bad, "citations of vanilla lines that do not exist:\n" + "\n".join(bad)


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
