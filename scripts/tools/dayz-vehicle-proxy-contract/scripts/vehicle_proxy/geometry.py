from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Tuple

import numpy as np
from scipy.spatial import cKDTree

from .manifest import Thresholds


_SIMILARITY_RTOL = 1e-9
_SIMILARITY_ATOL = 1e-12


class GeometryError(ValueError):
    """Geometry cannot support a meaningful source-to-assembly fit."""


@dataclass(frozen=True)
class ObjGeometry:
    vertices: np.ndarray
    faces: Tuple[Tuple[str, Tuple[int, ...]], ...]


@dataclass(frozen=True)
class FitMetrics:
    seed: str
    matrix: Tuple[Tuple[float, ...], ...]
    translation: Tuple[float, float, float]
    rotation_deg: float
    determinant: float
    uniform_scale: float
    forward_p95_m: float
    reverse_p95_m: float
    symmetric_p95_m: float


@dataclass(frozen=True)
class FitClassification:
    passes: bool
    repairable: bool
    reasons: Tuple[str, ...]


def _point_cloud(points: object, field: str, *, require_fit: bool) -> np.ndarray:
    try:
        cloud = np.asarray(points, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise GeometryError(f"{field} must be a finite Nx3 point cloud") from error
    if cloud.ndim != 2 or cloud.shape[1:] != (3,):
        raise GeometryError(f"{field} must be a finite Nx3 point cloud")
    if len(cloud) == 0:
        raise GeometryError(f"{field} must not be empty")
    if not np.isfinite(cloud).all():
        raise GeometryError(f"{field} must contain only finite coordinates")
    if require_fit:
        unique = np.unique(cloud, axis=0)
        if len(unique) < 3 or np.linalg.matrix_rank(unique - unique.mean(axis=0)) < 2:
            raise GeometryError(
                f"{field} must contain at least three non-collinear points"
            )
    return cloud


def _matrix4(value: object, field: str, *, require_invertible: bool) -> np.ndarray:
    try:
        matrix = np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise GeometryError(f"{field} must be a finite affine 4x4 matrix") from error
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise GeometryError(f"{field} must be a finite affine 4x4 matrix")
    if not np.allclose(matrix[3], (0.0, 0.0, 0.0, 1.0), atol=1e-12):
        raise GeometryError(f"{field} must have affine last row [0, 0, 0, 1]")
    if require_invertible and abs(float(np.linalg.det(matrix[:3, :3]))) <= 1e-12:
        raise GeometryError(f"{field} must have an invertible linear transform")
    return matrix


def _uniform_similarity_scale(linear: np.ndarray, field: str) -> float:
    singular = np.linalg.svd(linear, compute_uv=False)
    scale = float(singular.mean())
    if not math.isfinite(scale) or scale <= 1e-12:
        raise GeometryError(f"{field} must have positive uniform scale")
    if not np.allclose(
        singular,
        scale,
        rtol=_SIMILARITY_RTOL,
        atol=_SIMILARITY_ATOL,
    ):
        raise GeometryError(f"{field} must be a similarity transform")
    return scale


def parse_obj_text(text: str) -> ObjGeometry:
    if type(text) is not str:
        raise GeometryError("OBJ source must be text")
    vertices = []
    faces = []
    material = ""
    for line_number, raw in enumerate(text.splitlines(), start=1):
        fields = raw.split()
        if not fields or fields[0].startswith("#"):
            continue
        tag = fields[0]
        try:
            if tag == "v":
                if len(fields) < 4:
                    raise GeometryError(
                        f"OBJ vertex at line {line_number} requires three coordinates"
                    )
                vertex = tuple(float(value) for value in fields[1:4])
                if not all(math.isfinite(value) for value in vertex):
                    raise GeometryError(
                        f"OBJ vertex at line {line_number} is not finite"
                    )
                vertices.append(vertex)
            elif tag == "usemtl":
                if len(fields) < 2:
                    raise GeometryError(
                        f"OBJ material at line {line_number} has no name"
                    )
                material = fields[1].upper()
            elif tag == "f":
                tokens = tuple(
                    token for token in fields[1:] if not token.startswith("#")
                )
                if len(tokens) < 3:
                    raise GeometryError(
                        f"OBJ face at line {line_number} requires three vertices"
                    )
                indexes = []
                for token in tokens:
                    raw_index = token.split("/", 1)[0]
                    if not raw_index:
                        raise GeometryError(
                            f"OBJ face at line {line_number} has no vertex index"
                        )
                    value = int(raw_index)
                    if value == 0:
                        raise GeometryError(
                            f"OBJ face at line {line_number} uses index zero"
                        )
                    index = value - 1 if value > 0 else len(vertices) + value
                    if index < 0 or index >= len(vertices):
                        raise GeometryError(
                            f"OBJ face at line {line_number} has out-of-range index"
                        )
                    indexes.append(index)
                faces.append((material, tuple(indexes)))
        except GeometryError:
            raise
        except (TypeError, ValueError, OverflowError) as error:
            raise GeometryError(f"invalid OBJ geometry at line {line_number}") from error
    if not vertices:
        raise GeometryError("OBJ source contains no vertices")
    if not faces:
        raise GeometryError("OBJ source contains no faces")
    return ObjGeometry(np.asarray(vertices, dtype=float), tuple(faces))


def load_obj_geometry(path: Path) -> ObjGeometry:
    return parse_obj_text(path.read_text(encoding="utf-8", errors="strict"))


def select_source_points(
    geometry: ObjGeometry,
    prefixes: Tuple[str, ...],
    exact: Tuple[str, ...],
    complement: bool,
) -> np.ndarray:
    vertices = _point_cloud(geometry.vertices, "OBJ vertices", require_fit=False)
    normalized_prefixes = tuple(str(prefix).upper() for prefix in prefixes)
    exact_set = {str(name).upper() for name in exact}
    indexes = set()
    for material, face in geometry.faces:
        matched = material.upper() in exact_set or any(
            material.upper().startswith(prefix) for prefix in normalized_prefixes
        )
        if matched != complement:
            for index in face:
                if type(index) is not int or index < 0 or index >= len(vertices):
                    raise GeometryError("OBJ face contains an invalid vertex index")
                indexes.add(index)
    if not indexes:
        raise GeometryError("source material partition selected zero vertices")
    return vertices[sorted(indexes)]


def apply_matrix(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    cloud = _point_cloud(points, "points", require_fit=False)
    transform = _matrix4(matrix, "matrix", require_invertible=False)
    homogeneous = np.column_stack((cloud, np.ones(len(cloud))))
    return (homogeneous @ transform.T)[:, :3]


def _similarity(
    source: np.ndarray, target: np.ndarray, allow_reflection: bool
) -> np.ndarray:
    if len(source) < 3 or len(source) != len(target):
        raise GeometryError("ICP correspondence set is not meaningful")
    source_centroid = source.mean(axis=0)
    target_centroid = target.mean(axis=0)
    centered_source = source - source_centroid
    centered_target = target - target_centroid
    denominator = float((centered_source * centered_source).sum())
    if denominator <= 1e-12:
        raise GeometryError("ICP correspondence set has zero extent")
    u, singular, vt = np.linalg.svd(centered_source.T @ centered_target)
    signs = np.ones(3)
    if not allow_reflection and np.linalg.det(vt.T @ u.T) < 0.0:
        signs[-1] = -1.0
    rotation = vt.T @ np.diag(signs) @ u.T
    scale = float((singular * signs).sum() / denominator)
    if not math.isfinite(scale) or scale <= 1e-12:
        raise GeometryError("ICP correspondence set produced invalid scale")
    translation = target_centroid - scale * (rotation @ source_centroid)
    matrix = np.eye(4)
    matrix[:3, :3] = scale * rotation
    matrix[:3, 3] = translation
    return matrix


def _symmetric_p95(
    reference: np.ndarray, candidate: np.ndarray
) -> Tuple[float, float, float]:
    forward = cKDTree(reference).query(candidate, k=1)[0]
    reverse = cKDTree(candidate).query(reference, k=1)[0]
    forward_p95 = float(np.percentile(forward, 95))
    reverse_p95 = float(np.percentile(reverse, 95))
    return forward_p95, reverse_p95, max(forward_p95, reverse_p95)


def fit_surface(
    reference: np.ndarray,
    candidate: np.ndarray,
    seeds: Mapping[str, np.ndarray],
    iterations: int = 30,
    trim_percentile: float = 90.0,
) -> FitMetrics:
    reference_cloud = _point_cloud(reference, "reference", require_fit=True)
    candidate_cloud = _point_cloud(candidate, "candidate", require_fit=True)
    if not isinstance(seeds, Mapping) or not seeds:
        raise GeometryError("seeds must be a non-empty mapping")
    validated_seeds = []
    for name, value in seeds.items():
        if type(name) is not str or not name:
            raise GeometryError("seed names must be non-empty strings")
        seed = _matrix4(value, f"seed {name!r}", require_invertible=True)
        _uniform_similarity_scale(seed[:3, :3], f"seed {name!r}")
        validated_seeds.append(
            (name, seed)
        )
    if type(iterations) is not int or iterations <= 0:
        raise GeometryError("iterations must be a positive integer")
    if (
        type(trim_percentile) not in (int, float)
        or not math.isfinite(float(trim_percentile))
        or not 0.0 < float(trim_percentile) <= 100.0
    ):
        raise GeometryError("trim_percentile must be finite and in (0, 100]")

    best = None
    for seed_name, seed in validated_seeds:
        for allow_reflection in (False, True):
            matrix = seed.copy()
            current = apply_matrix(candidate_cloud, matrix)
            viable = True
            for _ in range(iterations):
                distances, indexes = cKDTree(reference_cloud).query(current, k=1)
                cutoff = np.percentile(distances, trim_percentile)
                keep = distances <= cutoff
                if int(np.count_nonzero(keep)) < 3:
                    nearest = np.argsort(distances)[:3]
                    keep = np.zeros(len(distances), dtype=bool)
                    keep[nearest] = True
                try:
                    increment = _similarity(
                        current[keep],
                        reference_cloud[np.asarray(indexes)[keep]],
                        allow_reflection,
                    )
                except GeometryError:
                    viable = False
                    break
                matrix = increment @ matrix
                updated = apply_matrix(candidate_cloud, matrix)
                if np.max(np.abs(updated - current)) < 1e-7:
                    current = updated
                    break
                current = updated
            if not viable:
                continue
            forward, reverse, symmetric = _symmetric_p95(reference_cloud, current)
            score = (symmetric, forward + reverse)
            if best is None or score < best[0]:
                best = (score, seed_name, matrix, forward, reverse)
    if best is None:
        raise GeometryError("no supplied seed produced a meaningful fit")

    _, seed_name, matrix, forward, reverse = best
    linear = matrix[:3, :3]
    determinant = float(np.linalg.det(linear))
    scale = _uniform_similarity_scale(linear, "fit matrix")
    orthogonal = linear / scale
    proper = (
        orthogonal
        if np.linalg.det(orthogonal) > 0.0
        else orthogonal @ np.diag((-1.0, 1.0, 1.0))
    )
    cosine = max(-1.0, min(1.0, (float(np.trace(proper)) - 1.0) / 2.0))
    rotation_deg = math.degrees(math.acos(cosine))
    return FitMetrics(
        seed_name,
        tuple(tuple(float(value) for value in row) for row in matrix),
        tuple(float(value) for value in matrix[:3, 3]),
        rotation_deg,
        determinant,
        scale,
        forward,
        reverse,
        max(forward, reverse),
    )


def classify_fit(
    metrics: FitMetrics, thresholds: Thresholds
) -> FitClassification:
    translation = float(np.linalg.norm(np.asarray(metrics.translation)))
    residual_ok = metrics.symmetric_p95_m <= thresholds.p95_m
    scale_ok = abs(metrics.uniform_scale - 1.0) <= thresholds.scale_error
    proper = metrics.determinant > 0.0
    identity = (
        translation <= thresholds.translation_m
        and metrics.rotation_deg <= thresholds.rotation_deg
        and scale_ok
    )
    reasons = []
    if not residual_ok:
        reasons.append("non-rigid residual exceeds tolerance")
    if not scale_ok:
        reasons.append("uniform scale correction exceeds tolerance")
    if not proper:
        reasons.append("reflection detected")
    if not identity:
        reasons.append("non-identity correction required")
    passes = residual_ok and proper and identity
    repairable = residual_ok and scale_ok and proper and not passes
    return FitClassification(passes, repairable, tuple(reasons))
