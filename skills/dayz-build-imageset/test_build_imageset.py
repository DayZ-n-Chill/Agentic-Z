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


class _ReadableImg:
    width = height = 64

    def __init__(self, fail_on_load=False):
        self.fail_on_load = fail_on_load

    def load(self):
        if self.fail_on_load:
            raise OSError("image file is truncated")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _UnidentifiedImageError(OSError):
    """Stands in for PIL.UnidentifiedImageError, which subclasses OSError."""


def _fake_open(path):
    if path.name == "empty.png":
        raise _UnidentifiedImageError(f"cannot identify image file '{path}'")
    return _ReadableImg(fail_on_load=path.name == "cut.png")


def test_build_one_fails_set_naming_unreadable_pngs(monkeypatch, tmp_path, capsys):
    set_dir = tmp_path / ".gui-sources" / "icons"
    set_dir.mkdir(parents=True)
    (set_dir / "empty.png").write_bytes(b"")
    (set_dir / "cut.png").write_bytes(b"x")
    (set_dir / "hud_ok.png").write_bytes(b"x")
    out_dir = tmp_path / "gui" / "imagesets"
    _touch_outputs(out_dir, "icons")
    monkeypatch.setattr(bi, "Image", type("I", (), {"open": staticmethod(_fake_open)}))
    monkeypatch.setattr(bi, "write_one_atlas", lambda *a: pytest.fail("must not convert"))

    assert bi.build_one(set_dir, "MyMod", out_dir, Path("ImageToPAA.exe")) is False
    err = capsys.readouterr().err
    assert "[FAIL]" in err and "empty.png" in err and "cut.png" in err
    assert "hud_ok.png" not in err
    # Earlier good outputs stay in place.
    assert (out_dir / "icons.paa").is_file() and (out_dir / "icons.imageset").is_file()


def test_main_builds_remaining_sets_after_unreadable_png(monkeypatch, tmp_path, capsys):
    mod = tmp_path / "MyMod"
    for name, files in (("a_bad", ["empty.png"]), ("b_good", ["hud_ok.png"])):
        d = mod / ".gui-sources" / name
        d.mkdir(parents=True)
        for f in files:
            (d / f).write_bytes(b"" if f == "empty.png" else b"x")
    built = []
    monkeypatch.setattr(bi.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(bi, "Image", type("I", (), {"open": staticmethod(_fake_open)}))
    monkeypatch.setattr(bi, "resolve_image_to_paa", lambda: Path("ImageToPAA.exe"))
    monkeypatch.setattr(bi, "write_one_atlas", lambda stem, *a: built.append(stem) or True)
    monkeypatch.setattr("sys.argv", ["build_imageset.py", str(mod), "--mod-name", "MyMod"])

    assert bi.main() == 1
    assert built == ["b_good"]
    assert "1 of 2 imagesets built." in capsys.readouterr().out


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


class _Sprite:
    width = height = 64

    def load(self):
        pass

    def convert(self, mode):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakePillow(_FakeImage):
    @staticmethod
    def open(path):
        return _Sprite()


def _real_build(monkeypatch, tmp_path, fake_run, parts=1, old_stems=("icons",), set_name="icons"):
    """build_one with the real write_one_atlas and staging, ImageToPAA faked by `fake_run`.

    `parts` > 1 makes pack_split return that many atlases. Every stem in
    `old_stems` gets a .paa and .imageset holding b"old" from an earlier run.
    """
    set_dir = tmp_path / ".gui-sources" / set_name
    set_dir.mkdir(parents=True)
    (set_dir / "a.png").write_bytes(b"x")
    out_dir = tmp_path / "gui" / "imagesets"
    out_dir.mkdir(parents=True)
    for stem in old_stems:
        for ext in (".paa", ".imageset"):
            (out_dir / f"{stem}{ext}").write_bytes(b"old")
    monkeypatch.setattr(bi, "Image", _FakePillow)
    if parts > 1:
        monkeypatch.setattr(bi, "pack_split", lambda metas: [((256, 256), [])] * parts)
    calls = []

    def run(cmd):
        calls.append(cmd)
        return fake_run(cmd, len(calls))

    monkeypatch.setattr(bi.subprocess, "run", run)
    ok = bi.build_one(set_dir, "MyMod", out_dir, Path("ImageToPAA.exe"))
    return ok, out_dir, calls


def _writes(cmd, n, rc=0):
    Path(cmd[2]).write_bytes(b"new paa")
    return bi.subprocess.CompletedProcess(cmd, rc)


def _partial_then_fail(cmd, n):
    Path(cmd[2]).write_bytes(b"trunc")
    return bi.subprocess.CompletedProcess(cmd, 1)


def _assert_no_staging_left(out_dir):
    assert not [d for d in out_dir.iterdir() if d.is_dir()]


def test_imagetopaa_never_writes_to_the_final_path(monkeypatch, tmp_path):
    ok, out_dir, calls = _real_build(monkeypatch, tmp_path, _writes)
    assert ok is True
    assert Path(calls[0][2]).parent != out_dir
    assert (out_dir / "icons.paa").read_bytes() == b"new paa"
    assert 'path "MyMod\\gui\\imagesets\\icons.paa"' in (out_dir / "icons.imageset").read_text()
    _assert_no_staging_left(out_dir)


def test_partial_write_then_failure_keeps_previous_single_output(monkeypatch, tmp_path, capsys):
    ok, out_dir, _ = _real_build(monkeypatch, tmp_path, _partial_then_fail)
    assert ok is False
    assert (out_dir / "icons.paa").read_bytes() == b"old"
    assert (out_dir / "icons.imageset").read_bytes() == b"old"
    assert "ImageToPAA exited 1 on icons" in capsys.readouterr().err
    _assert_no_staging_left(out_dir)


def test_exit_zero_without_output_keeps_previous_output(monkeypatch, tmp_path, capsys):
    """An earlier run's .paa must not pass for this run's output."""
    ok, out_dir, _ = _real_build(
        monkeypatch, tmp_path, lambda cmd, n: bi.subprocess.CompletedProcess(cmd, 0))
    assert ok is False
    assert "wrote no icons.paa" in capsys.readouterr().err
    assert (out_dir / "icons.paa").read_bytes() == b"old"
    assert (out_dir / "icons.imageset").read_bytes() == b"old"


def test_split_part_failure_replaces_no_part(monkeypatch, tmp_path):
    """Part 1 converts, part 2 writes a partial file and fails: no old part is touched."""
    def run(cmd, n):
        return _writes(cmd, n) if n == 1 else _partial_then_fail(cmd, n)

    ok, out_dir, _ = _real_build(monkeypatch, tmp_path, run, parts=2,
                                 old_stems=("icons_1", "icons_2"))
    assert ok is False
    for stem in ("icons_1", "icons_2"):
        assert (out_dir / f"{stem}.paa").read_bytes() == b"old"
        assert (out_dir / f"{stem}.imageset").read_bytes() == b"old"
    _assert_no_staging_left(out_dir)


def test_split_success_replaces_parts_and_drops_unsplit_output(monkeypatch, tmp_path):
    ok, out_dir, _ = _real_build(monkeypatch, tmp_path, _writes, parts=2,
                                 old_stems=("icons", "icons_1"))
    assert ok is True
    assert sorted(f.name for f in out_dir.iterdir()) == [
        "icons_1.imageset", "icons_1.paa", "icons_2.imageset", "icons_2.paa",
    ]
    assert (out_dir / "icons_1.paa").read_bytes() == b"new paa"


@pytest.mark.parametrize("name", ["main menu", "main-menu", "2icons", "menü"])
def test_build_one_rejects_bad_set_folder_name(tmp_path, capsys, name):
    set_dir = tmp_path / ".gui-sources" / name
    set_dir.mkdir(parents=True)
    (set_dir / "hud_ok.png").write_bytes(b"not read")
    out_dir = tmp_path / "gui" / "imagesets"
    assert bi.build_one(set_dir, "MyMod", out_dir, Path("ImageToPAA.exe")) is False
    err = capsys.readouterr().err
    assert "set folder names must be identifiers" in err and "Rename the folder" in err
    assert not out_dir.exists()


def test_main_fails_bad_set_name_but_builds_others(monkeypatch, tmp_path, capsys):
    mod = tmp_path / "MyMod"
    for name in ("main menu", "icons"):
        d = mod / ".gui-sources" / name
        d.mkdir(parents=True)
        (d / "hud_ok.png").write_bytes(b"x")
    built = []
    monkeypatch.setattr(bi.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(bi, "Image", _FakePillow)
    monkeypatch.setattr(bi, "resolve_image_to_paa", lambda: Path("ImageToPAA.exe"))
    monkeypatch.setattr(bi, "write_one_atlas", lambda stem, *a: built.append(stem) or True)
    monkeypatch.setattr("sys.argv", ["build_imageset.py", str(mod), "--mod-name", "MyMod"])
    assert bi.main() == 1
    assert built == ["icons"]
    assert "1 of 2 imagesets built." in capsys.readouterr().out


@pytest.mark.parametrize("others,expected", [
    ({"icons_1"}, ["icons_1"]),
    ({"ICONS_2", "other"}, ["icons_2"]),
    ({"icons_3", "icons"}, []),
])
def test_colliding_part_stems(others, expected):
    assert bi.colliding_part_stems("icons", 2, others) == expected


def test_colliding_part_stems_ignores_unsplit_sets():
    assert bi.colliding_part_stems("icons", 1, {"icons_1"}) == []


def test_split_stem_colliding_with_source_set_fails_before_converting(monkeypatch, tmp_path, capsys):
    set_dir = tmp_path / ".gui-sources" / "icons"
    set_dir.mkdir(parents=True)
    (set_dir / "a.png").write_bytes(b"x")
    out_dir = tmp_path / "gui" / "imagesets"
    monkeypatch.setattr(bi, "Image", _FakePillow)
    monkeypatch.setattr(bi, "pack_split", lambda metas: [((256, 256), [])] * 2)
    monkeypatch.setattr(bi, "write_one_atlas", lambda *a: pytest.fail("must not convert"))
    assert bi.build_one(set_dir, "MyMod", out_dir, Path("ImageToPAA.exe"),
                        frozenset({"icons_1"})) is False
    err = capsys.readouterr().err
    assert "icons_1 is also a source set name" in err
    assert not out_dir.exists()


def test_dry_run_writes_and_deletes_nothing(monkeypatch, tmp_path, capsys):
    set_dir = tmp_path / ".gui-sources" / "icons"
    set_dir.mkdir(parents=True)
    (set_dir / "a.png").write_bytes(b"x")
    out_dir = tmp_path / "gui" / "imagesets"
    _touch_outputs(out_dir, "icons_1", "icons_2")
    before = sorted(f.name for f in out_dir.iterdir())
    monkeypatch.setattr(bi, "Image", _FakePillow)
    monkeypatch.setattr(bi.subprocess, "run", lambda *a: pytest.fail("must not convert"))
    assert bi.build_one(set_dir, "MyMod", out_dir, Path("ImageToPAA.exe"), dry_run=True) is True
    out = capsys.readouterr().out
    assert "would write icons.paa + icons.imageset" in out
    assert "Would remove stale icons_1.paa" in out and "Would remove stale icons_2.imageset" in out
    assert sorted(f.name for f in out_dir.iterdir()) == before


def test_dry_run_empty_set_reports_but_keeps_outputs(tmp_path, capsys):
    set_dir = tmp_path / ".gui-sources" / "icons"
    set_dir.mkdir(parents=True)
    out_dir = tmp_path / "gui" / "imagesets"
    _touch_outputs(out_dir, "icons")
    removed = bi.build_one(set_dir, "MyMod", out_dir, Path("ImageToPAA.exe"), dry_run=True)
    assert removed is True
    assert (out_dir / "icons.paa").exists()
    assert "Would remove stale icons.paa" in capsys.readouterr().out


def test_main_dry_run_flag_reaches_build_one(monkeypatch, tmp_path, capsys):
    mod = _mod(tmp_path, "MyMod", prefix="MyMod")
    seen = []
    monkeypatch.setattr(bi.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(bi, "Image", object())
    monkeypatch.setattr(bi, "resolve_image_to_paa", lambda: Path("ImageToPAA.exe"))
    monkeypatch.setattr(bi, "build_one", lambda *a: seen.append(a[-1]) or True)
    monkeypatch.setattr("sys.argv", ["build_imageset.py", str(mod), "--dry-run"])
    assert bi.main() == 0
    assert seen == [True]
    assert "1 of 1 imagesets planned (dry run)." in capsys.readouterr().out


def _split_set(monkeypatch, tmp_path, convert_ok):
    """A set that packs into two atlases, with a single-atlas output left from an earlier run."""
    set_dir = tmp_path / ".gui-sources" / "icons"
    set_dir.mkdir(parents=True)
    (set_dir / "a.png").write_bytes(b"x")
    out_dir = tmp_path / "gui" / "imagesets"
    _touch_outputs(out_dir, "icons")

    class _Img:
        width = height = 64

        def load(self):
            pass

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


def _run_main(monkeypatch, cwd, argv, project=None):
    """Run main() with preflight, Pillow, ImageToPAA and packing stubbed; return build_one calls."""
    calls = []
    monkeypatch.setattr(bi.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(bi, "Image", object())
    monkeypatch.setattr(bi, "resolve_image_to_paa", lambda: Path("ImageToPAA.exe"))
    if project is not None:
        monkeypatch.setattr(bi.h, "resolve_project_dir", lambda: project)
    monkeypatch.setattr(
        bi, "build_one",
        lambda set_dir, mod_name, out_dir, *a: calls.append((set_dir, mod_name, out_dir)) or True,
    )
    monkeypatch.chdir(cwd)
    monkeypatch.setattr("sys.argv", ["build_imageset.py", *argv])
    assert bi.main() == 0
    return calls


def _mod(root, folder, prefix=None):
    mod = root / folder
    (mod / ".gui-sources" / "icons").mkdir(parents=True)
    if prefix is not None:
        (mod / "$PBOPREFIX$").write_text(prefix, encoding="utf-8")
    return mod


def test_modname_resolves_workspace_from_cached_project(monkeypatch, tmp_path):
    """Run from the repo root (or anywhere) with <ModName>, like the sibling skills."""
    project = tmp_path / "project"
    mod = _mod(project / "workspace", "MyMod", prefix="MyMod")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    calls = _run_main(monkeypatch, elsewhere, ["MyMod"], project=project)
    assert [(c[0], c[2]) for c in calls] == [
        (mod / ".gui-sources" / "icons", mod / "gui" / "imagesets")
    ]


def test_modname_missing_from_workspace_exits_with_hint(monkeypatch, tmp_path):
    (tmp_path / "workspace").mkdir()
    monkeypatch.setattr(bi.h, "resolve_project_dir", lambda: tmp_path)
    with pytest.raises(SystemExit) as exc:
        bi.resolve_mod_root("NoSuchMod")
    assert "workspace\\NoSuchMod not found" in str(exc.value)
    assert "/dayz-new-mod NoSuchMod" in str(exc.value)


def test_path_form_still_works_without_a_cached_project(monkeypatch, tmp_path):
    mod = _mod(tmp_path, "SomeFolder", prefix="SomeFolder")

    def no_project():
        raise AssertionError("path form must not need a cached project")

    monkeypatch.setattr(bi.h, "resolve_project_dir", no_project)
    calls = _run_main(monkeypatch, tmp_path, [str(mod)])
    assert calls[0][2] == mod / "gui" / "imagesets"
    calls = _run_main(monkeypatch, tmp_path, [".\\SomeFolder"])
    assert calls[0][2] == mod / "gui" / "imagesets"


@pytest.mark.parametrize("arg,expected", [
    ("MyMod", False), ("My_Mod2", False),
    (".", True), ("..", True), ("workspace/MyMod", True),
    ("workspace\\MyMod", True), ("C:\\mods\\MyMod", True), ("P:MyMod", True),
])
def test_is_path_form(arg, expected):
    assert bi.is_path_form(arg) is expected


def test_mod_name_defaults_to_pboprefix_not_folder_name(monkeypatch, tmp_path):
    """The .imageset path field is rooted at the PBO prefix, which may differ from the folder."""
    mod = _mod(tmp_path, "checkout-folder", prefix="MyMod")
    calls = _run_main(monkeypatch, tmp_path, [str(mod)])
    assert calls[0][1] == "MyMod"
    calls = _run_main(monkeypatch, tmp_path, [str(mod), "--mod-name", "Override"])
    assert calls[0][1] == "Override"


@pytest.mark.parametrize("content,expected", [
    ("MyMod", "MyMod"), ("MyMod\r\n", "MyMod"), ("\ufeffMyMod", "MyMod"),
    ("Author\\MyMod\\", "Author\\MyMod"),
])
def test_default_mod_name_reads_pboprefix(tmp_path, content, expected):
    (tmp_path / "$PBOPREFIX$").write_text(content, encoding="utf-8")
    assert bi.default_mod_name(tmp_path) == expected


def test_default_mod_name_falls_back_to_folder_with_warning(tmp_path, capsys):
    mod = tmp_path / "Folder"
    mod.mkdir()
    assert bi.default_mod_name(mod) == "Folder"
    assert "[WARN]" in capsys.readouterr().out


def test_remove_stale_outputs_ignores_case(tmp_path):
    """After renaming the folder Icons to icons, the old Icons_2.* is stale too."""
    _touch_outputs(tmp_path, "Icons_2", "ICONS_3")
    bi.remove_stale_outputs(tmp_path, "icons", 1, frozenset({"Icons_3"}))
    assert {p.stem for p in tmp_path.iterdir()} == {"ICONS_3"}


def _generated(out_dir, stem, paa=True):
    out_dir.mkdir(parents=True, exist_ok=True)
    bi.write_imageset_file(out_dir / f"{stem}.imageset", stem, 256, 256,
                           f"MyMod\\gui\\imagesets\\{stem}.paa", [])
    if paa:
        (out_dir / f"{stem}.paa").write_bytes(b"paa")


def test_looks_generated_only_matches_this_skills_format(tmp_path):
    _generated(tmp_path, "mine")
    assert bi.looks_generated(tmp_path / "mine.imageset")
    vanilla = tmp_path / "vanilla.imageset"
    vanilla.write_text('ImageSetClass {\n Name "vanilla"\n Textures {\n  ImageSetTextureClass {\n'
                       '   path "Gui/imagesets/vanilla.edds"\n  }\n }\n}\n', encoding="utf-8")
    assert not bi.looks_generated(vanilla)
    renamed = tmp_path / "renamed.imageset"
    renamed.write_text((tmp_path / "mine.imageset").read_text(encoding="utf-8"), encoding="utf-8")
    assert not bi.looks_generated(renamed)  # Name and path point at another stem


def test_find_orphan_outputs_lists_generated_files_of_deleted_sets(tmp_path):
    _generated(tmp_path, "old")          # set folder deleted
    _generated(tmp_path, "gone_1")       # part of a deleted split set
    _generated(tmp_path, "gone_2", paa=False)
    _generated(tmp_path, "icons")        # current set
    _generated(tmp_path, "Menu_2")       # part of the current set "menu", other case
    (tmp_path / "custom.imageset").write_text("hand made", encoding="utf-8")
    (tmp_path / "custom.paa").write_bytes(b"paa")
    orphans = bi.find_orphan_outputs(tmp_path, {"icons", "menu"})
    assert [p.name for p in orphans] == [
        "gone_1.imageset", "gone_1.paa", "gone_2.imageset", "old.imageset", "old.paa",
    ]
    assert bi.find_orphan_outputs(tmp_path / "nope", set()) == []


def _orphan_mod(tmp_path):
    mod = _mod(tmp_path, "MyMod", prefix="MyMod")
    out_dir = mod / "gui" / "imagesets"
    _generated(out_dir, "icons")
    _generated(out_dir, "old")
    return mod, out_dir


def test_main_warns_about_orphans_and_keeps_them_by_default(monkeypatch, tmp_path, capsys):
    mod, out_dir = _orphan_mod(tmp_path)
    _run_main(monkeypatch, tmp_path, [str(mod)])
    out = capsys.readouterr().out
    assert "[WARN]  orphan old.imageset" in out and "--prune" in out
    assert (out_dir / "old.paa").is_file() and (out_dir / "old.imageset").is_file()


def test_main_prune_deletes_orphans_only(monkeypatch, tmp_path, capsys):
    mod, out_dir = _orphan_mod(tmp_path)
    _run_main(monkeypatch, tmp_path, [str(mod), "--prune", "--dry-run"])
    assert "Would remove orphan old.paa" in capsys.readouterr().out
    assert (out_dir / "old.paa").is_file()
    _run_main(monkeypatch, tmp_path, [str(mod), "--prune"])
    assert "Removed orphan old.paa" in capsys.readouterr().out
    assert sorted(f.name for f in out_dir.iterdir()) == ["icons.imageset", "icons.paa"]


def test_main_prune_with_no_set_folders_left(monkeypatch, tmp_path, capsys):
    mod, out_dir = _orphan_mod(tmp_path)
    (mod / ".gui-sources" / "icons").rmdir()
    monkeypatch.setattr(bi.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(bi, "Image", object())
    monkeypatch.setattr("sys.argv", ["build_imageset.py", str(mod), "--prune"])
    with pytest.raises(SystemExit) as exc:
        bi.main()
    assert "no imageset subfolders" in str(exc.value)
    assert not any(out_dir.iterdir())


def test_main_skips_dot_folders_in_gui_sources(monkeypatch, tmp_path):
    mod = _mod(tmp_path, "MyMod", prefix="MyMod")
    (mod / ".gui-sources" / ".git").mkdir()
    calls = _run_main(monkeypatch, tmp_path, [str(mod)])  # asserts exit 0
    assert [c[0].name for c in calls] == ["icons"]
