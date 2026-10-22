"""Repo-wide checks that keep the agent team and the plugin manifest in step.

Run with: python -m pytest scripts/dev/test_repo_integrity.py
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
    assert registered == AGENT_NAMES


def test_every_user_skill_is_registered_in_the_plugin():
    registered = {Path(p).name for p in PLUGIN["skills"]}
    on_disk = {p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")}
    assert registered == on_disk - TEMPLATE_ONLY_SKILLS


def test_registered_paths_exist():
    for rel in PLUGIN["agents"] + PLUGIN["skills"]:
        assert (REPO / rel).exists(), rel


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_agent_name_matches_filename(path):
    assert _frontmatter(path)["name"] == path.stem


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_search_tools_work_in_clones_and_plugin_installs(path):
    # A clone exposes the server as mcp__dayz-rag__*, a plugin install as
    # mcp__plugin_agentic-z_dayz-rag__*. Unknown names are dropped silently,
    # so an agent needs both to reach search in either setup.
    tools = set(_tools(path))
    for tool in tools:
        if tool.startswith("mcp__dayz-rag__"):
            assert tool.replace("mcp__dayz-rag__", "mcp__plugin_agentic-z_dayz-rag__") in tools
        if tool.startswith("mcp__plugin_agentic-z_dayz-rag__"):
            assert tool.replace("mcp__plugin_agentic-z_dayz-rag__", "mcp__dayz-rag__") in tools


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_agents_have_no_machine_specific_paths(path):
    # P:\ is the DayZ Tools work drive every user mounts; any other drive letter
    # is one person's machine.
    text = path.read_text(encoding="utf-8")
    assert not re.findall(r"\b[A-OQ-Z]:\\", text)


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_referenced_repo_files_exist(path):
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r"(?:\.claude/(?:skills|agents|mcp)|scripts)/[\w./-]+\.(?:md|py|bat)", text):
        assert (REPO / ref).exists(), f"{path.name} points at missing {ref}"


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_referenced_agents_exist(path):
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r"`((?:dayz|figma)-[a-z-]+)`", text):
        if ref == "dayz-rag":
            continue
        assert ref in AGENT_NAMES or (SKILLS_DIR / ref).exists(), f"{path.name} names unknown agent {ref}"


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_referenced_slash_skills_exist(path):
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r"(?<![\w/.])/((?:dayz|agentic|docs|sync|clean)-[a-z0-9-]+)", text):
        assert (SKILLS_DIR / ref / "SKILL.md").exists(), f"{path.name} names unknown skill /{ref}"


def test_lead_workers_are_agents():
    text = (AGENTS_DIR / "dayz-lead.md").read_text(encoding="utf-8")
    section = text.split("## Your workers", 1)[1].split("\n## ", 1)[0]
    table = "\n".join(line for line in section.splitlines() if line.startswith("|"))
    assert table
    for ref in re.findall(r"`([a-z-]+)`", table):
        assert ref in AGENT_NAMES, f"lead lists unknown worker {ref}"


# Gatekeepers check and report; they must not be able to change what they judge.
READ_ONLY_GATES = {"dayz-mod-reviewer", "dayz-mod-debugger", "dayz-build-checker", "dayz-ingame-tester"}


@pytest.mark.parametrize("name", sorted(READ_ONLY_GATES))
def test_gates_cannot_edit(name):
    path = AGENTS_DIR / f"{name}.md"
    assert not set(_tools(path)) & {"Edit", "Write", "NotebookEdit"}
    # Setting `memory` auto-enables Write and Edit for any path.
    assert "memory" not in _frontmatter(path)


# Roles that run others and write nothing themselves. Setting `memory` auto-enables
# Read, Write and Edit, so these must also carry no memory.
NO_WRITE_ROLES = {"dayz-lead"}


@pytest.mark.parametrize("name", sorted(NO_WRITE_ROLES))
def test_no_write_roles_have_no_write_tools_or_memory(name):
    path = AGENTS_DIR / f"{name}.md"
    assert not set(_tools(path)) & {"Edit", "Write", "NotebookEdit"}
    assert "memory" not in _frontmatter(path)


def test_ingame_tester_matches_gate():
    # dayz-ingame-tester is the fallback for `/dayz-gate ingame`, so its ready line,
    # settle time and client timeout must match the script's defaults.
    agent = (AGENTS_DIR / "dayz-ingame-tester.md").read_text(encoding="utf-8")
    gate = (SKILLS_DIR / "dayz-gate" / "gate.py").read_text(encoding="utf-8")
    ready_re = re.search(r'^DEFAULT_READY_RE = r"(.+)"$', gate, re.M).group(1)
    settle = int(re.search(r"^DEFAULT_SETTLE_S = (\d+)", gate, re.M).group(1))
    timeout = int(re.search(r"^DEFAULT_TIMEOUT_S = (\d+)", gate, re.M).group(1))
    assert 'add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S' in gate
    ready_line = re.search(r"log line matching `([^`]+)`", agent).group(1)
    assert re.search(ready_re, ready_line)
    assert (settle, timeout) == (30, 300)
    assert "keep reading 30 more seconds" in agent
    assert "Give up after five minutes" in agent


def test_layout_validator_keeps_its_gate_mode_no_edit_rule():
    # The validator holds Write and Edit for cleanup mode, so only this sentence
    # keeps it from changing a file it gates.
    text = (AGENTS_DIR / "dayz-layout-validator.md").read_text(encoding="utf-8")
    assert "gate mode" in text
    assert "report only and never write or edit any file" in text


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
    assert skills - wrapped - RUNNABLE_WITHOUT_BAT == set()


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
    assert len(set(texts.values())) == 1
