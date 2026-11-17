from enum import IntEnum
from pathlib import Path
import struct

from .binary import (
    BinaryReader,
    encode_cstring,
    require_finite,
    require_float32,
)
from .errors import AnimationFormatError


MAGIC = b"SEAnim"
VERSION = 1
HEADER_SIZE = 28

PRESENCE_POSITION = 1 << 0
PRESENCE_ROTATION = 1 << 1
PRESENCE_SCALE = 1 << 2
PRESENCE_NOTE = 1 << 6
SUPPORTED_PRESENCE = (
    PRESENCE_POSITION
    | PRESENCE_ROTATION
    | PRESENCE_SCALE
    | PRESENCE_NOTE
)
PROPERTY_HIGH_PRECISION = 1 << 0
FLAG_LOOPED = 1 << 0


class AnimType(IntEnum):
    ABSOLUTE = 0
    ADDITIVE = 1
    RELATIVE = 2
    DELTA = 3


def read_seanim_bytes(data):
    reader = BinaryReader(data)
    if reader.read(6) != MAGIC:
        raise AnimationFormatError(
            "SEANIM_MAGIC", "expected SEAnim magic", 0
        )
    version_offset = reader.offset
    version = reader.unpack("h")[0]
    if version != VERSION:
        raise AnimationFormatError(
            "SEANIM_VERSION",
            "unsupported SEAnim version %d" % version,
            version_offset,
        )
    header_offset = reader.offset
    header_size = reader.u16()
    if header_size != HEADER_SIZE:
        raise AnimationFormatError(
            "SEANIM_HEADER_SIZE",
            "header size must be %d" % HEADER_SIZE,
            header_offset,
        )

    anim_type_offset = reader.offset
    anim_type = reader.u8()
    if anim_type not in range(4):
        raise AnimationFormatError(
            "SEANIM_ANIM_TYPE",
            "animation type must be 0..3",
            anim_type_offset,
        )
    anim_flags_offset = reader.offset
    anim_flags = reader.u8()
    if anim_flags & ~FLAG_LOOPED:
        raise AnimationFormatError(
            "SEANIM_FLAG_UNSUPPORTED",
            "unsupported animation flags 0x%02x" % anim_flags,
            anim_flags_offset,
        )
    presence_offset = reader.offset
    presence = reader.u8()
    if presence & ~SUPPORTED_PRESENCE:
        raise AnimationFormatError(
            "SEANIM_FLAG_UNSUPPORTED",
            "unsupported presence flags 0x%02x" % presence,
            presence_offset,
        )
    property_offset = reader.offset
    property_flags = reader.u8()
    if property_flags & ~PROPERTY_HIGH_PRECISION:
        raise AnimationFormatError(
            "SEANIM_FLAG_UNSUPPORTED",
            "unsupported property flags 0x%02x" % property_flags,
            property_offset,
        )
    reserved_offset = reader.offset
    if reader.read(2) != b"\0\0":
        raise AnimationFormatError(
            "SEANIM_RESERVED",
            "reserved header bytes must be zero",
            reserved_offset,
        )
    framerate_offset = reader.offset
    framerate = _finite_at(reader.f32(), "framerate", framerate_offset)
    if framerate <= 0.0:
        raise AnimationFormatError(
            "ANIM_VALUE_INVALID",
            "framerate must be greater than zero",
            framerate_offset,
        )
    frame_count_offset = reader.offset
    frame_count = reader.u32()
    if frame_count < 1:
        raise AnimationFormatError(
            "SEANIM_FRAME_COUNT",
            "frame count must be at least 1",
            frame_count_offset,
        )
    bone_count = reader.u32()
    modifier_count_offset = reader.offset
    modifier_count = reader.u8()
    reserved_offset = reader.offset
    if reader.read(3) != b"\0\0\0":
        raise AnimationFormatError(
            "SEANIM_RESERVED",
            "reserved header bytes must be zero",
            reserved_offset,
        )
    note_count = reader.u32()

    if modifier_count > bone_count:
        raise AnimationFormatError(
            "ANIM_COUNT_INVALID",
            "modifier count exceeds bone count",
            modifier_count_offset,
        )
    if (presence & (PRESENCE_POSITION | PRESENCE_ROTATION | PRESENCE_SCALE)) \
            and bone_count == 0:
        raise AnimationFormatError(
            "ANIM_COUNT_INVALID",
            "bone channel flags require at least one bone",
            presence_offset,
        )
    if bool(presence & PRESENCE_NOTE) != bool(note_count):
        raise AnimationFormatError(
            "ANIM_COUNT_INVALID",
            "note flag and note count disagree",
            presence_offset,
        )

    reader.require_count(bone_count, 1, "bones")
    names = []
    for _ in range(bone_count):
        name_offset = reader.offset
        name = reader.cstring()
        if not name or name in names:
            raise AnimationFormatError(
                "SEANIM_BONE_NAME",
                "bone names must be non-empty and unique",
                name_offset,
            )
        names.append(name)

    bone_format, bone_size = _index_format(bone_count)
    reader.require_count(modifier_count, bone_size + 1, "modifiers")
    modifiers = {}
    for _ in range(modifier_count):
        index_offset = reader.offset
        bone_index = reader.unpack(bone_format)[0]
        modifier = reader.u8()
        if bone_index >= bone_count or bone_index in modifiers:
            raise AnimationFormatError(
                "SEANIM_BONE_INDEX",
                "modifier bone index is invalid or duplicated",
                index_offset,
            )
        modifiers[bone_index] = modifier

    frame_format, frame_size = _index_format(frame_count)
    precision = (
        "float64"
        if property_flags & PROPERTY_HIGH_PRECISION
        else "float32"
    )
    scalar_format = "d" if precision == "float64" else "f"
    scalar_size = 8 if precision == "float64" else 4
    channels = (
        ("position_keys", PRESENCE_POSITION, 3),
        ("rotation_keys", PRESENCE_ROTATION, 4),
        ("scale_keys", PRESENCE_SCALE, 3),
    )
    bones = []
    for bone_index, name in enumerate(names):
        flags = reader.u8()
        bone = {
            "flags": flags,
            "modifier": modifiers.get(bone_index),
            "name": name,
            "position_keys": [],
            "rotation_keys": [],
            "scale_keys": [],
        }
        for key_name, presence_flag, components in channels:
            if not presence & presence_flag:
                continue
            key_count = reader.unpack(frame_format)[0]
            record_size = frame_size + components * scalar_size
            reader.require_count(key_count, record_size, key_name)
            for _ in range(key_count):
                frame_offset = reader.offset
                frame = reader.unpack(frame_format)[0]
                if frame >= frame_count:
                    raise AnimationFormatError(
                        "SEANIM_FRAME_INDEX",
                        "key frame %d is outside frame_count %d"
                        % (frame, frame_count),
                        frame_offset,
                    )
                values = []
                for component in range(components):
                    value_offset = reader.offset
                    value = reader.unpack(scalar_format)[0]
                    values.append(
                        _finite_at(
                            value,
                            "%s component %d" % (key_name, component),
                            value_offset,
                        )
                    )
                bone[key_name].append({"frame": frame, "value": values})
        bones.append(bone)

    notes = []
    if presence & PRESENCE_NOTE:
        reader.require_count(note_count, frame_size + 1, "notes")
        for _ in range(note_count):
            frame_offset = reader.offset
            frame = reader.unpack(frame_format)[0]
            if frame >= frame_count:
                raise AnimationFormatError(
                    "SEANIM_FRAME_INDEX",
                    "note frame %d is outside frame_count %d"
                    % (frame, frame_count),
                    frame_offset,
                )
            notes.append({"frame": frame, "name": reader.cstring()})

    if reader.remaining:
        raise AnimationFormatError(
            "ANIM_TRAILING_BYTES",
            "%d trailing bytes" % reader.remaining,
            reader.offset,
        )
    return {
        "anim_type": anim_type,
        "bones": bones,
        "format": "seanim",
        "frame_count": frame_count,
        "framerate": framerate,
        "looped": bool(anim_flags & FLAG_LOOPED),
        "notes": notes,
        "presence_flags": presence,
        "precision": precision,
        "version": VERSION,
    }


def write_seanim_bytes(document):
    normalized = _validate_document(document)
    bones = normalized["bones"]
    notes = normalized["notes"]
    frame_count = normalized["frame_count"]
    frame_format, _ = _index_format(frame_count)
    bone_format, _ = _index_format(len(bones))
    scalar_format = "d" if normalized["precision"] == "float64" else "f"

    presence = normalized["presence_flags"]
    property_flags = (
        PROPERTY_HIGH_PRECISION
        if normalized["precision"] == "float64"
        else 0
    )
    anim_flags = FLAG_LOOPED if normalized["looped"] else 0
    modifiers = [
        (index, bone["modifier"])
        for index, bone in enumerate(bones)
        if bone["modifier"] is not None
    ]

    payload = struct.pack(
        "<6BfII4BI",
        normalized["anim_type"],
        anim_flags,
        presence,
        property_flags,
        0,
        0,
        normalized["framerate"],
        frame_count,
        len(bones),
        len(modifiers),
        0,
        0,
        0,
        len(notes),
    )
    output = bytearray(MAGIC)
    output.extend(struct.pack("<hH", VERSION, HEADER_SIZE))
    output.extend(payload)
    for bone in bones:
        output.extend(encode_cstring(bone["name"]))
    for bone_index, modifier in modifiers:
        output.extend(struct.pack("<" + bone_format + "B",
                                  bone_index, modifier))

    channels = (
        ("position_keys", PRESENCE_POSITION, 3),
        ("rotation_keys", PRESENCE_ROTATION, 4),
        ("scale_keys", PRESENCE_SCALE, 3),
    )
    for bone in bones:
        output.extend(struct.pack("<B", bone["flags"]))
        for key_name, presence_flag, components in channels:
            if not presence & presence_flag:
                continue
            keys = bone[key_name]
            output.extend(struct.pack("<" + frame_format, len(keys)))
            for key in keys:
                values = key["value"]
                output.extend(
                    struct.pack(
                        "<" + frame_format + str(components) + scalar_format,
                        key["frame"],
                        *values
                    )
                )
    for note in notes:
        output.extend(struct.pack("<" + frame_format, note["frame"]))
        output.extend(encode_cstring(note["name"]))
    return bytes(output)


def read_seanim(path):
    return read_seanim_bytes(Path(path).read_bytes())


def write_seanim(
    path,
    bones,
    framerate=30.0,
    looped=False,
    anim_type=AnimType.RELATIVE,
    notes=None,
    modifiers=None,
    precision="float32",
):
    if modifiers is None:
        modifiers = {}
    if not isinstance(modifiers, dict):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "modifiers must be a bone-name mapping",
        )
    normalized_bones = []
    max_frame = 0
    for bone in bones:
        normalized = {
            "flags": bone.get("flags", 0),
            "modifier": bone.get("modifier", modifiers.get(bone.get("name"))),
            "name": bone.get("name"),
            "position_keys": _normalize_legacy_keys(
                bone, "position_keys", "pos_keys"
            ),
            "rotation_keys": _normalize_legacy_keys(
                bone, "rotation_keys", "rot_keys"
            ),
            "scale_keys": _normalize_legacy_keys(
                bone, "scale_keys", "scale_keys"
            ),
        }
        for channel in ("position_keys", "rotation_keys", "scale_keys"):
            for key in normalized[channel]:
                max_frame = max(max_frame, key["frame"])
        normalized_bones.append(normalized)
    normalized_notes = []
    for note_index, note in enumerate(notes or []):
        if isinstance(note, dict):
            if "frame" not in note:
                raise AnimationFormatError(
                    "ANIM_DOCUMENT_INVALID",
                    "notes element %d is missing frame" % note_index,
                )
            frame = note["frame"]
            name = note.get("name")
        else:
            try:
                frame, name = note
            except (TypeError, ValueError):
                raise AnimationFormatError(
                    "ANIM_DOCUMENT_INVALID",
                    "notes must be mappings or (frame, name) pairs",
                )
        frame = _strict_int(
            frame, "notes element %d frame" % note_index, 0, 0xFFFFFFFE
        )
        item = {"frame": frame, "name": name}
        max_frame = max(max_frame, frame)
        normalized_notes.append(item)
    document = {
        "anim_type": int(anim_type),
        "bones": normalized_bones,
        "format": "seanim",
        "frame_count": max_frame + 1,
        "framerate": framerate,
        "looped": looped,
        "notes": normalized_notes,
        "precision": precision,
        "version": VERSION,
    }
    data = write_seanim_bytes(document)
    Path(path).write_bytes(data)
    return data


def _finite_at(value, label, offset):
    try:
        return require_finite(value, label)
    except AnimationFormatError as error:
        raise AnimationFormatError(error.code, error.message, offset)


def _index_format(count):
    if count <= 0xFF:
        return "B", 1
    if count <= 0xFFFF:
        return "H", 2
    return "I", 4


def _strict_int(value, label, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "%s must be an int" % label,
        )
    if not minimum <= value <= maximum:
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "%s must be in %d..%d" % (label, minimum, maximum),
        )
    return value


def _validate_keys(
    keys, label, components, frame_count, scalar_validator
):
    if not isinstance(keys, list):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "%s must be a list" % label
        )
    output = []
    seen_frames = set()
    for key in keys:
        if not isinstance(key, dict) or set(key) != {"frame", "value"}:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "%s keys require frame and value" % label,
            )
        frame = _strict_int(key["frame"], "%s frame" % label,
                            0, frame_count - 1)
        if frame in seen_frames:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "%s contains duplicate frame %d" % (label, frame),
            )
        seen_frames.add(frame)
        value = key["value"]
        if not isinstance(value, (list, tuple)) or len(value) != components:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "%s value must have %d components" % (label, components),
            )
        output.append({
            "frame": frame,
            "value": [
                scalar_validator(component, "%s value" % label)
                for component in value
            ],
        })
    return output


def _validate_document(document):
    if not isinstance(document, dict):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "document must be an object"
        )
    required = {
        "anim_type", "bones", "format", "frame_count", "framerate",
        "looped", "notes", "precision", "version",
    }
    optional = {"presence_flags"}
    if (
        not required.issubset(document)
        or not set(document).issubset(required | optional)
    ):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "document fields must contain %s; optional fields are %s"
            % (sorted(required), sorted(optional)),
        )
    if document["format"] != "seanim" or document["version"] != VERSION:
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "format/version must be seanim/1",
        )
    anim_type = _strict_int(document["anim_type"], "anim_type", 0, 3)
    if not isinstance(document["looped"], bool):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "looped must be bool"
        )
    if document["precision"] not in ("float32", "float64"):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "precision must be float32 or float64",
        )
    framerate = require_float32(document["framerate"], "framerate")
    if framerate <= 0.0:
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "framerate must be greater than zero"
        )
    frame_count = _strict_int(
        document["frame_count"], "frame_count", 1, 0xFFFFFFFF
    )
    scalar_validator = (
        require_finite
        if document["precision"] == "float64"
        else require_float32
    )
    bones_value = document["bones"]
    if not isinstance(bones_value, list):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "bones must be a list"
        )
    if len(bones_value) > 0xFFFFFFFF:
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "too many bones"
        )
    bones = []
    names = set()
    for bone in bones_value:
        required_bone = {
            "flags", "modifier", "name", "position_keys",
            "rotation_keys", "scale_keys",
        }
        if not isinstance(bone, dict) or set(bone) != required_bone:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "bone fields must be exactly %s" % sorted(required_bone),
            )
        name = bone["name"]
        if not isinstance(name, str) or not name or name in names:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "bone names must be non-empty and unique",
            )
        encode_cstring(name)
        names.add(name)
        modifier = bone["modifier"]
        if modifier is not None:
            modifier = _strict_int(modifier, "modifier", 0, 255)
        bones.append({
            "flags": _strict_int(bone["flags"], "bone flags", 0, 255),
            "modifier": modifier,
            "name": name,
            "position_keys": _validate_keys(
                bone["position_keys"],
                "position_keys",
                3,
                frame_count,
                scalar_validator,
            ),
            "rotation_keys": _validate_keys(
                bone["rotation_keys"],
                "rotation_keys",
                4,
                frame_count,
                scalar_validator,
            ),
            "scale_keys": _validate_keys(
                bone["scale_keys"],
                "scale_keys",
                3,
                frame_count,
                scalar_validator,
            ),
        })
    notes_value = document["notes"]
    if not isinstance(notes_value, list):
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID", "notes must be a list"
        )
    notes = []
    for note in notes_value:
        if not isinstance(note, dict) or set(note) != {"frame", "name"}:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "notes require frame and name",
            )
        name = note["name"]
        encode_cstring(name)
        notes.append({
            "frame": _strict_int(
                note["frame"], "note frame", 0, frame_count - 1
            ),
            "name": name,
        })

    if "presence_flags" in document:
        presence_flags = _strict_int(
            document["presence_flags"], "presence_flags", 0, 0xFF
        )
        if presence_flags & ~SUPPORTED_PRESENCE:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "presence_flags contains unsupported bits",
            )
        bone_presence = (
            PRESENCE_POSITION | PRESENCE_ROTATION | PRESENCE_SCALE
        )
        if presence_flags & bone_presence and not bones:
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "bone channel presence_flags require at least one bone",
            )
        channels = (
            ("position_keys", PRESENCE_POSITION),
            ("rotation_keys", PRESENCE_ROTATION),
            ("scale_keys", PRESENCE_SCALE),
        )
        for key_name, presence_flag in channels:
            if any(bone[key_name] for bone in bones) \
                    and not presence_flags & presence_flag:
                raise AnimationFormatError(
                    "ANIM_DOCUMENT_INVALID",
                    "presence_flags does not declare non-empty %s" % key_name,
                )
        if bool(presence_flags & PRESENCE_NOTE) != bool(notes):
            raise AnimationFormatError(
                "ANIM_DOCUMENT_INVALID",
                "presence_flags and notes disagree",
            )
    else:
        presence_flags = 0
        if any(bone["position_keys"] for bone in bones):
            presence_flags |= PRESENCE_POSITION
        if any(bone["rotation_keys"] for bone in bones):
            presence_flags |= PRESENCE_ROTATION
        if any(bone["scale_keys"] for bone in bones):
            presence_flags |= PRESENCE_SCALE
        if notes:
            presence_flags |= PRESENCE_NOTE

    return {
        "anim_type": anim_type,
        "bones": bones,
        "format": "seanim",
        "frame_count": frame_count,
        "framerate": framerate,
        "looped": document["looped"],
        "notes": notes,
        "presence_flags": presence_flags,
        "precision": document["precision"],
        "version": VERSION,
    }


def _normalize_legacy_keys(bone, modern_name, legacy_name):
    has_modern = modern_name in bone
    has_legacy = legacy_name in bone
    if modern_name == legacy_name:
        has_legacy = False
    if has_modern and has_legacy:
        raise AnimationFormatError(
            "ANIM_DOCUMENT_INVALID",
            "bone cannot contain both %s and %s"
            % (modern_name, legacy_name),
        )
    value = bone.get(modern_name if has_modern else legacy_name, [])
    output = []
    for item_index, item in enumerate(value):
        if isinstance(item, dict):
            if "frame" not in item:
                raise AnimationFormatError(
                    "ANIM_DOCUMENT_INVALID",
                    "%s element %d is missing frame"
                    % (modern_name, item_index),
                )
            frame = item["frame"]
            components = item.get("value")
        else:
            try:
                frame, components = item
            except (TypeError, ValueError):
                raise AnimationFormatError(
                    "ANIM_DOCUMENT_INVALID",
                    "%s entries must be mappings or (frame, value) pairs"
                    % modern_name,
                )
            components = list(components)
        frame = _strict_int(
            frame,
            "%s element %d frame" % (modern_name, item_index),
            0,
            0xFFFFFFFE,
        )
        output.append({"frame": frame, "value": components})
    return output
