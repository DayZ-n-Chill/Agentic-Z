"""dayz-pbo-diff on synthetic PBOs written by the tests. Stdlib only."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest


TOOL_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_ROOT))

import pbo_diff  # noqa: E402


_VERS = 0x56657273
_COMPRESSED = 0x43707273
_PROPS = (("prefix", "fixture\\addon"), ("product", "dayz ugc"))


def pbo_bytes(entries, properties=_PROPS, *, sizes=None, trailer=b"\x00" + b"\x5a" * 20):
    """A PBO as a sequence of (name, data[, packing]); sizes overrides declared sizes."""
    header = bytearray()
    if properties:
        header.extend(b"\x00" + struct.pack("<5I", _VERS, 0, 0, 0, 0))
        for key, value in properties:
            header.extend(key.encode("ascii") + b"\x00" + value.encode("ascii") + b"\x00")
        header.append(0)
    payload = bytearray()
    for index, item in enumerate(entries):
        name, data = item[0], item[1]
        packing = item[2] if len(item) > 2 else 0
        size = len(data) if sizes is None or index not in sizes else sizes[index]
        header.extend(name.encode("ascii") + b"\x00")
        header.extend(struct.pack("<5I", packing, len(data), 0, 0, size))
        payload.extend(data)
    header.extend(b"\x00" + struct.pack("<5I", 0, 0, 0, 0, 0))
    return bytes(header + payload + trailer)


BASE = [
    ("config.bin", b"\x00raP fixture config"),
    ("data\\layers\\l_000_000.paa", b"layer-0"),
    ("data\\layers\\l_000_001.paa", b"layer-1"),
    ("data\\water.paa", b"water"),
    ("world.wrp", b"OPRW fixture world"),
]


def run(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = pbo_diff.main(argv)
        except SystemExit as exit_:
            code = exit_.code
    return code, stdout.getvalue(), stderr.getvalue()


class _Case(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, entries, properties=_PROPS, **kwargs):
        path = self.root / name
        path.write_bytes(pbo_bytes(entries, properties, **kwargs))
        return path

    def diff(self, old, new, *extra):
        out = self.root / f"diff-{old.stem}-{new.stem}.json"
        code, stdout, stderr = run(["--old", str(old), "--new", str(new), "--out", str(out), *extra])
        self.assertEqual(0, code, stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        return report, stdout

    def refused(self, old, new):
        out = self.root / "refused.json"
        code, _, stderr = run(["--old", str(old), "--new", str(new), "--out", str(out)])
        self.assertEqual(1, code)
        self.assertFalse(out.exists(), "a refused diff must write nothing")
        self.assertTrue(stderr.startswith("error: "), stderr)
        return stderr


class TestDiff(_Case):
    def test_identical(self):
        report, stdout = self.diff(self.write("old.pbo", BASE), self.write("new.pbo", BASE))

        self.assertEqual([5, 5], report["entries"])
        self.assertTrue(report["props_equal"])
        self.assertEqual([], report["only_old"])
        self.assertEqual([], report["only_new"])
        self.assertEqual([], report["differing"])
        self.assertEqual(0, report["differing_count"])
        self.assertEqual(report["differing"], report["differing_not_ignored"])
        self.assertEqual(0, json.loads(stdout)["differing_count"])

    def test_one_entry_changed(self):
        new = list(BASE)
        new[4] = ("world.wrp", b"OPRW fixture world, edited")

        report, _ = self.diff(self.write("old.pbo", BASE), self.write("new.pbo", new))

        self.assertEqual(["world.wrp"], report["differing"])
        self.assertEqual(1, report["differing_count"])
        self.assertEqual([], report["only_old"] + report["only_new"])

    def test_only_old_and_only_new_are_part_of_differing(self):
        new = [item for item in BASE if item[0] != "data\\water.paa"] + [("navmesh\\world.nm", b"TESM")]

        report, _ = self.diff(self.write("old.pbo", BASE), self.write("new.pbo", new))

        self.assertEqual(["data/water.paa"], report["only_old"])
        self.assertEqual(["navmesh/world.nm"], report["only_new"])
        self.assertEqual(["data/water.paa", "navmesh/world.nm"], report["differing"])
        self.assertEqual([5, 5], report["entries"])

    def test_names_use_forward_slashes_and_match_across_separators(self):
        new = [(name.replace("\\", "/"), data) for name, data in BASE]

        report, _ = self.diff(self.write("old.pbo", BASE), self.write("new.pbo", new))

        self.assertEqual([], report["differing"])

    def test_a_case_only_rename_is_reported_on_both_sides(self):
        new = list(BASE)
        new[3] = ("data\\Water.paa", b"water")

        report, _ = self.diff(self.write("old.pbo", BASE), self.write("new.pbo", new))

        self.assertEqual(["data/water.paa"], report["only_old"])
        self.assertEqual(["data/Water.paa"], report["only_new"])

    def test_properties_differ(self):
        props = (("prefix", "fixture\\other"), ("product", "dayz ugc"))

        report, _ = self.diff(self.write("old.pbo", BASE), self.write("new.pbo", BASE, props))

        self.assertFalse(report["props_equal"])
        self.assertEqual([list(item) for item in _PROPS], report["props_old"])
        self.assertEqual([list(item) for item in props], report["props_new"])
        self.assertEqual([], report["differing"])

    def test_property_order_counts(self):
        report, _ = self.diff(
            self.write("old.pbo", BASE), self.write("new.pbo", BASE, tuple(reversed(_PROPS)))
        )

        self.assertFalse(report["props_equal"])

    def test_few_entries(self):
        # The source script told the entry table from the properties by size (more
        # than 100 items): a PBO with 100 entries or fewer stopped it or swapped them.
        one = [("config.bin", b"\x00raP")]

        report, _ = self.diff(self.write("old.pbo", one), self.write("new.pbo", one))

        self.assertEqual([1, 1], report["entries"])
        self.assertTrue(report["props_equal"])

        report, _ = self.diff(self.write("e-old.pbo", []), self.write("e-new.pbo", one))
        self.assertEqual([0, 1], report["entries"])
        self.assertEqual(["config.bin"], report["only_new"])

    def test_more_properties_than_entries(self):
        props = tuple((f"key{index:03d}", str(index)) for index in range(150))
        few = [("a.c", b"a"), ("b.c", b"b")]

        report, _ = self.diff(self.write("old.pbo", few, props), self.write("new.pbo", few, props))

        self.assertEqual([2, 2], report["entries"])
        self.assertEqual(150, len(report["props_old"]))

    def test_many_entries(self):
        many = [(f"data\\t_{index:03d}.paa", b"%d" % index) for index in range(150)]
        new = list(many)
        new[7] = ("data\\t_007.paa", b"changed")

        report, _ = self.diff(self.write("old.pbo", many), self.write("new.pbo", new))

        self.assertEqual([150, 150], report["entries"])
        self.assertEqual(["data/t_007.paa"], report["differing"])

    def test_ignore_prefix_filters_a_view_only(self):
        new = [(name, data + b"!") if "layers" in name or name == "world.wrp" else (name, data) for name, data in BASE]
        old_path, new_path = self.write("old.pbo", BASE), self.write("new.pbo", new)

        report, _ = self.diff(old_path, new_path, "--ignore-prefix", "DATA\\Layers\\")

        self.assertEqual(
            ["data/layers/l_000_000.paa", "data/layers/l_000_001.paa", "world.wrp"],
            report["differing"],
        )
        self.assertEqual(["world.wrp"], report["differing_not_ignored"])
        self.assertEqual(["DATA\\Layers\\"], report["ignored_prefixes"])

    def test_ignore_prefix_repeats(self):
        new = [(name, data + b"!") for name, data in BASE]

        report, _ = self.diff(
            self.write("old.pbo", BASE),
            self.write("new.pbo", new),
            "--ignore-prefix",
            "data/layers/",
            "--ignore-prefix",
            "world.",
        )

        self.assertEqual(["config.bin", "data/water.paa"], report["differing_not_ignored"])

    def test_stdout_summarises_long_lists(self):
        many = [(f"t_{index:02d}.c", b"%d" % index) for index in range(20)]
        changed = [(name, data + b"!") for name, data in many]

        report, stdout = self.diff(self.write("old.pbo", many), self.write("new.pbo", changed))

        self.assertEqual(20, report["differing_count"])
        self.assertEqual(20, len(report["differing"]))
        self.assertEqual("20 items", json.loads(stdout)["differing"])

    def test_stdout_lists_eleven_and_summarises_twelve(self):
        for count in (11, 12):
            with self.subTest(count=count):
                many = [(f"t_{index:02d}.c", b"%d" % index) for index in range(count)]
                changed = [(name, data + b"!") for name, data in many]
                report, stdout = self.diff(
                    self.write(f"old{count}.pbo", many),
                    self.write(f"new{count}.pbo", changed),
                )
                listed = json.loads(stdout)["differing"]
                self.assertEqual(count, report["differing_count"])
                if count == 12:
                    self.assertEqual("12 items", listed)
                else:
                    self.assertEqual(count, len(listed))
                    self.assertIsInstance(listed, list)

    def test_equal_payload_under_a_different_header_is_equal(self):
        # Only the payload is hashed: a timestamp in the entry header is not content.
        old = self.write("old.pbo", BASE)
        data = bytearray(old.read_bytes())
        marker = b"world.wrp\x00"
        at = data.index(marker) + len(marker) + 12  # packing, original size, reserved, then timestamp
        data[at:at + 4] = struct.pack("<I", 1_700_000_000)
        new = self.root / "new.pbo"
        new.write_bytes(bytes(data))

        report, _ = self.diff(old, new)

        self.assertNotEqual(hashlib.sha256(old.read_bytes()).digest(), hashlib.sha256(new.read_bytes()).digest())
        self.assertEqual([], report["differing"])


class TestRefusals(_Case):
    def test_compressed_entry(self):
        packed = list(BASE) + [("data\\packed.paa", b"lzss", _COMPRESSED)]

        stderr = self.refused(self.write("old.pbo", BASE), self.write("new.pbo", packed))

        self.assertIn("compressed", stderr)

    def test_unsafe_path(self):
        for name in ("data\\..\\outside.c", "\\rooted.c", "c:evil.c", "data\\\\empty-part.c"):
            with self.subTest(name=name):
                self.refused(self.write("old.pbo", BASE), self.write("new.pbo", [(name, b"x")]))

    def test_duplicate_name(self):
        duplicate = list(BASE) + [("DATA/WATER.PAA", b"again")]

        stderr = self.refused(self.write("old.pbo", duplicate), self.write("new.pbo", BASE))

        self.assertIn("duplicate", stderr)

    def test_truncated_data(self):
        truncated = self.write("new.pbo", BASE, sizes={4: 4096}, trailer=b"")

        self.refused(self.write("old.pbo", BASE), truncated)

    def test_three_payload_bytes_eaten_from_the_trailer_is_refused(self):
        trailer = b"\x00" + b"\x5a" * 20
        data = pbo_bytes(BASE, trailer=trailer)
        new = self.root / "new.pbo"
        new.write_bytes(data[: -len(trailer) - 3] + trailer)

        self.refused(self.write("old.pbo", BASE), new)

    def test_missing_input(self):
        self.refused(self.write("old.pbo", BASE), self.root / "absent.pbo")

    def test_existing_out_is_refused_and_kept(self):
        out = self.root / "diff.json"
        out.write_text("prior evidence\n", encoding="utf-8")
        old, new = self.write("old.pbo", BASE), self.write("new.pbo", BASE)

        code, _, stderr = run(["--old", str(old), "--new", str(new), "--out", str(out)])

        self.assertEqual(1, code)
        self.assertIn("already exists", stderr)
        self.assertEqual("prior evidence\n", out.read_text(encoding="utf-8"))

    def test_usage_error_is_exit_2(self):
        code, _, _ = run(["--old", "a.pbo"])

        self.assertEqual(2, code)


class TestScriptPath(_Case):
    def test_runs_as_a_script_from_another_directory(self):
        old, new = self.write("old.pbo", BASE), self.write("new.pbo", BASE)
        out = self.root / "diff.json"

        result = subprocess.run(
            [sys.executable, str(TOOL_ROOT / "pbo_diff.py"), "--old", str(old), "--new", str(new), "--out", str(out)],
            cwd=str(self.root),
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(0, json.loads(out.read_text(encoding="utf-8"))["differing_count"])


if __name__ == "__main__":
    unittest.main()
