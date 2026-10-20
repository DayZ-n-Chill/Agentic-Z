"""Tests for the atlas packing logic in build_imageset.py (no Pillow or DayZ Tools needed)."""
import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "build_imageset", Path(__file__).with_name("build_imageset.py")
)
bi = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bi)

GAP = bi.GAP


def _sprites(n, w, h):
    return [(Path(f"s{i}.png"), w, h) for i in range(n)]


def _is_pot(n):
    return n > 0 and n & (n - 1) == 0


def _assert_valid_layout(dims, placed, gap=GAP):
    atlas_w, atlas_h = dims
    assert _is_pot(atlas_w) and _is_pot(atlas_h)
    boxes = []
    for _, w, h, x, y in placed:
        # gutter on every side, inside the atlas
        assert x >= gap and y >= gap
        assert x + w + gap <= atlas_w and y + h + gap <= atlas_h
        boxes.append((x - gap, y - gap, x + w + gap, y + h + gap))
    # sprites (without gutter) never overlap and are at least `gap` apart
    for i, a in enumerate(placed):
        for b in placed[i + 1:]:
            _, aw, ah, ax, ay = a
            _, bw, bh, bx, by = b
            apart_x = ax + aw + gap <= bx or bx + bw + gap <= ax
            apart_y = ay + ah + gap <= by or by + bh + gap <= ay
            assert apart_x or apart_y


def test_shelf_pack_single_sprite_uses_smallest_atlas():
    dims, placed = bi.shelf_pack(_sprites(1, 64, 64))
    assert dims == (256, 256)
    assert placed[0][3:] == (GAP, GAP)


def test_shelf_pack_gutter_and_power_of_two():
    sprites = _sprites(20, 100, 60) + _sprites(5, 200, 130)
    dims, placed = bi.shelf_pack(sprites)
    assert len(placed) == len(sprites)
    _assert_valid_layout(dims, placed)


def test_shelf_pack_allows_rectangular_atlas():
    # Two 236-wide sprites stacked fit 256x512 exactly; that beats 512x512 on area.
    dims, placed = bi.shelf_pack(_sprites(2, 236, 236))
    assert dims in ((256, 512), (512, 256))
    _assert_valid_layout(dims, placed)


def test_shelf_pack_sprite_exactly_filling_atlas_with_gutter():
    dims, _ = bi.shelf_pack(_sprites(1, 256 - 2 * GAP, 256 - 2 * GAP))
    assert dims == (256, 256)
    dims, _ = bi.shelf_pack(_sprites(1, 256 - 2 * GAP + 1, 10))
    assert dims[0] == 512


def test_shelf_pack_returns_none_when_nothing_fits():
    assert bi.shelf_pack(_sprites(1, 4096, 10)) == (None, None)


def test_pack_split_single_atlas_when_it_fits():
    atlases = bi.pack_split(_sprites(4, 64, 64))
    assert len(atlases) == 1


def test_pack_split_spreads_over_several_atlases():
    # Each 2000x2000 sprite + gutter needs its own quadrant; 5 can't share one 4096 atlas.
    sprites = _sprites(5, 2000, 2000)
    atlases = bi.pack_split(sprites)
    assert len(atlases) == 2
    assert sum(len(placed) for _, placed in atlases) == 5
    for dims, placed in atlases:
        _assert_valid_layout(dims, placed)


@pytest.mark.parametrize("w,h", [(4096, 64), (64, 4096), (4096 - 2 * GAP + 1, 10)])
def test_pack_split_refuses_oversize_sprite(w, h):
    # Oversize sprite mixed with normal ones, in any position after sorting.
    sprites = _sprites(3, 128, 128) + [(Path("huge.png"), w, h)]
    assert bi.pack_split(sprites) is None


def test_write_imageset_file_format(tmp_path):
    out = tmp_path / "icons.imageset"
    placed = [(Path("hud_health.png"), 64, 32, 10, 10)]
    bi.write_imageset_file(out, "icons", 256, 256, "MyMod\\gui\\imagesets\\icons.paa", placed)
    text = out.read_text(encoding="utf-8")
    assert 'path "MyMod\\gui\\imagesets\\icons.paa"' in text
    assert "ImageSetDefClass hud_health {" in text
    assert "Pos 10 10" in text and "Size 64 32" in text


def test_missing_pillow_exits_nonzero_with_hint(monkeypatch, tmp_path):
    monkeypatch.setattr(bi, "Image", None)
    monkeypatch.setattr("sys.argv", ["build_imageset.py", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        bi.main()
    assert "pip install -r" in str(exc.value)
