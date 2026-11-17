from dayz_3d_viewer import parse_rvmat


MINIMAL_RVMAT = """\
ambient[] = {0.5, 0.5, 0.5, 1};
diffuse[] = {0.2, 0.4, 0.8, 1};
forcedDiffuse[] = {0, 0, 0, 0};
specular[] = {0.1, 0.1, 0.1, 1};
emmisive[] = {0, 40, 0, 1};
specularPower = 60;
PixelShaderID = "Super";
VertexShaderID = "Super";
class Stage1
{
    texture = "mod\\data\\base_nohq.paa";
    uvSource = "tex";
};
class Stage2
{
    texture = "mod\\data\\base_co.paa";
    uvSource = "tex";
};
"""


def test_parse_minimal_rvmat(tmp_path):
    path = tmp_path / "housing.rvmat"
    path.write_text(MINIMAL_RVMAT, encoding="utf-8", newline="\n")
    parsed = parse_rvmat(str(path))
    assert parsed["name"] == "housing"
    assert parsed["file"] == str(path).replace("\\", "/")
    assert parsed["colors"]["diffuse"] == [0.2, 0.4, 0.8, 1.0]
    assert parsed["colors"]["emmisive"] == [0.0, 40.0, 0.0, 1.0]
    assert parsed["specular_power"] == 60.0
    assert parsed["pixel_shader"] == "Super"
    assert parsed["textures"]["normal"].replace("\\", "/").endswith("base_nohq.paa")
    assert parsed["textures"]["diffuse"].replace("\\", "/").endswith("base_co.paa")
    # is_emissive only inspects `emissive` / `forceddiffuse`, not the BI
    # `emmisive` spelling. The converter still reads `emmisive` for PBR.
    assert parsed["is_emissive"] is False
    assert len(parsed["stages"]) == 2

    emissive_only = tmp_path / "led.rvmat"
    emissive_only.write_text(
        "emissive[] = {0, 40, 0, 1};\n",
        encoding="utf-8",
        newline="\n",
    )
    assert parse_rvmat(str(emissive_only))["is_emissive"] is True
