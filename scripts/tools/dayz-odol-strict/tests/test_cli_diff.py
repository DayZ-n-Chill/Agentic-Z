import copy
import json

import pytest

from dayz_odol_strict.__main__ import main
from dayz_odol_strict.diff import diff_anatomy
from dayz_odol_strict.errors import OdolStrictError
from dayz_odol_strict.inspect import build_strict_summary


def _summary():
    payload = b"X" * 120
    preflight = {
        "container_offset": 0,
        "input_sha256": "1" * 64,
        "n_lods": 1,
        "payload": payload,
        "payload_sha256": "2" * 64,
        "resolutions": [1.0],
        "version": 55,
    }
    worker = {
        "lod_actual_end": [100],
        "lod_end_table": [100],
        "lod_errors": {},
        "lod_start_table": [20],
        "lods": [
            {
                "face_count": 1,
                "material_count": 1,
                "material_names": ["a.rvmat"],
                "named_properties": [["class", "test"]],
                "normal_count": 3,
                "proxy_count": 1,
                "resolution": 1.0,
                "selection_names": ["Body"],
                "vertex_count": 3,
            }
        ],
        "n_lods": 1,
        "resolutions": [1.0],
        "version": 55,
    }
    backend = {
        "api_id": "odol_reader.ODOL.from_bytes-v1",
        "manifest_id": "test",
        "manifest_sha256": "3" * 64,
    }
    return build_strict_summary(preflight, worker, backend)


def _write_summary(path, value):
    path.write_text(
        json.dumps(value, sort_keys=True), encoding="utf-8", newline=""
    )
    return path


def test_self_diff_has_no_findings_and_is_deterministic():
    value = _summary()
    first = diff_anatomy(value, copy.deepcopy(value))
    second = diff_anatomy(value, copy.deepcopy(value))
    assert first == second == {
        "equal": True,
        "findings": [],
        "schema_version": "dayz-odol-diff-v1",
    }


@pytest.mark.parametrize(
    ("mutation", "path"),
    [
        (
            lambda value: value["lods"][0].__setitem__(
                "resolution", 2.0
            ),
            "/lods/0/resolution",
        ),
        (
            lambda value: value["lods"][0]["selection_names"].__setitem__(
                0, "Hull"
            ),
            "/lods/0/selection_names/0",
        ),
        (
            lambda value: value["lods"][0]["named_properties"][0].__setitem__(
                "value", "changed"
            ),
            "/lods/0/named_properties/0/value",
        ),
        (
            lambda value: value["lods"][0].__setitem__("proxy_count", 2),
            "/lods/0/proxy_count",
        ),
        (
            lambda value: value["lods"][0].__setitem__(
                "raw_sha256", "f" * 64
            ),
            "/lods/0/raw_sha256",
        ),
    ],
)
def test_each_directed_anatomy_mutation_has_one_exact_path(mutation, path):
    reference = _summary()
    candidate = copy.deepcopy(reference)
    mutation(candidate)
    result = diff_anatomy(reference, candidate)
    assert result["equal"] is False
    assert len(result["findings"]) == 1
    assert result["findings"][0]["path"] == path
    assert set(result["findings"][0]) == {
        "expected", "observed", "path"
    }


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.pop("schema_version"),
        lambda value: value.__setitem__("extra", True),
        lambda value: value.__setitem__("version", 52),
        lambda value: value.__setitem__("input_sha256", "short"),
        lambda value: value["lods"][0].__setitem__("proxy_count", -1),
    ],
)
def test_invalid_summary_is_rejected_before_comparison(mutation):
    candidate = _summary()
    mutation(candidate)
    with pytest.raises(OdolStrictError) as raised:
        diff_anatomy(_summary(), candidate)
    assert raised.value.code == "ODOL_SUMMARY_INVALID"


def test_huge_summary_number_is_invalid_without_overflow_traceback():
    """Rompe si un entero JSON hostil provoca OverflowError en diff."""
    candidate = _summary()
    candidate["lods"][0]["resolution"] = 10 ** 10000
    with pytest.raises(OdolStrictError) as raised:
        diff_anatomy(_summary(), candidate)
    assert raised.value.code == "ODOL_SUMMARY_INVALID"


@pytest.mark.parametrize(
    ("changed", "expected_exit"),
    [(False, 0), (True, 1)],
)
def test_diff_cli_exit_and_sorted_json(
    tmp_path, capsys, changed, expected_exit
):
    reference = _summary()
    candidate = copy.deepcopy(reference)
    if changed:
        candidate["lods"][0]["proxy_count"] = 2
    reference_path = _write_summary(tmp_path / "ref.json", reference)
    candidate_path = _write_summary(tmp_path / "own.json", candidate)
    exit_code = main(["diff", str(reference_path), str(candidate_path)])
    captured = capsys.readouterr()
    assert exit_code == expected_exit
    assert captured.err == ""
    result = json.loads(captured.out)
    assert result["equal"] is (not changed)
    assert captured.out == json.dumps(
        result, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ) + "\n"


def test_invalid_diff_cli_exits_two_without_traceback(tmp_path, capsys):
    reference = _write_summary(tmp_path / "ref.json", _summary())
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    assert main(["diff", str(reference), str(invalid)]) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["error"]["code"] == (
        "ODOL_SUMMARY_INVALID"
    )


def test_inspect_cli_success_and_error_exits(
    tmp_path, capsys, monkeypatch
):
    source = tmp_path / "model.p3d"
    source.write_bytes(b"fixture")

    monkeypatch.setattr(
        "dayz_odol_strict.__main__.inspect_odol",
        lambda *args, **kwargs: _summary(),
    )
    assert main([
        "inspect", str(source), "--backend-root", str(tmp_path)
    ]) == 0
    assert json.loads(capsys.readouterr().out) == _summary()

    def invalid(*args, **kwargs):
        raise OdolStrictError("ODOL_SIGNATURE_MISSING", "test invalid")

    monkeypatch.setattr("dayz_odol_strict.__main__.inspect_odol", invalid)
    assert main([
        "inspect", str(source), "--backend-root", str(tmp_path)
    ]) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["error"]["code"] == (
        "ODOL_SIGNATURE_MISSING"
    )


def test_json_output_is_atomic_equivalent_and_stdout_empty(
    tmp_path, capsys
):
    reference = _write_summary(tmp_path / "ref.json", _summary())
    candidate = _write_summary(tmp_path / "own.json", _summary())
    output = tmp_path / "result.json"
    assert main([
        "diff",
        str(reference),
        str(candidate),
        "--json",
        str(output),
    ]) == 0
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
    assert output.read_bytes().endswith(b"\n")
    assert json.loads(output.read_text(encoding="utf-8"))["equal"] is True


def test_unwritable_json_output_exits_two_without_traceback(
    tmp_path, capsys
):
    reference = _write_summary(tmp_path / "ref.json", _summary())
    candidate = _write_summary(tmp_path / "own.json", _summary())
    output = tmp_path / "missing-parent" / "result.json"

    assert main([
        "diff",
        str(reference),
        str(candidate),
        "--json",
        str(output),
    ]) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["error"]["code"] == (
        "ODOL_OUTPUT_UNWRITABLE"
    )
    assert not output.exists()
