import math
import re

from .errors import OdolStrictError


TOP_FIELDS = {
    "backend_api_id",
    "backend_manifest_id",
    "backend_manifest_sha256",
    "container_offset",
    "input_sha256",
    "lod_count",
    "lods",
    "payload_sha256",
    "resolutions",
    "schema_version",
    "version",
}
LOD_FIELDS = {
    "actual_end",
    "declared_end",
    "declared_start",
    "face_count",
    "index",
    "material_count",
    "named_properties",
    "normal_count",
    "property_count",
    "proxy_count",
    "raw_sha256",
    "resolution",
    "selection_count",
    "selection_names",
    "vertex_count",
}


def diff_anatomy(reference, candidate):
    validate_summary(reference)
    validate_summary(candidate)
    findings = []
    _compare(reference, candidate, "", findings)
    findings.sort(key=lambda item: item["path"])
    return {
        "equal": not findings,
        "findings": findings,
        "schema_version": "dayz-odol-diff-v1",
    }


def validate_summary(value):
    if not isinstance(value, dict) or set(value) != TOP_FIELDS:
        _invalid()
    if value["schema_version"] != "dayz-odol-strict-v1" or \
            value["backend_api_id"] != \
            "odol_reader.ODOL.from_bytes-v1" or \
            value["version"] not in (53, 54, 55):
        _invalid()
    if not isinstance(value["backend_manifest_id"], str) or \
            not value["backend_manifest_id"]:
        _invalid()
    for field in (
        "backend_manifest_sha256", "input_sha256", "payload_sha256"
    ):
        if not _hash(value[field]):
            _invalid()
    if not _integer(value["container_offset"], 0) or \
            not _integer(value["lod_count"], 1, 64):
        _invalid()
    resolutions = value["resolutions"]
    if not isinstance(resolutions, list) or not resolutions or \
            not all(_number(item) for item in resolutions):
        _invalid()
    lods = value["lods"]
    if not isinstance(lods, list) or not lods:
        _invalid()
    for lod in lods:
        if not isinstance(lod, dict) or set(lod) != LOD_FIELDS:
            _invalid()
        if not _integer(lod["index"], 0) or \
                not _integer(lod["declared_start"], 0) or \
                not _integer(lod["declared_end"], 1) or \
                not _integer(lod["actual_end"], 1) or \
                lod["declared_start"] >= lod["declared_end"] or \
                lod["actual_end"] != lod["declared_end"]:
            _invalid()
        for field in (
            "face_count",
            "material_count",
            "normal_count",
            "property_count",
            "proxy_count",
            "selection_count",
            "vertex_count",
        ):
            if not _integer(lod[field], 0):
                _invalid()
        if not _number(lod["resolution"]) or \
                not _hash(lod["raw_sha256"]):
            _invalid()
        names = lod["selection_names"]
        if not isinstance(names, list) or \
                not all(isinstance(name, str) for name in names):
            _invalid()
        properties = lod["named_properties"]
        if not isinstance(properties, list):
            _invalid()
        for item in properties:
            if not isinstance(item, dict) or set(item) != {"name", "value"} \
                    or not isinstance(item["name"], str) \
                    or not isinstance(item["value"], str):
                _invalid()
    return value


def _compare(expected, observed, path, findings):
    if isinstance(expected, dict) and isinstance(observed, dict):
        for key in sorted(expected):
            _compare(
                expected[key],
                observed[key],
                path + "/" + _pointer_escape(key),
                findings,
            )
        return
    if isinstance(expected, list) and isinstance(observed, list):
        if len(expected) != len(observed):
            findings.append({
                "expected": len(expected),
                "observed": len(observed),
                "path": path,
            })
        for index in range(min(len(expected), len(observed))):
            _compare(
                expected[index],
                observed[index],
                path + "/" + str(index),
                findings,
            )
        return
    if expected != observed:
        findings.append({
            "expected": expected,
            "observed": observed,
            "path": path or "/",
        })


def _pointer_escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def _hash(value):
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


def _integer(value, minimum, maximum=None):
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= minimum
        and (maximum is None or value <= maximum)
    )


def _number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _invalid():
    raise OdolStrictError(
        "ODOL_SUMMARY_INVALID",
        "input does not match dayz-odol-strict-v1",
    )
