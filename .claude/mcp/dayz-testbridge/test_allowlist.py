"""The allowlist refuses unknown commands, bad types and every bound before anything is written."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import allowlist  # noqa: E402

CAR = [4200.0, 0.0, 10650.0]


@pytest.mark.parametrize("cmd, args, message", [
    ("exec", {}, "code is required"),
    ("run_script", {"code": "x"}, "unknown command"),
    ("spawn", {"cls": "Hatchback_02"}, "pos is required"),
    ("spawn", {"cls": "Hatch back", "pos": CAR}, "not allowed"),
    ("spawn", {"cls": "Hatchback_02", "pos": CAR, "extra": 1}, "unknown arguments"),
    ("spawn", {"cls": "Hatchback_02", "pos": [4200, 10650, 0]}, "swapped"),
    ("spawn", {"cls": "Hatchback_02", "pos": [-1, 0, 0]}, "inside the world"),
    ("spawn", {"cls": "Hatchback_02", "pos": [4200, 0]}, r"\[x, y, z\]"),
    ("spawn", {"cls": "Hatchback_02", "pos": CAR, "flags": 1060}, "ECE_NOPERSISTENCY_WORLD"),
    ("spawn", {"cls": "Hatchback_02", "pos": CAR, "flags": 1.5}, "whole number"),
    ("find_objects", {"pos": CAR, "radius": 201}, "outside"),
    ("drive", {"seconds": 61}, "outside"),
    ("drive", {"throttle": "1"}, "a number"),
    ("drive", {"steer": float("nan")}, "finite"),
    ("set_weather", {"rain": 1.5}, "outside"),
    ("set_time", {"hour": 24}, "outside"),
    ("teleport", {"pos": CAR, "ground": 1}, "true or false"),
    ("raycast", {"from": CAR, "to": CAR, "mode": "xray"}, "one of"),
    ("delete", {"net_id": "abc"}, "not allowed"),
    ("mark", {"label": "a b"}, "not allowed"),
    ("mark", {"label": "x" * 65}, "not allowed"),
    ("spawn_in_inventory", {"cls": "Apple", "where": "pocket"}, "one of"),
    ("surface", {"x": 100}, "z is required"),
])
def test_refused(cmd, args, message):
    with pytest.raises(allowlist.AllowlistError, match=message):
        allowlist.wire_args(cmd, args)


def test_defaults_are_filled_and_names_mapped_to_the_wire():
    wire = allowlist.wire_args("raycast", {"from": [10, 20, 30], "to": [10, 0, 30]})
    assert wire["from_pos"] == [10.0, 20.0, 30.0] and wire["to_pos"] == [10.0, 0.0, 30.0]
    assert wire["mode"] == "view" and "from" not in wire and set(wire) == set(allowlist.WIRE_DEFAULTS)
    assert allowlist.wire_args("surface", {"x": 1, "z": 2})["has_y"] is False
    assert allowlist.wire_args("surface", {"x": 1, "z": 2, "y": 5})["has_y"] is True
    assert allowlist.wire_args("get_in", {"net_id": "12,0"})["seat"] == 0


def test_every_command_names_its_peer_outputs_and_only_known_wire_fields():
    for name, spec in allowlist.COMMANDS.items():
        assert spec.peer in (allowlist.SERVER, allowlist.CLIENT, allowlist.BOTH), name
        assert spec.outputs or name == "shutdown", name
        for arg_name, arg in spec.args.items():
            assert (arg.wire or arg_name) in allowlist.WIRE_DEFAULTS, f"{name}.{arg_name} has no AZB_Args field"


def test_drive_timeout_follows_its_seconds():
    checked = allowlist.validate("drive", {"seconds": 30})
    assert allowlist.timeout("drive", checked) == 50.0


def test_only_exec_runs_code_and_it_needs_the_session_opt_in():
    # Owner decision 3, revised: running code is allowed, off by default, per-session opt-in.
    assert {n for n, c in allowlist.COMMANDS.items() if c.opt_in} == {"exec"}
    banned = ("eval", "script", "file", "call", "method", "invoke", "console")
    for name in allowlist.COMMANDS:
        assert not any(b in name for b in banned), name
