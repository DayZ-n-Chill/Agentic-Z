"""dayz-test: build, then launch a mod in DayZ Diag with file patching: server and client, one of them, or offline.

    python scripts/tools/dayz-test/dayz_test.py <ModName> [--mode all|server|client|offline]
        [--deps CF ...] [--server-only MOD]... [--server <instance>] [--port N] [--build] [--dry-run]
    python scripts/tools/dayz-test/dayz_test.py --kill

Modes:
  all      /dayz-launch-test: the server, a wait for its port, then the client (the default).
  server   the server alone, with the same command /dayz-launch-test builds.
  client   a client joining the server this tool started earlier (fast reconnects).
  offline  one DayZDiag with -mission and no server. Measured once on 1.30
           (2026-11-18, vanilla template copy): the world loaded and the economy
           spawned loot, but no "Creating Mission" line came within 150 s, so
           whether a player spawns is not known. Use it to look, not to judge a mod.

--build runs /dayz-build-pbo first, and refuses while the deployed PBO is held
open (a running game holds it, and AddonBuilder then fails its copy and leaves
the old PBO in place: references/build-and-storage-traps.md).

Every process this tool starts is recorded in .server/!DayZTest/run.json, and
--kill ends only those. It never stops a DayZDiag it did not start; use
/dayz-stop-test for that. Exit codes: 0 launched (or killed), 1 refused or
failed, 2 bad arguments.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parents[3]
SKILLS = REPO / "skills"
sys.path.insert(0, str(SKILLS / "_shared"))
import skill_helpers as h  # noqa: E402

launch = h.load_module("dayz_test_launch", SKILLS / "dayz-launch-test" / "launch.py")

LAUNCH_PY = SKILLS / "dayz-launch-test" / "launch.py"
BUILD_PY = SKILLS / "dayz-build-pbo" / "build.py"
DIAG_EXE = "DayZDiag_x64.exe"
RECORD_DIR = "!DayZTest"
OK, FAIL = h.OK, h.FAIL


class Refused(RuntimeError):
    """The tool will not go on; the message says why and what to do."""


# --- the record of what this tool started ----------------------------------------------

def record_path(project: Path) -> Path:
    return project / ".server" / RECORD_DIR / "run.json"


def load_record(project: Path) -> dict:
    try:
        data = json.loads(record_path(project).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"pids": {}}
    return data if isinstance(data, dict) and isinstance(data.get("pids"), dict) else {"pids": {}}


def save_record(project: Path, record: dict) -> None:
    path = record_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")


def diag_pids() -> list[int]:
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {DIAG_EXE}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return [int(r[1]) for r in csv.reader(out.splitlines()) if len(r) >= 2 and r[0].lower() == DIAG_EXE.lower() and r[1].isdigit()]


def kill_own(project: Path, running: Callable[[], list[int]] = diag_pids,
             kill: Callable[[int], None] = lambda pid: subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                                                                     capture_output=True)) -> list[int]:
    """End the processes this tool recorded and that still run; return their PIDs."""
    record = load_record(project)
    alive = set(running())
    killed = [pid for pid in record["pids"].values() if pid in alive]
    for pid in killed:
        kill(pid)
    record_path(project).unlink(missing_ok=True)
    return killed


# --- commands ----------------------------------------------------------------------------

def mod_arg(names: list[str]) -> str:
    return ";".join(str(launch.MODS_ROOT / f"@{n}") for n in names)


def server_cmd(diag: Path, project: Path, args) -> list[str]:
    cfg, server_profile, mission, _ = launch.verify_instance_environment(args.server, project, dry_run=args.dry_run)
    return launch.build_server_cmd(diag, mod_arg(args.deps + [args.mod]), args.port, cfg, server_profile, mission,
                                   server_mod_arg=mod_arg(args.server_only))


def client_cmd(diag: Path, project: Path, args) -> list[str]:
    _, _, _, client_profile = launch.verify_instance_environment(args.server, project, dry_run=args.dry_run)
    display = launch.read_client_display_prefs(project, create=not args.dry_run)
    return launch.build_client_cmd(diag, mod_arg(args.deps + [args.mod]), args.port, client_profile, display)


def offline_cmd(diag: Path, project: Path, args) -> list[str]:
    """The client command with -mission= in place of -connect= and -port=: one process, no server."""
    _, _, mission, _ = launch.verify_instance_environment(args.server, project, dry_run=args.dry_run)
    cmd = client_cmd(diag, project, args)
    return [p for p in cmd if p != "-connect=127.0.0.1" and not p.startswith("-port=")] + [f"-mission={mission}"]


# --- build -------------------------------------------------------------------------------

def pbo_held_open(pbo: Path) -> bool:
    """True when another process holds the deployed PBO so it cannot be renamed (a running game does)."""
    if not pbo.is_file():
        return False
    probe = pbo.with_name(pbo.name + ".dayz-test-probe")
    try:
        os.replace(pbo, probe)
    except PermissionError:
        return True
    os.replace(probe, pbo)
    return False


def build(args, run: Callable[[list[str]], int]) -> None:
    pbo = launch.MODS_ROOT / f"@{args.mod}" / "Addons" / f"{args.mod}.pbo"
    if pbo_held_open(pbo):
        raise Refused(f"{pbo} is held open (is the game running?). AddonBuilder would fail its copy and leave the old PBO. "
                      "Stop the session first: dayz_test.py --kill, or /dayz-stop-test for one this tool did not start.")
    rc = run([sys.executable, str(BUILD_PY), args.mod])
    if rc != 0:
        raise Refused(f"/dayz-build-pbo {args.mod} exited {rc}; nothing was launched")


# --- launch ------------------------------------------------------------------------------

def spawn(cmd: list[str]) -> int:
    proc = subprocess.Popen(cmd, close_fds=True, creationflags=h.DETACH_FLAGS)
    return proc.pid


def run_all(args, project: Path) -> dict:
    """The whole session through /dayz-launch-test; the PIDs it prints are recorded."""
    cmd = [sys.executable, str(LAUNCH_PY), *args.deps, args.mod, "--server", args.server, "--port", str(args.port)]
    for name in args.server_only:
        cmd += ["--server-only", name]
    if args.dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        raise Refused(f"/dayz-launch-test exited {proc.returncode}")
    pids = {}
    for line in proc.stdout.splitlines():
        for peer in ("Server", "Client"):
            if line.strip().startswith(f"[OK]") and f"{peer} PID:" in line:
                pids[peer.lower()] = int(line.rsplit(":", 1)[1])
    return pids


def run_one(mode: str, args, project: Path, diag: Path, record: dict,
            start: Callable[[list[str]], int] = spawn) -> dict:
    """server, client or offline: build the command, check what it needs, start it."""
    if mode == "server":
        cmd = server_cmd(diag, project, args)
    elif mode == "client":
        server_pid = record["pids"].get("server")
        if not args.dry_run and server_pid not in diag_pids():
            raise Refused("no server started by this tool is running; start one with --mode server (or --mode all)")
        cmd = client_cmd(diag, project, args)
    else:
        cmd = offline_cmd(diag, project, args)
    if args.dry_run:
        print(f"[DRY-RUN] {mode.capitalize()} cmd: {subprocess.list2cmdline(cmd)}")
        return {}
    if mode == "server":
        h.gate_on_free_port(args.port)
    else:
        h.gate_on_steam()
    print(f"[Launch] {mode.capitalize()}: {subprocess.list2cmdline(cmd)}")
    pid = start(cmd)
    print(f"{OK} {mode.capitalize()} PID: {pid}")
    return {mode: pid}


def parse(argv: Optional[list[str]]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mod", nargs="?", type=launch.mod_name, help="Mod under workspace/<ModName>/, built to P:\\Mods\\@<ModName>\\")
    ap.add_argument("--mode", choices=("all", "server", "client", "offline"), default="all")
    ap.add_argument("--deps", nargs="+", default=[], type=launch.mod_name, metavar="MOD",
                    help="Dependency mods in load order, loaded before the mod (CF or @CF).")
    ap.add_argument("--server-only", action="append", default=[], type=launch.mod_name, metavar="MOD",
                    help="A server-only mod; repeat the flag once per mod.")
    ap.add_argument("--server", default=launch.DEFAULT_INSTANCE, type=launch.instance_name)
    ap.add_argument("--port", type=launch.port, default=2302)
    ap.add_argument("--build", action="store_true", help="Run /dayz-build-pbo <ModName> first.")
    ap.add_argument("--dry-run", action="store_true", help="Print the commands; build and launch nothing.")
    ap.add_argument("--kill", action="store_true", help="End only the processes this tool started, then exit.")
    args = ap.parse_args(argv)
    if not args.kill and not args.mod:
        ap.error("name the mod, or pass --kill")
    return args


def main(argv: Optional[list[str]] = None) -> int:
    args = parse(argv)
    project = h.resolve_project_dir()
    if args.kill:
        killed = kill_own(project)
        print(f"{OK} Stopped {killed}" if killed else f"{OK} Nothing this tool started is running")
        return 0
    try:
        h.gate_on_preflight()
        launch.gate_on_old_layout(project)
        record = load_record(project)
        mine = [p for p in record["pids"].values() if p in diag_pids()]
        if mine and args.mode != "client" and not args.dry_run:
            raise Refused(f"a session this tool started is still running (PIDs {mine}); stop it with --kill first")
        if args.build and not args.dry_run:
            build(args, lambda cmd: subprocess.run(cmd).returncode)
        if not args.dry_run:
            launch.verify_built_mods(args.deps + [args.mod] + args.server_only)
        launch.gate_on_dependencies(args.deps + [args.mod], args.server_only, project)
        if args.mode == "all":
            pids = run_all(args, project)
        else:
            pids = run_one(args.mode, args, project, launch.resolve_diag_client(), record)
    except Refused as e:
        print(f"{FAIL} {e}")
        return 1
    if pids:
        if args.mode != "client":
            record = {"pids": {}}
        record["pids"].update(pids)
        record.update(mod=args.mod, mode=args.mode, instance=args.server, started=datetime.now().isoformat(timespec="seconds"))
        save_record(project, record)
        print(f"Recorded in {record_path(project)}; stop with: python {Path(__file__).as_posix()} --kill")
    return 0


if __name__ == "__main__":
    sys.exit(main())
