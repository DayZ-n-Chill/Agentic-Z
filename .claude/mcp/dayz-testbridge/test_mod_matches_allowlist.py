"""The mod's command switch and wire classes agree with allowlist.py and bridge.py.

The case labels are parsed per file: AZB_Protocol.c holds the commands of both
peers, the server files the server's, the client files the client's.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import allowlist  # noqa: E402
import bridge  # noqa: E402

SCRIPTS = HERE.parents[2] / "skills" / "dayz-launch-test" / "assets" / "testbridge-mod" / "src" / "AZ_TestBridge" / "scripts"
FILES = {
    "both": ["3_Game/AZB_Protocol.c"],
    "server": ["4_World/AZB_ServerCommands.c", "5_Mission/AZB_MissionServer.c"],
    "client": ["4_World/AZB_ClientCommands.c", "4_World/AZB_CarDrive.c", "5_Mission/AZB_MissionGameplay.c"],
}
CASE_RE = re.compile(r'case\s+"(\w+)"\s*:')


def text(rel: str) -> str:
    return (SCRIPTS / rel).read_text(encoding="utf-8")


def cases(group: str) -> set[str]:
    return {c for rel in FILES[group] for c in CASE_RE.findall(text(rel))}


def fields(cls: str) -> set[str]:
    src = "\n".join(text(rel) for group in FILES.values() for rel in group)
    m = re.search(rf"\bclass\s+{cls}\b[^{{]*\{{(.*?)\n\}}", src, re.S)
    assert m, f"no class {cls}"
    body = re.sub(r"\n\tvoid \w+\(\)\n\t\{.*?\n\t\}", "", m.group(1), flags=re.S)  # drop the constructor
    return set(re.findall(r"^\t(?:ref\s+)?[\w<>, ]+?\s+(\w+);", body, re.M))


def test_all_six_script_files_exist_and_no_other():
    found = {p.relative_to(SCRIPTS).as_posix() for p in SCRIPTS.rglob("*.c")}
    assert found == {rel for group in FILES.values() for rel in group}


def test_each_peer_handles_exactly_its_allowlisted_commands():
    by_peer = {
        "both": {n for n, c in allowlist.COMMANDS.items() if c.peer == allowlist.BOTH},
        "server": {n for n, c in allowlist.COMMANDS.items() if c.peer in (allowlist.SERVER, allowlist.BOTH)},
        "client": {n for n, c in allowlist.COMMANDS.items() if c.peer in (allowlist.CLIENT, allowlist.BOTH)},
    }
    assert cases("both") <= by_peer["both"]  # ping and mark; vehicle_state is written once per peer
    assert cases("server") | cases("both") == by_peer["server"]
    assert cases("client") | cases("both") == by_peer["client"]


def test_args_class_is_the_wire_object_the_host_writes():
    assert fields("AZB_Args") == set(allowlist.WIRE_DEFAULTS)
    assert fields("AZB_Command") == {"seq", "token", "cmd", "args"}


def test_result_and_data_classes_hold_every_declared_output():
    assert fields("AZB_Result") == bridge.RESULT_KEYS
    outputs = {o for c in allowlist.COMMANDS.values() for o in c.outputs}
    assert outputs <= fields("AZB_Data"), sorted(outputs - fields("AZB_Data"))
    unused = fields("AZB_Data") - outputs
    assert unused == set(), f"AZB_Data fields no command declares as output: {sorted(unused)}"


def test_hello_has_what_the_session_waits_for():
    assert {"peer", "token", "player_loaded", "player_count"} <= fields("AZB_Hello")


def test_unknown_commands_and_bad_files_are_refused_by_name():
    protocol = text("3_Game/AZB_Protocol.c")
    for code in ("unknown_command", "bad_json", "seq_mismatch", "wrong_token"):
        assert f'"{code}"' in protocol, code
    assert "FindFile" not in "".join(text(rel) for group in FILES.values() for rel in group)
