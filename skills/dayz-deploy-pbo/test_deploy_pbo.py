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


def test_unsigned_pbos_matches_signature_case_insensitively():
    pbos = [Path("MyMod_Data.pbo"), Path("Other.PBO")]
    bisigns = [Path("mymod_data.pbo.key.bisign"), Path("other.pbo.Key.BISIGN")]
    assert deploy.unsigned_pbos(pbos, bisigns) == []


def test_main_no_unsigned_warning_for_mixed_case_signature(deploy_env, capsys):
    addons = deploy_env.parent / "project" / "workspace" / "Bundle" / "Addons"
    (addons / "MyMod_Data.pbo").write_bytes(b"pbo")
    (addons / "mymod_data.pbo.key.bisign").write_bytes(b"sig")
    assert deploy.main() == 0
    out = capsys.readouterr().out
    assert "MyMod_Data.pbo has no matching .bisign" not in out
    assert "extras.pbo has no matching .bisign" in out


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


def test_stale_files_ignores_built_linker_when_bundle_has_config(tmp_path):
    bundle = tmp_path / "Bundle"
    bundle.mkdir()
    (bundle / "config.cpp").write_text("class CfgPatches {};", encoding="utf-8")
    out = tmp_path / "@Bundle" / "Addons"
    out.mkdir(parents=True)
    for n in ("Bundle.pbo", "Bundle.pbo.key.bisign", "extras.pbo", "gone.pbo", "gone.pbo.key.bisign"):
        (out / n).write_bytes(b"")
    assert deploy.stale_files("Bundle", bundle, [Path("Extras.PBO")], [], [], out.parent) == [
        out / "gone.pbo", out / "gone.pbo.key.bisign",
    ]


def test_stale_files_flags_modname_pbo_without_linker(tmp_path):
    bundle = tmp_path / "Bundle"
    bundle.mkdir()
    out = tmp_path / "@Bundle" / "Addons"
    out.mkdir(parents=True)
    (out / "Bundle.pbo").write_bytes(b"")
    (out / "Bundle.pbo.key.bisign").write_bytes(b"")
    assert deploy.stale_files("Bundle", bundle, [], [], [], out.parent) == [
        out / "Bundle.pbo", out / "Bundle.pbo.key.bisign",
    ]


def test_stale_files_flags_dropped_bikey_and_orphan_bisign(tmp_path):
    bundle = tmp_path / "Bundle"
    bundle.mkdir()
    root = tmp_path / "@Bundle"
    (root / "Addons").mkdir(parents=True)
    (root / "Keys").mkdir()
    for n in ("extras.pbo", "extras.pbo.newkey.bisign", "extras.pbo.oldkey.bisign", "readme.txt"):
        (root / "Addons" / n).write_bytes(b"")
    for n in ("NewKey.bikey", "oldkey.bikey"):
        (root / "Keys" / n).write_bytes(b"")
    got = deploy.stale_files(
        "Bundle", bundle,
        [Path("extras.pbo")], [Path("extras.pbo.newkey.bisign")], [Path("newkey.bikey")],
        root,
    )
    assert got == [root / "Addons" / "extras.pbo.oldkey.bisign", root / "Keys" / "oldkey.bikey"]


def test_main_warns_on_deployed_bikey_the_bundle_dropped(deploy_env, capsys):
    keys_out = deploy_env / "@Bundle" / "Keys"
    keys_out.mkdir(parents=True)
    h.write_marker(deploy_env / "@Bundle", "Bundle")
    (keys_out / "retired.bikey").write_bytes(b"old key")
    assert deploy.main() == 0
    out = capsys.readouterr().out
    assert "[WARN]  retired.bikey is deployed but not in the bundle - servers that take keys" in out
    assert f'del "{keys_out / "retired.bikey"}"' in out
    assert (keys_out / "retired.bikey").exists()


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


# --- --dry-run -----------------------------------------------------------------

def _snapshot(root: Path) -> dict:
    return {
        p.relative_to(root): (p.read_bytes(), p.stat().st_mtime) if p.is_file() else None
        for p in root.rglob("*")
    }


def test_dry_run_on_fresh_deploy_writes_nothing(deploy_env, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["deploy.py", "Bundle", "--dry-run"])
    assert deploy.main() == 0
    out = capsys.readouterr().out
    assert "copy       " in out and "extras.pbo" in out
    assert "[WARN]  extras.pbo has no matching .bisign" in out
    assert "1 would be copied, 0 unchanged" in out
    assert not deploy_env.exists()


def test_dry_run_leaves_existing_deploy_untouched(deploy_env, monkeypatch, capsys):
    bundle_addons = deploy_env.parent / "project" / "workspace" / "Bundle" / "Addons"
    (bundle_addons / "same.pbo").write_bytes(b"same")
    root = deploy_env / "@Bundle"
    out_addons = root / "Addons"
    out_addons.mkdir(parents=True)
    h.write_marker(root, "Bundle")
    (out_addons / "extras.pbo").write_bytes(b"older deployed build")
    deploy.copy_if_changed(bundle_addons / "same.pbo", out_addons)
    (out_addons / "gone.pbo").write_bytes(b"dropped")
    before = _snapshot(root)

    monkeypatch.setattr("sys.argv", ["deploy.py", "Bundle", "--dry-run"])
    assert deploy.main() == 0
    out = capsys.readouterr().out
    assert f"overwrite  {out_addons / 'extras.pbo'}" in out
    assert f"unchanged  {out_addons / 'same.pbo'}" in out
    assert "[WARN]  gone.pbo is deployed but not in the bundle" in out
    assert "1 would be copied, 1 unchanged" in out
    assert _snapshot(root) == before


def test_dry_run_with_unwritable_marker_still_exits_0(deploy_env, monkeypatch):
    monkeypatch.setattr(h, "write_marker", lambda root, name: pytest.fail("dry run wrote the marker"))
    monkeypatch.setattr("sys.argv", ["deploy.py", "Bundle", "--dry-run"])
    assert deploy.main() == 0


def test_dry_run_header_ends_with_backslash_on_its_own_line(deploy_env, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["deploy.py", "Bundle", "--dry-run"])
    assert deploy.main() == 0
    lines = capsys.readouterr().out.splitlines()
    header = f"Dry run - nothing will be written to {deploy_env / '@Bundle'}\\"
    i = lines.index(header)
    assert lines[i + 1] == f"  copy       {deploy_env / '@Bundle' / 'Addons' / 'extras.pbo'}"


# --- keys and metadata land in the deploy folder -------------------------------

def test_main_copies_bikey_and_metadata_into_deploy_folder(deploy_env, capsys):
    bundle = deploy_env.parent / "project" / "workspace" / "Bundle"
    (bundle / "Keys").mkdir()
    (bundle / "Keys" / "mykey.bikey").write_bytes(b"key")
    (bundle / "meta.cpp").write_text("protocol = 1;", encoding="utf-8")
    (bundle / "mod.cpp").write_text('name = "Bundle";', encoding="utf-8")
    assert deploy.main() == 0
    root = deploy_env / "@Bundle"
    assert (root / "Keys" / "mykey.bikey").read_bytes() == b"key"
    assert (root / "meta.cpp").read_text(encoding="utf-8") == "protocol = 1;"
    assert (root / "mod.cpp").read_text(encoding="utf-8") == 'name = "Bundle";'
    assert (root / "Addons" / "extras.pbo").read_bytes() == b"pbo"
    out = capsys.readouterr().out
    assert "4 copied, 0 unchanged (1 .pbo, 0 .bisign, 1 .bikey, 2 meta)" in out


def test_main_without_keys_creates_no_keys_folder(deploy_env):
    assert deploy.main() == 0
    assert not (deploy_env / "@Bundle" / "Keys").exists()


# --- newer-file guard ----------------------------------------------------------

def _deploy_newer_extras(deploy_env) -> Path:
    """Deploy dir owned by us, holding an extras.pbo newer than the bundle's."""
    out_addons = deploy_env / "@Bundle" / "Addons"
    out_addons.mkdir(parents=True)
    h.write_marker(deploy_env / "@Bundle", "Bundle")
    deployed = out_addons / "extras.pbo"
    deployed.write_bytes(b"newer deployed build")
    later = time.time() + 3600
    os.utime(deployed, (later, later))
    return deployed


def test_deployed_is_newer_respects_tolerance(tmp_path):
    src = tmp_path / "a.pbo"
    src.write_bytes(b"x")
    out = tmp_path / "out"
    out.mkdir()
    dst = out / "a.pbo"
    dst.write_bytes(b"y")
    t = src.stat().st_mtime
    os.utime(dst, (t + 1, t + 1))
    assert deploy.deployed_is_newer(src, out) is False
    os.utime(dst, (t + 60, t + 60))
    assert deploy.deployed_is_newer(src, out) is True
    os.utime(dst, (t - 60, t - 60))
    assert deploy.deployed_is_newer(src, out) is False
    assert deploy.deployed_is_newer(src, tmp_path / "missing") is False


def test_main_refuses_to_overwrite_newer_deployed_file(deploy_env):
    bundle_addons = deploy_env.parent / "project" / "workspace" / "Bundle" / "Addons"
    (bundle_addons / "fresh.pbo").write_bytes(b"new file")
    deployed = _deploy_newer_extras(deploy_env)
    with pytest.raises(SystemExit) as exc:
        deploy.main()
    msg = str(exc.value.code)
    assert "newer than the bundle copy" in msg
    assert str(deployed) in msg
    assert "--force" in msg
    assert deployed.read_bytes() == b"newer deployed build"
    # Checked before anything is copied.
    assert not (deployed.parent / "fresh.pbo").exists()


def test_main_force_overwrites_newer_deployed_file(deploy_env, monkeypatch):
    deployed = _deploy_newer_extras(deploy_env)
    monkeypatch.setattr("sys.argv", ["deploy.py", "Bundle", "--force"])
    assert deploy.main() == 0
    assert deployed.read_bytes() == b"pbo"


def test_main_overwrites_older_deployed_file_without_force(deploy_env):
    out_addons = deploy_env / "@Bundle" / "Addons"
    out_addons.mkdir(parents=True)
    h.write_marker(deploy_env / "@Bundle", "Bundle")
    deployed = out_addons / "extras.pbo"
    deployed.write_bytes(b"older deployed build")
    earlier = time.time() - 3600
    os.utime(deployed, (earlier, earlier))
    assert deploy.main() == 0
    assert deployed.read_bytes() == b"pbo"


def test_dry_run_marks_newer_deployed_file(deploy_env, monkeypatch, capsys):
    deployed = _deploy_newer_extras(deploy_env)
    monkeypatch.setattr("sys.argv", ["deploy.py", "Bundle", "--dry-run"])
    assert deploy.main() == 0
    out = capsys.readouterr().out
    assert f"  newer      {deployed}" in out
    assert "1 deployed file(s) marked 'newer'" in out
    assert "0 would be copied, 0 unchanged" in out
    assert deployed.read_bytes() == b"newer deployed build"


# --- linker signature collision ------------------------------------------------

def test_linker_collision_flags_modname_bisign(tmp_path):
    bundle = tmp_path / "Bundle"
    bundle.mkdir()
    (bundle / "config.cpp").write_text("class CfgPatches {};", encoding="utf-8")
    sig = Path("BUNDLE.pbo.key.bisign")
    assert deploy.linker_collision("Bundle", bundle, [Path("extras.pbo")], [sig]) == sig
    assert deploy.linker_collision(
        "Bundle", bundle, [Path("extras.pbo")], [Path("bundleextras.pbo.key.bisign")]
    ) is None


def test_linker_collision_none_without_config(tmp_path):
    bundle = tmp_path / "Bundle"
    bundle.mkdir()
    assert deploy.linker_collision(
        "Bundle", bundle, [Path("Bundle.pbo")], [Path("Bundle.pbo.key.bisign")]
    ) is None


def test_main_refuses_payload_bisign_named_like_linker(deploy_env):
    bundle = deploy_env.parent / "project" / "workspace" / "Bundle"
    (bundle / "config.cpp").write_text("class CfgPatches {};", encoding="utf-8")
    (bundle / "Addons" / "Bundle.pbo.mykey.bisign").write_bytes(b"payload sig")
    built = deploy_env / "@Bundle" / "Addons"
    built.mkdir(parents=True)
    h.write_marker(deploy_env / "@Bundle", "Bundle")
    (built / "Bundle.pbo.mykey.bisign").write_bytes(b"linker sig")
    with pytest.raises(SystemExit) as exc:
        deploy.main()
    assert "same name as the linker PBO's signature" in str(exc.value.code)
    assert (built / "Bundle.pbo.mykey.bisign").read_bytes() == b"linker sig"
    assert not (built / "extras.pbo").exists()
