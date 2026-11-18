"""The dayz-testbridge MCP tools against a recorded session and fake peers: no DayZ, no MCP client.

Named test_testbridge_server.py, not test_server.py, so pytest does not confuse it with dayz-rag's.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import allowlist  # noqa: E402
import bridge  # noqa: E402
import server  # noqa: E402
import session  # noqa: E402
from fakepeer import FakePeer  # noqa: E402

TOKEN = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def running(tmp_path, monkeypatch):
    """A recorded session whose two peers are fake and answer at once."""
    monkeypatch.setattr(session.h, "resolve_project_dir", lambda: tmp_path)
    dirs = session.peer_dirs(tmp_path, "chernarus-bridge")
    seated = {"in_vehicle": False}
    server_handlers = {
        "player_state": lambda a: (True, "", {"in_vehicle": seated["in_vehicle"], "seat": 0 if seated["in_vehicle"] else -1}),
        "spawn": lambda a: (True, "", {"net_id": "5,0", "type": a["cls"], "class_name": a["cls"], "pos": a["pos"]}),
    }

    def get_in(a):
        seated["in_vehicle"] = True
        return True, "", {"seated": True, "tries": 1}

    peers = [FakePeer(bridge.session_dir(dirs["server"], TOKEN), TOKEN, "server", server_handlers),
             FakePeer(bridge.session_dir(dirs["client"], TOKEN), TOKEN, "client", {"get_in": get_in})]
    for p in peers:
        p.__enter__()
    state = {"token": TOKEN, "instance": "chernarus-bridge", "pids": {"server": 1, "client": 2},
             "dirs": {k: str(v) for k, v in dirs.items()}, "offsets": {}, "marks": {}, "spawns": 0, "mod_line": ""}
    session.save_state(tmp_path, state)
    rt = session.Runtime(run=None, diag_pids=lambda: [1, 2], install=None, remove=None, kill=None,
                         sleep=lambda s: None)
    yield tmp_path, rt
    for p in peers:
        p.stop()


def test_list_commands_is_the_allowlist():
    out = server.list_commands_impl()
    assert set(out["commands"]) == set(allowlist.COMMANDS)
    assert out["commands"]["drive"]["args"]["seconds"]["max"] == allowlist.MAX_DRIVE_S
    assert out["commands"]["ping"]["peer"] == "both" and out["spawn_limit"] == 50


def test_get_in_waits_for_the_server_to_agree(running):
    _, rt = running
    res = server.command_impl("get_in", {"net_id": "5,0"}, None, rt)
    assert res["ok"] and res["data"]["seated"] and res["server"] == {"agrees": True, "in_vehicle": True, "seat": 0, "error": ""}


def test_spawns_are_counted_in_the_session_record(running):
    project, rt = running
    server.command_impl("spawn", {"cls": "Hatchback_02", "pos": [4200, 0, 10650]}, None, rt)
    assert session.load_state(project)["spawns"] == 1


def test_bad_commands_raise_before_anything_is_written(running):
    project, rt = running
    with pytest.raises(allowlist.AllowlistError):
        server.command_impl("exec", {}, None, rt)
    with pytest.raises(allowlist.AllowlistError):
        server.mark_impl("two words", rt)
    folder = bridge.session_dir(Path(session.load_state(project)["dirs"]["server"]), TOKEN)
    assert not list((folder / "cmd").glob("*.json"))


def test_no_session_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(session.h, "resolve_project_dir", lambda: tmp_path)
    with pytest.raises(RuntimeError, match="session_start first"):
        server.command_impl("player_state", {}, None, session.Runtime(None, lambda: [], None, None, None))


def test_logs_since_checks_its_arguments(running):
    with pytest.raises(ValueError, match="kinds"):
        server.logs_since_impl("", None, ["crash"], None, False)
    with pytest.raises(ValueError, match="peers"):
        server.logs_since_impl("", ["observer"], None, None, False)
    assert server.logs_since_impl("", None, None, None, False)["total"] == 0


def test_screenshot_writes_under_output_and_reports_a_black_frame(running):
    project, _ = running
    shots = []

    def capture(pid, out, crop):
        shots.append((pid, out, crop))
        out.write_bytes(b"png")
        return (640, 360)

    res = server.screenshot_impl("top-down", [0, 0, 640, 360], capture)
    assert res["ok"] and res["width"] == 640 and shots[0][0] == 2 and shots[0][2] == (0, 0, 640, 360)
    assert Path(res["path"]) == project / "output" / "testbridge" / TOKEN / "top-down.png"

    def black(pid, out, crop):
        raise server.window_capture.CaptureError("the capture is all black: the client drew nothing")

    res = server.screenshot_impl("dark", None, black)
    assert res == {"ok": False, "all_black": True, "error": res["error"], "path": None}
    with pytest.raises(ValueError):
        server.screenshot_impl("../escape", None, capture)


def test_the_app_registers_its_tools():
    pytest.importorskip("mcp")
    import anyio

    app = server.build_app()
    tools = anyio.run(app.list_tools)
    assert {t.name for t in tools} == {"list_commands", "session_start", "session_status", "session_stop",
                                       "command", "mark", "logs_since", "screenshot"}
    read_only = {t.name for t in tools if t.annotations and t.annotations.readOnlyHint}
    assert read_only == {"list_commands", "session_status", "logs_since"}
