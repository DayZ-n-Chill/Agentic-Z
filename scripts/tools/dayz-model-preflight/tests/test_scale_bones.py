import copy

import py3d

from dayz_model_preflight.findings import sort_findings
from dayz_model_preflight.runner import (
    check_scale_and_bones,
    collect_py3d_findings,
)

from _support import box_points, contract_value, make_lod, save_model


def _load(path):
    with path.open("rb") as stream:
        return py3d.P3D(stream)


def test_scale_uses_per_axis_bbox_dimensions_and_vector_tolerance(tmp_path):
    path = save_model(
        tmp_path / "target.p3d",
        [
            make_lod(
                box_points((2.005, 4.02, 5.99)),
                selections={"Pelvis": {"points": [0]}},
            )
        ],
    )
    contract = contract_value()
    contract["scale"]["tolerance_m"] = [0.01, 0.01, 0.02]
    findings = check_scale_and_bones(_load(path), contract)
    mismatch = [
        item for item in findings
        if item["code"] == "PREFLIGHT_SCALE_MISMATCH"
    ]
    assert len(mismatch) == 1
    assert mismatch[0]["lod_index"] == 0
    assert mismatch[0]["expected"] == [2.0, 4.0, 6.0]
    assert mismatch[0]["observed"] == [2.005, 4.02, 5.99]
    assert "4.020000" in mismatch[0]["message"]


def test_scale_within_scalar_tolerance_has_no_mismatch(tmp_path):
    path = save_model(
        tmp_path / "target.p3d",
        [
            make_lod(
                box_points((2.005, 4.005, 6.005)),
                selections={"Pelvis": {"faces": [0]}},
            )
        ],
    )
    contract = contract_value()
    contract["scale"]["tolerance_m"] = [0.01, 0.01, 0.01]
    assert not check_scale_and_bones(_load(path), contract)


def test_missing_contract_lod_is_a_model_finding(tmp_path):
    path = save_model(
        tmp_path / "target.p3d",
        [
            make_lod(
                box_points(), selections={"Pelvis": {"points": [0]}}
            )
        ],
    )
    contract = contract_value()
    contract["scale"]["lod_index"] = 3
    contract["bones"]["requirements"][0]["lod_index"] = 4
    findings = check_scale_and_bones(_load(path), contract)
    assert [item["code"] for item in findings] == [
        "PREFLIGHT_LOD_MISSING",
        "PREFLIGHT_LOD_MISSING",
    ]
    assert [item["lod_index"] for item in findings] == [3, 4]


def test_missing_selection_is_exact_case_and_unrelated_names_are_ignored(
    tmp_path
):
    path = save_model(
        tmp_path / "target.p3d",
        [
            make_lod(
                box_points(),
                selections={
                    "Pelvis": {"points": [0]},
                    "Unrelated": {},
                },
            )
        ],
    )
    contract = contract_value()
    contract["bones"]["requirements"][0]["selections"] = ["pelvis"]
    findings = check_scale_and_bones(_load(path), contract)
    assert len(findings) == 1
    assert findings[0]["code"] == "PREFLIGHT_BONE_SELECTION_MISSING"
    assert findings[0]["selection"] == "pelvis"


def test_empty_required_selection_is_distinct_from_missing(tmp_path):
    path = save_model(
        tmp_path / "target.p3d",
        [make_lod(box_points(), selections={"Pelvis": {}})],
    )
    findings = check_scale_and_bones(_load(path), contract_value())
    assert len(findings) == 1
    assert findings[0]["code"] == "PREFLIGHT_BONE_SELECTION_EMPTY"
    assert findings[0]["selection"] == "Pelvis"


def test_py3d_errors_keep_original_code_and_message(tmp_path):
    path = save_model(
        tmp_path / "target.p3d",
        [
            make_lod(
                box_points(),
                selections={"Pelvis": {"points": [0]}},
                masses=True,
            )
        ],
    )
    original = _load(path).validate()
    expected = next(
        item for item in original if item.code == "ERR_MASS_ONLY_GEOMETRY"
    )
    findings = collect_py3d_findings(_load(path))
    wrapped = next(
        item for item in findings
        if item["code"] == "PREFLIGHT_PY3D_ERROR"
    )
    assert wrapped["py3d_code"] == expected.code
    assert wrapped["message"] == expected.msg
    assert wrapped["severity"] == "ERROR"


def test_py3d_warnings_remain_visible_without_error_severity(tmp_path):
    path = save_model(
        tmp_path / "target.p3d",
        [
            make_lod(
                box_points(),
                selections={"Pelvis": {"points": [0]}},
                resolution=25000.0,
            )
        ],
    )
    findings = collect_py3d_findings(_load(path))
    warning = next(
        item for item in findings
        if item.get("py3d_code") == "WARN_LOD_KIND_UNKNOWN"
    )
    assert warning["code"] == "PREFLIGHT_PY3D_WARNING"
    assert warning["severity"] == "WARN"
    assert not any(item["severity"] == "ERROR" for item in findings)


def test_findings_sort_by_severity_code_lod_face_and_selection():
    findings = [
        {
            "code": "Z",
            "severity": "WARN",
            "message": "",
            "lod_index": None,
        },
        {
            "code": "B",
            "severity": "ERROR",
            "message": "",
            "lod_index": 1,
            "face_index": 2,
            "selection": "B",
        },
        {
            "code": "B",
            "severity": "ERROR",
            "message": "",
            "lod_index": 1,
            "face_index": 1,
            "selection": "A",
        },
        {
            "code": "A",
            "severity": "ERROR",
            "message": "",
            "lod_index": 9,
        },
    ]
    ordered = sort_findings(copy.deepcopy(findings))
    assert [
        (
            item["severity"],
            item["code"],
            item["lod_index"],
            item.get("face_index"),
            item.get("selection"),
        )
        for item in ordered
    ] == [
        ("ERROR", "A", 9, None, None),
        ("ERROR", "B", 1, 1, "A"),
        ("ERROR", "B", 1, 2, "B"),
        ("WARN", "Z", None, None, None),
    ]
