from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


ROLLOUT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = ROLLOUT_ROOT / "apply-s2-rollout.ps1"
POWERSHELL = shutil.which("powershell")

WHEEL_NAME = "py3d-1.4.0-py3-none-any.whl"
WHEEL_BYTES = b"pytest pinned wheel\n"

MODEL_RELATIVE = "dayz-model-pipeline/SKILL.md"
PROXY_RELATIVE = "dayz-proxy-align/SKILL.md"
VIEWER_RELATIVE = "dayz-3d-viewer/SKILL.md"

MODEL_PREIMAGE = b"model header\npy3d >= 1.2.0\nmodel footer\n"
MODEL_POSTIMAGE = b"model header\npy3d >= 1.4.0\nmodel footer\n"
PROXY_PREIMAGE = b"proxy header\nlegacy lifecycle\nproxy footer\n"
PROXY_POSTIMAGE = b"proxy header\nstrict lifecycle\nproxy footer\n"
VIEWER_PREIMAGE = b"viewer unchanged\n"

MODEL_PATCH = """--- a/dayz-model-pipeline/SKILL.md
+++ b/dayz-model-pipeline/SKILL.md
@@ -1,3 +1,3 @@
 model header
-py3d >= 1.2.0
+py3d >= 1.4.0
 model footer
"""
PROXY_PATCH = """--- a/dayz-proxy-align/SKILL.md
+++ b/dayz-proxy-align/SKILL.md
@@ -1,3 +1,3 @@
 proxy header
-legacy lifecycle
+strict lifecycle
 proxy footer
"""


pytestmark = pytest.mark.skipif(
    POWERSHELL is None,
    reason="Windows PowerShell is required for rollout integration tests",
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_bytes(root: Path, relative: str, payload: bytes) -> Path:
    destination = root / Path(relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return destination


def _tree_state(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): _sha256_bytes(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@dataclass(frozen=True)
class RolloutFixture:
    script: Path
    target: Path
    backup: Path


def _make_fixture(tmp_path: Path) -> RolloutFixture:
    py3d_root = tmp_path / "bundle" / "py3d"
    rollout_root = py3d_root / "rollout"
    patches_root = rollout_root / "patches"
    target = tmp_path / "target-skills"
    backup = tmp_path / "external-backups"

    patches_root.mkdir(parents=True)
    shutil.copy2(SOURCE_SCRIPT, rollout_root / SOURCE_SCRIPT.name)

    package_root = py3d_root / "py3d"
    package_root.mkdir()
    (package_root / "__init__.py").write_text(
        '__version__ = "1.4.0"\n',
        encoding="utf-8",
        newline="\n",
    )
    (py3d_root / "setup.py").write_text(
        "setup(\n    version = \"1.4.0\",\n)\n",
        encoding="utf-8",
        newline="\n",
    )

    wheel_path = py3d_root / "dist" / WHEEL_NAME
    wheel_path.parent.mkdir()
    wheel_path.write_bytes(WHEEL_BYTES)
    wheel_manifest = {
        "schema_version": "py3d-wheel-manifest-v2",
        "filename": WHEEL_NAME,
        "sha256": _sha256_bytes(WHEEL_BYTES),
        "source_date_epoch": 1784937600,
        "source_version": "1.4.0",
        "python_version": "3.14.3",
        "build_requires": ["setuptools==83.0.0"],
    }
    (rollout_root / "wheel-manifest.json").write_text(
        json.dumps(wheel_manifest, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    (patches_root / "dayz-model-pipeline__SKILL.md.patch").write_text(
        MODEL_PATCH,
        encoding="utf-8",
        newline="\n",
    )
    (patches_root / "dayz-proxy-align__SKILL.md.patch").write_text(
        PROXY_PATCH,
        encoding="utf-8",
        newline="\n",
    )
    preimage_manifest = {
        "schema_version": "py3d-rollout-preimage-v1",
        "snapshot_id": "pytest-fixture",
        "entries": [
            {
                "relative_path": MODEL_RELATIVE,
                "preimage_sha256": _sha256_bytes(MODEL_PREIMAGE),
                "status": "patched",
                "patch_path": "patches/dayz-model-pipeline__SKILL.md.patch",
            },
            {
                "relative_path": PROXY_RELATIVE,
                "preimage_sha256": _sha256_bytes(PROXY_PREIMAGE),
                "status": "patched",
                "patch_path": "patches/dayz-proxy-align__SKILL.md.patch",
            },
            {
                "relative_path": VIEWER_RELATIVE,
                "preimage_sha256": _sha256_bytes(VIEWER_PREIMAGE),
                "status": "not_applicable",
                "reason": "fixture has no py3d 1.4.0 delta",
            },
        ],
    }
    (rollout_root / "preimage-manifest.json").write_text(
        json.dumps(preimage_manifest, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    _write_bytes(target, MODEL_RELATIVE, MODEL_PREIMAGE)
    _write_bytes(target, PROXY_RELATIVE, PROXY_PREIMAGE)
    _write_bytes(target, VIEWER_RELATIVE, VIEWER_PREIMAGE)
    for skill_name in (
        "dayz-model-pipeline",
        "dayz-proxy-align",
        "dayz-3d-viewer",
    ):
        _write_bytes(
            target,
            f"{skill_name}/wheels/{WHEEL_NAME}",
            WHEEL_BYTES,
        )

    return RolloutFixture(
        script=rollout_root / SOURCE_SCRIPT.name,
        target=target,
        backup=backup,
    )


def _run_rollout(
    fixture: RolloutFixture,
    *,
    no_write: bool = False,
    backup: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        str(POWERSHELL),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(fixture.script),
        "-TargetSkillRoot",
        str(fixture.target),
        "-BackupRoot",
        str(backup or fixture.backup),
    ]
    if no_write:
        command.append("-NoWrite")
    return subprocess.run(
        command,
        cwd=fixture.target.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def test_correct_preimage_applies_patch_and_matches_postimage(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path)

    result = _run_rollout(fixture)

    assert result.returncode == 0, _combined_output(result)
    assert (fixture.target / MODEL_RELATIVE).read_bytes() == MODEL_POSTIMAGE
    assert (fixture.target / PROXY_RELATIVE).read_bytes() == PROXY_POSTIMAGE
    assert (fixture.target / VIEWER_RELATIVE).read_bytes() == VIEWER_PREIMAGE
    assert not any(fixture.target.glob("_backup_*"))
    assert any(
        path.read_bytes() == MODEL_PREIMAGE
        for path in fixture.backup.rglob("dayz-model-pipeline/SKILL.md")
    )


def test_one_byte_preimage_mismatch_fails_without_writing(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path)
    model_path = fixture.target / MODEL_RELATIVE
    model_path.write_bytes(MODEL_PREIMAGE.replace(b"1.2.0", b"1.2.1"))
    expected = _sha256_bytes(MODEL_PREIMAGE)
    observed = _sha256_bytes(model_path.read_bytes())
    before = _tree_state(fixture.target)

    result = _run_rollout(fixture)

    assert result.returncode != 0
    assert (
        f"[FAIL] preimage mismatch: {MODEL_RELATIVE} "
        f"expected={expected} observed={observed}"
    ) in _combined_output(result)
    assert _tree_state(fixture.target) == before
    assert not fixture.backup.exists()


def test_already_applied_patch_is_ok_and_writes_nothing(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path)
    (fixture.target / MODEL_RELATIVE).write_bytes(MODEL_POSTIMAGE)
    (fixture.target / PROXY_RELATIVE).write_bytes(PROXY_POSTIMAGE)
    before = _tree_state(fixture.target)

    result = _run_rollout(fixture)

    output = _combined_output(result)
    assert result.returncode == 0, output
    assert f"[OK] already applied: {MODEL_RELATIVE}" in output
    assert f"[OK] already applied: {PROXY_RELATIVE}" in output
    assert _tree_state(fixture.target) == before
    assert not fixture.backup.exists()


def test_backup_root_inside_target_is_rejected(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path)
    before = _tree_state(fixture.target)

    result = _run_rollout(
        fixture,
        backup=fixture.target / "forbidden-backups",
    )

    assert result.returncode != 0
    assert "BackupRoot must be outside TargetSkillRoot" in _combined_output(result)
    assert _tree_state(fixture.target) == before


def test_no_write_mismatch_exits_nonzero_and_writes_nothing(tmp_path: Path) -> None:
    fixture = _make_fixture(tmp_path)
    proxy_path = fixture.target / PROXY_RELATIVE
    proxy_path.write_bytes(PROXY_PREIMAGE.replace(b"legacy", b"Legacy"))
    before = _tree_state(fixture.target)

    result = _run_rollout(fixture, no_write=True)

    assert result.returncode != 0
    assert f"[FAIL] preimage mismatch: {PROXY_RELATIVE}" in _combined_output(result)
    assert _tree_state(fixture.target) == before
    assert not fixture.backup.exists()


def test_pinned_wheel_name_with_wrong_hash_aborts_without_overwrite(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(tmp_path)
    wheel_path = (
        fixture.target / "dayz-model-pipeline" / "wheels" / WHEEL_NAME
    )
    wheel_path.write_bytes(b"tampered wheel\n")
    before = _tree_state(fixture.target)

    result = _run_rollout(fixture)

    assert result.returncode != 0
    assert "[FAIL] wheel hash mismatch: dayz-model-pipeline" in _combined_output(
        result
    )
    assert _tree_state(fixture.target) == before
    assert not fixture.backup.exists()


def test_old_wheel_is_verified_in_external_backup_before_replacement(
    tmp_path: Path,
) -> None:
    fixture = _make_fixture(tmp_path)
    wheels_root = fixture.target / "dayz-model-pipeline" / "wheels"
    (wheels_root / WHEEL_NAME).unlink()
    old_wheel = wheels_root / "py3d-1.3.0-py3-none-any.whl"
    old_payload = b"old pinned wheel\n"
    old_wheel.write_bytes(old_payload)

    result = _run_rollout(fixture)

    assert result.returncode == 0, _combined_output(result)
    assert not old_wheel.exists()
    assert (wheels_root / WHEEL_NAME).read_bytes() == WHEEL_BYTES
    backups = list(
        fixture.backup.rglob(
            "dayz-model-pipeline/wheels/py3d-1.3.0-py3-none-any.whl"
        )
    )
    assert len(backups) == 1
    assert backups[0].read_bytes() == old_payload


def test_earlier_py3d_dayz_wheel_next_to_the_pinned_one_is_replaced(
    tmp_path: Path,
) -> None:
    """A wheel of an earlier pin under the py3d_dayz name is stale too, even
    with the pinned wheel already exact beside it: left there, the skills'
    installer, which wants exactly one py3d_dayz-*-py3-none-any.whl, would
    refuse the directory or install the old one."""
    fixture = _make_fixture(tmp_path)
    wheels_root = fixture.target / "dayz-model-pipeline" / "wheels"
    old_wheel = wheels_root / "py3d_dayz-1.3.0-py3-none-any.whl"
    old_payload = b"earlier py3d_dayz pin\n"
    old_wheel.write_bytes(old_payload)

    result = _run_rollout(fixture)

    assert result.returncode == 0, _combined_output(result)
    assert not old_wheel.exists()
    assert [p.name for p in wheels_root.iterdir()] == [WHEEL_NAME]
    assert (wheels_root / WHEEL_NAME).read_bytes() == WHEEL_BYTES
    backups = list(
        fixture.backup.rglob(
            "dayz-model-pipeline/wheels/py3d_dayz-1.3.0-py3-none-any.whl"
        )
    )
    assert len(backups) == 1
    assert backups[0].read_bytes() == old_payload
