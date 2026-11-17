import hashlib
import struct

import pytest

from dayz_odol_strict.errors import OdolStrictError
from dayz_odol_strict.preflight import preflight_odol_bytes


def _odol(version=55, count=2, resolutions=(1.0, 2.0), tail=b"payload"):
    return (
        b"ODOL"
        + struct.pack("<Ii", version, count)
        + struct.pack("<%df" % len(resolutions), *resolutions)
        + tail
    )


@pytest.mark.parametrize("prefix_size", [0, 16, 4096])
def test_direct_and_prefixed_payloads_select_the_same_odol_slice(prefix_size):
    payload = _odol()
    data = b"X" * prefix_size + payload
    result = preflight_odol_bytes(data)
    assert result["container_offset"] == prefix_size
    assert result["version"] == 55
    assert result["n_lods"] == 2
    assert result["resolutions"] == [1.0, 2.0]
    assert result["payload"] == payload
    assert result["payload_sha256"] == hashlib.sha256(payload).hexdigest()
    assert result["input_sha256"] == hashlib.sha256(data).hexdigest()


def test_supported_signature_inside_arbitrary_prefix_is_a_container():
    payload = _odol(version=53, count=1, resolutions=(123.0,))
    result = preflight_odol_bytes(b"arbitrary\0bytes" + payload)
    assert result["container_offset"] == len(b"arbitrary\0bytes")
    assert result["version"] == 53


def test_missing_and_multiple_plausible_signatures_fail_closed():
    with pytest.raises(OdolStrictError) as missing:
        preflight_odol_bytes(b"no signature here")
    assert missing.value.code == "ODOL_SIGNATURE_MISSING"

    first = _odol(count=1, resolutions=(1.0,))
    second = _odol(version=54, count=1, resolutions=(2.0,))
    with pytest.raises(OdolStrictError) as ambiguous:
        preflight_odol_bytes(first + b"prefix" + second)
    assert ambiguous.value.code == "ODOL_SIGNATURE_AMBIGUOUS"


@pytest.mark.parametrize("version", [0, 52, 56, 73])
def test_direct_unsupported_version_has_specific_error(version):
    with pytest.raises(OdolStrictError) as raised:
        preflight_odol_bytes(
            _odol(version=version, count=1, resolutions=(1.0,))
        )
    assert raised.value.code == "ODOL_VERSION_UNSUPPORTED"
    assert raised.value.offset == 4


def test_embedded_unsupported_header_does_not_become_a_candidate():
    with pytest.raises(OdolStrictError) as raised:
        preflight_odol_bytes(
            b"prefix" + _odol(version=52, count=1, resolutions=(1.0,))
        )
    assert raised.value.code == "ODOL_SIGNATURE_MISSING"


@pytest.mark.parametrize("count", [0, -1, -2147483648, 65])
def test_signed_lod_count_guard_runs_before_resolution_iteration(count):
    with pytest.raises(OdolStrictError) as raised:
        preflight_odol_bytes(_odol(count=count, resolutions=()))
    assert raised.value.code == "ODOL_LOD_COUNT_INVALID"
    assert raised.value.offset == 8


@pytest.mark.parametrize(
    "data",
    [
        b"ODOL",
        b"ODOL" + struct.pack("<I", 55),
        b"ODOL" + struct.pack("<Ii", 55, 2) + struct.pack("<f", 1.0),
    ],
)
def test_direct_header_or_resolution_table_truncation_is_specific(data):
    with pytest.raises(OdolStrictError) as raised:
        preflight_odol_bytes(data)
    assert raised.value.code == "ODOL_HEADER_TRUNCATED"


def test_embedded_supported_truncated_table_is_header_truncated():
    data = (
        b"prefix"
        + b"ODOL"
        + struct.pack("<Ii", 54, 2)
        + struct.pack("<f", 1.0)
    )
    with pytest.raises(OdolStrictError) as raised:
        preflight_odol_bytes(data)
    assert raised.value.code == "ODOL_HEADER_TRUNCATED"
    assert raised.value.offset == len(b"prefix") + 12
