"""Regression tests for extract_empties.py, the rig stage between fbx_extract.py
and build_rig_dayz.py.

extract_empties.py runs inside Blender. These tests run it against stand-in
`bpy` and `mathutils` modules that hold a scene built by hand, so they need
numpy only (build_rig_dayz.py needs it too); without numpy, as on the CI
runner, the module skips itself. Every expected matrix is worked out in the
comment above it.
"""

import json
import os
from pathlib import Path
import runpy
import stat
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

np = pytest.importorskip("numpy")


SCRIPTS = Path(__file__).resolve().parent
EXTRACTOR = SCRIPTS / "extract_empties.py"
BUILD_RIG = SCRIPTS / "build_rig_dayz.py"


class Matrix:
    """The part of mathutils.Matrix the extractor uses: @, [row][col], Translation."""

    def __init__(self, rows=None):
        self.m = np.identity(4) if rows is None else np.array(rows, dtype=float)

    @classmethod
    def Translation(cls, vector):
        m = np.identity(4)
        m[:3, 3] = vector
        return cls(m)

    def __matmul__(self, other):
        return Matrix(self.m @ other.m)

    def __getitem__(self, row):
        return [float(x) for x in self.m[row]]


def _turn_z(translation=(0.0, 0.0, 0.0)):
    """+90 deg about Z (x -> y, y -> -x), then the translation."""
    m = np.array([
        [0.0, -1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])
    m[:3, 3] = translation
    return Matrix(m)


class _Objects(list):
    """bpy.data.objects: iterable, and indexable by name."""

    def get(self, name, default=None):
        return next((o for o in self if o.name == name), default)

    def __getitem__(self, key):
        if isinstance(key, str):
            found = self.get(key)
            if found is None:
                raise KeyError(key)
            return found
        return super().__getitem__(key)


def _empty(name, parent, parent_type, parent_bone="", inverse=None, basis=None):
    # matrix_world stays at the origin, as on the helpers the BI FBX imports
    # disabled in viewports: the extractor must not read it.
    return SimpleNamespace(
        name=name, type="EMPTY", parent=parent, parent_type=parent_type,
        parent_bone=parent_bone, matrix_world=Matrix(),
        matrix_parent_inverse=inverse or Matrix(), matrix_basis=basis or Matrix(),
    )


def _mesh(parent):
    return SimpleNamespace(name="Male_body", type="MESH", parent=parent,
                           parent_type="OBJECT", parent_bone="")


# Helpers the scene hangs straight from the armature object, each at its own
# (0,k,0): name -> (k, the y the file must hold). The file keeps six decimals,
# so Camera1st_lock_dummy's 6.1234564 must read 6.123456.
_ON_ARMATURE = {
    "weapon": (1.0, 1.0), "LeftHandIK": (2.0, 2.0), "RightHandIK": (3.0, 3.0),
    "LeftHandIKTarget": (4.0, 4.0), "RightHandIK_Helper": (5.0, 5.0),
    "Camera1st_lock_dummy": (6.1234564, 6.123456),
}


def _scene(without=()):
    """Every helper the extractor looks for, minus `without`. Weapon_Root hangs
    from RightHand_Dummy and goes with it."""
    arm = SimpleNamespace(
        name="Armature", type="ARMATURE", parent=None, parent_type="OBJECT", parent_bone="",
        matrix_world=Matrix.Translation((10.0, 0.0, 0.0)),
        matrix_parent_inverse=Matrix(), matrix_basis=Matrix.Translation((10.0, 0.0, 0.0)),
        # pose matrices, armature space: RightHand turned 90 deg about Z, head (0,0,5)
        pose=SimpleNamespace(bones={
            "RightHand": SimpleNamespace(matrix=_turn_z((0.0, 0.0, 5.0))),
            "LeftHand": SimpleNamespace(matrix=Matrix.Translation((0.0, 0.0, 5.0))),
        }),
        data=SimpleNamespace(bones={
            "RightHand": SimpleNamespace(length=2.0),
            "LeftHand": SimpleNamespace(length=3.0),
        }),
    )
    objects = [arm]
    if "RightHand_Dummy" not in without:
        hand = _empty("RightHand_Dummy", arm, "BONE", "RightHand",
                      basis=Matrix.Translation((0.0, 0.0, 1.0)))
        objects.append(hand)
        if "Weapon_Root" not in without:
            objects.append(_empty("Weapon_Root", hand, "OBJECT",
                                  basis=Matrix.Translation((1.0, 0.0, 0.0))))
    if "LeftHand_Dummy" not in without:
        objects.append(_empty("LeftHand_Dummy", arm, "BONE", "LeftHand", inverse=_turn_z(),
                              basis=Matrix.Translation((4.0, 0.0, 0.0))))
    objects += [
        _empty(name, arm, "OBJECT", basis=Matrix.Translation((0.0, k, 0.0)))
        for name, (k, _) in _ON_ARMATURE.items() if name not in without
    ]
    objects += [_empty("Lamp_Helper", arm, "BONE", "LeftHand"), _mesh(arm)]
    return _Objects(objects)


_TURN = [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
_SAME = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _affine(rotation, translation):
    rows = [rotation[r] + [translation[r]] for r in range(3)]
    return rows + [[0.0, 0.0, 0.0, 1.0]]


EXPECTED = {
    # Armature (10,0,0) + head (0,0,5); the bone is turned 90 deg about Z, so
    # its tail (0,2,0) lands at (-2,0,0) while the empty's own (0,0,1) stays.
    "RightHand_Dummy": _affine(_TURN, (8.0, 0.0, 6.0)),
    # Child of RightHand_Dummy: its own (1,0,0) turns with it to (0,1,0).
    "Weapon_Root": _affine(_TURN, (8.0, 1.0, 6.0)),
    # (10,0,0) + head (0,0,5) + tail (0,3,0); the parent inverse turns the
    # empty, and its own (4,0,0) with it to (0,4,0). In the other order the
    # offset would stay (4,0,0).
    "LeftHand_Dummy": _affine(_TURN, (10.0, 7.0, 5.0)),
    # Children of the armature object: (10,0,0) + their own (0,k,0).
    **{name: _affine(_SAME, (10.0, y, 0.0)) for name, (_, y) in _ON_ARMATURE.items()},
}


def _run_extractor(monkeypatch, scratch, objects, import_error=None):
    """Run the script as Blender would, after the FBX import left `objects`
    or failed with `import_error`."""
    imported = []

    def import_fbx(filepath):
        imported.append(filepath)
        if import_error is not None:
            raise import_error

    bpy = ModuleType("bpy")
    bpy.ops = SimpleNamespace(
        wm=SimpleNamespace(read_factory_settings=lambda use_empty=False: None),
        import_scene=SimpleNamespace(fbx=import_fbx),
    )
    bpy.context = SimpleNamespace(view_layer=SimpleNamespace(update=lambda: None))
    bpy.data = SimpleNamespace(objects=objects)
    mathutils = ModuleType("mathutils")
    mathutils.Matrix = Matrix
    monkeypatch.setitem(sys.modules, "bpy", bpy)
    monkeypatch.setitem(sys.modules, "mathutils", mathutils)
    monkeypatch.setenv("DAYZ_ANIM_SCRATCH", str(scratch))
    # The extractor reads its FBX path from this variable when set; the tests expect the default name.
    monkeypatch.delenv("DAYZ_ANIM_RIG_FBX", raising=False)
    runpy.run_path(str(EXTRACTOR), run_name="__main__")
    return imported


def _write_rig_raw(scratch):
    """A rig_raw.json whose mesh vertices sit on the bone heads: build_rig_dayz.py
    aligns it at scale 1 with no shift, so only the viewer frame
    (x, y, z) -> (x, z, -y) is left."""
    heads = {
        "Pelvis": (0.0, 0.0, 1.0), "Neck": (0.0, 0.0, 1.8), "Head": (0.0, 0.0, 2.0),
        "RightHand": (-1.0, 0.0, 1.5), "LeftHand": (1.0, 0.0, 1.5),
        "RightFoot": (-0.2, 0.0, 0.0), "LeftFoot": (0.2, 0.0, 0.0),
    }
    rig = {
        "bones": [
            {"name": name, "parent": None if name == "Pelvis" else "Pelvis",
             "world": Matrix.Translation(head).m.tolist(), "length": 0.1}
            for name, head in heads.items()
        ],
        "mesh": {
            "verts": [list(head) for head in heads.values()],
            "faces": [[0, 1, 2]],
            "weights": [[["Pelvis", 1.0]] for _ in heads],
        },
    }
    (scratch / "rig_raw.json").write_text(json.dumps(rig), encoding="utf-8")


def _build_rig(scratch):
    return subprocess.run(
        [sys.executable, str(BUILD_RIG)],
        env=dict(os.environ, DAYZ_ANIM_SCRATCH=str(scratch)),
        capture_output=True, text=True,
    )


def test_every_helper_is_composed_through_its_parent_chain(tmp_path, monkeypatch):
    """Breaks if the file moves, matrix_world leaks in, the chain order changes,
    or a helper drops out of the list."""
    _run_extractor(monkeypatch, tmp_path, _scene())

    out = json.loads((tmp_path / "empties_armworld.json").read_text(encoding="utf-8"))
    assert out == EXPECTED


def test_a_helper_the_fbx_lacks_is_listed_not_fatal(tmp_path, monkeypatch, capsys):
    """Breaks if an absent helper other than RightHand_Dummy stops the run: the
    BI FBX has no LeftHandIKTarget, and its other eight must still be written."""
    _run_extractor(monkeypatch, tmp_path, _scene(without=("LeftHandIKTarget",)))

    out = json.loads((tmp_path / "empties_armworld.json").read_text(encoding="utf-8"))
    assert sorted(out) == sorted(set(EXPECTED) - {"LeftHandIKTarget"})
    assert "LeftHandIKTarget" in capsys.readouterr().out


def test_build_rig_dayz_turns_the_file_into_anchors(tmp_path, monkeypatch):
    """Breaks if build_rig_dayz.py stops finding the extractor's file or reading it."""
    _run_extractor(monkeypatch, tmp_path, _scene())
    _write_rig_raw(tmp_path)

    done = _build_rig(tmp_path)

    assert done.returncode == 0, done.stderr
    anchors = json.loads((tmp_path / "rig_dayz.json").read_text(encoding="utf-8"))["anchors"]
    assert sorted(anchors) == sorted(EXPECTED)
    # (8,0,6) -> (8,6,0) and (8,1,6) -> (8,6,-1)
    assert anchors["RightHand_Dummy"]["pos"] == [8.0, 6.0, 0.0]
    assert anchors["Weapon_Root"]["pos"] == [8.0, 6.0, -1.0]


def test_no_file_without_right_hand_dummy(tmp_path, monkeypatch):
    """Breaks if a rig without the weapon anchor still yields a file: build_viewer.py
    would then place the weapon at its fixed (0, 1.3, 0.2) without a word."""
    with pytest.raises(SystemExit) as stopped:
        _run_extractor(monkeypatch, tmp_path, _scene(without=("RightHand_Dummy",)))

    assert "RightHand_Dummy" in str(stopped.value.code)
    assert not (tmp_path / "empties_armworld.json").exists()


@pytest.mark.parametrize(
    "objects, import_error, read_only, stop",
    [
        (lambda: _scene(without=("RightHand_Dummy",)), None, False, SystemExit),
        (lambda: _Objects([_mesh(None)]), None, False, StopIteration),
        # The import itself fails (a missing FBX): the earlier file must be gone
        # already, so the removal has to come before the import.
        (_scene, RuntimeError("Couldn't open file"), False, RuntimeError),
        # An earlier file restored read-only must not survive either.
        (lambda: _scene(without=("RightHand_Dummy",)), None, True, SystemExit),
    ],
    ids=["no-right-hand", "no-armature", "import-fails", "read-only-earlier-file"],
)
def test_a_failed_run_leaves_no_earlier_file_behind(
        tmp_path, monkeypatch, objects, import_error, read_only, stop):
    """Breaks if an earlier run's empties_armworld.json outlives a failed one:
    build_rig_dayz.py would build on it and the viewer fall back without a word.
    The {} is the stand-in a session wrote by hand."""
    earlier = tmp_path / "empties_armworld.json"
    earlier.write_text("{}", encoding="utf-8")
    if read_only:
        earlier.chmod(stat.S_IREAD)
    _write_rig_raw(tmp_path)

    with pytest.raises(stop):
        _run_extractor(monkeypatch, tmp_path, objects(), import_error)

    assert not earlier.exists()
    done = _build_rig(tmp_path)
    assert done.returncode != 0
    assert "empties_armworld.json" in done.stderr


def test_both_extractors_ship_the_same_fbx(tmp_path, monkeypatch):
    """Breaks if the default FBX paths drift apart: build_rig_dayz.py pairs
    rig_raw.json with empties_armworld.json, so both come from one FBX."""
    imported = _run_extractor(monkeypatch, tmp_path, _scene())

    assert len(imported) == 1
    assert imported[0] in (SCRIPTS / "fbx_extract.py").read_text(encoding="utf-8")
