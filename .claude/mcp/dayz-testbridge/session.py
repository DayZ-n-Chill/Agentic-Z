"""Start, check and stop one dayz-testbridge session: a storage-free instance copy, the bridge mod, both peers.

session_start
  1. refuses while any DayZDiag_x64.exe runs (the tool never touches a session it did not start);
  2. copies .server/<instance>/ to .server/<instance>-bridge/ without storage_* (plan decision 1);
  3. makes the token and both peers' token folders;
  4. packs the bridge into P:\\Mods\\@AZ_TestBridge\\ with the shared helper packer;
  5. runs /dayz-launch-test <deps> <mods> --server <instance>-bridge --test-bridge <token>;
  6. saves .server/!TestBridge/session.json at once, so a restarted MCP server can still stop it;
  7. waits for both hello.json files, the client's with its player loaded, then closes the pause menu.

session_stop always runs to the end: get the player out of a car on the client,
kill only the process ids this session started, remove @AZ_TestBridge, rename
the token folders to <token>.done and delete session.json.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, NamedTuple, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SKILLS = REPO / "skills"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SKILLS / "_shared"))
import bridge  # noqa: E402
import helper_mod  # noqa: E402
import logs  # noqa: E402
import skill_helpers as h  # noqa: E402

behavior = h.load_module("dayz_testbridge_behavior", SKILLS / "dayz-gate" / "behavior.py")

LAUNCH_PY = SKILLS / "dayz-launch-test" / "launch.py"
BRIDGE_SOURCE = SKILLS / "dayz-launch-test" / "assets" / "testbridge-mod" / "src" / "AZ_TestBridge"
BRIDGE_MOD = "AZ_TestBridge"
INSTANCE_SUFFIX = "-bridge"
STATE_DIR = "!TestBridge"
DIAG_EXE = "DayZDiag_x64.exe"
P_DRIVE = Path("P:\\")
HELLO_TIMEOUT_S = 300.0
STOP_WAIT_S = 30.0
EJECT_TIMEOUT_S = 5.0  # session_stop asks the server where the player is; a silent bridge must not hold the stop


class SessionError(RuntimeError):
    """The session could not start or stop (an ERROR of the tool, not a verdict on a mod)."""


def run_captured(cmd: list[str]) -> tuple[int, str]:
    """(exit code, stdout+stderr). A temp file, not a pipe: launch.py leaves DayZ running with the pipe inherited."""
    with tempfile.TemporaryFile() as out:
        rc = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
        out.seek(0)
        return rc, out.read().decode("utf-8", errors="replace")


def parse_tasklist(output: str, pid: Optional[int] = None) -> list[int]:
    pids = []
    for row in csv.reader(output.splitlines()):
        if len(row) >= 2 and row[0].lower() == DIAG_EXE.lower() and row[1].isdigit():
            if pid is None or int(row[1]) == pid:
                pids.append(int(row[1]))
    return pids


class Runtime(NamedTuple):
    """Everything that touches processes, the P: drive or time, so tests run without DayZ."""
    run: Callable[[list[str]], tuple[int, str]]
    diag_pids: Callable[[], list[int]]
    install: Callable[[], None]
    remove: Callable[[], None]
    kill: Callable[[int], None]
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic


def real_runtime() -> Runtime:
    def diag_pids() -> list[int]:
        _, out = run_captured(["tasklist", "/FI", f"IMAGENAME eq {DIAG_EXE}", "/FO", "CSV", "/NH"])
        return parse_tasklist(out)

    def install() -> None:
        tools = h.preflight.find_dayz_tools()
        if tools is None:
            raise SessionError("DayZ Tools not found, so the bridge mod cannot be packed. Run /dayz-preflight.")
        addon_builder = tools / "Bin" / "AddonBuilder" / "AddonBuilder.exe"
        try:
            helper_mod.install(BRIDGE_SOURCE, BRIDGE_MOD, P_DRIVE, addon_builder, h.SCAFFOLD_MARKER, run_captured)
        except helper_mod.HelperModError as e:
            raise SessionError(f"could not pack {BRIDGE_MOD}: {e}") from e

    def remove() -> None:
        helper_mod.remove(P_DRIVE, BRIDGE_MOD, h.SCAFFOLD_MARKER)

    def kill(pid: int) -> None:
        run_captured(["taskkill", "/F", "/PID", str(pid)])

    return Runtime(run=run_captured, diag_pids=diag_pids, install=install, remove=remove, kill=kill)


# --- paths and state -----------------------------------------------------------------

def server_root(project_dir: Path) -> Path:
    return project_dir / ".server"


def state_path(project_dir: Path) -> Path:
    return server_root(project_dir) / STATE_DIR / "session.json"


def peer_dirs(project_dir: Path, instance_copy: str) -> dict[str, Path]:
    """Each peer's -profiles= folder, as /dayz-launch-test sets them."""
    return {"server": server_root(project_dir) / instance_copy / "Profiles",
            "client": server_root(project_dir) / "!ClientDiagLogs"}


def load_state(project_dir: Path) -> Optional[dict]:
    return bridge.read_json(state_path(project_dir))


def save_state(project_dir: Path, state: dict) -> None:
    path = state_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    bridge.write_atomic(path, state)


ALIVE_CHECK_S = 2.0  # tasklist is slow; look at the processes at most this often while waiting


def bridge_of(project_dir: Path, state: dict, rt: Runtime) -> bridge.Bridge:
    pids = state.get("pids", {})
    seen = {"at": None, "running": set()}

    def alive(peer: str) -> bool:
        now = rt.clock()
        if seen["at"] is None or now - seen["at"] >= ALIVE_CHECK_S:
            seen["at"], seen["running"] = now, set(rt.diag_pids())
        return pids.get(peer) in seen["running"]

    return bridge.Bridge(
        state["token"], {p: Path(d) for p, d in state["dirs"].items()},
        alive=alive, clock=rt.clock, sleep=rt.sleep, spawns=state.get("spawns", 0),
    )


# --- the instance copy ---------------------------------------------------------------

def copy_instance(project_dir: Path, instance: str) -> str:
    """Copy .server/<instance>/ to .server/<instance>-bridge/ with no storage_* (a fresh test world).

    The copy gets serverDZ.cfg, mission/ without storage_*, the <template>/
    junction /dayz-launch-test needs, and the Profiles/ settings without logs,
    the same way /dayz-gate behavior copies an instance (minus its test mission).
    """
    behavior.check_instance(instance)
    if instance.endswith(INSTANCE_SUFFIX):
        raise SessionError(f"pass the original instance, not the bridge copy {instance!r}")
    server = server_root(project_dir)
    src = server / instance
    cfg = src / "serverDZ.cfg"
    if not cfg.is_file() or not (src / "mission").is_dir():
        raise SessionError(f"instance {instance!r} is not set up (no serverDZ.cfg or mission/). Run /dayz-add-server {instance}")
    match = behavior.TEMPLATE_RE.search(cfg.read_text(encoding="utf-8", errors="replace"))
    if match is None or not behavior.TEMPLATE_NAME_RE.fullmatch(match.group(1)) or match.group(1) in (".", ".."):
        raise SessionError(f'{cfg} has no usable template = "..."; line. Run /dayz-add-server {instance}')
    template = match.group(1)
    name = instance + INSTANCE_SUFFIX
    dst = server / name
    dst.mkdir(parents=True, exist_ok=True)
    behavior._remove_tree(dst / template)
    behavior._remove_tree(dst / "mission")
    shutil.copytree(src / "mission", dst / "mission", ignore=shutil.ignore_patterns("storage_*"))
    shutil.copy2(cfg, dst / "serverDZ.cfg")
    behavior.make_junction(dst / template, dst / "mission")
    if (src / "Profiles").is_dir():
        shutil.copytree(src / "Profiles", dst / "Profiles", ignore=behavior._profile_logs, dirs_exist_ok=True)
    else:
        (dst / "Profiles").mkdir(exist_ok=True)
    return name


# --- start, status, stop ----------------------------------------------------------------

def start(project_dir: Path, mods: list[str], deps: Optional[list[str]] = None, server: str = "chernarus",
          port: int = 2302, rt: Optional[Runtime] = None, hello_timeout: float = HELLO_TIMEOUT_S) -> dict:
    rt = rt or real_runtime()
    deps = [d.lstrip("@") for d in deps or []]
    mods = [m.lstrip("@") for m in mods]  # empty: vanilla with the bridge only
    old = load_state(project_dir)
    if old is not None:
        raise SessionError(f"a test bridge session is already recorded ({state_path(project_dir)}); run session_stop first")
    running = rt.diag_pids()
    if running:
        raise SessionError(f"{DIAG_EXE} is already running (PIDs {running}) and this tool did not start it. "
                           "Close it yourself; the test bridge never stops a session it did not start.")

    copy = copy_instance(project_dir, server)
    token = bridge.new_token()
    dirs = peer_dirs(project_dir, copy)
    for d in dirs.values():
        bridge.make_dirs(bridge.session_dir(d, token))
    offsets = logs.snapshot(dirs)
    rt.install()
    cmd = [sys.executable, str(LAUNCH_PY), *deps, *mods, "--server", copy, "--port", str(port), "--test-bridge", token]
    rc, out = rt.run(cmd)
    pids = {}
    for peer in ("server", "client"):
        m = re.search(rf"{peer.capitalize()} PID: (\d+)", out)
        if m:
            pids[peer] = int(m.group(1))
    mod_line = re.search(r"-mod=(\S+)", out)
    state = {"token": token, "instance": copy, "port": port, "mods": mods, "deps": deps, "pids": pids,
             "dirs": {p: str(d) for p, d in dirs.items()}, "offsets": offsets, "marks": {}, "spawns": 0,
             "mod_line": mod_line.group(1) if mod_line else "",
             "started": datetime.now().isoformat(timespec="seconds")}
    if pids:
        save_state(project_dir, state)
    if rc != 0 or len(pids) != 2:
        stop(project_dir, rt, state=state)
        tail = "\n".join(out.strip().splitlines()[-15:])
        raise SessionError(f"/dayz-launch-test exited {rc} and the session was stopped again:\n{tail}")

    b = bridge_of(project_dir, state, rt)
    try:
        hellos = b.wait_hellos(["server", "client"], hello_timeout,
                               lambda peer, hello: peer == "server" or bool(hello.get("player_loaded")))
        resumed = b.call("resume")
    except bridge.BridgeError as e:
        stop(project_dir, rt, state=state)
        raise SessionError(f"the session started but the bridge did not answer ({e}); it was stopped again. "
                           "Read the client and server script logs for a compile error in AZ_TestBridge.") from e
    return {"token": token, "instance": copy, "pids": pids, "hellos": hellos, "resume": resumed,
            "mod_line": state["mod_line"], "state": str(state_path(project_dir))}


def status(project_dir: Path, rt: Optional[Runtime] = None) -> dict:
    rt = rt or real_runtime()
    state = load_state(project_dir)
    if state is None:
        return {"running": False, "reason": "no session recorded"}
    running = set(rt.diag_pids())
    b = bridge_of(project_dir, state, rt)
    dirs = {p: Path(d) for p, d in state["dirs"].items()}
    return {
        "running": True, "token": state["token"], "instance": state["instance"],
        "alive": {peer: pid in running for peer, pid in state["pids"].items()},
        "hellos": {peer: b.hello(peer) for peer in dirs},
        "last_seq": {peer: b.next_seq(peer) - 1 for peer in dirs},
        "crash_logs": logs.new_crash_logs(dirs, state["offsets"]),
        "mod_line": state.get("mod_line", ""),
    }


def stop(project_dir: Path, rt: Optional[Runtime] = None, state: Optional[dict] = None) -> dict:
    """Stop the recorded session. Every step runs even when one before it failed."""
    rt = rt or real_runtime()
    state = state or load_state(project_dir)
    if state is None:
        return {"stopped": False, "reason": "no session recorded"}
    steps: list[dict] = []
    pids = state.get("pids", {})
    running = set(rt.diag_pids())

    # 1. The player out of any car on the client first: a car deleted with crew crashed 1.30.
    if pids.get("client") in running and pids.get("server") in running:
        try:
            b = bridge_of(project_dir, state, rt)
            player = b.call("player_state", timeout=EJECT_TIMEOUT_S)
            if player.get("ok") and player["data"].get("in_vehicle"):
                steps.append({"step": "get-out", "result": b.call("get_out").get("ok")})
        except Exception as e:  # noqa: BLE001 - the stop must go on whatever the bridge does
            steps.append({"step": "get-out", "error": str(e)})

    # 2. Only the processes this session started.
    killed = []
    for peer in ("client", "server"):
        pid = pids.get(peer)
        if pid in running:
            rt.kill(pid)
            killed.append(pid)
    deadline = rt.clock() + STOP_WAIT_S
    while killed and set(killed) & set(rt.diag_pids()) and rt.clock() < deadline:
        rt.sleep(1)
    left = sorted(set(killed) & set(rt.diag_pids()))
    steps.append({"step": "kill", "killed": killed, "still_running": left})

    # 3. The bridge mod.
    try:
        rt.remove()
        steps.append({"step": "remove-mod", "result": f"@{BRIDGE_MOD} removed"})
    except OSError as e:
        steps.append({"step": "remove-mod", "error": str(e)})

    # 4. The token folders.
    for peer, d in state.get("dirs", {}).items():
        try:
            done = bridge.close(bridge.session_dir(Path(d), state["token"]))
            steps.append({"step": f"close-{peer}", "result": str(done) if done else "no folder"})
        except OSError as e:
            steps.append({"step": f"close-{peer}", "error": str(e)})

    # 5. The record.
    state_path(project_dir).unlink(missing_ok=True)
    return {"stopped": not left, "steps": steps}


def remember(project_dir: Path, state: dict, b: bridge.Bridge) -> None:
    """Save the spawn count so a restarted server keeps it; re-read the record first so a mark saved meanwhile stays."""
    fresh = load_state(project_dir) or state
    fresh["spawns"] = b.spawns
    save_state(project_dir, fresh)


def mark(project_dir: Path, label: str, rt: Optional[Runtime] = None) -> dict:
    """Save log offsets under `label`, then print MARK <label> on both peers."""
    rt = rt or real_runtime()
    state = load_state(project_dir)
    if state is None:
        raise SessionError("no session is running; run session_start first")
    dirs = {p: Path(d) for p, d in state["dirs"].items()}
    state["marks"][label] = logs.snapshot(dirs)
    save_state(project_dir, state)
    b = bridge_of(project_dir, state, rt)
    return {peer: b.call("mark", {"label": label}, peer=peer) for peer in ("server", "client")}


def logs_since(project_dir: Path, label: str = "", peers: Optional[list[str]] = None, kinds: tuple = logs.KINDS,
               pattern: Optional[str] = None, with_triage: bool = False) -> dict:
    """Log lines since a mark (or since the session started when `label` is empty)."""
    state = load_state(project_dir)
    if state is None:
        raise SessionError("no session is running; run session_start first")
    if label and label not in state["marks"]:
        raise SessionError(f"no mark {label!r}; marks so far: {sorted(state['marks'])}")
    offsets = state["marks"][label] if label else state["offsets"]
    dirs = {p: Path(d) for p, d in state["dirs"].items()}
    lines = logs.lines_since(dirs, offsets, peers, kinds, pattern)
    if with_triage:
        lines = logs.triage(lines)
    return {"since": label or "session start", "lines": lines, "bridge_errors": logs.bridge_errors(lines)}
