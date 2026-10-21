"""Tests for logwatch.py: lines written to a log while the watcher runs are triaged as they appear. No DayZ."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_logwatch_under_test", HERE / "logwatch.py")
logwatch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(logwatch)

KNOWN = logwatch.triage.load_known()

UNKNOWN_TYPE = 'SCRIPT    (E): @"MyVest/scripts/4_World/Vest.c,12": Unknown type \'CCConfig\''
NEW_ONLY = "[FAIL] zzlogwatchtest something nobody has seen before"
NOISE = "SCRIPT       : Creating Mission: mpmissions\\__cur_mp.chernarusplus"


def append(path: Path, *lines: str, newline: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if newline else ""))


def make_project(tmp_path: Path, instances=("chernarus",)) -> Path:
    for name in instances:
        (tmp_path / ".server" / name / "Profiles").mkdir(parents=True)
    (tmp_path / ".server" / "!ClientDiagLogs").mkdir(parents=True)
    return tmp_path


def collect():
    events = []
    return events, logwatch.Watcher(KNOWN, {"ModName": "MyVest"}, events.append)


# --- session folders -----------------------------------------------------------

def test_session_dirs_watch_every_instance_and_the_client(tmp_path):
    proj = make_project(tmp_path, ("chernarus", "livonia"))
    dirs = logwatch.session_dirs(proj, [])
    assert dirs == [
        proj / ".server" / "chernarus" / "Profiles",
        proj / ".server" / "livonia" / "Profiles",
        proj / ".server" / "!ClientDiagLogs",
    ]
    assert logwatch.session_dirs(proj, ["livonia"])[0] == proj / ".server" / "livonia" / "Profiles"


def test_session_dirs_refuse_a_missing_server(tmp_path):
    with pytest.raises(FileNotFoundError, match="dayz-add-server"):
        logwatch.session_dirs(tmp_path, [])
    proj = make_project(tmp_path)
    with pytest.raises(FileNotFoundError, match="livonia"):
        logwatch.session_dirs(proj, ["livonia"])


# --- tail ----------------------------------------------------------------------

def test_tail_skips_old_lines_and_reads_new_ones(tmp_path):
    log = tmp_path / "script.log"
    append(log, UNKNOWN_TYPE, "old line")
    tail = logwatch.Tail([tmp_path])
    assert tail.poll() == []
    append(log, "fresh line")
    assert tail.poll() == [(log, 3, "fresh line")]
    assert tail.poll() == []


def test_tail_reads_a_new_file_from_the_start_and_ignores_other_suffixes(tmp_path):
    tail = logwatch.Tail([tmp_path])
    append(tmp_path / "server_console.rpt", "a", "b")
    append(tmp_path / "notes.txt", "c")
    assert [t for _, _, t in tail.poll()] == ["a", "b"]


def test_tail_holds_back_a_half_written_line_until_final(tmp_path):
    log = tmp_path / "script.log"
    tail = logwatch.Tail([tmp_path])
    append(log, "done", "half", newline=False)
    assert [t for _, _, t in tail.poll()] == ["done"]
    assert [t for _, _, t in tail.poll(final=True)] == ["half"]


def test_tail_since_reads_recent_files_whole(tmp_path):
    old, recent = tmp_path / "old.log", tmp_path / "recent.log"
    append(old, "old")
    append(recent, "recent")
    os.utime(old, (time.time() - 3600, time.time() - 3600))
    tail = logwatch.Tail([tmp_path], since_s=600)
    assert [t for _, _, t in tail.poll()] == ["recent"]


def test_tail_rereads_a_rewritten_file(tmp_path):
    log = tmp_path / "script.log"
    append(log, "one", "two", "three")
    tail = logwatch.Tail([tmp_path])
    log.write_text("again\n", encoding="utf-8")
    assert tail.poll() == [(log, 1, "again")]


def test_tail_waits_for_a_folder_that_does_not_exist_yet(tmp_path):
    later = tmp_path / "Profiles"
    tail = logwatch.Tail([later])
    assert tail.poll() == []
    append(later / "script.log", "hello")
    assert [t for _, _, t in tail.poll()] == ["hello"]


# --- triage of each line -------------------------------------------------------

def test_known_line_carries_fix_and_owner(tmp_path):
    events, watcher = collect()
    watcher.feed([(tmp_path / "script.log", 7, UNKNOWN_TYPE)])
    assert len(events) == 1
    e = events[0]
    assert (e["status"], e["id"], e["owner_agent"], e["line"]) == ("known", "script-unknown-type", "dayz-script-specialist", 7)
    assert e["fix"]


def test_new_error_goes_to_the_debugger_and_noise_is_skipped(tmp_path):
    events, watcher = collect()
    watcher.feed([(tmp_path / "x.log", 1, NOISE), (tmp_path / "x.log", 2, NEW_ONLY)])
    assert [(e["status"], e["owner_agent"]) for e in events] == [("new", "dayz-mod-debugger")]


def test_repeats_are_counted_not_printed_again(tmp_path):
    events, watcher = collect()
    watcher.feed([(tmp_path / "a.log", 1, "10:00:01 " + UNKNOWN_TYPE), (tmp_path / "b.log", 9, "11:12:13 " + UNKNOWN_TYPE)])
    assert len(events) == 1
    s = watcher.summary(3, "duration")
    assert (s["errors"], s["known"], s["new"], s["repeats"]) == (1, 1, 0, 1)


def test_a_new_crash_log_is_flagged(tmp_path):
    events, watcher = collect()
    tail = logwatch.Tail([tmp_path])
    append(tmp_path / "crash_2026-10-21_10-00-00.log", "Exception code: C0000005 ACCESS_VIOLATION")
    watcher.feed_files(tail.new_files())
    assert events and events[0]["category"] == "crash" and events[0]["owner_agent"] == "dayz-mod-debugger"
    watcher.feed_files(tail.new_files())
    assert len(events) == 1


# --- watching a log while it is written ----------------------------------------

def test_watch_flags_errors_written_while_it_runs(tmp_path):
    """A writer thread appends lines while watch() polls; each error is reported once, in order."""
    proj = make_project(tmp_path)
    log = proj / ".server" / "chernarus" / "Profiles" / "script_2026-10-21_10-00-00.log"
    append(log, UNKNOWN_TYPE)  # written before the watch: must not be reported
    events = []
    reported = queue.Queue()
    watcher = logwatch.Watcher(KNOWN, {}, lambda e: (events.append(e), reported.put(e)))
    tail = logwatch.Tail(logwatch.session_dirs(proj, []))
    stop = threading.Event()

    def writer():
        append(log, NOISE)
        append(log, "10:00:05 " + UNKNOWN_TYPE)
        assert reported.get(timeout=10)["status"] == "known"  # seen while the watcher still runs
        append(proj / ".server" / "!ClientDiagLogs" / "script_2026-10-21_10-00-03.log", NEW_ONLY)
        assert reported.get(timeout=10)["status"] == "new"
        stop.set()

    thread = threading.Thread(target=writer)
    thread.start()
    summary = logwatch.watch(tail, watcher, interval=0.05, duration=20, session_alive=lambda: not stop.is_set())
    thread.join()
    assert [e["status"] for e in events] == ["known", "new"]
    assert events[0]["line"] == 3
    assert summary["stopped"] == "session closed"
    assert (summary["errors"], summary["known"], summary["new"]) == (2, 1, 1)


def test_watch_stops_after_duration_and_reads_the_last_line(tmp_path):
    log = tmp_path / "script.log"
    tail = logwatch.Tail([tmp_path])
    events, watcher = collect()
    clock = iter([0, 0, 1, 2, 3, 3])
    append(log, NEW_ONLY, newline=False)
    summary = logwatch.watch(tail, watcher, interval=0, duration=2, sleep=lambda s: None, clock=lambda: next(clock))
    assert summary["stopped"] == "duration"
    assert [e["text"] for e in events] == [NEW_ONLY]


def test_cli_streams_errors_while_a_log_is_written(tmp_path):
    """The real script, run as the .bat runs it: lines appear on stdout while the log grows."""
    log = tmp_path / "script.log"
    append(log, UNKNOWN_TYPE)
    proc = subprocess.Popen(
        [sys.executable, str(HERE / "logwatch.py"), "--dir", str(tmp_path), "--duration", "30",
         "--interval", "0.1", "--json"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
    )
    try:
        time.sleep(1.5)  # let it take its starting snapshot
        append(log, "12:00:00 " + UNKNOWN_TYPE)
        first = json.loads(proc.stdout.readline())
        assert (first["event"], first["status"], first["id"]) == ("error", "known", "script-unknown-type")
        append(log, NEW_ONLY)
        second = json.loads(proc.stdout.readline())
        assert (second["status"], second["owner_agent"], second["line"]) == ("new", "dayz-mod-debugger", 3)
        assert proc.poll() is None  # still watching
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_cli_text_output_and_exit_code(tmp_path, monkeypatch):
    monkeypatch.setattr(logwatch.triage, "cached_project_dir", lambda: None)
    out = io.StringIO()
    append(tmp_path / "script.log", "nothing wrong here")
    assert logwatch.main(["--dir", str(tmp_path), "--duration", "0", "--interval", "0"], out) == 0
    assert "Watching 1 folder(s)" in out.getvalue() and "0 error(s)" in out.getvalue()

    log = tmp_path / "later" / "script.log"
    append(log, "x")
    real_tail = logwatch.Tail

    def tail_then_write(dirs, since_s=0):
        tail = real_tail(dirs, since_s)
        append(log, UNKNOWN_TYPE)
        return tail

    monkeypatch.setattr(logwatch, "Tail", tail_then_write)
    out = io.StringIO()
    assert logwatch.main(["--dir", str(tmp_path / "later"), "--duration", "0", "--interval", "0", "--mod", "MyVest"], out) == 1
    text = out.getvalue()
    assert "known script-unknown-type -> dayz-script-specialist" in text
    assert "fix: " in text and "1 known, 0 new" in text


def test_cli_without_project_or_dir_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(logwatch.triage, "cached_project_dir", lambda: None)
    assert logwatch.main([]) == 2
    assert "dayz-init" in capsys.readouterr().err
