"""A stand-in for one AZ_TestBridge peer, for tests: answers command files the way the mod does.

It follows the mod's rules in AZB_Protocol.c: read only the next expected
cmd/<n>.json, skip a sequence number whose result already exists, refuse a
wrong sequence number or token, write res/<n>.json, then delete the command.
`handlers` maps a command name to a function(args) -> (ok, error, data).
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable, Optional

Handler = Callable[[dict], tuple]


def _ok(data: Optional[dict] = None):
    return True, "", data or {}


DEFAULT_HANDLERS: dict[str, Handler] = {
    "ping": lambda a: _ok({"version": "1.30.fake", "player_loaded": True, "player_count": 1}),
    "mark": lambda a: _ok({"label": a.get("label", "")}),
}


class FakePeer:
    def __init__(self, folder: Path, token: str, peer: str, handlers: Optional[dict[str, Handler]] = None,
                 hello: Optional[dict] = None, delay: float = 0.0):
        self.folder = Path(folder)
        self.token = token
        self.peer = peer
        self.handlers = {**DEFAULT_HANDLERS, **(handlers or {})}
        self.hello = hello
        self.delay = delay
        self.next = 1
        self.ran: list[tuple[int, str]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def __enter__(self):
        (self.folder / "cmd").mkdir(parents=True, exist_ok=True)
        (self.folder / "res").mkdir(parents=True, exist_ok=True)
        if self.hello is not None:
            (self.folder / "hello.json").write_text(json.dumps(
                {"peer": self.peer, "version": "1.30.fake", "token": self.token, "game_time_ms": 1, **self.hello}),
                encoding="utf-8")
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self.stop()

    def stop(self):
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(2)

    def _loop(self):
        while not self._stop.is_set():
            self.step()
            time.sleep(0.01)

    def step(self) -> None:
        cmd_dir, res_dir = self.folder / "cmd", self.folder / "res"
        while (res_dir / f"{self.next}.json").exists():  # never run a command that already has a result
            (cmd_dir / f"{self.next}.json").unlink(missing_ok=True)
            self.next += 1
        path = cmd_dir / f"{self.next}.json"
        if not path.exists():
            return
        seq = self.next
        try:
            cmd = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ok, error, data = False, "bad_json", {}
            cmd = {}
        else:
            if cmd.get("seq") != seq:
                ok, error, data = False, "seq_mismatch", {}
            elif cmd.get("token") != self.token:
                ok, error, data = False, "wrong_token", {}
            elif cmd.get("cmd") not in self.handlers:
                ok, error, data = False, "unknown_command", {}
            else:
                if self.delay:
                    time.sleep(self.delay)
                ok, error, data = self.handlers[cmd["cmd"]](cmd.get("args") or {})
                self.ran.append((seq, cmd["cmd"]))
        (res_dir / f"{seq}.json").write_text(json.dumps(
            {"seq": seq, "ok": ok, "error": error, "peer": self.peer, "game_time_ms": 1000 + seq, "data": data}),
            encoding="utf-8")
        path.unlink()
        self.next += 1
