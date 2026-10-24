"""Tests for clean.py: managed-mod detection, link handling, ownership marker, plan order."""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_clean_workspace_under_test", HERE / "clean.py")
clean = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(clean)
h = clean.h
_real_running_blockers = clean.running_blockers


@pytest.fixture(autouse=True)
def p_drive(monkeypatch, tmp_path):
    drive = tmp_path / "P"
    (drive / "Mods").mkdir(parents=True)
    monkeypatch.setattr(clean, "P_DRIVE", drive)
    monkeypatch.setattr(clean, "MODS_ROOT", drive / "Mods")
    return drive


@pytest.fixture(autouse=True)
def no_blockers(monkeypatch):
    """No DayZ or Workbench process by default (a real one may be running on the test machine)."""
    monkeypatch.setattr(clean, "running_blockers", lambda: [])


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
    assert plan == [("workspace-files", bundle), ("deployed", deployed), ("workspace", bundle)]
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


def test_discover_mods_target_missing_says_not_found(tmp_path):
    (tmp_path / "workspace").mkdir()
    with pytest.raises(SystemExit) as exc:
        clean.discover_mods(tmp_path / "workspace", "Typo")
    msg = str(exc.value.code)
    assert "not found" in msg
    assert "not a managed mod" not in msg and "rmdir" not in msg


def test_discover_mods_target_empty_name_never_sweeps(tmp_path, junctions):
    """An empty --mod must not fall through to the all-mods sweep."""
    _native(tmp_path / "workspace", "MyMod", junctions)
    with pytest.raises(SystemExit):
        clean.discover_mods(tmp_path / "workspace", "")


@pytest.mark.parametrize("bad", ["", "..", r"..\SomeLink", "../SomeLink", r"..\..\Windows", "My Mod", "@MyMod", "1Mod"])
def test_main_refuses_invalid_mod_name_before_touching_disk(project, monkeypatch, bad):
    """A --mod outside the name rule could resolve outside workspace\\ (a link there counts as managed)."""
    outside = project.parent / "SomeLink"
    outside.mkdir()
    monkeypatch.setattr(h, "is_link", lambda p: True)
    monkeypatch.setattr(h, "resolve_project_dir", lambda: pytest.fail("resolved the project for a bad name"))
    monkeypatch.setattr(clean, "remove_artifact", lambda *a: pytest.fail("removed for a bad name"))
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--mod", bad, "--yes")
    assert "Invalid mod name" in str(exc.value.code)
    assert outside.is_dir()


def test_main_missing_mod_says_not_found(project, monkeypatch):
    monkeypatch.setattr(clean, "remove_artifact", lambda *a: pytest.fail("removed a missing mod"))
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--mod", "Typo", "--yes")
    assert "not found" in str(exc.value.code)


def test_discover_mods_target_with_git_refuses(tmp_path, junctions):
    mod = _native(tmp_path / "workspace", "MyMod", junctions)
    (mod / ".git").mkdir()
    with pytest.raises(SystemExit) as exc:
        clean.discover_mods(tmp_path / "workspace", "MyMod")
    assert ".git" in str(exc.value.code)


# --- find_artifacts: ownership + order ------------------------------------------

def test_plan_order_keeps_proofs_until_last(p_drive, tmp_path, monkeypatch):
    """Workspace files first (most often locked), proofs (marker, junction) after, empty folder last."""
    mod = _native(tmp_path / "workspace", "MyMod")
    deployed = p_drive / "Mods" / "@MyMod"
    deployed.mkdir()
    h.write_marker(deployed, "MyMod")
    monkeypatch.setattr(h, "link_target", lambda p: mod if p == p_drive / "MyMod" else None)

    plan, warnings = clean.find_artifacts(mod)

    assert [kind for kind, _ in plan] == ["workspace-files", "deployed", "junction", "workspace"]
    assert plan[2][1] == p_drive / "MyMod"
    assert warnings == []


def test_unmarked_deploy_dir_is_skipped_with_warning(p_drive, tmp_path):
    mod = _native(tmp_path / "workspace", "MyMod")
    (p_drive / "Mods" / "@MyMod").mkdir()

    plan, warnings = clean.find_artifacts(mod)

    assert [kind for kind, _ in plan] == ["workspace-files", "workspace"]
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


def _mklink_j(link: Path, target: Path) -> None:
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are a Windows feature")
@pytest.mark.parametrize("argv", [(), ("--mod", "Imported")], ids=["sweep", "mod"])
def test_broken_imported_link_is_cleaned_with_its_junction_and_deploy_dir(project, p_drive, monkeypatch, argv):
    """An imported mod whose external source was deleted: the link, P:\\<Name> and the deploy dir all go."""
    pf = h._preflight()
    monkeypatch.setattr(h, "link_target", pf.link_target)
    monkeypatch.setattr(h, "paths_equal", pf.paths_equal)
    source = project.parent / "external" / "Imported"
    source.mkdir(parents=True)
    (source / "config.cpp").write_text("", encoding="utf-8")
    link = project / "workspace" / "Imported"
    _mklink_j(link, source)
    junction = p_drive / "Imported"
    _mklink_j(junction, link)
    deployed = p_drive / "Mods" / "@Imported"
    (deployed / "Addons").mkdir(parents=True)
    (deployed / "Addons" / "Imported.pbo").write_text("", encoding="utf-8")
    h.write_marker(deployed, "Imported")
    shutil.rmtree(source)
    assert h.is_link(link) and not link.is_dir()

    assert clean.unmanaged_reason(link) is None
    plan, _ = clean.find_artifacts(link)
    assert plan == [("deployed", deployed), ("junction", junction), ("workspace-link", link)]

    assert _main(monkeypatch, *argv, "--yes") == 0
    for p in (link, junction, deployed):
        assert not h.is_link(p) and not p.exists()


def test_file_symlink_is_not_a_dir_link(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(h, "is_link", lambda p: True)
    assert clean.unmanaged_reason(tmp_path / "notes.txt") is not None


def test_imported_link_is_planned_as_workspace_link(p_drive, tmp_path, monkeypatch):
    mod = tmp_path / "workspace" / "Imported"
    mod.mkdir(parents=True)
    monkeypatch.setattr(h, "is_link", lambda p: p == mod)
    plan, _ = clean.find_artifacts(mod)
    assert plan == [("workspace-link", mod)]


# --- remove_artifact never recurses into links -------------------------------

def test_remove_artifact_uses_rmdir_for_links(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(clean.subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(clean.shutil, "rmtree", lambda p: pytest.fail("rmtree must not run on a link"))
    clean.remove_artifact("workspace-link", tmp_path / "Imported")
    clean.remove_artifact("junction", tmp_path / "P" / "MyMod")
    assert [c[:3] for c in calls] == [["cmd", "/c", "rmdir"]] * 2


def test_remove_artifact_empties_then_removes_workspace(tmp_path):
    mod = _native(tmp_path, "MyMod")
    (mod / "Scripts" / "4_World").mkdir(parents=True)
    clean.remove_artifact("workspace-files", mod)
    assert mod.is_dir() and list(mod.iterdir()) == []
    clean.remove_artifact("workspace", mod)
    assert not mod.exists()


def test_remove_artifact_deployed_removes_marker_last(p_drive, monkeypatch):
    deployed = p_drive / "Mods" / "@MyMod"
    (deployed / "Addons").mkdir(parents=True)
    (deployed / "Addons" / "MyMod.pbo").write_text("", encoding="utf-8")
    (deployed / "zz_readme.txt").write_text("", encoding="utf-8")
    h.write_marker(deployed, "MyMod")
    order = []
    real_unlink = Path.unlink

    def record(self, *a, **kw):
        order.append(self.name)
        real_unlink(self, *a, **kw)

    monkeypatch.setattr(Path, "unlink", record)
    clean.remove_artifact("deployed", deployed)
    assert not deployed.exists()
    assert order[-1] == h.SCAFFOLD_MARKER


def test_remove_entry_removes_a_link_without_its_target(tmp_path, monkeypatch):
    target = tmp_path / "external"
    target.mkdir()
    (target / "keep.txt").write_text("", encoding="utf-8")
    link = tmp_path / "link"
    link.mkdir()
    monkeypatch.setattr(h, "is_link", lambda p: p == link)
    monkeypatch.setattr(clean.shutil, "rmtree", lambda p: pytest.fail("rmtree ran on a link"))
    clean._remove_entry(link)
    assert not link.exists() and (target / "keep.txt").is_file()


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


def test_main_reports_rmdir_message_on_failure(project, monkeypatch, capsys, junctions):
    _native(project / "workspace", "AMod", junctions)

    def rmdir_fails(kind, path):
        raise subprocess.CalledProcessError(2, ["cmd", "/c", "rmdir"], stderr="The process cannot access the file.")

    monkeypatch.setattr(clean, "remove_artifact", rmdir_fails)
    assert _main(monkeypatch, "--yes") == 1
    assert "The process cannot access the file." in capsys.readouterr().out


def test_main_never_removes_hand_placed_mod(project, monkeypatch, capsys):
    mod = _native(project / "workspace", "HandPlaced")
    monkeypatch.setattr(clean, "remove_artifact", lambda *a: pytest.fail("removed a hand-placed mod"))
    assert _main(monkeypatch, "--yes") == 0
    out = capsys.readouterr().out
    assert "skipping workspace\\HandPlaced" in out and "Nothing to clean." in out
    assert mod.is_dir()


def test_main_plans_health_results_before_the_workspace(project, monkeypatch, capsys, junctions):
    mod = _native(project / "workspace", "MyMod", junctions)
    health = project / ".server" / "!Health" / "MyMod"
    health.mkdir(parents=True)
    other = project / ".server" / "!Health" / "OtherMod"
    other.mkdir()
    removed = []
    monkeypatch.setattr(clean, "remove_artifact", lambda kind, path: removed.append((kind, path)))
    assert _main(monkeypatch, "--yes") == 0
    kinds = [k for k, _ in removed]
    assert ("health", health) in removed
    assert kinds.index("health") < kinds.index("workspace")
    assert all(path != other for _, path in removed)


def test_main_include_server_does_not_list_health_twice(project, monkeypatch, capsys, junctions):
    _native(project / "workspace", "MyMod", junctions)
    (project / ".server" / "!Health" / "MyMod").mkdir(parents=True)
    assert _main(monkeypatch, "--include-server", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "(health)" not in out and "(server staging)" in out


# --- a locked file must not cost the proof of ownership ----------------------

def _fake_link_removal(monkeypatch, junctions):
    """cmd /c rmdir on a faked P:\\<Name> junction: forget the fake link instead."""
    def run(cmd, **kw):
        assert cmd[:3] == ["cmd", "/c", "rmdir"]
        junctions.pop(Path(cmd[3]), None)
    monkeypatch.setattr(clean.subprocess, "run", run)


def test_locked_workspace_file_keeps_proof_and_rerun_finishes(project, p_drive, monkeypatch, capsys, junctions):
    """Workbench holding a workspace file stops run 1; run 2 still sees the mod as managed and finishes."""
    mod = _native(project / "workspace", "MyMod", junctions)
    (mod / "Scripts").mkdir()
    deployed = p_drive / "Mods" / "@MyMod"
    (deployed / "Addons").mkdir(parents=True)
    h.write_marker(deployed, "MyMod")
    _fake_link_removal(monkeypatch, junctions)
    real_rmtree = clean.shutil.rmtree

    def locked(path, *a, **kw):
        raise PermissionError(32, "The process cannot access the file", str(path))

    monkeypatch.setattr(clean.shutil, "rmtree", locked)
    assert _main(monkeypatch, "--yes") == 1
    assert "could not remove (workspace-files)" in capsys.readouterr().out
    assert p_drive / "MyMod" in junctions and h.owns_deploy_dir(deployed, "MyMod")
    assert [m.name for m in clean.discover_mods(project / "workspace", None)[0]] == ["MyMod"]

    monkeypatch.setattr(clean.shutil, "rmtree", real_rmtree)
    assert _main(monkeypatch, "--yes") == 0
    assert not mod.exists() and not deployed.exists() and p_drive / "MyMod" not in junctions


def test_locked_pbo_keeps_marker_and_junction(project, p_drive, monkeypatch, capsys, junctions):
    """DayZ holding the deployed .pbo stops the run with the marker and junction still in place."""
    mod = _native(project / "workspace", "MyMod", junctions)
    deployed = p_drive / "Mods" / "@MyMod"
    (deployed / "Addons").mkdir(parents=True)
    h.write_marker(deployed, "MyMod")
    _fake_link_removal(monkeypatch, junctions)
    real_rmtree = clean.shutil.rmtree

    def pbo_locked(path, *a, **kw):
        if Path(path).name == "Addons":
            raise PermissionError(32, "The process cannot access the file", str(path))
        real_rmtree(path, *a, **kw)

    monkeypatch.setattr(clean.shutil, "rmtree", pbo_locked)
    assert _main(monkeypatch, "--yes") == 1
    assert "could not remove (deployed)" in capsys.readouterr().out
    assert h.owns_deploy_dir(deployed, "MyMod") and p_drive / "MyMod" in junctions
    assert mod.is_dir()
    assert [m.name for m in clean.discover_mods(project / "workspace", None)[0]] == ["MyMod"]


# --- running DayZ or Workbench ------------------------------------------------

def test_main_refuses_while_dayz_or_workbench_runs(project, monkeypatch, junctions):
    mod = _native(project / "workspace", "MyMod", junctions)
    monkeypatch.setattr(clean, "running_blockers", lambda: ["DayZDiag_x64.exe"])
    monkeypatch.setattr(clean, "remove_artifact", lambda *a: pytest.fail("removed while DayZ runs"))
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--yes")
    msg = str(exc.value.code)
    assert "DayZDiag_x64.exe is running" in msg and "/dayz-stop-test" in msg
    assert mod.is_dir()


def test_dry_run_warns_while_dayz_or_workbench_runs(project, monkeypatch, capsys, junctions):
    _native(project / "workspace", "MyMod", junctions)
    monkeypatch.setattr(clean, "running_blockers", lambda: ["workbenchApp.exe"])
    assert _main(monkeypatch, "--dry-run") == 0
    out = capsys.readouterr().out
    assert "[WARN]" in out and "workbenchApp.exe is running" in out and "(--dry-run) nothing removed." in out


def test_running_blockers_reads_tasklist(monkeypatch):
    queries = []

    class _Done:
        def __init__(self, stdout):
            self.stdout = stdout

    def tasklist(cmd, **kw):
        queries.append(cmd)
        if "DayZDiag_x64.exe" in cmd[2]:
            return _Done('"DayZDiag_x64.exe","1234","Console","1","2,000 K"\n')
        return _Done("INFO: No tasks are running which match the specified criteria.\n")

    monkeypatch.setattr(clean.subprocess, "run", tasklist)
    assert _real_running_blockers() == ["DayZDiag_x64.exe"]
    assert [q[:2] for q in queries] == [["tasklist", "/FI"]] * 2
