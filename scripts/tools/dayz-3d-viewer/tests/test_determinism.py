from dayz_3d_viewer import (
    extract_geometry_for_viewer,
    generate_viewer_html,
    p3d_to_glb,
    run_pipeline,
)

from _support import make_memory_lod, make_triangle_lod, save_model


def test_glb_and_html_are_byte_identical_across_runs(tmp_path):
    model = save_model(
        tmp_path / "tri.p3d",
        [
            make_triangle_lod(selections={"Component01": {"points": [0], "faces": [0]}}),
            make_memory_lod(),
        ],
    )
    first_glb = tmp_path / "a.glb"
    second_glb = tmp_path / "b.glb"
    p3d_to_glb(str(model), str(first_glb))
    p3d_to_glb(str(model), str(second_glb))
    assert first_glb.read_bytes() == second_glb.read_bytes()

    geo = extract_geometry_for_viewer(str(model))
    first_html = generate_viewer_html(
        model_name="Synthetic", mode="embedded", geometry_data=geo
    )
    second_html = generate_viewer_html(
        model_name="Synthetic", mode="embedded", geometry_data=geo
    )
    assert first_html == second_html
    assert "timestamp" not in first_html.lower()


def test_pipeline_embedded_is_deterministic(tmp_path):
    model = save_model(tmp_path / "tri.p3d", [make_triangle_lod()])
    first = tmp_path / "out1"
    second = tmp_path / "out2"
    run_pipeline(str(model), output_dir=str(first), model_name="tri", mode="embedded")
    run_pipeline(str(model), output_dir=str(second), model_name="tri", mode="embedded")
    assert (first / "tri.glb").read_bytes() == (second / "tri.glb").read_bytes()
    assert (first / "tri_viewer.html").read_bytes() == (
        second / "tri_viewer.html"
    ).read_bytes()
