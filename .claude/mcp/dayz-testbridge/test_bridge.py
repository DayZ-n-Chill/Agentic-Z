"""The file protocol: atomic writes, one use per sequence number, tokens, timeouts and a dying peer."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import allowlist  # noqa: E402
import bridge  # noqa: E402
from fakepeer import FakePeer  # noqa: E402

TOKEN = "0123456789abcdef0123456789abcdef"
OLD_TOKEN = "fedcba9876543210fedcba9876543210"


@pytest.fixture
def dirs(tmp_path):
    return {"server": tmp_path / "server_profile", "client": tmp_path / "client_profile"}


def make(dirs, **kw) -> bridge.Bridge:
    b = bridge.Bridge(TOKEN, dirs, **kw)
    for folder in b.dirs.values():
        bridge.make_dirs(folder)
    return b


def test_a_command_round_trips_and_the_command_file_is_gone(dirs):
    b = make(dirs)
    with FakePeer(b.dirs["server"], TOKEN, "server") as peer:
        res = b.call("ping", peer="server")
        res2 = b.call("mark", {"label": "start"}, peer="server")
    assert res["ok"] and res["seq"] == 1 and res["data"]["player_loaded"] is True
    assert res2["seq"] == 2 and res2["data"] == {"label": "start"}
    assert peer.ran == [(1, "ping"), (2, "mark")]
    assert not list((b.dirs["server"] / "cmd").iterdir())
    assert sorted(p.name for p in (b.dirs["server"] / "res").iterdir()) == ["1.json", "2.json"]


def test_the_command_file_is_written_whole_by_rename(dirs, monkeypatch):
    b = make(dirs)
    seen = []
    real_replace = bridge.os.replace

    def spy(src, dst):
        seen.append((Path(src).name, Path(dst).name, json.loads(Path(src).read_text(encoding="utf-8"))["seq"]))
        real_replace(src, dst)

    monkeypatch.setattr(bridge.os, "replace", spy)
    with FakePeer(b.dirs["client"], TOKEN, "client"):
        b.call("ping", peer="client")
    assert seen == [("1.tmp", "1.json", 1)]


def test_every_wire_field_is_written_with_defaults(dirs):
    b = make(dirs)
    got = {}

    def spawn(args):
        got.update(args)
        return True, "", {"net_id": "1,2", "type": "Hatchback_02", "class_name": "Hatchback_02", "pos": [1, 2, 3]}

    with FakePeer(b.dirs["server"], TOKEN, "server", {"spawn": spawn}):
        res = b.call("spawn", {"cls": "Hatchback_02", "pos": [4200, 0, 10650]})
    assert set(got) == set(allowlist.WIRE_DEFAULTS)
    assert got["flags"] == allowlist.DEFAULT_SPAWN_FLAGS == 8389668 and got["placement"] == 512
    assert res["data"] == {"net_id": "1,2", "type": "Hatchback_02", "class_name": "Hatchback_02", "pos": [1, 2, 3]}
    assert b.spawns == 1


def test_a_reused_sequence_number_is_refused_before_writing(dirs):
    b = make(dirs)
    with FakePeer(b.dirs["server"], TOKEN, "server"):
        b.call("ping", peer="server")
    with pytest.raises(bridge.BridgeError, match="already used"):
        b.send("server", {"cmd": "ping", "args": {}}, 1, seq=1)


def test_an_out_of_order_sequence_number_is_refused_before_writing(dirs):
    b = make(dirs)
    with pytest.raises(bridge.BridgeError, match="out of order"):
        b.send("server", {"cmd": "ping", "args": {}}, 1, seq=5)
    assert not list((b.dirs["server"] / "cmd").iterdir())


def test_a_command_with_the_wrong_token_comes_back_refused_and_is_never_run(dirs):
    b = make(dirs)
    with FakePeer(b.dirs["server"], TOKEN, "server") as peer:
        res = b.send("server", {"cmd": "ping", "args": {}}, 5, token=OLD_TOKEN)
    assert res["ok"] is False and res["error"] == "wrong_token" and peer.ran == []


def test_the_peer_never_reruns_a_command_that_already_has_a_result(dirs):
    b = make(dirs)
    folder = b.dirs["server"]
    (folder / "res" / "1.json").write_text(json.dumps({"seq": 1, "ok": True}), encoding="utf-8")
    (folder / "cmd" / "1.json").write_text(json.dumps({"seq": 1, "token": TOKEN, "cmd": "ping", "args": {}}), encoding="utf-8")
    peer = FakePeer(folder, TOKEN, "server")
    peer.step()
    assert peer.ran == [] and not (folder / "cmd" / "1.json").exists() and peer.next == 2


def test_files_of_an_old_token_are_never_read(dirs):
    b = make(dirs)
    old = bridge.session_dir(dirs["server"], OLD_TOKEN)
    bridge.make_dirs(old)
    (old / "res" / "1.json").write_text(json.dumps({"seq": 1, "ok": True, "error": "", "peer": "server",
                                                    "game_time_ms": 0, "data": {}}), encoding="utf-8")
    (old / "hello.json").write_text(json.dumps({"token": OLD_TOKEN}), encoding="utf-8")
    assert b.next_seq("server") == 1 and b.hello("server") is None
    with FakePeer(b.dirs["server"], TOKEN, "server"):
        assert b.call("ping", peer="server")["seq"] == 1


def test_a_peer_that_never_answers_times_out(dirs):
    clock = [0.0]
    b = make(dirs, clock=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s))
    with pytest.raises(bridge.BridgeTimeout, match="did not answer command 1"):
        b.call("ping", peer="client")


def test_a_peer_that_dies_partway_is_reported(dirs):
    alive = {"server": True}
    b = make(dirs, alive=lambda p: alive[p], sleep=lambda s: alive.update(server=False))
    with pytest.raises(bridge.PeerDied, match="server process exited"):
        b.call("player_state")


def test_hellos_must_carry_this_token(dirs):
    b = make(dirs)
    with FakePeer(b.dirs["server"], TOKEN, "server", hello={"player_count": 1}), \
            FakePeer(b.dirs["client"], TOKEN, "client", hello={"player_loaded": True}):
        hellos = b.wait_hellos(["server", "client"], 5, lambda p, h: p == "server" or h.get("player_loaded"))
    assert hellos["client"]["player_loaded"] is True and hellos["server"]["token"] == TOKEN


def test_the_spawn_limit_is_enforced_before_writing(dirs):
    b = make(dirs, spawns=allowlist.MAX_SPAWNS)
    with pytest.raises(allowlist.AllowlistError, match="at most 50 spawns"):
        b.call("spawn", {"cls": "Hatchback_02", "pos": [4200, 0, 10650]})
    assert not list((b.dirs["server"] / "cmd").iterdir())


def test_a_both_peer_command_needs_its_peer_and_a_one_peer_command_refuses_the_other(dirs):
    b = make(dirs)
    with pytest.raises(allowlist.AllowlistError, match="both peers"):
        b.call("ping")
    with pytest.raises(allowlist.AllowlistError, match="runs on the client"):
        b.call("drive", {"throttle": 1.0}, peer="server")


def test_closing_renames_the_token_folder(dirs):
    b = make(dirs)
    done = bridge.close(b.dirs["server"])
    assert done.name == TOKEN + ".done" and done.is_dir() and not b.dirs["server"].exists()


def test_a_failed_command_keeps_only_its_reason(dirs):
    b = make(dirs)
    handlers = {"delete": lambda a: (False, "vehicle_has_crew", {"removed": False}),
                "get_in": lambda a: (False, "not_seated", {"seated": False, "reason": "possible=false"})}
    with FakePeer(b.dirs["server"], TOKEN, "server", handlers), FakePeer(b.dirs["client"], TOKEN, "client", handlers):
        res = b.call("delete", {"net_id": "3,4"})
        res2 = b.call("get_in", {"net_id": "3,4"})
    assert res["ok"] is False and res["error"] == "vehicle_has_crew" and res["data"] == {}
    assert res2["data"] == {"reason": "possible=false"}


def test_bad_tokens_are_refused():
    with pytest.raises(bridge.BridgeError, match="bad token"):
        bridge.session_dir(Path("x"), "../../evil")
    assert bridge.TOKEN_RE.match(bridge.new_token())
