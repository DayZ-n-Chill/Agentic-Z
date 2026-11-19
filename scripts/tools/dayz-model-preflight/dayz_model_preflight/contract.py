import importlib
import json
import math
import os
from pathlib import Path
import re

from .errors import PreflightError


CONTRACT_VERSION = "dayz-model-preflight-v1"
MINIMUM_PY3D_VERSION = (1, 6, 0)


def load_contract(path):
    contract_path = Path(path).resolve()
    try:
        raw = contract_path.read_bytes()
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PreflightError(
            "PREFLIGHT_CONTRACT_INVALID",
            "contract is not readable strict UTF-8 JSON: %s"
            % type(error).__name__,
        )

    _require_fields(
        value,
        {"schema_version", "scale", "bones", "winding"},
        "contract",
    )
    if value["schema_version"] != CONTRACT_VERSION:
        _invalid("schema_version must be %s" % CONTRACT_VERSION)

    scale_value = value["scale"]
    _require_fields(
        scale_value,
        {"lod_index", "expected_dimensions_m", "tolerance_m"},
        "scale",
    )
    expected_dimensions = _vector(
        scale_value["expected_dimensions_m"],
        "scale.expected_dimensions_m",
        positive=True,
    )
    tolerance_value = scale_value["tolerance_m"]
    if isinstance(tolerance_value, (list, tuple)):
        tolerances = _vector(
            tolerance_value, "scale.tolerance_m", positive=True
        )
    else:
        tolerance = _number(
            tolerance_value, "scale.tolerance_m", positive=True
        )
        tolerances = [tolerance, tolerance, tolerance]
    scale = {
        "expected_dimensions_m": expected_dimensions,
        "lod_index": _index(scale_value["lod_index"], "scale.lod_index"),
        "tolerance_m": tolerances,
    }

    bones_value = value["bones"]
    _require_fields(bones_value, {"requirements"}, "bones")
    requirements_value = _nonempty_list(
        bones_value["requirements"], "bones.requirements"
    )
    requirements = []
    for requirement_index, requirement in enumerate(requirements_value):
        label = "bones.requirements[%d]" % requirement_index
        _require_fields(requirement, {"lod_index", "selections"}, label)
        selections_value = _nonempty_list(
            requirement["selections"], label + ".selections"
        )
        selections = []
        for selection in selections_value:
            if not isinstance(selection, str) or not selection:
                _invalid("%s selections must be non-empty strings" % label)
            if selection in selections:
                _invalid("%s selections must be unique" % label)
            selections.append(selection)
        requirements.append({
            "lod_index": _index(
                requirement["lod_index"], label + ".lod_index"
            ),
            "selections": selections,
        })

    winding_value = value["winding"]
    _require_fields(
        winding_value,
        {
            "source_model",
            "transform",
            "position_tolerance_m",
            "faces",
        },
        "winding",
    )
    source_model = winding_value["source_model"]
    if not isinstance(source_model, str) or not source_model:
        _invalid("winding.source_model must be a non-empty relative path")
    source_relative = Path(source_model)
    if source_relative.is_absolute() or source_relative.drive:
        _invalid("winding.source_model must be relative")
    source_path = (contract_path.parent / source_relative).resolve()
    try:
        contained = (
            os.path.commonpath((contract_path.parent, source_path))
            == os.fspath(contract_path.parent)
        )
    except ValueError:
        contained = False
    if not contained:
        _invalid("winding.source_model escapes the contract directory")

    transform = _matrix(winding_value["transform"])
    faces_value = _nonempty_list(
        winding_value["faces"], "winding.faces"
    )
    faces = []
    seen_pairs = set()
    seen_source = set()
    seen_target = set()
    for face_map_index, mapping in enumerate(faces_value):
        label = "winding.faces[%d]" % face_map_index
        _require_fields(mapping, {"source", "target"}, label)
        normalized = {}
        for role in ("source", "target"):
            address = mapping[role]
            _require_fields(
                address, {"lod_index", "face_index"}, label + "." + role
            )
            normalized[role] = {
                "face_index": _index(
                    address["face_index"], label + "." + role + ".face_index"
                ),
                "lod_index": _index(
                    address["lod_index"], label + "." + role + ".lod_index"
                ),
            }
        source_address = (
            normalized["source"]["lod_index"],
            normalized["source"]["face_index"],
        )
        target_address = (
            normalized["target"]["lod_index"],
            normalized["target"]["face_index"],
        )
        pair = (source_address, target_address)
        if pair in seen_pairs:
            raise PreflightError(
                "PREFLIGHT_WINDING_EVIDENCE_MISSING",
                "winding contains a duplicate face mapping",
            )
        if source_address in seen_source or target_address in seen_target:
            raise PreflightError(
                "PREFLIGHT_WINDING_UNSUPPORTED_SPLIT",
                "schema v1 does not support one-to-many face lineage",
            )
        seen_pairs.add(pair)
        seen_source.add(source_address)
        seen_target.add(target_address)
        faces.append(normalized)

    return {
        "bones": {"requirements": requirements},
        "scale": scale,
        "schema_version": CONTRACT_VERSION,
        "source_model_path": source_path,
        "winding": {
            "faces": faces,
            "position_tolerance_m": _number(
                winding_value["position_tolerance_m"],
                "winding.position_tolerance_m",
                positive=True,
            ),
            "source_model": source_model,
            "transform": transform,
        },
    }


def require_dayz_py3d(module=None):
    if module is None:
        try:
            module = importlib.import_module("py3d")
        except (ImportError, ModuleNotFoundError):
            raise PreflightError(
                "PREFLIGHT_PY3D_UNAVAILABLE",
                "the DayZ py3d fork >=1.6.0 is required",
            )
    version_text = getattr(module, "__version__", "")
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version_text)
    version = tuple(map(int, match.groups())) if match else ()
    if getattr(module, "IS_DAYZ_FORK", False) is not True or \
            version < MINIMUM_PY3D_VERSION:
        raise PreflightError(
            "PREFLIGHT_PY3D_UNAVAILABLE",
            "the DayZ py3d fork >=1.6.0 is required",
        )
    return module


def _invalid(message):
    raise PreflightError("PREFLIGHT_CONTRACT_INVALID", message)


def _require_fields(value, fields, label):
    if not isinstance(value, dict) or set(value) != fields:
        _invalid("%s fields must be exactly %s" % (label, sorted(fields)))


def _nonempty_list(value, label):
    if not isinstance(value, list) or not value:
        _invalid("%s must be a non-empty list" % label)
    return value


def _index(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _invalid("%s must be a non-negative integer" % label)
    return value


def _number(value, label, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid("%s must be a finite number" % label)
    try:
        result = float(value)
    except OverflowError:
        _invalid("%s must be a finite number" % label)
    if not math.isfinite(result) or (positive and result <= 0.0):
        _invalid(
            "%s must be a %sfinite number"
            % (label, "positive " if positive else "")
        )
    return result


def _vector(value, label, positive=False):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        _invalid("%s must contain exactly three numbers" % label)
    return [
        _number(component, label, positive=positive) for component in value
    ]


def _matrix(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise PreflightError(
            "PREFLIGHT_WINDING_TRANSFORM_INVALID",
            "winding.transform must contain four rows",
        )
    matrix = []
    for row in value:
        if not isinstance(row, (list, tuple)) or len(row) != 4:
            raise PreflightError(
                "PREFLIGHT_WINDING_TRANSFORM_INVALID",
                "winding.transform rows must contain four values",
            )
        normalized_row = []
        for component in row:
            if isinstance(component, bool) or \
                    not isinstance(component, (int, float)):
                raise PreflightError(
                    "PREFLIGHT_WINDING_TRANSFORM_INVALID",
                    "winding.transform must contain finite numbers",
                )
            try:
                normalized_component = float(component)
            except OverflowError:
                raise PreflightError(
                    "PREFLIGHT_WINDING_TRANSFORM_INVALID",
                    "winding.transform must contain finite numbers",
                )
            if not math.isfinite(normalized_component):
                raise PreflightError(
                    "PREFLIGHT_WINDING_TRANSFORM_INVALID",
                    "winding.transform must contain finite numbers",
                )
            normalized_row.append(normalized_component)
        matrix.append(normalized_row)
    if any(
        abs(actual - expected) > 1e-12
        for actual, expected in zip(matrix[3], (0.0, 0.0, 0.0, 1.0))
    ):
        raise PreflightError(
            "PREFLIGHT_WINDING_TRANSFORM_INVALID",
            "winding.transform must have affine last row [0,0,0,1]",
        )
    return matrix
