"""Tests for input validation in pack_texture.py (no DayZ Tools needed)."""
import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "pack_texture", Path(__file__).with_name("pack_texture.py")
)
pt = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pt)


@pytest.mark.parametrize("stem", ["vest_co", "vest_camo_nohq", "vest_smdi", "VEST_CO", "a_b_NoHQ"])
def test_suffix_re_accepts_role_suffixes(stem):
    assert pt.SUFFIX_RE.search(stem)


@pytest.mark.parametrize("stem", ["vest", "vest_ca", "vest_co_old", "vestco", "vest_nohq2", "co"])
def test_suffix_re_rejects_other_names(stem):
    assert not pt.SUFFIX_RE.search(stem)


@pytest.mark.parametrize("name", ["vest_co.png", "vest_nohq.TGA", "vest_smdi.Png"])
def test_validate_input_accepts(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(b"")
    pt.validate_input(path)  # no SystemExit


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


def test_main_exits_1_on_partial_failure(monkeypatch, tmp_path, capsys):
    good = tmp_path / "good_co.png"
    bad = tmp_path / "bad_nohq.png"
    for p in (good, bad):
        p.write_bytes(b"")
    monkeypatch.setattr(pt.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(pt, "resolve_image_to_paa", lambda: tmp_path / "ImageToPAA.exe")
    monkeypatch.setattr(pt, "pack_one", lambda exe, src: src == good)
    monkeypatch.setattr("sys.argv", ["pack_texture.py", str(good), str(bad)])
    assert pt.main() == 1
    assert "1 of 2 textures packed." in capsys.readouterr().out
