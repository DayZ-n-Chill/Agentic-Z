from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Mapping, Sequence

import numpy as np


_FRAME_ATOL = 1e-9


@dataclass(frozen=True)
class EngineFinding:
    code: str
    lod_resolution: float
    selection: str | None = None
    proxy_selection_name: str | None = None
    proxy_basename: str | None = None
    animation_classes: tuple[str, ...] = ()
    property_name: str | None = None
    expected_value: str | None = None
    actual_value: str | None = None


def _finite_array(value, shape: tuple[int, ...], label: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if array.shape != shape:
        raise ValueError(f"{label} must have shape {shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must be finite")
    return array


def _orientation_frame(value, label: str) -> tuple[np.ndarray, np.ndarray]:
    frame = _finite_array(value, (3, 3), label)
    try:
        with np.errstate(over="raise", invalid="raise"):
            gram = frame.T @ frame
            determinant = float(np.linalg.det(frame))
        inverse = np.linalg.inv(frame)
    except (FloatingPointError, np.linalg.LinAlgError) as error:
        raise ValueError(f"{label} must be a proper orthonormal basis") from error
    if not np.all(np.isfinite(gram)) or not np.isfinite(determinant):
        raise ValueError(f"{label} must be a proper orthonormal basis")
    if not np.allclose(
        gram, np.eye(3), rtol=0.0, atol=_FRAME_ATOL
    ) or not np.isclose(
        determinant, 1.0, rtol=0.0, atol=_FRAME_ATOL
    ):
        raise ValueError(f"{label} must be a proper orthonormal basis")
    if not np.all(np.isfinite(inverse)):
        raise ValueError(f"{label} inverse must be finite")
    return frame, inverse


def compose_proxy_points(
    points, anchor, actual_frame, canonical_frame
) -> np.ndarray:
    """Compose candidate proxy points into engine space without recentering."""
    try:
        candidate = np.asarray(points, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("points must be numeric") from error
    if candidate.ndim != 2 or candidate.shape[1] != 3:
        raise ValueError("points must have shape Nx3")
    if not np.all(np.isfinite(candidate)):
        raise ValueError("points must be finite")
    translation = _finite_array(anchor, (3,), "anchor")
    actual, _ = _orientation_frame(actual_frame, "actual_frame")
    _, canonical_inverse = _orientation_frame(
        canonical_frame, "canonical_frame"
    )
    try:
        with np.errstate(over="raise", invalid="raise"):
            delta = actual @ canonical_inverse
    except FloatingPointError as error:
        raise ValueError("frame delta must be finite and rigid") from error
    _orientation_frame(delta, "frame delta")
    try:
        with np.errstate(over="raise", invalid="raise"):
            result = candidate @ delta.T + translation
    except FloatingPointError as error:
        raise ValueError("composed points must be finite") from error
    if not np.all(np.isfinite(result)):
        raise ValueError("composed points must be finite")
    return result


def find_property_findings(
    lods, required_properties: Sequence[tuple[str, str]]
) -> tuple[EngineFinding, ...]:
    findings = []
    for lod in lods:
        for property_name, expected_value in required_properties:
            actual_value = lod.properties.get(property_name)
            if actual_value == expected_value:
                continue
            if property_name == "autocenter" and expected_value == "0":
                code = "ENGINE-AUTOCENTER-UNCONFIRMED"
            else:
                code = "ENGINE-PROPERTY-MISMATCH"
            findings.append(
                EngineFinding(
                    code=code,
                    lod_resolution=float(lod.resolution),
                    property_name=property_name,
                    expected_value=expected_value,
                    actual_value=actual_value,
                )
            )
    return tuple(findings)


def _proxy_basename(proxy_path: str) -> str:
    return Path(proxy_path.replace("\\", "/")).name.lower()


def _validated_proxy_face_id(lod, proxy_name: str) -> int | None:
    selection = lod.selections.get(proxy_name)
    if selection is None:
        return None
    try:
        selected_point_ids = {id(point) for point in selection.points}
        selected_faces = tuple(selection.faces)
        if len(selected_point_ids) != 3 or len(selected_faces) != 1:
            return None
        face = selected_faces[0]
        if all(id(face) != id(lod_face) for lod_face in lod.faces):
            return None
        if len(face.vertices) != 3:
            return None
        referenced_point_ids = set()
        for vertex in face.vertices:
            point_index = int(vertex.point_index)
            if point_index < 0 or point_index >= len(lod.points):
                return None
            referenced_point_ids.add(id(lod.points[point_index]))
    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
        return None
    if referenced_point_ids != selected_point_ids:
        return None
    return id(face)


def find_animation_overlaps(
    lod,
    animated_selections: Mapping[str, Sequence[str]],
    allowed_host_animation_overlaps: Collection[tuple[float, str, str]],
) -> tuple[EngineFinding, ...]:
    """Report animated selections that share face objects with host proxies."""
    animated = []
    for name, animation_classes in animated_selections.items():
        normalized_name = name.lower()
        face_ids = set()
        for lod_name, selection in lod.selections.items():
            if lod_name.lower() == normalized_name:
                face_ids.update(id(face) for face in selection.faces)
        animated.append(
            (normalized_name, tuple(animation_classes), face_ids)
        )

    findings = []
    proxies = sorted(
        lod.get_proxies(), key=lambda proxy: (proxy["path"].lower(), proxy["name"])
    )
    for proxy in proxies:
        basename = _proxy_basename(proxy["path"])
        proxy_selection_name = str(proxy["name"]).strip().lower()
        proxy_face_id = _validated_proxy_face_id(lod, proxy["name"])
        if proxy_face_id is None:
            findings.append(
                EngineFinding(
                    code="ENGINE-PROXY-SELECTION-INVALID",
                    lod_resolution=float(lod.resolution),
                    selection=proxy["name"],
                    proxy_selection_name=proxy_selection_name,
                    proxy_basename=basename,
                )
            )
            continue
        proxy_face_ids = {proxy_face_id}
        for selection_name, animation_classes, animated_face_ids in sorted(animated):
            if not proxy_face_ids.intersection(animated_face_ids):
                continue
            exact_triple = (
                float(lod.resolution),
                proxy_selection_name,
                selection_name,
            )
            if exact_triple in allowed_host_animation_overlaps:
                continue
            findings.append(
                EngineFinding(
                    code="ENGINE-ANIMATION-OVERLAP",
                    lod_resolution=float(lod.resolution),
                    selection=selection_name,
                    proxy_selection_name=proxy_selection_name,
                    proxy_basename=basename,
                    animation_classes=animation_classes,
                )
            )
    return tuple(findings)
