"""Tests for sync.py: drift detection, orphan pruning and dry-run safety.

Every test builds a throwaway repo under tmp_path and points sync.REPO_ROOT
at it, so the real wiki is never read or written.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("docs_sync_sync", Path(__file__).parent / "sync.py")
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)

SKILL_TEXT = "---\nname: foo\ndescription: \"Does foo. Use when foo.\"\n---\n\n# /foo\n\nBody.\n"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "REPO_ROOT", tmp_path)
    (tmp_path / ".claude" / "skills" / "foo").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "foo" / "SKILL.md").write_text(SKILL_TEXT, encoding="utf-8")
    (tmp_path / "wiki" / "docs" / "skills").mkdir(parents=True)
    (tmp_path / "wiki" / "docs" / "agents").mkdir(parents=True)
    return tmp_path


def _set_mtime(path: Path, t: float) -> None:
    os.utime(path, (t, t))


def test_detect_drift_missing_mirror(repo):
    drift = sync.detect_drift()
    assert drift["missing_mirror"] == [repo / ".claude" / "skills" / "foo" / "SKILL.md"]
    assert drift["stale"] == [] and drift["orphan"] == []


def test_detect_drift_compares_content_not_mtime(repo):
    src = repo / ".claude" / "skills" / "foo" / "SKILL.md"
    mirror = repo / "wiki" / "docs" / "skills" / "foo.md"

    # Hand-edited mirror that is NEWER than its source is still stale.
    mirror.write_text("x", encoding="utf-8")
    _set_mtime(src, 1_000_000)
    _set_mtime(mirror, 2_000_000)
    assert sync.detect_drift()["stale"] == [src]

    # Correct content with an OLDER mtime (fresh checkout, touch) is in sync.
    sync.apply_all()
    _set_mtime(mirror, 1_000_000)
    _set_mtime(src, 2_000_000)
    assert sync.detect_drift() == {"missing_mirror": [], "stale": [], "orphan": []}


def test_detect_drift_folded_description_regression(repo):
    """A mirror written by the old line parser (description rendered as '&gt;') is stale."""
    src = repo / ".claude" / "skills" / "foo" / "SKILL.md"
    src.write_text("---\nname: foo\ndescription: >\n  Does foo.\n---\n\n# /foo\n", encoding="utf-8")
    mirror = repo / "wiki" / "docs" / "skills" / "foo.md"
    mirror.write_text("---\nname: foo\n---\n\n## Overview\n\n&gt;\n\n# /foo\n", encoding="utf-8")
    assert sync.detect_drift()["stale"] == [src]
    sync.apply_all()
    text = mirror.read_text(encoding="utf-8")
    assert "&gt;" not in text and "Does foo." in text


def test_detect_drift_orphans_skip_hand_written_pages(repo):
    skills_wiki = repo / "wiki" / "docs" / "skills"
    (skills_wiki / "foo.md").write_text("x", encoding="utf-8")
    (skills_wiki / "gone.md").write_text("x", encoding="utf-8")
    (skills_wiki / "about.md").write_text("x", encoding="utf-8")
    (skills_wiki / "_category.md").write_text("x", encoding="utf-8")
    (repo / "wiki" / "docs" / "agents" / "old-agent.md").write_text("x", encoding="utf-8")

    orphans = sync.detect_drift()["orphan"]
    assert sorted(p.name for p in orphans) == ["gone.md", "old-agent.md"]


def test_shared_folder_is_not_a_skill(repo):
    shared = repo / ".claude" / "skills" / "_shared"
    shared.mkdir()
    (shared / "SKILL.md").write_text(SKILL_TEXT, encoding="utf-8")
    kinds = [(m.name, k) for _, m, k in sync.find_canonical_targets()]
    assert kinds == [("foo.md", "skill")]


def test_apply_writes_mirror_and_prunes_orphan(repo):
    orphan = repo / "wiki" / "docs" / "skills" / "gone.md"
    orphan.write_text("x", encoding="utf-8")
    keep = repo / "wiki" / "docs" / "skills" / "about.md"
    keep.write_text("x", encoding="utf-8")

    assert sync.apply_all() == 0

    mirror = repo / "wiki" / "docs" / "skills" / "foo.md"
    assert mirror.is_file()
    assert "## Overview" in mirror.read_text(encoding="utf-8")
    assert not orphan.exists()
    assert keep.exists()
    assert sync.detect_drift() == {"missing_mirror": [], "stale": [], "orphan": []}


def test_apply_dry_run_changes_nothing(repo):
    orphan = repo / "wiki" / "docs" / "skills" / "gone.md"
    orphan.write_text("x", encoding="utf-8")

    assert sync.apply_all(dry_run=True) == 0

    assert orphan.exists()
    assert not (repo / "wiki" / "docs" / "skills" / "foo.md").exists()


def test_apply_reports_invalid_frontmatter(repo):
    src = repo / ".claude" / "skills" / "foo" / "SKILL.md"
    src.write_text("---\nname: [unclosed\n---\nbody\n", encoding="utf-8")
    assert sync.apply_all() == 1
    assert not (repo / "wiki" / "docs" / "skills" / "foo.md").exists()
    assert sync.detect_drift()["missing_mirror"] == [src]
