from __future__ import annotations

from dataclasses import replace
import os
import pathlib
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from vehicle_proxy.pbo import (
    PboFormatError,
    parse_pbo,
    read_entry,
    verify_deployed_closure,
    verify_paths_against_pbo,
)
from vehicle_proxy_fixtures import write_test_pbo


_VERS = 0x56657273


def _write_custom_pbo(
    path: pathlib.Path,
    entries: list[tuple[str, int, bytes, int | None]],
    *,
    extensions: tuple[tuple[str, str], ...] = (),
    include_terminator: bool = True,
) -> None:
    header = bytearray()
    payload = bytearray()
    if extensions:
        header.extend(b"\x00" + struct.pack("<5I", _VERS, 0, 0, 0, 0))
        for key, value in extensions:
            header.extend(key.encode("ascii") + b"\x00")
            header.extend(value.encode("ascii") + b"\x00")
        header.append(0)
    for name, packing, data, declared_size in entries:
        encoded = name.encode("ascii")
        size = len(data) if declared_size is None else declared_size
        header.extend(encoded + b"\x00")
        header.extend(struct.pack("<5I", packing, len(data), 0, 0, size))
        payload.extend(data)
    if include_terminator:
        header.extend(b"\x00" + struct.pack("<5I", 0, 0, 0, 0, 0))
    path.write_bytes(bytes(header + payload))


class TestPboClosure(unittest.TestCase):
    def test_exact_entry_hash_passes_and_stale_entry_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            disk = root / "data" / "proxy" / "body.p3d"
            disk.parent.mkdir(parents=True)
            disk.write_bytes(b"MLOD-current")
            pbo = root / "fixture.pbo"
            write_test_pbo(pbo, {"data\\proxy\\body.p3d": b"MLOD-current"})
            self.assertEqual([], verify_paths_against_pbo(pbo, root, [disk]))

            _write_custom_pbo(
                pbo,
                [("DATA/PROXY/BODY.P3D", 0, b"MLOD-current", None)],
            )
            self.assertEqual([], verify_paths_against_pbo(pbo, root, [disk]))

            write_test_pbo(pbo, {"data\\proxy\\body.p3d": b"MLOD-stale"})
            findings = verify_paths_against_pbo(pbo, root, [disk])
            self.assertEqual("PBO-HASH-MISMATCH", findings[0].code)
            self.assertEqual("data\\proxy\\body.p3d", findings[0].path)
            self.assertNotEqual(
                findings[0].source_sha256, findings[0].deployed_sha256
            )

    def test_product_extensions_preserve_data_offsets_and_entry_reads(self):
        with tempfile.TemporaryDirectory() as td:
            pbo = pathlib.Path(td) / "fixture.pbo"
            _write_custom_pbo(
                pbo,
                [
                    ("data/one.bin", 0, b"one", None),
                    ("data\\two.bin", 0, b"two-two", None),
                ],
                extensions=(("$PBOPREFIX$", "FIXTURE"), ("build", "test")),
            )

            entries = parse_pbo(pbo)

            self.assertEqual(
                ["data/one.bin", "data\\two.bin"],
                [entry.name for entry in entries],
            )
            self.assertEqual(entries[0].data_offset + 3, entries[1].data_offset)
            self.assertEqual(b"one", read_entry(pbo, entries[0]))
            self.assertEqual(b"two-two", read_entry(pbo, entries[1]))

    def test_read_entry_rejects_tampered_name_offset_and_descriptor(self):
        with tempfile.TemporaryDirectory() as td:
            pbo = pathlib.Path(td) / "fixture.pbo"
            write_test_pbo(pbo, {"data\\body.p3d": b"AAAA"})
            entry = parse_pbo(pbo)[0]
            forged_entries = {
                "name": replace(entry, name="data\\forged.p3d"),
                "offset": replace(entry, data_offset=entry.data_offset + 1),
                "descriptor": replace(
                    entry, original_size=entry.original_size + 1
                ),
            }

            for label, forged in forged_entries.items():
                with self.subTest(label=label):
                    with self.assertRaises(PboFormatError) as raised:
                        read_entry(pbo, forged)
                    self.assertEqual(4, raised.exception.exit_code)

    def test_read_entry_rejects_replaced_same_header_different_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            pbo = root / "fixture.pbo"
            replacement = root / "replacement.pbo"
            write_test_pbo(pbo, {"data\\body.p3d": b"AAAA"})
            entry = parse_pbo(pbo)[0]
            before = pbo.stat()

            write_test_pbo(replacement, {"data\\body.p3d": b"BBBB"})
            os.utime(
                replacement,
                ns=(before.st_atime_ns, before.st_mtime_ns),
            )
            self.assertEqual(
                pbo.read_bytes()[: entry.data_offset],
                replacement.read_bytes()[: entry.data_offset],
            )
            replacement.replace(pbo)

            with self.assertRaises(PboFormatError) as raised:
                read_entry(pbo, entry)
            self.assertEqual(4, raised.exception.exit_code)

    def test_verify_rejects_pbo_changed_during_single_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            source = root / "data" / "body.p3d"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"AAAA")
            pbo = root / "fixture.pbo"
            write_test_pbo(pbo, {"data\\body.p3d": b"AAAA"})
            entry = parse_pbo(pbo)[0]

            def changing_paths():
                yield source
                before = pbo.stat()
                with pbo.open("r+b") as handle:
                    handle.seek(entry.data_offset)
                    handle.write(b"BBBB")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.utime(
                    pbo,
                    ns=(before.st_atime_ns, before.st_mtime_ns + 2_000_000_000),
                )

            with self.assertRaises(PboFormatError) as raised:
                verify_paths_against_pbo(pbo, root, changing_paths())
            self.assertEqual(4, raised.exception.exit_code)

    def test_rejects_nonzero_vers_and_terminator_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for index in range(4):
                with self.subTest(control="Vers", field=index):
                    fields = [0, 0, 0, 0]
                    fields[index] = 1
                    pbo = root / f"vers-{index}.pbo"
                    pbo.write_bytes(
                        b"\x00"
                        + struct.pack("<5I", _VERS, *fields)
                        + b"\x00"
                        + b"\x00"
                        + struct.pack("<5I", 0, 0, 0, 0, 0)
                    )
                    with self.assertRaises(PboFormatError) as raised:
                        parse_pbo(pbo)
                    self.assertEqual(4, raised.exception.exit_code)

            for index in range(5):
                with self.subTest(control="terminator", field=index):
                    fields = [0, 0, 0, 0, 0]
                    fields[index] = 1
                    pbo = root / f"terminator-{index}.pbo"
                    pbo.write_bytes(b"\x00" + struct.pack("<5I", *fields))
                    with self.assertRaises(PboFormatError) as raised:
                        parse_pbo(pbo)
                    self.assertEqual(4, raised.exception.exit_code)

    def test_missing_entry_returns_stable_finding(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            disk = root / "data" / "missing.p3d"
            disk.parent.mkdir(parents=True)
            disk.write_bytes(b"source")
            pbo = root / "fixture.pbo"
            write_test_pbo(pbo, {"data\\other.p3d": b"source"})

            findings = verify_paths_against_pbo(pbo, root, [disk])

            self.assertEqual(1, len(findings))
            self.assertEqual("PBO-ENTRY-MISSING", findings[0].code)
            self.assertEqual("data\\missing.p3d", findings[0].path)
            self.assertIsNotNone(findings[0].source_sha256)
            self.assertIsNone(findings[0].deployed_sha256)

    def test_compressed_required_entry_is_format_error_not_hash_input(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            disk = root / "data" / "body.p3d"
            disk.parent.mkdir(parents=True)
            disk.write_bytes(b"source-unpacked")
            pbo = root / "fixture.pbo"
            _write_custom_pbo(
                pbo,
                [("data\\body.p3d", 0x43707273, b"source-unpacked", None)],
            )

            with self.assertRaises(PboFormatError) as raised:
                verify_paths_against_pbo(pbo, root, [disk])

            self.assertEqual(4, raised.exception.exit_code)
            self.assertIn("compressed", str(raised.exception).lower())

    def test_rejects_truncated_header_missing_terminator_and_out_of_range_data(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            cases = {
                "asciiz": b"unterminated-name",
                "header": b"name\x00" + b"\x00" * 19,
            }
            for label, content in cases.items():
                with self.subTest(label=label):
                    path = root / f"{label}.pbo"
                    path.write_bytes(content)
                    with self.assertRaises(PboFormatError) as raised:
                        parse_pbo(path)
                    self.assertEqual(4, raised.exception.exit_code)

            no_terminator = root / "no-terminator.pbo"
            _write_custom_pbo(
                no_terminator,
                [("data\\body.p3d", 0, b"payload-without-zero", None)],
                include_terminator=False,
            )
            with self.assertRaises(PboFormatError) as raised:
                parse_pbo(no_terminator)
            self.assertEqual(4, raised.exception.exit_code)

            bad_range = root / "bad-range.pbo"
            _write_custom_pbo(
                bad_range,
                [("data\\body.p3d", 0, b"tiny", 100)],
            )
            with self.assertRaises(PboFormatError) as raised:
                parse_pbo(bad_range)
            self.assertEqual(4, raised.exception.exit_code)

    def test_rejects_duplicate_normalized_name_and_invalid_pbo_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            duplicate = root / "duplicate.pbo"
            _write_custom_pbo(
                duplicate,
                [
                    ("Data/Body.p3d", 0, b"first", None),
                    ("data\\body.P3D", 0, b"second", None),
                ],
            )
            with self.assertRaises(PboFormatError) as raised:
                parse_pbo(duplicate)
            self.assertEqual(4, raised.exception.exit_code)

            invalid = root / "invalid-path.pbo"
            _write_custom_pbo(
                invalid,
                [("data\\..\\outside.p3d", 0, b"outside", None)],
            )
            with self.assertRaises(PboFormatError) as raised:
                parse_pbo(invalid)
            self.assertEqual(4, raised.exception.exit_code)

            invalid_component = root / "invalid-component.pbo"
            _write_custom_pbo(
                invalid_component,
                [("data\\bad:name.p3d", 0, b"invalid", None)],
            )
            with self.assertRaises(PboFormatError) as raised:
                parse_pbo(invalid_component)
            self.assertEqual(4, raised.exception.exit_code)

    def test_rejects_source_path_escape_and_missing_source(self):
        with tempfile.TemporaryDirectory() as td:
            parent = pathlib.Path(td)
            root = parent / "addon"
            root.mkdir()
            outside = parent / "outside.p3d"
            outside.write_bytes(b"outside")
            pbo = parent / "fixture.pbo"
            write_test_pbo(pbo, {"outside.p3d": b"outside"})

            for source in (outside, root / "missing.p3d"):
                with self.subTest(source=source.name):
                    with self.assertRaises(PboFormatError) as raised:
                        verify_paths_against_pbo(pbo, root, [source])
                    self.assertEqual(4, raised.exception.exit_code)

    def test_deployed_closure_checks_host_and_unique_proxy_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            host = root / "data" / "host.p3d"
            proxy = root / "data" / "proxy" / "body.p3d"
            proxy.parent.mkdir(parents=True)
            host.write_bytes(b"host-current")
            proxy.write_bytes(b"proxy-current")
            pbo = root / "fixture.pbo"
            write_test_pbo(
                pbo,
                {
                    "data\\host.p3d": b"host-current",
                    "data\\proxy\\body.p3d": b"proxy-current",
                },
            )
            manifest = SimpleNamespace(
                deployed_pbo=pbo,
                addon_root=root,
                host_p3d=host,
            )
            repeated = SimpleNamespace(proxy_path=proxy)

            self.assertEqual(
                [], verify_deployed_closure(manifest, (repeated, repeated))
            )

            write_test_pbo(
                pbo,
                {
                    "data\\host.p3d": b"host-current",
                    "data\\proxy\\body.p3d": b"proxy-stale",
                },
            )
            findings = verify_deployed_closure(manifest, (repeated, repeated))
            self.assertEqual(1, len(findings))
            self.assertEqual("data\\proxy\\body.p3d", findings[0].path)


if __name__ == "__main__":
    unittest.main()
