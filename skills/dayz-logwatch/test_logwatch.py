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


def test_session_dirs_skip_the_gate_behavior_copies_unless_named(tmp_path):
    """The /dayz-gate copies used to be watched by default, so a gate run's errors showed up
    under an instance the user never added."""
    proj = make_project(tmp_path, ("chernarus", "chernarus-behavior"))
    assert logwatch.session_dirs(proj, []) == [
        proj / ".server" / "chernarus" / "Profiles",
        proj / ".server" / "!ClientDiagLogs",
    ]
    assert logwatch.session_dirs(proj, ["chernarus-behavior"])[0] == (
        proj / ".server" / "chernarus-behavior" / "Profiles")


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



def test_since_reports_a_recent_crash_log_but_not_an_old_one(tmp_path):
    old, recent = tmp_path / "crash_2026-10-21_09-00-00.log", tmp_path / "crash_2026-10-21_10-00-00.log"
    append(old, "old crash")
    append(recent, "recent crash")
    os.utime(old, (time.time() - 3600, time.time() - 3600))
    events, watcher = collect()
    tail = logwatch.Tail([tmp_path], since_s=600)
    watcher.feed_files(tail.new_files())
    assert [e["file"] for e in events] == [str(recent)]
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


def _stepping_clock(step):
    now = [-step]

    def clock():
        now[0] += step
        return now[0]
    return clock


def test_watch_waits_for_the_session_to_start_before_stopping_on_close(tmp_path):
    """Started before /dayz-launch-test: not running yet is not "closed"."""
    tail = logwatch.Tail([tmp_path])
    events, watcher = collect()
    states = iter([False, False, True, True, False])
    calls = []

    def alive():
        calls.append(1)
        return next(states)

    summary = logwatch.watch(tail, watcher, interval=0, session_alive=alive, sleep=lambda s: None,
                             clock=_stepping_clock(logwatch.CLOSED_CHECK_S))
    assert summary["stopped"] == "session closed"
    assert len(calls) == 5  # kept going through both early False answers


def test_watch_gives_up_when_the_session_never_starts(tmp_path):
    tail = logwatch.Tail([tmp_path])
    events, watcher = collect()
    summary = logwatch.watch(tail, watcher, interval=0, session_alive=lambda: False, sleep=lambda s: None,
                             clock=_stepping_clock(logwatch.CLOSED_CHECK_S))
    assert summary["stopped"] == "session never started"
    assert summary["seconds"] >= logwatch.START_GRACE_S


def test_cli_session_never_started_exits_2(tmp_path, monkeypatch):
    monkeypatch.setattr(logwatch.triage, "cached_project_dir", lambda: None)
    monkeypatch.setattr(logwatch, "client_running", lambda: False)
    monkeypatch.setattr(logwatch, "START_GRACE_S", 0)
    out = io.StringIO()
    assert logwatch.main(["--dir", str(tmp_path), "--until-closed", "--interval", "0.1"], out) == 2
    assert "Stopped (session never started)" in out.getvalue()


def test_cli_errors_win_over_session_never_started(tmp_path, monkeypatch):
    monkeypatch.setattr(logwatch.triage, "cached_project_dir", lambda: None)
    monkeypatch.setattr(logwatch, "client_running", lambda: False)
    monkeypatch.setattr(logwatch, "START_GRACE_S", 0)
    append(tmp_path / "script.log", UNKNOWN_TYPE)
    out = io.StringIO()
    args = ["--dir", str(tmp_path), "--until-closed", "--since", "5", "--interval", "0.1"]
    assert logwatch.main(args, out) == 1
    assert "Stopped (session never started)" in out.getvalue()


def test_cli_start_timeout_reaches_watch(tmp_path, monkeypatch):
    """START_GRACE_S was hard-coded: a build between starting the watch and the launch could outlast it."""
    monkeypatch.setattr(logwatch.triage, "cached_project_dir", lambda: None)
    seen = {}
    real_watch = logwatch.watch

    def spy(*a, **k):
        seen["start_grace"] = k.get("start_grace")
        return real_watch(*a, **{**k, "session_alive": lambda: False, "start_grace": 0})

    monkeypatch.setattr(logwatch, "watch", spy)
    args = ["--dir", str(tmp_path), "--until-closed", "--interval", "0.1"]
    assert logwatch.main(args + ["--start-timeout", "900"], io.StringIO()) == 2
    assert seen["start_grace"] == 900
    assert logwatch.main(args, io.StringIO()) == 2
    assert seen["start_grace"] is None  # watch() falls back to START_GRACE_S


@pytest.mark.parametrize("value", ["0", "-5", "nan", "inf"])
def test_start_timeout_zero_negative_or_not_finite_exits_2(value, capsys):
    with pytest.raises(SystemExit) as exc:
        logwatch.main(["--dir", ".", "--until-closed", "--start-timeout", value])
    assert exc.value.code == 2
    assert "--start-timeout must be more than 0 seconds" in capsys.readouterr().err


def test_start_timeout_without_until_closed_exits_2(capsys):
    with pytest.raises(SystemExit) as exc:
        logwatch.main(["--dir", ".", "--duration", "1", "--start-timeout", "60"])
    assert exc.value.code == 2
    assert "--start-timeout needs --until-closed" in capsys.readouterr().err


def test_watch_honours_a_longer_start_grace(tmp_path):
    tail = logwatch.Tail([tmp_path])
    events, watcher = collect()
    summary = logwatch.watch(tail, watcher, interval=0, session_alive=lambda: False, start_grace=900,
                             sleep=lambda s: None, clock=_stepping_clock(logwatch.CLOSED_CHECK_S))
    assert summary["stopped"] == "session never started"
    assert summary["seconds"] >= 900


def test_watch_stops_at_once_on_a_crash_before_the_client_was_seen(tmp_path):
    """A client that crashed within one process check was never seen running, so the watch waited 300 s."""
    tail = logwatch.Tail([tmp_path])
    events, watcher = collect()
    polls = []

    def sleep(_):
        polls.append(1)
        if len(polls) == 2:
            append(tmp_path / "crash_2026-10-21_10-00-00.log", "Exception code: C0000005 ACCESS_VIOLATION")

    summary = logwatch.watch(tail, watcher, interval=0, session_alive=lambda: False, sleep=sleep,
                             clock=_stepping_clock(0.1))
    assert summary["stopped"] == "crashed before it was seen running"
    assert len(polls) == 2 and summary["errors"] == 1
    assert events[0]["category"] == "crash"


def test_watch_ignores_an_old_crash_read_with_since_before_the_start(tmp_path):
    """A crash log from --since is read on the first pass; it must not end the wait for the new session."""
    append(tmp_path / "crash_2026-10-21_09-00-00.log", "old crash")
    tail = logwatch.Tail([tmp_path], since_s=300)
    events, watcher = collect()
    states = iter([False, True, False])
    summary = logwatch.watch(tail, watcher, interval=0, session_alive=lambda: next(states), sleep=lambda s: None,
                             clock=_stepping_clock(logwatch.CLOSED_CHECK_S))
    assert summary["stopped"] == "session closed"
    assert summary["errors"] == 1  # still reported


def test_watch_crash_does_not_stop_a_plain_watch(tmp_path):
    tail = logwatch.Tail([tmp_path])
    events, watcher = collect()
    polls = []

    def sleep(_):
        polls.append(1)
        if len(polls) == 1:
            append(tmp_path / "crash_2026-10-21_10-00-00.log", "x")

    summary = logwatch.watch(tail, watcher, interval=0, duration=1, sleep=sleep, clock=_stepping_clock(0.1))
    assert summary["stopped"] == "duration" and summary["errors"] == 1


def test_cli_crash_before_start_exits_1(tmp_path, monkeypatch):
    monkeypatch.setattr(logwatch.triage, "cached_project_dir", lambda: None)
    monkeypatch.setattr(logwatch, "client_running", lambda: False)
    real_tail = logwatch.Tail

    class CrashingTail(real_tail):
        calls = 0

        def new_files(self):
            CrashingTail.calls += 1
            if CrashingTail.calls == 2:
                append(tmp_path / "crash_2026-10-21_10-00-00.log", "x")
            return super().new_files()

    monkeypatch.setattr(logwatch, "Tail", CrashingTail)
    out = io.StringIO()
    assert logwatch.main(["--dir", str(tmp_path), "--until-closed", "--interval", "0.1"], out) == 1
    assert "Stopped (crashed before it was seen running)" in out.getvalue()


@pytest.mark.parametrize("cmdline, client", [
    ('"C:/DayZ/DayZDiag_x64.exe" -profiles=x -mod=P:/Mods/@A -connect=127.0.0.1 -port=2302', True),
    ('"C:/DayZ/DayZDiag_x64.exe" -server -config=c -mod=P:/Mods/@A -port=2302', False),
    ('"C:/DayZ/DayZDiag_x64.exe" -SERVER -config=c', False),
    ("", True),  # command line hidden: assume the client, never stop early
])
def test_is_client_looks_for_the_server_switch(cmdline, client):
    assert logwatch.is_client(cmdline) is client


def test_client_running_ignores_the_server_process(monkeypatch):
    server = '"C:/DayZ/DayZDiag_x64.exe" -server -config=c -serverMod=P:/Mods/@S'
    client = '"C:/DayZ/DayZDiag_x64.exe" -connect=127.0.0.1'
    monkeypatch.setattr(logwatch, "diag_command_lines", lambda: [server])
    assert logwatch.client_running() is False  # server left running after the client window closed
    monkeypatch.setattr(logwatch, "diag_command_lines", lambda: [server, client])
    assert logwatch.client_running() is True
    monkeypatch.setattr(logwatch, "diag_command_lines", lambda: [server, ""])
    assert logwatch.client_running() is True  # a hidden command line counts as the client
    monkeypatch.setattr(logwatch, "diag_command_lines", lambda: [])
    assert logwatch.client_running() is False


def test_client_running_reports_unknown_when_the_query_fails(monkeypatch):
    monkeypatch.setattr(logwatch, "diag_command_lines", lambda: None)
    assert logwatch.client_running() is None


@pytest.mark.skipif(sys.platform != "win32", reason="the process query is Windows only")
def test_diag_command_lines_reads_real_command_lines_without_starting_a_process(monkeypatch):
    """It used to start PowerShell (about 1.5 s cold start) on every 5-second check."""
    marker = "zzlogwatch-cmdline-marker"
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", marker])
    try:
        def no_process(*a, **k):
            raise AssertionError("diag_command_lines must not start a process")

        monkeypatch.setattr(subprocess, "run", no_process)
        monkeypatch.setattr(subprocess, "Popen", no_process)
        lines = logwatch.diag_command_lines(Path(sys.executable).name)
        assert lines is not None and any(marker in line for line in lines)
        assert logwatch.diag_command_lines("zz-no-such-process.exe") == []
    finally:
        proc.kill()
        proc.wait()


def test_watch_stops_when_the_process_query_keeps_failing(tmp_path):
    """A failing query used to count as "client running", so the watch never stopped."""
    tail = logwatch.Tail([tmp_path])
    events, watcher = collect()
    calls = []

    def failing():
        calls.append(1)
        return None

    summary = logwatch.watch(tail, watcher, interval=0, session_alive=failing, sleep=lambda s: None,
                             clock=_stepping_clock(logwatch.CLOSED_CHECK_S))
    assert summary["stopped"] == "cannot read process list"
    assert len(calls) == logwatch.QUERY_FAILURES_MAX


def test_watch_forgives_a_failed_query_between_good_ones(tmp_path):
    tail = logwatch.Tail([tmp_path])
    events, watcher = collect()
    states = iter([True, None, None, True, None, None, False])
    summary = logwatch.watch(tail, watcher, interval=0, session_alive=lambda: next(states), sleep=lambda s: None,
                             clock=_stepping_clock(logwatch.CLOSED_CHECK_S))
    assert summary["stopped"] == "session closed"


def test_cli_failing_process_query_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(logwatch.triage, "cached_project_dir", lambda: None)

    monkeypatch.setattr(logwatch, "diag_command_lines", lambda: None)
    monkeypatch.setattr(logwatch, "CLOSED_CHECK_S", 0)
    out = io.StringIO()
    assert logwatch.main(["--dir", str(tmp_path), "--until-closed", "--interval", "0.1"], out) == 2
    assert "Stopped (cannot read process list)" in out.getvalue()
    assert "Cannot read the process list" in capsys.readouterr().err


GOOD_SHIPPED = {"id": "ok", "pattern": "Unknown type", "meaning": "m", "fix": "f", "owner_agent": "a"}
GOOD_LEARNED = {"id": "learned-ok", "fingerprint": "fp", "meaning": "m", "fix": "f", "owner_agent": "a"}


@pytest.mark.parametrize("entries,learned", [
    ([{"id": "bad-regex", "pattern": "Unknown type ('"}], None),
    ([{"id": "no-pattern", "fix": "x"}], None),
    ([{k: v for k, v in GOOD_SHIPPED.items() if k != "owner_agent"}], None),
    ([GOOD_SHIPPED], [{k: v for k, v in GOOD_LEARNED.items() if k != "meaning"}]),
    ([GOOD_SHIPPED], [{k: v for k, v in GOOD_LEARNED.items() if k != "fingerprint"}]),
    ([GOOD_SHIPPED], ["not an entry"]),
], ids=["bad regex", "missing pattern", "shipped missing owner_agent", "learned missing meaning",
        "learned missing fingerprint", "learned entry not a dict"])
def test_cli_broken_known_errors_file_exits_2(tmp_path, monkeypatch, capsys, entries, learned):
    shipped = tmp_path / "known-errors.json"
    shipped.write_text(json.dumps(entries), encoding="utf-8")
    project = None
    if learned is not None:
        project = tmp_path / "project"
        learned_file = logwatch.triage.learned_path(project)
        learned_file.parent.mkdir(parents=True)
        learned_file.write_text(json.dumps(learned), encoding="utf-8")
    monkeypatch.setattr(logwatch.triage, "cached_project_dir", lambda: project)
    monkeypatch.setattr(logwatch.triage, "KNOWN_ERRORS", shipped)
    assert logwatch.main(["--dir", str(tmp_path), "--duration", "0.1", "--interval", "0.1"], io.StringIO()) == 2
    assert "Could not load known errors" in capsys.readouterr().err


def test_cli_valid_learned_entry_loads(tmp_path, monkeypatch):
    """The check is not too strict: a complete learned entry next to a complete shipped one runs."""
    shipped = tmp_path / "known-errors.json"
    shipped.write_text(json.dumps([GOOD_SHIPPED]), encoding="utf-8")
    project = tmp_path / "project"
    learned_file = logwatch.triage.learned_path(project)
    learned_file.parent.mkdir(parents=True)
    learned_file.write_text(json.dumps([GOOD_LEARNED]), encoding="utf-8")
    monkeypatch.setattr(logwatch.triage, "cached_project_dir", lambda: project)
    monkeypatch.setattr(logwatch.triage, "KNOWN_ERRORS", shipped)
    assert logwatch.main(["--dir", str(tmp_path), "--duration", "0.1", "--interval", "0.1"], io.StringIO()) == 0


def test_duration_and_until_closed_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit) as exc:
        logwatch.main(["--dir", ".", "--duration", "5", "--until-closed"])
    assert exc.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


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
    assert logwatch.main(["--dir", str(tmp_path), "--duration", "0.1", "--interval", "0.1"], out) == 0
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
    assert logwatch.main(["--dir", str(tmp_path / "later"), "--duration", "0.1", "--interval", "0.1", "--mod", "MyVest"], out) == 1
    text = out.getvalue()
    assert "known script-unknown-type -> dayz-script-specialist" in text
    assert "fix: " in text and "1 known, 0 new" in text


def test_cli_without_project_or_dir_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(logwatch.triage, "cached_project_dir", lambda: None)
    assert logwatch.main([]) == 2
    assert "dayz-init" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["0", "-1", "0.01", "nan", "inf"])
def test_interval_below_minimum_exits_2(value, capsys):
    with pytest.raises(SystemExit) as exc:
        logwatch.main(["--dir", ".", "--duration", "1", "--interval", value])
    assert exc.value.code == 2
    assert "--interval must be at least" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["0", "-5", "nan", "inf"])
def test_duration_zero_negative_or_not_finite_exits_2(value, capsys):
    with pytest.raises(SystemExit) as exc:
        logwatch.main(["--dir", ".", "--duration", value])
    assert exc.value.code == 2
    assert "--duration must be more than 0 seconds" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["-1", "-0.5", "nan", "inf"])
def test_since_negative_or_not_finite_exits_2(value, capsys):
    with pytest.raises(SystemExit) as exc:
        logwatch.main(["--dir", ".", "--duration", "1", "--since", value])
    assert exc.value.code == 2
    assert "--since must be 0 or more minutes" in capsys.readouterr().err
