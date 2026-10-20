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
    assert drift["src_newer"] == [] and drift["orphan"] == []


def test_detect_drift_src_newer_and_in_sync(repo):
    src = repo / ".claude" / "skills" / "foo" / "SKILL.md"
    mirror = repo / "wiki" / "docs" / "skills" / "foo.md"
    mirror.write_text("x", encoding="utf-8")

    _set_mtime(mirror, 1_000_000)
    _set_mtime(src, 1_000_100)
    assert sync.detect_drift()["src_newer"] == [src]

    # Within the 1-second tolerance counts as in sync.
    _set_mtime(src, 1_000_000.5)
    drift = sync.detect_drift()
    assert drift == {"missing_mirror": [], "src_newer": [], "orphan": []}


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
    assert sync.detect_drift() == {"missing_mirror": [], "src_newer": [], "orphan": []}


def test_apply_dry_run_changes_nothing(repo):
    orphan = repo / "wiki" / "docs" / "skills" / "gone.md"
    orphan.write_text("x", encoding="utf-8")

    assert sync.apply_all(dry_run=True) == 0

    assert orphan.exists()
    assert not (repo / "wiki" / "docs" / "skills" / "foo.md").exists()


def test_apply_dry_run_leaves_unchanged_mirror_timestamp(repo):
    sync.apply_all()
    src = repo / ".claude" / "skills" / "foo" / "SKILL.md"
    mirror = repo / "wiki" / "docs" / "skills" / "foo.md"
    _set_mtime(mirror, 1_000_000)
    _set_mtime(src, 2_000_000)

    sync.apply_all(dry_run=True)
    assert mirror.stat().st_mtime == 1_000_000

    # A real apply aligns the timestamp so the drift detector stops flagging it.
    sync.apply_all()
    assert mirror.stat().st_mtime == 2_000_000
    assert sync.detect_drift()["src_newer"] == []
