"""Tests for sync.py: the read-only check between the repo and the wiki.

Every test builds a throwaway repo under tmp_path and points sync.REPO_ROOT
at it, so the real wiki is never read.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("docs_sync_sync", Path(__file__).parent / "sync.py")
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)

SKILLS_TABLE = """| Skill | What it does |
| --- | --- |
| **Setup** | |
| `/foo` | Does foo. |
"""

GUIDE = """## Agents

### All agents

| Agent | What it does |
| --- | --- |
| **Plan** | |
| **Lead** `lead-a` | Leads. |
| **Checker and tester** `check-b` `test-c` | Check and test. |

### Next section

| `not-an-agent` | ignored |
"""

APP = "const STATS = [\n  ['3', 'agents'],\n  ['1', 'skills'],\n  ['1', 'hooks'],\n  ['9', 'items graded A+'],\n];\n"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "REPO_ROOT", tmp_path)
    (tmp_path / ".claude" / "skills" / "foo").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "foo" / "SKILL.md").write_text("# /foo\n", encoding="utf-8")
    (tmp_path / ".claude" / "skills" / "_shared").mkdir()
    agents = tmp_path / ".claude" / "agents"
    agents.mkdir()
    for name in ("lead-a", "check-b", "test-c"):
        (agents / f"{name}.md").write_text("x", encoding="utf-8")
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "guard.py").write_text("", encoding="utf-8")
    (tmp_path / "hooks" / "test_guard.py").write_text("", encoding="utf-8")
    content = tmp_path / "wiki" / "src" / "content"
    content.mkdir(parents=True)
    (content / "skills-table.md").write_text(SKILLS_TABLE, encoding="utf-8")
    (content / "guide.md").write_text(GUIDE, encoding="utf-8")
    (tmp_path / "wiki" / "src" / "App.jsx").write_text(APP, encoding="utf-8")
    return tmp_path


def test_in_sync(repo):
    assert sync.detect_drift() == []


def test_one_row_can_name_several_agents(repo):
    assert sync.wiki_agents() == {"lead-a", "check-b", "test-c"}


def test_shared_folder_and_hook_tests_are_not_counted(repo):
    assert sync.repo_skills() == {"foo"}
    assert sync.repo_hooks() == {"guard"}


def test_skill_missing_from_wiki(repo):
    (repo / ".claude" / "skills" / "bar").mkdir()
    (repo / ".claude" / "skills" / "bar" / "SKILL.md").write_text("# /bar\n", encoding="utf-8")
    problems = sync.detect_drift()
    assert "The skill bar is in the repo but not in wiki/src/content/skills-table.md." in problems
    assert "wiki/src/App.jsx says 1 skills; the repo has 2." in problems


def test_wiki_names_a_skill_that_is_gone(repo):
    table = repo / "wiki" / "src" / "content" / "skills-table.md"
    table.write_text(SKILLS_TABLE + "| `/gone` | Old. |\n", encoding="utf-8")
    assert sync.detect_drift() == ["wiki/src/content/skills-table.md names the skill gone, which is not in the repo."]


def test_agent_missing_from_wiki(repo):
    (repo / ".claude" / "agents" / "new-d.md").write_text("x", encoding="utf-8")
    problems = sync.detect_drift()
    assert "The agent new-d is in the repo but not in wiki/src/content/guide.md (All agents)." in problems
    assert "wiki/src/App.jsx says 3 agents; the repo has 4." in problems


def test_names_outside_the_agents_table_are_ignored(repo):
    assert "not-an-agent" not in sync.wiki_agents()


def test_missing_agents_table_is_reported(repo):
    (repo / "wiki" / "src" / "content" / "guide.md").write_text("## Agents\n", encoding="utf-8")
    assert sync.detect_drift() == ["Cannot find the wiki's agent list in wiki/src/content/guide.md (All agents)."]


def test_check_never_writes(repo):
    (repo / ".claude" / "agents" / "new-d.md").write_text("x", encoding="utf-8")
    before = {p: p.read_bytes() for p in (repo / "wiki").rglob("*") if p.is_file()}
    sync.main(["--check"])
    assert {p: p.read_bytes() for p in (repo / "wiki").rglob("*") if p.is_file()} == before


def test_check_with_drift_exits_1(repo, capsys):
    (repo / ".claude" / "agents" / "new-d.md").write_text("x", encoding="utf-8")
    assert sync.main(["--check"]) == 1
    assert "2 place(s) where the wiki and the repo disagree" in capsys.readouterr().out


def test_check_in_sync_exits_0(repo, capsys):
    assert sync.main([]) == 0
    assert "the wiki matches the repo" in capsys.readouterr().out


def test_quiet_drift_emits_system_message_json(repo, capsys):
    (repo / ".claude" / "agents" / "new-d.md").write_text("x", encoding="utf-8")
    assert sync.main(["--check", "--quiet"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    assert json.loads(out) == {
        "systemMessage": "docs-sync: 2 place(s) where the wiki and the repo disagree. Run /docs-sync."
    }


def test_quiet_in_sync_is_silent(repo, capsys):
    assert sync.main(["--quiet"]) == 0
    assert capsys.readouterr().out == ""


def test_apply_is_gone(repo):
    with pytest.raises(SystemExit) as exc:
        sync.main(["--apply"])
    assert exc.value.code == 2
