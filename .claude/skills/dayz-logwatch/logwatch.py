"""/dayz-logwatch: tail a test session's logs and triage each new error line as it appears.

Watches the server and client log folders of the local test session (the
.server/<instance>/Profiles/ folders and the shared .server/!ClientDiagLogs/),
reads the .rpt and .log lines written after it started, and runs each error line
through /dayz-gate's triage (triage.py, known-errors.json and the project's
learned file). A known error prints its fix and owner; a new one is flagged for
dayz-mod-debugger. The same error again (same fingerprint) is only counted.

Usage:
  python logwatch.py [--server <instance> ...] [--dir DIR ...] [--since MINUTES]
                     [--duration S | --until-closed] [--interval S] [--mod <ModName>] [--json]

Exit codes: 0 no error lines seen, 1 at least one error line, 2 cannot run
(or --until-closed saw no session start and no error line).
See SKILL.md for details.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
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
CLOSED_CHECK_S = 5.0  # how often --until-closed asks whether the DayZ Diag client still runs
START_GRACE_S = 300.0  # how long --until-closed waits for the DayZ Diag client to start before giving up
SERVER_FLAG = re.compile(r"(?i)(?:^|\s)-server(?:\s|$)")


def is_log(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in LOG_SUFFIXES


def session_dirs(project: Path, instances: list[str]) -> list[Path]:
    """Server Profiles/ of each instance (all of them when none are named) and the client log folder."""
    server_root = project / ".server"
    if not server_root.is_dir():
        raise FileNotFoundError(f"no .server/ folder in {project}; run /dayz-add-server first")
    if instances:
        missing = [i for i in instances if not (server_root / i).is_dir()]
        if missing:
            raise FileNotFoundError(f"no test server instance {', '.join(missing)} under {server_root}")
    else:
        instances = sorted(p.name for p in server_root.iterdir() if p.is_dir() and not p.name.startswith("!"))
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

    def feed_files(self, paths: list[Path]) -> None:
        """A new crash log means the game crashed, whatever its lines say."""
        for path in paths:
            if path.name.lower().startswith("crash"):
                self.feed_crash(path)

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


def client_running() -> bool:
    """True while a DayZDiag_x64.exe without -server (the game client) is running.

    tasklist cannot show command lines, so this asks Win32_Process. Each process
    prints one "proc:" line; one whose command line Windows will not show counts
    as a client, and so does a query that fails, so the watch never stops early
    on a process it cannot read.
    """
    query = (
        f"Get-CimInstance Win32_Process -Filter \"Name='{DIAG_EXE}'\" "
        "| ForEach-Object { 'proc:' + $_.CommandLine }"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", query],
            capture_output=True, text=True, errors="replace",
        )
    except OSError:  # PowerShell missing from PATH: cannot tell, so keep watching
        return True
    if proc.returncode != 0:  # the query failed (CIM timeout and the like): keep watching
        return True
    return any(is_client(line[5:]) for line in proc.stdout.splitlines() if line.startswith("proc:"))


def watch(
    tail: Tail,
    watcher: Watcher,
    *,
    interval: float = POLL_S,
    duration: Optional[float] = None,
    session_alive: Optional[Callable[[], bool]] = None,
    start_grace: Optional[float] = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict:
    """Poll until the duration ends, the session closes (session_alive False) or Ctrl+C.

    A session counts as closed only after it has been seen running, so a watch
    started before /dayz-launch-test waits for the game. If it never starts
    within start_grace seconds (default START_GRACE_S), the watch stops with
    reason "session never started".

    One last read after stopping catches the lines written at the end, including a
    last line without a newline.
    """
    started = clock()
    last_check = None
    seen_alive = False
    grace = START_GRACE_S if start_grace is None else start_grace
    reason = "interrupted"
    try:
        while True:
            watcher.feed_files(tail.new_files())
            watcher.feed(tail.poll())
            now = clock()
            if duration is not None and now - started >= duration:
                reason = "duration"
                break
            if session_alive is not None and (last_check is None or now - last_check >= CLOSED_CHECK_S):
                last_check = now
                if session_alive():
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
                        help="Test server instance to watch (repeatable; default: every instance).")
    parser.add_argument("--dir", action="append", default=[], type=Path, metavar="DIR",
                        help="Watch this folder instead of the project's session folders (repeatable).")
    parser.add_argument("--since", type=float, default=0, metavar="MINUTES",
                        help="Read files changed in the last MINUTES from their start (default 0: only new lines).")
    stop_on = parser.add_mutually_exclusive_group()
    stop_on.add_argument("--duration", type=float, metavar="S", help="Stop after S seconds.")
    stop_on.add_argument("--until-closed", action="store_true",
                         help=f"Stop once the {DIAG_EXE} client (no -server) seen running has closed.")
    parser.add_argument("--interval", type=float, default=POLL_S, metavar="S", help="Seconds between reads (default 1).")
    parser.add_argument("--mod", help="Mod name, filled into fixes that mention <ModName>.")
    parser.add_argument("--json", action="store_true", help="Print one JSON object per line instead of text.")
    args = parser.parse_args(argv)
    if args.server and args.dir:
        parser.error("give --server or --dir, not both")

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
        known = triage.load_known(triage.KNOWN_ERRORS, learned)
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
    )
    print_summary(summary, out, args.json)
    # Errors seen (for example read with --since) win over "session never started".
    if summary["errors"]:
        return 1
    return 2 if summary["stopped"] == "session never started" else 0


if __name__ == "__main__":
    # Log lines can hold characters a cp1252 console can't print.
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
