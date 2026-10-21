"""Tests for the atlas packing logic in build_imageset.py (no Pillow or DayZ Tools needed)."""
import importlib.util
import os
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
    monkeypatch.setattr(bi.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(bi, "Image", None)
    monkeypatch.setattr("sys.argv", ["build_imageset.py", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        bi.main()
    assert "pip install -r" in str(exc.value)


def _touch_outputs(out_dir, *stems):
    out_dir.mkdir(parents=True, exist_ok=True)
    for stem in stems:
        for ext in (".paa", ".imageset"):
            (out_dir / f"{stem}{ext}").write_text("x", encoding="utf-8")


def test_remove_stale_outputs_single_atlas_drops_old_parts(tmp_path):
    _touch_outputs(tmp_path, "icons", "icons_1", "icons_2", "other")
    removed = bi.remove_stale_outputs(tmp_path, "icons", 1)
    assert sorted(p.name for p in removed) == [
        "icons_1.imageset", "icons_1.paa", "icons_2.imageset", "icons_2.paa",
    ]
    assert (tmp_path / "icons.paa").exists() and (tmp_path / "other.paa").exists()


def test_remove_stale_outputs_split_drops_unsplit_and_extra_parts(tmp_path):
    _touch_outputs(tmp_path, "icons", "icons_1", "icons_2", "icons_3")
    bi.remove_stale_outputs(tmp_path, "icons", 2)
    left = sorted(p.stem for p in tmp_path.iterdir())
    assert left == ["icons_1", "icons_1", "icons_2", "icons_2"]


def test_remove_stale_outputs_spares_other_sets_and_lookalikes(tmp_path):
    _touch_outputs(tmp_path, "icons_2", "icons_extra", "icons_1")
    bi.remove_stale_outputs(tmp_path, "icons", 1, frozenset({"icons_2"}))
    left = {p.stem for p in tmp_path.iterdir()}
    assert left == {"icons_2", "icons_extra"}


def test_remove_stale_outputs_missing_dir(tmp_path):
    assert bi.remove_stale_outputs(tmp_path / "nope", "icons", 1) == []


def test_resolve_image_to_paa_uses_shared_preflight(monkeypatch, tmp_path):
    exe = tmp_path / "Bin" / "ImageToPAA" / "ImageToPAA.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")

    class FakePreflight:
        @staticmethod
        def find_dayz_tools():
            return tmp_path

    monkeypatch.setattr(bi.h, "preflight", FakePreflight, raising=False)
    assert bi.resolve_image_to_paa() == exe


def test_no_local_preflight_copies():
    assert not hasattr(bi, "gate_on_preflight")
    assert not hasattr(bi, "_load_preflight_module")


def test_preflight_gate_runs_before_any_other_check(monkeypatch, tmp_path):
    def gate():
        raise SystemExit(7)

    monkeypatch.setattr(bi.h, "gate_on_preflight", gate)
    monkeypatch.setattr(bi, "Image", None)  # would fail next if the gate passed
    monkeypatch.setattr("sys.argv", ["build_imageset.py", str(tmp_path / "missing")])
    with pytest.raises(SystemExit) as exc:
        bi.main()
    assert exc.value.code == 7


@pytest.mark.parametrize("name", ["hud health.png", "2icon.png", "hud-health.png", "icône.png"])
def test_bad_sprite_names_flagged(name):
    assert bi.bad_sprite_names([Path(name), Path("hud_ok.png")]) == [name]


def test_build_one_rejects_bad_sprite_name_before_reading_images(tmp_path, capsys):
    set_dir = tmp_path / "icons"
    set_dir.mkdir()
    (set_dir / "hud health.png").write_bytes(b"not read")
    (set_dir / "hud_ok.png").write_bytes(b"not read")
    assert bi.build_one(set_dir, "MyMod", tmp_path / "out", Path("ImageToPAA.exe")) is False
    err = capsys.readouterr().err
    assert "hud health.png" in err and "hud_ok.png" not in err
    assert not (tmp_path / "out").exists()


def test_build_pbo_excludes_gui_sources():
    """SKILL.md promises the source PNGs stay out of the PBO; /dayz-build-pbo's exclude.lst does that."""
    exclude = Path(__file__).resolve().parents[1] / "dayz-build-pbo" / "exclude.lst"
    patterns = [l.strip() for l in exclude.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith(";")]
    assert any(p.startswith(".gui-sources") for p in patterns)
    assert any(".gui-sources" in p and p.startswith("*") for p in patterns)


def test_build_one_empty_set_clears_its_outputs(tmp_path):
    set_dir = tmp_path / ".gui-sources" / "icons"
    set_dir.mkdir(parents=True)
    out_dir = tmp_path / "gui" / "imagesets"
    _touch_outputs(out_dir, "icons", "icons_1", "other")
    assert bi.build_one(set_dir, "MyMod", out_dir, Path("ImageToPAA.exe"), frozenset({"other"}))
    assert sorted(p.name for p in out_dir.iterdir()) == ["other.imageset", "other.paa"]


class _FakeAtlas:
    def paste(self, *a):
        pass

    def save(self, path, fmt):
        Path(path).write_bytes(b"png")


class _FakeImage:
    @staticmethod
    def new(mode, size, color):
        return _FakeAtlas()


def _convert(monkeypatch, tmp_path, writes):
    """Run write_one_atlas with ImageToPAA faked to exit 0 and write the .paa only if `writes`."""
    monkeypatch.setattr(bi, "Image", _FakeImage)

    def fake_run(cmd):
        if writes:
            Path(cmd[2]).write_bytes(b"new paa")
        return bi.subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(bi.subprocess, "run", fake_run)
    return bi.write_one_atlas("icons", 256, 256, [], "MyMod", tmp_path, Path("ImageToPAA.exe"))


def _age(path):
    """Backdate `path` one minute, like a .paa left by an earlier run."""
    old = path.stat().st_mtime_ns - 60_000_000_000
    os.utime(path, ns=(old, old))


def test_write_one_atlas_rejects_paa_left_from_earlier_run(monkeypatch, tmp_path, capsys):
    stale = tmp_path / "icons.paa"
    stale.write_bytes(b"old paa")
    _age(stale)
    assert _convert(monkeypatch, tmp_path, writes=False) is False
    assert "did not rewrite icons.paa" in capsys.readouterr().err
    assert not (tmp_path / "icons.imageset").exists()


def test_write_one_atlas_accepts_rewritten_paa(monkeypatch, tmp_path):
    stale = tmp_path / "icons.paa"
    stale.write_bytes(b"old paa")
    _age(stale)
    assert _convert(monkeypatch, tmp_path, writes=True) is True
    assert (tmp_path / "icons.imageset").is_file()


def _split_set(monkeypatch, tmp_path, convert_ok):
    """A set that packs into two atlases, with a single-atlas output left from an earlier run."""
    set_dir = tmp_path / ".gui-sources" / "icons"
    set_dir.mkdir(parents=True)
    (set_dir / "a.png").write_bytes(b"x")
    out_dir = tmp_path / "gui" / "imagesets"
    _touch_outputs(out_dir, "icons")

    class _Img:
        width = height = 64

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(bi, "Image", type("I", (), {"open": staticmethod(lambda p: _Img())}))
    monkeypatch.setattr(bi, "pack_split", lambda metas: [((256, 256), []), ((256, 256), [])])
    monkeypatch.setattr(bi, "write_one_atlas", lambda stem, *a: convert_ok)
    return bi.build_one(set_dir, "MyMod", out_dir, Path("ImageToPAA.exe")), out_dir


def test_build_one_keeps_old_outputs_when_conversion_fails(monkeypatch, tmp_path):
    ok, out_dir = _split_set(monkeypatch, tmp_path, convert_ok=False)
    assert ok is False
    assert (out_dir / "icons.paa").is_file() and (out_dir / "icons.imageset").is_file()


def test_build_one_removes_old_outputs_after_success(monkeypatch, tmp_path):
    ok, out_dir = _split_set(monkeypatch, tmp_path, convert_ok=True)
    assert ok is True
    assert not (out_dir / "icons.paa").exists()


def test_install_hint_uses_py_launcher():
    """.claude/settings.json denies `python -m`, so the hint must use `py -m pip`."""
    here = Path(__file__).resolve().parent
    for text in ((here / "SKILL.md").read_text(encoding="utf-8"),
                 (here / "build_imageset.py").read_text(encoding="utf-8")):
        assert "python -m pip" not in text
        assert "py -m pip install -r" in text
