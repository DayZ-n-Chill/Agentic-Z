"""The file protocol between the host and the AZ_TestBridge mod.

Each peer (server and client) works only in its own folder,
<profile>/AZTestBridge/<token>/, so files of an earlier session are never read:

    hello.json        written by the peer once it is ready
    cmd/<seq>.json    written by the host: {seq, token, cmd, args}
    res/<seq>.json    written by the peer: {seq, ok, error, peer, game_time_ms, data}

The host writes <seq>.tmp and renames it, so the mod never reads half a file.
The mod reads only the next sequence number it expects (it never lists the
folder), writes the result, then deletes the command. A command counts as done
when its command file is gone and its result parses. A sequence number is used
once: the host refuses to write one that already has a command or result file,
and the mod never runs a command whose result already exists (the stale
cmd_1.json trap in references/actions-doors-and-inventory.md).
"""
from __future__ import annotations

import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any, Callable, Optional

import allowlist

BRIDGE_DIR = "AZTestBridge"
TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
POLL_S = 0.1
RESULT_KEYS = {"seq", "ok", "error", "peer", "game_time_ms", "data"}


class BridgeError(RuntimeError):
    """The host could not send the command or read its result (an ERROR, not a verdict on the mod)."""


class BridgeTimeout(BridgeError):
    pass


class PeerDied(BridgeError):
    pass


def new_token() -> str:
    return secrets.token_hex(16)


def session_dir(profile_dir: Path, token: str) -> Path:
    if not TOKEN_RE.match(token):
        raise BridgeError(f"bad token {token!r}: expected 32 lowercase hex characters")
    return Path(profile_dir) / BRIDGE_DIR / token


def make_dirs(folder: Path) -> None:
    (folder / "cmd").mkdir(parents=True, exist_ok=True)
    (folder / "res").mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Optional[dict]:
    """The JSON object in `path`, or None when it is missing, half written or not an object."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_atomic(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)


class Bridge:
    """Sends allowlisted commands to the peers of one session and waits for their results."""

    def __init__(
        self,
        token: str,
        peer_dirs: dict[str, Path],
        alive: Callable[[str], bool] = lambda peer: True,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        spawns: int = 0,
        allow_exec: bool = False,
        exec_log: Optional[Path] = None,
    ):
        self.token = token
        self.dirs = {peer: session_dir(d, token) for peer, d in peer_dirs.items()}
        self.alive = alive
        self.clock = clock
        self.sleep = sleep
        self.spawns = spawns  # kept in session.json by session.py, so a restarted MCP server keeps counting
        self.allow_exec = allow_exec  # exec only when the session opted in at start
        self.exec_log = exec_log

    # -- state read from the folders, so a restarted MCP server carries on --------------

    def next_seq(self, peer: str) -> int:
        """One more than the highest sequence number already written for this peer."""
        folder = self.dirs[peer]
        seen = [int(p.stem) for sub in ("cmd", "res") for p in (folder / sub).glob("*.json") if p.stem.isdigit()]
        return max(seen, default=0) + 1

    def hello(self, peer: str) -> Optional[dict]:
        hello = read_json(self.dirs[peer] / "hello.json")
        return hello if hello and hello.get("token") == self.token else None

    # -- sending --------------------------------------------------------------------------

    def call(self, cmd: str, args: Optional[dict] = None, peer: Optional[str] = None,
             timeout: Optional[float] = None) -> dict:
        """Check `cmd` against the allowlist, send it to its peer and return the result.

        Commands that run on both peers need `peer`. Raises AllowlistError before
        writing anything, BridgeError when the host side fails.
        """
        spec = allowlist.command(cmd)
        allowed = allowlist.peers(cmd)
        if peer is None:
            if len(allowed) != 1:
                raise allowlist.AllowlistError(f"{cmd} runs on both peers: pass peer='server' or peer='client'")
            peer = allowed[0]
        if peer not in allowed:
            raise allowlist.AllowlistError(f"{cmd} runs on the {spec.peer}, not the {peer}")
        checked = allowlist.validate(cmd, args)
        if spec.opt_in and not self.allow_exec:
            raise allowlist.AllowlistError(f"{cmd} is off: start the session with allow_exec=true to run code in it")
        if spec.opt_in:
            self.log_exec(peer, checked["code"])
        if cmd == "spawn" and self.spawns >= allowlist.MAX_SPAWNS:
            raise allowlist.AllowlistError(f"at most {allowlist.MAX_SPAWNS} spawns per server start (session_restart resets the count)")
        payload = {"cmd": cmd, "args": allowlist.wire_args(cmd, args)}
        if cmd == "spawn":
            self.spawns += 1  # counted when sent: a spawn that timed out may still have happened
        result = self.send(peer, payload, timeout if timeout is not None else allowlist.timeout(cmd, checked))
        return outputs_only(cmd, result)

    def log_exec(self, peer: str, code: str) -> None:
        """Append a code string to the session's exec log before it is sent (owner decision 3, revised)."""
        if self.exec_log is None:
            raise BridgeError("exec needs a session exec log")
        self.exec_log.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.exec_log.open("a", encoding="utf-8") as f:
            f.write(f"--- {stamp} {peer} seq {self.next_seq(peer)} ---\n{code}\n")

    def send(self, peer: str, payload: dict, timeout: float, seq: Optional[int] = None, token: Optional[str] = None) -> dict:
        """Write one command file and wait for its result. Low level: no allowlist check.

        `seq` and `token` are for tests and negative controls only (a command with
        the wrong token must come back refused, never run). A sequence number
        other than the next one, or one that already has a file, is refused.
        """
        if peer not in self.dirs:
            raise BridgeError(f"no {peer} peer in this session")
        folder = self.dirs[peer]
        expected = self.next_seq(peer)
        seq = expected if seq is None else seq
        cmd_path, res_path = folder / "cmd" / f"{seq}.json", folder / "res" / f"{seq}.json"
        if cmd_path.exists() or res_path.exists():
            raise BridgeError(f"sequence {seq} was already used on the {peer}; a sequence number is never reused")
        if seq != expected:
            raise BridgeError(f"sequence {seq} is out of order on the {peer}; the next one is {expected}")
        body = {"seq": seq, "token": self.token if token is None else token, **payload}
        write_atomic(cmd_path, body)
        return self.wait_result(peer, seq, timeout)

    def wait_result(self, peer: str, seq: int, timeout: float) -> dict:
        folder = self.dirs[peer]
        cmd_path, res_path = folder / "cmd" / f"{seq}.json", folder / "res" / f"{seq}.json"
        deadline = self.clock() + timeout
        while True:
            if not cmd_path.exists():
                res = read_json(res_path)
                if res is not None and res.get("seq") == seq:
                    missing = RESULT_KEYS - set(res)
                    if missing:
                        raise BridgeError(f"{peer} result {seq} lacks {sorted(missing)}")
                    return res
            if not self.alive(peer):
                raise PeerDied(f"the {peer} process exited before answering command {seq}")
            if self.clock() >= deadline:
                raise BridgeTimeout(f"the {peer} did not answer command {seq} within {timeout:g} s "
                                    "(is the client in the pause menu, or the mod not loaded?)")
            self.sleep(POLL_S)

    def wait_hellos(self, peers: list[str], timeout: float, ready: Callable[[str, dict], bool] = lambda p, h: True) -> dict:
        """Wait until every peer wrote a hello.json for this token that `ready` accepts."""
        deadline = self.clock() + timeout
        while True:
            hellos = {p: self.hello(p) for p in peers}
            if all(h is not None and ready(p, h) for p, h in hellos.items()):
                return hellos
            for p in peers:
                if not self.alive(p):
                    raise PeerDied(f"the {p} process exited before it said hello")
            if self.clock() >= deadline:
                late = [p for p, h in hellos.items() if h is None or not ready(p, h)]
                raise BridgeTimeout(f"no ready hello from {', '.join(late)} within {timeout:g} s")
            self.sleep(POLL_S * 5)


def close(folder: Path) -> Optional[Path]:
    """Rename a token folder to <token>.done at session stop; returns the new path."""
    if not folder.is_dir():
        return None
    done = folder.with_name(folder.name + ".done")
    n = 1
    while done.exists():
        done = folder.with_name(f"{folder.name}.done{n}")
        n += 1
    os.replace(folder, done)
    return done


def outputs_only(cmd: str, result: dict) -> dict[str, Any]:
    """The result with `data` cut to the outputs the allowlist declares for `cmd`.

    The mod writes every AZB_Data field (most at their defaults); only the
    command's own outputs mean anything. A failed command keeps only its
    `reason`, when the mod gave one.
    """
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if result.get("ok"):
        keep = {k: data.get(k) for k in allowlist.COMMANDS[cmd].outputs}
    else:
        keep = {"reason": data["reason"]} if data.get("reason") else {}
    return {**{k: v for k, v in result.items() if k != "data"}, "data": keep}
