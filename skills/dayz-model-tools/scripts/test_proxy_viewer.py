#!/usr/bin/env python3
"""Tests for proxy_viewer: finding viewer_core.py and writing the editor page.

Run: python -m pytest skills/dayz-model-tools/scripts/test_proxy_viewer.py, or python test_proxy_viewer.py.
The page test skips when viewer_core.py is not in the checkout; it ships with the
3D viewer tool under scripts/tools/dayz-3d-viewer.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proxy_viewer  # noqa: E402

RECIPE = {
    "model": "host.p3d",
    "lod0_index": 0,
    "body": {"positions": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "faces": [[0, 1, 2]]},
    "bbox": {"min": [0, 0, 0], "max": [1, 1, 0]},
    "proxies": [{
        "name": "proxy:\\dz\\characters\\proxies\\vest_dz.001",
        "slot": "Vest",
        "lod": 0,
        "point_indices": [3, 4, 5],
        "triangle": [[0, 1, 0], [0, 1.001, 0], [0, 1, 0.002]],
        "origin": [0, 1, 0],
        "ref_model": "\\dz\\characters\\proxies\\vest_dz",
        "frame": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "ambiguous": False,
        "angles_deg": [90.0, 63.43, 26.57],
    }],
}

FAKE_CORE = '''VIEWER_CORE_CONTRACT = "dayz-viewer-core/1"
THREE_VERSION = "{version}"
def importmap_script(): return "IMPORTMAP"
def module_imports(addons=(), three_alias="THREE"): return "IMPORTS"
def boot_js(**kwargs): return "BOOT"
def transform_controls_js(**kwargs): return "GIZMO"
'''


def test_repo_paths_name_the_tool_copy_first():
    repo = Path(__file__).resolve().parents[3]
    assert proxy_viewer.VIEWER_CORE_PATHS[0] == (
        repo / "scripts" / "tools" / "dayz-3d-viewer" / "dayz_3d_viewer" / "viewer_core.py"
    )


def test_missing_viewer_core_names_the_paths_it_tried(tmp_path):
    missing = tmp_path / "viewer_core.py"
    with pytest.raises(ImportError, match="viewer_core.py") as caught:
        proxy_viewer.load_viewer_core((missing,))
    assert str(missing) in str(caught.value)


def test_viewer_core_with_another_three_version_is_refused(tmp_path):
    stale = tmp_path / "viewer_core.py"
    stale.write_text(FAKE_CORE.format(version="0.160.0"), encoding="utf-8")
    with pytest.raises(ImportError):
        proxy_viewer.load_viewer_core((stale,))


def test_second_path_is_used_when_the_first_is_missing(tmp_path):
    good = tmp_path / "shared" / "viewer_core.py"
    good.parent.mkdir()
    good.write_text(FAKE_CORE.format(version=proxy_viewer.THREE_VERSION), encoding="utf-8")
    core = proxy_viewer.load_viewer_core((tmp_path / "tool" / "viewer_core.py", good))
    assert core.importmap_script() == "IMPORTMAP"


def test_page_embeds_the_recipe_and_has_an_english_ui(tmp_path):
    if not any(path.is_file() for path in proxy_viewer.VIEWER_CORE_PATHS):
        pytest.skip("viewer_core.py is not in this checkout (scripts/tools/dayz-3d-viewer)")
    recipe = tmp_path / "recipe.json"
    recipe.write_text(json.dumps(RECIPE), encoding="utf-8")
    out = tmp_path / "viewer.html"

    proxy_viewer.generate(str(recipe), str(out))

    html = out.read_text(encoding="utf-8")
    assert "const R = " + json.dumps(RECIPE) in html
    assert "three@" + proxy_viewer.THREE_VERSION in html
    assert "TransformControls" in html
    for label in ("Move (W)", "Rotate (E)", "Final result", "Worn ref", "Export edits", "No selection"):
        assert label in html, label
    for placeholder in ("__RECIPE__", "__MODEL__", "__VC_IMPORTMAP__", "__VC_IMPORTS__", "__VC_BOOT__", "__VC_GIZMO__"):
        assert placeholder not in html, placeholder


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
