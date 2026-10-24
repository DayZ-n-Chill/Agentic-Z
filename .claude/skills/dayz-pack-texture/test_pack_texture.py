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


def _tga(width, height):
    """An 18 byte TGA header: width at bytes 12 and 13, height at 14 and 15, little endian."""
    return bytes(12) + width.to_bytes(2, "little") + height.to_bytes(2, "little") + bytes(2)


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
    pt.validate_input(path)  # no SystemExit


def test_validate_input_refuses_png_that_is_not_a_power_of_two(tmp_path):
    path = tmp_path / "vest_co.png"
    path.write_bytes(_png(1000, 1000))
    with pytest.raises(SystemExit) as exc:
        pt.validate_input(path)
    assert "1000 x 1000 is not a power of two" in str(exc.value)
    assert "1024 x 1024" in str(exc.value)


def test_validate_input_accepts_tga_with_unequal_power_of_two_sides(tmp_path):
    path = tmp_path / "shirt_co.tga"
    path.write_bytes(_tga(1024, 512))
    assert pt.image_size(path) == (1024, 512)
    pt.validate_input(path)  # no SystemExit


def test_validate_input_refuses_unreadable_header(tmp_path):
    path = tmp_path / "vest_co.png"
    path.write_bytes(b"not a png")
    with pytest.raises(SystemExit) as exc:
        pt.validate_input(path)
    assert "cannot read the image size" in str(exc.value)


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
    with pytest.raises(SystemExit) as exc:
        pt.validate_input(path)
    assert message in str(exc.value)


def test_validate_input_rejects_missing_file(tmp_path):
    with pytest.raises(SystemExit) as exc:
        pt.validate_input(tmp_path / "missing_co.png")
    assert "Input not found" in str(exc.value)


class _FakePreflight:
    def __init__(self, root):
        self.root = root

    def find_dayz_tools(self):
        return self.root


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


def test_pack_one_never_overwrites_an_earlier_backup(monkeypatch, tmp_path):
    src = tmp_path / "vest_co.png"
    src.write_bytes(b"")
    dst = tmp_path / "vest_co.paa"
    dst.write_bytes(b"second")
    os.utime(dst, ns=(1_000_000_000, 1_000_000_000))
    (tmp_path / "vest_co.paa.bak").write_bytes(b"first")

    def run(cmd):
        Path(cmd[2]).write_bytes(b"third")
        return _Result(0)

    monkeypatch.setattr(pt.subprocess, "run", run)
    assert pt.pack_one(tmp_path / "ImageToPAA.exe", src) is True
    assert (tmp_path / "vest_co.paa.bak").read_bytes() == b"first"
    assert (tmp_path / "vest_co.paa.bak.1").read_bytes() == b"second"


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
    monkeypatch.setattr(pt.h, "gate_on_preflight", lambda: None)
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


def test_main_dry_run_still_validates(monkeypatch, tmp_path):
    bad = tmp_path / "vest.png"
    bad.write_bytes(_png(512, 512))
    monkeypatch.setattr(pt.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr("sys.argv", ["pack_texture.py", "--dry-run", str(bad)])
    with pytest.raises(SystemExit) as exc:
        pt.main()
    assert "basename must end with" in str(exc.value)


@pytest.mark.parametrize("names", [("vest_co.png", "vest_co.tga"), ("vest_co.png", "vest_co.png")])
def test_main_refuses_two_inputs_with_the_same_paa(monkeypatch, tmp_path, names):
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
    with pytest.raises(SystemExit) as exc:
        pt.main()
    assert "would both write vest_co.paa" in str(exc.value)
    assert not (tmp_path / "vest_co.paa").exists()


def test_check_unique_outputs_allows_distinct_paa_names(tmp_path):
    pt.check_unique_outputs([tmp_path / "vest_co.png", tmp_path / "vest_nohq.tga"])  # no SystemExit
