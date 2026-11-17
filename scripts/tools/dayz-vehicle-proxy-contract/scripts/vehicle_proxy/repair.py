from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

import numpy as np
import py3d

from .p3d_graph import ProxyNode, geometry_digest, structural_digest


_SUPPORTED_OPERATIONS = frozenset(
    {"set-autocenter-zero", "yaw180", "affine-fit"}
)
_COMPONENT_EPSILON = 1.0e-6
_SIMILARITY_RTOL = 1.0e-7
_SIMILARITY_ATOL = 1.0e-9

ImmutableMatrix = tuple[tuple[float, ...], ...]


class RepairRefused(ValueError):
    """A requested repair cannot satisfy the staging safety contract."""


def _require_supported(operation: str) -> None:
    if operation not in _SUPPORTED_OPERATIONS:
        raise RepairRefused(f"unsupported operation {operation!r}")


def _matrix4(value: object) -> np.ndarray:
    try:
        matrix = np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise RepairRefused("fit matrix must be a finite affine 4x4 matrix") from error
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise RepairRefused("fit matrix must be a finite affine 4x4 matrix")
    if not np.allclose(
        matrix[3],
        (0.0, 0.0, 0.0, 1.0),
        rtol=0.0,
        atol=_SIMILARITY_ATOL,
    ):
        raise RepairRefused("fit matrix must have affine last row [0, 0, 0, 1]")
    return matrix.copy()


def _freeze_matrix(value: object) -> ImmutableMatrix:
    matrix = _matrix4(value)
    return tuple(tuple(float(item) for item in row) for row in matrix)


@dataclass(frozen=True)
class RepairOperation:
    node: ProxyNode
    operation: str
    fit_matrix: ImmutableMatrix | None = None

    def __post_init__(self) -> None:
        _require_supported(self.operation)
        if self.fit_matrix is not None:
            if self.operation != "affine-fit":
                raise RepairRefused(
                    f"{self.operation} does not accept a fit matrix"
                )
            object.__setattr__(self, "fit_matrix", _freeze_matrix(self.fit_matrix))


def _similarity_components(
    value: object,
) -> tuple[np.ndarray, np.ndarray, frozenset[str]]:
    matrix = _matrix4(value)
    linear = matrix[:3, :3]
    determinant = float(np.linalg.det(linear))
    if not math.isfinite(determinant) or abs(determinant) <= _SIMILARITY_ATOL:
        raise RepairRefused("affine-fit linear transform must be invertible")
    if determinant < 0.0:
        raise RepairRefused("affine-fit reflection is not stageable")

    singular = np.linalg.svd(linear, compute_uv=False)
    scale = float(singular.mean())
    if not math.isfinite(scale) or scale <= _SIMILARITY_ATOL:
        raise RepairRefused("affine-fit must have positive uniform scale")
    if not np.allclose(
        singular,
        scale,
        rtol=_SIMILARITY_RTOL,
        atol=_SIMILARITY_ATOL,
    ):
        raise RepairRefused(
            "affine-fit must be a proper similarity; shear and non-uniform scale are refused"
        )

    rotation = linear / scale
    if not np.allclose(
        rotation.T @ rotation,
        np.eye(3),
        rtol=_SIMILARITY_RTOL,
        atol=_SIMILARITY_ATOL,
    ) or not math.isclose(
        float(np.linalg.det(rotation)),
        1.0,
        rel_tol=_SIMILARITY_RTOL,
        abs_tol=_SIMILARITY_ATOL,
    ):
        raise RepairRefused("affine-fit linear transform is not a proper rotation")

    cosine = max(-1.0, min(1.0, (float(np.trace(rotation)) - 1.0) / 2.0))
    components = set()
    if float(np.linalg.norm(matrix[:3, 3])) > _COMPONENT_EPSILON:
        components.add("translation")
    if math.degrees(math.acos(cosine)) > _COMPONENT_EPSILON:
        components.add("rotation")
    if abs(scale - 1.0) > _COMPONENT_EPSILON:
        components.add("uniform-scale")
    return matrix, rotation, frozenset(components)


def _authorized_matrix(node: ProxyNode, fit_matrix: object) -> np.ndarray:
    matrix, _, components = _similarity_components(fit_matrix)
    denied = components - frozenset(node.allowed_fit_components)
    if denied:
        raise RepairRefused(
            f"affine-fit components not authorized: {sorted(denied)}"
        )
    return matrix


def _validate_request(
    node: ProxyNode, operation: str, fit_matrix: object | None
) -> np.ndarray | None:
    _require_supported(operation)
    if operation not in node.repairs:
        raise RepairRefused(f"{operation} not authorized for {node.proxy_path}")
    if operation == "affine-fit":
        if fit_matrix is None:
            raise RepairRefused("affine-fit requires a measured matrix")
        return _authorized_matrix(node, fit_matrix)
    if fit_matrix is not None:
        raise RepairRefused(f"{operation} does not accept a fit matrix")
    return None


def plan_repairs(
    nodes: Sequence[ProxyNode],
    operation: str,
    fit_matrices: Mapping[tuple[str, float], object] | None = None,
) -> tuple[RepairOperation, ...]:
    """Plan every node that globally authorizes *operation*."""
    _require_supported(operation)
    selected = [node for node in nodes if operation in node.repairs]
    if not selected:
        raise RepairRefused(f"no nodes authorize {operation}")

    planned = []
    for node in selected:
        matrix = None
        if operation == "affine-fit":
            key = (node.piece, node.host_lod)
            if fit_matrices is None or key not in fit_matrices:
                raise RepairRefused(
                    f"missing affine-fit matrix for {node.piece}@{node.host_lod}"
                )
            matrix_array = _authorized_matrix(node, fit_matrices[key])
            matrix = _freeze_matrix(matrix_array)
        planned.append(RepairOperation(node, operation, matrix))

    planned.sort(
        key=lambda item: (
            item.node.host_lod,
            item.node.piece,
            str(item.node.proxy_path),
        )
    )
    return tuple(planned)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _path_key(path: Path) -> str:
    return os.path.normcase(os.fspath(path.resolve(strict=False)))


def _same_file_or_path(left: Path, right: Path) -> bool:
    if _path_key(left) == _path_key(right):
        return True
    if left.exists() and right.exists():
        try:
            return os.path.samefile(left, right)
        except OSError:
            return False
    return False


def _stage_paths(
    node: ProxyNode, staging_root: Path
) -> tuple[Path, Path, Path, Path]:
    relative = Path(node.addon_relative_path)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise RepairRefused(
            f"invalid addon-relative proxy path: {node.addon_relative_path}"
        )

    try:
        source = Path(node.proxy_path).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise RepairRefused(f"missing proxy source: {node.proxy_path}") from error
    if not source.is_file():
        raise RepairRefused(f"proxy source is not a file: {node.proxy_path}")

    addon_root = source
    for _ in relative.parts:
        addon_root = addon_root.parent
    expected_source = (addon_root / relative).resolve(strict=False)
    if not _same_file_or_path(source, expected_source):
        raise RepairRefused(
            "proxy_path is inconsistent with addon_relative_path: "
            f"{node.proxy_path} vs {node.addon_relative_path}"
        )

    staging = Path(staging_root).resolve(strict=False)
    if _is_within(staging, addon_root):
        raise RepairRefused(
            f"staging root must be outside addon root {addon_root}: {staging}"
        )
    destination = (staging / relative).resolve(strict=False)
    if not _is_within(destination, staging):
        raise RepairRefused(f"staging destination escapes root: {destination}")
    if _same_file_or_path(destination, source):
        raise RepairRefused(f"staging destination aliases source: {source}")
    if os.path.lexists(destination):
        raise RepairRefused(f"staging destination already exists: {destination}")
    return source, addon_root, staging, destination


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_mlod(path: Path) -> py3d.P3D:
    try:
        with path.open("rb") as handle:
            return py3d.P3D(handle)
    except (OSError, AssertionError, EOFError, ValueError) as error:
        raise RepairRefused(f"cannot read MLOD P3D: {path}") from error


def _normal_coordinates(normal: Any) -> tuple[float, float, float]:
    coordinates = normal.coords if hasattr(normal, "coords") else normal
    try:
        result = tuple(float(value) for value in coordinates)
    except (TypeError, ValueError, OverflowError) as error:
        raise RepairRefused("face normal must contain three finite coordinates") from error
    if len(result) != 3 or not np.isfinite(result).all():
        raise RepairRefused("face normal must contain three finite coordinates")
    return result


def _set_normal(lod, index: int, value: tuple[float, float, float]) -> None:
    normal = lod.facenormals[index]
    if hasattr(normal, "coords"):
        normal.coords = value
    else:
        lod.facenormals[index] = value


def _yaw180_lod(lod) -> None:
    for point in lod.points:
        x, y, z = point.coords
        point.coords = (-x, y, -z)
    for index, normal in enumerate(lod.facenormals):
        x, y, z = _normal_coordinates(normal)
        _set_normal(lod, index, (-x, y, -z))


def _apply_affine_lod(lod, matrix: np.ndarray, rotation: np.ndarray) -> None:
    linear = matrix[:3, :3]
    translation = matrix[:3, 3]
    for point in lod.points:
        transformed = linear @ np.asarray(point.coords, dtype=float) + translation
        point.coords = tuple(float(value) for value in transformed)
    for index, normal in enumerate(lod.facenormals):
        transformed = rotation @ np.asarray(_normal_coordinates(normal), dtype=float)
        length = float(np.linalg.norm(transformed))
        if length > 1.0e-12:
            transformed = transformed / length
        value = tuple(float(item) for item in transformed)
        _set_normal(lod, index, value)


def _points(model: py3d.P3D) -> tuple[tuple[tuple[float, ...], ...], ...]:
    return tuple(
        tuple(tuple(float(value) for value in point.coords) for point in lod.points)
        for lod in model.lods
    )


def _normals(model: py3d.P3D) -> tuple[tuple[tuple[float, ...], ...], ...]:
    return tuple(
        tuple(_normal_coordinates(normal) for normal in lod.facenormals)
        for lod in model.lods
    )


def _masses(model: py3d.P3D) -> tuple[tuple[float | None, ...], ...]:
    return tuple(tuple(point.mass for point in lod.points) for lod in model.lods)


def _properties(model: py3d.P3D) -> tuple[dict[str, str], ...]:
    return tuple(dict(lod.properties) for lod in model.lods)


def _all_coordinates_close(
    actual: tuple[tuple[tuple[float, ...], ...], ...],
    expected: tuple[tuple[tuple[float, ...], ...], ...],
) -> bool:
    if tuple(map(len, actual)) != tuple(map(len, expected)):
        return False
    for actual_lod, expected_lod in zip(actual, expected):
        for actual_value, expected_value in zip(actual_lod, expected_lod):
            if not np.allclose(
                actual_value,
                expected_value,
                rtol=1.0e-6,
                atol=1.0e-6,
            ):
                return False
    return True


def _expected_geometry(
    points: tuple[tuple[tuple[float, ...], ...], ...],
    normals: tuple[tuple[tuple[float, ...], ...], ...],
    operation: str,
    matrix: np.ndarray | None,
) -> tuple[
    tuple[tuple[tuple[float, ...], ...], ...],
    tuple[tuple[tuple[float, ...], ...], ...],
]:
    if operation == "set-autocenter-zero":
        return points, normals
    if operation == "yaw180":
        return (
            tuple(
                tuple((-value[0], value[1], -value[2]) for value in lod)
                for lod in points
            ),
            tuple(
                tuple((-value[0], value[1], -value[2]) for value in lod)
                for lod in normals
            ),
        )
    assert matrix is not None
    _, rotation, _ = _similarity_components(matrix)
    expected_points = tuple(
        tuple(
            tuple(
                float(value)
                for value in (
                    matrix[:3, :3] @ np.asarray(coords, dtype=float)
                    + matrix[:3, 3]
                )
            )
            for coords in lod
        )
        for lod in points
    )
    expected_normals = []
    for lod in normals:
        transformed_lod = []
        for coords in lod:
            transformed = rotation @ np.asarray(coords, dtype=float)
            length = float(np.linalg.norm(transformed))
            if length > 1.0e-12:
                transformed = transformed / length
            transformed_lod.append(tuple(float(value) for value in transformed))
        expected_normals.append(tuple(transformed_lod))
    return expected_points, tuple(expected_normals)


def _verify_readback(
    before: py3d.P3D,
    after: py3d.P3D,
    operation: str,
    matrix: np.ndarray | None,
) -> None:
    structural_before = tuple(structural_digest(lod) for lod in before.lods)
    structural_after = tuple(structural_digest(lod) for lod in after.lods)
    if structural_after != structural_before:
        raise RepairRefused("structural invariant changed")
    if _masses(after) != _masses(before):
        raise RepairRefused("point mass invariant changed")

    properties_before = _properties(before)
    properties_after = _properties(after)
    points_before = _points(before)
    normals_before = _normals(before)
    expected_points, expected_normals = _expected_geometry(
        points_before, normals_before, operation, matrix
    )
    if not _all_coordinates_close(_points(after), expected_points) or not _all_coordinates_close(
        _normals(after), expected_normals
    ):
        raise RepairRefused("staged geometry does not match the requested transform")

    if operation == "set-autocenter-zero":
        if tuple(geometry_digest(lod) for lod in after.lods) != tuple(
            geometry_digest(lod) for lod in before.lods
        ):
            raise RepairRefused("property-only operation changed geometry")
        expected_properties = []
        for properties in properties_before:
            updated = dict(properties)
            updated["autocenter"] = "0"
            expected_properties.append(updated)
        if properties_after != tuple(expected_properties):
            raise RepairRefused("property operation changed more than autocenter")
    elif properties_after != properties_before:
        raise RepairRefused("geometry operation changed properties")


def _verify_source_hash(source: Path, expected: str) -> None:
    try:
        actual = _sha256(source)
    except OSError as error:
        raise RepairRefused(f"source disappeared during staging: {source}") from error
    if actual != expected:
        raise RepairRefused(f"source changed during staging: {source}")


def _stage_private(
    node: ProxyNode,
    operation: str,
    transaction_root: Path,
    expected_source: Path,
    expected_hash: str,
    fit_matrix: object | None = None,
) -> Path:
    matrix = _validate_request(node, operation, fit_matrix)
    source, _, _, destination = _stage_paths(node, transaction_root)
    if not _same_file_or_path(source, expected_source):
        raise RepairRefused(f"source changed identity during staging: {source}")
    _verify_source_hash(source, expected_hash)
    try:
        before = _load_mlod(source)
        points_before = _points(before)
        normals_before = _normals(before)
        expected_points, expected_normals = _expected_geometry(
            points_before, normals_before, operation, matrix
        )

        if operation == "set-autocenter-zero":
            for lod in before.lods:
                lod.properties["autocenter"] = "0"
        elif operation == "yaw180":
            for lod in before.lods:
                _yaw180_lod(lod)
        else:
            assert matrix is not None
            _, rotation, _ = _similarity_components(matrix)
            for lod in before.lods:
                _apply_affine_lod(lod, matrix, rotation)

        if not _all_coordinates_close(_points(before), expected_points) or not _all_coordinates_close(
            _normals(before), expected_normals
        ):
            raise RepairRefused("in-memory geometry does not match the requested transform")

        destination.parent.mkdir(parents=True, exist_ok=True)
        before.save(destination, verify=True)
        reread = _load_mlod(destination)

        original = _load_mlod(source)
        _verify_readback(original, reread, operation, matrix)
        return destination
    finally:
        _verify_source_hash(source, expected_hash)


def stage_one(
    node: ProxyNode,
    operation: str,
    staging_root: Path,
    fit_matrix: object | None = None,
) -> Path:
    """Transactionally stage one verified repair without overwriting output."""
    return stage_repairs(
        (RepairOperation(node, operation, fit_matrix),), staging_root
    )[0]


def stage_repairs(
    operations: Sequence[RepairOperation], staging_root: Path
) -> tuple[Path, ...]:
    """Preflight and stage a complete repair plan in plan order."""
    plan = tuple(operations)
    if not plan:
        raise RepairRefused("repair plan is empty")

    requested_staging = Path(os.path.abspath(os.fspath(staging_root)))
    if os.path.lexists(requested_staging):
        raise RepairRefused(f"staging root already exists: {requested_staging}")

    paths = []
    source_paths = []
    source_hashes = []
    destinations: dict[str, Path] = {}
    staging = None
    for item in plan:
        if not isinstance(item, RepairOperation):
            raise RepairRefused("repair plan contains an invalid operation")
        _validate_request(item.node, item.operation, item.fit_matrix)
        source, _, item_staging, destination = _stage_paths(
            item.node, requested_staging
        )
        if staging is None:
            staging = item_staging
        elif _path_key(item_staging) != _path_key(staging):
            raise RepairRefused("repair plan resolves multiple staging roots")
        key = _path_key(destination)
        if key in destinations or any(
            _same_file_or_path(destination, previous) for previous in destinations.values()
        ):
            raise RepairRefused(f"duplicate staging destination: {destination}")
        destinations[key] = destination
        source_paths.append(source)
        source_hashes.append(_sha256(source))
        paths.append(destination)

    for destination in paths:
        if any(_same_file_or_path(destination, source) for source in source_paths):
            raise RepairRefused(f"staging destination aliases a source: {destination}")

    assert staging is not None
    if os.path.lexists(staging):
        raise RepairRefused(f"staging root already exists: {staging}")
    try:
        staging.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise RepairRefused(
            f"cannot create staging parent {staging.parent}: {error}"
        ) from error
    if not staging.parent.is_dir():
        raise RepairRefused(
            f"staging parent is not a directory: {staging.parent}"
        )
    if os.path.lexists(staging):
        raise RepairRefused(f"staging root already exists: {staging}")

    try:
        transaction = Path(
            tempfile.mkdtemp(
                prefix=f".{staging.name}.vehicle-proxy-repair-",
                dir=staging.parent,
            )
        )
    except OSError as error:
        raise RepairRefused(
            f"cannot create private staging sibling for {staging}: {error}"
        ) from error

    committed = False
    result = tuple(paths)
    try:
        for item, source, source_hash in zip(plan, source_paths, source_hashes):
            _stage_private(
                item.node,
                item.operation,
                transaction,
                source,
                source_hash,
                fit_matrix=item.fit_matrix,
            )
        for source, source_hash in zip(source_paths, source_hashes):
            _verify_source_hash(source, source_hash)

        try:
            if os.path.lexists(staging):
                raise RepairRefused(f"staging root already exists: {staging}")
            os.rename(transaction, staging)
        except RepairRefused:
            raise
        except FileExistsError as error:
            raise RepairRefused(f"staging root already exists: {staging}") from error
        except OSError as error:
            raise RepairRefused(
                f"cannot commit staging tree {staging}: {error}"
            ) from error
        committed = True
    finally:
        if not committed:
            try:
                shutil.rmtree(transaction)
            except OSError as error:
                raise RepairRefused(
                    f"cannot clean private staging transaction {transaction}: {error}"
                ) from error
    return result
