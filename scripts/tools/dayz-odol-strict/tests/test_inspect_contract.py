import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from dayz_odol_strict.errors import OdolStrictError
from dayz_odol_strict.inspect import build_strict_summary, inspect_odol


TOOL_ROOT = Path(__file__).parents[1]
SCHEMA_PATH = TOOL_ROOT / "schemas" / "dayz-odol-strict-v1.schema.json"


def _preflight():
    payload = bytes(range(200))
    return {
        "container_offset": 16,
        "input_sha256": "a" * 64,
        "n_lods": 2,
        "payload": payload,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "resolutions": [1.0, 1000.0],
        "version": 55,
    }


def _backend():
    return {
        "api_id": "odol_reader.ODOL.from_bytes-v1",
        "manifest_id": "test-backend-v1",
        "manifest_sha256": "b" * 64,
    }


def _worker():
    return {
        "lod_actual_end": [180, 80],
        "lod_end_table": [180, 80],
        "lod_errors": {},
        "lod_start_table": [100, 20],
        "lods": [
            {
                "face_count": 4,
                "material_count": 2,
                "material_names": ["z.rvmat", "a.rvmat"],
                "named_properties": [["z", "2"], ["a", "1"]],
                "normal_count": 6,
                "proxy_count": 1,
                "resolution": 1.0,
                "selection_names": ["Z", "A"],
                "vertex_count": 8,
            },
            {
                "face_count": 1,
                "material_count": 0,
                "material_names": [],
                "named_properties": [],
                "normal_count": 3,
                "proxy_count": 0,
                "resolution": 1000.0,
                "selection_names": [],
                "vertex_count": 3,
            },
        ],
        "n_lods": 2,
        "resolutions": [1.0, 1000.0],
        "version": 55,
    }


def test_complete_worker_result_becomes_schema_valid_deterministic_anatomy():
    summary = build_strict_summary(_preflight(), _worker(), _backend())
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(summary)
    assert summary["schema_version"] == "dayz-odol-strict-v1"
    assert summary["lod_count"] == 2
    assert [lod["index"] for lod in summary["lods"]] == [0, 1]
    assert summary["lods"][0]["declared_start"] == 100
    assert summary["lods"][1]["declared_start"] == 20
    assert summary["lods"][0]["selection_names"] == ["A", "Z"]
    assert summary["lods"][0]["named_properties"] == [
        {"name": "a", "value": "1"},
        {"name": "z", "value": "2"},
    ]
    assert summary["lods"][0]["selection_count"] == 2
    assert summary["lods"][0]["property_count"] == 2
    assert summary["lods"][0]["raw_sha256"] == hashlib.sha256(
        _preflight()["payload"][100:180]
    ).hexdigest()
    rendered = json.dumps(summary, sort_keys=True)
    assert "timestamp" not in rendered
    assert "C:\\" not in rendered


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.__setitem__("version", 54),
        lambda value: value.__setitem__("n_lods", 1),
        lambda value: value.__setitem__("resolutions", [1.0]),
        lambda value: value.__setitem__("lod_start_table", [20]),
        lambda value: value.__setitem__("lod_end_table", [80]),
        lambda value: value.__setitem__("lod_actual_end", [80]),
        lambda value: value.__setitem__("lods", value["lods"][:1]),
        lambda value: value.__setitem__("lod_errors", {"0": "failed"}),
        lambda value: value["lods"].__setitem__(0, None),
        lambda value: value["lods"][0].__setitem__("resolution", 2.0),
        lambda value: value["lods"][0].__setitem__("vertex_count", -1),
        lambda value: value["lods"][0].__setitem__(
            "material_count", 999
        ),
    ],
)
def test_count_table_error_none_or_anatomy_mismatch_is_partial(mutation):
    worker = _worker()
    mutation(worker)
    with pytest.raises(OdolStrictError) as raised:
        build_strict_summary(_preflight(), worker, _backend())
    assert raised.value.code == "ODOL_PARTIAL_RESULT"


def test_huge_backend_number_is_partial_without_overflow_traceback():
    """Rompe si float(int gigante) escapa del límite fail-closed."""
    worker = _worker()
    worker["resolutions"][0] = 10 ** 10000
    with pytest.raises(OdolStrictError) as raised:
        build_strict_summary(_preflight(), worker, _backend())
    assert raised.value.code == "ODOL_PARTIAL_RESULT"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["lod_start_table"].__setitem__(1, -1),
        lambda value: value["lod_end_table"].__setitem__(0, 201),
        lambda value: value["lod_end_table"].__setitem__(0, 100),
    ],
)
def test_out_of_bounds_or_empty_intervals_are_rejected(mutation):
    worker = _worker()
    mutation(worker)
    with pytest.raises(OdolStrictError) as raised:
        build_strict_summary(_preflight(), worker, _backend())
    assert raised.value.code == "ODOL_BOUNDARY_OOB"


def test_inexact_actual_end_is_rejected():
    worker = _worker()
    worker["lod_actual_end"][0] = 179
    with pytest.raises(OdolStrictError) as raised:
        build_strict_summary(_preflight(), worker, _backend())
    assert raised.value.code == "ODOL_BOUNDARY_INEXACT"


def test_overlap_is_checked_after_sort_not_table_order():
    worker = _worker()
    worker["lod_start_table"] = [50, 20]
    worker["lod_end_table"] = [100, 80]
    worker["lod_actual_end"] = [100, 80]
    with pytest.raises(OdolStrictError) as raised:
        build_strict_summary(_preflight(), worker, _backend())
    assert raised.value.code == "ODOL_BOUNDARY_OVERLAP"


def test_invalid_preflight_never_reaches_manifest_or_worker(
    tmp_path, monkeypatch
):
    source = tmp_path / "invalid.p3d"
    source.write_bytes(b"not a model")
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("backend boundary was crossed")

    monkeypatch.setattr(
        "dayz_odol_strict.inspect.verify_backend_manifest", forbidden
    )
    monkeypatch.setattr("dayz_odol_strict.inspect.invoke_worker", forbidden)
    with pytest.raises(OdolStrictError) as raised:
        inspect_odol(source, tmp_path)
    assert raised.value.code == "ODOL_SIGNATURE_MISSING"
    assert calls == []


def test_temporary_payload_staging_failure_is_backend_failure(
    tmp_path, monkeypatch
):
    """Rompe si un fallo I/O temporal escapa como traceback no contractual."""
    source = tmp_path / "input.p3d"
    source.write_bytes(b"synthetic input")
    monkeypatch.setattr(
        "dayz_odol_strict.inspect.preflight_odol_bytes",
        lambda _data: _preflight(),
    )
    monkeypatch.setattr(
        "dayz_odol_strict.inspect.verify_backend_manifest",
        lambda *_args, **_kwargs: _backend(),
    )
    original_write_bytes = Path.write_bytes

    def fail_payload_write(path, data):
        if path.name == "payload.p3d":
            raise OSError("synthetic staging failure")
        return original_write_bytes(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_payload_write)
    with pytest.raises(OdolStrictError) as raised:
        inspect_odol(source, tmp_path)
    assert raised.value.code == "ODOL_BACKEND_FAILURE"
