from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
import io
import math
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import py3d

from .engine import (
    compose_proxy_points,
    find_animation_overlaps,
    find_property_findings,
)
from .geometry import (
    FitClassification,
    FitMetrics,
    GeometryError,
    apply_matrix,
    classify_fit,
    fit_surface,
    load_obj_geometry,
    parse_obj_text,
    select_source_points,
)
from .manifest import VehicleManifest
from .model_cfg import ModelCfgError, convert_model_cfg
from .p3d_graph import GraphError, ProxyNode, direct_host_points, resolve_graph
from .pbo import PboFormatError, verify_deployed_closure
from .repair import RepairRefused, plan_repairs


IDENTITY = np.eye(4)
YAW180 = np.diag((-1.0, 1.0, -1.0, 1.0))
SEEDS = ("identity", "yaw180")


class AuditInputError(ValueError):
    """An input cannot support a complete, trustworthy audit."""


@dataclass(frozen=True)
class ModelSnapshot:
    path: Path
    identity: tuple[int, int, int, int]
    sha256: str
    payload: bytes = field(repr=False)


@dataclass(frozen=True)
class ProvenanceSnapshot:
    path: Path
    identity: tuple[int, int, int, int]
    sha256: str
    payload: bytes | None = field(default=None, repr=False)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AuditInputError("audit evidence contains a non-finite float")
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    raise AuditInputError(f"audit evidence is not JSON-safe: {type(value).__name__}")


@dataclass(frozen=True)
class AuditFinding:
    code: str
    severity: str
    piece: str
    host_lod: float
    path: str
    measured: Any
    expected: Any
    original_ordinal: int = field(default=0, compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.severity not in ("ERROR", "WARNING", "INFO"):
            raise AuditInputError(f"invalid finding severity: {self.severity!r}")
        _json_safe(self.measured)
        _json_safe(self.expected)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "piece": self.piece,
            "host_lod": self.host_lod,
            "path": self.path,
            "measured": _json_safe(self.measured),
            "expected": _json_safe(self.expected),
        }


@dataclass(frozen=True)
class LayerAudit:
    internal_lod: float
    metrics: FitMetrics
    classification: FitClassification

    def as_dict(self) -> dict[str, Any]:
        return {
            "internal_lod": self.internal_lod,
            "metrics": _metrics_dict(self.metrics),
            "classification": _classification_dict(self.classification),
        }


@dataclass(frozen=True)
class PreviewCloud:
    internal_lod: float
    source: tuple[tuple[float, float, float], ...]
    raw: tuple[tuple[float, float, float], ...]
    resolved: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class NodeAudit:
    node: ProxyNode
    raw: tuple[LayerAudit, ...]
    resolved: tuple[LayerAudit, ...]
    union: tuple[LayerAudit, ...]
    direct_host: tuple[LayerAudit, ...]
    previews: tuple[PreviewCloud, ...]
    eligible_operations: tuple[str, ...]
    affine_matrix: tuple[tuple[float, ...], ...] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "piece": self.node.piece,
            "host_lod": self.node.host_lod,
            "path": str(self.node.proxy_path),
            "proxy_basename": self.node.proxy_basename,
            "layers": {
                "raw": [item.as_dict() for item in self.raw],
                "resolved": [item.as_dict() for item in self.resolved],
                "union": [item.as_dict() for item in self.union],
            },
            "direct_host": [item.as_dict() for item in self.direct_host],
            "eligible_operations": list(self.eligible_operations),
            "affine_matrix": _json_safe(self.affine_matrix),
        }


@dataclass(frozen=True)
class AuditResult:
    vehicle: str
    nodes: tuple[NodeAudit, ...]
    findings: tuple[AuditFinding, ...]
    overall_status: str
    alignment_status: str
    source_available: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "vehicle": self.vehicle,
            "overall_status": self.overall_status,
            "alignment_status": self.alignment_status,
            "source_available": self.source_available,
            "findings": [finding.as_dict() for finding in self.findings],
            "nodes": [node.as_dict() for node in self.nodes],
        }


def _metrics_dict(metrics: FitMetrics) -> dict[str, Any]:
    return _json_safe(
        {
            "seed": metrics.seed,
            "matrix": metrics.matrix,
            "translation": metrics.translation,
            "rotation_deg": metrics.rotation_deg,
            "determinant": metrics.determinant,
            "uniform_scale": metrics.uniform_scale,
            "forward_p95_m": metrics.forward_p95_m,
            "reverse_p95_m": metrics.reverse_p95_m,
            "symmetric_p95_m": metrics.symmetric_p95_m,
        }
    )


def _classification_dict(classification: FitClassification) -> dict[str, Any]:
    return {
        "passes": classification.passes,
        "repairable": classification.repairable,
        "reasons": list(classification.reasons),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise AuditInputError(f"cannot hash provenance file {path}: {error}") from error
    return digest.hexdigest().upper()


def _identity(stat_result: os.stat_result) -> tuple[int, int, int, int]:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def _capture_model(path: Path, label: str) -> ModelSnapshot:
    path = Path(path)
    try:
        with path.open("rb") as handle:
            handle_before = _identity(os.fstat(handle.fileno()))
            path_before = _identity(path.stat())
            payload = handle.read()
            handle_after = _identity(os.fstat(handle.fileno()))
            path_after = _identity(path.stat())
    except OSError as error:
        raise AuditInputError(f"cannot capture {label} model {path}: {error}") from error
    if not (
        handle_before == path_before == handle_after == path_after
        and len(payload) == handle_before[2]
    ):
        raise AuditInputError(f"{label} model generation changed while capturing: {path}")
    return ModelSnapshot(
        path,
        handle_before,
        hashlib.sha256(payload).hexdigest().upper(),
        payload,
    )


def _verify_model(snapshot: ModelSnapshot) -> None:
    try:
        with snapshot.path.open("rb") as handle:
            handle_before = _identity(os.fstat(handle.fileno()))
            path_before = _identity(snapshot.path.stat())
            payload = handle.read()
            handle_after = _identity(os.fstat(handle.fileno()))
            path_after = _identity(snapshot.path.stat())
    except OSError as error:
        raise AuditInputError(
            f"model generation is no longer accessible: {snapshot.path}: {error}"
        ) from error
    digest = hashlib.sha256(payload).hexdigest().upper()
    if not (
        handle_before
        == path_before
        == handle_after
        == path_after
        == snapshot.identity
        and digest == snapshot.sha256
    ):
        raise AuditInputError(f"model generation changed during audit: {snapshot.path}")


def _provenance(
    manifest: VehicleManifest,
) -> tuple[tuple[Path, str, str, bool], ...]:
    items = [
        (manifest.source_scene, manifest.source_scene_sha256, "source scene", False),
    ]
    items.extend(
        (item.path, item.sha256, "source dependency", False)
        for item in manifest.source_dependencies
    )
    items.extend(
        (
            piece.source_obj,
            piece.source_sha256,
            f"piece source {piece.name}",
            True,
        )
        for piece in manifest.pieces
    )
    return tuple(items)


def _capture_provenance(
    path: Path, expected: str, label: str, retain_payload: bool
) -> ProvenanceSnapshot:
    digest = hashlib.sha256()
    retained = bytearray() if retain_payload else None
    try:
        with path.open("rb") as handle:
            handle_before = _identity(os.fstat(handle.fileno()))
            path_before = _identity(path.stat())
            total = 0
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
                total += len(block)
                if retained is not None:
                    retained.extend(block)
            handle_after = _identity(os.fstat(handle.fileno()))
            path_after = _identity(path.stat())
    except OSError as error:
        raise AuditInputError(f"cannot capture {label} {path}: {error}") from error
    if not (
        handle_before == path_before == handle_after == path_after
        and total == handle_before[2]
    ):
        raise AuditInputError(f"{label} generation changed while capturing: {path}")
    actual = digest.hexdigest().upper()
    if actual != expected.upper():
        raise AuditInputError(
            f"{label} SHA256 mismatch: {path}; expected {expected.upper()}, got {actual}"
        )
    return ProvenanceSnapshot(
        path,
        handle_before,
        actual,
        bytes(retained) if retained is not None else None,
    )


def _snapshot_sources(
    manifest: VehicleManifest,
) -> tuple[dict[Path, ProvenanceSnapshot], tuple[tuple[Path, str], ...]]:
    present: dict[Path, ProvenanceSnapshot] = {}
    missing = []
    for path, expected, label, retain_payload in _provenance(manifest):
        if not path.exists():
            missing.append((path, label))
            continue
        if not path.is_file():
            raise AuditInputError(f"{label} is not a file: {path}")
        present[path] = _capture_provenance(
            path, expected, label, retain_payload
        )
    return present, tuple(missing)


def _verify_provenance(snapshot: ProvenanceSnapshot) -> None:
    digest = hashlib.sha256()
    try:
        with snapshot.path.open("rb") as handle:
            handle_before = _identity(os.fstat(handle.fileno()))
            path_before = _identity(snapshot.path.stat())
            total = 0
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
                total += len(block)
            handle_after = _identity(os.fstat(handle.fileno()))
            path_after = _identity(snapshot.path.stat())
    except OSError as error:
        raise AuditInputError(
            f"source provenance is no longer accessible: {snapshot.path}: {error}"
        ) from error
    if not (
        handle_before
        == path_before
        == handle_after
        == path_after
        == snapshot.identity
        and total == snapshot.identity[2]
        and digest.hexdigest().upper() == snapshot.sha256
    ):
        raise AuditInputError(
            f"source provenance generation changed during audit: {snapshot.path}"
        )


def _rehash_sources(snapshot: Mapping[Path, ProvenanceSnapshot]) -> None:
    for item in snapshot.values():
        _verify_provenance(item)


def _validated_axis_deferrals(
    model: py3d.P3D,
    errors: tuple[Any, ...],
    allowed_axis_parent_selections: tuple[str, ...],
    path: Path,
) -> tuple[tuple[str, float], ...]:
    axis_errors = tuple(
        finding
        for finding in errors
        if finding.code == "ERR_AXIS_SELECTION_MISSING"
    )
    other_errors = tuple(
        finding
        for finding in errors
        if finding.code != "ERR_AXIS_SELECTION_MISSING"
    )
    if other_errors:
        raise AuditInputError(f"invalid host MLOD {path}: {other_errors}")

    first_visual = next((lod for lod in model.lods if lod.kind() == "visual"), None)
    occurrences = []
    if first_visual is not None:
        for memory_lod in (lod for lod in model.lods if lod.kind() == "memory"):
            for axis_name, selection in memory_lod.selections.items():
                if not axis_name.endswith("_axis"):
                    continue
                base = axis_name[:-len("_axis")]
                if base not in first_visual.selections:
                    occurrences.append((base, axis_name, selection))

    if len(axis_errors) != len(occurrences):
        raise AuditInputError(
            "host axis validation evidence cardinality mismatch: "
            f"validator={len(axis_errors)}, recomputed={len(occurrences)}"
        )

    allowed = set(allowed_axis_parent_selections)
    deferred = []
    for base in allowed_axis_parent_selections:
        matches = [item for item in occurrences if item[0] == base]
        if len(matches) != 1:
            raise AuditInputError(
                f"allowed host axis parent {base!r} maps to {len(matches)} findings"
            )
        _, axis_name, selection = matches[0]
        if len(selection.points) != 2:
            raise AuditInputError(
                f"allowed host axis {axis_name!r} has {len(selection.points)} points; expected 2"
            )
        deferred.append((base, float(first_visual.resolution)))

    unlisted = sorted(base for base, _, _ in occurrences if base not in allowed)
    if unlisted:
        raise AuditInputError(f"unlisted host axis-selection errors: {unlisted}")
    return tuple(deferred)


def _load_p3d(
    snapshot: ModelSnapshot,
    label: str,
    *,
    allowed_axis_parent_selections: tuple[str, ...] | None = None,
) -> tuple[py3d.P3D, tuple[tuple[str, float], ...]]:
    try:
        model = py3d.P3D(io.BytesIO(snapshot.payload))
        errors = tuple(item for item in model.validate() if item.severity == "ERROR")
    except (AssertionError, EOFError, ValueError, TypeError) as error:
        raise AuditInputError(
            f"cannot read {label} MLOD {snapshot.path}: {error}"
        ) from error
    deferred = ()
    if allowed_axis_parent_selections is not None:
        deferred = _validated_axis_deferrals(
            model,
            errors,
            allowed_axis_parent_selections,
            snapshot.path,
        )
        errors = ()
    if errors:
        raise AuditInputError(f"invalid {label} MLOD {snapshot.path}: {errors}")
    return model, deferred


def _visual_lods(model: py3d.P3D, path: Path) -> tuple[Any, ...]:
    lods = tuple(lod for lod in model.lods if 0.0 <= float(lod.resolution) < 1000.0)
    if not lods:
        raise AuditInputError(f"proxy contains no visual LOD: {path}")
    return lods


def _lod_points(lod: Any, path: Path) -> np.ndarray:
    try:
        points = np.asarray([point.coords for point in lod.points], dtype=float)
    except (AttributeError, TypeError, ValueError, OverflowError) as error:
        raise AuditInputError(f"invalid point cloud in {path}@{lod.resolution}") from error
    if points.ndim != 2 or points.shape[1:] != (3,) or not np.isfinite(points).all():
        raise AuditInputError(f"invalid point cloud in {path}@{lod.resolution}")
    return points


def _fit(reference: np.ndarray, candidate: np.ndarray, manifest: VehicleManifest, internal_lod: float) -> LayerAudit:
    metrics = fit_surface(
        reference,
        candidate,
        {"identity": IDENTITY, "yaw180": YAW180},
    )
    return LayerAudit(internal_lod, metrics, classify_fit(metrics, manifest.thresholds))


def _cloud_tuple(points: np.ndarray) -> tuple[tuple[float, float, float], ...]:
    return tuple(tuple(float(value) for value in row) for row in points)


def _host_lod_by_resolution(host: py3d.P3D, resolution: float) -> Any:
    matches = [lod for lod in host.lods if float(lod.resolution) == resolution]
    if len(matches) != 1:
        raise AuditInputError(f"host visual LOD cardinality for {resolution} is {len(matches)}")
    return matches[0]


def _eligible_operations(
    node: ProxyNode,
    raw: tuple[LayerAudit, ...],
    reference_clouds: tuple[np.ndarray, ...],
    raw_clouds: tuple[np.ndarray, ...],
    property_codes: tuple[str, ...],
    manifest: VehicleManifest,
) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...] | None]:
    eligible = []
    affine_matrix = None
    if (
        "set-autocenter-zero" in node.repairs
        and "ENGINE-AUTOCENTER-UNCONFIRMED" in property_codes
    ):
        eligible.append("set-autocenter-zero")

    yaw_ok = bool(raw) and all(
        item.metrics.seed == "yaw180" and item.classification.repairable for item in raw
    )
    if yaw_ok and "yaw180" in node.repairs:
        for reference, candidate in zip(reference_clouds, raw_clouds):
            corrected = apply_matrix(candidate, YAW180)
            check = fit_surface(reference, corrected, {"identity": IDENTITY})
            if not classify_fit(check, manifest.thresholds).passes or check.seed != "identity":
                yaw_ok = False
                break
    if yaw_ok and "yaw180" in node.repairs:
        eligible.append("yaw180")

    if raw and "affine-fit" in node.repairs and all(item.classification.repairable for item in raw):
        matrices = [np.asarray(item.metrics.matrix, dtype=float) for item in raw]
        if all(np.allclose(matrices[0], item, rtol=1.0e-9, atol=1.0e-9) for item in matrices[1:]):
            candidate = tuple(
                tuple(float(value) for value in row) for row in matrices[0]
            )
            try:
                plan_repairs(
                    (node,),
                    "affine-fit",
                    fit_matrices={(node.piece, node.host_lod): candidate},
                )
            except RepairRefused:
                pass
            else:
                affine_matrix = candidate
                eligible.append("affine-fit")
    return tuple(eligible), affine_matrix


def audit(manifest: VehicleManifest) -> AuditResult:
    """Run the ordered, read-only vehicle proxy contract audit."""
    findings: list[AuditFinding] = []
    ordinal = 0

    def add(
        code: str,
        severity: str,
        piece: str,
        host_lod: float,
        path: str,
        measured: Any,
        expected: Any,
    ) -> None:
        nonlocal ordinal
        findings.append(
            AuditFinding(code, severity, piece, host_lod, path, measured, expected, ordinal)
        )
        ordinal += 1

    try:
        source_snapshot, missing_sources = _snapshot_sources(manifest)
        for path, label in missing_sources:
            add(
                "SOURCE-UNAVAILABLE",
                "ERROR",
                "",
                -1.0,
                str(path),
                {"available": False, "kind": label},
                {"available": True},
            )

        host_snapshot = _capture_model(manifest.host_p3d, "host")
        nodes = resolve_graph(manifest)
        _verify_model(host_snapshot)
        host, deferred_axes = _load_p3d(
            host_snapshot,
            "host",
            allowed_axis_parent_selections=manifest.allowed_axis_parent_selections,
        )
        for base, visual_resolution in deferred_axes:
            add(
                "P3D-AXIS-SELECTION-DEFERRED",
                "WARNING",
                "",
                visual_resolution,
                str(manifest.host_p3d),
                {
                    "axis_selection": f"{base}_axis",
                    "parent_selection": base,
                    "source_code": "ERR_AXIS_SELECTION_MISSING",
                },
                {"runtime_gate": "steering/damper animation in-game"},
            )

        direct_owners: dict[float, set[str]] = {}
        for node in nodes:
            if node.include_host_direct:
                direct_owners.setdefault(node.host_lod, set()).add(node.piece)
        ambiguous_owners = {
            lod: sorted(owners)
            for lod, owners in direct_owners.items()
            if len(owners) > 1
        }
        if ambiguous_owners:
            raise AuditInputError(
                "more than one include_host_direct owner at a host LOD: "
                f"{ambiguous_owners}"
            )

        source_by_piece: dict[str, tuple[np.ndarray, np.ndarray | None, np.ndarray]] = {}
        for piece in manifest.pieces:
            piece_snapshot = source_snapshot.get(piece.source_obj)
            if piece_snapshot is None:
                continue
            if piece_snapshot.payload is None:
                raise AuditInputError(
                    f"piece source snapshot has no retained bytes: {piece.source_obj}"
                )
            geometry = parse_obj_text(
                piece_snapshot.payload.decode("utf-8", errors="strict")
            )
            full = apply_matrix(geometry.vertices, np.asarray(manifest.source_matrix, dtype=float))
            if piece.include_host_direct:
                direct = apply_matrix(
                    select_source_points(
                        geometry,
                        piece.host_direct_material_prefixes,
                        piece.host_direct_material_exact,
                        complement=False,
                    ),
                    np.asarray(manifest.source_matrix, dtype=float),
                )
                proxy = apply_matrix(
                    select_source_points(
                        geometry,
                        piece.host_direct_material_prefixes,
                        piece.host_direct_material_exact,
                        complement=True,
                    ),
                    np.asarray(manifest.source_matrix, dtype=float),
                )
            else:
                direct = None
                proxy = full
            source_by_piece[piece.name] = (proxy, direct, full)

        proxy_snapshots: dict[Path, ModelSnapshot] = {}
        for node in nodes:
            key = node.proxy_path.resolve(strict=False)
            if key not in proxy_snapshots:
                proxy_snapshots[key] = _capture_model(node.proxy_path, "proxy")

        loaded_nodes = []
        for node in nodes:
            model, _ = _load_p3d(
                proxy_snapshots[node.proxy_path.resolve(strict=False)], "proxy"
            )
            loaded_nodes.append((node, _visual_lods(model, node.proxy_path)))

        node_audits = []
        for node, visual_lods in loaded_nodes:
            raw_layers = []
            resolved_layers = []
            union_layers = []
            direct_layers = []
            previews = []
            reference_clouds = []
            raw_clouds = []
            host_lod = _host_lod_by_resolution(host, node.host_lod)
            source = source_by_piece.get(node.piece)

            if node.ambiguous:
                add(
                    "ENGINE-FRAME-AMBIGUOUS",
                    "ERROR",
                    node.piece,
                    node.host_lod,
                    str(node.host_path),
                    {"ambiguous": True, "selection": node.proxy_selection},
                    {"ambiguous": False},
                )

            property_findings = find_property_findings(
                visual_lods, manifest.required_properties
            )
            property_codes = tuple(item.code for item in property_findings)
            for item in property_findings:
                add(
                    item.code,
                    "ERROR",
                    node.piece,
                    node.host_lod,
                    str(node.proxy_path),
                    {
                        "internal_lod": item.lod_resolution,
                        "property": item.property_name,
                        "value": item.actual_value,
                    },
                    {"property": item.property_name, "value": item.expected_value},
                )

            for visual_lod in visual_lods:
                raw_points = _lod_points(visual_lod, node.proxy_path)
                try:
                    resolved_points = compose_proxy_points(
                        raw_points,
                        node.anchor,
                        node.frame,
                        manifest.canonical_proxy_frame,
                    )
                except ValueError as error:
                    add(
                        "ENGINE-FRAME-INVALID",
                        "ERROR",
                        node.piece,
                        node.host_lod,
                        str(node.host_path),
                        {"error": str(error), "selection": node.proxy_selection},
                        {"proper_rigid_frame": True},
                    )
                    resolved_points = raw_points

                source_points = np.empty((0, 3), dtype=float)
                if source is not None:
                    proxy_reference, direct_reference, full_reference = source
                    source_points = full_reference
                    raw_layers.append(
                        _fit(proxy_reference, raw_points, manifest, float(visual_lod.resolution))
                    )
                    resolved_layers.append(
                        _fit(proxy_reference, resolved_points, manifest, float(visual_lod.resolution))
                    )
                    reference_clouds.append(proxy_reference)
                    raw_clouds.append(raw_points)
                    if node.include_host_direct:
                        assert direct_reference is not None
                        direct_points = direct_host_points(host_lod)
                        direct_layers.append(
                            _fit(
                                direct_reference,
                                direct_points,
                                manifest,
                                float(visual_lod.resolution),
                            )
                        )
                        assembled = np.vstack((direct_points, resolved_points))
                        union_reference = full_reference
                    else:
                        assembled = resolved_points
                        union_reference = proxy_reference
                    union_layers.append(
                        _fit(union_reference, assembled, manifest, float(visual_lod.resolution))
                    )
                previews.append(
                    PreviewCloud(
                        float(visual_lod.resolution),
                        _cloud_tuple(source_points),
                        _cloud_tuple(raw_points),
                        _cloud_tuple(resolved_points),
                    )
                )

            raw_tuple = tuple(raw_layers)
            resolved_tuple = tuple(resolved_layers)
            union_tuple = tuple(union_layers)
            direct_tuple = tuple(direct_layers)
            if raw_tuple and not all(
                item.classification.passes
                for layer in (raw_tuple, resolved_tuple, union_tuple, direct_tuple)
                for item in layer
            ):
                add(
                    "ALIGNMENT-MISMATCH",
                    "ERROR",
                    node.piece,
                    node.host_lod,
                    str(node.proxy_path),
                    {
                        "raw": [item.as_dict() for item in raw_tuple],
                        "resolved": [item.as_dict() for item in resolved_tuple],
                        "union": [item.as_dict() for item in union_tuple],
                    },
                    {
                        "translation_m": manifest.thresholds.translation_m,
                        "rotation_deg": manifest.thresholds.rotation_deg,
                        "scale_error": manifest.thresholds.scale_error,
                        "p95_m": manifest.thresholds.p95_m,
                    },
                )

            eligible, affine_matrix = _eligible_operations(
                node,
                raw_tuple,
                tuple(reference_clouds),
                tuple(raw_clouds),
                property_codes,
                manifest,
            )
            node_audits.append(
                NodeAudit(
                    node,
                    raw_tuple,
                    resolved_tuple,
                    union_tuple,
                    direct_tuple,
                    tuple(previews),
                    eligible,
                    affine_matrix,
                )
            )

        animated = convert_model_cfg(manifest.model_cfg, manifest.cfgconvert)
        declared_host_overlaps = {
            (
                allowance.host_lod,
                allowance.proxy_selection_name,
                allowance.animated_selection,
            )
            for allowance in manifest.allowed_host_animation_overlaps
        }
        actual_host_overlaps = Counter()
        visual_host_lods = tuple(
            lod for lod in host.lods if 0.0 <= float(lod.resolution) < 1000.0
        )
        for host_lod in visual_host_lods:
            for item in find_animation_overlaps(host_lod, animated, ()):
                if (
                    item.code == "ENGINE-ANIMATION-OVERLAP"
                    and item.proxy_selection_name is not None
                    and item.selection is not None
                ):
                    actual_host_overlaps[
                        (
                            float(host_lod.resolution),
                            item.proxy_selection_name,
                            item.selection,
                        )
                    ] += 1
        invalid_cardinality = {
            triple: actual_host_overlaps[triple]
            for triple in declared_host_overlaps
            if actual_host_overlaps[triple] != 1
        }
        if invalid_cardinality:
            raise AuditInputError(
                "allowed_host_animation_overlaps must match exactly one occurrence: "
                f"{sorted(invalid_cardinality.items())}"
            )
        lowered_piece_overlaps = {
            (
                node.host_lod,
                node.proxy_selection.strip().lower(),
                selection.strip().lower(),
            )
            for node in nodes
            for selection in node.allowed_animated_selections
        }
        allowed = declared_host_overlaps | lowered_piece_overlaps
        by_key = {(node.host_lod, node.proxy_basename): node for node in nodes}
        for host_lod in visual_host_lods:
            for item in find_animation_overlaps(host_lod, animated, allowed):
                node = by_key.get((float(host_lod.resolution), item.proxy_basename or ""))
                add(
                    item.code,
                    "ERROR",
                    node.piece if node is not None else "",
                    float(host_lod.resolution),
                    str(manifest.host_p3d),
                    {
                        "selection": item.selection,
                        "proxy_basename": item.proxy_basename,
                        "animation_classes": item.animation_classes,
                    },
                    {"allowed": False},
                )

        model_snapshots = (host_snapshot, *proxy_snapshots.values())
        for snapshot in model_snapshots:
            _verify_model(snapshot)
        deployed_findings = verify_deployed_closure(manifest, nodes)
        for snapshot in model_snapshots:
            _verify_model(snapshot)
        for item in deployed_findings:
            add(
                item.code,
                "ERROR",
                "",
                -1.0,
                item.path,
                {
                    "message": item.message,
                    "source_sha256": item.source_sha256,
                    "deployed_sha256": item.deployed_sha256,
                },
                {"source_equals_deployed": True},
            )

        _rehash_sources(source_snapshot)
        for snapshot in model_snapshots:
            _verify_model(snapshot)
    except AuditInputError:
        raise
    except (GraphError, GeometryError, ModelCfgError, PboFormatError) as error:
        raise AuditInputError(str(error)) from error
    except (OSError, AssertionError, EOFError, ValueError, TypeError) as error:
        raise AuditInputError(f"invalid audit input: {error}") from error

    ordered = tuple(
        sorted(
            findings,
            key=lambda item: (
                item.piece,
                item.host_lod,
                item.code,
                item.path,
                item.original_ordinal,
            ),
        )
    )
    source_available = not missing_sources
    overall = "FAIL" if any(item.severity == "ERROR" for item in ordered) else "PASS"
    if not source_available:
        alignment = "UNKNOWN"
    else:
        alignment_codes = (
            "ALIGNMENT-",
            "ENGINE-FRAME-",
            "ENGINE-AUTOCENTER-UNCONFIRMED",
        )
        alignment = (
            "FAIL"
            if any(
                item.severity == "ERROR"
                and (
                    item.code.startswith(alignment_codes[0])
                    or item.code.startswith(alignment_codes[1])
                    or item.code == alignment_codes[2]
                )
                for item in ordered
            )
            else "PASS"
        )
    return AuditResult(
        manifest.vehicle,
        tuple(node_audits),
        ordered,
        overall,
        alignment,
        source_available,
    )
