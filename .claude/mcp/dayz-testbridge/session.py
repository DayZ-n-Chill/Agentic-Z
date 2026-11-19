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
launch = h.load_module("dayz_testbridge_launch", SKILLS / "dayz-launch-test" / "launch.py")

LAUNCH_PY = SKILLS / "dayz-launch-test" / "launch.py"
BRIDGE_SOURCE = SKILLS / "dayz-launch-test" / "assets" / "testbridge-mod" / "src" / "AZ_TestBridge"
BRIDGE_MOD = "AZ_TestBridge"
INSTANCE_SUFFIX = "-bridge"
STATE_DIR = "!TestBridge"
DIAG_EXE = "DayZDiag_x64.exe"
P_DRIVE = Path("P:\\")
HELLO_TIMEOUT_S = 300.0
STOP_WAIT_S = 30.0
SHUTDOWN_WAIT_S = 180.0  # an orderly server exit saves the world first
LOGOUT_WAIT_S = 240.0    # how long a restarted client waits for the server to drop the old player
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
    spawn: Callable[[list[str]], int] = lambda cmd: subprocess.Popen(cmd, close_fds=True, creationflags=h.DETACH_FLAGS).pid


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
        allow_exec=bool(state.get("allow_exec")), exec_log=exec_log_path(project_dir, state["token"]),
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
          port: int = 2302, rt: Optional[Runtime] = None, hello_timeout: float = HELLO_TIMEOUT_S,
          allow_exec: bool = False) -> dict:
    """Start a session. allow_exec turns on the `exec` command for this session only (owner decision 3, revised)."""
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
    state = {"token": token, "instance": copy, "port": port, "mods": mods, "deps": deps, "pids": {},
             "dirs": {p: str(d) for p, d in dirs.items()}, "offsets": logs.snapshot(dirs), "marks": {}, "spawns": 0,
             "mod_line": "", "allow_exec": bool(allow_exec), "restarts": 0,
             "started": datetime.now().isoformat(timespec="seconds")}
    rt.install()
    _launch(project_dir, state, rt)
    return {**_await_ready(project_dir, state, rt, hello_timeout), "token": token, "instance": copy,
            "allow_exec": state["allow_exec"], "exec_log": str(exec_log_path(project_dir, token)) if allow_exec else None,
            "state": str(state_path(project_dir))}


def exec_log_path(project_dir: Path, token: str) -> Path:
    return state_path(project_dir).parent / f"exec-{token}.log"


def _launch(project_dir: Path, state: dict, rt: Runtime) -> None:
    """Run /dayz-launch-test for the session's mods, instance and token; record the two process ids."""
    cmd = [sys.executable, str(LAUNCH_PY), *state["deps"], *state["mods"], "--server", state["instance"],
           "--port", str(state["port"]), "--test-bridge", state["token"]]
    if state.get("allow_exec"):
        cmd.append("--test-bridge-exec")
    rc, out = rt.run(cmd)
    pids = {}
    for peer in ("server", "client"):
        m = re.search(rf"{peer.capitalize()} PID: (\d+)", out)
        if m:
            pids[peer] = int(m.group(1))
    mod_line = re.search(r"-mod=(\S+)", out)
    state["pids"] = pids
    state["mod_line"] = mod_line.group(1) if mod_line else state.get("mod_line", "")
    if pids:
        save_state(project_dir, state)
    if rc != 0 or len(pids) != 2:
        stop(project_dir, rt, state=state)
        tail = "\n".join(out.strip().splitlines()[-15:])
        raise SessionError(f"/dayz-launch-test exited {rc} and the session was stopped again:\n{tail}")


def _await_ready(project_dir: Path, state: dict, rt: Runtime, hello_timeout: float, peers=("server", "client")) -> dict:
    """Wait for the hellos (the client's with its player loaded), then close the pause menu."""
    b = bridge_of(project_dir, state, rt)
    try:
        hellos = b.wait_hellos(list(peers), hello_timeout,
                               lambda peer, hello: peer == "server" or bool(hello.get("player_loaded")))
        resumed = b.call("resume")
    except bridge.BridgeError as e:
        stop(project_dir, rt, state=state)
        raise SessionError(f"the session started but the bridge did not answer ({e}); it was stopped again. "
                           "Read the client and server script logs for a compile error in AZ_TestBridge.") from e
    return {"pids": state["pids"], "hellos": hellos, "resume": resumed, "mod_line": state["mod_line"]}


def _clear_hello(state: dict, peer: str) -> None:
    (bridge.session_dir(Path(state["dirs"][peer]), state["token"]) / "hello.json").unlink(missing_ok=True)


def _wait_gone(rt: Runtime, pids: list[int], timeout: float) -> bool:
    deadline = rt.clock() + timeout
    while set(pids) & set(rt.diag_pids()):
        if rt.clock() >= deadline:
            return False
        rt.sleep(1)
    return True


def restart(project_dir: Path, keep_storage: bool = True, rt: Optional[Runtime] = None,
            hello_timeout: float = HELLO_TIMEOUT_S, shutdown_timeout: float = SHUTDOWN_WAIT_S) -> dict:
    """Shut the server down in order (it saves its world), then start server and client again.

    keep_storage keeps the storage this session's own server wrote in the
    storage-free copy, so a mod's saved data can be checked after a restart
    (owner decision 1 still holds: the copy starts without storage). With
    keep_storage=False the copy is made fresh again. The token stays, so the
    sequence numbers go on; each peer skips commands that already have results.
    """
    rt = rt or real_runtime()
    state = load_state(project_dir)
    if state is None:
        raise SessionError("no session is running; run session_start first")
    b = bridge_of(project_dir, state, rt)
    pids = dict(state["pids"])
    running = set(rt.diag_pids())
    steps: list[dict] = []
    if pids.get("client") in running:  # out of any car first, then the client goes, so the server saves no seated player
        try:
            if b.call("player_state", timeout=EJECT_TIMEOUT_S)["data"].get("in_vehicle"):
                b.call("get_out")
        except bridge.BridgeError as e:
            steps.append({"step": "get-out", "error": str(e)})
        rt.kill(pids["client"])
    graceful = False
    if pids.get("server") in running:
        b.call("shutdown")
        graceful = _wait_gone(rt, [pids["server"]], shutdown_timeout)
        if not graceful:
            rt.kill(pids["server"])
            _wait_gone(rt, [pids["server"]], STOP_WAIT_S)
    _wait_gone(rt, [p for p in pids.values()], STOP_WAIT_S)
    steps.append({"step": "shutdown", "graceful": graceful})
    if not keep_storage:
        copy_instance(project_dir, state["instance"][:-len(INSTANCE_SUFFIX)])
    storage = sorted(p.name for p in (server_root(project_dir) / state["instance"] / "mission").glob("storage_*"))
    for peer in ("server", "client"):
        _clear_hello(state, peer)
    state["restarts"] = state.get("restarts", 0) + 1
    state["spawns"] = 0  # the restarted server spawns afresh; its clear_spawns list starts empty
    _launch(project_dir, state, rt)
    ready = _await_ready(project_dir, state, rt, hello_timeout)
    return {**ready, "steps": steps, "graceful_shutdown": graceful, "storage_kept": keep_storage, "storage": storage}


def restart_client(project_dir: Path, rt: Optional[Runtime] = None, hello_timeout: float = HELLO_TIMEOUT_S) -> dict:
    """End only the client and start it again into the running server (a stuck picture, a client bound to its first car)."""
    rt = rt or real_runtime()
    state = load_state(project_dir)
    if state is None:
        raise SessionError("no session is running; run session_start first")
    running = set(rt.diag_pids())
    if state["pids"].get("server") not in running:
        raise SessionError("the session's server is not running; use session_restart")
    if state["pids"].get("client") in running:
        rt.kill(state["pids"]["client"])
        _wait_gone(rt, [state["pids"]["client"]], STOP_WAIT_S)
    # Measured: a client started while the server still held the killed client's player
    # was refused (error 0x00040033) and fell back to the main menu. Wait for the server to let go.
    b = bridge_of(project_dir, state, rt)
    deadline = rt.clock() + LOGOUT_WAIT_S
    while b.call("ping", peer="server")["data"].get("player_count"):
        if rt.clock() >= deadline:
            raise SessionError(f"the server still holds the old client's player after {LOGOUT_WAIT_S:g} s")
        rt.sleep(3)
    _clear_hello(state, "client")
    state["pids"]["client"] = rt.spawn(client_command(project_dir, state))
    save_state(project_dir, state)
    return _await_ready(project_dir, state, rt, hello_timeout, peers=("client",))


def client_command(project_dir: Path, state: dict) -> list[str]:
    """The client line /dayz-launch-test builds for this session, bridge and token included."""
    diag = launch.resolve_diag_client()
    _, _, _, client_profile = launch.verify_instance_environment(state["instance"], project_dir)
    mod_arg = ";".join(str(launch.MODS_ROOT / f"@{n}") for n in state["deps"] + state["mods"])
    display = launch.read_client_display_prefs(project_dir)
    cmd = launch.add_test_bridge(mod_arg, launch.build_client_cmd(diag, mod_arg, state["port"], client_profile, display),
                                 state["token"])
    if state.get("allow_exec"):
        cmd.append("-azBridgeExec=1")
    return cmd


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
    """Save the spawn count so the next call keeps counting from it (session_restart resets it); re-read the record first so a mark saved meanwhile stays."""
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
