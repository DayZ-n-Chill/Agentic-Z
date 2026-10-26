"""Tests for the PreToolUse /dayz-scope-mod guard (scope_guard.py)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "scope_guard.py"


def _project(tmp_path: Path, active: str | None = "MyVest", mods=("MyVest", "OtherMod", ".git")) -> Path:
    for m in mods:
        (tmp_path / "workspace" / m).mkdir(parents=True)
        if not m.startswith("."):
            (tmp_path / "workspace" / m / "config.cpp").write_text("class CfgPatches {};", encoding="utf-8")
    if active:
        state = tmp_path / ".claude" / "local-memory" / "dayz-active-scope.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({"active_mod": active, "denied_rules": []}), encoding="utf-8")
    return tmp_path


def _run(
    project: Path,
    file_path: str,
    tool: str = "Edit",
    env_project: bool = True,
    tool_input: dict | None = None,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    payload = {
        "session_id": "s",
        "cwd": str(project),
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input if tool_input is not None else {"file_path": file_path, "content": "x"},
    }
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if env_project:
        env["CLAUDE_PROJECT_DIR"] = str(project)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=30
    )


def _denied(r: subprocess.CompletedProcess) -> str | None:
    assert r.returncode == 0
    if not r.stdout:
        return None
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert out["permissionDecision"] == "deny"
    return out["permissionDecisionReason"]


def test_blocks_other_mod_in_workspace(tmp_path):
    p = _project(tmp_path)
    reason = _denied(_run(p, str(p / "workspace" / "OtherMod" / "config.cpp")))
    assert reason and "active scope is MyVest" in reason and "OtherMod" in reason
    assert "/dayz-scope-mod --clear" in reason


def test_blocks_mod_folder_created_after_scoping(tmp_path):
    p = _project(tmp_path)
    assert _denied(_run(p, str(p / "workspace" / "BrandNew" / "config.cpp"), tool="Write"))


@pytest.mark.parametrize("rel", [r"workspace\MyVest\config.cpp", r"workspace\myvest\data\x.rvmat", r"workspace\README.md", r"docs\notes.md"])
def test_allows_active_mod_and_non_mod_paths(tmp_path, rel):
    p = _project(tmp_path)
    assert _denied(_run(p, str(p / rel))) is None


@pytest.mark.parametrize(
    "path, blocked",
    [
        (r"P:\OtherMod\config.cpp", True),
        (r"p:/othermod/scripts/4_World/x.c", True),
        ("/p/OtherMod/config.cpp", True),
        (r"P:\Mods\@OtherMod\Addons\OtherMod.pbo", True),
        (r"P:\MyVest\config.cpp", False),
        (r"P:\DZ\data\config.cpp", False),  # vanilla data, not a mod in workspace/
        (r"P:\Mods\@CF\Addons\x.pbo", False),
    ],
)
def test_p_drive_paths(tmp_path, path, blocked):
    p = _project(tmp_path)
    assert (_denied(_run(p, path)) is not None) is blocked


def test_no_scope_means_no_output(tmp_path):
    p = _project(tmp_path, active=None)
    assert _denied(_run(p, str(p / "workspace" / "OtherMod" / "config.cpp"))) is None


def test_falls_back_to_cwd_without_project_env(tmp_path):
    p = _project(tmp_path)
    assert _denied(_run(p, str(p / "workspace" / "OtherMod" / "x.c"), env_project=False))


@pytest.mark.parametrize("stdin", ["", "garbage", json.dumps({"tool_input": None})])
def test_bad_input_never_blocks(stdin):
    r = subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, text=True, timeout=30)
    assert (r.returncode, r.stdout) == (0, "")


def test_corrupt_state_file_never_blocks(tmp_path):
    p = _project(tmp_path)
    (p / ".claude" / "local-memory" / "dayz-active-scope.json").write_text("{not json", encoding="utf-8")
    assert _denied(_run(p, str(p / "workspace" / "OtherMod" / "config.cpp"))) is None


@pytest.mark.parametrize("marker", ["config.cpp", "$PBOPREFIX$"])
def test_only_folders_with_a_mod_marker_count_as_mods(tmp_path, marker):
    p = _project(tmp_path)
    notes = p / "workspace" / "_notes"
    notes.mkdir()
    assert _denied(_run(p, str(notes / "todo.md"))) is None  # helper folder, not a mod
    other = p / "workspace" / "PboOnly"
    other.mkdir()
    (other / marker).write_text("x", encoding="utf-8")
    assert _denied(_run(p, str(other / "scripts" / "x.c")))


def test_creating_prefix_file_in_new_folder_is_blocked(tmp_path):
    p = _project(tmp_path)
    assert _denied(_run(p, str(p / "workspace" / "BrandNew" / "$PBOPREFIX$"), tool="Write"))


@pytest.mark.parametrize(
    "rel, blocked",
    [
        (r"workspace\MyVest\..\OtherMod\a.c", True),  # climbs out of the active mod into another one
        ("workspace/MyVest/scripts/../../OtherMod/config.cpp", True),
        (r"workspace\OtherMod\..\MyVest\a.c", False),  # lands back in the active mod
        (r"workspace\MyVest\.\data\x.rvmat", False),
    ],
)
def test_dot_dot_segments_are_collapsed(tmp_path, rel, blocked):
    p = _project(tmp_path)
    assert (_denied(_run(p, str(p) + os.sep + rel)) is not None) is blocked


@pytest.mark.parametrize(
    "path, blocked",
    [
        (r"P:\MyVest\..\OtherMod\config.cpp", True),
        (r"P:\Mods\@MyVest\..\@OtherMod\Addons\x.pbo", True),
        ("/p/MyVest/../OtherMod/x.c", True),
        (r"P:\..\OtherMod\x.c", True),  # '..' at the drive root stays at the root, as on Windows
        (r"P:\OtherMod\..\MyVest\x.c", False),
    ],
)
def test_dot_dot_on_p_drive(tmp_path, path, blocked):
    p = _project(tmp_path)
    assert (_denied(_run(p, path)) is not None) is blocked


@pytest.mark.parametrize("target, blocked", [("OtherMod", True), ("MyVest", False)])
def test_multiedit_payload(tmp_path, target, blocked):
    p = _project(tmp_path)
    file_path = str(p / "workspace" / target / "scripts" / "4_World" / "x.c")
    tool_input = {"file_path": file_path, "edits": [{"old_string": "a", "new_string": "b"}]}
    assert (_denied(_run(p, file_path, tool="MultiEdit", tool_input=tool_input)) is not None) is blocked


@pytest.mark.parametrize(
    "rel, blocked",
    [
        (r"workspace\OtherMod.\x.c", True),  # Win32 drops the trailing dot: the file lands in OtherMod
        (r"workspace\OtherMod \x.c", True),  # and the trailing space
        (r"workspace\OtherMod. .\scripts\x.c", True),
        (r"workspace\MyVest.\x.c", False),  # the active mod, spelled with a trailing dot
    ],
)
def test_trailing_dots_and_spaces_are_cut(tmp_path, rel, blocked):
    p = _project(tmp_path)
    assert (_denied(_run(p, str(p) + os.sep + rel)) is not None) is blocked


@pytest.mark.parametrize("prefix", [r"\\?" + "\\", r"\\." + "\\"])
@pytest.mark.parametrize("target, blocked", [("OtherMod", True), ("MyVest", False)])
def test_long_path_and_device_prefixes_are_dropped(tmp_path, prefix, target, blocked):
    p = _project(tmp_path)
    path = prefix + str(p / "workspace" / target / "a.c")
    assert (_denied(_run(p, path)) is not None) is blocked


@pytest.mark.parametrize("path, blocked", [(r"\\?\P:\OtherMod\x.c", True), (r"\\?\P:\MyVest\x.c", False)])
def test_prefixed_p_drive_paths(tmp_path, path, blocked):
    p = _project(tmp_path)
    assert (_denied(_run(p, path)) is not None) is blocked


@pytest.mark.parametrize(
    "rel, blocked",
    [
        ("game/!Workshop/@OtherMod/Addons/OtherMod.pbo", True),  # the real folder behind P:\Mods\@OtherMod
        ("game/!workshop/@othermod/mod.cpp", True),
        ("game/!Workshop/@MyVest/Addons/MyVest.pbo", False),
        ("game/!Workshop/@CF/Addons/cf.pbo", False),  # not a mod in workspace/
        ("elsewhere/!Workshop/@OtherMod/a.c", False),  # a !Workshop folder outside the game install
    ],
)
def test_game_workshop_paths(tmp_path, rel, blocked):
    p = _project(tmp_path / "proj")
    game = tmp_path / "game"
    game.mkdir()
    (game / "DayZ_x64.exe").write_bytes(b"")
    reason = _denied(_run(p, str(tmp_path / rel), extra_env={"DAYZ_GAME_PATH": str(game)}))
    assert (reason is not None) is blocked
    if blocked:
        assert "the mod othermod" in reason.lower()


def _link_dir(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:  # Windows without symlink rights: a junction needs none
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)


def test_link_inside_active_mod_into_other_mod_is_blocked(tmp_path):
    p = _project(tmp_path)
    link = p / "workspace" / "MyVest" / "shared"
    _link_dir(link, p / "workspace" / "OtherMod")
    assert _denied(_run(p, str(link / "a.c")))
    assert _denied(_run(p, str(p / "workspace" / "MyVest" / "scripts" / "a.c"))) is None


# ---- sibling mods still being created --------------------------------------

@pytest.mark.parametrize(
    "rel",
    [
        "workspace/BrandNew/scripts/3_Game/x.c",  # before BrandNew has config.cpp
        "workspace/BrandNew/mod.cpp",
        "workspace/BrandNew/data/x.rvmat",
    ],
)
def test_new_sibling_folder_is_blocked_before_its_marker(tmp_path, rel):
    p = _project(tmp_path)
    reason = _denied(_run(p, str(p / rel), tool="Write"))
    assert reason and "BrandNew" in reason and "leading underscore" in reason


def test_existing_folder_without_marker_counts_as_a_mod(tmp_path):
    p = _project(tmp_path)
    (p / "workspace" / "Scratch").mkdir()
    assert _denied(_run(p, str(p / "workspace" / "Scratch" / "notes.md")))


@pytest.mark.parametrize("rel", ["workspace/_notes/todo.md", "workspace/_newhelper/a/b.md", "workspace/.git/config"])
def test_underscore_and_dotted_folders_stay_editable(tmp_path, rel):
    p = _project(tmp_path)
    assert _denied(_run(p, str(p / rel), tool="Write")) is None


def test_underscore_folder_with_a_marker_is_a_mod(tmp_path):
    p = _project(tmp_path)
    assert _denied(_run(p, str(p / "workspace" / "_Odd" / "config.cpp"), tool="Write"))


def test_relative_file_path_is_read_against_cwd(tmp_path):
    p = _project(tmp_path)
    assert _denied(_run(p, "workspace/OtherMod/a.c"))
    assert _denied(_run(p, "workspace/MyVest/a.c")) is None


# ---- malformed state files -------------------------------------------------

@pytest.mark.parametrize("state", ["[]", '["MyVest"]', "{}", '{"active_mod": null}', '{"active_mod": 5}', '"MyVest"'])
def test_state_file_without_an_active_mod_never_blocks(tmp_path, state):
    p = _project(tmp_path)
    (p / ".claude" / "local-memory" / "dayz-active-scope.json").write_text(state, encoding="utf-8")
    r = _run(p, str(p / "workspace" / "OtherMod" / "config.cpp"))
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")


# ---- 8.3 short names -------------------------------------------------------

def _short(path: Path) -> str:
    import ctypes

    buf = ctypes.create_unicode_buffer(32768)
    n = ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, len(buf))
    return buf.value if n else str(path)


@pytest.mark.skipif(sys.platform != "win32", reason="8.3 short names are a Windows feature")
@pytest.mark.parametrize("target, blocked", [("OtherModule", True), ("MyVestLonger", False)])
def test_short_name_paths(tmp_path, target, blocked):
    p = _project(tmp_path, active="MyVestLonger", mods=("MyVestLonger", "OtherModule"))
    folder = p / "workspace" / target
    short = _short(folder)
    if Path(short).name.lower() == target.lower():
        pytest.skip("this volume does not create 8.3 short names")
    assert "~" in Path(short).name
    # the whole path in short form, and only the mod folder short (a file that does not exist yet)
    for path in (short + "\\a.c", str(p / "workspace" / Path(short).name / "new.c")):
        assert (_denied(_run(p, path)) is not None) is blocked, path


# ---- !Workshop without preflight.py or a game install ----------------------

def _hook_copy(tmp_path: Path, preflight: str | None) -> Path:
    """A copy of the hook in a tree whose skills/dayz-preflight/preflight.py is `preflight` (None: missing)."""
    root = tmp_path / "plugin"
    (root / "hooks").mkdir(parents=True)
    copy = root / "hooks" / "scope_guard.py"
    copy.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    if preflight is not None:
        pre = root / "skills" / "dayz-preflight" / "preflight.py"
        pre.parent.mkdir(parents=True)
        pre.write_text(preflight, encoding="utf-8")
    return copy


@pytest.mark.parametrize(
    "preflight",
    [None, "def find_dayz_game():\n    return None\n", "raise RuntimeError('broken preflight')\n"],
    ids=["missing", "no-game", "broken"],
)
def test_workshop_path_without_preflight_or_game(tmp_path, preflight):
    p = _project(tmp_path / "proj")
    game = tmp_path / "game"
    game.mkdir()
    (game / "DayZ_x64.exe").write_bytes(b"")
    copy = _hook_copy(tmp_path, preflight)

    def run(path: str) -> subprocess.CompletedProcess:
        payload = {"cwd": str(p), "tool_name": "Edit", "tool_input": {"file_path": path}}
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(p), "DAYZ_GAME_PATH": str(game)}
        return subprocess.run(
            [sys.executable, str(copy)], input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=30
        )

    r = run(str(game / "!Workshop" / "@OtherMod" / "Addons" / "x.pbo"))
    assert (r.returncode, r.stdout) == (0, "")  # not checked, and no crash
    assert _denied(run(str(p / "workspace" / "OtherMod" / "x.c")))  # the other places are still guarded


# ---- shell commands ---------------------------------------------------------

def _shell(project: Path, command: str, tool: str) -> str | None:
    return _denied(_run(project, "", tool=tool, tool_input={"command": command}))


@pytest.mark.parametrize(
    "command",
    [
        "echo x > workspace/OtherMod/a.c",
        'echo x >> "workspace/OtherMod/a b.c"',
        "printf x 2> workspace/OtherMod/err.log",
        "echo x &> workspace/OtherMod/a.c",
        "echo x >workspace/OtherMod/a.c",
        "cp workspace/MyVest/a.c workspace/OtherMod/",
        "cp -r -t workspace/OtherMod workspace/MyVest/a.c",
        "cp --target-directory=workspace/OtherMod workspace/MyVest/a.c",
        "mv workspace/OtherMod/a.c workspace/MyVest/",  # removes the file from OtherMod
        "mv -t workspace/OtherMod workspace/MyVest/a.c",  # -t names the destination folder
        "mv --target-directory=workspace/OtherMod workspace/MyVest/a.c",
        "sed -i 's/a/b/' workspace/OtherMod/a.c",
        "sed -i.bak -e s/a/b/ workspace/OtherMod/a.c",
        "perl -pi -e 's/a/b/' workspace/OtherMod/a.c",
        "sed -E -i s/a/b/ workspace/OtherMod/config.cpp",  # -E is extended regex, not a script option
        "sed -i --expression=s/a/b/ workspace/OtherMod/a.c",  # inline script value, the file follows
        "cd workspace/OtherMod && echo x > a.c",
        r"cd /d workspace\OtherMod && echo x > a.c",  # cmd's /d switch is not the cd target
        "cd workspace; rm -rf OtherMod",
        "rm -rf workspace/OtherMod",
        "rm -f workspace/OtherMod/a.c",
        "mkdir -p workspace/BrandNew/scripts",
        "touch workspace/BrandNew/config.cpp",
        "echo x | tee -a $CLAUDE_PROJECT_DIR/workspace/OtherMod/a.c",
        'echo x > "${CLAUDE_PROJECT_DIR}/workspace/OtherMod/a.c"',
        "cat <<'EOF' > workspace/OtherMod/a.c\nclass A {};\nEOF",
        'bash -c "echo x > workspace/OtherMod/a.c"',
        "echo x > P:/OtherMod/a.c",
        "echo x > /p/Mods/@OtherMod/mod.cpp",
        "cp a.pbo P:/Mods/@OtherMod/Addons/",
        "true && (echo x > workspace/OtherMod/a.c)",
        "cp workspace/MyVest/a.c \\\n  workspace/OtherMod/a.c",
        "ln -s ../MyVest/a.c workspace/OtherMod/a.c",
        "rsync -a workspace/MyVest/ workspace/OtherMod/",
    ],
)
def test_bash_writes_into_other_mods_are_blocked(tmp_path, command):
    p = _project(tmp_path)
    reason = _shell(p, command, "Bash")
    assert reason and "this command writes to" in reason and "active scope is MyVest" in reason


@pytest.mark.parametrize(
    "command",
    [
        r"Set-Content -Path workspace\OtherMod\a.c -Value x",
        r"Set-Content workspace\OtherMod\a.c x",
        r'"x" | Out-File -Encoding utf8 workspace\OtherMod\a.c',
        r"Copy-Item workspace\MyVest\a.c -Destination workspace\OtherMod\a.c",
        r"Copy-Item workspace\MyVest\a.c workspace\OtherMod\a.c",
        r'Add-Content "$env:CLAUDE_PROJECT_DIR\workspace\OtherMod\a.c" x',
        r"Remove-Item -Recurse -Force workspace\OtherMod",
        r"New-Item -ItemType Directory -Path workspace\BrandNew\scripts",
        r"Move-Item workspace\OtherMod\a.c workspace\MyVest\a.c",
        r'powershell -NoProfile -Command "Set-Content P:\OtherMod\a.c x"',
        r"Write-Output x *> workspace\OtherMod\a.c",
        r"Set-Location workspace\OtherMod; Set-Content a.c x",
        r"Push-Location workspace\OtherMod; Set-Content a.c x",
        r"Push-Location workspace\OtherMod; Push-Location ..\MyVest; Pop-Location; Set-Content a.c x",
        r"Expand-Archive x.zip -DestinationPath workspace\OtherMod",
        r"Copy-Item a.c -Destination:workspace\OtherMod\a.c",  # PowerShell colon form
        r"Expand-Archive x.zip -DestinationPath:workspace\OtherMod",
        r"Remove-Item -Path:workspace\OtherMod\a.c",  # colon form of -Path
        r"Remove-Item -LiteralPath:workspace\OtherMod\a.c",
        r"Set-Content -Path:workspace\OtherMod\a.c -Value x",
        r"New-Item -Path:workspace\OtherMod\a.c",
        r"Set-Location workspace\OtherMod; Expand-Archive ..\MyVest\a.zip",  # no destination: unpacks into OtherMod
        r"Expand-Archive workspace\MyVest\a.zip workspace\OtherMod",  # second positional is the destination
        r"cmd /c copy workspace\MyVest\a.c workspace\OtherMod\a.c",
        "Set-Content `\n  -Path workspace\\OtherMod\\a.c -Value x",
        r"Get-ChildItem workspace\MyVest | ForEach-Object { Copy-Item $_ workspace\OtherMod }",
    ],
)
def test_powershell_writes_into_other_mods_are_blocked(tmp_path, command):
    p = _project(tmp_path)
    assert _shell(p, command, "PowerShell")


@pytest.mark.parametrize(
    "command",
    [
        "cat workspace/OtherMod/a.c",
        "grep -rn foo workspace/OtherMod",
        "sed -n 1,5p workspace/OtherMod/a.c",
        "sed 's/a/b/' workspace/OtherMod/a.c > workspace/MyVest/a.c",
        "cp workspace/OtherMod/a.c workspace/MyVest/a.c",  # reading from another mod is fine
        "echo x > workspace/MyVest/a.c 2>&1",
        "ls workspace/OtherMod > workspace/MyVest/list.txt 2>/dev/null",
        "wc -l < workspace/OtherMod/a.c",
        "cat <<< workspace/OtherMod/a.c > workspace/MyVest/b.c",
        "cat <<'EOF' > workspace/MyVest/a.c\nrm -rf workspace/OtherMod\nEOF\necho done",
        "# rm -rf workspace/OtherMod",
        "git diff workspace/OtherMod",
        "echo x > workspace/_notes/a.md",
        "cd workspace/OtherMod && cd ../MyVest && echo x > a.c",
        "pushd workspace/OtherMod; popd; echo x > a.c",  # popd returns to the project root
        "pushd workspace/MyVest && pushd ../OtherMod && popd && echo x > a.c",
        "echo 'rm -rf workspace/OtherMod'",
        "rm -rf workspace/MyVest/build",
        "sed -i --expression=s/a/b/ workspace/MyVest/a.c",
        "",
    ],
)
def test_bash_reads_and_active_mod_writes_pass(tmp_path, command):
    p = _project(tmp_path)
    assert _shell(p, command, "Bash") is None


@pytest.mark.parametrize(
    "command",
    [
        r"Get-Content workspace\OtherMod\a.c | Set-Content workspace\MyVest\a.c",
        r"Copy-Item -Path workspace\OtherMod\a.c -Destination workspace\MyVest\a.c",
        r"Copy-Item workspace\OtherMod\a.c -Destination:workspace\MyVest\a.c",
        r"Select-String -Path workspace\OtherMod\*.c -Pattern foo",
        r"Set-Content -Path workspace\MyVest\a.c -Value workspace\OtherMod",
        r"Push-Location workspace\OtherMod; Pop-Location; Set-Content a.c x",
        r"Set-Location workspace\MyVest; Expand-Archive ..\OtherMod\a.zip",  # reads the zip, unpacks into MyVest
    ],
)
def test_powershell_reads_and_active_mod_writes_pass(tmp_path, command):
    p = _project(tmp_path)
    assert _shell(p, command, "PowerShell") is None


def test_shell_command_relative_paths_use_the_hook_cwd(tmp_path):
    p = _project(tmp_path)
    assert _shell(p, "echo x > a.c", "Bash") is None  # cwd is the project: a.c is outside every mod
    payload = {"cwd": str(p / "workspace" / "OtherMod"), "tool_name": "Bash", "tool_input": {"command": "echo x > a.c"}}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(p)}
    r = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=30
    )
    assert _denied(r)


@pytest.mark.parametrize("command", ["ls 2> /dev/null", "dir > NUL", "Get-Item x > $null"])
def test_null_device_redirects_are_not_files(tmp_path, command):
    p = _project(tmp_path)
    payload = {"cwd": str(p / "workspace" / "OtherMod"), "tool_name": "Bash", "tool_input": {"command": command}}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(p)}
    r = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=30
    )
    assert _denied(r) is None


@pytest.mark.parametrize(
    "command, blocked",
    [
        ("if true; then rm -rf workspace/OtherMod; fi", True),
        ("for f in a; do rm workspace/OtherMod/a; done", True),
        ("if false; then :; else touch workspace/OtherMod/a; fi", True),
        ("while true; do mkdir workspace/OtherMod/x; done", True),
        ("! rm workspace/OtherMod/a", True),
        ("if true; then rm workspace/MyVest/a; fi", False),
    ],
)
def test_shell_writes_after_bash_keywords_are_checked(tmp_path, command, blocked):
    p = _project(tmp_path)
    assert bool(_shell(p, command, "Bash")) is blocked


def test_shell_command_without_scope_passes(tmp_path):
    p = _project(tmp_path, active=None)
    assert _shell(p, "rm -rf workspace/OtherMod", "Bash") is None


@pytest.mark.parametrize("tool_input", [{}, {"command": None}, {"command": 5}])
def test_shell_tool_with_bad_input_never_blocks(tmp_path, tool_input):
    p = _project(tmp_path)
    r = _run(p, "", tool="Bash", tool_input=tool_input)
    assert (r.returncode, r.stdout) == (0, "")


@pytest.mark.parametrize("config", ["hooks/hooks.json", ".claude/settings.json"])
def test_hook_is_wired_for_edit_and_shell_tools(config):
    events = json.loads((SCRIPT.parents[1] / config).read_text(encoding="utf-8"))["hooks"]
    group = next(g for g in events["PreToolUse"] if any("scope_guard.py" in h["command"] for h in g["hooks"]))
    assert set(group["matcher"].split("|")) == {"Edit", "Write", "MultiEdit", "Bash", "PowerShell"}
