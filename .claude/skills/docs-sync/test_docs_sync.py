"""Tests for sync.py: every check, the CLI modes and exit codes, and a run on the real wiki.

Most tests build a small fake repo under tmp_path and point sync.REPO_ROOT at
it, so the real wiki is never written. The fake wiki holds every claim in
sync.CLAIMS, worded exactly as the table has it, with the fake repo's numbers.
The CLI tests copy the scripts into the fake repo and run them there with a
real `python` process, so REPO_ROOT resolves to the fake repo exactly as it
resolves to the clone in real use.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("docs_sync_sync", HERE / "sync.py")
sync = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = sync  # dataclasses look their module up here
_spec.loader.exec_module(sync)

GUIDE = """# Guide

Agentic-Z includes 2 agents, 2 skills and 3 hooks. Tier 3 holds The 2 agents, the 2 skills, and the reference files.

## Contents

- [Agents](#agents)

## Agents

Agentic-Z has 2 agents.

| Agent | What it does |
| --- | --- |
| **Group** | |
| **Alpha** `alpha-agent` | Does alpha. |
| **Beta** `beta-agent` | Does beta. |

## Grading

Answer tests (evals) check 1 of the 2 agents. Answer tests cover 1 of the 2 agents. The 1 agents that use RAG search also send text off the machine.

The final grades cover 6 items. All 6 are at A+: 2 of the 2 agents, 2 of the 2 skills and 2 of the 2 shared items. The 2 shared items are neither agents nor skills. The final grades cover 6 items, and 6 are at A+: 2 of the 2 agents, 2 of the 2 skills and 2 of the 2 shared items.

The rules are split into a 3-line core and two topic files of 2 to 4 lines.

```
agents\\ | The 2 agents, one .md file each; skills\\ | The 2 skills, one folder each with its SKILL.md; The two DayZ rules topic files; hooks\\ | The 3 hooks: edit check
```

### Quality by version

| Item | v1 | final |
| --- | --- | --- |
| **Agents** | | |
| `alpha-agent` | B | A+ |
| `beta-agent` | not built | A+ |
| **Skills** | | |
| `bar` | A | A+ |
| `foo` | B | A+ |
| **Shared** | | |
| `_shared/x (README + 2 files)` | not built | A+ |
| Grading method note (this section) | not built | A+ |

## Status and next steps

Agentic-Z has 99 agents.
"""

TEAM = """# Team
| Agent memory | 1 of the 2 agents keep notes. |
This document describes the 2 agents and 2 skills that work together. Agentic-Z provides 2 slash commands. The 3 hooks are described in the hooks section.

The DayZ rules file is split into a 3-line core and two topic files of 2 to 4 lines. The final grades cover 6 items, and all 6 are at A+: 2 of the 2 agents, 2 of the 2 skills and 2 of the 2 shared items. The 2 shared items are neither agents nor skills. The final grades cover 6 items, and 6 are at A+: 2 of the 2 agents, 2 of the 2 skills and 2 of the 2 shared items.

## Quality by version

| Item | v1 | final |
| --- | --- | --- |
| Agents | | |
| `alpha-agent` | B | A+ |
| `beta-agent` | not built | A+ |
| Skills | | |
| `bar` | A | A+ |
| `foo` | B | A+ |
| Shared | | |
| `_shared/x (README + 2 files)` | not built | A+ |
| Grading method note | not built | A+ |
"""

SKILLS_TABLE = """| Skill | What it does |
| --- | --- |
| **Setup** | |
| `/foo` | Foo. |
| `/bar` | Bar. |
"""

APP = """const STATS = [
  ['2', 'agents'],
  ['2', 'skills'],
  ['3', 'hooks'],
  ['6', 'items graded A+'],
];
"""

CONTENT_JS = "const HIDDEN = new Set(['status-and-next-steps', 'open-items']);\n"

GRADES = [
    {"batch": "agents-a", "item": "alpha-agent", "grade": "A+", "reason": "r"},
    {"batch": "agents-b", "item": "beta-agent", "grade": "A+", "reason": "r"},
    {"batch": "skills-a", "item": "foo", "grade": "B", "reason": "r"},
    {"batch": "skills-a", "item": "bar", "grade": "A+", "reason": "r"},
    {"batch": "skills-b", "item": "foo", "grade": "A+", "reason": "r"},  # graded twice: latest wins, counts once
]
GRADES_SHARED = [
    {"batch": "shared", "item": "Pack: _shared/x (README + 2 files)", "grade": "A+", "reason": "r"},
    {"batch": "shared", "item": "Method note (read first)", "grade": "A+", "reason": "r"},
]


def build_repo(root: Path, with_scripts: bool = False) -> Path:
    """A fake clone whose wiki matches its sources exactly."""
    def w(rel: str, text: str) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")

    w("agents/alpha-agent.md", "---\nname: alpha-agent\nmemory: project\n"
                                        "tools: Read, mcp__dayz-rag__search_dayz_source\n---\n")
    w("agents/beta-agent.md", "---\nname: beta-agent\ntools: Read\n---\n"
                                       "memory: in the body is not frontmatter\ntools: mcp__dayz-rag__get_dayz_file\n")
    for name in ("foo", "bar"):
        w(f"skills/{name}/SKILL.md", f"---\nname: {name}\n---\n")
    for name in ("a_hook", "b_hook", "c_hook", "test_a_hook"):
        w(f"{sync.HOOKS_DIR}/{name}.py", "")
    w("evals/questions/alpha-agent.json", "{}")
    w("evals/questions/not-an-agent.json", "{}")
    w(f"{sync.GRADES_DIR}/final_grades.json", json.dumps(GRADES))
    w(f"{sync.GRADES_DIR}/final_grades_shared.json", json.dumps(GRADES_SHARED))
    w(sync.RULES_CORE, "a\nb\nc\n")
    w(f"{sync.RULES_TOPICS}/a.md", "a\nb\n")
    w(f"{sync.RULES_TOPICS}/b.md", "a\nb\nc\nd\n")
    w(sync.GUIDE, GUIDE)
    w(sync.TEAM, TEAM)
    w(sync.SKILLS_TABLE, SKILLS_TABLE)
    w(sync.APP_JSX, APP)
    w(sync.CONTENT_JS, CONTENT_JS)
    if with_scripts:
        # A docs-sync folder with its SKILL.md would be a third skill, so the
        # scripts live next to a SKILL.md only when the skills table lists it.
        dst = root / ".claude" / "skills" / "docs-sync"
        dst.mkdir(parents=True)
        for name in ("sync.py", "apply.py"):
            shutil.copy(HERE / name, dst / name)
        shared = root / "skills" / "_shared"
        shared.mkdir(parents=True, exist_ok=True)
        shutil.copy(HERE.parents[2] / "skills" / "_shared" / "skill_helpers.py", shared / "skill_helpers.py")
    return root


def edit(root: Path, rel: str, old: str, new: str) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {rel}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")


def run_cli(root: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    script = root / ".claude" / "skills" / "docs-sync" / "sync.py"
    if env is None:
        env = {k: v for k, v in os.environ.items() if k != sync.WIKI_ENV}  # the copy's own wiki/ folder
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, encoding="utf-8", env=env)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "REPO_ROOT", tmp_path)
    monkeypatch.delenv(sync.WIKI_ENV, raising=False)  # the fixture's own wiki/ folder is the wiki
    return build_repo(tmp_path)


# The real wiki lives in its own private repository, cloned next to this one. CI and
# public clones have no copy, so the checks against the real wiki skip there.
needs_wiki = pytest.mark.skipif(sync.wiki_dir() is None, reason=f"no {sync.WIKI_REPO} checkout next to this repo")


def problems() -> list[str]:
    return [str(p) for p in sync.run_checks()[1]]


def claim_match(root: Path, claim: sync.Claim) -> tuple[int, re.Match]:
    """(1-based line, match) of the first place the claim is found in its file."""
    for i, line in enumerate((root / claim.file).read_text(encoding="utf-8").split("\n"), 1):
        m = sync.claim_regex(claim).search(line)
        if m:
            return i, m
    raise AssertionError(f"claim not in {claim.file}: {claim.text}")


CLAIM_IDS = [f"{c.file.rsplit('/', 1)[-1]}:{c.text[:40]}" for c in sync.CLAIMS]


# ---------------------------------------------------------------- clean baseline

def test_matching_wiki_has_no_problems(repo):
    assert problems() == []


def test_facts_count_distinct_items_and_latest_grades(repo):
    facts = sync.gather_facts()
    counts = {k: v for k, (v, _) in facts.counts.items()}
    assert counts == {
        "agents": 2, "skills": 2, "hooks": 3, "eval_agents": 1, "memory_agents": 1,
        "rag_agents": 1,  # beta-agent names a dayz-rag tool only below its frontmatter
        "graded_agents": 2, "graded_skills": 2, "graded_shared": 2, "graded_total": 6,
        "aplus_agents": 2, "aplus_skills": 2, "aplus_shared": 2, "graded_aplus": 6,
        "core_lines": 3, "topic_files": 2, "topic_min": 2, "topic_max": 4,
    }
    assert facts.grades["skills"]["foo"] == "A+"  # the later entry wins


def test_line_count_matches_wc_l(tmp_path):
    f = tmp_path / "x.md"
    f.write_bytes(b"a\nb\nno trailing newline")
    assert sync.line_count(f) == 2


def test_slugify_matches_content_js():
    assert sync.slugify("What changed from Agentic-Z 1.6.0") == "what-changed-from-agentic-z-160"
    assert sync.slugify("Add-ons (planned)") == "add-ons-planned"
    assert sync.slugify("`docs-sync` é") == "docs-sync"


# ---------------------------------------------------------------- names

def test_missing_agent_is_reported_at_the_section(repo):
    (repo / "agents/gamma-agent.md").write_text("x", encoding="utf-8")
    out = problems()
    assert "wiki/src/content/guide.md:9: agent `gamma-agent` exists but is not listed in the \"## Agents\" tables" in out


def test_unknown_agent_is_reported_at_its_row(repo):
    edit(repo, sync.GUIDE, "`beta-agent` | Does", "`beta-agent` `ghost-agent` | Does")
    out = problems()
    assert any(p.startswith("wiki/src/content/guide.md:17: names agent `ghost-agent`, which does not exist") for p in out)


def test_agent_listed_twice_is_reported(repo):
    edit(repo, sync.GUIDE, "| **Beta** `beta-agent` | Does beta. |",
         "| **Beta** `beta-agent` | Does beta. |\n| **Alpha again** `alpha-agent` | x |")
    assert "wiki/src/content/guide.md:18: agent `alpha-agent` is listed 2 times (first at line 16)" in problems()


def test_missing_and_unknown_skills_are_reported(repo):
    (repo / "skills/baz").mkdir()
    (repo / "skills/baz/SKILL.md").write_text("x", encoding="utf-8")
    edit(repo, sync.SKILLS_TABLE, "| `/bar` | Bar. |", "| `/bar` | Bar. |\n| `/qux` | Gone. |")
    out = problems()
    assert "wiki/src/content/skills-table.md:1: skill `baz` exists but is not listed in the skills table" in out
    assert "wiki/src/content/skills-table.md:6: names skill `qux`, which does not exist" in out


def test_shared_folder_and_folders_without_skill_md_are_not_skills(repo):
    (repo / "skills/_shared/x").mkdir(parents=True)
    (repo / "skills/_shared/SKILL.md").write_text("x", encoding="utf-8")
    (repo / "skills/__pycache__").mkdir()
    assert problems() == []


def test_missing_agents_section_is_reported(repo):
    edit(repo, sync.GUIDE, "## Agents\n", "## Helpers\n")
    assert any('no "## Agents" section' in p for p in problems())


# ---------------------------------------------------------------- the claims table

def test_every_claim_names_known_facts_and_one_fact_per_number():
    facts = {"agents", "skills", "hooks", "eval_agents", "memory_agents", "rag_agents", "graded_agents", "graded_skills", "graded_shared",
             "graded_total", "aplus_agents", "aplus_skills", "aplus_shared", "graded_aplus",
             "core_lines", "topic_files", "topic_min", "topic_max"}
    for claim in sync.CLAIMS:
        assert claim.file in (sync.GUIDE, sync.TEAM, sync.APP_JSX), claim
        assert claim.text.count("{N}") == len(claim.facts), claim
        assert set(claim.facts) <= facts, claim
    assert len({(c.file, c.text) for c in sync.CLAIMS}) == len(sync.CLAIMS)


@needs_wiki
@pytest.mark.parametrize("claim", sync.CLAIMS, ids=CLAIM_IDS)
def test_each_claim_is_found_in_the_real_wiki(claim):
    hidden = sync.hidden_slugs()
    if claim.file == sync.APP_JSX:
        lines, visible = sync.read(claim.file).split("\n"), None
    else:
        doc = sync.load_doc(claim.file, hidden)
        lines, visible = doc.lines, doc.visible
    found = [i for i, line in enumerate(lines)
             if sync.claim_regex(claim).search(line) and (visible is None or visible[i])]
    assert found, f"{claim.text!r} is not in a visible part of {claim.file}"


# Counts in the visible wiki that no fact computes, left out of CLAIMS on
# purpose. Any other count of agents, skills, hooks or items must sit inside a
# CLAIMS match, or a source change would leave it stale with nothing flagging it.
NOT_FACTS = {
    (sync.TEAM, "six items"),          # an example request: "holds six items"
    (sync.GUIDE, "five gate agents"),
    (sync.GUIDE, "Two agents"),        # "Two agents have general web or remote design access"
    (sync.TEAM, "Three agents"),       # the Figma pipeline
    (sync.TEAM, "three skills"),       # the skills one reviewer graded without pytest
    (sync.TEAM, "21 skills"),          # skills named in the rules file's exception entries
}
COUNT = re.compile(sync.NUMBER + r"(?: of the \d+)?(?: [\w-]+)? (?:agents|skills|hooks|items)\b")


@needs_wiki
def test_every_visible_count_is_a_claim_or_known_not_to_be_a_fact():
    hidden = sync.hidden_slugs()
    stray = []
    for rel in (sync.GUIDE, sync.TEAM):
        doc = sync.load_doc(rel, hidden)
        for i, line in enumerate(doc.lines):
            if not doc.visible[i]:
                continue
            spans = [m.span() for c in sync.CLAIMS if c.file == rel for m in sync.claim_regex(c).finditer(line)]
            stray += [f"{rel}:{i + 1}: {m.group(0)!r}" for m in COUNT.finditer(line)
                      if not any(a <= m.start() and m.end() <= b for a, b in spans)
                      and (rel, m.group(0)) not in NOT_FACTS]
    assert stray == [], "add a CLAIMS entry for each count, or list it in NOT_FACTS if no fact computes it"


@needs_wiki
def test_real_repository_reports_no_missing_claim():
    _, found = sync.run_checks()
    assert not [str(p) for p in found if "claim not found" in p.message]


@pytest.mark.parametrize("index", range(len(sync.CLAIMS)), ids=CLAIM_IDS)
def test_a_changed_number_is_reported_and_fixed(repo, index):
    claim = sync.CLAIMS[index]
    line_no, m = claim_match(repo, claim)
    token = m.group(1)
    wrong = "seven" if not token.isdigit() else str(int(token) + 7)
    path = repo / claim.file
    original = path.read_text(encoding="utf-8")
    lines = original.split("\n")
    lines[line_no - 1] = lines[line_no - 1][:m.start(1)] + wrong + lines[line_no - 1][m.end(1):]
    path.write_text("\n".join(lines), encoding="utf-8", newline="")

    expected = sync.gather_facts().counts[claim.facts[0]][0]
    _, found = sync.run_checks()
    assert [p for p in found if p.fix is None] == []
    assert any(p.file == claim.file and p.line == line_no and p.old == wrong
               and str(p).startswith(f"{claim.file}:{line_no}: says {wrong}, expected {expected} (")
               for p in found), [str(p) for p in found]
    apply = sync.h.load_module("docs_sync_apply_claims", HERE / "apply.py")
    apply.apply_fixes(repo, found)
    assert path.read_text(encoding="utf-8") == original
    assert problems() == []


@pytest.mark.parametrize("index", range(len(sync.CLAIMS)), ids=CLAIM_IDS)
def test_a_removed_claim_is_reported_as_not_found(repo, index):
    claim = sync.CLAIMS[index]
    _, m = claim_match(repo, claim)
    edit(repo, claim.file, m.group(0), "Reworded.")
    shown = claim.text.replace("{N}", "N")
    out = problems()
    assert f'{claim.file}: claim not found: "{shown}"; update the CLAIMS table in sync.py' in out
    # Reported as a problem to hand-edit, never fixed by --apply.
    assert not any(p.fix for p in sync.run_checks()[1] if "claim not found" in p.message)


# Accurate or inaccurate sentences that look like claims but are not in the table.
LOOKALIKES = [
    "The lead dispatches 3 agents in parallel. Only 12 skills need P:\\ mounted.",
    "Each team lead has 4 agents under it. The DayZ lead covers 6 skills for packing.",
    "Agentic-Z has 7 agents in the UI team. Someone of the 9 agents was busy.",
    "The 3 agents: normalizer, translator, validator. The Figma pipeline runs the 3 agents in order.",
    "Answer tests check 9 of the 9 agents next year. The 9 shared items listed below are new.",
    "The final grades covered 99 items last year. This guide covers 8 agents and 8 skills.",
]


@pytest.mark.parametrize("sentence", LOOKALIKES)
def test_lookalike_sentences_are_ignored_and_left_alone(repo, sentence):
    edit(repo, sync.GUIDE, "Agentic-Z has 2 agents.", "Agentic-Z has 2 agents. " + sentence)
    edit(repo, sync.TEAM, "provides 2 slash commands.", "provides 2 slash commands. " + sentence)
    edit(repo, sync.APP_JSX, "];", "  ['9', 'agent hours'],\n];")
    before = {rel: (repo / rel).read_text(encoding="utf-8") for rel in (sync.GUIDE, sync.TEAM, sync.APP_JSX)}
    assert problems() == []
    assert sync.main(["--apply"]) == 0
    assert {rel: (repo / rel).read_text(encoding="utf-8") for rel in before} == before


def test_a_wrong_number_beside_a_claim_is_not_rewritten(repo):
    # Only the numbers inside a matched claim are touched; the rest of the line is not.
    edit(repo, sync.GUIDE, "Agentic-Z has 2 agents.", "Agentic-Z has 4 agents. It dispatches 4 agents at once.")
    assert sync.main(["--apply"]) == 0
    assert "Agentic-Z has 2 agents. It dispatches 4 agents at once." in (repo / sync.GUIDE).read_text(encoding="utf-8")


def test_number_words_are_read_and_rewritten_as_words(repo):
    edit(repo, sync.TEAM, "and two topic files of", "and Seven topic files of")
    assert problems() == [
        "wiki/src/content/team.md:5: says Seven, expected 2 (topic files in skills/_shared/conventions/) [fixable]"]
    assert sync._spell(2, "Seven") == "Two" and sync._spell(2, "7") == "2" and sync._spell(30, "three") == "30"
    assert sync._number("Twenty") == 20 and sync._number("143") == 143


def test_hidden_sections_are_skipped(repo):
    # "Agentic-Z has 99 agents." sits under "## Status and next steps", which content.js hides.
    assert problems() == []
    edit(repo, sync.CONTENT_JS, "'status-and-next-steps', ", "")
    assert problems() == ["wiki/src/content/guide.md:47: says 99, expected 2 (agent files in agents/) [fixable]"]


def test_a_claim_found_only_in_a_hidden_section_is_not_found(repo):
    edit(repo, sync.GUIDE, "Agentic-Z has 2 agents.\n", "\n")
    assert problems() == ['wiki/src/content/guide.md: claim not found: "Agentic-Z has N agents."; '
                          'update the CLAIMS table in sync.py']


def test_only_the_claims_check_skips_hidden_sections(repo):
    # The names check still reads a hidden "## Agents" table.
    edit(repo, sync.CONTENT_JS, "'open-items'", "'open-items', 'agents'")
    edit(repo, sync.GUIDE, "`beta-agent` | Does", "`beta-agent` `ghost-agent` | Does")
    out = problems()
    assert any('claim not found: "Agentic-Z has N agents."' in p for p in out)
    assert any("names agent `ghost-agent`, which does not exist" in p for p in out)


def test_hook_scripts_exclude_tests(repo):
    (repo / sync.HOOKS_DIR / "d_hook.py").write_text("", encoding="utf-8")
    (repo / sync.HOOKS_DIR / "test_d_hook.py").write_text("", encoding="utf-8")
    out = problems()
    assert "wiki/src/App.jsx:4: says 3, expected 4 (hook scripts in hooks/ (not test_*.py)) [fixable]" in out
    assert len(out) == 3  # App.jsx, the guide's opening sentence and its tree


def test_rules_line_counts_are_checked(repo):
    (repo / sync.RULES_CORE).write_text("a\nb\nc\nd\n", encoding="utf-8")
    (repo / sync.RULES_TOPICS / "c.md").write_text("x\n" * 9, encoding="utf-8")
    out = problems()
    # The rules sentence lives on the team page ("split into a N-line core and N topic files of N to N lines").
    assert any(p.startswith("wiki/src/content/team.md:5: says 3, expected 4 (wc -l") for p in out)
    assert any(p.startswith("wiki/src/content/team.md:5: says two, expected 3 (topic files") for p in out)
    assert any(p.startswith("wiki/src/content/team.md:5: says 4, expected 9 (longest topic file") for p in out)


@pytest.mark.parametrize("rel", [sync.RULES_CORE, f"{sync.RULES_TOPICS}/b.md"])
def test_locked_rules_file_is_a_source_error_not_a_traceback(repo, monkeypatch, capsys, rel):
    locked = repo / rel
    real = Path.read_bytes

    def read_bytes(self):
        if self == locked:
            raise PermissionError(13, "Permission denied")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    assert sync.main(["--check"]) == 1
    assert f"cannot read {rel}: Permission denied" in capsys.readouterr().err


@pytest.mark.parametrize("content", ["export const sections = [];\n", "const HIDDEN = [];\n"])
def test_missing_hidden_set_is_a_source_error(repo, capsys, content):
    # Without it, the hidden "99 agents" section would be checked instead of the run failing.
    (repo / sync.CONTENT_JS).write_text(content, encoding="utf-8")
    with pytest.raises(sync.SourceError, match=r"content\.js: no `const HIDDEN = new Set"):
        sync.run_checks()
    assert sync.main(["--check"]) == 1
    assert "expected" not in capsys.readouterr().out


# ---------------------------------------------------------------- grade tables

def test_grade_table_missing_row(repo):
    edit(repo, sync.TEAM, "| `bar` | A | A+ |\n", "")
    assert "wiki/src/content/team.md:7: graded item 'bar' (docs/grades/final_grades.json) has no row in this table" in problems()


def test_grade_table_row_not_in_grade_files(repo):
    edit(repo, sync.GUIDE, "| `foo` | B | A+ |", "| `foo` | B | A+ |\n| `old-skill` | B | A |")
    assert "wiki/src/content/guide.md:41: `old-skill` is not in the grade files (docs/grades/)" in problems()


def test_grade_table_duplicate_row(repo):
    edit(repo, sync.TEAM, "| `foo` | B | A+ |", "| `foo` | B | A+ |\n| `foo` | B | A+ |")
    assert "wiki/src/content/team.md:17: `foo` appears again (first at line 16); each graded item belongs in one row" in problems()


def test_grade_table_wrong_final_grade(repo):
    edit(repo, sync.GUIDE, "| `beta-agent` | not built | A+ |", "| `beta-agent` | not built | A |")
    out = problems()
    assert "wiki/src/content/guide.md:37: final grade of `beta-agent` is 'A', expected 'A+' (latest in docs/grades/final_grades.json)" in out
    # Not a count, so --apply does not touch it.
    assert not any(p.fix for p in sync.run_checks()[1])


# The shipped wiki states the true A+ count ("and N are at A+"), so CLAIMS holds no
# all_aplus claim. The fixture still has an "All N are at A+" sentence in each file;
# these claims keep the rule tested that such a sentence is reworded by hand, never rewritten.
ALL_APLUS_CLAIMS = [
    sync.Claim(sync.GUIDE, "The final grades cover {N} items. All {N} are at A+: {N} of the {N} agents, "
                           "{N} of the {N} skills and {N} of the {N} shared items.",
               ("graded_total", "graded_total") + sync._GRADED, all_aplus=True),
    sync.Claim(sync.TEAM, "The final grades cover {N} items, and all {N} are at A+: {N} of the {N} agents, "
                          "{N} of the {N} skills and {N} of the {N} shared items.",
               ("graded_total", "graded_total") + sync._GRADED, all_aplus=True),
]


def _beta_drops_to_a(repo, monkeypatch):
    """beta-agent drops to A (6 graded, 5 at A+); the true-count sentences and stats say so."""
    monkeypatch.setattr(sync, "CLAIMS", sync.CLAIMS + ALL_APLUS_CLAIMS)
    grades = [dict(g, grade="A") if g["item"] == "beta-agent" else g for g in GRADES]
    (repo / sync.GRADES_DIR / "final_grades.json").write_text(json.dumps(grades), encoding="utf-8")
    for rel in (sync.GUIDE, sync.TEAM):
        edit(repo, rel, "and 6 are at A+: 2 of the 2 agents", "and 5 are at A+: 1 of the 2 agents")


def test_true_count_sentence_follows_the_a_plus_count(repo):
    grades = [dict(g, grade="A") if g["item"] == "beta-agent" else g for g in GRADES]
    (repo / sync.GRADES_DIR / "final_grades.json").write_text(json.dumps(grades), encoding="utf-8")
    out = problems()
    assert any(p.startswith("wiki/src/content/guide.md:23: says 6, expected 5") for p in out)
    assert any(p.startswith("wiki/src/content/guide.md:23: says 2, expected 1") for p in out)


def test_not_every_item_at_a_plus_needs_a_hand_edit_not_a_rewrite(repo, capsys, monkeypatch):
    # beta-agent drops to A: 6 graded, 5 at A+. No number makes "cover 6 items. All N are
    # at A+" true, so --apply must not rewrite it into "cover 6 items. All 5 are at A+".
    _beta_drops_to_a(repo, monkeypatch)
    for rel in (sync.GUIDE, sync.TEAM):
        edit(repo, rel, "| `beta-agent` | not built | A+ |", "| `beta-agent` | not built | A |")
    edit(repo, sync.APP_JSX, "['6', 'items graded A+']", "['5', 'items graded A+']")
    before = {rel: (repo / rel).read_text(encoding="utf-8") for rel in (sync.GUIDE, sync.TEAM)}

    found = sync.run_checks()[1]
    hand = [p for p in found if "every graded item is A+" in p.message]
    assert [(p.file, p.fix) for p in hand] == [(sync.GUIDE, None), (sync.TEAM, None)]
    assert str(hand[0]) == ("wiki/src/content/guide.md:23: says every graded item is A+, "
                            "but 5 of 6 are; reword this sentence")
    assert not any(p.fix for p in found)
    assert sync.main(["--apply"]) == 1
    assert {rel: (repo / rel).read_text(encoding="utf-8") for rel in before} == before
    assert sync.main(["--check"]) == 1


def test_all_aplus_sentence_still_reports_its_other_numbers_without_fixing_them(repo, monkeypatch):
    # beta-agent drops to A, and guide.md's sentence also has a wrong agent count.
    # One run must report both the reword and the wrong count, and --apply must
    # leave that sentence alone.
    _beta_drops_to_a(repo, monkeypatch)
    for rel in (sync.GUIDE, sync.TEAM):
        edit(repo, rel, "| `beta-agent` | not built | A+ |", "| `beta-agent` | not built | A |")
    edit(repo, sync.APP_JSX, "['6', 'items graded A+']", "['5', 'items graded A+']")
    text = (repo / sync.GUIDE).read_text(encoding="utf-8")
    m = sync.claim_regex(ALL_APLUS_CLAIMS[0]).search(text)
    group = 4  # "{N} of the {N} agents": the graded_agents number
    edit(repo, sync.GUIDE, m.group(0), m.group(0)[:m.start(group) - m.start()] + "99" + m.group(0)[m.end(group) - m.start():])
    before = (repo / sync.GUIDE).read_text(encoding="utf-8")

    line = [p for p in sync.run_checks()[1] if p.file == sync.GUIDE and p.line == 23]
    assert any("every graded item is A+" in p.message for p in line)
    wrong = [p for p in line if p.message.startswith("says 99,")]
    assert len(wrong) == 1 and wrong[0].fix is None
    sync.main(["--apply"])
    assert (repo / sync.GUIDE).read_text(encoding="utf-8") == before


def test_skill_md_documents_the_all_aplus_hand_edit():
    text = (Path(sync.__file__).parent / "SKILL.md").read_text(encoding="utf-8")
    assert "says every graded item is A+, but X of Y are; reword this sentence" in text
    assert "all_aplus=True" in text


def test_grade_items_with_the_same_row_label_are_reported(repo):
    # "Pack: alpha-agent (old)" and "alpha-agent" both read as "alpha-agent"; one used to drop out unseen.
    shared = GRADES_SHARED + [{"batch": "shared", "item": "Pack: alpha-agent (old)", "grade": "B", "reason": "r"}]
    (repo / sync.GRADES_DIR / "final_grades_shared.json").write_text(json.dumps(shared), encoding="utf-8")
    out = [p for p in problems() if "same row label" in p]
    assert len(out) == 2 and all("'alpha-agent' and 'Pack: alpha-agent (old)'" in p for p in out)


def test_grade_table_uses_latest_grade_of_item_graded_twice(repo):
    edit(repo, sync.TEAM, "| `foo` | B | A+ |", "| `foo` | B | B |")
    assert any("final grade of `foo` is 'B', expected 'A+'" in p for p in problems())


def test_missing_grade_table_section(repo):
    edit(repo, sync.TEAM, "## Quality by version", "## Grades")
    assert 'wiki/src/content/team.md:1: no "Quality by version" section with the grade table' in problems()


def test_item_key_normalises_labels():
    assert sync.item_key("Pack: _shared/ai (README + 5 files)") == sync.item_key("`_shared/ai (README + 5 files)`")
    assert sync.item_key("Method note (read first)") == sync.item_key("Grading method note (the section)")
    assert sync.item_key("`vest\\_camo`") == "vest_camo"


# ---------------------------------------------------------------- sources

@pytest.mark.parametrize("name", sync.GRADE_FILES)
def test_missing_grade_file_is_a_source_error(repo, name):
    (repo / sync.GRADES_DIR / name).unlink()
    with pytest.raises(sync.SourceError, match=re.escape(f"cannot read {sync.GRADES_DIR}/{name}")):
        sync.run_checks()


def test_missing_grades_folder_is_a_source_error(repo, capsys):
    shutil.rmtree(repo / sync.GRADES_DIR)
    assert sync.main(["--check"]) == 1
    assert f"cannot read {sync.GRADES_DIR}/final_grades.json" in capsys.readouterr().err


@pytest.mark.parametrize("content, message", [
    ("{not json", "is not valid JSON"),
    ('{"item": "x"}', "must hold a JSON list"),
    ('[{"item": "x", "grade": "A+"}]', "entry 1 needs string fields"),
])
def test_bad_grade_file_is_a_source_error(repo, content, message):
    (repo / sync.GRADES_DIR / "final_grades.json").write_text(content, encoding="utf-8")
    with pytest.raises(sync.SourceError, match=message):
        sync.run_checks()


def test_unknown_batch_prefix_is_a_source_error_not_left_out_of_counts(repo):
    extra = GRADES + [{"batch": "mods-panel", "item": "agentic-z-panel", "grade": "A+", "reason": "r"}]
    (repo / sync.GRADES_DIR / "final_grades.json").write_text(json.dumps(extra), encoding="utf-8")
    with pytest.raises(sync.SourceError, match="final_grades.json has a batch starting 'mods'"):
        sync.run_checks()


def test_quiet_turns_an_unexpected_error_into_a_skipped_check(repo, capsys, monkeypatch):
    def denied(path):
        raise PermissionError(13, "Permission denied", str(path))
    monkeypatch.setattr(sync, "line_count", denied)
    assert sync.main(["--check", "--quiet"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    message = json.loads(captured.out)["systemMessage"]
    assert message.startswith("docs-sync: check skipped: PermissionError:")
    # Outside --quiet the same error is one failure line, not a traceback.
    assert sync.main(["--check"]) == 1
    err = capsys.readouterr().err
    assert "check failed: PermissionError:" in err and "Traceback" not in err


def remove_source(root: Path, what: str) -> str:
    """Break one count source in a fake repo; return the message the SourceError should carry."""
    if what == "agents":
        shutil.rmtree(root / "agents")
        return "cannot read agents/: folder is missing"
    if what == "conventions":
        shutil.rmtree(root / sync.RULES_TOPICS)
        return f"cannot read {sync.RULES_TOPICS}/: folder is missing"
    if what == "empty conventions":
        for p in (root / sync.RULES_TOPICS).glob("*.md"):
            p.unlink()
        return f"cannot read {sync.RULES_TOPICS}/: no *.md files"
    if what == "empty agents":
        for p in (root / "agents").glob("*.md"):
            p.unlink()
        return "cannot read agents/: no *.md files"
    if what == "evals":
        shutil.rmtree(root / "evals" / "questions")
        return "cannot read evals/questions/: folder is missing"
    if what == "empty evals":
        for p in (root / "evals" / "questions").glob("*.json"):
            p.unlink()
        return "cannot read evals/questions/: no *.json files"
    if what == "hooks":
        shutil.rmtree(root / sync.HOOKS_DIR)
        return f"cannot read {sync.HOOKS_DIR}/: folder is missing"
    if what == "only test hooks":
        for p in (root / sync.HOOKS_DIR).glob("*_hook.py"):
            if not p.name.startswith("test_"):
                p.unlink()
        return f"cannot read {sync.HOOKS_DIR}/: no hook scripts"
    if what == "non-utf8 wiki":
        (root / sync.GUIDE).write_bytes(b"# Guide\n\xff\xfe 2 agents\n")
        return f"cannot read {sync.GUIDE}: not valid UTF-8"
    if what == "non-utf8 grades":
        (root / sync.GRADES_DIR / "final_grades.json").write_bytes(b"[\xff]")
        return f"cannot read {sync.GRADES_DIR}/final_grades.json: not valid UTF-8"
    if what == "grades":
        shutil.rmtree(root / sync.GRADES_DIR)
        return f"cannot read {sync.GRADES_DIR}/final_grades.json"
    raise ValueError(what)


SOURCES = ["agents", "empty agents", "conventions", "empty conventions", "evals", "empty evals",
           "hooks", "only test hooks", "non-utf8 wiki", "non-utf8 grades", "grades"]


@pytest.mark.parametrize("what", SOURCES)
def test_missing_or_unreadable_source_is_a_source_error_not_a_zero_count(repo, capsys, what):
    message = remove_source(repo, what)
    with pytest.raises(sync.SourceError, match=re.escape(message)):
        sync.run_checks()
    assert sync.main(["--check"]) == 1
    captured = capsys.readouterr()
    assert message in captured.err and "expected 0" not in captured.out


# ---------------------------------------------------------------- CLI (in process)

def test_check_exit_codes(repo, capsys):
    assert sync.main([]) == 0
    assert "[OK]" in capsys.readouterr().out
    edit(repo, sync.GUIDE, "has 2 agents", "has 4 agents")
    assert sync.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "guide.md:11: says 4, expected 2" in out and "1 fixable with --apply" in out


def test_source_error_exits_1(repo, capsys):
    (repo / sync.GUIDE).unlink()
    assert sync.main(["--check"]) == 1
    assert "cannot read wiki/src/content/guide.md" in capsys.readouterr().err


def test_map_prints_each_check_and_every_claim(repo, capsys):
    assert sync.main(["--map"]) == 0
    out = capsys.readouterr().out
    for word in ("names", "claims", "grades", "eval_agents", "graded_total"):
        assert word in out
    for claim in sync.CLAIMS:
        assert claim.text.replace("{N}", "N") in out


def test_skill_md_points_at_map_instead_of_copying_the_claims():
    # --map prints the claims straight from CLAIMS; a hand copy in SKILL.md
    # would go out of date silently the next time CLAIMS changes.
    skill = (HERE / "SKILL.md").read_text(encoding="utf-8")
    assert "run `--map`" in skill
    copied = [c.text for c in sync.CLAIMS if c.text.replace("{N}", "N").strip(" .,") in skill]
    assert not copied, f"SKILL.md copies claims from CLAIMS; point at --map instead: {copied}"


@pytest.mark.parametrize("args", [["--dry-run"], ["--check", "--apply"], ["--apply", "--map"],
                                  ["--quiet", "--apply"], ["--quiet", "--map"]])
def test_usage_errors_exit_2(repo, args):
    with pytest.raises(SystemExit) as e:
        sync.main(args)
    assert e.value.code == 2


# ---------------------------------------------------------------- CLI (real process, Stop hook)

@pytest.fixture
def cli_repo(tmp_path):
    return build_repo(tmp_path, with_scripts=True)


def test_quiet_prints_nothing_when_in_sync(cli_repo):
    r = run_cli(cli_repo, "--check", "--quiet")
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")


def test_quiet_prints_one_system_message_line_on_problems(cli_repo):
    edit(cli_repo, sync.GUIDE, "has 2 agents", "has 4 agents")
    edit(cli_repo, sync.SKILLS_TABLE, "| `/bar` | Bar. |\n", "")
    r = run_cli(cli_repo, "--check", "--quiet")
    assert r.returncode == 0
    lines = r.stdout.splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"systemMessage": "docs-sync: 2 wiki problem(s), 1 fixable with --apply. Run /docs-sync."}


def test_quiet_reports_a_missing_claim_in_its_one_line(cli_repo):
    edit(cli_repo, sync.TEAM, "Agentic-Z provides 2 slash commands.", "Agentic-Z ships two dozen commands.")
    r = run_cli(cli_repo, "--check", "--quiet")
    assert r.returncode == 0
    assert json.loads(r.stdout) == {"systemMessage": "docs-sync: 1 wiki problem(s), 0 fixable with --apply. Run /docs-sync."}


@pytest.mark.parametrize("what", ["conventions", "evals", "non-utf8 wiki", "grades"])
def test_quiet_skips_the_check_for_a_broken_source_and_exits_0(cli_repo, what):
    message = remove_source(cli_repo, what)
    r = run_cli(cli_repo, "--check", "--quiet")
    assert (r.returncode, r.stderr) == (0, "")
    assert len(r.stdout.splitlines()) == 1
    assert json.loads(r.stdout)["systemMessage"].startswith(f"docs-sync: check skipped: {message}")


def test_cli_check_exits_1_on_problems_and_2_on_usage(cli_repo):
    assert run_cli(cli_repo).returncode == 0
    edit(cli_repo, sync.TEAM, "| `foo` | B | A+ |\n", "")
    r = run_cli(cli_repo, "--check")
    assert r.returncode == 1 and "graded item 'foo'" in r.stdout
    assert run_cli(cli_repo, "--dry-run").returncode == 2


# ---------------------------------------------------------------- the real repository

@needs_wiki
def test_checker_parses_the_real_repository():
    """The real wiki and sources parse; drift may be reported, but no source error and every section is found."""
    facts, found = sync.run_checks()
    assert facts.counts["agents"][0] > 0 and facts.counts["skills"][0] > 0
    assert facts.counts["graded_total"][0] > 0
    assert all(isinstance(p, sync.Problem) for p in found)
    assert not [str(p) for p in found if p.message.startswith("no ")]  # every section was found


def test_wiki_is_found_in_its_own_checkout(tmp_path, monkeypatch):
    # The wiki moved to DayZ-n-Chill/Agentic-Z-Wiki: a clone next to this repo is used, an
    # AGENTIC_Z_WIKI path wins, and an empty AGENTIC_Z_WIKI means there is no wiki.
    repo, sibling, other = tmp_path / "Agentic-Z", tmp_path / "Agentic-Z-Wiki", tmp_path / "elsewhere"
    for folder in (repo, sibling / "src" / "content", other / "src"):
        folder.mkdir(parents=True)
    (sibling / "src" / "content" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    monkeypatch.setattr(sync, "REPO_ROOT", repo)
    monkeypatch.delenv(sync.WIKI_ENV, raising=False)
    assert sync.wiki_dir() == sibling
    assert sync.source_path(sync.GUIDE) == sibling / "src" / "content" / "guide.md"
    assert sync.source_path("docs/grades/final_grades.json") == repo / "docs" / "grades" / "final_grades.json"
    assert sync.read(sync.GUIDE) == "# Guide\n"
    monkeypatch.setenv(sync.WIKI_ENV, str(other))
    assert sync.wiki_dir() == other
    monkeypatch.setenv(sync.WIKI_ENV, "")
    assert sync.wiki_dir() is None
    with pytest.raises(sync.SourceError, match="no wiki checkout"):
        sync.source_path(sync.GUIDE)


def test_no_wiki_is_nothing_to_check(cli_repo):
    # Public clones and CI have no wiki: --check says so and exits 0, and the Stop hook stays silent.
    env = {**os.environ, sync.WIKI_ENV: ""}
    r = run_cli(cli_repo, "--check", env=env)
    assert r.returncode == 0 and "no wiki to check" in r.stdout and sync.WIKI_REPO in r.stdout
    r = run_cli(cli_repo, "--check", "--quiet", env=env)
    assert (r.returncode, r.stdout) == (0, "")


def test_real_grade_items_stay_distinct_after_normalising():
    facts = sync.gather_facts()
    items = [item for kind in facts.grades.values() for item in kind]
    assert len({sync.item_key(i) for i in items}) == len(items)
