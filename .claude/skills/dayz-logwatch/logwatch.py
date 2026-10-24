"""/dayz-logwatch: tail a test session's logs and triage each new error line as it appears.

Watches the server and client log folders of the local test session (the
.server/<instance>/Profiles/ folders and the shared .server/!ClientDiagLogs/),
reads the .rpt and .log lines written after it started, and runs each error line
through /dayz-gate's triage (triage.py, known-errors.json and the project's
learned file). A known error prints its fix and owner; a new one is flagged for
dayz-mod-debugger. The same error again (same fingerprint) is only counted.

Usage:
  python logwatch.py [--server <instance> ...] [--since MINUTES]
                     [--duration S | --until-closed [--start-timeout S]] [--interval S]
                     [--mod <ModName>] [--json]
  python logwatch.py --dir DIR [--dir DIR ...] [--since MINUTES]
                     [--duration S | --until-closed [--start-timeout S]] [--interval S]
                     [--mod <ModName>] [--json]

Exit codes: 0 no error lines seen, 1 at least one error line, 2 cannot run
(or --until-closed saw no session start, or could not read the process list,
and saw no error line).
See SKILL.md for details.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Callable, Optional, TextIO

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import skill_helpers as h  # noqa: E402

triage = h.load_module("dayz_logwatch_triage", HERE.parent / "dayz-gate" / "triage.py")

LOG_SUFFIXES = (".rpt", ".log")
CLIENT_DIR = "!ClientDiagLogs"
DIAG_EXE = "DayZDiag_x64.exe"
DEBUGGER = "dayz-mod-debugger"
POLL_S = 1.0
MIN_INTERVAL_S = 0.1
CLOSED_CHECK_S = 5.0  # how often --until-closed asks whether the DayZ Diag client still runs
START_GRACE_S = 300.0  # default --start-timeout: how long --until-closed waits for the client to start
QUERY_FAILURES_MAX = 3  # failed process-list queries in a row before --until-closed gives up
SERVER_FLAG = re.compile(r"(?i)(?:^|\s)-server(?:\s|$)")
BEHAVIOR_SUFFIX = "-behavior"  # the /dayz-gate behavior copies, .server/<instance>-behavior/


def is_log(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in LOG_SUFFIXES


def session_dirs(project: Path, instances: list[str]) -> list[Path]:
    """Server Profiles/ of each instance and the client log folder.

    With no instance named it watches every instance made by /dayz-add-server,
    leaving out the shared `!` folders and the `<instance>-behavior` copies that
    /dayz-gate behavior rebuilds (the /dayz-init hub hides them too). Name such a
    copy with --server to watch it.
    """
    server_root = project / ".server"
    if not server_root.is_dir():
        raise FileNotFoundError(f"no .server/ folder in {project}; run /dayz-add-server first")
    if instances:
        missing = [i for i in instances if not (server_root / i).is_dir()]
        if missing:
            raise FileNotFoundError(f"no test server instance {', '.join(missing)} under {server_root}")
    else:
        instances = sorted(p.name for p in server_root.iterdir() if p.is_dir() and not p.name.startswith("!")
                           and not p.name.endswith(BEHAVIOR_SUFFIX))
    return [server_root / i / "Profiles" for i in instances] + [server_root / CLIENT_DIR]


class Tail:
    """Reads the complete lines appended to the log files in some folders.

    Files present at the start are read from their end, unless they changed in
    the last `since_s` seconds; those, and files that appear later, are read
    from the start and returned once by new_files().
    A file that shrinks (rewritten) is read again from the start.
    """

    def __init__(self, dirs: list[Path], since_s: float = 0, now: Optional[float] = None):
        self.dirs = dirs
        self.offsets: dict[Path, int] = {}
        self.line_numbers: dict[Path, int] = {}
        cutoff = (time.time() if now is None else now) - since_s
        for path in self._files():
            stat = path.stat()
            if not since_s or stat.st_mtime < cutoff:
                self.offsets[path] = stat.st_size
        # A file read from its start (changed within since_s) counts as new, so
        # a recent crash*.log is still reported as a crash.
        self.known_files = set(self.offsets)

    def _files(self) -> list[Path]:
        return [p for d in self.dirs if d.is_dir() for p in sorted(d.iterdir()) if is_log(p)]

    def new_files(self) -> list[Path]:
        """Log files that appeared since the last call (since the start, the first time)."""
        files = [p for p in self._files() if p not in self.known_files]
        self.known_files.update(files)
        return files

    def poll(self, final: bool = False) -> list[tuple[Path, int, str]]:
        new = []
        for path in self._files():
            offset = self.offsets.get(path, 0)
            try:
                size = path.stat().st_size
                if size < offset:
                    offset, self.line_numbers[path] = 0, 0
                with path.open("rb") as f:
                    if path not in self.line_numbers:
                        self.line_numbers[path] = f.read(offset).count(b"\n")
                    f.seek(offset)
                    chunk = f.read()
            except OSError:  # deleted or locked between listing and reading; try again next poll
                continue
            if not final:  # hold back a partly written last line
                chunk = chunk[: chunk.rfind(b"\n") + 1]
            if not chunk:
                continue
            self.offsets[path] = offset + len(chunk)
            for text in chunk.decode("utf-8", errors="replace").splitlines():
                self.line_numbers[path] += 1
                new.append((path, self.line_numbers[path], text))
        return new


ENTRY_KEYS = ("id", "meaning", "fix", "owner_agent")  # what triage.match_line reads from a matched entry


def check_known(known: list[dict]) -> list[dict]:
    """Raise ValueError for an entry a match would crash on, so a broken file stops the watch at start.

    triage.load_known only checks that shipped entries have a pattern. A learned
    entry (no compiled regex) also needs its fingerprint, and every entry needs
    the keys match_line copies into the result.
    """
    for number, entry in enumerate(known, 1):
        learned = entry.get("_re") is None
        needed = ENTRY_KEYS + (("fingerprint",) if learned else ())
        missing = [key for key in needed if key not in entry]
        if missing:
            kind = "learned" if learned else "shipped"
            name = entry.get("id", f"entry {number}")
            raise ValueError(f"{kind} entry {name!r} is missing {', '.join(missing)}")
    return known


def triage_line(path: Path, number: int, text: str, known: list[dict], context: dict) -> Optional[dict]:
    """The triage result for an error line, or None for a line that reports no error."""
    category = triage.classify(text)
    result = triage.match_line(text, known, context)
    if category is None and result["status"] == "new":
        return None
    if result["status"] == "new":
        result["owner_agent"] = DEBUGGER
    return {"file": str(path), "line": number, "text": text.strip(), "category": category, **result}


class Watcher:
    """Turns new log lines into events: one per first sight of an error, repeats only counted."""

    def __init__(self, known: list[dict], context: dict, emit: Callable[[dict], None]):
        self.known = known
        self.context = context
        self.emit = emit
        self.seen: dict[str, dict] = {}
        self.repeats = 0

    def feed(self, lines: list[tuple[Path, int, str]]) -> None:
        for path, number, text in lines:
            result = triage_line(path, number, text, self.known, self.context)
            if result is None:
                continue
            fp = result["fingerprint"]
            if fp in self.seen:
                self.seen[fp]["count"] += 1
                self.repeats += 1
                continue
            result["count"] = 1
            self.seen[fp] = result
            self.emit({"event": "error", **result})

    def feed_files(self, paths: list[Path]) -> int:
        """A new crash log means the game crashed, whatever its lines say. Returns how many there were."""
        crashes = [path for path in paths if path.name.lower().startswith("crash")]
        for path in crashes:
            self.feed_crash(path)
        return len(crashes)

    def feed_crash(self, path: Path) -> None:
        result = {
            "file": str(path), "line": 0, "text": f"crash log written: {path.name}", "category": "crash",
            "status": "new", "owner_agent": DEBUGGER, "fingerprint": f"crash log written: {path.name.lower()}",
        }
        if result["fingerprint"] not in self.seen:
            result["count"] = 1
            self.seen[result["fingerprint"]] = result
            self.emit({"event": "error", **result})

    def summary(self, seconds: float, reason: str) -> dict:
        errors = list(self.seen.values())
        return {
            "event": "summary",
            "stopped": reason,
            "seconds": round(seconds),
            "errors": len(errors),
            "known": sum(1 for e in errors if e["status"] == "known"),
            "new": sum(1 for e in errors if e["status"] == "new"),
            "repeats": self.repeats,
        }


def is_client(command_line: str) -> bool:
    """True unless the DayZDiag_x64.exe command line carries the -server switch.

    /dayz-launch-test runs the server and the client from the same binary, and the
    server keeps running after the player closes the client window.
    """
    return not SERVER_FLAG.search(command_line)


def diag_command_lines(exe: str = DIAG_EXE) -> Optional[list[str]]:
    """Command lines of the running processes named exe, or None if the process list cannot be read.

    One in-process Win32 query (a Toolhelp process snapshot, then
    NtQueryInformationProcess class 60, ProcessCommandLineInformation, Windows
    8.1 and later) instead of a PowerShell Get-CimInstance call, which costs
    about 1.5 s of cold start on every check. tasklist cannot show command
    lines, and wmic is gone from current Windows 11. A process whose command
    line Windows will not show (access denied, it exited meanwhile) is listed
    as "". None off Windows or when the snapshot fails.
    """
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        ntdll = ctypes.WinDLL("ntdll")
    except (ImportError, OSError, AttributeError):  # not Windows
        return None

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    class UNICODE_STRING(ctypes.Structure):
        _fields_ = [("Length", wintypes.USHORT), ("MaximumLength", wintypes.USHORT), ("Buffer", ctypes.c_void_p)]

    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ("Process32FirstW", "Process32NextW"):
        getattr(kernel32, name).argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
        getattr(kernel32, name).restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    ntdll.NtQueryInformationProcess.argtypes = [
        wintypes.HANDLE, wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG, ctypes.POINTER(wintypes.ULONG)]
    ntdll.NtQueryInformationProcess.restype = wintypes.LONG

    TH32CS_SNAPPROCESS = 0x2
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_COMMAND_LINE_INFORMATION = 60
    invalid = ctypes.c_void_p(-1).value

    def command_line(pid: int) -> str:
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return ""
        try:
            size = wintypes.ULONG(0)
            ntdll.NtQueryInformationProcess(handle, PROCESS_COMMAND_LINE_INFORMATION, None, 0, ctypes.byref(size))
            if size.value < ctypes.sizeof(UNICODE_STRING):
                return ""
            buf = ctypes.create_string_buffer(size.value)
            if ntdll.NtQueryInformationProcess(handle, PROCESS_COMMAND_LINE_INFORMATION, buf, size,
                                               ctypes.byref(size)) != 0:
                return ""
            text = UNICODE_STRING.from_buffer(buf)
            return ctypes.wstring_at(text.Buffer, text.Length // 2) if text.Buffer else ""
        finally:
            kernel32.CloseHandle(handle)

    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == invalid:
        return None
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            return None
        lines = []
        while True:
            if entry.szExeFile.lower() == exe.lower():
                lines.append(command_line(entry.th32ProcessID))
            if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                return lines
    finally:
        kernel32.CloseHandle(snap)


def client_running() -> Optional[bool]:
    """True while a DayZDiag_x64.exe without -server (the game client) is running.

    A process whose command line Windows will not show counts as a client, so
    the watch never stops early on a process it cannot read. Returns None when
    the process list cannot be read: the answer is unknown, and watch() gives
    up after QUERY_FAILURES_MAX in a row.
    """
    lines = diag_command_lines()
    if lines is None:
        return None
    return any(is_client(line) for line in lines)


def watch(
    tail: Tail,
    watcher: Watcher,
    *,
    interval: float = POLL_S,
    duration: Optional[float] = None,
    session_alive: Optional[Callable[[], Optional[bool]]] = None,
    start_grace: Optional[float] = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict:
    """Poll until the duration ends, the session closes (session_alive False) or Ctrl+C.

    A session counts as closed only after it has been seen running, so a watch
    started before /dayz-launch-test waits for the game. If it never starts
    within start_grace seconds (default START_GRACE_S), the watch stops with
    reason "session never started". A crash log that appears after the first
    read while the game has not been seen running yet ends the wait at once
    with reason "crashed before it was seen running": a client that crashes
    between two process checks is never seen running. Crash logs read on the
    first pass (the --since files) do not count. session_alive returning None means the
    check failed; after QUERY_FAILURES_MAX failures in a row the watch stops with
    reason "cannot read process list" instead of guessing.

    One last read after stopping catches the lines written at the end, including a
    last line without a newline.
    """
    started = clock()
    last_check = None
    seen_alive = False
    failures = 0
    grace = START_GRACE_S if start_grace is None else start_grace
    reason = "interrupted"
    first_pass = True
    try:
        while True:
            crashes = watcher.feed_files(tail.new_files())
            watcher.feed(tail.poll())
            if session_alive is not None and crashes and not seen_alive and not first_pass:
                reason = "crashed before it was seen running"
                break
            first_pass = False
            now = clock()
            if duration is not None and now - started >= duration:
                reason = "duration"
                break
            if session_alive is not None and (last_check is None or now - last_check >= CLOSED_CHECK_S):
                last_check = now
                alive = session_alive()
                failures = failures + 1 if alive is None else 0
                if alive is None:
                    if failures >= QUERY_FAILURES_MAX:
                        reason = "cannot read process list"
                        break
                elif alive:
                    seen_alive = True
                elif seen_alive:
                    reason = "session closed"
                    break
                elif now - started >= grace:
                    reason = "session never started"
                    break
            sleep(interval)
    except KeyboardInterrupt:
        pass
    watcher.feed_files(tail.new_files())
    watcher.feed(tail.poll(final=True))
    return watcher.summary(clock() - started, reason)


def _rel(path: str, base: Optional[Path]) -> str:
    if base is not None:
        try:
            return Path(path).relative_to(base).as_posix()
        except ValueError:
            pass
    return path


def text_emitter(out: TextIO, base: Optional[Path]) -> Callable[[dict], None]:
    def emit(event: dict) -> None:
        where = _rel(event["file"], base) + (f":{event['line']}" if event["line"] else "")
        if event["status"] == "known":
            print(f"known {event['id']} -> {event['owner_agent']}  {where}", file=out)
            print(f"      {event['text']}", file=out)
            print(f"      fix: {event['fix']}", file=out)
        else:
            print(f"new   -> {DEBUGGER}  {where}", file=out)
            print(f"      {event['text']}", file=out)
        out.flush()
    return emit


def json_emitter(out: TextIO) -> Callable[[dict], None]:
    def emit(event: dict) -> None:
        print(json.dumps(event), file=out)
        out.flush()
    return emit


def print_summary(summary: dict, out: TextIO, as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary), file=out)
        return
    print(
        f"Stopped ({summary['stopped']}) after {summary['seconds']} s: {summary['errors']} error(s), "
        f"{summary['known']} known, {summary['new']} new, {summary['repeats']} repeat(s) not shown.",
        file=out,
    )


def main(argv: Optional[list[str]] = None, out: TextIO = sys.stdout) -> int:
    parser = argparse.ArgumentParser(description="Tail a test session's logs and triage each new error line.")
    parser.add_argument("--server", action="append", default=[], metavar="INSTANCE",
                        help="Test server instance to watch (repeatable; default: every instance except the -behavior copies).")
    parser.add_argument("--dir", action="append", default=[], type=Path, metavar="DIR",
                        help="Watch this folder instead of the project's session folders (repeatable).")
    parser.add_argument("--since", type=float, default=0, metavar="MINUTES",
                        help="Read files changed in the last MINUTES from their start (default 0: only new lines).")
    stop_on = parser.add_mutually_exclusive_group()
    stop_on.add_argument("--duration", type=float, metavar="S", help="Stop after S seconds.")
    stop_on.add_argument("--until-closed", action="store_true",
                         help=f"Stop once the {DIAG_EXE} client (no -server) seen running has closed.")
    parser.add_argument("--start-timeout", type=float, metavar="S",
                        help=f"With --until-closed, seconds to wait for the client to start "
                             f"(default {START_GRACE_S:g}).")
    parser.add_argument("--interval", type=float, default=POLL_S, metavar="S",
                        help=f"Seconds between reads (default 1, at least {MIN_INTERVAL_S}).")
    parser.add_argument("--mod", help="Mod name, filled into fixes that mention <ModName>.")
    parser.add_argument("--json", action="store_true", help="Print one JSON object per line instead of text.")
    args = parser.parse_args(argv)
    if args.server and args.dir:
        parser.error("give --server or --dir, not both")
    # 0 would spin a CPU core, a negative value crashes time.sleep and inf overflows it.
    if not (math.isfinite(args.interval) and args.interval >= MIN_INTERVAL_S):
        parser.error(f"--interval must be at least {MIN_INTERVAL_S} seconds")
    # 0 or less would stop after one read and report a clean session; nan never stops.
    if args.duration is not None and not (math.isfinite(args.duration) and args.duration > 0):
        parser.error("--duration must be more than 0 seconds")
    # 0 is the default (only new lines); a negative value would silently act as 0
    # and nan would read every file from its start.
    if not (math.isfinite(args.since) and args.since >= 0):
        parser.error("--since must be 0 or more minutes")
    if args.start_timeout is not None:
        if not args.until_closed:
            parser.error("--start-timeout needs --until-closed")
        # 0 or less would give up before the first process check; nan never gives up.
        if not (math.isfinite(args.start_timeout) and args.start_timeout > 0):
            parser.error("--start-timeout must be more than 0 seconds")

    project = triage.cached_project_dir()
    if args.dir:
        dirs = [d.resolve() for d in args.dir]
    else:
        if project is None:
            print(f"{h.FAIL} No project cached; run /dayz-init, or pass --dir.", file=sys.stderr)
            return 2
        try:
            dirs = session_dirs(project, args.server)
        except FileNotFoundError as e:
            print(f"{h.FAIL} {e}", file=sys.stderr)
            return 2
    learned = triage.learned_path(project) if project else None
    try:
        known = check_known(triage.load_known(triage.KNOWN_ERRORS, learned))
    except (ValueError, json.JSONDecodeError, re.error, KeyError, TypeError) as e:
        print(f"{h.FAIL} Could not load known errors: {e}", file=sys.stderr)
        return 2

    base = project.resolve() if project and not args.dir else None
    emit = json_emitter(out) if args.json else text_emitter(out, base)
    tail = Tail(dirs, since_s=args.since * 60)
    if not args.json:
        stop = "Ctrl+C to stop" if args.duration is None and not args.until_closed else "stops on its own"
        print(f"Watching {len(dirs)} folder(s) for new .rpt and .log lines ({stop}):", file=out)
        for d in dirs:
            note = "" if d.is_dir() else "  (not there yet)"
            print(f"  {_rel(str(d), base)}{note}", file=out)
        out.flush()
    summary = watch(
        tail,
        Watcher(known, {"ModName": args.mod}, emit),
        interval=args.interval,
        duration=args.duration,
        session_alive=client_running if args.until_closed else None,
        start_grace=args.start_timeout,
    )
    print_summary(summary, out, args.json)
    if summary["stopped"] == "cannot read process list":
        print(f"{h.FAIL} Cannot read the process list (the Windows process snapshot failed "
              f"{QUERY_FAILURES_MAX} times in a row), so --until-closed cannot tell when the client closes. "
              "Use --duration instead.", file=sys.stderr)
    # Errors seen (for example read with --since) win over the exit-2 stop reasons.
    if summary["errors"]:
        return 1
    return 2 if summary["stopped"] in ("session never started", "cannot read process list") else 0


if __name__ == "__main__":
    # Log lines can hold characters a cp1252 console can't print.
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
