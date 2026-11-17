import copy
import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from dayz_odol_strict.inspect import inspect_odol


TOOL_ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).with_name("fixtures")
SCHEMA = json.loads(
    (TOOL_ROOT / "schemas" / "dayz-odol-strict-v1.schema.json").read_text(
        encoding="utf-8"
    )
)
BACKEND_ROOT = os.environ.get("DAYZ_ODOL_BACKEND_ROOT")


@pytest.mark.skipif(
    not BACKEND_ROOT, reason="DAYZ_ODOL_BACKEND_ROOT is not configured"
)
@pytest.mark.parametrize(
    ("filename", "version", "lod_count", "sha256"),
    [
        (
            "odol-v53-ammo-box.p3d",
            53,
            1,
            "c2ba93cc05d3d47df5400c6f5f68aef928687eef06ce38747340927cd39e96ba",
        ),
        (
            "odol-v54-rugermarkiv-optic.p3d",
            54,
            1,
            "ccdb62e78661f2a0d98e5d5ca8844a8a7f0ae5242c2e1f403530d01d0ef037f9",
        ),
        (
            "odol-v55-lfquad-body.p3d",
            55,
            5,
            "9dd2b16a70001b5e6513bf26da0b24db6c2a92c09f6fa09ae9aab20f77ef19d3",
        ),
    ],
)
def test_authorized_real_fixture_is_complete_and_schema_valid(
    filename, version, lod_count, sha256
):
    summary = inspect_odol(FIXTURES / filename, BACKEND_ROOT)
    Draft202012Validator(SCHEMA).validate(summary)
    assert summary["input_sha256"] == sha256
    assert summary["payload_sha256"] == sha256
    assert summary["container_offset"] == 0
    assert summary["version"] == version
    assert summary["lod_count"] == lod_count
    assert len(summary["lods"]) == lod_count
    assert all(
        lod["actual_end"] == lod["declared_end"]
        and lod["declared_start"] < lod["declared_end"]
        and len(lod["raw_sha256"]) == 64
        for lod in summary["lods"]
    )
    assert str(BACKEND_ROOT) not in json.dumps(summary)


@pytest.mark.skipif(
    not BACKEND_ROOT, reason="DAYZ_ODOL_BACKEND_ROOT is not configured"
)
@pytest.mark.parametrize("prefix_size", [16, 4096])
def test_container_prefix_changes_only_input_identity_and_offset(
    tmp_path, prefix_size
):
    original = FIXTURES / "odol-v53-ammo-box.p3d"
    wrapped = tmp_path / "wrapped.p3d"
    wrapped.write_bytes(b"X" * prefix_size + original.read_bytes())
    direct = inspect_odol(original, BACKEND_ROOT)
    contained = inspect_odol(wrapped, BACKEND_ROOT)
    for value in (direct, contained):
        value.pop("input_sha256")
        value.pop("container_offset")
    assert contained == direct
