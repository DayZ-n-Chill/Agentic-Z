"""Tests for deploy.py: idempotent copy, ownership gate, bundle checks, .bisign detection."""
from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_deploy_pbo_under_test", HERE / "deploy.py")
deploy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(deploy)
h = deploy.h


# --- copy_if_changed -----------------------------------------------------------

def test_copy_if_changed_copies_new_file(tmp_path):
    src = tmp_path / "a.pbo"
    src.write_bytes(b"payload")
    dst_dir = tmp_path / "out" / "Addons"
    assert deploy.copy_if_changed(src, dst_dir) is True
    assert (dst_dir / "a.pbo").read_bytes() == b"payload"


def test_copy_if_changed_skips_identical_second_run(tmp_path):
    src = tmp_path / "a.pbo"
    src.write_bytes(b"payload")
    dst_dir = tmp_path / "out"
    deploy.copy_if_changed(src, dst_dir)
    assert deploy.copy_if_changed(src, dst_dir) is False


def test_copy_if_changed_recopies_when_size_differs(tmp_path):
    src = tmp_path / "a.pbo"
    src.write_bytes(b"payload")
    dst_dir = tmp_path / "out"
    deploy.copy_if_changed(src, dst_dir)
    src.write_bytes(b"bigger payload")
    assert deploy.copy_if_changed(src, dst_dir) is True
    assert (dst_dir / "a.pbo").read_bytes() == b"bigger payload"


def test_copy_if_changed_recopies_when_mtime_differs(tmp_path):
    src = tmp_path / "a.pbo"
    src.write_bytes(b"payload")
    dst_dir = tmp_path / "out"
    deploy.copy_if_changed(src, dst_dir)
    later = time.time() + 60
    os.utime(src, (later, later))
    assert deploy.copy_if_changed(src, dst_dir) is True


# --- unsigned_pbos -------------------------------------------------------------

def test_unsigned_pbos_flags_only_missing_signatures():
    pbos = [Path("a.pbo"), Path("b.pbo"), Path("ab.pbo")]
    bisigns = [Path("a.pbo.mykey.bisign")]
    assert deploy.unsigned_pbos(pbos, bisigns) == [Path("b.pbo"), Path("ab.pbo")]


def test_unsigned_pbos_empty_when_all_signed():
    assert deploy.unsigned_pbos([Path("a.pbo")], [Path("a.pbo.key.bisign")]) == []


# --- verify_bundle -------------------------------------------------------------

def test_verify_bundle_requires_pbo(tmp_path):
    (tmp_path / "workspace" / "Bundle" / "Addons").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        deploy.verify_bundle("Bundle", tmp_path)
    assert "No .pbo" in str(exc.value.code)


def test_verify_bundle_requires_addons(tmp_path):
    (tmp_path / "workspace" / "Bundle").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        deploy.verify_bundle("Bundle", tmp_path)
    assert "Addons" in str(exc.value.code)


def test_verify_bundle_accepts_payload_without_config(tmp_path):
    addons = tmp_path / "workspace" / "Bundle" / "Addons"
    addons.mkdir(parents=True)
    (addons / "x.pbo").write_bytes(b"")
    assert deploy.verify_bundle("Bundle", tmp_path) == tmp_path / "workspace" / "Bundle"


# --- gate_on_marker (shared with build and clean) ------------------------------

def test_gate_on_marker_refuses_unowned_dir(tmp_path):
    root = tmp_path / "@Bundle"
    root.mkdir()
    (root / h.SCAFFOLD_MARKER).write_text("SomeoneElse\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        h.gate_on_marker("Bundle", root)


def test_gate_on_marker_accepts_owned_dir(tmp_path):
    root = tmp_path / "@Bundle"
    root.mkdir()
    h.write_marker(root, "Bundle")
    h.gate_on_marker("Bundle", root)


# --- main() --------------------------------------------------------------------

@pytest.fixture
def deploy_env(tmp_path, monkeypatch):
    project = tmp_path / "project"
    addons = project / "workspace" / "Bundle" / "Addons"
    addons.mkdir(parents=True)
    (addons / "extras.pbo").write_bytes(b"pbo")
    mods = tmp_path / "Mods"
    monkeypatch.setattr(deploy, "MODS_ROOT", mods)
    monkeypatch.setattr(deploy, "validate_p_mods", lambda: None)
    monkeypatch.setattr(h, "resolve_project_dir", lambda: project)
    monkeypatch.setattr(h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr("sys.argv", ["deploy.py", "Bundle"])
    return mods


def test_main_warns_unsigned_pbo_with_single_space(deploy_env, capsys):
    assert deploy.main() == 0
    out = capsys.readouterr().out
    assert "[WARN]  extras.pbo has no matching .bisign" in out
    assert (deploy_env / "@Bundle" / h.SCAFFOLD_MARKER).read_text(encoding="utf-8") == "Bundle\n"


def test_main_reports_locked_file_and_exits_1(deploy_env, monkeypatch, capsys):
    def locked(src, dst):
        raise PermissionError(13, "The process cannot access the file", str(dst))

    monkeypatch.setattr(deploy.shutil, "copy2", locked)
    assert deploy.main() == 1
    out = capsys.readouterr().out
    assert "[FAIL]  could not copy extras.pbo:" in out
    assert "Close DayZ or run /dayz-stop-test" in out
    # Marked as ours, so the rerun after closing DayZ passes the ownership gate.
    h.gate_on_marker("Bundle", deploy_env / "@Bundle")


def test_main_exits_1_when_marker_cannot_be_written(deploy_env, monkeypatch):
    monkeypatch.setattr(h, "write_marker", lambda root, name: False)
    assert deploy.main() == 1


@pytest.mark.parametrize("bad", ["..", "../Other", r"..\..\Windows", "My Mod", "@MyMod", "1Mod"])
def test_main_refuses_invalid_mod_name_before_touching_disk(deploy_env, monkeypatch, bad):
    monkeypatch.setattr(h, "resolve_project_dir", lambda: pytest.fail("resolved the project for a bad name"))
    monkeypatch.setattr("sys.argv", ["deploy.py", bad])
    with pytest.raises(SystemExit) as exc:
        deploy.main()
    assert "Invalid mod name" in str(exc.value.code)
    assert not deploy_env.exists()


# --- stale payload and linker collision ----------------------------------------

def test_main_warns_on_deployed_pbo_the_bundle_dropped(deploy_env, capsys):
    addons_out = deploy_env / "@Bundle" / "Addons"
    addons_out.mkdir(parents=True)
    h.write_marker(deploy_env / "@Bundle", "Bundle")
    (addons_out / "old_name.pbo").write_bytes(b"renamed away")
    assert deploy.main() == 0
    out = capsys.readouterr().out
    assert "[WARN]  old_name.pbo is deployed but not in the bundle" in out
    assert f'del "{addons_out / "old_name.pbo"}"' in out
    assert "extras.pbo is deployed" not in out
    # Still never deletes.
    assert (addons_out / "old_name.pbo").exists()


def test_stale_pbos_ignores_built_linker_when_bundle_has_config(tmp_path):
    bundle = tmp_path / "Bundle"
    bundle.mkdir()
    (bundle / "config.cpp").write_text("class CfgPatches {};", encoding="utf-8")
    out = tmp_path / "Addons"
    out.mkdir()
    for n in ("Bundle.pbo", "extras.pbo", "gone.pbo", "gone.pbo.key.bisign"):
        (out / n).write_bytes(b"")
    assert deploy.stale_pbos("Bundle", bundle, [Path("Extras.PBO")], out) == [out / "gone.pbo"]


def test_stale_pbos_flags_modname_pbo_without_linker(tmp_path):
    bundle = tmp_path / "Bundle"
    bundle.mkdir()
    out = tmp_path / "Addons"
    out.mkdir()
    (out / "Bundle.pbo").write_bytes(b"")
    assert deploy.stale_pbos("Bundle", bundle, [], out) == [out / "Bundle.pbo"]


def test_main_refuses_payload_named_like_linker(deploy_env, capsys):
    bundle = deploy_env.parent / "project" / "workspace" / "Bundle"
    (bundle / "config.cpp").write_text("class CfgPatches {};", encoding="utf-8")
    (bundle / "Addons" / "bundle.pbo").write_bytes(b"payload")
    built = deploy_env / "@Bundle" / "Addons"
    built.mkdir(parents=True)
    h.write_marker(deploy_env / "@Bundle", "Bundle")
    (built / "Bundle.pbo").write_bytes(b"linker")
    with pytest.raises(SystemExit) as exc:
        deploy.main()
    assert "same name as the linker PBO" in str(exc.value.code)
    assert (built / "Bundle.pbo").read_bytes() == b"linker"
    assert not (built / "extras.pbo").exists()


def test_main_allows_modname_pbo_without_linker_config(deploy_env):
    bundle = deploy_env.parent / "project" / "workspace" / "Bundle"
    (bundle / "Addons" / "Bundle.pbo").write_bytes(b"payload")
    assert deploy.main() == 0
    assert (deploy_env / "@Bundle" / "Addons" / "Bundle.pbo").read_bytes() == b"payload"
