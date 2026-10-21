"""Tests for clean.py: managed-mod detection, link handling, ownership marker, plan order."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_clean_workspace_under_test", HERE / "clean.py")
clean = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(clean)
h = clean.h


@pytest.fixture(autouse=True)
def p_drive(monkeypatch, tmp_path):
    drive = tmp_path / "P"
    (drive / "Mods").mkdir(parents=True)
    monkeypatch.setattr(clean, "P_DRIVE", drive)
    monkeypatch.setattr(clean, "MODS_ROOT", drive / "Mods")
    return drive


@pytest.fixture(autouse=True)
def junctions(monkeypatch):
    """Fake P:\\<Name> links: {link path: target}. Empty means no links exist."""
    links: dict[Path, Path] = {}
    monkeypatch.setattr(h, "link_target", lambda p: links.get(p))
    monkeypatch.setattr(h, "paths_equal", lambda a, b: Path(a).resolve() == Path(b).resolve())
    return links


def _native(workspace: Path, name: str, junctions: dict | None = None) -> Path:
    """A /dayz-new-mod scaffold; pass `junctions` to also fake its P:\\<Name> junction."""
    mod = workspace / name
    mod.mkdir(parents=True)
    (mod / "config.cpp").write_text("", encoding="utf-8")
    (mod / "$PBOPREFIX$").write_text(name, encoding="utf-8")
    if junctions is not None:
        junctions[clean.P_DRIVE / name] = mod
    return mod


# --- unmanaged_reason / link detection --------------------------------------

def test_scaffold_with_junction_is_managed(tmp_path, junctions):
    assert clean.unmanaged_reason(_native(tmp_path, "MyMod", junctions)) is None


def test_hand_placed_mod_without_proof_is_not_managed(tmp_path):
    """config.cpp + $PBOPREFIX$ alone do not prove the toolkit made it."""
    reason = clean.unmanaged_reason(_native(tmp_path, "HandPlaced"))
    assert reason and "no proof" in reason


def test_folder_with_git_is_never_managed(p_drive, tmp_path, junctions):
    mod = _native(tmp_path, "MyMod", junctions)
    (mod / ".git").mkdir()
    deployed = p_drive / "Mods" / "@MyMod"
    deployed.mkdir()
    h.write_marker(deployed, "MyMod")
    reason = clean.unmanaged_reason(mod)
    assert reason and ".git" in reason


def test_file_is_not_managed(tmp_path):
    (tmp_path / "notes.txt").write_text("", encoding="utf-8")
    assert clean.unmanaged_reason(tmp_path / "notes.txt") is not None


def test_link_without_scaffold_files_is_managed(tmp_path, monkeypatch):
    (tmp_path / "Imported").mkdir()
    monkeypatch.setattr(h, "is_link", lambda p: True)
    assert clean.unmanaged_reason(tmp_path / "Imported") is None


def test_discover_mods_skips_unmanaged_and_warns_on_mod_folders(tmp_path, junctions):
    ws = tmp_path / "workspace"
    _native(ws, "B", junctions)
    _native(ws, "A", junctions)
    _native(ws, "HandPlaced")
    (ws / "Junk").mkdir()
    mods, warnings = clean.discover_mods(ws, None)
    assert [p.name for p in mods] == ["A", "B"]
    assert len(warnings) == 1
    assert "workspace\\HandPlaced" in warnings[0] and "rmdir /s /q" in warnings[0]


def test_payload_bundle_with_matching_marker_is_managed(p_drive, tmp_path):
    bundle = tmp_path / "workspace" / "Bundle"
    (bundle / "Addons").mkdir(parents=True)
    assert clean.unmanaged_reason(bundle) is not None
    deployed = p_drive / "Mods" / "@Bundle"
    deployed.mkdir()
    h.write_marker(deployed, "OtherName")
    assert clean.unmanaged_reason(bundle) is not None
    h.write_marker(deployed, "Bundle")
    assert clean.unmanaged_reason(bundle) is None
    assert [p.name for p in clean.discover_mods(tmp_path / "workspace", None)[0]] == ["Bundle"]


def test_payload_bundle_plan_removes_deployed_and_workspace(p_drive, tmp_path):
    bundle = tmp_path / "workspace" / "Bundle"
    (bundle / "Addons").mkdir(parents=True)
    deployed = p_drive / "Mods" / "@Bundle"
    deployed.mkdir()
    h.write_marker(deployed, "Bundle")
    plan, warnings = clean.find_artifacts(bundle)
    assert plan == [("deployed", deployed), ("workspace", bundle)]
    assert warnings == []


def test_discover_mods_missing_workspace(tmp_path):
    assert clean.discover_mods(tmp_path / "workspace", None) == ([], [])


def test_discover_mods_target_not_managed_explains_and_hints(tmp_path):
    _native(tmp_path / "workspace", "HandPlaced")
    with pytest.raises(SystemExit) as exc:
        clean.discover_mods(tmp_path / "workspace", "HandPlaced")
    msg = str(exc.value.code)
    assert "no proof" in msg and "imported mod link" in msg and "ownership marker" in msg
    assert "rmdir /s /q" in msg


def test_discover_mods_target_with_git_refuses(tmp_path, junctions):
    mod = _native(tmp_path / "workspace", "MyMod", junctions)
    (mod / ".git").mkdir()
    with pytest.raises(SystemExit) as exc:
        clean.discover_mods(tmp_path / "workspace", "MyMod")
    assert ".git" in str(exc.value.code)


# --- find_artifacts: ownership + order ------------------------------------------

def test_plan_order_junction_deployed_workspace(p_drive, tmp_path, monkeypatch):
    mod = _native(tmp_path / "workspace", "MyMod")
    deployed = p_drive / "Mods" / "@MyMod"
    deployed.mkdir()
    h.write_marker(deployed, "MyMod")
    monkeypatch.setattr(h, "link_target", lambda p: mod if p == p_drive / "MyMod" else None)

    plan, warnings = clean.find_artifacts(mod)

    assert [kind for kind, _ in plan] == ["junction", "deployed", "workspace"]
    assert plan[0][1] == p_drive / "MyMod"
    assert warnings == []


def test_unmarked_deploy_dir_is_skipped_with_warning(p_drive, tmp_path):
    mod = _native(tmp_path / "workspace", "MyMod")
    (p_drive / "Mods" / "@MyMod").mkdir()

    plan, warnings = clean.find_artifacts(mod)

    assert [kind for kind, _ in plan] == ["workspace"]
    assert len(warnings) == 1 and h.SCAFFOLD_MARKER in warnings[0]


def test_mismatched_marker_is_skipped(p_drive, tmp_path):
    mod = _native(tmp_path / "workspace", "MyMod")
    deployed = p_drive / "Mods" / "@MyMod"
    deployed.mkdir()
    h.write_marker(deployed, "OtherMod")

    plan, warnings = clean.find_artifacts(mod)
    assert "deployed" not in [kind for kind, _ in plan]
    assert warnings


def test_junction_pointing_elsewhere_is_left_alone(p_drive, tmp_path, monkeypatch):
    mod = _native(tmp_path / "workspace", "MyMod")
    monkeypatch.setattr(h, "link_target", lambda p: tmp_path / "other-project" / "MyMod")
    plan, _ = clean.find_artifacts(mod)
    assert "junction" not in [kind for kind, _ in plan]


def test_imported_link_is_planned_as_workspace_link(p_drive, tmp_path, monkeypatch):
    mod = tmp_path / "workspace" / "Imported"
    mod.mkdir(parents=True)
    monkeypatch.setattr(h, "is_link", lambda p: p == mod)
    plan, _ = clean.find_artifacts(mod)
    assert plan[-1] == ("workspace-link", mod)


# --- remove_artifact never recurses into links -------------------------------

def test_remove_artifact_uses_rmdir_for_links(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(clean.subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(clean.shutil, "rmtree", lambda p: pytest.fail("rmtree must not run on a link"))
    clean.remove_artifact("workspace-link", tmp_path / "Imported")
    clean.remove_artifact("junction", tmp_path / "P" / "MyMod")
    assert [c[:3] for c in calls] == [["cmd", "/c", "rmdir"]] * 2


def test_remove_artifact_rmtree_for_folders(tmp_path):
    mod = _native(tmp_path, "MyMod")
    clean.remove_artifact("workspace", mod)
    assert not mod.exists()


# --- main() -------------------------------------------------------------------

class _Stdin:
    def __init__(self, tty: bool):
        self._tty = tty

    def isatty(self):
        return self._tty


@pytest.fixture
def project(monkeypatch, tmp_path):
    root = tmp_path / "project"
    (root / "workspace").mkdir(parents=True)
    monkeypatch.setattr(h, "resolve_project_dir", lambda: root)
    monkeypatch.setattr(h, "gate_on_preflight", lambda: None)
    return root


def _main(monkeypatch, *argv):
    monkeypatch.setattr(clean.sys, "argv", ["clean.py", *argv])
    return clean.main()


def test_main_refuses_without_yes_when_not_a_tty(project, monkeypatch, junctions):
    mod = _native(project / "workspace", "MyMod", junctions)
    monkeypatch.setattr(clean.sys, "stdin", _Stdin(False))
    monkeypatch.setattr(clean, "remove_artifact", lambda *a: pytest.fail("removed without consent"))
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch)
    assert "--yes" in str(exc.value.code)
    assert mod.is_dir()


def test_main_dry_run_removes_nothing(project, monkeypatch, capsys, junctions):
    mod = _native(project / "workspace", "MyMod", junctions)
    (project / ".server").mkdir()
    monkeypatch.setattr(clean, "remove_artifact", lambda *a: pytest.fail("dry run removed something"))
    assert _main(monkeypatch, "--include-server", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "(--dry-run) nothing removed." in out and "(server staging)" in out
    assert mod.is_dir() and (project / ".server").is_dir()


def test_main_include_server_refuses_legacy_layout(project, monkeypatch):
    (project / "workspace" / "_server").mkdir()
    (project / ".server").mkdir()
    monkeypatch.setattr(clean, "remove_artifact", lambda *a: pytest.fail("removed despite legacy layout"))
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--include-server", "--yes")
    assert "Legacy layout" in str(exc.value.code)
    assert (project / ".server").is_dir()


def test_main_stops_at_first_failed_removal(project, monkeypatch, capsys, junctions):
    _native(project / "workspace", "AMod", junctions)
    _native(project / "workspace", "BMod", junctions)
    calls = []

    def fail_first(kind, path):
        calls.append(path)
        raise OSError("in use")

    monkeypatch.setattr(clean, "remove_artifact", fail_first)
    assert _main(monkeypatch, "--yes") == 1
    assert len(calls) == 1
    assert "could not remove" in capsys.readouterr().out


def test_main_never_removes_hand_placed_mod(project, monkeypatch, capsys):
    mod = _native(project / "workspace", "HandPlaced")
    monkeypatch.setattr(clean, "remove_artifact", lambda *a: pytest.fail("removed a hand-placed mod"))
    assert _main(monkeypatch, "--yes") == 0
    out = capsys.readouterr().out
    assert "skipping workspace\\HandPlaced" in out and "Nothing to clean." in out
    assert mod.is_dir()
