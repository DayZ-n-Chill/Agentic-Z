"""Regression tests for seanim_writer.py: SEAnim bone modifiers survive a read/write round trip.

A DayZATool 1.3 extract of a vanilla clip marks bones RELATIVE through SEAnim bone
modifiers (p_1hd_erc_idle_low: 60 of its 65 bones, all type 2). read_seanim skipped
them and write_seanim always wrote a count of 0, so editing one track of a vanilla
clip turned every bone ABSOLUTE. The fixtures are built here byte by byte from the
SEAnim v1 layout (as seanim.py of the io_anim_seanim Blender add-on reads it), not
with write_seanim, so the writer is checked against the format, not against itself.
"""

import importlib.util
from pathlib import Path
import struct

import pytest


SCRIPTS = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sw = _load("skill_seanim_writer_modifiers", SCRIPTS / "seanim_writer.py")

ABSOLUTE, RELATIVE = 0, 2   # SEAnim animation types (seanim.py SEANIM_TYPE)
LOC, ROT = 1 << 0, 1 << 1   # presence flags


def _index_char(count):
    # frame_t / bone_t: the narrowest unsigned type that holds the count (seanim.py)
    if count <= 0xFF:
        return "B"
    if count <= 0xFFFF:
        return "H"
    return "I"


def build_seanim(bones, modifiers, frame_count, framerate=60.0, anim_type=ABSOLUTE):
    """bones: [(name, pos_keys, rot_keys)]; modifiers: [(bone_index, type)] in file order."""
    out = bytearray(b"SEAnim") + struct.pack("<h", 1)
    payload = struct.pack(
        "<6BfII4BI",
        anim_type, 0, LOC | ROT, 0, 0, 0,          # type, flags, presence, properties, reserved x2
        framerate, frame_count, len(bones),
        len(modifiers), 0, 0, 0,                   # modifier count, reserved x3
        0,                                         # note count
    )
    out += struct.pack("<h", len(payload) + 2) + payload
    for name, _, _ in bones:
        out += name.encode("utf-8") + b"\0"
    bone_t = _index_char(len(bones))
    for bone_index, kind in modifiers:
        out += struct.pack("<" + bone_t + "B", bone_index, kind)
    frame_t = _index_char(frame_count)
    for _, pos_keys, rot_keys in bones:
        out += b"\0"                               # per-bone flags
        out += struct.pack("<" + frame_t, len(pos_keys))
        for frame, value in pos_keys:
            out += struct.pack("<" + frame_t + "3f", frame, *value)
        out += struct.pack("<" + frame_t, len(rot_keys))
        for frame, value in rot_keys:
            out += struct.pack("<" + frame_t + "4f", frame, *value)
    return bytes(out)


IDENTITY = (0.0, 0.0, 0.0, 1.0)
TURN = (0.0, 0.5, 0.0, 0.75)

# Shaped like the DayZATool extract of p_1hd_erc_idle_low: an ABSOLUTE header, the
# roots and LeftHand_Dummy without a modifier, the other bones RELATIVE and without
# position keys.
EXTRACT_BONES = [
    ("Scene_Root", [(0, (0.0, 0.0, 0.0))], [(0, IDENTITY), (3, IDENTITY)]),
    ("EntityPosition", [(0, (0.0, 0.0, 0.0)), (3, (0.0, 0.0, 1.5))], [(0, IDENTITY)]),
    ("Collision", [], [(0, IDENTITY)]),
    ("Pelvis", [(0, (0.0, 98.25, 0.0))], [(0, IDENTITY), (3, TURN)]),
    ("Spine", [], [(0, TURN), (1, IDENTITY), (3, TURN)]),
    ("Spine1", [], [(0, IDENTITY)]),
    ("LeftArm", [], [(0, IDENTITY), (3, TURN)]),
    ("LeftHand_Dummy", [], [(0, IDENTITY)]),
    ("RightArm", [], [(0, TURN)]),
]
EXTRACT_MODIFIERS = [(4, RELATIVE), (5, RELATIVE), (6, RELATIVE), (8, RELATIVE)]
EXPECTED_MODIFIERS = [None, None, None, None, RELATIVE, RELATIVE, RELATIVE, None, RELATIVE]


def _write_back(path, data):
    return sw.write_seanim(
        str(path), data["bones"], framerate=data["framerate"],
        looped=data["looped"], anim_type=data["anim_type"], notes=data["notes"],
    )


@pytest.fixture
def extract(tmp_path):
    raw = build_seanim(EXTRACT_BONES, EXTRACT_MODIFIERS, frame_count=4)
    path = tmp_path / "extract.seanim"
    path.write_bytes(raw)
    return path, raw


def test_read_returns_the_modifier_of_each_bone(extract):
    path, _ = extract
    data = sw.read_seanim(str(path))
    assert [b["name"] for b in data["bones"]] == [b[0] for b in EXTRACT_BONES]
    assert [b["modifier"] for b in data["bones"]] == EXPECTED_MODIFIERS
    assert data["anim_type"] == ABSOLUTE


def test_read_then_write_gives_back_the_same_bytes(extract, tmp_path):
    path, raw = extract
    out = _write_back(tmp_path / "back.seanim", sw.read_seanim(str(path)))
    assert out == raw
    assert (tmp_path / "back.seanim").read_bytes() == raw


def test_editing_one_track_keeps_every_modifier(extract, tmp_path):
    path, _ = extract
    data = sw.read_seanim(str(path))
    left_arm = next(b for b in data["bones"] if b["name"] == "LeftArm")
    left_arm["rot_keys"] = [(0, TURN), (3, IDENTITY)]
    out = _write_back(tmp_path / "edited.seanim", data)
    edited = [
        (name, pos, [(0, TURN), (3, IDENTITY)] if name == "LeftArm" else rot)
        for name, pos, rot in EXTRACT_BONES
    ]
    assert out == build_seanim(edited, EXTRACT_MODIFIERS, frame_count=4)
    again = sw.read_seanim(str(tmp_path / "edited.seanim"))
    assert [b["modifier"] for b in again["bones"]] == EXPECTED_MODIFIERS


def test_a_modifier_stays_with_its_bone_when_bones_are_dropped(extract, tmp_path):
    path, _ = extract
    data = sw.read_seanim(str(path))
    kept = [b for b in data["bones"] if b["name"] not in ("Scene_Root", "Spine1")]
    out = sw.write_seanim(str(tmp_path / "masked.seanim"), kept, framerate=60.0)
    rest = [b for b in EXTRACT_BONES if b[0] not in ("Scene_Root", "Spine1")]
    # Spine, LeftArm and RightArm move from indices 4, 6, 8 to 3, 4, 6
    assert out == build_seanim(rest, [(3, RELATIVE), (4, RELATIVE), (6, RELATIVE)], frame_count=4)


def test_past_255_bones_the_modifier_index_is_two_bytes_wide(tmp_path):
    bones = [("Bone%03d" % i, [], [(0, IDENTITY)]) for i in range(300)]
    bones[0] = ("Bone000", [(0, (0.0, 1.0, 0.0))], [(0, IDENTITY)])
    bones[299] = ("Bone299", [], [(0, IDENTITY), (2, TURN)])
    modifiers = [(0, RELATIVE), (255, 1), (256, RELATIVE), (299, 3)]
    raw = build_seanim(bones, modifiers, frame_count=3)
    path = tmp_path / "wide.seanim"
    path.write_bytes(raw)
    data = sw.read_seanim(str(path))
    assert {i: b["modifier"] for i, b in enumerate(data["bones"]) if b["modifier"] is not None} \
        == dict(modifiers)
    assert _write_back(tmp_path / "wide_back.seanim", data) == raw


def test_modifier_0_is_kept_as_a_value_and_255_is_a_valid_byte(tmp_path):
    # 0 (ABSOLUTE) under a RELATIVE header is an override, not "no modifier": a truthiness
    # test on read or on write would drop it. 255 is the top of the byte the format stores.
    bones = [("Root", [(0, (0.0, 0.0, 0.0))], [(0, IDENTITY)]), ("Spine", [], [(0, TURN)]),
             ("Neck", [], [(0, IDENTITY)])]
    raw = build_seanim(bones, [(1, ABSOLUTE), (2, 255)], frame_count=1, anim_type=RELATIVE)
    path = tmp_path / "zero.seanim"
    path.write_bytes(raw)
    data = sw.read_seanim(str(path))
    assert [b["modifier"] for b in data["bones"]] == [None, ABSOLUTE, 255]
    assert _write_back(tmp_path / "zero_back.seanim", data) == raw


def test_a_modifier_equal_to_the_header_type_is_still_written(tmp_path):
    # An explicit override that repeats the header's type is redundant but present in the
    # file; dropping it would change the bytes of a clip read and written back.
    bones = [("Root", [(0, (0.0, 0.0, 0.0))], [(0, IDENTITY)]), ("Spine", [], [(0, TURN)]),
             ("Arm", [], [(0, IDENTITY)])]
    raw = build_seanim(bones, [(1, ABSOLUTE)], frame_count=1, anim_type=ABSOLUTE)
    path = tmp_path / "same.seanim"
    path.write_bytes(raw)
    data = sw.read_seanim(str(path))
    assert [b["modifier"] for b in data["bones"]] == [None, ABSOLUTE, None]
    assert _write_back(tmp_path / "same_back.seanim", data) == raw


@pytest.mark.parametrize("bone_count", [255, 256, 65535, 65536])
def test_the_modifier_index_widens_exactly_past_255_and_65535_bones(tmp_path, bone_count):
    # bone_t is one byte up to 255 bones, two up to 65535, four above (seanim.py)
    bones = [("B%05d" % i, [], []) for i in range(bone_count)]
    bones[0] = ("B00000", [(0, (0.0, 1.0, 0.0))], [(0, IDENTITY)])
    modifiers = [(bone_count - 1, RELATIVE)]
    raw = build_seanim(bones, modifiers, frame_count=1)
    path = tmp_path / "width.seanim"
    path.write_bytes(raw)
    data = sw.read_seanim(str(path))
    assert data["bones"][-1]["modifier"] == RELATIVE
    assert _write_back(tmp_path / "width_back.seanim", data) == raw


def test_write_accepts_255_modifiers_the_most_the_header_counts(tmp_path):
    bones = [("Bone%03d" % i, [], [(0, IDENTITY)]) for i in range(255)]
    bones[0] = ("Bone000", [(0, (0.0, 1.0, 0.0))], [(0, IDENTITY)])
    raw = build_seanim(bones, [(i, RELATIVE) for i in range(255)], frame_count=1)
    path = tmp_path / "most.seanim"
    path.write_bytes(raw)
    assert _write_back(tmp_path / "most_back.seanim", sw.read_seanim(str(path))) == raw


def test_bones_without_a_modifier_key_write_no_modifier_block(tmp_path):
    # What every caller in this skill passes (seanim_export.py, ik_pose_to_seanim.py):
    # the output must keep the layout it had before modifiers were written.
    bones = [
        {"name": "Spine", "pos_keys": [(0, (0.0, 10.0, 0.0))], "rot_keys": [(0, IDENTITY), (2, TURN)]},
        {"name": "LeftArm", "rot_keys": [(0, TURN)]},
    ]
    out = sw.write_seanim(str(tmp_path / "plain.seanim"), bones, framerate=30.0)
    expected = build_seanim(
        [("Spine", [(0, (0.0, 10.0, 0.0))], [(0, IDENTITY), (2, TURN)]), ("LeftArm", [], [(0, TURN)])],
        [], frame_count=3, framerate=30.0,
    )
    assert out == expected
    assert [b["modifier"] for b in sw.read_seanim(str(tmp_path / "plain.seanim"))["bones"]] == [None, None]


@pytest.mark.parametrize("modifiers", [[(9, RELATIVE)], [(4, RELATIVE), (4, 1)], [(4, RELATIVE), (4, RELATIVE)]],
                         ids=["index-out-of-range", "index-repeated", "index-repeated-same-type"])
def test_read_refuses_a_modifier_it_cannot_attach_to_one_bone(tmp_path, modifiers):
    path = tmp_path / "bad.seanim"
    path.write_bytes(build_seanim(EXTRACT_BONES, modifiers, frame_count=4))
    with pytest.raises(ValueError, match="modifier"):
        sw.read_seanim(str(path))


@pytest.mark.parametrize("value", [-1, 256, 2.0, True, False],
                         ids=["negative", "over-a-byte", "float", "bool-true", "bool-false"])
def test_write_refuses_a_modifier_that_is_not_a_byte(tmp_path, value):
    bones = [{"name": "Spine", "rot_keys": [(0, IDENTITY)], "modifier": value}]
    with pytest.raises(ValueError, match="modifier"):
        sw.write_seanim(str(tmp_path / "bad.seanim"), bones)


def test_write_refuses_more_modifiers_than_the_header_can_count(tmp_path):
    bones = [{"name": "Bone%03d" % i, "rot_keys": [(0, IDENTITY)], "modifier": RELATIVE} for i in range(256)]
    with pytest.raises(ValueError, match="modifier"):
        sw.write_seanim(str(tmp_path / "many.seanim"), bones)
