"""Tests for inventory.py: classifying a PBO from its header, and the SKILL.md reference table."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import struct
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
# Loaded by path under a unique name, so it cannot clash with another skill's module.
_spec = importlib.util.spec_from_file_location("dayz_pbo_inventory_under_test", HERE / "inventory.py")
inv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inv)

VERS = 0x56657273
CPRS = 0x43707273


def write_pbo(path: Path, files: dict[str, bytes], prefix: str | None = "TheirMod", trailer: bool = True,
              compressed: tuple[str, ...] = ()) -> Path:
    """A PBO as AddonBuilder writes it: properties record, entry table, data, SHA-1 trailer."""
    out = b""
    if prefix is not None:
        out += b"\x00" + struct.pack("<5I", VERS, 0, 0, 0, 0) + b"prefix\x00" + prefix.encode("latin-1") + b"\x00\x00"
    for name, data in files.items():
        packing = CPRS if name in compressed else 0
        out += name.encode("latin-1") + b"\x00" + struct.pack("<5I", packing, 0, 0, 1700000000, len(data))
    out += b"\x00" + struct.pack("<5I", 0, 0, 0, 0, 0)
    out += b"".join(files.values())
    if trailer:
        out += b"\x00" + hashlib.sha1(out).digest()
    path.write_bytes(out)
    return path


MOD_FILES = {
    "config.bin": b"\x00raP1234",
    "Scripts\\4_World\\Plane.c": b"class Plane {};",
    "data\\plane.p3d": b"ODOL\x38\x00\x00\x00",
    "data\\plane_co.paa": b"paa",
}


def test_config_with_scripts_or_models_is_a_mod(tmp_path):
    info = inv.inventory(write_pbo(tmp_path / "a.pbo", MOD_FILES))
    assert info["kind"] == inv.MOD
    assert info["prefix"] == "TheirMod"
    assert info["entries"] == 4
    assert info["bytes"] == sum(len(d) for d in MOD_FILES.values())
    assert info["config"] == ["config.bin"]
    assert info["suffixes"][".c"] == 1 and info["suffixes"][".p3d"] == 1
    assert info["trailer_ok"] is True
    assert info["unsafe"] == [] and info["compressed"] == 0


def test_config_alone_is_config_only(tmp_path):
    # The 662-byte case: a scripts mod packed without its .c files still mounts.
    info = inv.inventory(write_pbo(tmp_path / "a.pbo", {"config.bin": b"\x00raP1234"}))
    assert info["kind"] == inv.CONFIG_ONLY


def test_empty_config_with_archives_is_a_source_distribution(tmp_path):
    files = {"config.bin": b"", "planes\\spitfire.rar": b"Rar!", "planes\\spitfire.fbx": b"fbx"}
    info = inv.inventory(write_pbo(tmp_path / "a.pbo", files))
    assert info["kind"] == inv.SOURCE
    assert info["empty_config"] == ["config.bin"]
    assert info["config"] == []


def test_no_config_and_no_source_art_is_data_only(tmp_path):
    info = inv.inventory(write_pbo(tmp_path / "a.pbo", {"data\\a_co.paa": b"paa", "data\\a.rvmat": b"x"}))
    assert info["kind"] == inv.DATA


def test_nested_config_counts(tmp_path):
    files = {"sub\\Config.CPP": b"class CfgPatches {};", "sub\\gui\\menu.layout": b"FrameWidgetClass {}"}
    assert inv.inventory(write_pbo(tmp_path / "a.pbo", files))["kind"] == inv.MOD


@pytest.mark.parametrize("name, reason", [
    ("..\\evil.c", "'..' segment"),
    ("scripts/../../evil.c", "'..' segment"),
    ("\\abs.c", "absolute path"),
    ("/abs.c", "absolute path"),
    ("C:\\Windows\\x.c", "drive letter"),
    ("scripts\\COM1.c", "Windows device name"),
    ("nul", "Windows device name"),
    ("scripts\\a\x07b.c", "control character"),
])
def test_unsafe_entry_names_are_named(name, reason):
    assert inv.unsafe_reason(name) == reason


@pytest.mark.parametrize("name", ["scripts\\4_World\\a.c", "data\\common.paa", "config.bin", "a..b.c", "console.c"])
def test_ordinary_entry_names_are_safe(name):
    assert inv.unsafe_reason(name) is None


def test_unsafe_guid_and_compressed_entries_are_counted(tmp_path):
    files = {
        "config.bin": b"\x00raP",
        "..\\out.c": b"x",
        "{0A1B2C3D-0000-1111-2222-333344445555}.c": b"y",
        "gui\\a.layout": b"zz",
    }
    info = inv.inventory(write_pbo(tmp_path / "a.pbo", files, compressed=("gui\\a.layout",)))
    assert info["unsafe"] == [{"name": "..\\out.c", "reason": "'..' segment"}]
    assert info["guid_names"] == 1
    assert info["compressed"] == 1


def test_missing_trailer_is_reported_and_can_be_skipped(tmp_path):
    path = write_pbo(tmp_path / "a.pbo", MOD_FILES, trailer=False)
    assert inv.inventory(path)["trailer_ok"] is False
    assert inv.inventory(path, check_trailer=False)["trailer_ok"] is None


def test_find_pbos_walks_folders_and_keeps_named_files(tmp_path):
    (tmp_path / "x" / "deep").mkdir(parents=True)
    a = write_pbo(tmp_path / "x" / "deep" / "A.PBO", MOD_FILES)
    b = write_pbo(tmp_path / "b.pbo", MOD_FILES)
    (tmp_path / "x" / "notes.txt").write_text("no", encoding="utf-8")
    assert inv.find_pbos([str(tmp_path / "x"), str(b)]) == [a, b]


def test_main_prints_a_report_and_a_summary(tmp_path, capsys):
    write_pbo(tmp_path / "mod.pbo", MOD_FILES)
    write_pbo(tmp_path / "src.pbo", {"planes\\a.zip": b"PK"}, prefix=None)
    assert inv.main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "kind:   deployable mod" in out
    assert "kind:   source asset distribution" in out
    assert "prefix: (none)" in out
    assert "2 PBO(s): 1 mod, 1 source-distribution" in out


def test_main_warns_about_obfuscated_and_compressed_entries(tmp_path, capsys):
    files = {"config.bin": b"\x00raP", "..\\out.c": b"x", "gui\\a.layout": b"zz"}
    write_pbo(tmp_path / "a.pbo", files, compressed=("gui\\a.layout",), trailer=False)
    assert inv.main([str(tmp_path / "a.pbo")]) == 0
    out = capsys.readouterr().out
    assert "1 compressed entry" in out
    assert "1 unsafe entry name(s)" in out and "'..' segment" in out
    assert "no valid checksum trailer" in out


def test_main_json_lists_every_pbo(tmp_path, capsys):
    write_pbo(tmp_path / "mod.pbo", MOD_FILES)
    assert inv.main([str(tmp_path), "--json", "--no-trailer"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [d["kind"] for d in data] == [inv.MOD]
    assert data[0]["trailer_ok"] is None


def test_main_fails_on_an_unreadable_pbo_and_goes_on(tmp_path, capsys):
    (tmp_path / "bad.pbo").write_bytes(b"not a pbo")
    write_pbo(tmp_path / "good.pbo", MOD_FILES)
    assert inv.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "not a readable PBO" in out
    assert "2 PBO(s): 1 mod; 1 unreadable" in out


def test_main_fails_when_no_pbo_is_found(tmp_path, capsys):
    assert inv.main([str(tmp_path)]) == 1
    assert "No .pbo file found" in capsys.readouterr().out


def test_skill_reference_table_lists_every_reference_file():
    # A reference file missing from SKILL.md's table is never opened; a row without a file is a dead end.
    listed = set(re.findall(r"`references/([\w.-]+\.md)`", (HERE / "SKILL.md").read_text(encoding="utf-8")))
    on_disk = {p.name for p in (HERE / "references").glob("*.md")}
    assert on_disk, "skills/dayz-pbo-reverse-engineering/references holds no .md file"
    assert listed == on_disk
