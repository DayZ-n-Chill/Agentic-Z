from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Tuple


_ALLOWED_REPAIRS = frozenset({"set-autocenter-zero", "yaw180", "affine-fit"})
_ALLOWED_FIT_COMPONENTS = frozenset(
    {"translation", "rotation", "reflection", "uniform-scale"}
)


class ManifestError(ValueError):
    """Manifest violates the fail-closed schema."""


@dataclass(frozen=True)
class HashedPath:
    path: Path
    sha256: str


@dataclass(frozen=True)
class Thresholds:
    translation_m: float
    rotation_deg: float
    scale_error: float
    p95_m: float


@dataclass(frozen=True)
class VariantSpec:
    host_lod: float
    expected_proxy_basename: str
    repairs: Tuple[str, ...]
    allowed_fit_components: Tuple[str, ...]


@dataclass(frozen=True)
class PieceSpec:
    name: str
    source_obj: Path
    source_sha256: str
    include_host_direct: bool
    host_direct_material_prefixes: Tuple[str, ...]
    host_direct_material_exact: Tuple[str, ...]
    allowed_animated_selections: Tuple[str, ...]
    variants: Tuple[VariantSpec, ...]


@dataclass(frozen=True)
class AllowedHostAnimationOverlap:
    host_lod: float
    proxy_selection_name: str
    animated_selection: str


@dataclass(frozen=True)
class VehicleManifest:
    vehicle: str
    addon_root: Path
    host_p3d: Path
    model_cfg: Path
    cfgconvert: Path
    deployed_pbo: Path
    pbo_prefix: str
    source_scene: Path
    source_scene_sha256: str
    source_dependencies: Tuple[HashedPath, ...]
    source_matrix: Tuple[Tuple[float, ...], ...]
    canonical_proxy_frame: Tuple[Tuple[float, ...], ...]
    allowed_host_animation_overlaps: Tuple[AllowedHostAnimationOverlap, ...]
    allowed_axis_parent_selections: Tuple[str, ...]
    required_properties: Tuple[Tuple[str, str], ...]
    thresholds: Thresholds
    pieces: Tuple[PieceSpec, ...]


def _absolute(value: str, field: str) -> Path:
    if type(value) is not str:
        raise ManifestError(f"{field} must be an absolute path string")
    path = Path(value)
    if not path.is_absolute():
        raise ManifestError(f"{field} must be absolute: {value}")
    return path


def _hash(value: str, field: str) -> str:
    if type(value) is not str:
        raise ManifestError(f"{field} must be SHA256 hex")
    normalized = value.upper()
    if len(normalized) != 64 or any(
        character not in "0123456789ABCDEF" for character in normalized
    ):
        raise ManifestError(f"{field} must be SHA256 hex")
    return normalized


def _finite_json_number(value: object, field: str) -> float:
    if type(value) not in (int, float):
        raise ManifestError(f"{field} must be a finite JSON number")
    try:
        normalized = float(value)
    except OverflowError as error:
        raise ManifestError(f"{field} must be a finite JSON number") from error
    if not math.isfinite(normalized):
        raise ManifestError(f"{field} must be a finite JSON number")
    return normalized


def _matrix(
    value: object, field: str, expected_rows: int, expected_columns: int
) -> Tuple[Tuple[float, ...], ...]:
    if type(value) is not list or len(value) != expected_rows:
        raise ManifestError(
            f"{field} must be a {expected_rows}x{expected_columns} array"
        )
    rows = []
    for row_index, row in enumerate(value):
        if type(row) is not list or len(row) != expected_columns:
            raise ManifestError(
                f"{field} must be a {expected_rows}x{expected_columns} array"
            )
        rows.append(
            tuple(
                _finite_json_number(
                    cell, f"{field}[{row_index}][{column_index}]"
                )
                for column_index, cell in enumerate(row)
            )
        )
    return tuple(rows)


def _string_tuple(value: object, field: str) -> Tuple[str, ...]:
    if type(value) is not list or any(type(item) is not str for item in value):
        raise ManifestError(f"{field} must be an array of strings")
    return tuple(value)


def _normalized_unique_string_tuple(value: object, field: str) -> Tuple[str, ...]:
    values = _string_tuple(value, field)
    normalized = tuple(item.strip().lower() for item in values)
    if any(not item for item in normalized):
        raise ManifestError(f"{field} values must be non-empty strings")
    if len(set(normalized)) != len(normalized):
        raise ManifestError(f"{field} values must be unique after normalization")
    return normalized


def _normalized_nonempty_string(value: object, field: str) -> str:
    normalized = _string(value, field).strip().lower()
    if not normalized:
        raise ManifestError(f"{field} must be a non-empty string")
    return normalized


def _string(value: object, field: str) -> str:
    if type(value) is not str:
        raise ManifestError(f"{field} must be a string")
    return value


def _json_object(value: object, field: str) -> dict:
    if type(value) is not dict:
        raise ManifestError(f"{field} must be an object")
    return value


def _json_array(value: object, field: str) -> list:
    if type(value) is not list:
        raise ManifestError(f"{field} must be an array")
    return value


def _string_mapping(value: object, field: str) -> Tuple[Tuple[str, str], ...]:
    mapping = _json_object(value, field)
    if any(type(key) is not str or type(item) is not str for key, item in mapping.items()):
        raise ManifestError(f"{field} must map strings to strings")
    return tuple(sorted(mapping.items()))


def _parse_manifest(data: object) -> VehicleManifest:
    data = _json_object(data, "manifest root")
    schema_version = data.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        raise ManifestError("schema_version must be 1")
    required = (
        "vehicle",
        "addon_root",
        "host_p3d",
        "model_cfg",
        "cfgconvert",
        "deployed_pbo",
        "pbo_prefix",
        "source",
        "canonical_proxy_frame",
        "required_properties",
        "thresholds",
        "pieces",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ManifestError(f"missing fields: {missing}")
    vehicle = _string(data["vehicle"], "vehicle")
    pbo_prefix = _string(data["pbo_prefix"], "pbo_prefix")
    source = _json_object(data["source"], "source")
    thresholds = _json_object(data["thresholds"], "thresholds")
    raw_pieces = _json_array(data["pieces"], "pieces")
    required_properties = _string_mapping(
        data["required_properties"], "required_properties"
    )
    allowed_axis_parent_selections = _normalized_unique_string_tuple(
        data.get("allowed_axis_parent_selections", []),
        "allowed_axis_parent_selections",
    )
    raw_host_animation_overlaps = _json_array(
        data.get("allowed_host_animation_overlaps", []),
        "allowed_host_animation_overlaps",
    )
    allowed_host_animation_overlaps = []
    seen_host_animation_overlaps = set()
    semantic_fields = {
        "host_lod",
        "proxy_selection_name",
        "animated_selection",
    }
    for overlap_index, overlap_value in enumerate(raw_host_animation_overlaps):
        overlap_field = f"allowed_host_animation_overlaps[{overlap_index}]"
        overlap = _json_object(overlap_value, overlap_field)
        if set(overlap) != semantic_fields:
            raise ManifestError(
                f"{overlap_field} must contain exactly {sorted(semantic_fields)}"
            )
        parsed = AllowedHostAnimationOverlap(
            _finite_json_number(overlap["host_lod"], f"{overlap_field}.host_lod"),
            _normalized_nonempty_string(
                overlap["proxy_selection_name"],
                f"{overlap_field}.proxy_selection_name",
            ),
            _normalized_nonempty_string(
                overlap["animated_selection"],
                f"{overlap_field}.animated_selection",
            ),
        )
        triple = (
            parsed.host_lod,
            parsed.proxy_selection_name,
            parsed.animated_selection,
        )
        if triple in seen_host_animation_overlaps:
            raise ManifestError(
                "allowed_host_animation_overlaps contains a duplicate normalized triple"
            )
        seen_host_animation_overlaps.add(triple)
        allowed_host_animation_overlaps.append(parsed)
    matrix = _matrix(source["matrix"], "source.matrix", 4, 4)
    frame = _matrix(data["canonical_proxy_frame"], "canonical_proxy_frame", 3, 3)
    pieces = []
    for piece_index, raw_piece_value in enumerate(raw_pieces):
        piece_field = f"pieces[{piece_index}]"
        raw_piece = _json_object(raw_piece_value, piece_field)
        piece_name = _string(raw_piece["name"], f"{piece_field}.name")
        raw_variants = _json_array(raw_piece["variants"], f"{piece_field}.variants")
        variants = []
        seen = set()
        for variant_index, raw_variant_value in enumerate(raw_variants):
            variant_field = f"{piece_field}.variants[{variant_index}]"
            raw_variant = _json_object(raw_variant_value, variant_field)
            lod = _finite_json_number(
                raw_variant["host_lod"], f"{variant_field}.host_lod"
            )
            if lod in seen:
                raise ManifestError(f"duplicate host_lod {lod} in {piece_name}")
            seen.add(lod)
            repairs = _string_tuple(
                raw_variant.get("repairs", []), f"{variant_field}.repairs"
            )
            unknown = sorted(set(repairs) - _ALLOWED_REPAIRS)
            if unknown:
                raise ManifestError(f"unknown repairs: {unknown}")
            components = _string_tuple(
                raw_variant.get("allowed_fit_components", []),
                f"{variant_field}.allowed_fit_components",
            )
            unknown_components = sorted(set(components) - _ALLOWED_FIT_COMPONENTS)
            if unknown_components:
                raise ManifestError(f"unknown fit components: {unknown_components}")
            if components and "affine-fit" not in repairs:
                raise ManifestError("allowed_fit_components requires affine-fit repair")
            variants.append(
                VariantSpec(
                    lod,
                    _string(
                        raw_variant["expected_proxy_basename"],
                        f"{variant_field}.expected_proxy_basename",
                    ).lower(),
                    repairs,
                    components,
                )
            )
        include_direct = raw_piece["include_host_direct"]
        if type(include_direct) is not bool:
            raise ManifestError("pieces.include_host_direct must be a boolean")
        prefixes = tuple(
            value.upper()
            for value in _string_tuple(
                raw_piece.get("host_direct_material_prefixes", []),
                "pieces.host_direct_material_prefixes",
            )
        )
        exact = tuple(
            value.upper()
            for value in _string_tuple(
                raw_piece.get("host_direct_material_exact", []),
                "pieces.host_direct_material_exact",
            )
        )
        if include_direct and not prefixes and not exact:
            raise ManifestError(
                f"{piece_name} includes host-direct geometry but has no source material partition"
            )
        selections = tuple(
            value.lower()
            for value in _string_tuple(
                raw_piece.get("allowed_animated_selections", []),
                "pieces.allowed_animated_selections",
            )
        )
        pieces.append(
            PieceSpec(
                piece_name,
                _absolute(raw_piece["source_obj"], "source_obj"),
                _hash(raw_piece["source_sha256"], "source_sha256"),
                include_direct,
                prefixes,
                exact,
                selections,
                tuple(variants),
            )
        )
    raw_dependencies = _json_array(
        source.get("dependencies", []), "source.dependencies"
    )
    dependencies = []
    for dependency_index, dependency_value in enumerate(raw_dependencies):
        dependency_field = f"source.dependencies[{dependency_index}]"
        dependency = _json_object(dependency_value, dependency_field)
        dependencies.append(
            HashedPath(
                _absolute(dependency["path"], f"{dependency_field}.path"),
                _hash(dependency["sha256"], f"{dependency_field}.sha256"),
            )
        )
    return VehicleManifest(
        vehicle,
        _absolute(data["addon_root"], "addon_root"),
        _absolute(data["host_p3d"], "host_p3d"),
        _absolute(data["model_cfg"], "model_cfg"),
        _absolute(data["cfgconvert"], "cfgconvert"),
        _absolute(data["deployed_pbo"], "deployed_pbo"),
        pbo_prefix,
        _absolute(source["scene"], "source.scene"),
        _hash(source["scene_sha256"], "source.scene_sha256"),
        tuple(dependencies),
        matrix,
        frame,
        tuple(allowed_host_animation_overlaps),
        allowed_axis_parent_selections,
        required_properties,
        Thresholds(
            _finite_json_number(
                thresholds["translation_m"], "thresholds.translation_m"
            ),
            _finite_json_number(
                thresholds["rotation_deg"], "thresholds.rotation_deg"
            ),
            _finite_json_number(thresholds["scale_error"], "thresholds.scale_error"),
            _finite_json_number(thresholds["p95_m"], "thresholds.p95_m"),
        ),
        tuple(pieces),
    )


def load_manifest(path: Path) -> VehicleManifest:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        return _parse_manifest(data)
    except ManifestError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as error:
        raise ManifestError(f"invalid manifest schema: {error}") from error
