"""Tests for pbo_entries.py: header properties, the entry table and the checksum trailer."""
from __future__ import annotations

import hashlib
import importlib.util
import struct
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
# Loaded by path and left out of sys.modules, the way build.py loads it.
_spec = importlib.util.spec_from_file_location("dayz_pbo_entries_under_test", HERE / "pbo_entries.py")
pe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pe)


def pbo_bytes(files: dict[str, bytes], properties: dict[str, str] | None = None, trailer: bool = True,
              compressed: tuple[str, ...] = ()) -> bytes:
    """A PBO as AddonBuilder writes it: properties record, entry table, data, SHA-1 trailer."""
    out = b""
    if properties is not None:
        out += b"\x00" + struct.pack("<5I", pe.VERS_MAGIC, 0, 0, 0, 0)
        for key, value in properties.items():
            out += key.encode("latin-1") + b"\x00" + value.encode("latin-1") + b"\x00"
        out += b"\x00"
    for name, data in files.items():
        packing = pe.CPRS_MAGIC if name in compressed else 0
        out += name.encode("latin-1") + b"\x00" + struct.pack("<5I", packing, 0, 0, 1700000000, len(data))
    out += b"\x00" + struct.pack("<5I", 0, 0, 0, 0, 0)
    out += b"".join(files.values())
    if trailer:
        out += b"\x00" + hashlib.sha1(out).digest()
    return out


def write_pbo(path: Path, files: dict[str, bytes], **kwargs) -> Path:
    path.write_bytes(pbo_bytes(files, **kwargs))
    return path


FILES = {"config.bin": b"\x00raP....", "scripts\\4_World\\Thing.c": b"class Thing {};", "data\\a.p3d": b"ODOL" + b"\x38\0\0\0"}


def test_reads_properties_entries_and_trailer(tmp_path):
    pbo = pe.read_pbo(write_pbo(tmp_path / "MyMod.pbo", FILES, properties={"product": "dayz ugc", "prefix": "MyMod"}))
    assert pbo.properties == {"product": "dayz ugc", "prefix": "MyMod"}
    assert pbo.prefix == "MyMod"
    assert [e.name for e in pbo.entries] == list(FILES)
    assert [e.data_size for e in pbo.entries] == [len(d) for d in FILES.values()]
    assert pbo.trailer_ok is True
    assert not any(e.compressed for e in pbo.entries)


def test_entry_offsets_point_at_each_files_bytes(tmp_path):
    pbo = pe.read_pbo(write_pbo(tmp_path / "MyMod.pbo", FILES, properties={"prefix": "MyMod"}))
    assert [pe.read_entry(pbo, e) for e in pbo.entries] == list(FILES.values())


def test_names_compare_lower_case_with_backslashes(tmp_path):
    pbo = pe.read_pbo(write_pbo(tmp_path / "a.pbo", {"Scripts/4_World/Thing.C": b"x"}, properties={"prefix": "a"}))
    assert pbo.names() == {"scripts\\4_world\\thing.c"}


def test_pbo_without_a_properties_record_has_no_prefix(tmp_path):
    pbo = pe.read_pbo(write_pbo(tmp_path / "a.pbo", {"config.cpp": b"class CfgPatches {};"}))
    assert pbo.properties == {} and pbo.prefix == ""
    assert [e.name for e in pbo.entries] == ["config.cpp"]


def test_compressed_entry_is_flagged(tmp_path):
    pbo = pe.read_pbo(write_pbo(tmp_path / "a.pbo", {"a.layout": b"zz", "b.c": b"y"}, properties={}, compressed=("a.layout",)))
    assert [e.compressed for e in pbo.entries] == [True, False]


def test_missing_trailer_is_reported_not_raised(tmp_path):
    pbo = pe.read_pbo(write_pbo(tmp_path / "a.pbo", FILES, properties={"prefix": "a"}, trailer=False))
    assert pbo.trailer_ok is False
    assert len(pbo.entries) == len(FILES)


def test_a_changed_byte_breaks_the_trailer(tmp_path):
    raw = bytearray(pbo_bytes(FILES, properties={"prefix": "a"}))
    raw[-30] ^= 0xFF  # a byte of the packed files, 9 bytes before the trailer
    path = tmp_path / "a.pbo"
    path.write_bytes(bytes(raw))
    assert pe.read_pbo(path).trailer_ok is False


def test_trailer_check_can_be_skipped(tmp_path):
    assert pe.read_pbo(write_pbo(tmp_path / "a.pbo", FILES, properties={}), check_trailer=False).trailer_ok is None


@pytest.mark.parametrize("raw, needle", [
    (b"pbo", "ends inside an entry name"),
    (b"config.cpp\x00\x00\x00", "ends inside the entry table"),
    (b"x" * 2000, "longer than"),
])
def test_malformed_files_raise_pbo_error(tmp_path, raw, needle):
    path = tmp_path / "bad.pbo"
    path.write_bytes(raw)
    with pytest.raises(pe.PboError) as exc:
        pe.read_pbo(path)
    assert needle in str(exc.value)


def test_entry_table_longer_than_the_file_is_a_truncated_pbo(tmp_path):
    raw = pbo_bytes({"big.paa": b"x" * 500}, properties={"prefix": "a"}, trailer=False)
    path = tmp_path / "cut.pbo"
    path.write_bytes(raw[:-400])
    with pytest.raises(pe.PboError) as exc:
        pe.read_pbo(path)
    assert "truncated" in str(exc.value)


def test_second_properties_record_is_refused(tmp_path):
    vers = b"\x00" + struct.pack("<5I", pe.VERS_MAGIC, 0, 0, 0, 0) + b"prefix\x00a\x00\x00"
    path = tmp_path / "twice.pbo"
    path.write_bytes(vers + vers + b"\x00" + struct.pack("<5I", 0, 0, 0, 0, 0))
    with pytest.raises(pe.PboError) as exc:
        pe.read_pbo(path)
    assert "second properties record" in str(exc.value)
