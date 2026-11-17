"""Tests for the checks build.py runs around AddonBuilder: an empty temp dir before the
build, the result code in AddonBuilder's log, and the built PBO's entries against the stage."""
from __future__ import annotations

import hashlib
import importlib.util
import os
import stat
import struct
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_build_pbo_checks_under_test", HERE / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)
h = build.h
pe = build.pbo_entries


def write_pbo(path: Path, files: dict[str, bytes], prefix: str | None = "MyMod", trailer: bool = True) -> Path:
    """A PBO as AddonBuilder writes it: properties record, entry table, data, SHA-1 trailer."""
    out = b""
    if prefix is not None:
        out += b"\x00" + struct.pack("<5I", pe.VERS_MAGIC, 0, 0, 0, 0)
        out += b"product\x00dayz ugc\x00prefix\x00" + prefix.encode("ascii") + b"\x00\x00"
    for name, data in files.items():
        out += name.encode("ascii") + b"\x00" + struct.pack("<5I", 0, 0, 0, 1700000000, len(data))
    out += b"\x00" + struct.pack("<5I", 0, 0, 0, 0, 0) + b"".join(files.values())
    if trailer:
        out += b"\x00" + hashlib.sha1(out).digest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)
    return path


def make_stage(root: Path, files: list[str]) -> Path:
    stage = root / "_stage" / "MyMod"
    for rel in files:
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x")
    return stage


# What AddonBuilder 1.0.240639 packed for a staged scripts mod (measured): config.bin beside
# config.cpp, every included file under its own name, no entry for $PBOPREFIX$.
STAGED = ["config.cpp", "$PBOPREFIX$", "scripts/4_World/Thing.c", "data/thing.p3d", "data/thing_co.paa", "stringtable.csv"]
PACKED = ["config.bin", "config.cpp", "scripts\\4_World\\Thing.c", "data\\thing.p3d", "data\\thing_co.paa", "stringtable.csv"]


def _check(tmp_path, staged=STAGED, packed=PACKED, **pbo_kwargs):
    stage = make_stage(tmp_path, staged)
    pbo = write_pbo(tmp_path / "out" / "MyMod.pbo", {name: b"data" for name in packed}, **pbo_kwargs)
    return build.check_pbo_contents(pbo, stage, "MyMod")


# --- PBO contents against the stage --------------------------------------------

def test_complete_pbo_has_no_findings(tmp_path):
    errors, warnings, summary = _check(tmp_path)
    assert errors == [] and warnings == []
    assert summary == "MyMod.pbo holds 6 entries; all 5 packable staged files are in it"


@pytest.mark.parametrize("gone", ["scripts\\4_World\\Thing.c", "data\\thing.p3d"])
def test_missing_script_or_model_is_an_error(tmp_path, gone):
    errors, warnings, summary = _check(tmp_path, packed=[n for n in PACKED if n != gone])
    assert len(errors) == 1 and gone in errors[0] and "1 staged script or model file(s)" in errors[0]
    assert warnings == []
    assert "4 of 5 packable staged files" in summary


def test_missing_other_payload_is_a_warning(tmp_path):
    errors, warnings, _ = _check(tmp_path, packed=[n for n in PACKED if n != "stringtable.csv"])
    assert errors == []
    assert len(warnings) == 1 and "stringtable.csv" in warnings[0] and "include.lst lets through" in warnings[0]


def test_entry_names_match_without_case(tmp_path):
    packed = ["config.bin", "CONFIG.CPP", "Scripts\\4_world\\thing.c", "DATA\\Thing.p3d", "data\\thing_co.paa", "stringtable.csv"]
    assert _check(tmp_path, packed=packed)[:2] == ([], [])


def test_wrong_prefix_is_an_error(tmp_path):
    errors, _, _ = _check(tmp_path, prefix="Other")
    assert len(errors) == 1 and "'Other'" in errors[0] and "'MyMod'" in errors[0]


def test_prefix_matches_without_case(tmp_path):
    assert _check(tmp_path, prefix="mymod")[0] == []


def test_pbo_without_any_config_is_an_error(tmp_path):
    errors, warnings, _ = _check(tmp_path, packed=[n for n in PACKED if not n.startswith("config")])
    assert any("neither config.bin nor config.cpp" in e for e in errors)
    assert warnings == []  # the config is reported once, as the error


def test_config_bin_alone_is_enough(tmp_path):
    errors, warnings, _ = _check(tmp_path, packed=[n for n in PACKED if n != "config.cpp"])
    assert errors == []
    assert len(warnings) == 1 and "config.cpp" in warnings[0]


def test_files_in_a_nested_source_temp_or_doc_folder_get_the_folder_hint(tmp_path):
    # Measured with AddonBuilder 1.0.240639: the sync copies these, FileBank leaves them out.
    staged = STAGED + ["scripts/4_World/Temp/T.c", "data/doc/readme.txt"]
    errors, warnings, _ = _check(tmp_path, staged=staged)
    assert len(errors) == 1 and "scripts\\4_World\\Temp\\T.c" in errors[0]
    assert "folder named Source, Temp or Doc" in errors[0]
    assert len(warnings) == 1 and "data\\doc\\readme.txt" in warnings[0]
    assert "folder named Source, Temp or Doc" in warnings[0]


def test_a_missing_file_outside_those_folders_gets_no_folder_hint(tmp_path):
    errors, _, _ = _check(tmp_path, packed=[n for n in PACKED if not n.endswith(".c")])
    assert "Source, Temp or Doc" not in errors[0]


def test_entries_that_are_not_in_the_stage_are_a_warning(tmp_path):
    errors, warnings, _ = _check(tmp_path, packed=PACKED + ["old\\leftover.c", "thing.p3d"])
    assert errors == []
    assert len(warnings) == 1 and "2 entries" in warnings[0] and "old\\leftover.c" in warnings[0]


def test_generated_entries_are_not_extras(tmp_path):
    staged = STAGED + ["data/config.cpp"]
    packed = PACKED + ["data\\config.cpp", "data\\config.bin", "texHeaders.bin", "$PBOPREFIX$.txt"]
    assert _check(tmp_path, staged=staged, packed=packed)[:2] == ([], [])


def test_summary_counts_staged_files_with_no_include_pattern(tmp_path):
    staged = STAGED + ["model.cfg", "README.md", "notes.md", ".gitkeep"]
    errors, warnings, summary = _check(tmp_path, staged=staged)
    assert errors == [] and warnings == []
    assert summary.endswith(
        "(4 staged file(s) match no include.lst pattern and stay out: (no extension) 1, .cfg 1, .md 2)"
    )


def test_unreadable_pbo_is_a_warning_and_no_summary(tmp_path):
    stage = make_stage(tmp_path, STAGED)
    pbo = tmp_path / "MyMod.pbo"
    pbo.write_bytes(b"pbo")
    errors, warnings, summary = build.check_pbo_contents(pbo, stage, "MyMod")
    assert errors == [] and summary is None
    assert len(warnings) == 1 and "its contents were not checked" in warnings[0]


def test_pbo_without_its_checksum_trailer_is_a_warning(tmp_path):
    errors, warnings, _ = _check(tmp_path, trailer=False)
    assert errors == []
    assert len(warnings) == 1 and "does not end in the checksum" in warnings[0]


def test_include_patterns_come_from_include_lst():
    patterns = build.include_patterns()
    assert "*.c" in patterns and "*.p3d" in patterns and "*.csv" in patterns
    assert all(p == p.lower() and p.startswith("*.") for p in patterns)


# --- the temp dir starts empty ---------------------------------------------------

def test_clear_stale_temp_does_nothing_without_a_temp_dir(tmp_path, capsys):
    build.clear_stale_temp(tmp_path / "temp" / "MyMod")
    assert capsys.readouterr().out == ""


def test_clear_stale_temp_removes_old_files_even_read_only(tmp_path, capsys):
    temp = tmp_path / "temp" / "MyMod"
    old = temp / "mymod" / "scripts" / "old.c"
    old.parent.mkdir(parents=True)
    old.write_text("class Old {};", encoding="utf-8")
    os.chmod(old, stat.S_IREAD)
    build.clear_stale_temp(temp)
    assert not temp.exists()
    assert f"Removed the temp dir left by an earlier build: {temp}" in capsys.readouterr().out


def test_clear_stale_temp_stops_when_a_file_is_locked(tmp_path, monkeypatch):
    temp = tmp_path / "temp" / "MyMod"
    temp.mkdir(parents=True)

    def locked(folder):
        raise PermissionError(32, "The process cannot access the file", str(folder / "config.bin"))

    monkeypatch.setattr(build, "remove_tree", locked)
    with pytest.raises(SystemExit) as exc:
        build.clear_stale_temp(temp)
    msg = str(exc.value.code)
    assert msg.startswith(build.FAIL) and "config.bin" in msg and "pack old files" in msg


def test_clear_stale_temp_stops_when_the_folder_survives(tmp_path, monkeypatch):
    temp = tmp_path / "temp" / "MyMod"
    temp.mkdir(parents=True)
    monkeypatch.setattr(build, "remove_tree", lambda folder: None)  # reports success, removes nothing
    with pytest.raises(SystemExit) as exc:
        build.clear_stale_temp(temp)
    assert "still there after removing it" in str(exc.value.code)


# --- the result code in AddonBuilder's log ---------------------------------------

def _log_line(code: int, when: float) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when))
    return f"{stamp},968 [DEBUG] 1: AddonBuilder.Program.RunComandLineApp - Build finished. [ResultCode]={code}\n"


def test_addon_builder_log_sits_beside_the_addonbuilder_folder():
    exe = Path("C:/Tools/DayZ Tools/Bin/AddonBuilder/AddonBuilder.exe")
    assert build.addon_builder_log(exe) == Path("C:/Tools/DayZ Tools/Bin/Logs/AddonBuilder.rpt")


@pytest.mark.parametrize("code", [0, 1])
def test_logged_result_code_reads_this_builds_line(tmp_path, code):
    started = time.time()
    log = tmp_path / "AddonBuilder.rpt"
    log.write_text(
        _log_line(0, started - 3600) + "2026-01-01 10:00:00,000 [DEBUG] 1: X - Task end\n" + _log_line(code, started + 1),
        encoding="utf-8",
    )
    assert build.logged_result_code(log, started) == code


def test_logged_result_code_ignores_an_earlier_builds_line(tmp_path):
    started = time.time()
    log = tmp_path / "AddonBuilder.rpt"
    log.write_text(_log_line(1, started - 3600), encoding="utf-8")
    assert build.logged_result_code(log, started) is None


def test_logged_result_code_accepts_a_build_that_ends_in_its_first_second(tmp_path):
    started = time.time()
    log = tmp_path / "AddonBuilder.rpt"
    log.write_text(_log_line(1, started), encoding="utf-8")  # the log cuts the time to the second
    assert build.logged_result_code(log, started) == 1


def test_logged_result_code_without_a_log_or_a_result_line(tmp_path):
    assert build.logged_result_code(tmp_path / "missing.rpt", time.time()) is None
    log = tmp_path / "AddonBuilder.rpt"
    log.write_text("2026-01-01 10:00:00,000 [DEBUG] 1: X - Task end\n", encoding="utf-8")
    assert build.logged_result_code(log, time.time()) is None


def _stderr_line(message: str, when: float) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when))
    return f"{stamp},583 [WARN] 5: AddonBuilder.Tasks.ProcessBuildTask.process_ErrorDataReceived - {message}\n"


# The line CfgConvert wrote for a member defined twice (AddonBuilder 1.0.240639, binarize 1.30.164289.70).
DUPLICATE_MEMBER = r"File P:\temp\_stage\MyMod\config.cpp, line 17: /CfgVehicles/MyItem.scope: Member already defined."


def test_logged_tool_errors_returns_this_builds_stderr_lines(tmp_path):
    started = time.time()
    log = tmp_path / "AddonBuilder.rpt"
    log.write_text(
        _stderr_line("an error from an earlier build", started - 3600)
        + _stderr_line("FileServer MaxCacheSize = 34253 MB", started)
        + _stderr_line(DUPLICATE_MEMBER, started)
        + _stderr_line("", started)  # the tools end their output with an empty line
        + _log_line(1, started),
        encoding="utf-8",
    )
    assert build.logged_tool_errors(log, started) == [DUPLICATE_MEMBER]


def test_logged_tool_errors_keeps_the_last_lines_and_survives_a_missing_log(tmp_path):
    started = time.time()
    log = tmp_path / "AddonBuilder.rpt"
    log.write_text("".join(_stderr_line(f"error {n}", started) for n in range(15)), encoding="utf-8")
    assert build.logged_tool_errors(log, started, limit=3) == ["error 12", "error 13", "error 14"]
    assert build.logged_tool_errors(tmp_path / "missing.rpt", started) == []


# --- main ------------------------------------------------------------------------

@pytest.fixture
def p_drive(monkeypatch, tmp_path):
    drive = tmp_path / "P"
    drive.mkdir()
    monkeypatch.setattr(build, "P_DRIVE", drive)
    monkeypatch.setattr(build, "MODS_ROOT", drive / "Mods")
    monkeypatch.setattr(build.lint, "P_DRIVE", drive)
    return drive


def _main_env(p_drive, tmp_path, monkeypatch, run, exe=Path("AB.exe")):
    project = tmp_path / "proj"
    mod = project / "workspace" / "MyMod"
    (mod / "scripts" / "4_World").mkdir(parents=True)
    (mod / "config.cpp").write_text(
        'class CfgPatches { class MyMod { units[] = {}; weapons[] = {}; requiredAddons[] = {"DZ_Data"}; }; };\n'
        'class CfgMods { class MyMod { type = "mod"; class defs { class worldScriptModule'
        ' { value = ""; files[] = {"MyMod/scripts/4_World"}; }; }; }; };',
        encoding="utf-8",
    )
    (mod / "$PBOPREFIX$").write_text("MyMod", encoding="utf-8")
    (mod / "scripts" / "4_World" / "Thing.c").write_text("class Thing {};", encoding="utf-8")
    monkeypatch.setattr(build, "TEMP_ROOT", tmp_path / "temp")
    monkeypatch.setattr(build.h, "resolve_project_dir", lambda: project)
    monkeypatch.setattr(build.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(build, "validate_p_mods", lambda: None)
    monkeypatch.setattr(build, "verify_junction", lambda m, w: None)
    monkeypatch.setattr(build, "resolve_addon_builder", lambda: exe)
    monkeypatch.setattr(build.subprocess, "run", run)
    monkeypatch.setattr("sys.argv", ["build.py", "MyMod"])
    return p_drive / "Mods" / "@MyMod"


def test_main_passes_and_prints_the_summary_for_a_complete_pbo(p_drive, tmp_path, monkeypatch, capsys):
    deploy = p_drive / "Mods" / "@MyMod"

    def good_build(cmd):
        write_pbo(deploy / "Addons" / "MyMod.pbo", {"config.bin": b"b", "config.cpp": b"c", "scripts\\4_World\\Thing.c": b"t"})
        return build.subprocess.CompletedProcess(cmd, 0)

    _main_env(p_drive, tmp_path, monkeypatch, good_build)
    assert build.main() == 0
    out = capsys.readouterr().out
    assert f"{build.OK} MyMod.pbo holds 3 entries; all 2 packable staged files are in it" in out
    assert build.WARN not in out and "Cleaned temp and stage dirs" in out


def test_main_fails_when_a_script_did_not_reach_the_pbo(p_drive, tmp_path, monkeypatch, capsys):
    deploy = p_drive / "Mods" / "@MyMod"

    def config_only_build(cmd):
        write_pbo(deploy / "Addons" / "MyMod.pbo", {"config.bin": b"b"})
        return build.subprocess.CompletedProcess(cmd, 0)

    _main_env(p_drive, tmp_path, monkeypatch, config_only_build)
    assert build.main() == 1
    out = capsys.readouterr().out
    assert f"{build.FAIL} 1 staged script or model file(s) are not in MyMod.pbo: scripts\\4_World\\Thing.c" in out
    assert "do not test with it" in out and "Built:" not in out
    stage = tmp_path / "temp" / "_stage" / "MyMod"
    assert f"stage dir {stage}" in out and stage.is_dir()


def test_main_fails_on_a_failed_result_code_although_addonbuilder_exited_0(p_drive, tmp_path, monkeypatch, capsys):
    exe = tmp_path / "DayZ Tools" / "Bin" / "AddonBuilder" / "AddonBuilder.exe"
    log = tmp_path / "DayZ Tools" / "Bin" / "Logs" / "AddonBuilder.rpt"
    log.parent.mkdir(parents=True)
    deploy = p_drive / "Mods" / "@MyMod"
    (deploy / "Addons").mkdir(parents=True)
    h.write_marker(deploy, "MyMod")
    # The PBO of the last good build is still there, as after a real failed build.
    write_pbo(deploy / "Addons" / "MyMod.pbo", {"config.bin": b"b", "scripts\\4_World\\Thing.c": b"t"})

    def failed_build(cmd):
        now = time.time()
        log.write_text(_stderr_line(DUPLICATE_MEMBER, now) + _log_line(1, now), encoding="utf-8")
        return build.subprocess.CompletedProcess(cmd, 0)

    _main_env(p_drive, tmp_path, monkeypatch, failed_build, exe=exe)
    assert build.main() == 1
    out = capsys.readouterr().out
    assert "AddonBuilder exited 0, but its log says the build failed ([ResultCode]=1)" in out
    assert f"       {DUPLICATE_MEMBER}" in out  # the log names the cause; AddonBuilder's own output does not
    assert str(log) in out and "stale PBO" not in out


def test_main_empties_a_kept_temp_dir_before_addonbuilder_runs(p_drive, tmp_path, monkeypatch, capsys):
    deploy = p_drive / "Mods" / "@MyMod"
    stale = tmp_path / "temp" / "MyMod" / "mymod" / "scripts" / "4_World" / "Old.c"
    stale.parent.mkdir(parents=True)
    stale.write_text("class Old {};", encoding="utf-8")
    seen = []

    def good_build(cmd):
        seen.append(stale.exists())
        write_pbo(deploy / "Addons" / "MyMod.pbo", {"config.bin": b"b", "config.cpp": b"c", "scripts\\4_World\\Thing.c": b"t"})
        return build.subprocess.CompletedProcess(cmd, 0)

    _main_env(p_drive, tmp_path, monkeypatch, good_build)
    assert build.main() == 0
    assert seen == [False]
    assert "Removed the temp dir left by an earlier build" in capsys.readouterr().out


def test_main_does_not_run_addonbuilder_on_a_temp_dir_it_cannot_empty(p_drive, tmp_path, monkeypatch):
    (tmp_path / "temp" / "MyMod").mkdir(parents=True)
    ran = []
    _main_env(p_drive, tmp_path, monkeypatch, lambda cmd: ran.append(cmd))
    real_remove = build.remove_tree

    def locked_temp(folder):
        if folder == tmp_path / "temp" / "MyMod":
            raise PermissionError(32, "in use", str(folder))
        real_remove(folder)

    monkeypatch.setattr(build, "remove_tree", locked_temp)
    with pytest.raises(SystemExit) as exc:
        build.main()
    assert "Could not empty the temp dir of an earlier build" in str(exc.value.code)
    assert ran == []
