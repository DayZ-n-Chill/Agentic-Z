import math
import struct

from .errors import AnimationFormatError


class BinaryReader:
    def __init__(self, data):
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("BinaryReader data must be bytes-like")
        self._data = bytes(data)
        self._offset = 0

    @property
    def offset(self):
        return self._offset

    @property
    def remaining(self):
        return len(self._data) - self._offset

    def read(self, size):
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError("read size must be a non-negative int")
        if size > self.remaining:
            raise AnimationFormatError(
                "ANIM_TRUNCATED",
                "need %d bytes, only %d remain" % (size, self.remaining),
                self._offset,
            )
        start = self._offset
        self._offset += size
        return self._data[start:self._offset]

    def peek(self, size):
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError("peek size must be a non-negative int")
        return self._data[self._offset:self._offset + size]

    def unpack(self, format_code):
        size = struct.calcsize("<" + format_code)
        return struct.unpack("<" + format_code, self.read(size))

    def u8(self):
        return self.unpack("B")[0]

    def u16(self):
        return self.unpack("H")[0]

    def u32(self):
        return self.unpack("I")[0]

    def i32(self):
        return self.unpack("i")[0]

    def f32(self):
        return self.unpack("f")[0]

    def f64(self):
        return self.unpack("d")[0]

    def require_count(self, count, minimum_item_size, label):
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise AnimationFormatError(
                "ANIM_COUNT_INVALID",
                "%s count must be a non-negative int" % label,
                self._offset,
            )
        if isinstance(minimum_item_size, bool) or \
                not isinstance(minimum_item_size, int) or \
                minimum_item_size <= 0:
            raise ValueError("minimum item size must be a positive int")
        if count > self.remaining // minimum_item_size:
            raise AnimationFormatError(
                "ANIM_COUNT_INVALID",
                "%s count %d cannot fit in %d remaining bytes"
                % (label, count, self.remaining),
                self._offset,
            )
        return count

    def cstring(self):
        start = self._offset
        end = self._data.find(b"\0", start)
        if end < 0:
            raise AnimationFormatError(
                "ANIM_STRING_UNTERMINATED",
                "NUL terminator not found",
                start,
            )
        raw = self._data[start:end]
        try:
            value = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise AnimationFormatError(
                "ANIM_UTF8_INVALID",
                "string is not valid UTF-8",
                start,
            )
        self._offset = end + 1
        return value

    def fixed_cstring(self, size):
        start = self._offset
        if size > self.remaining:
            return self.read(size)
        field = self._data[start:start + size]
        nul = field.find(b"\0")
        if nul < 0:
            raise AnimationFormatError(
                "ANIM_STRING_UNTERMINATED",
                "fixed string has no NUL terminator",
                start,
            )
        if any(field[nul + 1:]):
            raise AnimationFormatError(
                "ANIM_STRING_PADDING",
                "fixed string has non-zero bytes after NUL",
                start + nul + 1,
            )
        try:
            value = field[:nul].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise AnimationFormatError(
                "ANIM_UTF8_INVALID",
                "fixed string is not valid UTF-8",
                start,
            )
        self._offset += size
        return value


def encode_cstring(value):
    if not isinstance(value, str):
        raise AnimationFormatError(
            "ANIM_STRING_INVALID",
            "string value must be str",
        )
    if "\0" in value:
        raise AnimationFormatError(
            "ANIM_STRING_INVALID",
            "string value must not contain NUL",
        )
    try:
        return value.encode("utf-8", errors="strict") + b"\0"
    except UnicodeEncodeError:
        raise AnimationFormatError(
            "ANIM_UTF8_INVALID",
            "string cannot be encoded as UTF-8",
        )


def encode_fixed_cstring(value, size):
    raw = encode_cstring(value)
    if len(raw) > size:
        raise AnimationFormatError(
            "ANIM_STRING_TOO_LONG",
            "UTF-8 string needs %d bytes including NUL; field is %d"
            % (len(raw), size),
        )
    return raw + b"\0" * (size - len(raw))


def require_finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnimationFormatError(
            "ANIM_VALUE_INVALID",
            "%s must be a finite number" % label,
        )
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        raise AnimationFormatError(
            "ANIM_VALUE_INVALID",
            "%s must be a finite number" % label,
        )
    if not math.isfinite(result):
        raise AnimationFormatError(
            "ANIM_VALUE_INVALID",
            "%s must be a finite number" % label,
        )
    return result


def require_float32(value, label):
    result = require_finite(value, label)
    try:
        struct.pack("<f", result)
    except (OverflowError, struct.error):
        raise AnimationFormatError(
            "ANIM_VALUE_INVALID",
            "%s must fit a finite float32" % label,
        )
    return result
