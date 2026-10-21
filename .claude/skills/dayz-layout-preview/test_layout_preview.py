"""Tests for layout_preview.py: parsing, box layout, findings and PNG output on vanilla style fixtures."""
import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
_SPEC = importlib.util.spec_from_file_location("layout_preview", HERE / "layout_preview.py")
lp = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = lp  # dataclasses look the module up while the class is built
_SPEC.loader.exec_module(lp)

VANILLA = Path("P:/gui/layouts")


def boxes(name, w=1920, h=1080, show_hidden=False):
    root = lp.parse((FIXTURES / name).read_text(encoding="utf-8"))
    return {b.widget.name: b for b in lp.layout(root, w, h, show_hidden=show_hidden)}


def rect(box):
    return (round(box.x, 2), round(box.y, 2), round(box.w, 2), round(box.h, 2))


# ------------------------------------------------------------------ parsing

def test_parse_tree_and_properties():
    root = lp.parse((FIXTURES / "hud_corner.layout").read_text(encoding="utf-8"))
    assert (root.cls, root.name) == ("FrameWidgetClass", "rootFrame")
    panel = root.children[0]
    assert [c.name for c in panel.children] == ["img_icon", "txt_status"]
    text = panel.children[1]
    assert text.word("text") == "Healthy"
    assert text.props['"text color"'] == ["1", "1", "1", "1"]
    assert text.num('"exact text size"') == 20


def test_parse_one_line_widgets():
    root = lp.parse((FIXTURES / "inline_row.layout").read_text(encoding="utf-8"))
    far = next(c for c in root.children if c.name == "txt_far")
    assert far.props == {
        "text": ['"Far"'], "halign": ["right_ref"], "size": ["300", "30"], "position": ["-100", "0"],
        "hexactpos": ["1"], "vexactpos": ["1"], "hexactsize": ["1"], "vexactsize": ["1"],
    }


@pytest.mark.parametrize("text, message", [
    ("<FrameWidget name='x'/>", "XML"),
    ("FrameWidgetClass root {\n size 1 1\n", "never closed"),
    ("FrameWidgetClass root {\n}\n}\n", "no open block"),
    ("// nothing here\n", "no root widget"),
])
def test_parse_rejects_broken_layouts(text, message):
    with pytest.raises(lp.LayoutError, match=message):
        lp.parse(text)


# ------------------------------------------------------------------- layout

def test_exact_boxes_anchor_to_right_and_bottom():
    b = boxes("hud_corner.layout")
    assert rect(b["rootFrame"]) == (0, 0, 1920, 1080)
    assert rect(b["panel_status"]) == (1576, 936, 320, 120)
    assert rect(b["img_icon"]) == (1586, 964, 64, 64)  # centered vertically in the panel
    assert rect(b["txt_status"]) == (1660, 972, 160, 48)  # relative size of a pixel panel
    assert rect(b["panel_topbar"]) == (0, 0, 1920, 40)


def test_relative_sizes_follow_the_screen_and_exact_sizes_do_not():
    small, wide = boxes("hud_corner.layout", 1280, 720), boxes("hud_corner.layout", 3440, 1440)
    assert rect(small["panel_topbar"])[2:] == (1280, 40)
    assert rect(wide["panel_topbar"])[2:] == (3440, 40)
    assert rect(small["panel_status"]) == (1280 - 344, 720 - 144, 320, 120)
    assert rect(wide["panel_status"]) == (3440 - 344, 1440 - 144, 320, 120)


def test_grid_spacer_cells_and_hidden_children():
    b = boxes("menu_dialog.layout")
    assert rect(b["grid_buttons"]) == (760, 390, 400, 300)
    assert rect(b["btn_play"]) == (770, 400, 185, 135)  # its own position is ignored in a grid
    assert rect(b["btn_options"]) == (965, 400, 185, 135)  # the hidden button takes no cell
    assert rect(b["btn_quit"]) == (770, 578.75, 185, 67.5)
    assert "btn_secret" not in b
    shown = boxes("menu_dialog.layout", show_hidden=True)
    assert shown["btn_secret"].hidden and not shown["btn_play"].hidden


def test_scaled_grows_exact_values_with_screen_height():
    b = boxes("menu_dialog.layout", 2560, 1440)
    k = 1440 / lp.SCALE_REF_HEIGHT
    assert rect(b["grid_buttons"]) == (round((2560 - 400 * k) / 2, 2), 520, round(400 * k, 2), 400)


def test_wrap_spacer_flows_and_wraps():
    b = boxes("inline_row.layout")
    assert rect(b["img_slot0"]) == (0, 0, 100, 50)
    assert rect(b["img_slot1"]) == (110, 0, 100, 50)
    assert rect(b["img_slot2"]) == (0, 60, 100, 50)


# ----------------------------------------------------------------- findings

def test_findings_name_off_screen_and_missing_toggles():
    report = lp.preview(FIXTURES / "inline_row.layout", lp.DEFAULT_SIZES, None)
    by_rule = {f["rule"]: f for f in report["findings"]}
    assert by_rule["off-screen"]["widget"] == "txt_far"
    assert by_rule["off-screen"]["sizes"] == ["1280x720", "1920x1080", "2560x1440", "3440x1440"]
    assert by_rule["missing-toggle"]["widget"] == "panel_loose"
    assert "png" not in report["sizes"][0]


def test_clean_fixture_has_no_findings():
    assert lp.preview(FIXTURES / "hud_corner.layout", lp.DEFAULT_SIZES, None)["findings"] == []


# ---------------------------------------------------------------- rendering

def test_cli_writes_one_png_per_size(tmp_path, capsys):
    pytest.importorskip("PIL")
    from PIL import Image

    layouts = [str(FIXTURES / n) for n in ("hud_corner.layout", "menu_dialog.layout", "inline_row.layout")]
    assert lp.main(layouts + ["--out", str(tmp_path)]) == 0
    for name in ("hud_corner", "menu_dialog", "inline_row"):
        for w, h in lp.DEFAULT_SIZES:
            with Image.open(tmp_path / f"{name}_{w}x{h}.png") as img:
                assert img.size == (w, h)
    out = capsys.readouterr().out
    assert "[WARN] inline_row.layout:" in out and "off-screen" in out


def test_render_fills_panels_with_their_color(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    lp.main([str(FIXTURES / "hud_corner.layout"), "--out", str(tmp_path), "--sizes", "1920x1080", "--no-labels"])
    with Image.open(tmp_path / "hud_corner_1920x1080.png") as img:
        background, topbar = img.getpixel((960, 540)), img.getpixel((960, 20))
    assert background == (28, 30, 34)
    assert topbar != background


def test_cli_reports_broken_and_missing_files(tmp_path, capsys):
    pytest.importorskip("PIL")
    broken = tmp_path / "broken.layout"
    broken.write_text("FrameWidgetClass root {\n", encoding="utf-8")
    assert lp.main([str(broken), str(tmp_path / "nope.layout"), "--out", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "never closed" in out and "no such file" in out


def test_sizes_argument():
    assert lp.parse_sizes("1280x720, 3440X1440") == [(1280, 720), (3440, 1440)]
    with pytest.raises(Exception):
        lp.parse_sizes("1920by1080")


@pytest.mark.skipif(not VANILLA.is_dir(), reason="vanilla layouts on P: not available")
def test_every_vanilla_layout_parses_and_lays_out():
    for path in sorted(VANILLA.rglob("*.layout")):
        root = lp.parse(path.read_text(encoding="utf-8", errors="replace"))
        assert lp.layout(root, 1920, 1080, show_hidden=True), path
