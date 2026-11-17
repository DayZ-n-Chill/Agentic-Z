"""Tests for rvmat_lint.py and rvmat_template.py (next to this file). Standard library only.

Run: python -m pytest skills/dayz-texture-pipeline/scripts -q
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rvmat_lint  # noqa: E402
import rvmat_template  # noqa: E402

CALM_WATER_STUB = 'PixelShaderID="CalmWater";\nVertexShaderID="CalmWater";\n'


def _codes(findings):
    return {item.code for item in findings}


def test_built_in_self_tests_pass(capsys):
    assert rvmat_lint.main(["--self-test"]) == 0
    assert rvmat_template.main(["--self-test"]) == 0
    assert capsys.readouterr().out.splitlines() == ["self-test passed", "matpbr self-test passed", "self-test passed"]


def test_every_template_kind_lints_without_errors(tmp_path):
    # A generated template must not trip the linter that the skill runs on it next.
    for kind in ("super", "damage", "emissive", "multi"):
        out = tmp_path / f"{kind}_damage.rvmat" if kind == "damage" else tmp_path / f"{kind}.rvmat"
        assert rvmat_template.main([kind, "--prefix", r"mymod\data\thing", "--output", str(out)]) == 0
        findings = rvmat_lint.lint_file(out, None)
        assert not [f for f in findings if f.severity == "ERROR"], (kind, findings)
    pen = tmp_path / "pen.rvmat"
    assert rvmat_template.main(["penetration", "--output", str(pen)]) == 0
    assert rvmat_lint.lint_file(pen, None) == []


def test_damage_template_carries_the_overlay_and_passes_the_damage_check(tmp_path):
    out = tmp_path / "thing_damage.rvmat"
    rvmat_template.main(["damage", "--prefix", r"mymod\data\thing", "--output", str(out)])
    text = out.read_text(encoding="utf-8")
    assert r'texture="dz\weapons\data\weapons_damage_generic_mc.paa";' in text
    assert "aside[]={4,0,0}; up[]={0,4,0};" in text
    assert "DAMAGE_STAGE3_PROCEDURAL" not in _codes(rvmat_lint.lint_file(out, None))


def test_a_procedural_stage3_in_a_damage_material_is_a_warning(tmp_path):
    out = tmp_path / "thing_damage.rvmat"
    out.write_text(rvmat_template.render_super(r"mymod\data\thing"), encoding="utf-8")
    assert "DAMAGE_STAGE3_PROCEDURAL" in _codes(rvmat_lint.lint_file(out, None))


def test_source_extension_absolute_path_and_forward_slash_are_reported():
    text = (
        'PixelShaderID="Super";\nVertexShaderID="Super";\n'
        'class Stage1 { texture="C:\\art\\thing_nohq.png"; };\n'
        'class Stage5 { texture="mymod/data/thing_smdi.paa"; };\n'
    )
    found = rvmat_lint.lint_text(text, "thing.rvmat")
    assert {"ABSOLUTE_TEXTURE_PATH", "SOURCE_TEXTURE_EXT", "FORWARD_SLASH_PATH"} <= _codes(found)
    assert {f.line for f in found if f.code == "FORWARD_SLASH_PATH"} == {4}


def test_texture_existence_is_checked_under_the_given_root(tmp_path):
    (tmp_path / "mymod" / "data").mkdir(parents=True)
    (tmp_path / "mymod" / "data" / "thing_nohq.paa").write_bytes(b"")
    text = (
        'PixelShaderID="Super";\nVertexShaderID="Super";\n'
        'class Stage1 { texture="mymod\\data\\thing_nohq.paa"; };\n'
        'class Stage5 { texture="mymod\\data\\thing_smdi.paa"; };\n'
        'class Stage7 { texture="#(argb,8,8,3)color(0,0,0,1,CO)"; };\n'
    )
    missing = [f for f in rvmat_lint.lint_text(text, "thing.rvmat", tmp_path) if f.code == "TEXTURE_NOT_FOUND"]
    assert len(missing) == 1 and "thing_smdi.paa" in missing[0].message


def test_a_missing_root_is_an_error_not_a_list_of_missing_textures(tmp_path, capsys):
    rvmat = tmp_path / "thing.rvmat"
    rvmat.write_text(rvmat_template.render_super(r"mymod\data\thing"), encoding="utf-8")
    assert rvmat_lint.main([str(rvmat), "--pdrive-root", str(tmp_path / "not_mounted")]) == 2
    captured = capsys.readouterr()
    assert "is not a folder" in captured.err and captured.out == ""


def test_vanilla_water_pairing_gets_no_finding(tmp_path):
    # P:\DZ\water_bliss\ponds\data\enoch_pond.rvmat is these two lines, next to an .emat
    # that holds MatWaterPool { ... }: a valid vanilla pair that is not MatPBR.
    rvmat = tmp_path / "enoch_pond.rvmat"
    rvmat.write_text(CALM_WATER_STUB, encoding="utf-8")
    (tmp_path / "enoch_pond.emat").write_text("MatWaterPool {\n Color 0.0392 0.0549 0.0667 0.3725\n ZWrite 0\n}\n", encoding="utf-8")
    assert rvmat_lint.lint_file(rvmat, None) == []


def test_an_emat_with_neither_material_class_is_still_reported(tmp_path):
    rvmat = tmp_path / "thing.rvmat"
    rvmat.write_text(CALM_WATER_STUB, encoding="utf-8")
    (tmp_path / "thing.emat").write_text("SomethingElse {\n}\n", encoding="utf-8")
    assert _codes(rvmat_lint.lint_file(rvmat, None)) == {"MATPBR_BLOCK_MISSING"}


def test_json_output_and_exit_codes(tmp_path, capsys):
    good = tmp_path / "good.rvmat"
    good.write_text(rvmat_template.render_super(r"mymod\data\thing"), encoding="utf-8")
    assert rvmat_lint.main([str(good)]) == 0
    assert capsys.readouterr().out.strip() == "No findings."

    bad = tmp_path / "bad.rvmat"
    bad.write_text('PixelShaderID="Multi";\nVertexShaderID="Super";\n', encoding="utf-8")
    assert rvmat_lint.main([str(bad), "--json"]) == 1
    codes = {item["code"] for item in json.loads(capsys.readouterr().out)}
    assert "MULTI_SHADER_MISMATCH" in codes and "MULTI_MISSING_BASE_STAGE" in codes

    warn_only = tmp_path / "warn.rvmat"
    warn_only.write_text('PixelShaderID="Super";\nVertexShaderID="Super";\n', encoding="utf-8")
    assert rvmat_lint.main([str(warn_only)]) == 0
    assert rvmat_lint.main([str(warn_only), "--warnings-as-errors"]) == 1
    assert rvmat_lint.main([str(tmp_path / "gone.rvmat")]) == 1
