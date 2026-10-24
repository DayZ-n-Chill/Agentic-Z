"""Tests for input validation in pack_texture.py (no DayZ Tools needed)."""
import importlib.util
import os
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "pack_texture", Path(__file__).with_name("pack_texture.py")
)
pt = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pt)


def _png(width, height):
    """The first 24 bytes of a PNG: signature, IHDR length and type, width, height."""
    return pt.PNG_SIGNATURE + (13).to_bytes(4, "big") + b"IHDR" + width.to_bytes(4, "big") + height.to_bytes(4, "big")


def _tga(width, height, image_type=2, depth=32, color_map_type=0):
    """An 18 byte TGA header: color map type at byte 1, image type at byte 2, width at
    bytes 12 and 13, height at 14 and 15 (little endian), bits per pixel at byte 16."""
    return (
        bytes([0, color_map_type, image_type]) + bytes(9)
        + width.to_bytes(2, "little") + height.to_bytes(2, "little") + bytes([depth, 0])
    )


def _image(name, width=1024, height=1024):
    return _tga(width, height) if name.lower().endswith(".tga") else _png(width, height)


@pytest.mark.parametrize("stem", ["vest_co", "vest_camo_nohq", "vest_smdi", "VEST_CO", "a_b_NoHQ"])
def test_suffix_re_accepts_core_suffixes(stem):
    assert pt.SUFFIX_RE.search(stem)


@pytest.mark.parametrize("suffix", pt.ALLOWED_SUFFIXES)
def test_suffix_re_accepts_every_vanilla_suffix(suffix):
    assert pt.SUFFIX_RE.search("vest" + suffix)
    assert pt.SUFFIX_RE.search("VEST" + suffix.upper())


@pytest.mark.parametrize("stem", ["glass_ca", "ui_icon_lco", "bricks_broken_full_dtsmdi", "rock_apart1_mask"])
def test_suffix_re_accepts_vanilla_examples(stem):
    assert pt.SUFFIX_RE.search(stem)


@pytest.mark.parametrize("stem", ["vest", "vest_co_old", "vestco", "vest_nohq2", "co", "vest_diffuse", "vest_normal", "vest_c"])
def test_suffix_re_rejects_other_names(stem):
    assert not pt.SUFFIX_RE.search(stem)


@pytest.mark.parametrize("name", ["vest_co.png", "vest_nohq.TGA", "vest_smdi.Png", "glass_ca.png", "vest_as.tga"])
def test_validate_input_accepts(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(_image(name))
    assert pt.validate_input(path) == []


def test_validate_input_refuses_png_that_is_not_a_power_of_two(tmp_path):
    path = tmp_path / "vest_co.png"
    path.write_bytes(_png(1000, 1000))
    (error,) = pt.validate_input(path)
    assert "1000 x 1000 is not a power of two" in error
    assert "1024 x 1024" in error


def test_validate_input_accepts_tga_with_unequal_power_of_two_sides(tmp_path):
    path = tmp_path / "shirt_co.tga"
    path.write_bytes(_tga(1024, 512))
    assert pt.image_size(path) == (1024, 512)
    assert pt.validate_input(path) == []


@pytest.mark.parametrize(
    "header",
    [
        _tga(512, 512, image_type=0),        # no image data
        _tga(512, 512, image_type=7),        # not a TGA image type
        _tga(512, 512, depth=0),             # no bits per pixel
        _tga(512, 512, color_map_type=5),    # not a color map type
        _png(512, 512),                      # a PNG renamed to .tga
        bytes(18),                           # zeroed file
    ],
)
def test_validate_input_refuses_corrupt_or_mislabeled_tga(tmp_path, header):
    path = tmp_path / "vest_co.tga"
    path.write_bytes(header)
    (error,) = pt.validate_input(path)
    assert "cannot read the image size" in error


@pytest.mark.parametrize("image_type", sorted(pt.TGA_IMAGE_TYPES))
@pytest.mark.parametrize("depth", sorted(pt.TGA_PIXEL_DEPTHS))
def test_image_size_reads_every_valid_tga_kind(tmp_path, image_type, depth):
    path = tmp_path / "vest_co.tga"
    path.write_bytes(_tga(256, 128, image_type=image_type, depth=depth))
    assert pt.image_size(path) == (256, 128)


def test_corrupt_tga_stops_the_batch_before_any_conversion(monkeypatch, tmp_path, capsys):
    good = tmp_path / "good_co.png"
    good.write_bytes(_png(512, 512))
    bad = tmp_path / "bad_nohq.tga"
    bad.write_bytes(bytes(18))

    def no_run(*a, **k):
        raise AssertionError("nothing may convert while an input is corrupt")

    monkeypatch.setattr(pt.subprocess, "run", no_run)
    monkeypatch.setattr(pt.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(pt, "resolve_image_to_paa", lambda: tmp_path / "ImageToPAA.exe")
    monkeypatch.setattr("sys.argv", ["pack_texture.py", str(good), str(bad)])
    assert pt.main() == 1
    assert "bad_nohq.tga: cannot read the image size" in capsys.readouterr().err
    assert not (tmp_path / "good_co.paa").exists()


def test_validate_input_refuses_unreadable_header(tmp_path):
    path = tmp_path / "vest_co.png"
    path.write_bytes(b"not a png")
    (error,) = pt.validate_input(path)
    assert "cannot read the image size" in error


@pytest.mark.parametrize("side,nearest", [(1000, 1024), (700, 512), (3000, 2048), (50, 64), (768, 1024)])
def test_nearest_vanilla_size(side, nearest):
    assert pt.nearest_vanilla_size(side) == nearest


@pytest.mark.parametrize(
    "name,message",
    [
        ("vest_co.jpg", "only .png, .tga accepted"),
        ("vest_co.paa", "only .png, .tga accepted"),
        ("vest.png", "basename must end with"),
        ("vest_co_v2.png", "basename must end with"),
    ],
)
def test_validate_input_rejects(tmp_path, name, message):
    path = tmp_path / name
    path.write_bytes(b"")
    errors = pt.validate_input(path)
    assert any(message in e for e in errors)


def test_validate_input_rejects_missing_file(tmp_path):
    (error,) = pt.validate_input(tmp_path / "missing_co.png")
    assert "Input not found" in error


def test_validate_input_reports_wrong_extension_and_missing_suffix_together(tmp_path):
    path = tmp_path / "vest.jpg"
    path.write_bytes(b"")
    errors = pt.validate_input(path)
    assert len(errors) == 2
    assert "only .png, .tga accepted" in errors[0]
    assert "basename must end with" in errors[1]


def test_validate_input_reports_missing_suffix_and_bad_size_together(tmp_path):
    path = tmp_path / "vest.png"
    path.write_bytes(_png(1000, 512))
    errors = pt.validate_input(path)
    assert len(errors) == 2
    assert "basename must end with" in errors[0]
    assert "1000 x 512 is not a power of two" in errors[1]


def test_validate_input_refuses_a_folder_named_like_an_image(tmp_path):
    folder = tmp_path / "vest_co.png"
    folder.mkdir()
    (error,) = pt.validate_input(folder)
    assert error.startswith(pt.h.FAIL)
    assert "is a folder" in error


def test_validate_input_reports_unreadable_file_instead_of_traceback(monkeypatch, tmp_path):
    path = tmp_path / "vest_co.png"
    path.write_bytes(_png(512, 512))

    def locked(*a, **k):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(pt, "image_size", locked)
    (error,) = pt.validate_input(path)
    assert error.startswith(pt.h.FAIL)
    assert "cannot read the file (Permission denied)" in error


def test_main_reports_every_bad_input_in_one_run(monkeypatch, tmp_path, capsys):
    good = tmp_path / "good_co.png"
    good.write_bytes(_png(512, 512))
    big = tmp_path / "big_co.png"
    big.write_bytes(_png(1000, 1000))
    wide = tmp_path / "wide_nohq.tga"
    wide.write_bytes(_tga(700, 512))
    nosuffix = tmp_path / "plain.png"
    nosuffix.write_bytes(_png(512, 512))
    wrong_ext = tmp_path / "vest_co.jpg"
    wrong_ext.write_bytes(b"")
    corrupt = tmp_path / "broken_smdi.tga"
    corrupt.write_bytes(bytes(18))
    twin = tmp_path / "good_co.tga"
    twin.write_bytes(_tga(512, 512))
    missing = tmp_path / "missing_co.png"

    def no_run(*a, **k):
        raise AssertionError("nothing may convert while any input is bad")

    monkeypatch.setattr(pt.subprocess, "run", no_run)
    monkeypatch.setattr(pt.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(pt, "resolve_image_to_paa", lambda: tmp_path / "ImageToPAA.exe")
    args = [good, big, wide, nosuffix, wrong_ext, corrupt, twin, missing]
    monkeypatch.setattr("sys.argv", ["pack_texture.py", *map(str, args)])
    assert pt.main() == 1
    err = capsys.readouterr().err
    assert "big_co.png: 1000 x 1000 is not a power of two" in err
    assert "wide_nohq.tga: 700 x 512 is not a power of two" in err
    assert "plain.png: basename must end with" in err
    assert "vest_co.jpg: only .png, .tga accepted" in err
    assert "broken_smdi.tga: cannot read the image size" in err
    assert "good_co.png and good_co.tga would both write good_co.paa" in err
    assert "Input not found" in err and "missing_co.png" in err
    assert "7 input problem(s) found; nothing converted." in err
    assert not list(tmp_path.glob("*.paa"))


class _FakePreflight:
    def __init__(self, root, p_mounted=True):
        self.root = root
        self.p_mounted = p_mounted
        self.p_checks = 0

    def find_dayz_tools(self):
        return self.root

    def check_p_drive(self):
        self.p_checks += 1
        return self.p_mounted


def _no_full_preflight():
    raise AssertionError("a dry run must not run the full preflight, which can create P:\\Mods")


def test_dry_run_gate_is_read_only(monkeypatch):
    fake = _FakePreflight(None)
    monkeypatch.setattr(pt.h, "preflight", fake, raising=False)
    monkeypatch.setattr(pt.h, "gate_on_preflight", _no_full_preflight)
    pt.gate(dry_run=True)  # no SystemExit
    assert fake.p_checks == 1


def test_dry_run_gate_exits_1_without_p_drive(monkeypatch):
    monkeypatch.setattr(pt.h, "preflight", _FakePreflight(None, p_mounted=False), raising=False)
    monkeypatch.setattr(pt.h, "gate_on_preflight", _no_full_preflight)
    with pytest.raises(SystemExit) as exc:
        pt.gate(dry_run=True)
    assert exc.value.code == 1


def test_real_run_gate_runs_full_preflight(monkeypatch):
    calls = []
    monkeypatch.setattr(pt.h, "gate_on_preflight", lambda: calls.append(1))
    pt.gate(dry_run=False)
    assert calls == [1]


def test_resolve_image_to_paa_uses_preflight_resolver(monkeypatch, tmp_path):
    exe = tmp_path / "Bin" / "ImageToPAA" / "ImageToPAA.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    monkeypatch.setattr(pt.h, "preflight", _FakePreflight(tmp_path), raising=False)
    assert pt.resolve_image_to_paa() == exe


def test_resolve_image_to_paa_without_tools_exits(monkeypatch):
    monkeypatch.setattr(pt.h, "preflight", _FakePreflight(None), raising=False)
    with pytest.raises(SystemExit) as exc:
        pt.resolve_image_to_paa()
    assert "DayZ Tools not found" in str(exc.value)


def test_main_gates_before_validating(monkeypatch, tmp_path):
    def gate():
        raise SystemExit(1)

    monkeypatch.setattr(pt.h, "gate_on_preflight", gate)
    monkeypatch.setattr("sys.argv", ["pack_texture.py", str(tmp_path / "missing_co.png")])
    with pytest.raises(SystemExit) as exc:
        pt.main()
    assert exc.value.code == 1


class _Result:
    def __init__(self, returncode):
        self.returncode = returncode


def test_pack_one_nonzero_exit_returns_false(monkeypatch, tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    monkeypatch.setattr(pt.subprocess, "run", lambda cmd: _Result(3))
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert "ImageToPAA exited 3 on vest_co.png" in capsys.readouterr().err


def test_pack_one_success_without_output_returns_false(monkeypatch, tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    monkeypatch.setattr(pt.subprocess, "run", lambda cmd: _Result(0))
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert "reported success but" in capsys.readouterr().err


def test_pack_one_success_writes_paa(monkeypatch, tmp_path):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")

    def run(cmd):
        Path(cmd[2]).write_bytes(b"paa")
        return _Result(0)

    monkeypatch.setattr(pt.subprocess, "run", run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is True


def test_pack_one_success_without_rewrite_of_existing_paa_fails(monkeypatch, tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    (tmp_path / "vest_co.paa").write_bytes(b"old paa")
    monkeypatch.setattr(pt.subprocess, "run", lambda cmd: _Result(0))
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert "did not rewrite" in capsys.readouterr().err


def test_pack_one_overwrites_existing_paa(monkeypatch, tmp_path):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    dst = tmp_path / "vest_co.paa"
    dst.write_bytes(b"old paa")
    os.utime(dst, ns=(1_000_000_000, 1_000_000_000))

    def run(cmd):
        Path(cmd[2]).write_bytes(b"new paa")
        return _Result(0)

    monkeypatch.setattr(pt.subprocess, "run", run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is True
    assert dst.read_bytes() == b"new paa"


def test_main_exits_1_on_partial_failure(monkeypatch, tmp_path, capsys):
    good = tmp_path / "good_co.png"
    bad = tmp_path / "bad_nohq.png"
    for p in (good, bad):
        p.write_bytes(_png(512, 512))
    monkeypatch.setattr(pt.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(pt, "resolve_image_to_paa", lambda: tmp_path / "ImageToPAA.exe")
    monkeypatch.setattr(pt, "pack_one", lambda exe, src: src == good)
    monkeypatch.setattr("sys.argv", ["pack_texture.py", str(good), str(bad)])
    assert pt.main() == 1
    assert "1 of 2 textures packed." in capsys.readouterr().out


def test_pack_one_backs_up_existing_paa_before_overwrite(monkeypatch, tmp_path):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    dst = tmp_path / "vest_co.paa"
    dst.write_bytes(b"hand tuned")
    os.utime(dst, ns=(1_000_000_000, 1_000_000_000))

    def run(cmd):
        Path(cmd[2]).write_bytes(b"new paa")
        return _Result(0)

    monkeypatch.setattr(pt.subprocess, "run", run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is True
    assert dst.read_bytes() == b"new paa"
    assert (tmp_path / "vest_co.paa.bak").read_bytes() == b"hand tuned"


def test_pack_one_keeps_backup_when_conversion_fails(monkeypatch, tmp_path):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    dst = tmp_path / "vest_co.paa"
    dst.write_bytes(b"hand tuned")

    def run(cmd):
        Path(cmd[2]).write_bytes(b"half written")
        return _Result(1)

    monkeypatch.setattr(pt.subprocess, "run", run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert (tmp_path / "vest_co.paa.bak").read_bytes() == b"hand tuned"


def test_pack_one_restores_backup_when_conversion_fails(monkeypatch, tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    dst = tmp_path / "vest_co.paa"
    dst.write_bytes(b"hand tuned")

    def run(cmd):
        Path(cmd[2]).write_bytes(b"half written")
        return _Result(1)

    monkeypatch.setattr(pt.subprocess, "run", run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert dst.read_bytes() == b"hand tuned"
    assert "Restored the previous vest_co.paa from vest_co.paa.bak" in capsys.readouterr().err


def test_pack_one_restores_backup_when_tool_deletes_the_paa(monkeypatch, tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    dst = tmp_path / "vest_co.paa"
    dst.write_bytes(b"hand tuned")

    def run(cmd):
        Path(cmd[2]).unlink()
        return _Result(0)

    monkeypatch.setattr(pt.subprocess, "run", run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert dst.read_bytes() == b"hand tuned"
    assert "Restored the previous vest_co.paa" in capsys.readouterr().err


def test_pack_one_restores_backup_when_paa_left_unchanged(monkeypatch, tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    dst = tmp_path / "vest_co.paa"
    dst.write_bytes(b"hand tuned")
    monkeypatch.setattr(pt.subprocess, "run", lambda cmd: _Result(0))
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert dst.read_bytes() == b"hand tuned"
    assert "Restored the previous vest_co.paa" in capsys.readouterr().err


def test_pack_one_removes_partial_paa_when_none_existed(monkeypatch, tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")

    def run(cmd):
        Path(cmd[2]).write_bytes(b"half written")
        return _Result(1)

    monkeypatch.setattr(pt.subprocess, "run", run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert not (tmp_path / "vest_co.paa").exists()
    assert "Removed the partial vest_co.paa" in capsys.readouterr().err


def test_pack_one_says_how_to_restore_when_undo_fails(monkeypatch, tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    (tmp_path / "vest_co.paa").write_bytes(b"hand tuned")
    real_copy = pt.shutil.copy2
    calls = []

    def copy2(a, b):
        calls.append(1)
        if len(calls) > 1:
            raise PermissionError(13, "Permission denied")
        return real_copy(a, b)

    def run(cmd):
        Path(cmd[2]).write_bytes(b"half written")
        return _Result(1)

    monkeypatch.setattr(pt.shutil, "copy2", copy2)
    monkeypatch.setattr(pt.subprocess, "run", run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert "copy vest_co.paa.bak over vest_co.paa by hand" in capsys.readouterr().err


def test_pack_one_skips_conversion_when_backup_fails(monkeypatch, tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    dst = tmp_path / "vest_co.paa"
    dst.write_bytes(b"hand tuned")

    def copy2(a, b):
        raise PermissionError(13, "Permission denied")

    def no_run(*a, **k):
        raise AssertionError("must not convert without a backup")

    monkeypatch.setattr(pt.shutil, "copy2", copy2)
    monkeypatch.setattr(pt.subprocess, "run", no_run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert dst.read_bytes() == b"hand tuned"
    assert "Could not back up vest_co.paa" in capsys.readouterr().err


def _repack(monkeypatch, tmp_path, content):
    """One successful pack_one of vest_co.png that writes `content` to vest_co.paa."""
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    dst = tmp_path / "vest_co.paa"
    if dst.exists():
        os.utime(dst, ns=(1_000_000_000, 1_000_000_000))

    def run(cmd):
        Path(cmd[2]).write_bytes(content)
        return _Result(0)

    monkeypatch.setattr(pt.subprocess, "run", run)
    return pt.pack_one(tmp_path / "ImageToPAA.exe", src)


def test_repeated_repacks_keep_a_single_rolling_backup(monkeypatch, tmp_path, capsys):
    (tmp_path / "vest_co.paa").write_bytes(b"first")
    for content in (b"second", b"third", b"fourth"):
        assert _repack(monkeypatch, tmp_path, content) is True
    assert (tmp_path / "vest_co.paa").read_bytes() == b"fourth"
    # Only the copy from just before the last run is kept; nothing piles up.
    assert (tmp_path / "vest_co.paa.bak").read_bytes() == b"third"
    assert sorted(p.name for p in tmp_path.glob("vest_co.paa.bak*")) == ["vest_co.paa.bak"]
    out = capsys.readouterr().out
    assert out.count("(replaced the previous backup)") == 2
    assert "[WARN]" not in out


def test_repack_counts_leftover_numbered_backups_and_keeps_them(monkeypatch, tmp_path, capsys):
    (tmp_path / "vest_co.paa").write_bytes(b"current")
    (tmp_path / "vest_co.paa.bak").write_bytes(b"older")
    (tmp_path / "vest_co.paa.bak.1").write_bytes(b"old 1")
    (tmp_path / "vest_co.paa.bak.2").write_bytes(b"old 2")
    (tmp_path / "other_co.paa.bak.1").write_bytes(b"not ours")
    assert _repack(monkeypatch, tmp_path, b"new") is True
    assert (tmp_path / "vest_co.paa.bak").read_bytes() == b"current"
    assert (tmp_path / "vest_co.paa.bak.1").read_bytes() == b"old 1"
    out = capsys.readouterr().out
    assert "3 backups of vest_co.paa exist" in out
    assert "vest_co.paa.bak.1, vest_co.paa.bak.2" in out
    assert "other_co" not in out


def test_failed_backup_copy_keeps_the_previous_backup_intact(monkeypatch, tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    (tmp_path / "vest_co.paa").write_bytes(b"current")
    (tmp_path / "vest_co.paa.bak").write_bytes(b"previous good")

    def copy2(a, b):
        Path(b).write_bytes(b"half")  # a copy that dies partway through
        raise OSError(28, "No space left on device")

    def no_run(*a, **k):
        raise AssertionError("must not convert without a backup")

    monkeypatch.setattr(pt.shutil, "copy2", copy2)
    monkeypatch.setattr(pt.subprocess, "run", no_run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is False
    assert (tmp_path / "vest_co.paa.bak").read_bytes() == b"previous good"
    assert not (tmp_path / "vest_co.paa.bak.tmp").exists()
    assert (tmp_path / "vest_co.paa").read_bytes() == b"current"


def test_dry_run_says_when_the_backup_would_be_replaced(tmp_path, capsys):
    src = tmp_path / "vest_co.png"
    (tmp_path / "vest_co.paa").write_bytes(b"current")
    (tmp_path / "vest_co.paa.bak").write_bytes(b"older")
    pt.plan_one(src)
    out = capsys.readouterr().out
    assert "to vest_co.paa.bak, replacing the current vest_co.paa.bak" in out


@pytest.mark.parametrize(
    "name,hint,label",
    [
        ("vest_normal.png", "vest_nohq.png", "normal map"),
        ("vest_NRM.tga", "vest_nohq.tga", "normal map"),
        ("vestnormalmap.png", "vestnormalmap_nohq.png", "normal map"),
        ("vest_spec.png", "vest_smdi.png", "specular"),
        ("vest_specular.png", "vest_smdi.png", "specular"),
        ("vest_alpha.png", "vest_ca.png", "color with alpha"),
        ("vest_diffuse.png", "vest_co.png", "color/diffuse"),
        ("vest_albedo.png", "vest_co.png", "color/diffuse"),
        ("vest.png", "vest_co.png", "color/diffuse"),
        ("north_vest.png", "north_vest_co.png", "color/diffuse"),
        ("normal.png", "normal_nohq.png", "normal map"),
    ],
)
def test_missing_suffix_hint_follows_the_stem(tmp_path, name, hint, label):
    path = tmp_path / name
    path.write_bytes(_image(name, 512, 512))
    (error,) = pt.validate_input(path)
    assert f"Rename to e.g. {hint} ({label})." in error


def test_pack_one_without_existing_paa_writes_no_backup(monkeypatch, tmp_path):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")

    def run(cmd):
        Path(cmd[2]).write_bytes(b"paa")
        return _Result(0)

    monkeypatch.setattr(pt.subprocess, "run", run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is True
    assert not list(tmp_path.glob("*.bak*"))


def test_main_dry_run_lists_and_writes_nothing(monkeypatch, tmp_path, capsys):
    fresh = tmp_path / "fresh_co.png"
    tuned = tmp_path / "tuned_nohq.png"
    for p in (fresh, tuned):
        p.write_bytes(_png(512, 512))
    (tmp_path / "tuned_nohq.paa").write_bytes(b"hand tuned")
    before = sorted(p.name for p in tmp_path.iterdir())

    def no_run(*a, **k):
        raise AssertionError("dry run must not invoke ImageToPAA")

    monkeypatch.setattr(pt.subprocess, "run", no_run)
    monkeypatch.setattr(pt.h, "gate_on_preflight", _no_full_preflight)
    monkeypatch.setattr(pt.h, "preflight", _FakePreflight(None), raising=False)
    monkeypatch.setattr(pt, "resolve_image_to_paa", lambda: tmp_path / "ImageToPAA.exe")
    monkeypatch.setattr("sys.argv", ["pack_texture.py", "--dry-run", str(fresh), str(tuned)])
    assert pt.main() == 0
    out = capsys.readouterr().out
    assert "fresh_co.png  ->  fresh_co.paa" in out
    assert "tuned_nohq.png  ->  tuned_nohq.paa" in out
    assert "would back up the existing tuned_nohq.paa to tuned_nohq.paa.bak" in out
    assert "fresh_co.paa to" not in out
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert (tmp_path / "tuned_nohq.paa").read_bytes() == b"hand tuned"


def test_main_dry_run_still_validates(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "vest.png"
    bad.write_bytes(_png(512, 512))
    monkeypatch.setattr(pt.h, "gate_on_preflight", _no_full_preflight)
    monkeypatch.setattr(pt.h, "preflight", _FakePreflight(None), raising=False)
    monkeypatch.setattr("sys.argv", ["pack_texture.py", "--dry-run", str(bad)])
    assert pt.main() == 1
    assert "basename must end with" in capsys.readouterr().err


@pytest.mark.parametrize("names", [("vest_co.png", "vest_co.tga"), ("vest_co.png", "vest_co.png")])
def test_main_refuses_two_inputs_with_the_same_paa(monkeypatch, tmp_path, capsys, names):
    paths = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(_image(name))
        paths.append(str(path))

    def no_run(*a, **k):
        raise AssertionError("nothing may convert when two inputs share a .paa")

    monkeypatch.setattr(pt.subprocess, "run", no_run)
    monkeypatch.setattr(pt.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(pt, "resolve_image_to_paa", lambda: tmp_path / "ImageToPAA.exe")
    monkeypatch.setattr("sys.argv", ["pack_texture.py", *paths])
    assert pt.main() == 1
    assert "would both write vest_co.paa" in capsys.readouterr().err
    assert not (tmp_path / "vest_co.paa").exists()


def test_check_unique_outputs_allows_distinct_paa_names(tmp_path):
    assert pt.check_unique_outputs([tmp_path / "vest_co.png", tmp_path / "vest_nohq.tga"]) == []


def test_check_unique_outputs_reports_every_collision(tmp_path):
    errors = pt.check_unique_outputs(
        [tmp_path / "a_co.png", tmp_path / "a_co.tga", tmp_path / "b_co.png", tmp_path / "B_CO.tga"]
    )
    assert len(errors) == (2 if os.name == "nt" else 1)
    assert "a_co.png and a_co.tga would both write a_co.paa" in errors[0]
