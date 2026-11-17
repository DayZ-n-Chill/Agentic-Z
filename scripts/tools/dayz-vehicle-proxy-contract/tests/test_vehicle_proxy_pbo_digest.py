"""digest_pbo: the header properties and per-entry SHA-256 that tools/dayz-pbo-diff reads.

Stdlib only, so it runs where the rest of this suite's dependencies are absent.
"""

from __future__ import annotations

import hashlib
import pathlib
import struct
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from vehicle_proxy import pbo as pbo_mod  # noqa: E402
from vehicle_proxy.pbo import (  # noqa: E402
    PboDigest,
    PboFormatError,
    digest_pbo,
    parse_pbo,
    read_entry,
)


_VERS = 0x56657273
_COMPRESSED = 0x43707273


def _pbo_bytes(entries, properties=(), *, trailer=b""):
    header = bytearray()
    if properties:
        header.extend(b"\x00" + struct.pack("<5I", _VERS, 0, 0, 0, 0))
        for key, value in properties:
            header.extend(key.encode("ascii") + b"\x00")
            header.extend(value.encode("ascii") + b"\x00")
        header.append(0)
    payload = bytearray()
    for name, data, packing in entries:
        header.extend(name.encode("ascii") + b"\x00")
        header.extend(struct.pack("<5I", packing, len(data), 0, 0, len(data)))
        payload.extend(data)
    header.extend(b"\x00" + struct.pack("<5I", 0, 0, 0, 0, 0))
    return bytes(header + payload + trailer)


class TestDigestPbo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, entries, properties=(), *, trailer=b""):
        path = self.root / name
        path.write_bytes(_pbo_bytes(entries, properties, trailer=trailer))
        return path

    def test_properties_in_file_order_and_payload_hashes(self):
        properties = (("prefix", "fixture\\addon"), ("product", "dayz ugc"), ("version", "7"))
        entries = [
            ("config.bin", b"\x00raP-fixture", 0),
            ("data\\one.paa", b"one", 0),
            ("data/two.paa", b"", 0),
        ]
        path = self._write("a.pbo", entries, properties, trailer=b"\x00" + b"\x11" * 20)

        digest = digest_pbo(path)

        self.assertIsInstance(digest, PboDigest)
        self.assertEqual(properties, digest.properties)
        self.assertEqual(
            [(name, hashlib.sha256(data).hexdigest()) for name, data, _ in entries],
            [(entry.name, sha256) for entry, sha256 in digest.entries],
        )

    def test_entries_are_the_ones_parse_pbo_and_read_entry_see(self):
        path = self._write(
            "a.pbo",
            [("a.c", b"class A {};", 0), ("b\\c.c", b"class C {};", 0)],
            (("prefix", "x"),),
        )

        digest = digest_pbo(path)

        self.assertEqual(parse_pbo(path), tuple(entry for entry, _ in digest.entries))
        for entry, sha256 in digest.entries:
            self.assertEqual(hashlib.sha256(read_entry(path, entry)).hexdigest(), sha256)

    def test_no_vers_block_gives_no_properties(self):
        path = self._write("a.pbo", [("a.c", b"x", 0)])

        self.assertEqual((), digest_pbo(path).properties)

    def test_properties_outnumbering_entries_stay_properties(self):
        properties = tuple((f"key{index:03d}", f"value{index}") for index in range(150))
        path = self._write("a.pbo", [("only.c", b"x", 0)], properties)

        digest = digest_pbo(path)

        self.assertEqual(properties, digest.properties)
        self.assertEqual(["only.c"], [entry.name for entry, _ in digest.entries])

    def test_compressed_entry_fails_closed(self):
        path = self._write("a.pbo", [("a.c", b"x", 0), ("b.c", b"packed", _COMPRESSED)])

        with self.assertRaises(PboFormatError) as raised:
            digest_pbo(path)

        self.assertIn("compressed", str(raised.exception))
        self.assertEqual(4, raised.exception.exit_code)

    def test_truncated_entry_data_fails_closed(self):
        data = _pbo_bytes([("a.c", b"0123456789", 0)])
        path = self.root / "a.pbo"
        path.write_bytes(data[:-3])

        with self.assertRaises(PboFormatError):
            digest_pbo(path)

    def test_three_payload_bytes_eaten_from_the_trailer_are_refused(self):
        trailer = b"\x00" + b"\x11" * 20
        data = _pbo_bytes([("a.c", b"0123456789", 0)], trailer=trailer)
        path = self.root / "a.pbo"
        path.write_bytes(data[: -len(trailer) - 3] + trailer)

        with self.assertRaises(PboFormatError) as raised:
            digest_pbo(path)

        self.assertIn("leftover", str(raised.exception))

    def test_five_bytes_after_the_trailer_are_refused(self):
        path = self._write(
            "a.pbo",
            [("a.c", b"x", 0)],
            trailer=b"\x00" + b"\x11" * 20 + b"xxxxx",
        )

        with self.assertRaises(PboFormatError) as raised:
            digest_pbo(path)

        self.assertIn("26", str(raised.exception))

    def test_no_trailer_is_accepted(self):
        path = self._write("a.pbo", [("a.c", b"x", 0)], trailer=b"")

        self.assertEqual(["a.c"], [entry.name for entry, _ in digest_pbo(path).entries])

    def test_twenty_one_byte_trailer_is_accepted(self):
        path = self._write(
            "a.pbo", [("a.c", b"x", 0)], trailer=b"\x00" + b"\x11" * 20
        )

        self.assertEqual(["a.c"], [entry.name for entry, _ in digest_pbo(path).entries])

    def test_twenty_one_byte_trailer_without_the_zero_marker_is_refused(self):
        path = self._write(
            "a.pbo", [("a.c", b"x", 0)], trailer=b"X" + b"Z" * 20
        )

        with self.assertRaises(PboFormatError) as raised:
            digest_pbo(path)

        self.assertIn("do not start with 0x00", str(raised.exception))

    def test_file_that_changes_while_hashing_is_refused(self):
        path = self._write("a.pbo", [("a.c", b"payload", 0)])
        original = pbo_mod._sha256_entry_handle

        def mutate_after_hash(handle, entry):
            digest = original(handle, entry)
            path.write_bytes(path.read_bytes() + b"x")
            return digest

        with mock.patch.object(pbo_mod, "_sha256_entry_handle", mutate_after_hash):
            with self.assertRaises(PboFormatError) as raised:
                digest_pbo(path)

        self.assertIn("PBO snapshot changed while reading", str(raised.exception))

    def test_missing_file_is_a_format_error(self):
        with self.assertRaises(PboFormatError):
            digest_pbo(self.root / "absent.pbo")


if __name__ == "__main__":
    unittest.main()
