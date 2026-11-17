import copy
import importlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from dayz_model_preflight.contract import load_contract, require_dayz_py3d
from dayz_model_preflight.errors import PreflightError


TOOL_ROOT = Path(__file__).parents[1]
SCHEMA_PATH = (
    TOOL_ROOT / "schemas" / "dayz-model-preflight-v1.schema.json"
)


def valid_contract():
    return {
        "schema_version": "dayz-model-preflight-v1",
        "scale": {
            "lod_index": 0,
            "expected_dimensions_m": [2.0, 4.0, 6.0],
            "tolerance_m": 0.01,
        },
        "bones": {
            "requirements": [
                {"lod_index": 0, "selections": ["Pelvis", "Spine"]}
            ]
        },
        "winding": {
            "source_model": "source.p3d",
            "transform": [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            "position_tolerance_m": 1e-5,
            "faces": [
                {
                    "source": {"lod_index": 0, "face_index": 0},
                    "target": {"lod_index": 0, "face_index": 0},
                }
            ],
        },
    }


def write_contract(tmp_path, value):
    path = tmp_path / "contract.json"
    path.write_text(
        json.dumps(value, allow_nan=True), encoding="utf-8", newline=""
    )
    return path


def test_tracked_schema_accepts_complete_v1_contract():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(valid_contract())


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.pop("scale"),
        lambda value: value.__setitem__("extra", True),
        lambda value: value["scale"].pop("lod_index"),
        lambda value: value["scale"].__setitem__(
            "expected_dimensions_m", [1.0, 2.0]
        ),
        lambda value: value["scale"].__setitem__("tolerance_m", 0.0),
        lambda value: value["scale"].__setitem__(
            "tolerance_m", [0.1, 0.1]
        ),
        lambda value: value["bones"].__setitem__("requirements", []),
        lambda value: value["bones"]["requirements"][0].__setitem__(
            "selections", []
        ),
        lambda value: value["bones"]["requirements"][0].__setitem__(
            "selections", ["Pelvis", "Pelvis"]
        ),
        lambda value: value["winding"].__setitem__("faces", []),
        lambda value: value["winding"]["faces"][0]["source"].__setitem__(
            "face_index", -1
        ),
    ],
)
def test_schema_rejects_missing_unknown_or_structurally_invalid_fields(
    mutation
):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    value = valid_contract()
    mutation(value)
    assert list(Draft202012Validator(schema).iter_errors(value))


def test_load_contract_normalizes_scalar_tolerance_and_resolves_source(
    tmp_path
):
    (tmp_path / "source.p3d").write_bytes(b"placeholder")
    loaded = load_contract(write_contract(tmp_path, valid_contract()))
    assert loaded["scale"]["tolerance_m"] == [0.01, 0.01, 0.01]
    assert loaded["source_model_path"] == (tmp_path / "source.p3d").resolve()


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda value: value["scale"]["expected_dimensions_m"].__setitem__(
                0, math.nan
            ),
            "PREFLIGHT_CONTRACT_INVALID",
        ),
        (
            lambda value: value["scale"]["expected_dimensions_m"].__setitem__(
                0, 10 ** 1000
            ),
            "PREFLIGHT_CONTRACT_INVALID",
        ),
        (
            lambda value: value["winding"]["transform"][0].__setitem__(
                0, math.inf
            ),
            "PREFLIGHT_WINDING_TRANSFORM_INVALID",
        ),
        (
            lambda value: value["winding"]["transform"][0].__setitem__(
                0, 10 ** 1000
            ),
            "PREFLIGHT_WINDING_TRANSFORM_INVALID",
        ),
        (
            lambda value: value["winding"]["transform"].__setitem__(
                3, [0.0, 0.0, 1.0, 1.0]
            ),
            "PREFLIGHT_WINDING_TRANSFORM_INVALID",
        ),
        (
            lambda value: value["winding"].__setitem__(
                "source_model", "../escape.p3d"
            ),
            "PREFLIGHT_CONTRACT_INVALID",
        ),
        (
            lambda value: value["winding"].__setitem__(
                "source_model", "C:/absolute/source.p3d"
            ),
            "PREFLIGHT_CONTRACT_INVALID",
        ),
        (
            lambda value: value["winding"]["faces"].append(
                copy.deepcopy(value["winding"]["faces"][0])
            ),
            "PREFLIGHT_WINDING_EVIDENCE_MISSING",
        ),
        (
            lambda value: value["winding"]["faces"].append(
                {
                    "source": {"lod_index": 0, "face_index": 1},
                    "target": {"lod_index": 0, "face_index": 0},
                }
            ),
            "PREFLIGHT_WINDING_UNSUPPORTED_SPLIT",
        ),
    ],
)
def test_load_contract_fails_closed_on_semantic_ambiguity(
    tmp_path, mutation, code
):
    value = valid_contract()
    mutation(value)
    with pytest.raises(PreflightError) as raised:
        load_contract(write_contract(tmp_path, value))
    assert raised.value.code == code


def test_cross_reused_face_addresses_are_split_not_exact_duplicate(tmp_path):
    """Rompe si A->Y se etiqueta duplicado tras A->X y B->Y."""
    value = valid_contract()
    value["winding"]["faces"].extend([
        {
            "source": {"lod_index": 0, "face_index": 1},
            "target": {"lod_index": 0, "face_index": 1},
        },
        {
            "source": {"lod_index": 0, "face_index": 0},
            "target": {"lod_index": 0, "face_index": 1},
        },
    ])
    with pytest.raises(PreflightError) as raised:
        load_contract(write_contract(tmp_path, value))
    assert raised.value.code == "PREFLIGHT_WINDING_UNSUPPORTED_SPLIT"


@pytest.mark.parametrize(
    "raw",
    [b"", b"{", b"[]", b'{"schema_version":"wrong"}'],
)
def test_load_contract_rejects_invalid_json_or_root(tmp_path, raw):
    path = tmp_path / "contract.json"
    path.write_bytes(raw)
    with pytest.raises(PreflightError) as raised:
        load_contract(path)
    assert raised.value.code == "PREFLIGHT_CONTRACT_INVALID"


def test_dependency_gate_rejects_missing_py3d(monkeypatch):
    def missing(_name):
        raise ModuleNotFoundError("py3d")

    monkeypatch.setattr(importlib, "import_module", missing)
    with pytest.raises(PreflightError) as raised:
        require_dayz_py3d()
    assert raised.value.code == "PREFLIGHT_PY3D_UNAVAILABLE"


@pytest.mark.parametrize(
    "module",
    [
        SimpleNamespace(IS_DAYZ_FORK=False, __version__="1.4.0"),
        SimpleNamespace(IS_DAYZ_FORK=True, __version__="1.3.0"),
        SimpleNamespace(IS_DAYZ_FORK=True, __version__="1.5.0"),
        SimpleNamespace(IS_DAYZ_FORK=True, __version__="not-a-version"),
    ],
)
def test_dependency_gate_rejects_upstream_old_or_unversioned_py3d(module):
    with pytest.raises(PreflightError) as raised:
        require_dayz_py3d(module)
    assert raised.value.code == "PREFLIGHT_PY3D_UNAVAILABLE"


def test_dependency_gate_accepts_dayz_fork_1_6_0():
    module = SimpleNamespace(IS_DAYZ_FORK=True, __version__="1.6.0")
    assert require_dayz_py3d(module) is module
