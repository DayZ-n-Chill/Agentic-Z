import json
import math
from pathlib import Path

import pytest

from dayz_animation_formats.errors import AnimationFormatError
from dayz_animation_formats.rtm import read_rtm_bytes, write_rtm_bytes


FIXTURES = Path(__file__).with_name("fixtures")


def _fixture_bytes():
    return (FIXTURES / "rtm-0101-mdat.rtm").read_bytes()


def _golden_document():
    return json.loads(
        (FIXTURES / "rtm-0101-mdat.json").read_text(encoding="utf-8")
    )


def test_reads_frozen_a3ob_fixture_as_hand_checked_document():
    """Breaks if axes, blocks, casing or matrices diverge from A3OB."""
    assert read_rtm_bytes(_fixture_bytes()) == _golden_document()


def test_writer_reproduces_frozen_a3ob_bytes():
    """Breaks if the RTM component order stops being compatible."""
    assert write_rtm_bytes(_golden_document()) == _fixture_bytes()


def test_rtm_semantic_roundtrip_preserves_mdat_and_transforms():
    """Breaks if the writer loses metadata or a row of the public matrix."""
    expected = _golden_document()
    assert read_rtm_bytes(write_rtm_bytes(expected)) == expected


def test_empty_mdat_container_roundtrip_preserves_exact_bytes():
    """Breaks if an observed RTM_MDAT is dropped for having zero entries."""
    raw = _fixture_bytes()
    animation = raw[raw.index(b"RTM_0101"):]
    original = b"RTM_MDAT" + b"\0" * 8 + animation

    document = read_rtm_bytes(original)

    assert write_rtm_bytes(document) == original
    assert document["mdat_present"] is True
    assert document["metadata"] == []


def test_animation_without_mdat_roundtrip_preserves_exact_bytes():
    """Breaks if the reader invents an RTM_MDAT that was not declared."""
    raw = _fixture_bytes()
    original = raw[raw.index(b"RTM_0101"):]

    document = read_rtm_bytes(original)

    assert write_rtm_bytes(document) == original
    assert document["mdat_present"] is False


def test_explicit_mdat_absence_with_metadata_is_rejected():
    """Breaks if the writer repairs a contradiction by silently emitting MDAT."""
    document = _golden_document()
    document["mdat_present"] = False

    with pytest.raises(AnimationFormatError) as raised:
        write_rtm_bytes(document)

    assert raised.value.code == "ANIM_DOCUMENT_INVALID"
    assert "mdat_present cannot be false" in raised.value.message


def test_manual_rtm_document_without_mdat_field_keeps_legacy_inference():
    """Breaks if the absent field stops inferring MDAT from metadata."""
    document = _golden_document()
    document.pop("mdat_present", None)

    assert write_rtm_bytes(document) == _fixture_bytes()

    document["metadata"] = []
    raw = _fixture_bytes()
    animation = raw[raw.index(b"RTM_0101"):]
    assert write_rtm_bytes(document) == animation


@pytest.mark.parametrize(
    "fixture_path", sorted(FIXTURES.glob("*.rtm")), ids=lambda path: path.name
)
def test_rtm_corpus_read_write_roundtrip_is_byte_exact(fixture_path):
    """Breaks if any RTM in the corpus is normalized during read→write."""
    original = fixture_path.read_bytes()

    assert write_rtm_bytes(read_rtm_bytes(original)) == original


@pytest.mark.parametrize(
    ("data", "code", "offset"),
    [
        (b"BMTR" + b"\0" * 20, "RTM_FORMAT_UNSUPPORTED", 0),
        (b"UNKNOWN!" + b"\0" * 20, "RTM_FORMAT_UNSUPPORTED", 0),
        (_fixture_bytes() + b"RTM_0101", "RTM_BLOCK_ORDER", 258),
        (_fixture_bytes() + b"X", "ANIM_TRAILING_BYTES", 258),
    ],
)
def test_unsupported_duplicate_and_trailing_blocks_fail_closed(
    data, code, offset
):
    """Breaks if RTM falls back to best-effort or ignores a trailing block."""
    with pytest.raises(AnimationFormatError) as raised:
        read_rtm_bytes(data)
    assert raised.value.code == code
    assert raised.value.offset == offset


def test_mdat_after_animation_is_rejected_as_out_of_order():
    """Breaks if the parser accepts RTM_0101 followed by RTM_MDAT."""
    raw = _fixture_bytes()
    animation_offset = raw.index(b"RTM_0101")
    reordered = raw[animation_offset:] + raw[:animation_offset]
    with pytest.raises(AnimationFormatError) as raised:
        read_rtm_bytes(reordered)
    assert raised.value.code == "RTM_BLOCK_ORDER"


@pytest.mark.parametrize("cut", [0, 7, 15, 31, 60, 120, 257])
def test_truncated_rtm_never_returns_partial_frames(cut):
    """Breaks if an incomplete frame/transform is padded with zeros."""
    with pytest.raises(AnimationFormatError) as raised:
        read_rtm_bytes(_fixture_bytes()[:cut])
    assert raised.value.code in {
        "ANIM_COUNT_INVALID",
        "ANIM_TRUNCATED",
        "ANIM_STRING_UNTERMINATED",
        "RTM_FORMAT_UNSUPPORTED",
    }


def test_fixed_bone_field_without_nul_is_rejected():
    """Breaks if a 32-byte name is silently truncated."""
    raw = bytearray(_fixture_bytes())
    animation_offset = raw.index(b"RTM_0101")
    bone_field = animation_offset + 28
    raw[bone_field:bone_field + 32] = b"A" * 32
    with pytest.raises(AnimationFormatError) as raised:
        read_rtm_bytes(bytes(raw))
    assert raised.value.code == "ANIM_STRING_UNTERMINATED"
    assert raised.value.offset == bone_field


@pytest.mark.parametrize(
    "mutation",
    [
        lambda doc: doc.__setitem__("motion", [math.nan, 0.0, 0.0]),
        lambda doc: doc.__setitem__("bones", ["Pelvis", "Pelvis"]),
        lambda doc: doc.__setitem__("bones", ["é" * 16]),
        lambda doc: doc["frames"][0].__setitem__("transforms", []),
        lambda doc: doc["frames"][0]["transforms"][0].__setitem__(
            "bone", "pelvis"
        ),
        lambda doc: doc["frames"][0]["transforms"][0]["matrix"][0].__setitem__(
            0, math.inf
        ),
        lambda doc: doc["frames"][0]["transforms"][0]["matrix"].__setitem__(
            3, [0.0, 0.0, 1.0, 1.0]
        ),
        lambda doc: doc.__setitem__("version", "BMTR"),
    ],
)
def test_rtm_writer_validates_complete_document_before_emission(mutation):
    """Breaks if the writer accepts an ambiguous or structurally incoherent RTM."""
    document = _golden_document()
    mutation(document)
    with pytest.raises(AnimationFormatError):
        write_rtm_bytes(document)


def test_rtm_float32_overflow_is_stable_format_error():
    """Breaks if struct.pack leaks OverflowError outside the public contract."""
    document = _golden_document()
    document["motion"][0] = 1e100
    with pytest.raises(AnimationFormatError) as raised:
        write_rtm_bytes(document)
    assert raised.value.code == "ANIM_VALUE_INVALID"
