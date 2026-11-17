import hashlib
import io
import math
from numbers import Real
from pathlib import Path

from .contract import load_contract, require_dayz_py3d
from .errors import PreflightError
from .findings import finding, sort_findings
from .winding import check_winding


def check_scale_and_bones(model, contract):
    findings = []
    scale = contract["scale"]
    scale_lod_index = scale["lod_index"]
    scale_lod = _lod_or_none(model, scale_lod_index)
    if scale_lod is None:
        findings.append(finding(
            "PREFLIGHT_LOD_MISSING",
            "ERROR",
            "target scale LOD %d does not exist" % scale_lod_index,
            lod_index=scale_lod_index,
        ))
    else:
        try:
            minimum, maximum, _center = scale_lod.bbox()
            raw_dimensions = [
                maximum[index] - minimum[index] for index in range(3)
            ]
        except ValueError:
            raw_dimensions = [0.0, 0.0, 0.0]
        expected = scale["expected_dimensions_m"]
        tolerance = scale["tolerance_m"]
        if any(
            abs(actual - wanted) > allowed
            for actual, wanted, allowed in zip(
                raw_dimensions, expected, tolerance
            )
        ):
            observed = [round(value, 6) for value in raw_dimensions]
            findings.append(finding(
                "PREFLIGHT_SCALE_MISMATCH",
                "ERROR",
                (
                    "LOD %d dimensions expected "
                    "[%.6f, %.6f, %.6f] m, observed "
                    "[%.6f, %.6f, %.6f] m"
                )
                % (
                    scale_lod_index,
                    expected[0],
                    expected[1],
                    expected[2],
                    observed[0],
                    observed[1],
                    observed[2],
                ),
                lod_index=scale_lod_index,
                expected=list(expected),
                observed=observed,
                tolerance=list(tolerance),
            ))

    for requirement in contract["bones"]["requirements"]:
        lod_index = requirement["lod_index"]
        lod = _lod_or_none(model, lod_index)
        if lod is None:
            findings.append(finding(
                "PREFLIGHT_LOD_MISSING",
                "ERROR",
                "target bone-selection LOD %d does not exist" % lod_index,
                lod_index=lod_index,
            ))
            continue
        for name in requirement["selections"]:
            selection = lod.selections.get(name)
            if selection is None:
                findings.append(finding(
                    "PREFLIGHT_BONE_SELECTION_MISSING",
                    "ERROR",
                    "required selection %r is missing from LOD %d"
                    % (name, lod_index),
                    lod_index=lod_index,
                    selection=name,
                ))
            elif not selection.points and not selection.faces:
                findings.append(finding(
                    "PREFLIGHT_BONE_SELECTION_EMPTY",
                    "ERROR",
                    "required selection %r is empty in LOD %d"
                    % (name, lod_index),
                    lod_index=lod_index,
                    selection=name,
                ))
    return sort_findings(findings)


def collect_py3d_findings(model, model_role=None):
    findings = []
    for item in model.validate():
        is_error = item.severity == "ERROR"
        details = {"py3d_code": item.code}
        if model_role is not None:
            details["model_role"] = model_role
        findings.append(finding(
            (
                "PREFLIGHT_PY3D_ERROR"
                if is_error
                else "PREFLIGHT_PY3D_WARNING"
            ),
            item.severity,
            item.msg,
            lod_index=item.lod,
            **details
        ))
    return sort_findings(findings)


def _lod_or_none(model, index):
    if index >= len(model.lods):
        return None
    return model.lods[index]


def _is_finite_number(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, Real)
        and math.isfinite(float(value))
    )


def _is_valid_index(value, count):
    return (
        not isinstance(value, bool)
        and isinstance(value, int)
        and 0 <= value < count
    )


def _finite_vector(value, size):
    return (
        isinstance(value, (list, tuple))
        and len(value) == size
        and all(_is_finite_number(component) for component in value)
    )


def _model_structure_is_safe(model):
    try:
        if not isinstance(model.lods, (list, tuple)):
            return False
        for lod in model.lods:
            if not _is_finite_number(lod.resolution):
                return False
            if not all(
                isinstance(items, (list, tuple))
                for items in (
                    lod.points,
                    lod.facenormals,
                    lod.faces,
                    lod.sharp_edges,
                )
            ):
                return False
            if any(
                not _finite_vector(point.coords, 3)
                for point in lod.points
            ):
                return False
            if any(
                not _finite_vector(normal, 3)
                for normal in lod.facenormals
            ):
                return False
            point_count = len(lod.points)
            normal_count = len(lod.facenormals)
            for face in lod.faces:
                if not isinstance(face.vertices, (list, tuple)):
                    return False
                for vertex in face.vertices:
                    if not _is_valid_index(
                        vertex.point_index, point_count
                    ):
                        return False
                    if not _is_valid_index(
                        vertex.normal_index, normal_count
                    ):
                        return False
                    if not _finite_vector(vertex.uv, 2):
                        return False
            for edge in lod.sharp_edges:
                if not isinstance(edge, (list, tuple)) or len(edge) != 2:
                    return False
                if not all(
                    _is_valid_index(point_index, point_count)
                    for point_index in edge
                ):
                    return False
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False
    return True


def run_preflight(model_path, contract_path):
    model_path = Path(model_path)
    contract_path = Path(contract_path)
    model_bytes = _read_bytes(model_path)
    contract_bytes = _read_bytes(contract_path)
    model_hash = _sha256(model_bytes)
    contract_hash = _sha256(contract_bytes)

    try:
        py3d = require_dayz_py3d()
    except PreflightError as error:
        return _invalid_result(error, model_hash, contract_hash)

    try:
        contract = load_contract(contract_path)
    except PreflightError as error:
        return _invalid_result(error, model_hash, contract_hash)

    if model_bytes is None:
        return _invalid_result(
            PreflightError(
                "PREFLIGHT_MODEL_UNREADABLE",
                "target model cannot be read",
            ),
            model_hash,
            contract_hash,
        )
    source_bytes = _read_bytes(contract["source_model_path"])
    if source_bytes is None:
        return _invalid_result(
            PreflightError(
                "PREFLIGHT_MODEL_UNREADABLE",
                "source model cannot be read",
            ),
            model_hash,
            contract_hash,
        )
    try:
        target_model = py3d.P3D(io.BytesIO(model_bytes))
    except Exception:
        return _invalid_result(
            PreflightError(
                "PREFLIGHT_MODEL_UNREADABLE",
                "target model is not a readable MLOD",
            ),
            model_hash,
            contract_hash,
        )
    try:
        source_model = py3d.P3D(io.BytesIO(source_bytes))
    except Exception:
        return _invalid_result(
            PreflightError(
                "PREFLIGHT_MODEL_UNREADABLE",
                "source model is not a readable MLOD",
            ),
            model_hash,
            contract_hash,
        )

    for role, model in (
        ("target", target_model),
        ("source", source_model),
    ):
        if not _model_structure_is_safe(model):
            return _invalid_result(
                PreflightError(
                    "PREFLIGHT_MODEL_UNREADABLE",
                    "%s model cannot be validated safely" % role,
                ),
                model_hash,
                contract_hash,
            )

    try:
        findings = []
        findings.extend(collect_py3d_findings(target_model, "target"))
        findings.extend(collect_py3d_findings(source_model, "source"))
        findings.extend(check_scale_and_bones(target_model, contract))
    except Exception:
        return _invalid_result(
            PreflightError(
                "PREFLIGHT_MODEL_UNREADABLE",
                "model validation failed safely",
            ),
            model_hash,
            contract_hash,
        )
    invalid = False
    try:
        findings.extend(
            check_winding(source_model, target_model, contract["winding"])
        )
    except PreflightError as error:
        invalid = True
        findings.append(finding(
            error.code, "ERROR", error.message, lod_index=None
        ))
    findings = sort_findings(findings)
    if invalid:
        verdict = "INVALID"
    elif any(item["severity"] == "ERROR" for item in findings):
        verdict = "FAIL"
    else:
        verdict = "PASS"
    return {
        "contract_sha256": contract_hash,
        "findings": findings,
        "model_sha256": model_hash,
        "schema_version": "dayz-model-preflight-result-v1",
        "verdict": verdict,
    }


def _read_bytes(path):
    try:
        return path.read_bytes()
    except OSError:
        return None


def _sha256(data):
    return None if data is None else hashlib.sha256(data).hexdigest()


def _invalid_result(error, model_hash, contract_hash):
    return {
        "contract_sha256": contract_hash,
        "findings": [
            finding(
                error.code,
                "ERROR",
                error.message,
                lod_index=None,
            )
        ],
        "model_sha256": model_hash,
        "schema_version": "dayz-model-preflight-result-v1",
        "verdict": "INVALID",
    }
