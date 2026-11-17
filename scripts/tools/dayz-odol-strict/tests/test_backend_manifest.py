import hashlib
import json
from pathlib import Path
import shutil

import pytest

from dayz_odol_strict.errors import OdolStrictError
from dayz_odol_strict.manifest import verify_backend_manifest
from dayz_odol_strict.worker import invoke_worker


FAKE_BACKEND = Path(__file__).with_name("fake_backend")


def _write_manifest(
    tmp_path,
    files=("odol_reader.py",),
    source_root=FAKE_BACKEND,
):
    value = {
        "api_id": "odol_reader.ODOL.from_bytes-v1",
        "files": [
            {
                "path": name,
                "sha256": hashlib.sha256(
                    (source_root / name).read_bytes()
                ).hexdigest(),
            }
            for name in files
        ],
        "manifest_id": "test-backend-v1",
        "schema_version": "odol-backend-manifest-v1",
    }
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(value, sort_keys=True), encoding="utf-8", newline=""
    )
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_fake_root(tmp_path):
    root = tmp_path / "backend"
    root.mkdir()
    shutil.copyfile(
        FAKE_BACKEND / "odol_reader.py", root / "odol_reader.py"
    )
    return root


def test_exact_backend_manifest_returns_pinned_identity(tmp_path):
    root = _copy_fake_root(tmp_path)
    manifest, manifest_hash = _write_manifest(tmp_path)
    verified = verify_backend_manifest(root, manifest, manifest_hash)
    assert verified["api_id"] == "odol_reader.ODOL.from_bytes-v1"
    assert verified["manifest_id"] == "test-backend-v1"
    assert verified["manifest_sha256"] == manifest_hash
    assert verified["root"] == root.resolve()


@pytest.mark.parametrize("missing", ["root", "manifest", "file"])
def test_absent_root_manifest_or_backend_file_is_missing(tmp_path, missing):
    root = _copy_fake_root(tmp_path)
    manifest, manifest_hash = _write_manifest(tmp_path)
    if missing == "root":
        root = tmp_path / "absent-root"
    elif missing == "manifest":
        manifest = tmp_path / "absent-manifest.json"
    else:
        (root / "odol_reader.py").unlink()
    with pytest.raises(OdolStrictError) as raised:
        verify_backend_manifest(root, manifest, manifest_hash)
    assert raised.value.code == "ODOL_BACKEND_MISSING"


def test_changed_backend_byte_is_drift(tmp_path):
    root = _copy_fake_root(tmp_path)
    manifest, manifest_hash = _write_manifest(tmp_path)
    (root / "odol_reader.py").write_bytes(
        (root / "odol_reader.py").read_bytes() + b"\n# drift\n"
    )
    with pytest.raises(OdolStrictError) as raised:
        verify_backend_manifest(root, manifest, manifest_hash)
    assert raised.value.code == "ODOL_BACKEND_DRIFT"


@pytest.mark.parametrize("bad_path", ["../outside.py", "C:/outside.py"])
def test_relative_path_escape_or_absolute_file_is_drift(tmp_path, bad_path):
    root = _copy_fake_root(tmp_path)
    manifest, _manifest_hash = _write_manifest(tmp_path)
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["files"][0]["path"] = bad_path
    manifest.write_text(
        json.dumps(value, sort_keys=True), encoding="utf-8", newline=""
    )
    expected_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    with pytest.raises(OdolStrictError) as raised:
        verify_backend_manifest(root, manifest, expected_hash)
    assert raised.value.code == "ODOL_BACKEND_DRIFT"


def test_manifest_byte_drift_is_rejected_before_file_checks(tmp_path):
    root = _copy_fake_root(tmp_path)
    manifest, manifest_hash = _write_manifest(tmp_path)
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(OdolStrictError) as raised:
        verify_backend_manifest(root, manifest, manifest_hash)
    assert raised.value.code == "ODOL_BACKEND_DRIFT"


def _worker_payload():
    return {
        "lod_actual_end": [120],
        "lod_end_table": [120],
        "lod_errors": {},
        "lod_start_table": [20],
        "lods": [
            {
                "face_count": 2,
                "material_names": ["mat.rvmat"],
                "named_properties": [["class", "test"]],
                "normal_count": 3,
                "proxy_count": 1,
                "resolution": 1.0,
                "selection_names": ["A", "B"],
                "vertex_count": 3,
            }
        ],
        "n_lods": 1,
        "resolutions": [1.0],
        "version": 55,
    }


def test_isolated_worker_returns_only_serializable_backend_fields(tmp_path):
    root = _copy_fake_root(tmp_path)
    manifest, manifest_hash = _write_manifest(tmp_path)
    verified = verify_backend_manifest(root, manifest, manifest_hash)
    payload_path = tmp_path / "payload.bin"
    payload_path.write_text(
        json.dumps(_worker_payload()), encoding="utf-8", newline=""
    )
    result = invoke_worker(payload_path, verified)
    assert result["version"] == 55
    assert result["lods"][0] == {
        "face_count": 2,
        "material_count": 1,
        "material_names": ["mat.rvmat"],
        "named_properties": [["class", "test"]],
        "normal_count": 3,
        "proxy_count": 1,
        "resolution": 1.0,
        "selection_names": ["A", "B"],
        "vertex_count": 3,
    }
    assert "verdict" not in result
    assert str(root) not in json.dumps(result)


def test_isolated_worker_does_not_import_unpinned_python_from_backend_root(
    tmp_path,
):
    root = _copy_fake_root(tmp_path)
    reader_path = root / "odol_reader.py"
    reader_path.write_text(
        "import backend_helper\n"
        + reader_path.read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="",
    )
    (root / "backend_helper.py").write_text(
        "import struct\nassert struct.calcsize('<I') == 4\n",
        encoding="utf-8",
        newline="",
    )
    marker_path = root / "intruder-imported"
    (root / "struct.py").write_text(
        "from pathlib import Path\n"
        "Path(__file__).with_name('intruder-imported').write_text("
        "'yes', encoding='utf-8')\n"
        "def calcsize(_format):\n"
        "    return 4\n",
        encoding="utf-8",
        newline="",
    )
    manifest, manifest_hash = _write_manifest(
        tmp_path,
        files=("backend_helper.py", "odol_reader.py"),
        source_root=root,
    )
    verified = verify_backend_manifest(root, manifest, manifest_hash)
    payload_path = tmp_path / "payload.bin"
    payload_path.write_text(
        json.dumps(_worker_payload()), encoding="utf-8", newline=""
    )

    result = invoke_worker(payload_path, verified)

    assert result["version"] == 55
    assert not marker_path.exists()


def test_isolated_worker_exception_is_backend_failure(tmp_path):
    root = _copy_fake_root(tmp_path)
    manifest, manifest_hash = _write_manifest(tmp_path)
    verified = verify_backend_manifest(root, manifest, manifest_hash)
    payload_path = tmp_path / "payload.bin"
    payload_path.write_bytes(b"FAIL")
    with pytest.raises(OdolStrictError) as raised:
        invoke_worker(payload_path, verified)
    assert raised.value.code == "ODOL_BACKEND_FAILURE"
