import hashlib
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import pytest


TOOL_ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).with_name("fixtures")
SCHEMA_PATH = TOOL_ROOT / "schemas" / "animation-inspect-v1.schema.json"


def _run_cli(*arguments):
    return subprocess.run(
        [sys.executable, "-m", "dayz_animation_formats", *map(str, arguments)],
        cwd=TOOL_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        (
            "seanim-v1-full.seanim",
            {
                "format": "seanim",
                "schema_version": 1,
                "sha256": (
                    "75af1c6ab01ae715e6cea01e6897b804"
                    "586687ccf7a234c21be6bef871288b29"
                ),
                "summary": {
                    "anim_type": 3,
                    "bone_count": 2,
                    "frame_count": 11,
                    "framerate": 60.0,
                    "looped": True,
                    "modifier_count": 1,
                    "note_count": 1,
                    "position_key_count": 3,
                    "precision": "float64",
                    "rotation_key_count": 3,
                    "scale_key_count": 2,
                },
                "version": 1,
            },
        ),
        (
            "rtm-0101-mdat.rtm",
            {
                "format": "rtm",
                "schema_version": 1,
                "sha256": (
                    "37aa63f705d874c79b94721027d376a7"
                    "cab347fc94691ad419e1172c5597c3f8"
                ),
                "summary": {
                    "bone_count": 1,
                    "frame_count": 2,
                    "metadata_count": 1,
                    "motion": [1.0, 2.0, 3.0],
                    "transform_count": 2,
                },
                "version": "RTM_0101",
            },
        ),
    ],
)
def test_inspect_cli_returns_deterministic_schema_valid_json(
    filename, expected
):
    """Rompe si inspect filtra rutas/tiempo o cambia su contrato v1."""
    result = _run_cli("inspect", FIXTURES / filename)
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.endswith("\n")
    assert json.loads(result.stdout) == expected
    assert result.stdout == json.dumps(
        expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ) + "\n"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(expected)
    assert str(FIXTURES) not in result.stdout
    assert "timestamp" not in result.stdout


def test_output_file_bytes_equal_stdout_bytes(tmp_path):
    """Rompe si --output usa otra serialización o añade metadatos físicos."""
    fixture = FIXTURES / "seanim-v1-full.seanim"
    stdout_result = _run_cli("inspect", fixture)
    destination = tmp_path / "inspection.json"
    file_result = _run_cli("inspect", fixture, "--output", destination)
    assert file_result.returncode == 0
    assert file_result.stdout == ""
    assert file_result.stderr == ""
    assert destination.read_bytes() == stdout_result.stdout.encode("utf-8")


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        (b"not-a-format", "ANIM_FORMAT_UNSUPPORTED"),
        (b"SEAnim", "ANIM_TRUNCATED"),
        (b"BMTR" + b"\0" * 20, "ANIM_FORMAT_UNSUPPORTED"),
    ],
)
def test_invalid_input_exits_two_with_machine_error_on_stdout(
    tmp_path, payload, expected_code
):
    """Rompe si hay fallback, traceback o error esperado en stderr."""
    source = tmp_path / "invalid.bin"
    source.write_bytes(payload)
    result = _run_cli("inspect", source)
    assert result.returncode == 2
    assert result.stderr == ""
    value = json.loads(result.stdout)
    assert value["error"]["code"] == expected_code
    assert set(value) == {"error"}
    assert set(value["error"]) == {"code", "message", "offset"}
    assert str(source) not in result.stdout
    assert result.stdout.endswith("\n")


def test_frozen_fixture_hashes_are_the_bytes_inspected():
    """Rompe si el test compara JSON con un fixture distinto al versionado."""
    for name in ("seanim-v1-full.seanim", "rtm-0101-mdat.rtm"):
        path = FIXTURES / name
        result = _run_cli("inspect", path)
        assert json.loads(result.stdout)["sha256"] == hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
