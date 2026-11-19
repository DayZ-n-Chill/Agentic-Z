"""Regression tests for seanim_export.py: viewer bone frames -> DayZATool SEAnim.

Expected values are written out by hand from the Route C conversion calibrated
on the JD rig: rotation (x,y,z,w) -> (-y,-z,x,w), rest position
(x,y,z) -> (y,z,-x) in cm. The FBX rig built by build_rig_dayz.py carries the
same skeleton turned 90 deg about Z, (x,y,z) -> (y,-x,z), so one pose authored
on either rig must come out as the same SEAnim.
"""

import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPTS = Path(__file__).resolve().parent
EXPORTER = SCRIPTS / "seanim_export.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sw = _load("skill_seanim_writer", SCRIPTS / "seanim_writer.py")

W = math.sqrt(1.0 - 0.14)
Q_A = (0.1, 0.2, 0.3, W)        # a rotation whose components are all distinct
Q_B = (-0.3, 0.1, 0.2, W)

# One small skeleton in the JD rig's bone frames: meters, each child offset in
# its parent's frame. Chain children of Left* bones sit at +Y, of Right* at -Y;
# the shoulders and the index/ring pairs carry the roll DayZ's skeleton has.
JD_SKELETON = [
    ("Pelvis", None, (0.0, 1.0, 0.0)),
    ("Spine", "Pelvis", (0.0, 0.1, 0.0)),
    ("Spine3", "Spine", (0.0, 0.2, 0.0)),
    ("LeftShoulder", "Spine3", (0.01, 0.15, 0.05)),
    ("LeftArm", "LeftShoulder", (0.0, 0.16, 0.0)),
    ("LeftForeArm", "LeftArm", (0.0, 0.25, 0.0)),
    ("LeftHand", "LeftForeArm", (0.0, 0.24, 0.0)),
    ("LeftHandIndex1", "LeftHand", (-0.0015, 0.086, 0.0375)),
    ("LeftHandIndex2", "LeftHandIndex1", (0.0, 0.045, 0.0)),
    ("LeftHandRing", "LeftHand", (0.0, 0.034, 0.01)),
    ("RightShoulder", "Spine3", (-0.01, 0.15, 0.05)),
    ("RightArm", "RightShoulder", (0.0, -0.16, 0.0)),
    ("RightForeArm", "RightArm", (0.0, -0.25, 0.0)),
    ("RightHand", "RightForeArm", (0.0, -0.24, 0.0)),
    ("RightHandIndex1", "RightHand", (0.0015, -0.086, -0.0375)),
    ("RightHandIndex2", "RightHandIndex1", (0.0, -0.045, 0.0)),
    ("RightHandRing", "RightHand", (0.0, -0.034, -0.01)),
    ("RightHandThumb1", "RightHand", (-0.02, -0.015, -0.03)),
    ("RightHand_Dummy", "RightHand", (-0.0373, -0.0735, 0.0042)),
    ("Weapon_Root", "RightHand_Dummy", (0.0, -0.02, 0.0)),
]
ORDER = [name for name, _, _ in JD_SKELETON]


def _turn_pos(p):
    """JD bone frame -> FBX-rig bone frame (measured: q_fbx = (y,-x,z,w)_jd)."""
    return (p[1], -p[0], p[2])


def _turn_quat(q):
    return (q[1], -q[0], q[2], q[3])


def _rig(turn=False):
    bones = []
    for name, parent, pos in JD_SKELETON:
        bones.append({
            "name": name,
            "parent": parent,
            "pos": list(_turn_pos(pos) if turn else pos),
            "quat": list(_turn_quat((0.0, 0.0, 0.0, 1.0)) if turn else (0.0, 0.0, 0.0, 1.0)),
        })
    return {"space": "test", "bone_order": list(ORDER), "bones": bones}


def _frame_quat(name, frame):
    """Q_A on every bone at frame 0 and 2, Q_B on RightHand at frame 1."""
    if frame == 1 and name == "RightHand":
        return Q_B
    if frame == 1:
        return (0.0, 0.0, 0.0, 1.0)
    return Q_A


def _anim(turn=False):
    frames = []
    for fr in range(3):
        q = {n: list(_turn_quat(_frame_quat(n, fr)) if turn else _frame_quat(n, fr)) for n in ORDER}
        frames.append({"bones": q})
    return {"format": "dayz-anim-authoring/v1", "space": "rig-local-quat", "fps": 30,
            "bone_order": list(ORDER), "keyframes": [0, 2], "frames": frames}


def _write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _run(tmp_path, anim, rig, *extra):
    anim_p = _write(tmp_path / "anim.json", anim)
    rig_p = _write(tmp_path / "rig.json", rig)
    out = tmp_path / "out.seanim"
    proc = subprocess.run(
        [sys.executable, str(EXPORTER), "--anim", str(anim_p), "--rig", str(rig_p),
         "--out", str(out), *extra],
        capture_output=True, text=True,
    )
    return proc, out


def _close(a, b, eps=1e-5):
    return len(a) == len(b) and all(abs(x - y) <= eps for x, y in zip(a, b))


def _bones(out):
    return {b["name"]: b for b in sw.read_seanim(str(out))["bones"]}


# Hand-written expectations (calibrated formula):
#   Q_A (0.1, 0.2, 0.3, w)   -> (-0.2, -0.3, 0.1, w)
#   Q_B (-0.3, 0.1, 0.2, w)  -> (-0.1, -0.2, -0.3, w)
#   RightHandThumb1 (-0.02, -0.015, -0.03) m -> (-1.5, -3.0, 2.0) cm
#   LeftShoulder (0.01, 0.15, 0.05) m -> (15, 5, -1) cm ; RightShoulder -> (15, 5, 1) cm
#   LeftHand (0, 0.24, 0) m -> (24, 0, 0) cm ; RightHand (0, -0.24, 0) m -> (-24, 0, 0) cm
#   RightHandIndex1 (0.0015, -0.086, -0.0375) m -> (-8.6, -3.75, -0.15) cm
EXPECT_ROT_A = (-0.2, -0.3, 0.1, W)
EXPECT_ROT_B = (-0.1, -0.2, -0.3, W)
EXPECT_POS = {
    "RightHandThumb1": (-1.5, -3.0, 2.0),
    "LeftShoulder": (15.0, 5.0, -1.0),
    "RightShoulder": (15.0, 5.0, 1.0),
    "LeftHand": (24.0, 0.0, 0.0),
    "RightHand": (-24.0, 0.0, 0.0),
    "RightHandIndex1": (-8.6, -3.75, -0.15),
}


@pytest.mark.parametrize("turn", [False, True], ids=["jd-rig", "fbx-rig"])
def test_pose_converts_to_the_calibrated_seanim_values(tmp_path, turn):
    """Breaks if either rig's bone frames reach the SEAnim without the calibrated map."""
    proc, out = _run(tmp_path, _anim(turn), _rig(turn))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    got = _bones(out)
    assert list(got) == ORDER
    rh = dict(got["RightHand"]["rot_keys"])
    assert _close(rh[0], EXPECT_ROT_A) and _close(rh[2], EXPECT_ROT_A)
    assert _close(rh[1], EXPECT_ROT_B)
    assert _close(dict(got["LeftHandIndex2"]["rot_keys"])[1], (0.0, 0.0, 0.0, 1.0))
    for name, cm in EXPECT_POS.items():
        keys = got[name]["pos_keys"]
        assert len(keys) == 1 and keys[0][0] == 0
        assert _close(keys[0][1], cm, eps=1e-4), (name, keys[0][1], cm)


def test_both_rigs_give_identical_seanim_keys(tmp_path):
    """Breaks if the FBX map stops being the calibrated map composed with the measured turn."""
    jd_dir = tmp_path / "jd"
    fbx_dir = tmp_path / "fbx"
    jd_dir.mkdir()
    fbx_dir.mkdir()
    p1, out_jd = _run(jd_dir, _anim(False), _rig(False))
    p2, out_fbx = _run(fbx_dir, _anim(True), _rig(True))
    assert p1.returncode == 0 and p2.returncode == 0, p1.stderr + p2.stderr
    a, b = _bones(out_jd), _bones(out_fbx)
    for name in ORDER:
        for grp in ("rot_keys", "pos_keys"):
            ka, kb = a[name][grp], b[name][grp]
            assert [f for f, _ in ka] == [f for f, _ in kb]
            assert all(_close(x, y, eps=1e-5) for (_, x), (_, y) in zip(ka, kb)), (name, grp)


def test_position_map_reflects_and_quaternions_follow_it():
    """Breaks if a map loses the det -1 reflection or the quaternion sign that goes with it."""
    mod = _load("skill_seanim_export", EXPORTER)
    for frame in ("jd", "fbx"):
        cols = [mod.seanim_pos_cm(frame, e) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
        m = [[cols[c][r] / 100.0 for c in range(3)] for r in range(3)]
        det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
               - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
               + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
        assert abs(det + 1.0) < 1e-9, (frame, det)
        # under a reflection M the vector part of a rotation maps to -M v
        for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            rot = mod.seanim_rot(frame, (*v, 0.0))
            pos = mod.seanim_pos_cm(frame, v)
            assert _close(rot[:3], tuple(-c / 100.0 for c in pos)), (frame, v, rot, pos)


def test_rig_frames_are_read_from_rest_offsets():
    """Breaks if detection confuses the two rigs."""
    mod = _load("skill_seanim_export", EXPORTER)
    assert mod.detect_rig_frame(_rig(False)) == "jd"
    assert mod.detect_rig_frame(_rig(True)) == "fbx"


@pytest.mark.parametrize("helper", ["RightHand_Dummy", "Weapon_Root"])
def test_helper_off_bind_does_not_decide_the_rig_frame(helper):
    """Breaks if a helper the viewer moved (RightHand_Dummy at the grip, or its child
    Weapon_Root) can veto a valid rig."""
    mod = _load("skill_seanim_export", EXPORTER)
    rig = _rig(False)
    next(b for b in rig["bones"] if b["name"] == helper)["pos"] = [-0.05, 0.0, 0.0]
    assert mod.detect_rig_frame(rig) == "jd"


def _blender_native_rig():
    """Same skeleton, but every chain child at +Y (Blender's head-to-tail layout)."""
    rig = _rig(False)
    for b in rig["bones"]:
        b["pos"] = [b["pos"][0], abs(b["pos"][1]), b["pos"][2]]
    return rig


def _mixed_rig():
    """Left side in JD frames, right side in FBX frames."""
    rig = _rig(False)
    for b in rig["bones"]:
        if b["parent"] and b["parent"].startswith("Right"):
            b["pos"] = list(_turn_pos(b["pos"]))
    return rig


def _rolled_by(deg):
    """Every bone frame rolled by deg about its axis (JD Y): the bone axes still read JD."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    rig = _rig(False)
    for b in rig["bones"]:
        if b["parent"]:
            x, y, z = b["pos"]
            b["pos"] = [c * x - s * z, y, s * x + c * z]
    return rig


def _rolled_rig():
    return _rolled_by(180.0)


def _rolled_5deg_rig():
    return _rolled_by(5.0)


@pytest.mark.parametrize("make_rig", [_blender_native_rig, _mixed_rig, _rolled_rig, _rolled_5deg_rig],
                         ids=["blender-native", "mixed", "rolled", "rolled-5deg"])
def test_unknown_rig_frame_is_refused(tmp_path, make_rig):
    """Breaks if a rig of neither calibrated family gets a conversion anyway."""
    mod = _load("skill_seanim_export", EXPORTER)
    with pytest.raises(ValueError):
        mod.detect_rig_frame(make_rig())
    proc, out = _run(tmp_path, _anim(False), make_rig())
    assert proc.returncode != 0
    assert "rig frame" in proc.stderr
    assert not out.exists()


def test_roll_inside_the_tolerance_is_accepted():
    """Breaks if the roll tolerance drops to zero: the two real rigs read up to 0.07 deg off
    vanilla, so a 1 deg roll must still pass (and 5 deg must not, above)."""
    mod = _load("skill_seanim_export", EXPORTER)
    assert mod.detect_rig_frame(_rolled_by(1.0)) == "jd"


def test_anim_bone_missing_from_rig_is_refused(tmp_path):
    """Breaks if an anim authored on another rig is converted with this rig's frames."""
    anim = _anim(False)
    anim["bone_order"].append("RightHandPinky1")
    for fr in anim["frames"]:
        fr["bones"]["RightHandPinky1"] = list(Q_A)
    proc, out = _run(tmp_path, anim, _rig(False))
    assert proc.returncode != 0
    assert "RightHandPinky1" in proc.stderr
    assert not out.exists()


def test_rest_pose_reference_masks_bones(tmp_path):
    """Breaks if --rest-pose stops limiting the export to the reference's bones."""
    ref = tmp_path / "ref.seanim"
    keep = ["RightHandIndex1", "Spine", "LeftHand", "RightHand"]
    sw.write_seanim(str(ref), [{"name": n, "rot_keys": [(0, (0.0, 0.0, 0.0, 1.0))]} for n in keep])
    proc, out = _run(tmp_path, _anim(False), _rig(False), "--rest-pose", str(ref))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    got = _bones(out)
    assert list(got) == ["Spine", "LeftHand", "RightHand", "RightHandIndex1"]
    assert _close(dict(got["RightHand"]["rot_keys"])[1], EXPECT_ROT_B)


def test_rest_pose_reference_positions_are_not_copied(tmp_path):
    """Breaks if a reference position (RELATIVE in vanilla extracts: an offset from rest) is
    written as this ABSOLUTE clip's offset."""
    ref = tmp_path / "ref.seanim"
    sw.write_seanim(str(ref), [
        {"name": "Spine3", "pos_keys": [(0, (0.0, 0.0, 0.0))], "rot_keys": [(0, (0.0, 0.0, 0.0, 1.0))]},
        {"name": "RightHand", "pos_keys": [(0, (-7.35, 0.42, 3.73))], "rot_keys": [(0, (0.0, 0.0, 0.0, 1.0))]},
    ])
    proc, out = _run(tmp_path, _anim(True), _rig(True), "--rest-pose", str(ref))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    got = _bones(out)
    assert list(got) == ["Spine3", "RightHand"]
    assert _close(got["Spine3"]["pos_keys"][0][1], (20.0, 0.0, 0.0), eps=1e-4)
    assert _close(got["RightHand"]["pos_keys"][0][1], EXPECT_POS["RightHand"], eps=1e-4)


def test_per_frame_positions_are_flagged_and_ignored(tmp_path):
    """Breaks if per-frame positions (the project viewer's Weapon_* slide) leave silently or
    replace the rest offset."""
    anim = _anim(False)
    for fr in anim["frames"]:
        fr["pos"] = {"RightHand": [0.5, 0.5, 0.5]}
    proc, out = _run(tmp_path, anim, _rig(False))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "per-frame positions" in proc.stderr
    assert _close(_bones(out)["RightHand"]["pos_keys"][0][1], EXPECT_POS["RightHand"], eps=1e-4)


def test_missing_rest_pose_reference_is_refused(tmp_path):
    """Breaks if a missing mask file silently exports every bone, root included."""
    proc, out = _run(tmp_path, _anim(False), _rig(False), "--rest-pose", str(tmp_path / "nope.seanim"))
    assert proc.returncode != 0
    assert not out.exists()


def test_root_bone_without_mask_is_flagged(tmp_path):
    """Breaks if a root bone is exported in silence: the bone-frame map does not cover it."""
    proc, out = _run(tmp_path, _anim(False), _rig(False))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Pelvis" in proc.stderr and "root" in proc.stderr


def test_keys_only_ending_before_the_last_frame_passes_the_gate(tmp_path):
    """Breaks if --keys-only checks the written frame count against every frame of the anim."""
    anim = _anim(False)
    anim["keyframes"] = [0, 1]
    proc, out = _run(tmp_path, anim, _rig(False), "--keys-only")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    rd = sw.read_seanim(str(out))
    assert rd["frame_count"] == 2
    assert [f for f, _ in _bones(out)["RightHand"]["rot_keys"]] == [0, 1]
