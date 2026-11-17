import hashlib
import math
from pathlib import Path
import tempfile

from .errors import OdolStrictError
from .manifest import verify_backend_manifest
from .preflight import preflight_odol_bytes
from .worker import invoke_worker


DEFAULT_BACKEND_MANIFEST = (
    Path(__file__).parents[1] / "backend" / "manifest-v1.json"
)
WORKER_FIELDS = {
    "lod_actual_end",
    "lod_end_table",
    "lod_errors",
    "lod_start_table",
    "lods",
    "n_lods",
    "resolutions",
    "version",
}
LOD_FIELDS = {
    "face_count",
    "material_count",
    "material_names",
    "named_properties",
    "normal_count",
    "proxy_count",
    "resolution",
    "selection_names",
    "vertex_count",
}


def build_strict_summary(preflight, worker_result, backend_identity):
    expected_count = preflight["n_lods"]
    if not isinstance(worker_result, dict) or \
            set(worker_result) != WORKER_FIELDS:
        _partial("backend result fields are incomplete")
    if worker_result["version"] != preflight["version"] or \
            worker_result["n_lods"] != expected_count:
        _partial("backend header does not match preflight")
    if worker_result["lod_errors"] != {}:
        _partial("backend reported one or more LOD errors")

    list_fields = (
        "resolutions",
        "lod_start_table",
        "lod_end_table",
        "lod_actual_end",
        "lods",
    )
    for field in list_fields:
        value = worker_result[field]
        if not isinstance(value, list) or len(value) != expected_count:
            _partial("backend %s length does not match LOD count" % field)
    resolutions = worker_result["resolutions"]
    if len(preflight["resolutions"]) != expected_count:
        _partial("preflight resolution table length is inconsistent")
    for index, (actual, expected) in enumerate(
        zip(resolutions, preflight["resolutions"])
    ):
        if not _finite_number(actual) or float(actual) != float(expected):
            _partial("backend resolution %d does not match preflight" % index)
    if any(lod is None for lod in worker_result["lods"]):
        _partial("backend returned a missing LOD")

    payload = preflight["payload"]
    payload_size = len(payload)
    intervals = []
    for index, (start, end, actual_end) in enumerate(
        zip(
            worker_result["lod_start_table"],
            worker_result["lod_end_table"],
            worker_result["lod_actual_end"],
        )
    ):
        if not all(_nonnegative_int(value) for value in (
            start, end, actual_end
        )) or not 0 <= start < end <= payload_size:
            raise OdolStrictError(
                "ODOL_BOUNDARY_OOB",
                "LOD %d interval is outside the sliced payload" % index,
            )
        if actual_end != end:
            raise OdolStrictError(
                "ODOL_BOUNDARY_INEXACT",
                "LOD %d actual end does not equal declared end" % index,
            )
        intervals.append((start, end, index))
    ordered_intervals = sorted(intervals)
    for previous, current in zip(
        ordered_intervals, ordered_intervals[1:]
    ):
        if current[0] < previous[1]:
            raise OdolStrictError(
                "ODOL_BOUNDARY_OVERLAP",
                "declared LOD intervals overlap",
            )

    lod_summaries = []
    for index, lod in enumerate(worker_result["lods"]):
        if not isinstance(lod, dict) or set(lod) != LOD_FIELDS:
            _partial("LOD %d anatomy fields are incomplete" % index)
        if not _finite_number(lod["resolution"]) or \
                float(lod["resolution"]) != float(resolutions[index]):
            _partial("LOD %d anatomy resolution does not match" % index)
        counts = {}
        for field in (
            "vertex_count",
            "face_count",
            "normal_count",
            "material_count",
            "proxy_count",
        ):
            if not _nonnegative_int(lod[field]):
                _partial("LOD %d %s is invalid" % (index, field))
            counts[field] = lod[field]
        material_names = lod["material_names"]
        if not _string_list(material_names) or \
                counts["material_count"] != len(material_names):
            _partial("LOD %d material anatomy is inconsistent" % index)
        selection_names = lod["selection_names"]
        if not _string_list(selection_names):
            _partial("LOD %d selection names are invalid" % index)
        properties_value = lod["named_properties"]
        if not isinstance(properties_value, list):
            _partial("LOD %d named properties are invalid" % index)
        named_properties = []
        for item in properties_value:
            if not isinstance(item, list) or len(item) != 2 or \
                    not all(isinstance(component, str) for component in item):
                _partial("LOD %d named property is invalid" % index)
            named_properties.append({"name": item[0], "value": item[1]})
        named_properties.sort(
            key=lambda item: (item["name"], item["value"])
        )
        start = worker_result["lod_start_table"][index]
        end = worker_result["lod_end_table"][index]
        lod_summaries.append({
            "actual_end": worker_result["lod_actual_end"][index],
            "declared_end": end,
            "declared_start": start,
            "face_count": counts["face_count"],
            "index": index,
            "material_count": counts["material_count"],
            "named_properties": named_properties,
            "normal_count": counts["normal_count"],
            "property_count": len(named_properties),
            "proxy_count": counts["proxy_count"],
            "raw_sha256": hashlib.sha256(payload[start:end]).hexdigest(),
            "resolution": float(lod["resolution"]),
            "selection_count": len(selection_names),
            "selection_names": sorted(selection_names),
            "vertex_count": counts["vertex_count"],
        })

    return {
        "backend_api_id": backend_identity["api_id"],
        "backend_manifest_id": backend_identity["manifest_id"],
        "backend_manifest_sha256": backend_identity["manifest_sha256"],
        "container_offset": preflight["container_offset"],
        "input_sha256": preflight["input_sha256"],
        "lod_count": expected_count,
        "lods": lod_summaries,
        "payload_sha256": preflight["payload_sha256"],
        "resolutions": [float(value) for value in resolutions],
        "schema_version": "dayz-odol-strict-v1",
        "version": preflight["version"],
    }


def inspect_odol(path, backend_root, backend_manifest=None):
    try:
        input_bytes = Path(path).read_bytes()
    except OSError:
        raise OdolStrictError(
            "ODOL_SIGNATURE_MISSING", "input file cannot be read"
        )
    preflight = preflight_odol_bytes(input_bytes)
    manifest_path = (
        DEFAULT_BACKEND_MANIFEST
        if backend_manifest is None
        else Path(backend_manifest)
    )
    backend = verify_backend_manifest(backend_root, manifest_path)
    try:
        with tempfile.TemporaryDirectory(
            prefix="dayz-odol-strict-"
        ) as directory:
            payload_path = Path(directory) / "payload.p3d"
            payload_path.write_bytes(preflight["payload"])
            worker_result = invoke_worker(payload_path, backend)
    except OSError:
        raise OdolStrictError(
            "ODOL_BACKEND_FAILURE",
            "temporary backend payload staging failed",
        )
    return build_strict_summary(preflight, worker_result, backend)


def _partial(message):
    raise OdolStrictError("ODOL_PARTIAL_RESULT", message)


def _nonnegative_int(value):
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    )


def _finite_number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _string_list(value):
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
