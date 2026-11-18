"""Session start, status and stop against a fake launch and fake peers: no DayZ, no P: drive."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bridge  # noqa: E402
import session  # noqa: E402
from fakepeer import FakePeer  # noqa: E402

CFG = 'allowFilePatching = 1;\nclass Missions\n{\n\tclass DayZ\n\t{\n\t\ttemplate = "dayzOffline.chernarusplus";\n\t};\n};\n'


@pytest.fixture
def project(tmp_path, monkeypatch):
    inst = tmp_path / ".server" / "chernarus"
    (inst / "mission" / "storage_1" / "data").mkdir(parents=True)
    (inst / "mission" / "init.c").write_text("void main() {}\n", encoding="utf-8")
    (inst / "serverDZ.cfg").write_text(CFG, encoding="utf-8")
    (inst / "Profiles").mkdir()
    (inst / "Profiles" / "settings.json").write_text("{}", encoding="utf-8")
    (inst / "Profiles" / "script_old.log").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr(session.behavior, "make_junction", lambda link, target: link.mkdir())
    return tmp_path


class FakeGame:
    """Stands in for launch.py and the two DayZDiag processes."""

    def __init__(self, rc=0, hello=True, foreign=()):
        self.rc, self.hello = rc, hello
        self.running = list(foreign)
        self.peers: list[FakePeer] = []
        self.cmds, self.killed, self.events = [], [], []
        self.client_handlers = {"resume": lambda a: (True, "", {"paused": False}),
                                "get_out": lambda a: (True, "", {"on_foot": True})}
        self.server_handlers = {"player_state": lambda a: (True, "", {"in_vehicle": True, "seat": 0})}

    def run(self, cmd):
        self.cmds.append(cmd)
        token = cmd[cmd.index("--test-bridge") + 1]
        instance = cmd[cmd.index("--server") + 1]
        if self.rc != 0:
            return self.rc, "[FAIL] something\n"
        self.running += [111, 222]
        if self.hello:
            for peer, handlers, hello in (("server", self.server_handlers, {"player_count": 1}),
                                          ("client", self.client_handlers, {"player_loaded": True})):
                folder = bridge.session_dir(self.dirs[peer], token)
                fake = FakePeer(folder, token, peer, handlers, hello=hello)
                fake.__enter__()
                self.peers.append(fake)
        return 0, f"[Launch] Server: x -mod=P:\\Mods\\@MyMod;P:\\Mods\\@AZ_TestBridge -azBridge={token}\n" \
                  f"Server PID: 111\nClient PID: 222\n{instance}\n"

    def runtime(self, project):
        self.dirs = session.peer_dirs(project, "chernarus-bridge")
        return session.Runtime(
            run=self.run, diag_pids=lambda: list(self.running), install=lambda: self.events.append("install"),
            remove=lambda: self.events.append("remove"), kill=self.kill, sleep=lambda s: None,
        )

    def kill(self, pid):
        self.killed.append(pid)
        self.running.remove(pid)

    def close(self):
        for p in self.peers:
            p.stop()


def test_start_copies_the_instance_launches_with_the_bridge_and_waits_for_both_hellos(project):
    game = FakeGame()
    try:
        out = session.start(project, ["MyMod"], deps=["@CF"], rt=game.runtime(project), hello_timeout=5)
        cmd = game.cmds[0]
        assert cmd[2:5] == ["CF", "MyMod", "--server"] and cmd[5] == "chernarus-bridge"
        assert cmd[-2:] == ["--test-bridge", out["token"]] and bridge.TOKEN_RE.match(out["token"])
        assert game.events == ["install"]
        assert out["pids"] == {"server": 111, "client": 222} and out["hellos"]["client"]["player_loaded"]
        assert out["resume"]["ok"] and "AZ_TestBridge" in out["mod_line"]
        copy = project / ".server" / "chernarus-bridge"
        assert (copy / "mission" / "init.c").is_file() and not (copy / "mission" / "storage_1").exists()
        assert (copy / "Profiles" / "settings.json").is_file() and not (copy / "Profiles" / "script_old.log").exists()
        assert (copy / "dayzOffline.chernarusplus").is_dir()
        assert (project / ".server" / "chernarus" / "mission" / "storage_1").is_dir()  # the user's world is untouched
        state = json.loads(session.state_path(project).read_text(encoding="utf-8"))
        assert state["token"] == out["token"] and state["pids"] == {"server": 111, "client": 222}
    finally:
        game.close()


def test_start_refuses_while_a_foreign_dayzdiag_runs(project):
    game = FakeGame(foreign=[999])
    with pytest.raises(session.SessionError, match="did not start it"):
        session.start(project, ["MyMod"], rt=game.runtime(project))
    assert game.cmds == [] and game.events == [] and game.killed == []


def test_a_failed_launch_is_cleaned_up_and_reported(project):
    game = FakeGame(rc=1)
    with pytest.raises(session.SessionError, match="exited 1"):
        session.start(project, ["MyMod"], rt=game.runtime(project))
    assert game.events == ["install", "remove"] and not session.state_path(project).exists()


def test_no_hello_stops_the_session_again(project):
    game = FakeGame(hello=False)
    with pytest.raises(session.SessionError, match="did not answer"):
        session.start(project, ["MyMod"], rt=game.runtime(project), hello_timeout=0.3)
    assert sorted(game.killed) == [111, 222] and game.events[-1] == "remove"
    assert not session.state_path(project).exists()


def test_stop_gets_out_kills_only_its_own_pids_removes_the_mod_and_renames_the_folders(project):
    game = FakeGame()
    try:
        out = session.start(project, ["MyMod"], rt=game.runtime(project), hello_timeout=5)
        game.running.append(555)  # someone else's DayZDiag started later
        stopped = session.stop(project, game.runtime(project))
    finally:
        game.close()
    assert stopped["stopped"] and sorted(game.killed) == [111, 222] and 555 in game.running
    assert stopped["steps"][0] == {"step": "get-out", "result": True}
    assert game.events == ["install", "remove"]
    for d in game.dirs.values():
        assert (d / "AZTestBridge" / (out["token"] + ".done")).is_dir()
        assert not (d / "AZTestBridge" / out["token"]).exists()
    assert not session.state_path(project).exists()


def test_the_session_record_survives_a_restarted_mcp_server(project):
    game = FakeGame()
    try:
        session.start(project, ["MyMod"], rt=game.runtime(project), hello_timeout=5)
        # A new process: nothing in memory, only session.json.
        rt = game.runtime(project)
        state = session.load_state(project)
        b = session.bridge_of(project, state, rt)
        assert b.next_seq("client") == 2  # resume used seq 1
        assert b.call("resume")["seq"] == 2
        status = session.status(project, rt)
        assert status["alive"] == {"server": True, "client": True} and status["last_seq"]["client"] == 2
        with pytest.raises(session.SessionError, match="already recorded"):
            session.start(project, ["MyMod"], rt=rt)
    finally:
        session.stop(project, game.runtime(project))
        game.close()


def test_marks_and_logs_since(project):
    game = FakeGame()
    try:
        session.start(project, ["MyMod"], rt=game.runtime(project), hello_timeout=5)
        log = game.dirs["server"] / "script_now.log"
        log.write_text("before\n", encoding="utf-8")
        session.mark(project, "m1", game.runtime(project))
        with log.open("a", encoding="utf-8") as f:
            f.write("[AZ-BRIDGE] ERROR result 9: x\nafter\n")
        got = session.logs_since(project, "m1")
        assert [ln["text"] for ln in got["lines"]] == ["[AZ-BRIDGE] ERROR result 9: x", "after"]
        assert len(got["bridge_errors"]) == 1
        assert "before" in [ln["text"] for ln in session.logs_since(project)["lines"]]
        with pytest.raises(session.SessionError, match="no mark"):
            session.logs_since(project, "nope")
    finally:
        session.stop(project, game.runtime(project))
        game.close()


def test_copy_refuses_a_bridge_copy_and_a_missing_instance(project):
    with pytest.raises(session.SessionError, match="not the bridge copy"):
        session.copy_instance(project, "chernarus-bridge")
    with pytest.raises(session.SessionError, match="not set up"):
        session.copy_instance(project, "livonia")
