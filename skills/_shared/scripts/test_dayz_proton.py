"""dayz-proton.sh without Steam or Proton: what a runner can check.

Everything that starts a tool needs a Steam install and is measured by hand; see
skills/_shared/linux-proton.md. POSIX only: the script is the Linux route.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "dayz-proton.sh"

pytestmark = pytest.mark.skipif(os.name == "nt", reason="the Linux runner script")

requires_real_sway = pytest.mark.skipif(
    platform.machine() not in ("x86_64", "AMD64"),
    reason="needs the x86_64 ELF fake sway; a script sway is not accepted as sway",
)


def run(
    tmp_path: Path,
    *args: str,
    steam: bool = True,
    bin_dir: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    path = os.environ["PATH"] if bin_dir is None else f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
    env = {"PATH": path, "HOME": str(home)}
    if steam:
        (tmp_path / "steam" / "steamapps").mkdir(parents=True, exist_ok=True)
        env["STEAM_ROOT"] = str(tmp_path / "steam")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["sh", str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=60, check=False
    )


def test_the_script_parses() -> None:
    subprocess.run(["sh", "-n", str(SCRIPT)], check=True)


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck is not installed")
def test_shellcheck_finds_no_warnings() -> None:
    done = subprocess.run(
        ["shellcheck", "-S", "warning", str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stdout


def test_no_steam_install_is_named_not_guessed(tmp_path: Path) -> None:
    done = run(tmp_path, "doctor", steam=False)
    assert done.returncode != 0
    assert "no Steam install found" in done.stderr


def test_no_arguments_print_the_usage_and_fail(tmp_path: Path) -> None:
    done = run(tmp_path)
    assert done.returncode == 2
    assert "dayz-proton.sh doctor" in done.stderr


def test_winpath_maps_a_linux_path_to_z(tmp_path: Path) -> None:
    done = run(tmp_path, "winpath", "/var/lib/mods/@Mod")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "Z:\\var\\lib\\mods\\@Mod"


def test_doctor_names_a_missing_proton_and_changes_nothing(tmp_path: Path) -> None:
    done = run(tmp_path, "doctor")
    assert "no Proton found" in done.stdout + done.stderr
    assert not list((tmp_path / "home").rglob("dayz-proton"))


def fake_dayzmake(tmp_path: Path, help_text: str, version: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    tool = bin_dir / "dayzmake"
    tool.write_text(
        "#!/bin/sh\n"
        f'case "$1" in --version) echo "dayzmake {version}" ;; *) echo "{help_text}" ;; esac\n'
    )
    tool.chmod(0o755)
    return bin_dir


@pytest.mark.parametrize(
    ("help_text", "version", "expected"),
    [
        ("build [--proton-binarize]", "v2.0.0", "dayzmake v2.0.0 (ok)"),
        (
            "build [--proton-binarize]",
            "v1.0.0",
            "dayzmake v1.0.0 (ok for building; upgrade to >= v2.0.0 before unpacking PBOs you did not build)",
        ),
        ("build [--proton-binarize]", "v0.3.0", "from before the rename (v0.3.0)"),
        ("build", "v0.3.0", "armake2, whose V3 file hash omits *.c"),
    ],
)
def test_doctor_tells_dayzmake_from_plain_armake2_and_old_builds(
    tmp_path: Path, help_text: str, version: str, expected: str
) -> None:
    done = run(tmp_path, "doctor", bin_dir=fake_dayzmake(tmp_path, help_text, version))
    assert expected in done.stdout


# --- fakes for binarize / tool / headless / init -----------------------------

def _write(path: Path, text: str, exe: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if exe:
        path.chmod(0o755)
    return path


def fake_proton(tmp_path: Path, spawn_wineserver_from: Path | None = None) -> tuple[Path, Path, Path]:
    """A `proton` that records its argv and any .bat it is handed, and fakes
    the prefix layout. Returns (proton_dir, calls_file, bats_file)."""
    proton_dir = tmp_path / "proton-tool"
    calls = tmp_path / "proton-calls.txt"
    bats = tmp_path / "proton-bats.txt"
    lines = [
        "#!/bin/sh",
        f"printf 'CALL\\n' >> '{calls}'",
        f"for a in \"$@\"; do printf 'ARG %s\\n' \"$a\" >> '{calls}'; done",
        'if [ -n "${STEAM_COMPAT_DATA_PATH:-}" ]; then mkdir -p "$STEAM_COMPAT_DATA_PATH/pfx/dosdevices"; fi',
        "for a in \"$@\"; do case $a in *.bat)",
        "  _p=$(printf '%s' \"$a\" | sed 's/^Z://; s/\\\\/\\//g')",
        f"  [ -f \"$_p\" ] && {{ printf 'BAT %s\\n' \"$_p\" >> '{bats}'; cat \"$_p\" >> '{bats}'; }} ;;",
        "esac; done",
        'if [ -f "${DAYZ_PROTON_HOME:-}/binarize/run.bat" ]; then',
        f"  printf 'BAT run.bat\\n' >> '{bats}'; cat \"$DAYZ_PROTON_HOME/binarize/run.bat\" >> '{bats}'",
        '  mkdir -p "$DAYZ_PROTON_HOME/binarize/out"; printf \'done\\n\' > "$DAYZ_PROTON_HOME/binarize/out/binarize.log"',
        "fi",
    ]
    if spawn_wineserver_from is not None:
        new_pid = tmp_path / "spawned-wineserver.pid"
        # Spawn via a foreground python3 helper, not shell `&`: a
        # non-interactive sh starts async commands with SIGINT/SIGQUIT
        # ignored and ignored dispositions survive exec, so the child
        # would shrug off the script's kill -INT. The helper runs in the
        # foreground (SIGINT caught/default), and exec resets a caught
        # SIGINT to the default in the wineserver child.
        lines += [
            'for a in "$@"; do if [ "$a" = regedit ]; then',
            f"  WINEPREFIX=\"$STEAM_COMPAT_DATA_PATH/pfx\" WAYLAND_DISPLAY=wayland-test "
            f"python3 -c 'import subprocess,sys; p=subprocess.Popen([sys.argv[1]]); print(p.pid)' "
            f"'{spawn_wineserver_from}' > '{new_pid}'",
            "fi; done",
        ]
    lines += ["exit 0", ""]
    _write(proton_dir / "proton", "\n".join(lines), exe=True)
    return proton_dir, calls, bats


def fake_steam_with_tools(tmp_path: Path) -> Path:
    steam = tmp_path / "steam"
    tools = steam / "steamapps" / "common" / "DayZ Tools"
    _write(
        steam / "steamapps" / "appmanifest_830640.acf",
        '"AppState"\n{\n"appid" "830640"\n"name" "DayZ Tools"\n'
        '"installdir" "DayZ Tools"\n"StateFlags" "4"\n"buildid" "1"\n}\n',
    )
    _write(tools / "installscript.vdf", '"InstallScript"\n{\n}\n')
    _write(tools / "Bin" / "Binarize" / "binarize.exe", "fake\n")
    _write(tools / "Bin" / "DsUtils" / "DSSignFile.exe", "fake\n")
    return steam


def parse_calls(calls: Path) -> list[list[str]]:
    if not calls.exists():
        return []
    out: list[list[str]] = []
    current: list[str] | None = None
    for line in calls.read_text().splitlines():
        if line == "CALL":
            current = []
            out.append(current)
        elif line.startswith("ARG ") and current is not None:
            current.append(line[4:])
    return out


def expected_bat_quote(value: str) -> str:
    pct = value.replace("%", "%%")
    cut = len(pct)
    while cut > 0 and pct[cut - 1] == "\\":
        cut -= 1
    trail = pct[cut:]
    return '"' + pct[:cut] + trail + trail + '"'


def binarize_setup(tmp_path: Path) -> dict[str, object]:
    fake_steam_with_tools(tmp_path)
    proton_dir, calls, bats = fake_proton(tmp_path)
    proot = tmp_path / "P"
    (proot / "MyMod").mkdir(parents=True)
    dzhome = tmp_path / "dzhome"
    env = {"PROTON": str(proton_dir), "DAYZ_PROTON_HOME": str(dzhome)}
    return {"proot": proot, "dzhome": dzhome, "env": env, "calls": calls, "bats": bats}


# --- binarize batch serialization --------------------------------------------
# These prove how the .bat is serialized, not how cmd.exe / binarize.exe
# parse it.

SPECIAL_ARGS = [
    "my cube.p3d",
    "cube.p3d & del P:\\MyMod\\important.txt & rem .p3d",
    "a&b.p3d",
    "a|b.p3d",
    "a^b.p3d",
    "a(b).p3d",
    "a;b.p3d",
    "a,b.p3d",
    "a!X!b.p3d",
    "%PATH%",
    "%1",
    "%%",
    "100%.p3d",
    "dir\\",
    "dir\\\\",
]


def test_binarize_bat_quotes_every_user_argument(tmp_path: Path) -> None:
    s = binarize_setup(tmp_path)
    done = run(
        tmp_path, "binarize", str(s["proot"]), "MyMod", str(tmp_path / "out"),
        *SPECIAL_ARGS, extra_env=s["env"],  # type: ignore[arg-type]
    )
    assert done.returncode == 0, done.stderr
    calls = parse_calls(s["calls"])  # type: ignore[arg-type]
    bat_calls = [c for c in calls if "Z:\\run.bat" in c]
    assert bat_calls, calls
    # The cmd.exe /c argument is a single .bat path and carries no user text.
    assert bat_calls[-1] == ["run", "cmd.exe", "/c", "Z:\\run.bat"]
    for call in calls:
        for arg in SPECIAL_ARGS:
            assert arg not in call
    bat = (s["dzhome"] / "binarize" / "run.bat").read_text()  # type: ignore[operator]
    lines = bat.splitlines()
    assert lines[0] == "@echo off"
    assert lines[1] == "setlocal DisableDelayedExpansion"
    assert expected_bat_quote("P:\\MyMod") in bat
    for arg in SPECIAL_ARGS:
        assert expected_bat_quote(arg) in bat, arg
    # Outside the quoted spans the user's metacharacters do not appear: strip
    # every "..." span and check the injection text is gone with it.
    stripped = re.sub(r'"[^"]*"', '""', bat)
    assert "del P:" not in stripped
    assert "a&b" not in stripped and "a|b" not in stripped


def test_binarize_with_no_file_arguments_is_valid(tmp_path: Path) -> None:
    s = binarize_setup(tmp_path)
    done = run(
        tmp_path, "binarize", str(s["proot"]), "MyMod/", str(tmp_path / "out"),
        extra_env=s["env"],  # type: ignore[arg-type]
    )
    assert done.returncode == 0, done.stderr
    bat = (s["dzhome"] / "binarize" / "run.bat").read_text()  # type: ignore[operator]
    # Trailing / stripped: P:\MyMod, not P:\MyMod\ before the closing quote.
    assert '"P:\\MyMod" "Z:\\out"' in bat


@pytest.mark.parametrize("bad", ['a"b.p3d', "a\nb.p3d", "a\rb.p3d", "a\n", ""])
def test_binarize_refuses_bad_arguments_before_any_side_effect(tmp_path: Path, bad: str) -> None:
    s = binarize_setup(tmp_path)
    marker = s["dzhome"] / "binarize" / "out" / "marker.txt"  # type: ignore[operator]
    marker.parent.mkdir(parents=True)
    marker.write_text("keep\n")
    done = run(
        tmp_path, "binarize", str(s["proot"]), "MyMod", str(tmp_path / "out"),
        bad, extra_env=s["env"],  # type: ignore[arg-type]
    )
    assert done.returncode != 0
    assert not (s["calls"]).exists()  # type: ignore[union-attr]
    assert not (s["dzhome"] / "binarize" / "run.bat").exists()  # type: ignore[operator]
    assert marker.read_text() == "keep\n"


def test_binarize_refuses_a_bad_addon_before_any_side_effect(tmp_path: Path) -> None:
    s = binarize_setup(tmp_path)
    done = run(
        tmp_path, "binarize", str(s["proot"]), 'Bad"Mod', str(tmp_path / "out"),
        "cube.p3d", extra_env=s["env"],  # type: ignore[arg-type]
    )
    assert done.returncode != 0
    assert "double quote" in done.stderr
    assert not (s["calls"]).exists()  # type: ignore[union-attr]


def test_run_tool_bat_quoting_is_unchanged(tmp_path: Path) -> None:
    fake_steam_with_tools(tmp_path)
    proton_dir, _calls, bats = fake_proton(tmp_path)
    dzhome = tmp_path / "dzhome"
    (dzhome / "tools" / "pfx" / "dosdevices").mkdir(parents=True)
    done = run(
        tmp_path, "tool", "DSSignFile", "a & b.pbo", "100%.pbo", "sp ace.pbo",
        extra_env={"PROTON": str(proton_dir), "DAYZ_PROTON_HOME": str(dzhome)},
    )
    assert done.returncode == 0, done.stderr
    bat = bats.read_text()
    lines = bat.splitlines()
    assert lines[1] == "@echo off"
    assert lines[2] == "setlocal DisableDelayedExpansion"
    assert 'DSSignFile.exe"' in lines[3]
    assert '"a & b.pbo"' in bat
    assert '"100%%.pbo"' in bat
    assert '"sp ace.pbo"' in bat


def test_run_tool_bat_quotes_every_user_argument(tmp_path: Path) -> None:
    fake_steam_with_tools(tmp_path)
    proton_dir, calls_path, bats = fake_proton(tmp_path)
    dzhome = tmp_path / "dzhome"
    (dzhome / "tools" / "pfx" / "dosdevices").mkdir(parents=True)
    tool_args = ["C:\\dir with space\\", "%PATH%", "!x!", *SPECIAL_ARGS]
    done = run(
        tmp_path, "tool", "DSSignFile", *tool_args,
        extra_env={"PROTON": str(proton_dir), "DAYZ_PROTON_HOME": str(dzhome)},
    )
    assert done.returncode == 0, done.stderr
    calls = parse_calls(calls_path)
    assert calls, calls_path
    for call in calls:
        for arg in tool_args:
            assert arg not in call
    bat = bats.read_text()
    lines = bat.splitlines()
    assert lines[1] == "@echo off"
    assert lines[2] == "setlocal DisableDelayedExpansion"
    assert lines[3].startswith('"Z:\\') and 'DSSignFile.exe" ' in lines[3]
    assert '"C:\\dir with space\\\\"' in bat
    assert '"%%PATH%%"' in bat
    assert '"!x!"' in bat
    for arg in SPECIAL_ARGS:
        assert expected_bat_quote(arg) in bat, arg
    stripped = re.sub(r'"[^"]*"', '""', "\n".join(lines[1:]))
    assert "del P:" not in stripped
    assert "a&b" not in stripped and "a|b" not in stripped


@pytest.mark.parametrize("bad", ['a"&calc&"', 'a"b.pbo', "a\nb.pbo", "a\rb.pbo", "a\n", ""])
def test_run_tool_refuses_bad_arguments_before_any_side_effect(tmp_path: Path, bad: str) -> None:
    fake_steam_with_tools(tmp_path)
    proton_dir, calls_path, bats = fake_proton(tmp_path)
    dzhome = tmp_path / "dzhome"
    tmpdir = tmp_path / "tmp"
    tmpdir.mkdir()
    done = run(
        tmp_path, "tool", "DSSignFile", bad,
        extra_env={
            "PROTON": str(proton_dir),
            "DAYZ_PROTON_HOME": str(dzhome),
            "TMPDIR": str(tmpdir),
        },
    )
    assert done.returncode != 0
    assert "tool DSSignFile:" in done.stderr
    assert "binarize:" not in done.stderr
    assert not calls_path.exists()
    assert not bats.exists()
    assert not dzhome.exists()
    assert list(tmpdir.iterdir()) == []


# --- headless identity and wineserver stops ----------------------------------

def _fake_pause_binary(path: Path) -> None:
    """A tiny x86_64 ELF that pauses forever, ignoring argv; its comm is
    the file name it is written under (sway, wineserver). Never copy a
    system binary for this: a copied multi-call binary (uutils sleep on
    newer runners) exits at once under another name. Only built on x86_64;
    tests using it are skipped elsewhere (requires_real_sway)."""
    import struct

    assert platform.machine() in ("x86_64", "AMD64")
    path.parent.mkdir(parents=True, exist_ok=True)
    code = bytes.fromhex("b8220000000f05ebf7")  # pause(); jmp back
    total = 64 + 56 + len(code)
    elf = struct.pack(
        "<16sHHIQQQIHHHHHH",
        b"\x7fELF\x02\x01\x01" + b"\x00" * 9, 2, 62, 1, 0x400078, 64, 0, 0, 64, 56, 1, 0, 0, 0,
    ) + struct.pack("<IIQQQQQQ", 1, 5, 0, 0x400000, 0x400000, total, total, 0x1000) + code
    path.write_bytes(elf)
    path.chmod(0o755)


def _fake_sway_binary(path: Path) -> None:
    """The pause ELF named sway (comm is sway and argv is exactly what the
    launcher passed; a #! script would run as the interpreter instead and
    is not accepted as sway)."""
    _fake_pause_binary(path)


def fake_sway(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    _fake_sway_binary(bin_dir / "sway")
    return bin_dir


def pid_gone(pid: int) -> bool:
    stat = Path(f"/proc/{pid}/stat")
    if not stat.exists():
        return True
    try:
        return stat.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    except (OSError, IndexError):
        return True


def wait_gone(pid: int, seconds: float = 5.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if pid_gone(pid):
            return True
        time.sleep(0.05)
    return pid_gone(pid)


def wait_for_pid_file(path: Path, seconds: float = 10.0) -> int:
    """The pid recorded in a file another process writes, waiting (bounded)
    until the file exists and holds a complete pid instead of reading it
    once; -1 when no pid appears within the bound. A file can be visible
    before its writer's printf lands, so an unparsable read also retries."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            text = path.read_text().strip()
        except OSError:
            text = ""
        if text:
            try:
                return int(text)
            except ValueError:
                pass
        time.sleep(0.01)
    return -1


def state_sway_pids(state: Path) -> list[int]:
    """Live pids whose argv is exactly sway -c <state>/sway.conf, found by
    scanning /proc for this state's unique conf path (not by sway.pid, so a
    sway whose tracking was removed is still found)."""
    conf = str(state / "sway.conf")
    found: list[int] = []
    proc = Path("/proc")
    if not proc.exists():
        return found
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        argv = [a.decode(errors="surrogateescape") for a in argv if a]
        if len(argv) == 3 and argv[0].rsplit("/", 1)[-1] == "sway" and argv[1] == "-c" and argv[2] == conf:
            found.append(int(entry.name))
    return found


def state_launcher_pids(state: Path) -> list[int]:
    """Live pids that look like this state's launcher (argv holds the
    launcher `exec sway` form with the state as an entry) or its sway."""
    conf = str(state / "sway.conf")
    found: list[int] = []
    proc = Path("/proc")
    if not proc.exists():
        return found
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        argv = [a.decode(errors="surrogateescape") for a in argv if a]
        if any(conf in a for a in argv) or (
            any("exec sway" in a for a in argv) and str(state) in argv
        ):
            found.append(int(entry.name))
    return found


def wait_no_state_sway(state: Path, seconds: float = 3.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if not state_sway_pids(state):
            return True
        time.sleep(0.05)
    return not state_sway_pids(state)


def kill_state_sways(state: Path) -> None:
    """Last-resort cleanup: kill every sway of this state found via /proc,
    plus whatever pid sway.pid names, even if no test captured a pid."""
    pids = set(state_sway_pids(state))
    pid_file = state / "sway.pid"
    if pid_file.exists():
        try:
            pids.add(int(pid_file.read_text().strip()))
        except ValueError:
            pass
    for pid in pids:
        kill_process_tree(pid)


def kill_process_tree(pid: int) -> None:
    """Kill a process and every descendant (via pgrep -P), leaves first."""
    if pid <= 0:
        return
    children: list[int] = []
    try:
        out = subprocess.run(
            ["pgrep", "-P", str(pid)], capture_output=True, text=True, check=False
        )
        children = [int(x) for x in out.stdout.split()]
    except (OSError, ValueError):
        children = []
    for child in children:
        kill_process_tree(child)
    if not pid_gone(pid):
        try:
            os.kill(pid, 9)
        except OSError:
            pass
    wait_gone(pid, 2.0)


def kill_popen(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None:
        return
    kill_process_tree(proc.pid)
    try:
        proc.wait(timeout=5)
    except Exception:
        pass


def start_fake_wineserver(tmp_path: Path, name: str, wineprefix: Path, display: str) -> subprocess.Popen[bytes]:
    exe_dir = tmp_path / name
    exe_dir.mkdir(parents=True, exist_ok=True)
    exe = exe_dir / "wineserver"
    _fake_pause_binary(exe)
    env = {"PATH": os.environ["PATH"], "WINEPREFIX": str(wineprefix), "WAYLAND_DISPLAY": display}
    return subprocess.Popen([str(exe)], env=env)


def headless_start(
    tmp_path: Path, state: Path, bin_dir: Path, dzhome: Path,
    tool: str = "ObjectBuilder", extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {"DAYZ_PROTON_HOME": str(dzhome)}
    if extra_env:
        env.update(extra_env)
    return run(
        tmp_path, "headless", "start", str(state), tool,
        bin_dir=bin_dir, extra_env=env,
    )


def popen_headless_start(
    tmp_path: Path, state: Path, bin_dir: Path, dzhome: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.Popen[str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    (tmp_path / "steam" / "steamapps").mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(home),
        "STEAM_ROOT": str(tmp_path / "steam"),
        "DAYZ_PROTON_HOME": str(dzhome),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.Popen(
        ["sh", str(SCRIPT), "headless", "start", str(state), "ObjectBuilder"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


@requires_real_sway
def test_headless_start_then_stop_signals_our_sway(tmp_path: Path) -> None:
    bin_dir = fake_sway(tmp_path)
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    pid = -1
    try:
        done = headless_start(tmp_path, state, bin_dir, dzhome)
        assert done.returncode == 0, done.stderr
        pid = int((state / "sway.pid").read_text().strip())
        assert not pid_gone(pid)
        assert (state / "sway.identity").exists()
        identity = (state / "sway.identity").read_text().splitlines()
        assert identity[-2] == "-c" and identity[-1].endswith("/sway.conf")
        done = run(
            tmp_path, "headless", "stop", str(state),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr
        assert wait_gone(pid), "our sway was not signalled"
        assert not (state / "sway.pid").exists()
    finally:
        kill_process_tree(pid)


def test_headless_stop_does_not_kill_an_unrelated_live_process(tmp_path: Path) -> None:
    sleeper = subprocess.Popen(["sleep", "30"])
    try:
        state = tmp_path / "state"
        state.mkdir()
        (state / "sway.pid").write_text(f"{sleeper.pid}\n")
        done = run(
            tmp_path, "headless", "stop", str(state),
            extra_env={"DAYZ_PROTON_HOME": str(tmp_path / "dzhome")},
        )
        assert done.returncode == 0, done.stderr
        assert sleeper.poll() is None, "unrelated process was killed"
        assert "not verified" in done.stderr
        assert not (state / "sway.pid").exists()
    finally:
        kill_popen(sleeper)  # type: ignore[arg-type]


@pytest.mark.parametrize("tamper", ["starttime", "conf"])
@requires_real_sway
def test_headless_stop_rejects_a_tampered_identity(tmp_path: Path, tamper: str) -> None:
    bin_dir = fake_sway(tmp_path)
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    pid = -1
    try:
        done = headless_start(tmp_path, state, bin_dir, dzhome)
        assert done.returncode == 0, done.stderr
        pid = int((state / "sway.pid").read_text().strip())
        lines = (state / "sway.identity").read_text().splitlines()
        if tamper == "starttime":
            lines[0] = "1"
        else:
            lines[-1] = "/somewhere/else/sway.conf"
        (state / "sway.identity").write_text("\n".join(lines) + "\n")
        done = run(
            tmp_path, "headless", "stop", str(state),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr
        assert not pid_gone(pid), f"sway with a tampered {tamper} was signalled"
    finally:
        kill_process_tree(pid)


@requires_real_sway
def test_headless_stop_signals_only_the_sessions_wineserver(tmp_path: Path) -> None:
    bin_dir = fake_sway(tmp_path)
    dzhome = tmp_path / "dzhome"
    for display, should_die in [("wayland-2", False), ("wayland-1", True)]:
        state = tmp_path / f"state-{display}"
        server: subprocess.Popen[bytes] | None = None
        pid = -1
        try:
            done = headless_start(tmp_path, state, bin_dir, dzhome)
            assert done.returncode == 0, done.stderr
            pid = int((state / "sway.pid").read_text().strip())
            server = start_fake_wineserver(tmp_path, f"ws-{display}", dzhome / "tools" / "pfx", display)
            (state / "wayland-display").write_text("wayland-1\n")
            done = run(
                tmp_path, "headless", "stop", str(state),
                bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
            )
            assert done.returncode == 0, done.stderr
            assert wait_gone(pid)
            assert server is not None
            if should_die:
                assert server.wait(timeout=5) is not None
            else:
                assert server.poll() is None, "wineserver of another display was signalled"
        finally:
            kill_process_tree(pid)
            kill_popen(server)


@requires_real_sway
def test_headless_stop_with_dead_sway_leaves_the_wineserver_alone(tmp_path: Path) -> None:
    bin_dir = fake_sway(tmp_path)
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    server: subprocess.Popen[bytes] | None = None
    pid = -1
    try:
        done = headless_start(tmp_path, state, bin_dir, dzhome)
        assert done.returncode == 0, done.stderr
        pid = int((state / "sway.pid").read_text().strip())
        server = start_fake_wineserver(tmp_path, "ws-dead", dzhome / "tools" / "pfx", "wayland-1")
        (state / "wayland-display").write_text("wayland-1\n")
        # Kill the real fake sway from the test; stop must then leave the
        # same-display wineserver alone and say so.
        kill_process_tree(pid)
        assert wait_gone(pid)
        done = run(
            tmp_path, "headless", "stop", str(state),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr
        assert "leaving its wineserver alone" in done.stderr
        assert server.poll() is None
    finally:
        kill_process_tree(pid)
        kill_popen(server)


@requires_real_sway
def test_headless_stop_with_empty_display_leaves_other_display_wineserver(tmp_path: Path) -> None:
    bin_dir = fake_sway(tmp_path)
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    server: subprocess.Popen[bytes] | None = None
    pid = -1
    try:
        done = headless_start(tmp_path, state, bin_dir, dzhome)
        assert done.returncode == 0, done.stderr
        pid = int((state / "sway.pid").read_text().strip())
        server = start_fake_wineserver(tmp_path, "ws-empty", dzhome / "tools" / "pfx", "wayland-2")
        # Only a newline: bytes on disk, but an empty recorded display.
        (state / "wayland-display").write_text("\n")
        done = run(
            tmp_path, "headless", "stop", str(state),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr
        assert wait_gone(pid), "our sway was not signalled"
        assert "leaving the wineserver alone" in done.stderr
        assert server.poll() is None, "wineserver on another display was signalled on an empty display"
    finally:
        kill_process_tree(pid)
        kill_popen(server)


@requires_real_sway
def test_headless_second_start_is_refused_and_first_stays_stoppable(tmp_path: Path) -> None:
    bin_dir = fake_sway(tmp_path)
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    pid = -1
    try:
        done = headless_start(tmp_path, state, bin_dir, dzhome, tool="ObjectBuilder")
        assert done.returncode == 0, done.stderr
        pid = int((state / "sway.pid").read_text().strip())
        done = headless_start(tmp_path, state, bin_dir, dzhome, tool="DayZDiag")
        assert done.returncode != 0
        assert "still has a running sway or launcher" in done.stderr
        assert not pid_gone(pid), "first sway died on the refused second start"
        assert int((state / "sway.pid").read_text().strip()) == pid
        done = run(
            tmp_path, "headless", "stop", str(state),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr
        assert wait_gone(pid), "first sway was not stoppable after the refused start"
    finally:
        kill_process_tree(pid)


def test_headless_start_fails_when_sway_never_appears(tmp_path: Path) -> None:
    bin_dir = tmp_path / "fakebin"
    record = tmp_path / "never-sway.pid"
    _write(
        bin_dir / "sway",
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$$\" > '{record}'\n"
        "exec sleep 30\n",
        exe=True,
    )
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    recorded = -1
    try:
        done = headless_start(
            tmp_path, state, bin_dir, dzhome,
            extra_env={"DAYZ_PROTON_START_WAIT_TENTHS": "5"},
        )
        assert done.returncode != 0
        assert "sway did not start" in done.stderr
        assert not (state / "sway.identity").exists(), "an identity was published for the launcher"
        assert not (state / "sway.pid").exists()
        if record.exists():
            recorded = int(record.read_text().strip())
    finally:
        if record.exists():
            try:
                recorded = int(record.read_text().strip())
            except ValueError:
                recorded = -1
        kill_process_tree(recorded)
        # The sway.pid was removed by the failed start; also clean any pid
        # the failed run left in the state dir before finally ran.
        pid_file = state / "sway.pid"
        if pid_file.exists():
            try:
                kill_process_tree(int(pid_file.read_text().strip()))
            except ValueError:
                pass


@pytest.mark.parametrize(
    ("wait_tenths", "delay"),
    [("0", "0.2"), ("1", "0.2"), ("0", "1.5")],
)
@requires_real_sway
def test_headless_start_with_slow_launcher_and_tiny_wait_leaves_no_sway(
    tmp_path: Path, wait_tenths: str, delay: str
) -> None:
    # A setsid shim that sleeps `delay` seconds before exec'ing the real
    # setsid makes the launcher child slower than the parent's wait (0, and
    # 0.1s). The failed start must not leave a sway it cannot stop: it
    # cancels first, so the child never execs sway. On the old code the
    # parent removed its tracking before the child wrote sway.pid and that
    # sway lived on. The 0.2s cases sit inside failed_start_cleanup's
    # bounded 0.5s re-check window (5 x 0.1s in dayz-proton.sh), so the
    # parent's late-pid signal could still catch a child that ignored the
    # cancel. The 1.5s case is slower than that window: the parent has
    # removed sway.pid/sway.identity long before the child would write its
    # pid, so only the child's own sway.cancel checks (in the launcher
    # `sh -c`) can prevent the sway from starting. Removing those checks
    # must make the 1.5s case fail.
    bin_dir = fake_sway(tmp_path)
    real_setsid = shutil.which("setsid")
    assert real_setsid is not None
    record = tmp_path / "setsid-shim.pid"
    _write(
        bin_dir / "setsid",
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$$\" > '{record}'\n"
        f"sleep {delay}\n"
        f"exec '{real_setsid}' \"$@\"\n",
        exe=True,
    )
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    shim_pid = -1
    try:
        done = headless_start(
            tmp_path, state, bin_dir, dzhome,
            extra_env={"DAYZ_PROTON_START_WAIT_TENTHS": wait_tenths},
        )
        assert done.returncode != 0
        assert "sway did not start" in done.stderr
        # The shim is a child process: under load it may not have written
        # its pid record yet when the failed start returns, so wait
        # (bounded) for the record instead of reading it once. Waiting for
        # it also makes the poll below non-vacuous: the shim has actually
        # started before we poll for it to settle (its sleep, its exec of
        # the real setsid, and the launcher's cancel check).
        # Both bounded waits are comfortably longer than the largest shim
        # delay (delay + 5s; 6.5s for the 1.5s case), so a sway that only
        # appears after the delay cannot slip past them as "not there yet".
        settle = float(delay) + 5.0
        shim_pid = wait_for_pid_file(record, seconds=settle)
        assert shim_pid > 0, "the setsid shim never wrote its pid record"
        # Observe the whole settle window, not just its first instant:
        # wait_no_state_sway alone returns at the first empty scan, which
        # for a still-sleeping shim is before any sway could appear and
        # would pass vacuously even without the child's cancel check. Poll
        # for the full window (the shim's sleep, its exec of the real
        # setsid, and the launcher's cancel check all fall inside it) and
        # fail if a sway of this state appears at any point; only then is
        # the final empty check meaningful.
        deadline = time.time() + settle
        while time.time() < deadline:
            assert not state_sway_pids(state), (
                f"failed start (wait {wait_tenths}, delay {delay}) "
                "left a running sway of this state"
            )
            time.sleep(0.05)
        # Bounded poll for the child to settle, then no sway of this state
        # may exist (a `headless stop` could not end an untracked one).
        assert wait_no_state_sway(state, seconds=settle), (
            f"failed start (wait {wait_tenths}, delay {delay}) "
            "left a running sway of this state"
        )
        assert not (state / "sway.pid").exists()
        assert not (state / "sway.identity").exists()
    finally:
        kill_process_tree(shim_pid)
        kill_state_sways(state)


@pytest.mark.parametrize("dirname", ["state\nwith-newline", r"a\tb", "state with space"])
def test_headless_start_refuses_a_disallowed_state_path(tmp_path: Path, dirname: str) -> None:
    # A newline, a backslash or a space in the state path is refused before
    # any side effect: the directory is not created and no file is written.
    # The parent directory already exists (it is tmp_path itself).
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir(exist_ok=True)
    dzhome = tmp_path / "dzhome"
    state = tmp_path / dirname
    done = headless_start(tmp_path, state, bin_dir, dzhome)
    assert done.returncode != 0
    assert "may only contain" in done.stderr
    assert not state.exists(), "a refused state path created its directory"
    assert not list(tmp_path.glob("state*")) or dirname.startswith("a"), (
        "a refused state path wrote a file"
    )


@requires_real_sway
def test_headless_start_stop_with_dotted_dashed_state_path(tmp_path: Path) -> None:
    # An allowed name with . and - still starts and stops; the conf path
    # reaches awk through ENVIRON (passing it with awk -v would let escape
    # handling mis-compare some state paths).
    bin_dir = fake_sway(tmp_path)
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state.v1-test"
    pid = -1
    try:
        done = headless_start(tmp_path, state, bin_dir, dzhome)
        assert done.returncode == 0, done.stderr
        pid = wait_for_pid_file(state / "sway.pid")
        assert pid > 0, "the launcher child never wrote sway.pid"
        assert not pid_gone(pid)
        assert (state / "sway.identity").exists()
        done = run(
            tmp_path, "headless", "stop", str(state),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr
        assert wait_gone(pid), "stop did not signal the sway of a dotted/dashed state path"
        assert not (state / "sway.pid").exists()
    finally:
        kill_process_tree(pid)
        kill_state_sways(state)


@requires_real_sway
def test_headless_retry_is_refused_while_first_launcher_is_pending(tmp_path: Path) -> None:
    # A setsid shim waits for a release file instead of exec'ing the real
    # setsid, so launcher A stays pending with no timing luck. The first
    # start (wait 0) fails; a retry must be refused with the state
    # untouched while A is still pending; after release A sees sway.cancel
    # and leaves no untracked sway; then a fresh start succeeds and stop
    # ends it, and no process of the state is alive at the end.
    bin_dir = fake_sway(tmp_path)
    real_setsid = shutil.which("setsid")
    assert real_setsid is not None
    release = tmp_path / "release-a"
    record = tmp_path / "setsid-shim.pid"
    _write(
        bin_dir / "setsid",
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$$\" > '{record}'\n"
        "_n=0\n"
        f"while [ ! -e '{release}' ]; do\n"
        "    _n=$((_n + 1)); [ \"$_n\" -lt 2000 ] || exit 1\n"
        "    sleep 0.01\n"
        "done\n"
        f"exec '{real_setsid}' \"$@\"\n",
        exe=True,
    )
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    shim_pid = -1
    pid = -1
    try:
        done = headless_start(
            tmp_path, state, bin_dir, dzhome,
            extra_env={"DAYZ_PROTON_START_WAIT_TENTHS": "0"},
        )
        assert done.returncode != 0
        assert "sway did not start" in done.stderr
        shim_pid = wait_for_pid_file(record, seconds=5.0)
        assert shim_pid > 0, "the setsid shim never wrote its pid record"
        before = {
            p.name: p.read_bytes() for p in sorted(state.iterdir()) if p.is_file()
        }
        done = headless_start(tmp_path, state, bin_dir, dzhome)
        assert done.returncode != 0
        assert "still has a running sway or launcher" in done.stderr
        after = {
            p.name: p.read_bytes() for p in sorted(state.iterdir()) if p.is_file()
        }
        assert after == before, "the refused retry changed the state"
        assert not pid_gone(shim_pid), "launcher A died on the refused retry"
        release.write_text("go\n")
        assert wait_gone(shim_pid, seconds=10.0), "launcher A did not settle after release"
        deadline = time.time() + 10.0
        while state_launcher_pids(state) and time.time() < deadline:
            time.sleep(0.05)
        assert not state_launcher_pids(state), "launcher A is still running after release"
        assert wait_no_state_sway(state, seconds=5.0), (
            "released launcher A left an untracked sway"
        )
        assert not state_sway_pids(state)
        done = headless_start(tmp_path, state, bin_dir, dzhome)
        assert done.returncode == 0, done.stderr
        pid = wait_for_pid_file(state / "sway.pid")
        assert pid > 0 and not pid_gone(pid)
        done = run(
            tmp_path, "headless", "stop", str(state),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr
        assert wait_gone(pid), "stop did not end the sway started after release"
        assert wait_no_state_sway(state, seconds=5.0)
        assert not state_sway_pids(state)
    finally:
        # Create the release so a still-waiting shim can exit, then kill
        # only this test's own processes.
        release.write_text("go\n")
        kill_process_tree(shim_pid)
        kill_process_tree(pid)
        kill_state_sways(state)


@requires_real_sway
def test_headless_second_start_refused_while_first_launcher_is_still_pending(
    tmp_path: Path,
) -> None:
    # Synchronised, no timing luck: a setsid shim writes a READY file and
    # then waits for a RELEASE file before exec-ing the real setsid, so the
    # first start stays pending -- with neither sway.pid nor sway.cancel in
    # the state yet -- although its launcher is already alive. A second
    # start on the same state must be refused without creating or changing
    # any file in the state; releasing the first launcher must then let it
    # succeed and be tracked, and stop must end it with nothing left.
    bin_dir = fake_sway(tmp_path)
    real_setsid = shutil.which("setsid")
    assert real_setsid is not None
    ready = tmp_path / "launcher-ready"
    release = tmp_path / "launcher-release"
    _write(
        bin_dir / "setsid",
        "#!/bin/sh\n"
        f": > '{ready}'\n"
        "_n=0\n"
        f"while [ ! -e '{release}' ]; do\n"
        "    _n=$((_n + 1)); [ \"$_n\" -lt 2000 ] || exit 1\n"
        "    sleep 0.01\n"
        "done\n"
        f"exec '{real_setsid}' \"$@\"\n",
        exe=True,
    )
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    state.mkdir()
    first: subprocess.Popen[str] | None = None
    pid = -1
    try:
        first = popen_headless_start(
            tmp_path, state, bin_dir, dzhome,
            extra_env={"DAYZ_PROTON_START_WAIT_TENTHS": "200"},
        )
        deadline = time.time() + 10.0
        while not ready.exists() and time.time() < deadline:
            time.sleep(0.01)
        assert ready.exists(), "the first launcher never reached the setsid shim"
        before_names = sorted(p.name for p in state.iterdir())
        before = {p.name: p.read_bytes() for p in state.iterdir() if p.is_file()}
        done = headless_start(tmp_path, state, bin_dir, dzhome)
        assert done.returncode != 0
        assert "still has a running sway or launcher" in done.stderr
        after_names = sorted(p.name for p in state.iterdir())
        after = {p.name: p.read_bytes() for p in state.iterdir() if p.is_file()}
        assert after_names == before_names, "the refused second start changed the state listing"
        assert after == before, "the refused second start changed a file in the state"
        release.write_text("go\n")
        _out, err = first.communicate(timeout=30)
        assert first.returncode == 0, err
        pid = wait_for_pid_file(state / "sway.pid")
        assert pid > 0 and not pid_gone(pid), "the released first launcher was not tracked"
        done = run(
            tmp_path, "headless", "stop", str(state),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr
        assert wait_gone(pid), "stop did not end the released first sway"
        assert wait_no_state_sway(state, seconds=5.0)
        assert not state_sway_pids(state)
        assert not state_launcher_pids(state)
    finally:
        release.write_text("go\n")
        if first is not None and first.poll() is None:
            kill_process_tree(first.pid)
            try:
                first.wait(timeout=5)
            except Exception:
                pass
        kill_process_tree(pid)
        kill_state_sways(state)


@requires_real_sway
def test_headless_alias_to_a_newline_directory_is_refused(tmp_path: Path) -> None:
    # A symlink `alias` to a directory named "state<LF>": resolving it must
    # keep the newline (a plain $(cd ... && pwd -P) strips it and would
    # resolve to the normal session's `state`). stop and start through the
    # alias must be refused before anything is read, created or signalled,
    # and the normal session must stay running and untouched.
    bin_dir = fake_sway(tmp_path)
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    newline_dir = tmp_path / "state\n"
    newline_dir.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(newline_dir, target_is_directory=True)
    pid = -1
    try:
        done = headless_start(tmp_path, state, bin_dir, dzhome)
        assert done.returncode == 0, done.stderr
        pid = wait_for_pid_file(state / "sway.pid")
        assert pid > 0 and not pid_gone(pid)
        pid_bytes = (state / "sway.pid").read_bytes()
        done = run(
            tmp_path, "headless", "stop", str(alias),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode != 0
        assert "may only contain" in done.stderr
        assert not pid_gone(pid), "stop through the alias signalled the normal session"
        assert (state / "sway.pid").read_bytes() == pid_bytes
        done = headless_start(tmp_path, alias, bin_dir, dzhome)
        assert done.returncode != 0
        assert "may only contain" in done.stderr
        assert not pid_gone(pid), "start through the alias touched the normal session"
        assert (state / "sway.pid").read_bytes() == pid_bytes
        assert list(newline_dir.iterdir()) == [], "the refused alias wrote into its target"
        done = run(
            tmp_path, "headless", "stop", str(state),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr
        assert wait_gone(pid), "the normal session was not stoppable afterwards"
    finally:
        kill_process_tree(pid)
        kill_state_sways(state)


@requires_real_sway
def test_headless_start_checks_again_after_the_last_wait(tmp_path: Path) -> None:
    # Deterministic, not timed: the fake sway only becomes the real (ELF)
    # sway once a marker file appears, and the marker is created by the
    # test hook (DAYZ_PROTON_TEST_HOOK) exactly when the parent reports its
    # last wait iteration. The hook is the barrier, in this order: FIRST it
    # waits (bounded) until the child's pid record exists and holds a pid,
    # only THEN does it create the marker, and then it waits (bounded)
    # until that pid has exec'd the real ELF sway before returning:
    # /proc/<pid>/exe resolving to the realbin/sway fixture, or argv[0]
    # being that path. /proc/<pid>/comm cannot tell that moment: comm is
    # the executed file's name, so the fake script named sway already has
    # comm sway before its exec of the ELF, and a comm wait returned while
    # the pid was still the script (/bin/sh .../fakebin/sway -c conf),
    # whose argv the parent's strict final check rightly refuses. Reading
    # the record before that wait raced the child's exec chain: an empty
    # pid made the hook's wait unmatchable, so the hook returned
    # before the child was ready and the parent's final check failed the
    # start under load. If the record never appears the hook leaves the
    # marker uncreated, so the start fails with its own "sway did not
    # start" instead of the hook silently timing out. So the sway becomes
    # ready after the parent's last sleep and only a loop that checks
    # again after that sleep can see it: a check-before-sleep loop made
    # its last check before the marker existed and fails this test. The
    # start must still succeed and track it, so a later stop can signal it.
    real_dir = tmp_path / "realbin"
    _fake_sway_binary(real_dir / "sway")
    bin_dir = tmp_path / "fakebin"
    marker = tmp_path / "become-sway"
    record = tmp_path / "late-sway.pid"
    _write(
        bin_dir / "sway",
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$$\" > '{record}'\n"
        # Bounded (~20 s): if the hook never creates the marker (its pid
        # wait expired, or the test failed earlier) exit instead of
        # spinning forever on a marker that will never appear.
        "_n=0\n"
        f"while [ ! -e '{marker}' ]; do\n"
        "    _n=$((_n + 1)); [ \"$_n\" -lt 2000 ] || exit 1\n"
        "    sleep 0.01\n"
        "done\n"
        f"exec '{real_dir / 'sway'}' \"$@\"\n",
        exe=True,
    )
    hook = _write(
        tmp_path / "test-hook.sh",
        "#!/bin/sh\n"
        "# $1 = wait iteration, $2 = total iterations (see dayz-proton.sh).\n"
        "# The script ignores this hook's exit status, so a bound expiring\n"
        "# is made visible by leaving the marker uncreated (the parent then\n"
        "# fails the start with its own message), never by exit code.\n"
        '[ "$1" = "$2" ] || exit 0\n'
        "# 1) Bounded (~10 s in 10 ms steps) wait until the child's pid\n"
        "# record exists and holds a pid. The record is written by the\n"
        "# fake sway, the second stage of the child's exec chain, so it\n"
        "# may not exist yet when this hook first runs.\n"
        "_pid=; _i=0\n"
        'while [ "$_i" -lt 1000 ]; do\n'
        f"    if [ -s '{record}' ]; then\n"
        f"        _pid=$(cat '{record}' 2>/dev/null) || _pid=\n"
        '        [ -n "$_pid" ] && break\n'
        "    fi\n"
        "    sleep 0.01; _i=$((_i + 1))\n"
        "done\n"
        "# No pid within the bound: leave the marker uncreated and return.\n"
        '[ -n "$_pid" ] || exit 0\n'
        "# 2) Only now release the child, then wait (bounded, ~10 s in\n"
        "# 10 ms steps) until that pid has exec'd the real ELF: its\n"
        "# /proc/<pid>/exe resolves to the ELF fixture, or argv[0] (the\n"
        "# first /proc/<pid>/cmdline field) is that path. Not comm: the\n"
        "# fake script named sway already has comm sway before the exec.\n"
        f": > '{marker}'\n"
        "_i=0\n"
        'while [ "$_i" -lt 1000 ]; do\n'
        '    _exe=$(readlink "/proc/$_pid/exe" 2>/dev/null) || _exe=\n'
        f"    [ \"$_exe\" = '{real_dir / 'sway'}' ] && exit 0\n"
        "    _a0=$(tr '\\0' '\\n' < \"/proc/$_pid/cmdline\" 2>/dev/null | head -n 1) || _a0=\n"
        f"    [ \"$_a0\" = '{real_dir / 'sway'}' ] && exit 0\n"
        "    sleep 0.01; _i=$((_i + 1))\n"
        "done\n"
        "exit 0\n",
        exe=True,
    )
    dzhome = tmp_path / "dzhome"
    state = tmp_path / "state"
    pid = -1
    try:
        done = headless_start(
            tmp_path, state, bin_dir, dzhome,
            extra_env={
                "DAYZ_PROTON_START_WAIT_TENTHS": "5",
                "DAYZ_PROTON_TEST_HOOK": str(hook),
            },
        )
        assert done.returncode == 0, done.stderr
        assert (state / "sway.pid").exists(), "sway that became ready in the last wait was left untracked"
        pid = int((state / "sway.pid").read_text().strip())
        assert not pid_gone(pid)
        assert (state / "sway.identity").exists()
        done = run(
            tmp_path, "headless", "stop", str(state),
            bin_dir=bin_dir, extra_env={"DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr
        assert wait_gone(pid), "tracked late sway was not signalled by stop"
    finally:
        kill_process_tree(pid)
        kill_state_sways(state)
        if record.exists():
            try:
                kill_process_tree(int(record.read_text().strip()))
            except ValueError:
                pass


@requires_real_sway
def test_wineserver_with_a_stale_starttime_is_not_signalled(tmp_path: Path) -> None:
    # Drive the script's own signal_session_wineservers with an enumeration
    # stub that returns a pid:starttime pair whose start time is stale (1):
    # the re-check before the signal must refuse it. The script body up to
    # its command dispatch is sourced; only prefix_wineserver is stubbed.
    fake_steam_with_tools(tmp_path)
    dzhome = tmp_path / "dzhome"
    prefix = dzhome / "tools" / "pfx"
    server: subprocess.Popen[bytes] | None = None
    try:
        server = start_fake_wineserver(tmp_path, "ws-stale", prefix, "wayland-1")
        assert server is not None
        source = SCRIPT.read_text()
        body = source.split("\ncmd=${1:-}", 1)[0]
        driver = tmp_path / "driver.sh"
        driver.write_text(
            body
            + "\nprefix_wineserver() { printf '%s:1\\n' \"$FAKE_WS_PID\"; }\n"
            + "signal_session_wineservers \"$FAKE_WS_PREFIX\" \"wayland-1\"\n"
        )
        env = {
            "PATH": os.environ["PATH"], "HOME": str(tmp_path / "home"),
            "STEAM_ROOT": str(tmp_path / "steam"),
            "FAKE_WS_PID": str(server.pid), "FAKE_WS_PREFIX": str(prefix),
        }
        (tmp_path / "home").mkdir(exist_ok=True)
        done = subprocess.run(
            ["sh", str(driver)], env=env, capture_output=True, text=True, timeout=30, check=False
        )
        assert done.returncode == 0, done.stderr
        assert server.poll() is None, "a wineserver whose start time changed was signalled"
    finally:
        kill_popen(server)


@requires_real_sway
def test_init_leaves_a_busy_prefix_running_and_stops_only_new_wineservers(tmp_path: Path) -> None:
    fake_steam_with_tools(tmp_path)
    dzhome = tmp_path / "dz[1]"
    tools_prefix = dzhome / "tools"
    (tools_prefix / "pfx" / "dosdevices").mkdir(parents=True)
    mfc = tools_prefix / "pfx" / "drive_c" / "windows" / "syswow64" / "mfc140.dll"
    mfc.parent.mkdir(parents=True)
    mfc.write_text("fake\n")
    busy: subprocess.Popen[bytes] | None = None
    try:
        busy = start_fake_wineserver(tmp_path, "ws-busy", tools_prefix / "pfx", "wayland-test")
        assert busy is not None
        sleeper_dir = tmp_path / "ws-new"
        sleeper_dir.mkdir()
        sleeper = sleeper_dir / "wineserver"
        _fake_pause_binary(sleeper)
        proton_dir, _calls, _bats = fake_proton(tmp_path, spawn_wineserver_from=sleeper)
        done = run(
            tmp_path, "init",
            extra_env={"PROTON": str(proton_dir), "DAYZ_PROTON_HOME": str(dzhome)},
        )
        assert done.returncode == 0, done.stderr + done.stdout
        assert busy.poll() is None, "the already-running wineserver was signalled"
        assert "left running" in done.stderr
        new_pid_file = tmp_path / "spawned-wineserver.pid"
        assert new_pid_file.exists(), "the fake Proton did not spawn a wineserver"
        assert wait_gone(int(new_pid_file.read_text().strip())), "the new wineserver was not signalled"
    finally:
        kill_popen(busy)
        new_pid_file = tmp_path / "spawned-wineserver.pid"
        if new_pid_file.exists():
            try:
                new_pid = int(new_pid_file.read_text().strip())
            except ValueError:
                new_pid = -1
            kill_process_tree(new_pid)
