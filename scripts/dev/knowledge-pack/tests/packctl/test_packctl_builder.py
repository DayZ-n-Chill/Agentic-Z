from __future__ import annotations

import json
import os
import stat
import zipfile
from pathlib import Path

import pytest

from packctl_testlib import run_git

from packctl.builder import build_archive


def codes(report: dict[str, object]) -> list[str]:
    return [str(item["code"]) for item in report["findings"]]


def test_two_clean_builds_are_byte_identical(repo_factory, tmp_path: Path) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})
    first = tmp_path / "one.zip"
    second = tmp_path / "two.zip"

    report_a = build_archive(root, first)
    report_b = build_archive(root, second)

    assert report_a["verdict"] == "PASS"
    assert report_b["verdict"] == "PASS"
    assert first.read_bytes() == second.read_bytes()
    assert report_a["artifacts"]["archive_sha256"] == report_b["artifacts"][
        "archive_sha256"
    ]


def test_zip_profile_and_manifest_counts(repo_factory, tmp_path: Path) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})
    output = tmp_path / "pack.zip"

    report = build_archive(root, output)

    assert report["verdict"] == "PASS"
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert names == sorted(names)
        assert names == ["LICENSE", "README.md", "manifest.json"]
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["payload_file_count"] == 2
        assert manifest["archive_member_count"] == 3
        for info in archive.infolist():
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.create_system == 3
            assert stat.S_IMODE(info.external_attr >> 16) == 0o644
        assert archive.comment == b""


def test_dirty_repo_is_rejected_without_output(repo_factory, tmp_path: Path) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})
    (root / "README.md").write_text("# Dirty\n", encoding="utf-8")
    output = tmp_path / "pack.zip"

    report = build_archive(root, output)

    assert "BUILD-DIRTY" in codes(report)
    assert not output.exists()


def test_unmapped_tracked_file_is_rejected(repo_factory, tmp_path: Path) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})
    (root / "extra.txt").write_text("extra\n", encoding="utf-8")
    run_git(root, "add", "extra.txt")
    run_git(root, "commit", "-qm", "extra")
    output = tmp_path / "pack.zip"

    report = build_archive(root, output)

    assert "SOURCE-UNMAPPED" in codes(report)
    assert not output.exists()


def test_payload_symlink_is_rejected(repo_factory, tmp_path: Path) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})
    target = root / "target.txt"
    target.write_text("target\n", encoding="utf-8")
    link = root / "linked.txt"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("This Windows environment does not permit symlink fixtures.")
    run_git(root, "add", "target.txt", "linked.txt")
    run_git(root, "commit", "-qm", "symlink fixture")
    output = tmp_path / "pack.zip"

    report = build_archive(root, output)

    assert "BUILD-REPARSE" in codes(report)
    assert not output.exists()
