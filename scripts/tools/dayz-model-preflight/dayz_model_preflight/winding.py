import itertools
import math

from .errors import PreflightError
from .findings import finding, sort_findings


def check_winding(source_model, target_model, winding):
    matrix, determinant = _validate_transform(winding.get("transform"))
    tolerance = winding.get("position_tolerance_m")
    if isinstance(tolerance, bool) or \
            not isinstance(tolerance, (int, float)):
        raise PreflightError(
            "PREFLIGHT_CONTRACT_INVALID",
            "winding position tolerance must be positive and finite",
        )
    try:
        tolerance = float(tolerance)
    except OverflowError:
        raise PreflightError(
            "PREFLIGHT_CONTRACT_INVALID",
            "winding position tolerance must be positive and finite",
        )
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise PreflightError(
            "PREFLIGHT_CONTRACT_INVALID",
            "winding position tolerance must be positive and finite",
        )
    mappings = winding.get("faces")
    if not isinstance(mappings, list) or not mappings:
        _evidence_error("winding requires a non-empty face map")

    normalized = []
    seen_pairs = set()
    seen_source = set()
    seen_target = set()
    for mapping in mappings:
        try:
            source = _address(mapping["source"])
            target = _address(mapping["target"])
        except (KeyError, TypeError):
            _evidence_error("winding contains an invalid face address")
        pair = (source, target)
        if pair in seen_pairs:
            _evidence_error("winding contains a duplicate face mapping")
        if source in seen_source or target in seen_target:
            raise PreflightError(
                "PREFLIGHT_WINDING_UNSUPPORTED_SPLIT",
                "schema v1 does not support one-to-many face lineage",
            )
        seen_pairs.add(pair)
        seen_source.add(source)
        seen_target.add(target)
        normalized.append((source, target))

    missing = []
    for role, model, addresses in (
        ("source", source_model, seen_source),
        ("target", target_model, seen_target),
    ):
        for lod_index in sorted({address[0] for address in addresses}):
            if lod_index >= len(model.lods):
                missing.append(finding(
                    "PREFLIGHT_LOD_MISSING",
                    "ERROR",
                    "%s winding LOD %d does not exist" % (role, lod_index),
                    lod_index=lod_index,
                    model_role=role,
                ))
    if missing:
        return sort_findings(missing)

    _validate_addresses_and_coverage(
        source_model, seen_source, "source"
    )
    _validate_addresses_and_coverage(
        target_model, seen_target, "target"
    )

    expected_relation = "PRESERVE" if determinant > 0.0 else "REVERSE"
    findings = []
    for source_address, target_address in normalized:
        source_lod_index, source_face_index = source_address
        target_lod_index, target_face_index = target_address
        source_face = (
            source_model.lods[source_lod_index].faces[source_face_index]
        )
        target_face = (
            target_model.lods[target_lod_index].faces[target_face_index]
        )
        source_arity = len(source_face.vertices)
        target_arity = len(target_face.vertices)
        if source_arity not in (3, 4) or target_arity not in (3, 4) or \
                source_arity != target_arity:
            raise PreflightError(
                "PREFLIGHT_WINDING_UNSUPPORTED_SPLIT",
                "mapped polygons must have matching triangle/quad arity",
            )
        source_positions = [
            _transform_position(vertex.point.coords, matrix)
            for vertex in source_face.vertices
        ]
        target_positions = [
            _position(vertex.point.coords) for vertex in target_face.vertices
        ]
        matches = [
            permutation
            for permutation in itertools.permutations(range(source_arity))
            if all(
                math.dist(source_positions[index],
                          target_positions[permutation[index]]) <= tolerance
                for index in range(source_arity)
            )
        ]
        if len(matches) != 1:
            raise PreflightError(
                "PREFLIGHT_WINDING_GEOMETRY_MISMATCH",
                (
                    "source LOD %d face %d does not have one unambiguous "
                    "target geometry match"
                )
                % (source_lod_index, source_face_index),
            )
        observed_relation = _relation(matches[0])
        if observed_relation != expected_relation:
            findings.append(finding(
                "PREFLIGHT_WINDING_RELATION_MISMATCH",
                "ERROR",
                (
                    "target LOD %d face %d is %s; transform determinant "
                    "%.12g requires %s"
                )
                % (
                    target_lod_index,
                    target_face_index,
                    observed_relation,
                    determinant,
                    expected_relation,
                ),
                lod_index=target_lod_index,
                face_index=target_face_index,
                determinant=determinant,
                expected=expected_relation,
                observed=observed_relation,
                source_face_index=source_face_index,
                source_lod_index=source_lod_index,
            ))
    return sort_findings(findings)


def _address(value):
    if not isinstance(value, dict) or set(value) != {
        "lod_index", "face_index",
    }:
        _evidence_error("face address fields are invalid")
    output = []
    for field in ("lod_index", "face_index"):
        item = value[field]
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            _evidence_error("face address values must be non-negative ints")
        output.append(item)
    return tuple(output)


def _evidence_error(message):
    raise PreflightError("PREFLIGHT_WINDING_EVIDENCE_MISSING", message)


def _validate_addresses_and_coverage(model, addresses, role):
    by_lod = {}
    for lod_index, face_index in addresses:
        lod = model.lods[lod_index]
        if face_index >= len(lod.faces):
            _evidence_error(
                "%s LOD %d face %d is out of range"
                % (role, lod_index, face_index)
            )
        by_lod.setdefault(lod_index, set()).add(face_index)
    for lod_index, covered in by_lod.items():
        expected = set(range(len(model.lods[lod_index].faces)))
        if covered != expected:
            _evidence_error(
                "%s LOD %d face coverage is incomplete"
                % (role, lod_index)
            )


def _validate_transform(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        _transform_error("transform must contain four rows")
    matrix = []
    for row in value:
        if not isinstance(row, (list, tuple)) or len(row) != 4:
            _transform_error("transform rows must contain four values")
        normalized = []
        for component in row:
            if isinstance(component, bool) or \
                    not isinstance(component, (int, float)):
                _transform_error("transform values must be finite numbers")
            try:
                normalized_component = float(component)
            except OverflowError:
                _transform_error("transform values must be finite numbers")
            if not math.isfinite(normalized_component):
                _transform_error("transform values must be finite numbers")
            normalized.append(normalized_component)
        matrix.append(normalized)
    if any(
        abs(actual - expected) > 1e-12
        for actual, expected in zip(matrix[3], (0.0, 0.0, 0.0, 1.0))
    ):
        _transform_error("transform must have affine last row [0,0,0,1]")
    upper = [row[:3] for row in matrix[:3]]
    determinant = (
        upper[0][0] * (
            upper[1][1] * upper[2][2] - upper[1][2] * upper[2][1]
        )
        - upper[0][1] * (
            upper[1][0] * upper[2][2] - upper[1][2] * upper[2][0]
        )
        + upper[0][2] * (
            upper[1][0] * upper[2][1] - upper[1][1] * upper[2][0]
        )
    )
    if not math.isfinite(determinant) or abs(determinant) <= 1e-12:
        _transform_error("transform upper 3x3 is singular")
    return matrix, determinant


def _transform_error(message):
    raise PreflightError("PREFLIGHT_WINDING_TRANSFORM_INVALID", message)


def _position(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise PreflightError(
            "PREFLIGHT_WINDING_GEOMETRY_MISMATCH",
            "model point is not a three-component position",
        )
    try:
        output = tuple(float(component) for component in value)
    except (TypeError, ValueError, OverflowError):
        raise PreflightError(
            "PREFLIGHT_WINDING_GEOMETRY_MISMATCH",
            "model point contains a non-finite position",
        )
    if not all(math.isfinite(component) for component in output):
        raise PreflightError(
            "PREFLIGHT_WINDING_GEOMETRY_MISMATCH",
            "model point contains a non-finite position",
        )
    return output


def _transform_position(value, matrix):
    x, y, z = _position(value)
    return tuple(
        matrix[row][0] * x
        + matrix[row][1] * y
        + matrix[row][2] * z
        + matrix[row][3]
        for row in range(3)
    )


def _relation(permutation):
    count = len(permutation)
    origin = permutation[0]
    if all(
        permutation[index] == (origin + index) % count
        for index in range(count)
    ):
        return "PRESERVE"
    if all(
        permutation[index] == (origin - index) % count
        for index in range(count)
    ):
        return "REVERSE"
    return "MIXED"
