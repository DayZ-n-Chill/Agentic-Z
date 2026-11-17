"""The fail-closed contract of py3d's reproducible wheel."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest


PY3D_ROOT = Path(__file__).resolve().parents[1]
ROLLOUT_ROOT = PY3D_ROOT / "rollout"
BUILD_SCRIPT = ROLLOUT_ROOT / "build-wheel.ps1"
APPLY_SCRIPT = ROLLOUT_ROOT / "apply-s2-rollout.ps1"
SCHEMA_V2 = "py3d-wheel-manifest-v2"
BUILD_REQUIRES = ["setuptools==83.0.0"]
V2_FIELDS = {
    "build_requires",
    "filename",
    "python_version",
    "schema_version",
    "sha256",
    "source_date_epoch",
    "source_version",
}


def _powershell():
    executable = shutil.which("powershell")
    assert executable is not None, "powershell is required for rollout tests"
    return executable


def _v2_manifest(**overrides):
    manifest = {
        "schema_version": SCHEMA_V2,
        "filename": "py3d-1.4.0-py3-none-any.whl",
        "sha256": "a" * 64,
        "source_date_epoch": 1784937600,
        "source_version": "1.4.0",
        "python_version": "3.14.3",
        "build_requires": list(BUILD_REQUIRES),
    }
    manifest.update(overrides)
    return manifest


def _extract_apply_validation_block():
    source = APPLY_SCRIPT.read_text(encoding="utf-8")
    start = source.index("try {\n    $Manifest = Get-Content")
    end = source.index("\n$SourceVersion = Get-SourceVersion", start)
    return source[start:end]


def _run_apply_manifest_validation(tmp_path, manifest):
    manifest_path = tmp_path / "wheel-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=4) + "\n",
        encoding="utf-8",
    )
    harness = tmp_path / "validate-wheel-manifest.ps1"
    harness.write_text(
        "[CmdletBinding()]\n"
        "param([Parameter(Mandatory = $true)][string]$ManifestPath)\n"
        '$ErrorActionPreference = "Stop"\n'
        + _extract_apply_validation_block()
        + '\nWrite-Output "VALID"\n',
        encoding="utf-8",
    )
    return subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(harness),
            "-ManifestPath",
            str(manifest_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _builder_manifest_contract():
    source = BUILD_SCRIPT.read_text(encoding="utf-8")
    block = re.search(
        r"(?ms)^\s*\$Manifest = \[ordered\]@\{\s*(.*?)^\s*\}",
        source,
    )
    assert block is not None
    fields = set(re.findall(r"(?m)^\s*([a-z0-9_]+)\s*=", block.group(1)))
    schema = re.search(
        r'(?m)^\s*schema_version\s*=\s*"([^"]+)"',
        block.group(1),
    )
    assert schema is not None
    return fields, schema.group(1)


def _write_fake_python(path, wheel_bytes):
    payload = wheel_bytes.decode("ascii")
    path.write_text(
        "@echo off\n"
        'if "%~1"=="-c" (\n'
        "  echo 3.14.3\n"
        "  exit /b 0\n"
        ")\n"
        'set "wheel_dir=%~8"\n'
        '> "%wheel_dir%\\py3d-1.4.0-py3-none-any.whl" '
        f"<nul set /p={payload}\n"
        "exit /b 0\n",
        encoding="ascii",
    )


def _snapshot_tree(root):
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_v2_manifest_contract_matches_builder_and_apply_validator(tmp_path):
    """Breaks if producer and consumer stop sharing the v2 fields and schema."""
    fields, schema = _builder_manifest_contract()
    assert fields == V2_FIELDS
    assert schema == SCHEMA_V2

    result = _run_apply_manifest_validation(tmp_path, _v2_manifest())
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "VALID"


def test_v1_manifest_shape_is_rejected(tmp_path):
    """Breaks if the rollout starts accepting the v1 contract, which pins no
    toolchain, again."""
    manifest = {
        "schema_version": "py3d-wheel-manifest-v1",
        "filename": "py3d-1.4.0-py3-none-any.whl",
        "sha256": "a" * 64,
        "source_date_epoch": 1784937600,
        "source_version": "1.4.0",
    }
    result = _run_apply_manifest_validation(tmp_path, manifest)
    assert result.returncode != 0


def test_non_v2_schema_is_rejected(tmp_path):
    """Breaks if an unknown schema reaches the rollout."""
    result = _run_apply_manifest_validation(
        tmp_path,
        _v2_manifest(schema_version="py3d-wheel-manifest-v3"),
    )
    assert result.returncode != 0
    assert "tracked wheel manifest schema is unsupported" in (
        result.stdout + result.stderr
    )


def test_invalid_sha256_is_rejected(tmp_path):
    """Breaks if the consumer accepts an identity that is not a lower-case
    SHA-256."""
    result = _run_apply_manifest_validation(
        tmp_path,
        _v2_manifest(sha256="NOT-A-SHA256"),
    )
    assert result.returncode != 0
    assert "tracked wheel manifest SHA-256 is invalid" in (
        result.stdout + result.stderr
    )


@pytest.mark.parametrize("missing", [False, True])
def test_empty_or_missing_build_requires_is_rejected(tmp_path, missing):
    """Breaks if the manifest can omit the pinned toolchain."""
    manifest = _v2_manifest(build_requires=[])
    if missing:
        del manifest["build_requires"]
    result = _run_apply_manifest_validation(tmp_path, manifest)
    assert result.returncode != 0


def test_hash_mismatch_without_update_keeps_manifest_and_dist_exact(tmp_path):
    """Breaks if a FAIL publishes a wheel or re-seals the manifest."""
    source_root = tmp_path / "py3d"
    rollout_root = source_root / "rollout"
    package_root = source_root / "py3d"
    dist_root = source_root / "dist"
    rollout_root.mkdir(parents=True)
    package_root.mkdir()
    dist_root.mkdir()

    shutil.copy2(BUILD_SCRIPT, rollout_root / BUILD_SCRIPT.name)
    (source_root / "setup.py").write_text(
        'from setuptools import setup\nsetup(\n    version = "1.4.0",\n)\n',
        encoding="utf-8",
    )
    (package_root / "__init__.py").write_text(
        '__version__ = "1.4.0"\n',
        encoding="utf-8",
    )
    (source_root / "pyproject.toml").write_text(
        "[build-system]\n"
        'requires = ["setuptools==83.0.0"]\n'
        'build-backend = "setuptools.build_meta"\n',
        encoding="utf-8",
    )

    expected_sha = "0" * 64
    manifest_path = rollout_root / "wheel-manifest.json"
    manifest_path.write_text(
        json.dumps(_v2_manifest(sha256=expected_sha), indent=4) + "\n",
        encoding="utf-8",
    )
    (dist_root / "keep.txt").write_bytes(b"existing-dist-state")
    wheel_bytes = b"deterministic-wheel"
    fake_python = tmp_path / "fake-python.cmd"
    _write_fake_python(fake_python, wheel_bytes)

    manifest_before = manifest_path.read_bytes()
    dist_before = _snapshot_tree(dist_root)
    actual_sha = hashlib.sha256(wheel_bytes).hexdigest()
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(rollout_root / BUILD_SCRIPT.name),
            "-Python",
            str(fake_python),
            "-OutputDirectory",
            str(dist_root),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert (
        "The reproducible build does not match the pinned wheel identity."
        in output
    )
    assert f"expected={expected_sha} actual={actual_sha}" in output
    assert manifest_path.read_bytes() == manifest_before
    assert _snapshot_tree(dist_root) == dist_before
