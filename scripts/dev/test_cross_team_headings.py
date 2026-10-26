"""Cross-team handoff headings: every "For the <team> lead" heading a worker agent writes must be one
that dayz-lead copies after its table and dayz-orchestrator turns into a task, or the work is dropped.

Run with: py -m pytest scripts/dev/test_cross_team_headings.py
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO / "agents"
HEADING = re.compile(r'"For the (\w+) lead"')


def _text(name: str) -> str:
    return (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _headings(text: str) -> set[str]:
    return set(HEADING.findall(text))


def _worker_headings() -> dict[str, set[str]]:
    out = {}
    for path in sorted(AGENTS_DIR.glob("*.md")):
        if path.stem in {"dayz-lead", "dayz-orchestrator"}:
            continue
        found = _headings(path.read_text(encoding="utf-8"))
        if found:
            out[path.stem] = found
    return out


def test_lead_and_orchestrator_forward_every_worker_heading():
    lead = _headings(_text("dayz-lead"))
    orchestrator = _headings(_text("dayz-orchestrator"))
    missing = [
        f"{agent}: For the {team} lead (lead forwards: {team in lead}, orchestrator forwards: {team in orchestrator})"
        for agent, teams in _worker_headings().items()
        for team in sorted(teams)
        if team not in lead or team not in orchestrator
    ]
    assert not missing, "cross-team headings nobody forwards:\n" + "\n".join(missing)


def test_weapon_report_hands_art_list_on_and_reports_lint():
    report = _text("dayz-weapon-specialist").split("## Report", 1)[1]
    assert '"For the art lead"' in report
    assert "dayz-object-builder" in report
    assert "/dayz-lint" in report


def test_docs_writer_sends_scope_unknown_under_config_lead_heading():
    text = _text("dayz-docs-writer")
    scope_bullet = next(line for line in text.splitlines() if "`scope-unknown`" in line)
    assert '"For the config lead"' in scope_bullet
    report = text.split("## Report", 1)[1]
    assert '"For the config lead"' in report
    assert "On a direct call" in report and "use no lead headings" in report
    assert "conventions/config.md" in next(l for l in text.splitlines() if l.startswith("Follow Tier 2"))


def test_ai_specialist_report_uses_lead_headings_lint_and_reassign():
    # The Report said "under its own heading" and "for the config lead", so no exact heading
    # string existed and dayz-lead could drop the spawn setup and config classes.
    text = _text("dayz-ai-specialist")
    report = text.split("## Report", 1)[1]
    assert '"For the server lead"' in report and "dayz-server-admin" in report
    assert '"For the config lead"' in report and "dayz-config-specialist" in report
    assert "/dayz-lint" in report and '"Reassign"' in report
    tools = next(l for l in text.splitlines() if l.startswith("tools:"))
    assert "Bash" in tools and "Skill" in tools


def test_vehicle_report_has_direct_call_rule_and_leaves_cfgpatches_to_config_specialist():
    text = _text("dayz-vehicle-specialist")
    report = text.split("## Report", 1)[1]
    assert "On a direct call" in report and "use no lead headings" in report
    assert "Either of you may add a `CfgPatches` entry" not in text
    assert "The `CfgPatches` class is yours alone" in _text("dayz-config-specialist")
    assert "belongs to dayz-config-specialist alone" in text


def test_agent_creator_validates_with_the_whole_dev_suite():
    # Running only test_repo_integrity.py let a new worker with a misspelled "For the X lead"
    # heading pass validation; the heading check lives in this file.
    text = _text("agent-creator")
    assert "py -m pytest -q scripts/dev/`" in text, "agent-creator must validate with the whole scripts/dev suite"
    assert "py -m pytest -q scripts/dev/test_repo_integrity.py" not in text
    checklist = REPO / "docs" / "agent-registration.md"
    assert "docs/agent-registration.md" in text and checklist.is_file()
    steps = checklist.read_text(encoding="utf-8")
    assert "test_lead_and_orchestrator_forward_every_worker_heading" in steps
    assert "dayz-orchestrator.md" in steps, "a new cross-team heading must be forwarded by the orchestrator too"


def test_vehicle_specialist_listed_as_reader_of_config_and_scripts_topics():
    conv = (REPO / "skills" / "_shared" / "dayz-conventions.md").read_text(encoding="utf-8")
    for topic in ("config", "scripts"):
        row = next(l for l in conv.splitlines() if l.startswith(f"| `conventions/{topic}.md` |"))
        assert "vehicle-specialist" in row.rsplit("|", 2)[1], f"conventions/{topic}.md Read by must list vehicle-specialist"
