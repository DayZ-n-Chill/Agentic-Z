"""Tests for build.py: workspace, junction, ownership-marker and stale-PBO checks."""
from __future__ import annotations

import fnmatch
import importlib.util
import os
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_build_pbo_under_test", HERE / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)
h = build.h


@pytest.fixture
def p_drive(monkeypatch, tmp_path):
    drive = tmp_path / "P"
    drive.mkdir()
    monkeypatch.setattr(build, "P_DRIVE", drive)
    monkeypatch.setattr(build, "MODS_ROOT", drive / "Mods")
    monkeypatch.setattr(build.lint, "P_DRIVE", drive)
    return drive


def _scaffold(project: Path, name: str = "MyMod") -> Path:
    mod = project / "workspace" / name
    mod.mkdir(parents=True)
    (mod / "config.cpp").write_text(
        f"class CfgPatches {{ class {name} {{ units[] = {{}}; weapons[] = {{}}; requiredAddons[] = {{\"DZ_Data\"}}; }}; }};",
        encoding="utf-8",
    )
    (mod / "$PBOPREFIX$").write_text(name, encoding="utf-8")
    return mod


# --- workspace -------------------------------------------------------------

def test_verify_workspace_accepts_scaffold(tmp_path):
    mod = _scaffold(tmp_path)
    assert build.verify_workspace("MyMod", tmp_path) == mod


def test_verify_workspace_missing_folder(tmp_path):
    with pytest.raises(SystemExit) as exc:
        build.verify_workspace("MyMod", tmp_path)
    assert "not found" in str(exc.value.code)


@pytest.mark.parametrize("missing", ["config.cpp", "$PBOPREFIX$"])
def test_verify_workspace_missing_required_file(tmp_path, missing):
    mod = _scaffold(tmp_path)
    (mod / missing).unlink()
    with pytest.raises(SystemExit) as exc:
        build.verify_workspace("MyMod", tmp_path)
    assert missing in str(exc.value.code)


@pytest.mark.parametrize("prefix", ["Other", "MyMod\\data", "mymod", ""])
def test_verify_workspace_refuses_prefix_mismatch(tmp_path, prefix):
    mod = _scaffold(tmp_path)
    (mod / "$PBOPREFIX$").write_text(prefix, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        build.verify_workspace("MyMod", tmp_path)
    msg = str(exc.value.code)
    assert "$PBOPREFIX$" in msg and repr(prefix) in msg and "'MyMod'" in msg


def test_verify_workspace_accepts_prefix_with_newline_or_bom(tmp_path):
    mod = _scaffold(tmp_path)
    (mod / "$PBOPREFIX$").write_bytes(b"\xef\xbb\xbfMyMod\r\n")
    assert build.verify_workspace("MyMod", tmp_path) == mod


# --- junction ----------------------------------------------------------------

def test_verify_junction_missing(p_drive, tmp_path):
    with pytest.raises(SystemExit) as exc:
        build.verify_junction("MyMod", tmp_path / "workspace" / "MyMod")
    assert "junction is missing" in str(exc.value.code)
    assert "/dayz-add-scaffold MyMod --piece junction" in str(exc.value.code)


def test_verify_junction_real_folder(p_drive, tmp_path):
    (p_drive / "MyMod").mkdir()
    with pytest.raises(SystemExit) as exc:
        build.verify_junction("MyMod", tmp_path / "workspace" / "MyMod")
    assert "real folder" in str(exc.value.code)


def test_verify_junction_points_elsewhere(p_drive, tmp_path, monkeypatch):
    (p_drive / "MyMod").mkdir()
    monkeypatch.setattr(h, "link_target", lambda p: tmp_path / "somewhere-else")
    with pytest.raises(SystemExit) as exc:
        build.verify_junction("MyMod", tmp_path / "workspace" / "MyMod")
    assert "points at" in str(exc.value.code)


def test_verify_junction_valid(p_drive, tmp_path, monkeypatch):
    workspace_mod = tmp_path / "workspace" / "MyMod"
    (p_drive / "MyMod").mkdir()
    monkeypatch.setattr(h, "link_target", lambda p: workspace_mod)
    assert build.verify_junction("MyMod", workspace_mod) == p_drive / "MyMod"


# --- ownership marker ---------------------------------------------------------

def test_marker_gate_refuses_existing_unmarked_deploy_dir(p_drive):
    deploy = build.MODS_ROOT / "@MyMod"
    (deploy / "Addons").mkdir(parents=True)
    with pytest.raises(SystemExit):
        h.gate_on_marker("MyMod", deploy)


def test_marker_gate_allows_first_build_and_marked_dir(p_drive):
    deploy = build.MODS_ROOT / "@MyMod"
    h.gate_on_marker("MyMod", deploy)  # absent: first build
    deploy.mkdir(parents=True)
    h.write_marker(deploy, "MyMod")
    h.gate_on_marker("MyMod", deploy)


# --- AddonBuilder command and output -----------------------------------------

def test_build_cmd_includes_include_list_and_clear(tmp_path):
    cmd = build.build_addon_builder_cmd(
        Path("AB.exe"), Path("P:/MyMod"), Path("P:/Mods/@MyMod/Addons"), "MyMod", Path("P:/temp/MyMod"), clean=True
    )
    assert f"-include={build.INCLUDE_LIST}" in cmd
    assert "-prefix=MyMod" in cmd
    assert cmd[-1] == "-clear"
    assert "-clear" not in build.build_addon_builder_cmd(
        Path("AB.exe"), Path("s"), Path("t"), "MyMod", Path("tmp"), clean=False
    )


def test_build_cmd_never_passes_exclude():
    # AddonBuilder 1.0.240639 crashes on any -exclude= (ArgumentNullException in
    # TextureHeaderBinazrizeTask); the live AZTestVest build hit it. build.py stages
    # the mod with exclude.lst applied instead.
    cmd = build.build_addon_builder_cmd(
        Path("AB.exe"), Path("P:/temp/_stage/MyMod"), Path("P:/Mods/@MyMod/Addons"), "MyMod",
        Path("P:/temp/MyMod"), clean=False
    )
    assert not any(a.startswith("-exclude") for a in cmd)
    patterns = build.exclude_patterns()
    assert ".gui-sources\\*.*" in patterns and "*\\.gui-sources\\*" in patterns
    assert "*\\.git\\*" in patterns
    assert "workbench\\*.*" in patterns and "*\\workbench\\*" in patterns


def test_stage_source_leaves_out_excluded_files(tmp_path):
    src = tmp_path / "MyMod"
    for rel in ["config.cpp", "scripts/4_World/Temp/MyHelper.c", "workbench/dayz.gproj",
                "gui/.gui-sources/icon.png", "data/old.bak", "Source/model.blend"]:
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text("x", encoding="utf-8")
    stage = tmp_path / "stage" / "MyMod"
    (stage / "stale.c").parent.mkdir(parents=True)
    (stage / "stale.c").write_text("old", encoding="utf-8")  # a previous stage is replaced
    assert build.stage_source(src, stage, build.exclude_patterns()) == (2, 4)
    kept = sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file())
    assert kept == ["config.cpp", "scripts/4_World/Temp/MyHelper.c"]


def _exclude_patterns():
    return build.exclude_patterns()


def _excluded(rel_path, patterns):
    return build.is_excluded(rel_path, patterns)


@pytest.mark.parametrize("rel", [
    "scripts\\4_World\\Temp\\MyHelper.c",
    "scripts\\3_Game\\source\\Util.c",
    "data\\doc\\sign.p3d",
    "data\\Doc\\sign_co.paa",
    "gui\\layouts\\temp\\panel.layout",
    "config.cpp",
])
def test_exclude_list_keeps_nested_source_temp_doc_folders(rel):
    # A folder named Source, Temp or Doc below the mod root is part of the mod.
    # The old *\Source\*, *\Temp\* and *\Doc\* patterns dropped these files
    # silently, so their classes went missing in game.
    assert not _excluded(rel, _exclude_patterns())


@pytest.mark.parametrize("rel", ["Source\\model.blend", "temp\\scratch.c", "Doc\\readme.txt"])
def test_exclude_list_still_drops_root_source_temp_doc_folders(rel):
    assert _excluded(rel, _exclude_patterns())


def test_exclude_list_anchors_source_temp_doc_to_mod_root():
    for pat in _exclude_patterns():
        folder = pat.lstrip("*\\").split("\\")[0].lower()
        if folder in ("source", "temp", "doc"):
            assert not pat.startswith("*"), f"unanchored exclude {pat!r} drops nested {folder} folders"


@pytest.mark.parametrize("bad", ["..", "../Other", r"..\Other", r"..\..\Windows", "My Mod", "@MyMod", "1Mod"])
def test_main_refuses_invalid_mod_name_before_touching_disk(p_drive, tmp_path, monkeypatch, bad):
    monkeypatch.setattr(build.h, "resolve_project_dir", lambda: pytest.fail("resolved the project for a bad name"))
    monkeypatch.setattr(build, "gate_on_lint", lambda *a: pytest.fail("linted a bad name"))
    monkeypatch.setattr(build, "TEMP_ROOT", tmp_path / "temp")
    monkeypatch.setattr(build.subprocess, "run", lambda *a, **k: pytest.fail("ran a command for a bad name"))
    monkeypatch.setattr("sys.argv", ["build.py", bad])
    with pytest.raises(SystemExit) as exc:
        build.main()
    assert "Invalid mod name" in str(exc.value.code)
    assert not (p_drive / "Mods").exists()
    assert not (tmp_path / "temp").exists()


def test_include_list_exists_and_covers_scripts():
    patterns = build.INCLUDE_LIST.read_text(encoding="utf-8").strip().split(";")
    assert "*.c" in patterns and "*.layout" in patterns


def test_check_pbo_output_missing(tmp_path):
    assert "missing" in build.check_pbo_output(tmp_path / "MyMod.pbo", time.time())


def test_check_pbo_output_stale(tmp_path):
    pbo = tmp_path / "MyMod.pbo"
    pbo.write_bytes(b"old")
    old = time.time() - 3600
    os.utime(pbo, (old, old))
    assert "stale" in build.check_pbo_output(pbo, time.time())


def test_check_pbo_output_fresh(tmp_path):
    started = time.time()
    pbo = tmp_path / "MyMod.pbo"
    pbo.write_bytes(b"new")
    assert build.check_pbo_output(pbo, started) is None


# --- --clean safety ----------------------------------------------------------

def test_other_pbos_lists_only_foreign_pbos(tmp_path):
    addons = tmp_path / "Addons"
    addons.mkdir()
    for name in ("MyMod.pbo", "mymod.pbo.bisign", "Payload.pbo", "Extra.PBO", "readme.txt"):
        (addons / name).write_text("x", encoding="utf-8")
    assert build.other_pbos(addons, "MyMod") == ["Extra.PBO", "Payload.pbo"]
    assert build.other_pbos(tmp_path / "missing", "MyMod") == []


def test_gate_clean_refuses_when_payload_pbos_present(tmp_path):
    addons = tmp_path / "Addons"
    addons.mkdir()
    (addons / "MyMod.pbo").write_text("x", encoding="utf-8")
    build.gate_clean(addons, "MyMod")  # only our own PBO: allowed
    (addons / "Payload.pbo").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        build.gate_clean(addons, "MyMod")
    assert "Payload.pbo" in str(exc.value.code)


def test_main_clean_refuses_before_running_addonbuilder(p_drive, tmp_path, monkeypatch):
    project = tmp_path / "proj"
    _scaffold(project)
    deploy = p_drive / "Mods" / "@MyMod"
    (deploy / "Addons").mkdir(parents=True)
    h.write_marker(deploy, "MyMod")
    (deploy / "Addons" / "Payload.pbo").write_text("x", encoding="utf-8")
    ran = []
    monkeypatch.setattr(build.h, "resolve_project_dir", lambda: project)
    monkeypatch.setattr(build.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(build, "validate_p_mods", lambda: None)
    monkeypatch.setattr(build, "verify_junction", lambda m, w: None)
    monkeypatch.setattr(build, "resolve_addon_builder", lambda: Path("AB.exe"))
    monkeypatch.setattr(build.subprocess, "run", lambda *a, **k: ran.append(a))
    monkeypatch.setattr("sys.argv", ["build.py", "MyMod", "--clean"])
    with pytest.raises(SystemExit) as exc:
        build.main()
    assert "--clean would wipe" in str(exc.value.code)
    assert ran == []


def test_failed_first_build_does_not_block_the_rebuild(p_drive, tmp_path, monkeypatch):
    """A first build that fails after creating @MyMod/Addons must leave the folder
    marked, so the next build passes the ownership gate and succeeds."""
    project = tmp_path / "proj"
    _scaffold(project)
    deploy = p_drive / "Mods" / "@MyMod"
    monkeypatch.setattr(build, "TEMP_ROOT", tmp_path / "temp")
    monkeypatch.setattr(build.h, "resolve_project_dir", lambda: project)
    monkeypatch.setattr(build.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(build, "validate_p_mods", lambda: None)
    monkeypatch.setattr(build, "verify_junction", lambda m, w: None)
    monkeypatch.setattr(build, "resolve_addon_builder", lambda: Path("AB.exe"))
    monkeypatch.setattr("sys.argv", ["build.py", "MyMod"])

    monkeypatch.setattr(build.subprocess, "run", lambda cmd: build.subprocess.CompletedProcess(cmd, 3))
    assert build.main() == 3
    assert (deploy / "Addons").is_dir()
    assert h.owns_deploy_dir(deploy, "MyMod")

    def good_build(cmd):
        (deploy / "Addons" / "MyMod.pbo").write_bytes(b"pbo")
        return build.subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(build.subprocess, "run", good_build)
    assert build.main() == 0
    assert (deploy / "Addons" / "MyMod.pbo").is_file()


# --- /dayz-lint gate -------------------------------------------------------

def test_lint_gate_passes_a_clean_scaffold(p_drive, tmp_path, capsys):
    project = tmp_path / "proj"
    _scaffold(project)
    build.gate_on_lint("MyMod", project)
    assert "/dayz-lint passed" in capsys.readouterr().out


def test_main_stops_on_lint_errors_after_preflight(p_drive, tmp_path, monkeypatch, capsys):
    project = tmp_path / "proj"
    mod = _scaffold(project)
    (mod / "scripts" / "4_World").mkdir(parents=True)
    (mod / "scripts" / "4_World" / "x.c").write_text("modded class PlayerBase extends PlayerBase {}\n", encoding="utf-8")
    called = []
    monkeypatch.setattr(build.h, "resolve_project_dir", lambda: project)
    monkeypatch.setattr(build.h, "gate_on_preflight", lambda: called.append("preflight"))
    monkeypatch.setattr("sys.argv", ["build.py", "MyMod"])
    with pytest.raises(SystemExit) as exc:
        build.main()
    message = str(exc.value.code)
    assert "/dayz-lint found 1 error(s)" in message
    assert "workspace/MyMod/scripts/4_World/x.c:1" in message
    # An unlisted scripts folder does not stop loading, so it is a warning, not one of the errors.
    assert "no CfgMods defs entry" not in message
    assert "[WARN]  lint workspace/MyMod/config.cpp: scripts/4_World/ holds scripts" in capsys.readouterr().out
    assert called == ["preflight"]


def test_main_gates_on_preflight_before_lint(p_drive, tmp_path, monkeypatch):
    # L2 rule: preflight runs at the start, so an unmounted P:\ is reported
    # before any lint output or lint FAIL can hide it.
    project = tmp_path / "proj"
    _scaffold(project)
    order = []

    def failing_preflight():
        order.append("preflight")
        raise SystemExit("[FAIL]  P:\ is not mounted")

    monkeypatch.setattr(build.h, "resolve_project_dir", lambda: project)
    monkeypatch.setattr(build.h, "gate_on_preflight", failing_preflight)
    monkeypatch.setattr(build, "gate_on_lint", lambda *a: order.append("lint"))
    monkeypatch.setattr("sys.argv", ["build.py", "MyMod"])
    with pytest.raises(SystemExit) as exc:
        build.main()
    assert "P:\ is not mounted" in str(exc.value.code)
    assert order == ["preflight"]
