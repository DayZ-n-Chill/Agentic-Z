"""The facenormals budget, and one negative per validate() finding code."""

import pytest

from builders import build_cube_p3d, build_multilod_p3d


def codes(findings):
    return [f.code for f in findings]


# ---- VAL-POS ----------------------------------------------------------------

def test_val_pos_clean_models(fork):
    """VAL-POS: modelos sanos -> 0 findings (ni WARN)."""
    assert build_cube_p3d(fork).validate() == []
    assert build_multilod_p3d(fork).validate() == []


# ---- one fixture per finding code ------------------------------------

def test_val_neg_selection_stale_replaced_list(fork):
    p3d = build_cube_p3d(fork)
    p3d.lods[0].points = list(p3d.lods[0].points)
    fs = p3d.validate()
    assert codes(fs) == ["ERR_SELECTION_STALE"]
    assert fs[0].severity == "ERROR" and fs[0].lod == 0


def test_val_neg_selection_stale_foreign_key(fork):
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    other = build_cube_p3d(fork).lods[0]
    sel = lod.new_selection("lf_foreign")
    sel.points[other.points[0]] = 1
    fs = p3d.validate()
    assert codes(fs) == ["ERR_SELECTION_STALE"]
    assert "lf_foreign" in fs[0].msg and "identity" in fs[0].msg


def test_val_neg_weight_range(fork):
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.selections["Component01"].faces[lod.faces[0]] = 1.5
    fs = p3d.validate()
    assert codes(fs) == ["ERR_WEIGHT_RANGE"]
    assert "Component01" in fs[0].msg and fs[0].lod == 0


def test_val_neg_property_truncation_fingerprint(fork):
    """Exactly 63 bytes is a WARN: the fingerprint of truncation by other
    tooling."""
    p3d = build_cube_p3d(fork)
    p3d.lods[0].properties["class"] = "v" * 63
    fs = p3d.validate()
    assert codes(fs) == ["WARN_PROPERTY_TRUNCATION"]
    assert fs[0].severity == "WARN"  # a WARN does not block the round trip


def test_val_neg_unreadable_roundtrip(fork, monkeypatch):
    """Perdida semantica inyectada -> ERR_UNREADABLE_ROUNDTRIP (no raise)."""
    p3d = build_cube_p3d(fork)
    orig = fork.Selection.write

    def lossy_write(self, f, name=None):
        emptied = fork.Selection(self.all_points, self.all_faces)
        return orig(emptied, f, name=name)

    monkeypatch.setattr(fork.Selection, "write", lossy_write)
    fs = p3d.validate()
    assert codes(fs) == ["ERR_UNREADABLE_ROUNDTRIP"]
    assert fs[0].lod is None and "membership" in fs[0].msg


# ---- NORMALS ---------------------------------------------------------

def test_normals_pos_at_budget_clean(fork):
    """Exactly 32768 facenormals produces no findings."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.facenormals += [(0.0, 0.0, 1.0)] * (32768 - len(lod.facenormals))
    assert lod.validate_normals_budget(lod_index=0) == []


def test_normals_neg_over_budget_warn_default(fork):
    """32769 produces WARN_NORMALS_BUDGET at severity WARN, not ERROR."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.facenormals += [(0.0, 0.0, 1.0)] * (32769 - len(lod.facenormals))
    fs = p3d.validate()
    assert codes(fs) == ["WARN_NORMALS_BUDGET"]
    assert fs[0].severity == "WARN" and "32769" in fs[0].msg


def test_normals_severity_configurable(fork):
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.facenormals += [(0.0, 0.0, 1.0)] * (32769 - len(lod.facenormals))
    fs = p3d.validate(normals_severity="ERROR")
    assert codes(fs) == ["WARN_NORMALS_BUDGET"] and fs[0].severity == "ERROR"
    with pytest.raises(ValueError):
        lod.validate_normals_budget(severity="FATAL")
