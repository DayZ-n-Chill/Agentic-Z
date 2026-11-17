import math
import struct

import pytest

from dayz_animation_formats.binary import (
    BinaryReader,
    encode_cstring,
    encode_fixed_cstring,
    require_finite,
)
from dayz_animation_formats.errors import AnimationFormatError


def test_reader_tracks_offsets_and_little_endian_values():
    """Breaks if a later error reports a wrong offset or endianness."""
    reader = BinaryReader(struct.pack("<BHIf", 7, 513, 70000, 1.25))
    assert reader.offset == 0
    assert reader.u8() == 7
    assert reader.offset == 1
    assert reader.u16() == 513
    assert reader.u32() == 70000
    assert reader.f32() == pytest.approx(1.25)
    assert reader.remaining == 0


def test_short_read_fails_at_first_missing_field_offset():
    """Breaks if a truncated read returns partial bytes."""
    reader = BinaryReader(b"\x01\x02")
    with pytest.raises(AnimationFormatError) as raised:
        reader.u32()
    assert raised.value.code == "ANIM_TRUNCATED"
    assert raised.value.offset == 0
    assert reader.offset == 0


def test_count_is_rejected_before_iteration_or_allocation():
    """Breaks if count*item_size can exceed the remaining bytes."""
    reader = BinaryReader(b"\0" * 8)
    with pytest.raises(AnimationFormatError) as raised:
        reader.require_count(3, 4, "frames")
    assert raised.value.code == "ANIM_COUNT_INVALID"
    assert raised.value.offset == 0
    assert reader.offset == 0


def test_cstring_requires_nul_and_strict_utf8():
    """Breaks if a corrupt string is accepted with silent replacement."""
    with pytest.raises(AnimationFormatError) as missing:
        BinaryReader(b"abc").cstring()
    assert missing.value.code == "ANIM_STRING_UNTERMINATED"
    assert missing.value.offset == 0

    with pytest.raises(AnimationFormatError) as invalid:
        BinaryReader(b"\xff\0").cstring()
    assert invalid.value.code == "ANIM_UTF8_INVALID"
    assert invalid.value.offset == 0


def test_fixed_cstring_requires_nul_zero_padding_and_byte_bound():
    """Breaks if RTM truncates names or hides bytes after the NUL."""
    assert BinaryReader(b"Pelvis\0\0").fixed_cstring(8) == "Pelvis"
    with pytest.raises(AnimationFormatError) as missing:
        BinaryReader(b"12345678").fixed_cstring(8)
    assert missing.value.code == "ANIM_STRING_UNTERMINATED"
    with pytest.raises(AnimationFormatError) as padding:
        BinaryReader(b"A\0X\0").fixed_cstring(4)
    assert padding.value.code == "ANIM_STRING_PADDING"
    with pytest.raises(AnimationFormatError) as too_long:
        encode_fixed_cstring("é" * 16, 32)
    assert too_long.value.code == "ANIM_STRING_TOO_LONG"


def test_string_writers_reject_nul_and_emit_exact_utf8():
    """Breaks if an embedded NUL alters the format boundaries."""
    assert encode_cstring("arma") == b"arma\0"
    assert encode_fixed_cstring("A", 4) == b"A\0\0\0"
    with pytest.raises(AnimationFormatError) as raised:
        encode_cstring("a\0b")
    assert raised.value.code == "ANIM_STRING_INVALID"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_require_finite_rejects_non_finite_scalar(value):
    """Breaks if NaN/Inf enters serialized keys or matrices."""
    with pytest.raises(AnimationFormatError) as raised:
        require_finite(value, "phase")
    assert raised.value.code == "ANIM_VALUE_INVALID"


@pytest.mark.parametrize("value", [True, "1.0", object()])
def test_require_finite_rejects_non_json_number_types(value):
    """Breaks if bool/text is silently normalized to float."""
    with pytest.raises(AnimationFormatError) as raised:
        require_finite(value, "phase")
    assert raised.value.code == "ANIM_VALUE_INVALID"
