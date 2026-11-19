import hashlib
import struct

from .errors import OdolStrictError


SUPPORTED_VERSIONS = (53, 54, 55)
MAX_LODS = 64


def preflight_odol_bytes(data):
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("ODOL input must be bytes-like")
    value = bytes(data)
    if value.startswith(b"ODOL"):
        _validate_direct_header(value)

    candidates = []
    count_error = None
    truncation_error = None
    search_from = 0
    while True:
        offset = value.find(b"ODOL", search_from)
        if offset < 0:
            break
        search_from = offset + 1
        remaining = len(value) - offset
        if remaining < 8:
            truncation_error = truncation_error or offset + 4
            continue
        version = struct.unpack_from("<I", value, offset + 4)[0]
        if version not in SUPPORTED_VERSIONS:
            continue
        if remaining < 12:
            truncation_error = truncation_error or offset + 8
            continue
        n_lods = struct.unpack_from("<i", value, offset + 8)[0]
        if not 1 <= n_lods <= MAX_LODS:
            count_error = count_error or offset + 8
            continue
        header_end = offset + 12 + 4 * n_lods
        if header_end > len(value):
            truncation_error = truncation_error or offset + 12
            continue
        resolutions = list(
            struct.unpack_from("<%df" % n_lods, value, offset + 12)
        )
        candidates.append((offset, version, n_lods, resolutions))

    if len(candidates) > 1:
        raise OdolStrictError(
            "ODOL_SIGNATURE_AMBIGUOUS",
            "more than one plausible supported ODOL signature exists",
        )
    if not candidates:
        if count_error is not None:
            raise OdolStrictError(
                "ODOL_LOD_COUNT_INVALID",
                "ODOL LOD count must be in 1..64",
                count_error,
            )
        if truncation_error is not None:
            raise OdolStrictError(
                "ODOL_HEADER_TRUNCATED",
                "ODOL header or resolution table is truncated",
                truncation_error,
            )
        raise OdolStrictError(
            "ODOL_SIGNATURE_MISSING",
            "no plausible supported ODOL signature exists",
        )

    offset, version, n_lods, resolutions = candidates[0]
    payload = value[offset:]
    return {
        "container_offset": offset,
        "input_sha256": hashlib.sha256(value).hexdigest(),
        "n_lods": n_lods,
        "payload": payload,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "resolutions": resolutions,
        "version": version,
    }


def _validate_direct_header(value):
    if len(value) < 8:
        raise OdolStrictError(
            "ODOL_HEADER_TRUNCATED",
            "ODOL version field is truncated",
            4,
        )
    version = struct.unpack_from("<I", value, 4)[0]
    if version not in SUPPORTED_VERSIONS:
        raise OdolStrictError(
            "ODOL_VERSION_UNSUPPORTED",
            "only ODOL versions 53, 54 and 55 are supported",
            4,
        )
    if len(value) < 12:
        raise OdolStrictError(
            "ODOL_HEADER_TRUNCATED",
            "ODOL LOD count field is truncated",
            8,
        )
    n_lods = struct.unpack_from("<i", value, 8)[0]
    if not 1 <= n_lods <= MAX_LODS:
        raise OdolStrictError(
            "ODOL_LOD_COUNT_INVALID",
            "ODOL LOD count must be in 1..64",
            8,
        )
    if 12 + 4 * n_lods > len(value):
        raise OdolStrictError(
            "ODOL_HEADER_TRUNCATED",
            "ODOL resolution table is truncated",
            12,
        )
