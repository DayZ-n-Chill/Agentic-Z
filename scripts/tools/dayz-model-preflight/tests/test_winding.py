import copy
import math

import py3d
import pytest

from dayz_model_preflight.errors import PreflightError
from dayz_model_preflight.winding import check_winding

from _support import make_lod, save_model


IDENTITY = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]


def _winding(transform=None, faces=None, tolerance=1e-5):
    return {
        "faces": faces or [
            {
                "source": {"lod_index": 0, "face_index": 0},
                "target": {"lod_index": 0, "face_index": 0},
            }
        ],
        "position_tolerance_m": tolerance,
        "source_model": "source.p3d",
        "transform": copy.deepcopy(transform or IDENTITY),
    }


def _load(path):
    with path.open("rb") as stream:
        return py3d.P3D(stream)


def _pair(
    tmp_path,
    source_points,
    target_points=None,
    source_faces=((0, 1, 2),),
    target_faces=None,
    source_lods=None,
    target_lods=None,
):
    if target_points is None:
        target_points = source_points
    if target_faces is None:
        target_faces = source_faces
    if source_lods is None:
        source_lods = [make_lod(source_points, source_faces)]
    if target_lods is None:
        target_lods = [make_lod(target_points, target_faces)]
    source_path = save_model(tmp_path / "source.p3d", source_lods)
    target_path = save_model(tmp_path / "target.p3d", target_lods)
    return _load(source_path), _load(target_path)


def test_identity_and_cyclic_shift_preserve_pass(tmp_path):
    points = [(0, 0, 0), (2, 0, 0), (0, 1, 0)]
    source, target = _pair(
        tmp_path, points, target_faces=((1, 2, 0),)
    )
    assert check_winding(source, target, _winding()) == []


def test_rotation_translation_transform_preserves_relation(tmp_path):
    source_points = [(0, 0, 0), (2, 0, 0), (0, 1, 0)]
    target_points = [(3, -2, 1), (3, 0, 1), (2, -2, 1)]
    transform = [
        [0.0, -1.0, 0.0, 3.0],
        [1.0, 0.0, 0.0, -2.0],
        [0.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    source, target = _pair(
        tmp_path, source_points, target_points, target_faces=((2, 0, 1),)
    )
    assert check_winding(source, target, _winding(transform)) == []


def test_reflection_requires_reverse_cyclic_order(tmp_path):
    source_points = [(0, 0, 0), (2, 0, 0), (0, 1, 0)]
    target_points = [(0, 0, 0), (-2, 0, 0), (0, 1, 0)]
    reflection = [
        [-1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    source, target = _pair(
        tmp_path, source_points, target_points, target_faces=((0, 2, 1),)
    )
    assert check_winding(source, target, _winding(reflection)) == []


@pytest.mark.parametrize(
    ("transform", "target_face", "expected_relation"),
    [
        (IDENTITY, (0, 2, 1), "PRESERVE"),
        (
            [
                [-1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            (0, 1, 2),
            "REVERSE",
        ),
    ],
)
def test_wrong_preserve_or_reverse_relation_is_model_failure(
    tmp_path, transform, target_face, expected_relation
):
    source_points = [(0, 0, 0), (2, 0, 0), (0, 1, 0)]
    target_points = [
        (
            transform[0][0] * x + transform[0][1] * y + transform[0][3],
            transform[1][0] * x + transform[1][1] * y + transform[1][3],
            z,
        )
        for x, y, z in source_points
    ]
    source, target = _pair(
        tmp_path, source_points, target_points, target_faces=(target_face,)
    )
    findings = check_winding(source, target, _winding(transform))
    assert len(findings) == 1
    assert findings[0]["code"] == "PREFLIGHT_WINDING_RELATION_MISMATCH"
    assert findings[0]["expected"] == expected_relation
    assert findings[0]["lod_index"] == 0
    assert findings[0]["face_index"] == 0


def test_mixed_quad_order_is_relation_mismatch_not_geometry_repair(tmp_path):
    points = [(0, 0, 0), (2, 0, 0), (2, 1, 0), (0, 1, 0)]
    source, target = _pair(
        tmp_path,
        points,
        source_faces=((0, 1, 2, 3),),
        target_faces=((0, 2, 1, 3),),
    )
    findings = check_winding(source, target, _winding())
    assert [item["code"] for item in findings] == [
        "PREFLIGHT_WINDING_RELATION_MISMATCH"
    ]
    assert findings[0]["observed"] == "MIXED"


def test_geometry_mismatch_is_invalid_evidence(tmp_path):
    source, target = _pair(
        tmp_path,
        [(0, 0, 0), (2, 0, 0), (0, 1, 0)],
        [(0, 0, 0), (2, 0, 0), (0, 1.1, 0)],
    )
    with pytest.raises(PreflightError) as raised:
        check_winding(source, target, _winding(tolerance=1e-4))
    assert raised.value.code == "PREFLIGHT_WINDING_GEOMETRY_MISMATCH"


@pytest.mark.parametrize(
    "transform",
    [
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        [
            [math.nan, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        [
            [10 ** 1000, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0, 1.0],
        ],
    ],
)
def test_singular_nonfinite_or_nonaffine_transform_is_invalid(
    tmp_path, transform
):
    points = [(0, 0, 0), (2, 0, 0), (0, 1, 0)]
    source, target = _pair(tmp_path, points)
    with pytest.raises(PreflightError) as raised:
        check_winding(source, target, _winding(transform))
    assert raised.value.code == "PREFLIGHT_WINDING_TRANSFORM_INVALID"


def test_huge_position_tolerance_is_contract_invalid(tmp_path):
    points = [(0, 0, 0), (2, 0, 0), (0, 1, 0)]
    source, target = _pair(tmp_path, points)
    with pytest.raises(PreflightError) as raised:
        check_winding(source, target, _winding(tolerance=10 ** 1000))
    assert raised.value.code == "PREFLIGHT_CONTRACT_INVALID"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda winding: winding["faces"].append(
            copy.deepcopy(winding["faces"][0])
        ),
        lambda winding: winding["faces"][0]["source"].__setitem__(
            "face_index", 9
        ),
    ],
)
def test_duplicate_or_out_of_range_face_address_is_invalid(
    tmp_path, mutation
):
    points = [(0, 0, 0), (2, 0, 0), (0, 1, 0)]
    source, target = _pair(tmp_path, points)
    winding = _winding()
    mutation(winding)
    with pytest.raises(PreflightError) as raised:
        check_winding(source, target, winding)
    assert raised.value.code == "PREFLIGHT_WINDING_EVIDENCE_MISSING"


def test_uncovered_face_in_referenced_lod_is_invalid(tmp_path):
    points = [(0, 0, 0), (2, 0, 0), (0, 1, 0), (2, 1, 0)]
    faces = ((0, 1, 2), (1, 3, 2))
    source, target = _pair(
        tmp_path, points, source_faces=faces, target_faces=faces
    )
    with pytest.raises(PreflightError) as raised:
        check_winding(source, target, _winding())
    assert raised.value.code == "PREFLIGHT_WINDING_EVIDENCE_MISSING"


def test_triangle_to_quad_and_one_to_many_are_unsupported_splits(tmp_path):
    points = [(0, 0, 0), (2, 0, 0), (2, 1, 0), (0, 1, 0)]
    source, target = _pair(
        tmp_path,
        points,
        source_faces=((0, 1, 2),),
        target_faces=((0, 1, 2, 3),),
    )
    with pytest.raises(PreflightError) as raised:
        check_winding(source, target, _winding())
    assert raised.value.code == "PREFLIGHT_WINDING_UNSUPPORTED_SPLIT"

    source, target = _pair(
        tmp_path,
        points,
        source_faces=((0, 1, 2),),
        target_faces=((0, 1, 2), (0, 2, 3)),
    )
    winding = _winding(
        faces=[
            {
                "source": {"lod_index": 0, "face_index": 0},
                "target": {"lod_index": 0, "face_index": 0},
            },
            {
                "source": {"lod_index": 0, "face_index": 0},
                "target": {"lod_index": 0, "face_index": 1},
            },
        ]
    )
    with pytest.raises(PreflightError) as raised:
        check_winding(source, target, winding)
    assert raised.value.code == "PREFLIGHT_WINDING_UNSUPPORTED_SPLIT"


def test_missing_source_or_target_lod_is_a_model_finding(tmp_path):
    points = [(0, 0, 0), (2, 0, 0), (0, 1, 0)]
    source, target = _pair(tmp_path, points)
    winding = _winding()
    winding["faces"][0]["target"]["lod_index"] = 3
    findings = check_winding(source, target, winding)
    assert [item["code"] for item in findings] == [
        "PREFLIGHT_LOD_MISSING"
    ]
    assert findings[0]["lod_index"] == 3
