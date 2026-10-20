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


def test_gate_reports_missing_preflight(monkeypatch, tmp_path):
    # Importing the module must not need preflight.py, so this check can fire.
    monkeypatch.setattr(pt, "PREFLIGHT", tmp_path / "preflight.py")
    monkeypatch.setattr(pt, "REPO_ROOT", tmp_path)
    with pytest.raises(SystemExit) as exc:
        pt.gate_on_preflight()
    assert "dayz-preflight not found" in str(exc.value)
