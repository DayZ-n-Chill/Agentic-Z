import hashlib
import json
from pathlib import Path
import struct


FIXTURES = Path(__file__).with_name("fixtures")


def test_authorized_fixture_manifest_matches_every_tracked_byte():
    manifest = json.loads(
        (FIXTURES / "fixtures.json").read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == "dayz-odol-fixtures-v1"
    assert len(manifest["fixtures"]) == 3
    assert {
        item["version"]: item["lod_count"]
        for item in manifest["fixtures"]
    } == {53: 1, 54: 1, 55: 5}
    for item in manifest["fixtures"]:
        assert set(item) == {
            "filename",
            "lod_count",
            "rights",
            "sha256",
            "size",
            "version",
        }
        assert "authorized" in item["rights"].lower()
        path = FIXTURES / item["filename"]
        payload = path.read_bytes()
        assert len(payload) == item["size"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
        assert payload[:4] == b"ODOL"
        version, lod_count = struct.unpack("<ii", payload[4:12])
        assert version == item["version"]
        assert lod_count == item["lod_count"]


def test_fixture_manifest_contains_no_physical_source_path():
    text = (FIXTURES / "fixtures.json").read_text(encoding="utf-8")
    assert "C:\\" not in text
    assert "OneDrive" not in text
    assert "ObsidianVault" not in text
