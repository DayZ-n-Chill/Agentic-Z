from dayz_3d_viewer import (
    extract_geometry_for_viewer,
    generate_viewer_html,
    p3d_to_glb,
)
from dayz_3d_viewer.viewer_template import THREE_CDN, THREE_JS_VERSION

from _support import make_triangle_lod, save_model


def test_embedded_html_contains_geometry_and_no_host_paths(tmp_path):
    model = save_model(tmp_path / "tri.p3d", [make_triangle_lod()])
    geo = extract_geometry_for_viewer(str(model))
    assert len(geo["positions"]) == 3
    html_path = tmp_path / "viewer.html"
    html = generate_viewer_html(
        model_name="Synthetic Tri",
        mode="embedded",
        geometry_data=geo,
        output_path=str(html_path),
    )
    text = html_path.read_text(encoding="utf-8")
    assert text == html
    assert "const M=" in text
    assert THREE_JS_VERSION in text
    assert THREE_CDN in text
    assert "Synthetic Tri" in text
    assert str(tmp_path) not in text
    assert str(tmp_path).replace("\\", "/") not in text
    assert "C:\\Users" not in text
    assert "C:/Users" not in text
    assert html_path.read_bytes().count(b"\r\n") == 0


def test_web_html_links_relative_glb(tmp_path):
    model = save_model(tmp_path / "tri.p3d", [make_triangle_lod()])
    glb = tmp_path / "tri.glb"
    p3d_to_glb(str(model), str(glb))
    html_path = tmp_path / "web.html"
    generate_viewer_html(
        model_name="Web Tri",
        mode="web",
        glb_url="tri.glb",
        output_path=str(html_path),
    )
    text = html_path.read_text(encoding="utf-8")
    assert "tri.glb" in text
    assert "GLTFLoader" in text
    assert str(tmp_path) not in text
    assert str(glb) not in text
    assert "C:\\Users" not in text
