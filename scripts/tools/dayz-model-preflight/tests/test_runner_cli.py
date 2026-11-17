import hashlib
import json
from pathlib import Path

import py3d
import pytest

from dayz_model_preflight import runner
from dayz_model_preflight.__main__ import main
from dayz_model_preflight.errors import PreflightError
from dayz_model_preflight.runner import run_preflight

from _support import box_points, contract_value, make_lod, save_model


@pytest.fixture(autouse=True)
def accept_versioned_test_fork(monkeypatch):
    monkeypatch.setattr(
        runner, "require_dayz_py3d", lambda module=None: py3d
    )


def _case(tmp_path, dimensions=(2.0, 4.0, 6.0)):
    points = box_points(dimensions)
    source = save_model(
        tmp_path / "source.p3d", [make_lod(points)]
    )
    target = save_model(
        tmp_path / "target.p3d",
        [
            make_lod(
                points, selections={"Pelvis": {"points": [0]}}
            )
        ],
    )
    contract = contract_value()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(contract, sort_keys=True),
        encoding="utf-8",
        newline="",
    )
    return source, target, contract_path


def _snapshot(directory):
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.iterdir()
        if path.is_file()
    }


def test_run_preflight_positive_has_deterministic_result_contract(tmp_path):
    _source, target, contract = _case(tmp_path)
    first = run_preflight(target, contract)
    second = run_preflight(target, contract)
    assert first == second
    assert first["schema_version"] == "dayz-model-preflight-result-v1"
    assert first["verdict"] == "PASS"
    assert not any(
        item["severity"] == "ERROR" for item in first["findings"]
    )
    assert first["model_sha256"] == hashlib.sha256(
        target.read_bytes()
    ).hexdigest()
    assert first["contract_sha256"] == hashlib.sha256(
        contract.read_bytes()
    ).hexdigest()
    rendered = json.dumps(first, sort_keys=True)
    assert str(tmp_path) not in rendered
    assert "timestamp" not in rendered


def test_valid_scale_failure_is_fail_not_invalid(tmp_path):
    _source, target, contract = _case(
        tmp_path, dimensions=(2.0, 4.2, 6.0)
    )
    result = run_preflight(target, contract)
    assert result["verdict"] == "FAIL"
    assert "PREFLIGHT_SCALE_MISMATCH" in {
        item["code"] for item in result["findings"]
    }


def test_invalid_contract_and_unreadable_models_are_invalid(tmp_path):
    _source, target, contract = _case(tmp_path)
    contract.write_text("{}", encoding="utf-8")
    result = run_preflight(target, contract)
    assert result["verdict"] == "INVALID"
    assert result["findings"][0]["code"] == "PREFLIGHT_CONTRACT_INVALID"

    _source, target, contract = _case(tmp_path)
    target.write_bytes(b"not-an-mlod")
    result = run_preflight(target, contract)
    assert result["verdict"] == "INVALID"
    assert result["findings"][0]["code"] == "PREFLIGHT_MODEL_UNREADABLE"

    _source, target, contract = _case(tmp_path)
    (tmp_path / "source.p3d").write_bytes(b"not-an-mlod")
    result = run_preflight(target, contract)
    assert result["verdict"] == "INVALID"
    assert result["findings"][0]["code"] == "PREFLIGHT_MODEL_UNREADABLE"


@pytest.mark.parametrize("corruption", ["nonfinite_point", "invalid_index"])
def test_parseable_but_unsafe_model_is_invalid_without_traceback(
    tmp_path, corruption
):
    _source, target, contract = _case(tmp_path)
    with target.open("rb") as stream:
        model = py3d.P3D(stream)
    if corruption == "nonfinite_point":
        model.lods[0].points[0].coords = (float("nan"), 0.0, 0.0)
    else:
        model.lods[0].faces[0].vertices[0].point_index = len(
            model.lods[0].points
        )
    model.save(target)

    result = run_preflight(target, contract)

    assert result["verdict"] == "INVALID"
    assert [item["code"] for item in result["findings"]] == [
        "PREFLIGHT_MODEL_UNREADABLE"
    ]


def test_unexpected_py3d_validation_error_is_invalid_without_traceback(
    tmp_path, monkeypatch
):
    _source, target, contract = _case(tmp_path)

    def broken_validation(*args, **kwargs):
        raise RuntimeError("directed validation failure")

    monkeypatch.setattr(runner, "collect_py3d_findings", broken_validation)
    result = run_preflight(target, contract)

    assert result["verdict"] == "INVALID"
    assert [item["code"] for item in result["findings"]] == [
        "PREFLIGHT_MODEL_UNREADABLE"
    ]


def test_dependency_failure_is_invalid_before_model_parse(tmp_path, monkeypatch):
    _source, target, contract = _case(tmp_path)
    target.write_bytes(b"not-an-mlod")

    def unavailable(module=None):
        raise PreflightError(
            "PREFLIGHT_PY3D_UNAVAILABLE", "test dependency failure"
        )

    monkeypatch.setattr(runner, "require_dayz_py3d", unavailable)
    result = run_preflight(target, contract)
    assert result["verdict"] == "INVALID"
    assert [item["code"] for item in result["findings"]] == [
        "PREFLIGHT_PY3D_UNAVAILABLE"
    ]


@pytest.mark.parametrize("kind", ["pass", "fail", "invalid"])
def test_every_verdict_preserves_inputs_and_creates_no_p3d(tmp_path, kind):
    dimensions = (2.0, 4.0, 6.0)
    if kind == "fail":
        dimensions = (2.0, 4.2, 6.0)
    _source, target, contract = _case(tmp_path, dimensions)
    if kind == "invalid":
        contract.write_text("{", encoding="utf-8")
    before = _snapshot(tmp_path)
    result = run_preflight(target, contract)
    after = _snapshot(tmp_path)
    assert after == before
    assert result["verdict"] == kind.upper()
    assert sorted(path.name for path in tmp_path.glob("*.p3d")) == [
        "source.p3d",
        "target.p3d",
    ]


@pytest.mark.parametrize(
    ("kind", "expected_exit"),
    [("pass", 0), ("fail", 1), ("invalid", 2)],
)
def test_cli_exit_json_and_stdout_are_deterministic(
    tmp_path, capsys, kind, expected_exit
):
    dimensions = (2.0, 4.0, 6.0)
    if kind == "fail":
        dimensions = (2.0, 4.2, 6.0)
    _source, target, contract = _case(tmp_path, dimensions)
    if kind == "invalid":
        contract.write_text("{", encoding="utf-8")
    exit_code = main([
        "check", str(target), "--contract", str(contract)
    ])
    captured = capsys.readouterr()
    assert exit_code == expected_exit
    assert captured.err == ""
    assert captured.out.endswith("\n")
    result = json.loads(captured.out)
    assert result["verdict"] == kind.upper()
    assert captured.out == json.dumps(
        result, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ) + "\n"
    assert str(tmp_path) not in captured.out


def test_cli_json_output_is_complete_and_stdout_empty(tmp_path, capsys):
    _source, target, contract = _case(tmp_path)
    output = tmp_path / "result.json"
    before_inputs = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (target, contract)
    }
    exit_code = main([
        "check",
        str(target),
        "--contract",
        str(contract),
        "--json",
        str(output),
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == captured.err == ""
    assert output.read_bytes().endswith(b"\n")
    assert json.loads(output.read_text(encoding="utf-8"))["verdict"] == "PASS"
    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (target, contract)
    } == before_inputs


def test_invalid_json_destination_does_not_change_inputs(
    tmp_path, capsys
):
    _source, target, contract = _case(tmp_path)
    before = _snapshot(tmp_path)
    output = tmp_path / "missing" / "result.json"
    exit_code = main([
        "check",
        str(target),
        "--contract",
        str(contract),
        "--json",
        str(output),
    ])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err == ""
    assert json.loads(captured.out)["findings"][0]["code"] == (
        "PREFLIGHT_OUTPUT_UNWRITABLE"
    )
    assert _snapshot(tmp_path) == before
    assert not output.exists()


def test_help_is_lazy_and_does_not_require_py3d(monkeypatch, capsys):
    def fail_if_called(module=None):
        raise AssertionError("dependency gate should not run for --help")

    monkeypatch.setattr(runner, "require_dayz_py3d", fail_if_called)
    with pytest.raises(SystemExit) as raised:
        main(["--help"])
    assert raised.value.code == 0
    assert "check" in capsys.readouterr().out
