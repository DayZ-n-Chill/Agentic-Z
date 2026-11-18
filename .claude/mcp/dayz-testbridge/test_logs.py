"""Offsets, marks, rotated logs and the client's 255-character cut, on fixture log files."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import logs  # noqa: E402


def write(path: Path, text: str, mode: str = "w") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode, encoding="utf-8", newline="\n") as f:
        f.write(text)


def peers(tmp_path):
    return {"server": tmp_path / "server", "client": tmp_path / "client"}


def test_only_lines_after_the_offset_are_read_with_their_real_line_numbers(tmp_path):
    dirs = peers(tmp_path)
    script = dirs["server"] / "script_2026-11-18_10-00-00.log"
    write(script, "boot 1\nboot 2\n")
    offsets = logs.snapshot(dirs)
    write(script, "[AZ-BRIDGE] MARK start\nSCRIPT (E): boom\n", "a")
    lines = logs.lines_since(dirs, offsets)
    assert [(ln["line"], ln["text"]) for ln in lines] == [(3, "[AZ-BRIDGE] MARK start"), (4, "SCRIPT (E): boom")]
    assert lines[0]["peer"] == "server" and lines[0]["file"] == script.name


def test_a_file_new_since_the_offset_is_read_whole_and_other_files_are_skipped(tmp_path):
    dirs = peers(tmp_path)
    write(dirs["client"] / "script_old.log", "old\n")
    write(dirs["client"] / "notes.txt", "not a log\n")
    offsets = logs.snapshot(dirs)
    write(dirs["client"] / "DayZDiag_x64_2026.RPT", "rpt line\n")
    lines = logs.lines_since(dirs, offsets)
    assert [ln["text"] for ln in lines] == ["rpt line"]
    assert logs.lines_since(dirs, offsets, kinds=("script",)) == []


def test_a_rotated_log_shorter_than_its_offset_is_read_from_the_start(tmp_path):
    dirs = peers(tmp_path)
    script = dirs["server"] / "script_x.log"
    write(script, "a long first session line\n" * 10)
    offsets = logs.snapshot(dirs)
    write(script, "fresh\n")
    lines = logs.lines_since(dirs, offsets)
    assert [(ln["line"], ln["text"]) for ln in lines] == [(1, "fresh")]


def test_marks_are_found_even_when_the_client_cut_the_line(tmp_path):
    dirs = peers(tmp_path)
    label = "step7-raycast-down-at-the-car"
    prefix = "12:00:00.000 SCRIPT       : "
    cut = (prefix + "[AZ-BRIDGE] MARK " + label + " " + "x" * 300)[:logs.CLIENT_LINE_LIMIT]
    write(dirs["client"] / "script_c.log", cut + "\n")
    lines = logs.lines_since(dirs, {})
    assert len(logs.find_mark(lines, label)) == 1
    assert logs.find_mark(lines, "other") == []


def test_regex_peer_filter_bridge_errors_and_triage(tmp_path):
    dirs = peers(tmp_path)
    write(dirs["server"] / "script_s.log", "[AZ-BRIDGE] ERROR result 3: disk\nfine\n")
    write(dirs["client"] / "script_c.log", "NULL pointer to instance\n")
    lines = logs.lines_since(dirs, {}, peers=["server"])
    assert [ln["text"] for ln in logs.bridge_errors(lines)] == ["[AZ-BRIDGE] ERROR result 3: disk"]
    only = logs.lines_since(dirs, {}, pattern=r"NULL pointer")
    assert [ln["peer"] for ln in only] == ["client"]
    triaged = logs.triage(only)
    assert triaged[0]["category"] == "null_pointer"


def test_crash_logs_written_since_the_offset_are_listed(tmp_path):
    dirs = peers(tmp_path)
    write(dirs["server"] / "crash_old.log", "old\n")
    offsets = logs.snapshot(dirs)
    write(dirs["client"] / "crash_2026.log", "boom\n")
    assert [Path(p).name for p in logs.new_crash_logs(dirs, offsets)] == ["crash_2026.log"]
