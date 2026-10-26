"""dayz-lead: a docs task gets a reviewer brief that can fail a wrong README, and the plugin root
rule picks one version folder from the plugin cache.

Run with: py -m pytest scripts/dev/test_lead_docs_gate_and_plugin_root.py
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEAD = (REPO / "agents" / "dayz-lead.md").read_text(encoding="utf-8")


def _gates() -> str:
    return LEAD.split("## Gates", 1)[1].split("\n## ", 1)[0]


def test_docs_task_brief_checks_readme_against_config():
    # The reviewer's checks never read a README, so a wrong classname or dependency list passed.
    gates = _gates()
    assert "dayz-docs-writer" in gates
    for needed in ("## Classnames", "scope = 2", "requiredAddons", "load order", "CRITICAL"):
        assert needed in gates, f"docs-task reviewer brief must cover {needed!r}"


def test_plugin_root_rule_names_the_cache_glob_and_a_version_choice():
    # "the plugins/ folder of the Claude config folder" gave no path and no rule when the
    # cache held two version folders, so the lead could hand workers stale paths.
    assert "Glob `**/.claude-plugin/plugin.json`" in LEAD
    assert r"cache\<marketplace>\agentic-z\<version>" in LEAD
    assert "$CLAUDE_CONFIG_DIR" in LEAD and "~/.claude" in LEAD
    assert "highest version" in LEAD


def test_body_stays_in_the_agent_creator_range():
    body = LEAD.split("\n---\n", 1)[1].strip().splitlines()
    assert 10 <= len(body) <= 60, f"dayz-lead body is {len(body)} lines"
