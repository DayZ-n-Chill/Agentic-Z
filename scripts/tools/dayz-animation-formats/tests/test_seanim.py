import copy
import json
import math
import struct
from pathlib import Path

import pytest

from dayz_animation_formats.errors import AnimationFormatError
from dayz_animation_formats.seanim import (
    AnimType,
    read_seanim,
    read_seanim_bytes,
    write_seanim,
    write_seanim_bytes,
)


FIXTURES = Path(__file__).with_name("fixtures")


def _golden_document():
    return json.loads(
        (FIXTURES / "seanim-v1-full.json").read_text(encoding="utf-8")
    )


def _declared_empty_channel_bytes(presence_flags):
    payload = struct.pack(
        "<6BfII4BI",
        AnimType.RELATIVE,
        0,
        presence_flags,
        0,
        0,
        0,
        30.0,
        1,
        1,
        0,
        0,
        0,
        0,
        0,
    )
    return b"SEAnim" + struct.pack("<hH", 1, 28) + payload + b"b\0\0\0"


def test_reads_frozen_se2dev_fixture_as_hand_checked_document():
    """Rompe si el lector diverge del oracle SE2Dev en cualquier campo."""
    expected = _golden_document()
    actual = read_seanim(FIXTURES / "seanim-v1-full.seanim")
    assert actual == expected


def test_writer_reproduces_frozen_se2dev_bytes():
    """Rompe si orden, widths, flags o precisión dejan de ser compatibles."""
    expected = (FIXTURES / "seanim-v1-full.seanim").read_bytes()
    assert write_seanim_bytes(_golden_document()) == expected


@pytest.mark.parametrize(
    ("presence_flags", "channel"),
    [(1, "position_keys"), (2, "rotation_keys"), (4, "scale_keys")],
)
def test_declared_empty_bone_channel_roundtrip_preserves_exact_bytes(
    presence_flags, channel
):
    """Rompe si un canal declarado se elimina por contener cero claves."""
    original = _declared_empty_channel_bytes(presence_flags)

    document = read_seanim_bytes(original)

    assert write_seanim_bytes(document) == original
    assert document["presence_flags"] == presence_flags
    assert document["bones"][0][channel] == []


@pytest.mark.parametrize(
    ("presence_flag", "channel"),
    [(1, "position_keys"), (2, "rotation_keys"), (4, "scale_keys")],
)
def test_keys_in_undeclared_bone_channel_fail_closed(presence_flag, channel):
    """Rompe si claves no declaradas se emiten reparando flags en silencio."""
    document = _golden_document()
    document["presence_flags"] = 0x47 & ~presence_flag

    with pytest.raises(AnimationFormatError) as raised:
        write_seanim_bytes(document)

    assert raised.value.code == "ANIM_DOCUMENT_INVALID"
    assert "does not declare" in raised.value.message
    assert channel in raised.value.message


def test_manual_seanim_document_without_presence_flags_keeps_legacy_inference():
    """Rompe si el nuevo campo pasa a ser obligatorio para llamantes existentes."""
    document = _golden_document()
    document.pop("presence_flags", None)
    expected = (FIXTURES / "seanim-v1-full.seanim").read_bytes()

    assert write_seanim_bytes(document) == expected


@pytest.mark.parametrize(
    "fixture_path",
    sorted(FIXTURES.glob("*.seanim")),
    ids=lambda path: path.name,
)
def test_seanim_corpus_read_write_roundtrip_is_byte_exact(fixture_path):
    """Rompe si cualquier SEAnim del corpus se normaliza durante read→write."""
    original = fixture_path.read_bytes()

    assert write_seanim_bytes(read_seanim_bytes(original)) == original


@pytest.mark.parametrize("anim_type", list(range(4)))
@pytest.mark.parametrize(
    ("precision", "tolerance"),
    [("float32", 1e-6), ("float64", 1e-12)],
)
def test_all_types_and_precisions_roundtrip(anim_type, precision, tolerance):
    """Rompe si un tipo 0..3 o la precisión seleccionada se normaliza."""
    document = _golden_document()
    document["anim_type"] = anim_type
    document["precision"] = precision
    actual = read_seanim_bytes(write_seanim_bytes(document))
    assert actual["anim_type"] == anim_type
    assert actual["precision"] == precision
    for actual_bone, expected_bone in zip(actual["bones"], document["bones"]):
        for channel in ("position_keys", "rotation_keys", "scale_keys"):
            for got, want in zip(
                actual_bone[channel], expected_bone[channel]
            ):
                assert got["frame"] == want["frame"]
                assert got["value"] == pytest.approx(
                    want["value"], abs=tolerance
                )


def test_write_seanim_wrapper_defaults_to_relative_and_legacy_bone_keys(
    tmp_path,
):
    """Rompe si el wrapper conserva el antiguo default ABSOLUTE=0."""
    path = tmp_path / "default.seanim"
    write_seanim(
        path,
        [
            {
                "name": "Root",
                "pos_keys": [(0, (1.0, 2.0, 3.0))],
                "rot_keys": [(0, (0.0, 0.0, 0.0, 1.0))],
                "scale_keys": [],
            }
        ],
    )
    actual = read_seanim(path)
    assert actual["anim_type"] == AnimType.RELATIVE
    assert actual["frame_count"] == 1
    assert actual["bones"][0]["position_keys"] == [
        {"frame": 0, "value": [1.0, 2.0, 3.0]}
    ]


def test_write_seanim_missing_bone_key_frame_is_typed_error(tmp_path):
    """Rompe si el repro MEN-4 filtra TypeError desde una clave de hueso."""
    path = tmp_path / "missing-bone-frame.seanim"

    with pytest.raises(AnimationFormatError) as raised:
        write_seanim(
            path,
            bones=[{
                "name": "b",
                "position_keys": [{"value": [0, 0, 0]}],
            }],
        )

    assert raised.value.code == "ANIM_DOCUMENT_INVALID"
    assert "position_keys element 0 is missing frame" in raised.value.message


def test_write_seanim_missing_note_frame_is_typed_error(tmp_path):
    """Rompe si una nota sin frame filtra TypeError antes del validador."""
    path = tmp_path / "missing-note-frame.seanim"

    with pytest.raises(AnimationFormatError) as raised:
        write_seanim(path, bones=[], notes=[{"name": "event"}])

    assert raised.value.code == "ANIM_DOCUMENT_INVALID"
    assert "notes element 0 is missing frame" in raised.value.message


@pytest.mark.parametrize(
    ("mutate", "code", "offset"),
    [
        (lambda raw: raw.__setitem__(0, ord("X")), "SEANIM_MAGIC", 0),
        (
            lambda raw: raw.__setitem__(
                slice(6, 8), struct.pack("<h", 2)
            ),
            "SEANIM_VERSION",
            6,
        ),
        (
            lambda raw: raw.__setitem__(
                slice(8, 10), struct.pack("<H", 27)
            ),
            "SEANIM_HEADER_SIZE",
            8,
        ),
        (lambda raw: raw.__setitem__(10, 4), "SEANIM_ANIM_TYPE", 10),
        (lambda raw: raw.__setitem__(11, 2), "SEANIM_FLAG_UNSUPPORTED", 11),
        (
            lambda raw: raw.__setitem__(12, raw[12] | 0x80),
            "SEANIM_FLAG_UNSUPPORTED",
            12,
        ),
        (
            lambda raw: raw.__setitem__(13, raw[13] | 0x02),
            "SEANIM_FLAG_UNSUPPORTED",
            13,
        ),
        (
            lambda raw: raw.__setitem__(
                slice(16, 20), struct.pack("<f", math.nan)
            ),
            "ANIM_VALUE_INVALID",
            16,
        ),
        (lambda raw: raw.__setitem__(48, 2), "SEANIM_BONE_INDEX", 48),
        (lambda raw: raw.extend(b"X"), "ANIM_TRAILING_BYTES", 288),
    ],
)
def test_directed_header_index_and_trailing_mutations_fail_closed(
    mutate, code, offset
):
    """Rompe si corrupción conocida produce un documento parcial."""
    raw = bytearray((FIXTURES / "seanim-v1-full.seanim").read_bytes())
    mutate(raw)
    with pytest.raises(AnimationFormatError) as raised:
        read_seanim_bytes(bytes(raw))
    assert raised.value.code == code
    assert raised.value.offset == offset


@pytest.mark.parametrize("cut", [0, 7, 9, 35, 48, 51, 100, 287])
def test_every_truncated_region_fails_without_partial_document(cut):
    """Rompe si EOF actúa como NUL/cero y devuelve datos incompletos."""
    raw = (FIXTURES / "seanim-v1-full.seanim").read_bytes()[:cut]
    with pytest.raises(AnimationFormatError) as raised:
        read_seanim_bytes(raw)
    assert raised.value.code in {
        "ANIM_COUNT_INVALID",
        "ANIM_TRUNCATED",
        "ANIM_STRING_UNTERMINATED",
    }


def test_frame_outside_declared_range_is_rejected():
    """Rompe si un índice igual a frame_count se acepta."""
    raw = bytearray((FIXTURES / "seanim-v1-full.seanim").read_bytes())
    raw[77] = 11
    with pytest.raises(AnimationFormatError) as raised:
        read_seanim_bytes(bytes(raw))
    assert raised.value.code == "SEANIM_FRAME_INDEX"
    assert raised.value.offset == 77


@pytest.mark.parametrize(
    "mutation",
    [
        lambda doc: doc.__setitem__("framerate", math.inf),
        lambda doc: doc.__setitem__("anim_type", 4),
        lambda doc: doc["bones"].append(copy.deepcopy(doc["bones"][0])),
        lambda doc: doc["bones"][0]["position_keys"][0].__setitem__(
            "frame", -1
        ),
        lambda doc: doc["bones"][0].__setitem__("flags", 256),
    ],
)
def test_writer_rejects_invalid_document_before_returning_bytes(mutation):
    """Rompe si el writer emite un prefijo antes de validar todo."""
    document = _golden_document()
    mutation(document)
    with pytest.raises(AnimationFormatError):
        write_seanim_bytes(document)


def test_float32_writer_overflow_is_stable_format_error():
    """Rompe si struct.pack filtra OverflowError fuera del contrato público."""
    document = _golden_document()
    document["precision"] = "float32"
    document["bones"][0]["position_keys"][0]["value"][0] = 1e100
    with pytest.raises(AnimationFormatError) as raised:
        write_seanim_bytes(document)
    assert raised.value.code == "ANIM_VALUE_INVALID"
