from pathlib import Path
import struct

from .binary import (
    BinaryReader,
    encode_fixed_cstring,
    require_finite,
    require_float32,
)
from .errors import AnimationFormatError


MDAT_SIGNATURE = b"RTM_MDAT"
ANIMATION_SIGNATURE = b"RTM_0101"
SUPPORTED_SIGNATURES = (MDAT_SIGNATURE, ANIMATION_SIGNATURE)


def read_rtm_bytes(data):
    reader = BinaryReader(data)
    signature_offset = reader.offset
    signature = reader.read(8)
    if signature not in SUPPORTED_SIGNATURES:
        raise AnimationFormatError(
            "RTM_FORMAT_UNSUPPORTED",
            "expected RTM_MDAT or RTM_0101",
            signature_offset,
        )

    mdat_present = signature == MDAT_SIGNATURE
    metadata = []
    if mdat_present:
        padding_offset = reader.offset
        if reader.read(4) != b"\0\0\0\0":
            raise AnimationFormatError(
                "RTM_MDAT_PADDING",
                "RTM_MDAT reserved bytes must be zero",
                padding_offset,
            )
        count = reader.u32()
        reader.require_count(count, 6, "RTM metadata")
        for _ in range(count):
            phase_offset = reader.offset
            phase = _finite_at(reader.f32(), "metadata phase", phase_offset)
            metadata.append({
                "name": _read_lascii(reader),
                "phase": phase,
                "value": _read_lascii(reader),
            })
        signature_offset = reader.offset
        signature = reader.read(8)
        if signature != ANIMATION_SIGNATURE:
            raise AnimationFormatError(
                "RTM_BLOCK_ORDER",
                "RTM_MDAT must be followed by exactly one RTM_0101 block",
                signature_offset,
            )

    motion_offset = reader.offset
    motion_disk = reader.unpack("3f")
    motion = [
        _finite_at(motion_disk[0], "motion x", motion_offset),
        _finite_at(motion_disk[2], "motion y", motion_offset + 8),
        _finite_at(motion_disk[1], "motion z", motion_offset + 4),
    ]
    frame_count_offset = reader.offset
    frame_count = reader.u32()
    bone_count_offset = reader.offset
    bone_count = reader.u32()
    if frame_count < 1 or bone_count < 1:
        raise AnimationFormatError(
            "ANIM_COUNT_INVALID",
            "RTM requires at least one frame and one bone",
            frame_count_offset if frame_count < 1 else bone_count_offset,
        )
    minimum_size = (
        bone_count * 32
        + frame_count * (4 + bone_count * (32 + 12 * 4))
    )
    if minimum_size > reader.remaining:
        raise AnimationFormatError(
            "ANIM_COUNT_INVALID",
            "RTM frame/bone counts cannot fit in remaining bytes",
            frame_count_offset,
        )

    bones = []
    bone_set = set()
    for _ in range(bone_count):
        name_offset = reader.offset
        name = reader.fixed_cstring(32)
        if not name or name in bone_set:
            raise AnimationFormatError(
                "RTM_BONE_NAME",
                "bone names must be non-empty and unique",
                name_offset,
            )
        bone_set.add(name)
        bones.append(name)

    frames = []
    for _ in range(frame_count):
        phase_offset = reader.offset
        phase = _finite_at(reader.f32(), "frame phase", phase_offset)
        transforms = []
        for expected_bone in bones:
            bone_offset = reader.offset
            bone = reader.fixed_cstring(32)
            if bone != expected_bone:
                raise AnimationFormatError(
                    "RTM_BONE_ORDER",
                    "transform bone %r does not match %r"
                    % (bone, expected_bone),
                    bone_offset,
                )
            values_offset = reader.offset
            values = reader.unpack("12f")
            for index, value in enumerate(values):
                _finite_at(
                    value,
                    "transform matrix component",
                    values_offset + index * 4,
                )
            transforms.append({
                "bone": bone,
                "matrix": [
                    [values[0], values[6], values[3], values[9]],
                    [values[2], values[8], values[5], values[11]],
                    [values[1], values[7], values[4], values[10]],
                    [0.0, 0.0, 0.0, 1.0],
                ],
            })
        frames.append({"phase": phase, "transforms": transforms})

    if reader.remaining:
        code = (
            "RTM_BLOCK_ORDER"
            if reader.peek(8) in SUPPORTED_SIGNATURES
            else "ANIM_TRAILING_BYTES"
        )
        raise AnimationFormatError(
            code,
            "%d bytes remain after RTM_0101" % reader.remaining,
            reader.offset,
        )
    return {
        "bones": bones,
        "format": "rtm",
        "frames": frames,
        "mdat_present": mdat_present,
        "metadata": metadata,
        "motion": motion,
        "version": "RTM_0101",
    }


def write_rtm_bytes(document):
    normalized = _validate_document(document)
    output = bytearray()
    if normalized["mdat_present"]:
        output.extend(MDAT_SIGNATURE)
        output.extend(struct.pack("<II", 0, len(normalized["metadata"])))
        for item in normalized["metadata"]:
            output.extend(struct.pack("<f", item["phase"]))
            output.extend(_encode_lascii(item["name"]))
            output.extend(_encode_lascii(item["value"]))

    motion = normalized["motion"]
    output.extend(ANIMATION_SIGNATURE)
    output.extend(struct.pack("<3f", motion[0], motion[2], motion[1]))
    output.extend(
        struct.pack(
            "<II", len(normalized["frames"]), len(normalized["bones"])
        )
    )
    for bone in normalized["bones"]:
        output.extend(encode_fixed_cstring(bone, 32))
    for frame in normalized["frames"]:
        output.extend(struct.pack("<f", frame["phase"]))
        for transform in frame["transforms"]:
            matrix = transform["matrix"]
            output.extend(encode_fixed_cstring(transform["bone"], 32))
            output.extend(
                struct.pack(
                    "<12f",
                    matrix[0][0],
                    matrix[2][0],
                    matrix[1][0],
                    matrix[0][2],
                    matrix[2][2],
                    matrix[1][2],
                    matrix[0][1],
                    matrix[2][1],
                    matrix[1][1],
                    matrix[0][3],
                    matrix[2][3],
                    matrix[1][3],
                )
            )
    return bytes(output)


def read_rtm(path):
    return read_rtm_bytes(Path(path).read_bytes())


def write_rtm(path, document):
    data = write_rtm_bytes(document)
    Path(path).write_bytes(data)
    return data


def _read_lascii(reader):
    start = reader.offset
    size = reader.u8()
    raw = reader.read(size)
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise AnimationFormatError(
            "ANIM_UTF8_INVALID",
            "length-prefixed string is not valid UTF-8",
            start,
        )


def _encode_lascii(value):
    if not isinstance(value, str):
        raise AnimationFormatError(
            "ANIM_STRING_INVALID",
            "length-prefixed string value must be str",
        )
    try:
        raw = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise AnimationFormatError(
            "ANIM_UTF8_INVALID",
            "string cannot be encoded as UTF-8",
        )
    if len(raw) > 0xFF:
        raise AnimationFormatError(
            "ANIM_STRING_TOO_LONG",
            "length-prefixed UTF-8 string exceeds 255 bytes",
        )
    return struct.pack("<B", len(raw)) + raw


def _finite_at(value, label, offset):
    try:
        return require_finite(value, label)
    except AnimationFormatError as error:
        raise AnimationFormatError(error.code, error.message, offset)


def _require_list(value, label):
    if not isinstance(value, list):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "%s must be a list" % label
        )
    return value


def _validate_matrix(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "matrix must contain four rows"
        )
    matrix = []
    for row in value:
        if not isinstance(row, (list, tuple)) or len(row) != 4:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "matrix rows must contain four components",
            )
        matrix.append([
            require_float32(component, "matrix component")
            for component in row
        ])
    expected_last_row = (0.0, 0.0, 0.0, 1.0)
    if any(
        abs(actual - expected) > 1e-12
        for actual, expected in zip(matrix[3], expected_last_row)
    ):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "matrix last row must be [0, 0, 0, 1]",
        )
    return matrix


def _validate_document(document):
    if not isinstance(document, dict):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "document must be an object"
        )
    required = {
        "bones", "format", "frames", "metadata", "motion", "version",
    }
    optional = {"mdat_present"}
    if not required.issubset(document) \
            or not set(document).issubset(required | optional):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "document fields must contain %s; optional fields are %s"
            % (sorted(required), sorted(optional)),
        )
    if document["format"] != "rtm" or document["version"] != "RTM_0101":
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "format/version must be rtm/RTM_0101",
        )

    motion_value = document["motion"]
    if not isinstance(motion_value, (list, tuple)) or len(motion_value) != 3:
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "motion must contain three components",
        )
    motion = [
        require_float32(component, "motion component")
        for component in motion_value
    ]

    bones_value = _require_list(document["bones"], "bones")
    if not 1 <= len(bones_value) <= 0xFFFFFFFF:
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "bones must contain 1..4294967295 names",
        )
    bones = []
    seen_bones = set()
    for name in bones_value:
        if not isinstance(name, str) or not name or name in seen_bones:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "bone names must be non-empty and unique",
            )
        encode_fixed_cstring(name, 32)
        seen_bones.add(name)
        bones.append(name)

    metadata_value = _require_list(document["metadata"], "metadata")
    if len(metadata_value) > 0xFFFFFFFF:
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "too many metadata items"
        )
    metadata = []
    for item in metadata_value:
        if not isinstance(item, dict) or set(item) != {
            "name", "phase", "value",
        }:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "metadata requires name, phase, and value",
            )
        _encode_lascii(item["name"])
        _encode_lascii(item["value"])
        metadata.append({
            "name": item["name"],
            "phase": require_float32(
                item["phase"], "metadata phase"
            ),
            "value": item["value"],
        })

    if "mdat_present" in document:
        mdat_present = document["mdat_present"]
        if not isinstance(mdat_present, bool):
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID", "mdat_present must be bool"
            )
        if not mdat_present and metadata:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "mdat_present cannot be false when metadata is not empty",
            )
    else:
        mdat_present = bool(metadata)

    frames_value = _require_list(document["frames"], "frames")
    if not 1 <= len(frames_value) <= 0xFFFFFFFF:
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "frames must contain 1..4294967295 entries",
        )
    frames = []
    for frame in frames_value:
        if not isinstance(frame, dict) or set(frame) != {
            "phase", "transforms",
        }:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "frames require phase and transforms",
            )
        transforms_value = _require_list(
            frame["transforms"], "frame transforms"
        )
        if len(transforms_value) != len(bones):
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "each frame requires one transform per bone",
            )
        transforms = []
        for index, transform in enumerate(transforms_value):
            if not isinstance(transform, dict) or set(transform) != {
                "bone", "matrix",
            }:
                raise AnimationFormatError(
                    "ANIM_DOCUMENT_INVALID",
                    "transforms require bone and matrix",
                )
            if transform["bone"] != bones[index]:
                raise AnimationFormatError(
                    "ANIM_DOCUMENT_INVALID",
                    "transform bones must match exact bone order and casing",
                )
            transforms.append({
                "bone": transform["bone"],
                "matrix": _validate_matrix(transform["matrix"]),
            })
        frames.append({
            "phase": require_float32(frame["phase"], "frame phase"),
            "transforms": transforms,
        })
    return {
        "bones": bones,
        "format": "rtm",
        "frames": frames,
        "mdat_present": mdat_present,
        "metadata": metadata,
        "motion": motion,
        "version": "RTM_0101",
    }
