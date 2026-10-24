"""Tests for add_scaffold.py: every piece is idempotent and never touches existing files."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_add_scaffold_under_test", HERE / "add_scaffold.py")
scaf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scaf)

GPROJ = """GameProjectClass {
 Configurations {
  GameProjectConfigClass PC {
   FileSystem {
    FileSystemPathClass {
     Name "Game Root"
     Directory "./"
    }
   }
   ScriptModules {
    ScriptModulePathClass {
     Name "game"
     Paths {
      "scripts/3_Game"
     }
    }
   }
  }
 }
}
"""


@pytest.fixture
def fake_tools(monkeypatch, tmp_path):
    wb = tmp_path / "Tools" / "Bin" / "Workbench"
    wb.mkdir(parents=True)
    (wb / "dayz.gproj").write_text(GPROJ, encoding="utf-8")
    (wb / "DayZSetting.xml").write_text("<settings/>", encoding="utf-8")
    monkeypatch.setattr(scaf._nm, "find_dayz_tools", lambda: tmp_path / "Tools")
    return wb


def _author():
    return "Tester"


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _run_piece(piece: str, target: Path) -> str:
    return scaf.add_piece(piece, target, "MyMod", _author)


@pytest.mark.parametrize("piece", scaf.PIECES)
def test_second_run_changes_nothing(piece, tmp_path, fake_tools):
    target = tmp_path / "workspace" / "MyMod"
    target.mkdir(parents=True)
    assert _run_piece(piece, target) == scaf.ADDED
    before = _snapshot(target)
    assert _run_piece(piece, target) == scaf.PRESENT
    assert _snapshot(target) == before


@pytest.mark.parametrize(
    "piece, rel, status",
    [
        ("config", "config.cpp", scaf.PRESENT),
        # "user content" is not "MyMod", so the prefix is kept but reported wrong.
        ("prefix", "$PBOPREFIX$", scaf.WRONG),
        ("readme", "README.md", scaf.PRESENT),
    ],
)
def test_existing_file_is_left_untouched(piece, rel, status, tmp_path):
    target = tmp_path / "MyMod"
    target.mkdir()
    (target / rel).write_text("user content", encoding="utf-8")
    assert _run_piece(piece, target) == status
    assert (target / rel).read_text(encoding="utf-8") == "user content"


def test_existing_config_does_not_prompt_for_author(tmp_path):
    target = tmp_path / "MyMod"
    target.mkdir()
    (target / "config.cpp").write_text("mine", encoding="utf-8")
    assert scaf.add_config(target, "MyMod", lambda: pytest.fail("author must not be resolved")) == scaf.PRESENT


def test_skeleton_adds_only_missing_folders(tmp_path):
    target = tmp_path / "MyMod"
    (target / "data").mkdir(parents=True)
    (target / "data" / "model.p3d").write_bytes(b"p3d")
    assert scaf.add_skeleton(target) == scaf.ADDED
    assert (target / "scripts" / "3_Game" / ".gitkeep").exists()
    assert not (target / "data" / ".gitkeep").exists()
    assert (target / "data" / "model.p3d").read_bytes() == b"p3d"


def test_workbench_keeps_existing_gproj_and_adds_missing_xml(tmp_path, fake_tools):
    target = tmp_path / "MyMod"
    (target / "workbench").mkdir(parents=True)
    (target / "workbench" / "dayz.gproj").write_text("custom gproj", encoding="utf-8")
    assert scaf.add_workbench(target, "MyMod") == scaf.ADDED
    assert (target / "workbench" / "dayz.gproj").read_text(encoding="utf-8") == "custom gproj"
    assert (target / "workbench" / "DayZSetting.xml").read_text(encoding="utf-8") == "<settings/>"


def test_workbench_gproj_gets_mod_paths(tmp_path, fake_tools):
    target = tmp_path / "MyMod"
    target.mkdir()
    scaf.add_workbench(target, "MyMod")
    text = (target / "workbench" / "dayz.gproj").read_text(encoding="utf-8")
    assert '"MyMod/scripts/3_Game"' in text and 'Directory "P:/MyMod/"' in text


def test_workbench_skipped_without_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(scaf._nm, "find_dayz_tools", lambda: None)
    target = tmp_path / "MyMod"
    target.mkdir()
    assert scaf.add_workbench(target, "MyMod") == scaf.SKIPPED
    assert not (target / "workbench").exists()


def test_workbench_skipped_when_tools_gproj_missing(tmp_path, fake_tools):
    # DayZ Tools present but Bin\Workbench\dayz.gproj missing: only the xml
    # can be copied, which must not count as the workbench piece being added.
    (fake_tools / "dayz.gproj").unlink()
    target = tmp_path / "MyMod"
    target.mkdir()
    assert scaf.add_workbench(target, "MyMod") == scaf.SKIPPED
    assert not (target / "workbench" / "dayz.gproj").exists()
    assert (target / "workbench" / "DayZSetting.xml").exists()


def test_unknown_piece_raises(tmp_path):
    with pytest.raises(ValueError):
        scaf.add_piece("bogus", tmp_path, "MyMod", _author)


def test_lazy_author_resolves_once(monkeypatch):
    calls = []
    monkeypatch.setattr(scaf._nm, "resolve_author", lambda cli: calls.append(cli) or "Handle")
    get_author = scaf.lazy_author("Handle")
    assert get_author() == "Handle" and get_author() == "Handle"
    assert calls == ["Handle"]


def _run_main(monkeypatch, tmp_path, argv):
    project = tmp_path / "project"
    monkeypatch.setattr(scaf.h, "resolve_project_dir", lambda: project)
    monkeypatch.setattr(scaf.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(scaf._nm, "AUTHOR_CACHE", tmp_path / "author.txt")
    monkeypatch.setattr(scaf.sys, "argv", ["add_scaffold.py", *argv])
    return scaf.main()


def test_main_runs_pieces_in_documented_order_and_counts_skipped(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(scaf._nm, "find_dayz_tools", lambda: None)
    target = tmp_path / "project" / "workspace" / "MyMod"
    target.mkdir(parents=True)
    (target / "config.cpp").write_text("mine", encoding="utf-8")
    (target / "README.md").write_text("mine", encoding="utf-8")
    assert _run_main(monkeypatch, tmp_path, ["MyMod"]) == 0
    out = capsys.readouterr().out
    order = [out.index(s) for s in ("config.cpp present", "$PBOPREFIX$ written",
                                    "workbench/ skipped", "README.md present", "Skeleton folders created")]
    assert order == sorted(order)
    assert "2 piece(s) added, 2 already present, 1 skipped." in out


def test_main_nothing_to_add(monkeypatch, tmp_path, capsys, fake_tools):
    target = tmp_path / "project" / "workspace" / "MyMod"
    target.mkdir(parents=True)
    _run_main(monkeypatch, tmp_path, ["MyMod", "--author", "Tester"])
    capsys.readouterr()
    _run_main(monkeypatch, tmp_path, ["MyMod"])
    assert "Nothing to add" in capsys.readouterr().out


def test_main_refuses_missing_folder(monkeypatch, tmp_path):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, tmp_path, ["MyMod"])
    assert "does not exist" in str(exc.value.code)


def test_output_matches_new_mod_templates(tmp_path):
    target = tmp_path / "MyMod"
    target.mkdir()
    scaf.add_config(target, "MyMod", _author)
    expected = scaf._nm.CONFIG_CPP_TEMPLATE.substitute(modname="MyMod", author="Tester")
    assert (target / "config.cpp").read_text(encoding="utf-8") == expected


# --- junction piece ---------------------------------------------------------------

@pytest.fixture
def p_drive(monkeypatch, tmp_path):
    """A fake P:\\ plus a recorder in place of new-mod's make_dir_link."""
    drive = tmp_path / "P"
    drive.mkdir()
    monkeypatch.setattr(scaf, "P_DRIVE", drive)
    made = []

    def fake_link(src, dst):
        made.append((src, dst))
        return "junction"

    monkeypatch.setattr(scaf._nm, "make_dir_link", fake_link)
    return drive, made


def test_junction_created_when_absent(tmp_path, p_drive, capsys):
    drive, made = p_drive
    target = tmp_path / "workspace" / "MyMod"
    target.mkdir(parents=True)
    assert _run_piece("junction", target) == scaf.ADDED
    assert made == [(target, drive / "MyMod")]
    assert "junction ->" in capsys.readouterr().out


def test_junction_present_when_link_already_points_here(tmp_path, p_drive, monkeypatch):
    drive, made = p_drive
    target = tmp_path / "workspace" / "MyMod"
    target.mkdir(parents=True)
    (drive / "MyMod").mkdir()
    monkeypatch.setattr(scaf.h, "link_target", lambda p: target)
    monkeypatch.setattr(scaf.h, "paths_equal", lambda a, b: a == b)
    assert _run_piece("junction", target) == scaf.PRESENT
    assert made == []


def test_junction_refuses_real_folder(tmp_path, p_drive, monkeypatch):
    drive, made = p_drive
    (drive / "MyMod").mkdir()
    monkeypatch.setattr(scaf.h, "link_target", lambda p: None)
    with pytest.raises(SystemExit) as exc:
        _run_piece("junction", tmp_path / "workspace" / "MyMod")
    assert "real folder" in str(exc.value.code)
    assert made == []


def test_junction_refuses_link_to_elsewhere(tmp_path, p_drive, monkeypatch):
    drive, made = p_drive
    (drive / "MyMod").mkdir()
    monkeypatch.setattr(scaf.h, "link_target", lambda p: tmp_path / "other")
    monkeypatch.setattr(scaf.h, "paths_equal", lambda a, b: a == b)
    with pytest.raises(SystemExit) as exc:
        _run_piece("junction", tmp_path / "workspace" / "MyMod")
    assert "pointing at" in str(exc.value.code)
    assert made == []


def test_junction_creation_failure_exits(tmp_path, p_drive, monkeypatch):
    def boom(src, dst):
        raise OSError("access denied")

    monkeypatch.setattr(scaf._nm, "make_dir_link", boom)
    with pytest.raises(SystemExit) as exc:
        _run_piece("junction", tmp_path / "workspace" / "MyMod")
    assert "access denied" in str(exc.value.code)


def test_junction_not_part_of_all(monkeypatch, tmp_path, p_drive, fake_tools):
    _drive, made = p_drive
    (tmp_path / "project" / "workspace" / "MyMod").mkdir(parents=True)
    assert _run_main(monkeypatch, tmp_path, ["MyMod", "--author", "Tester"]) == 0
    assert made == []


def test_main_junction_piece_is_preflight_gated(monkeypatch, tmp_path, p_drive):
    (tmp_path / "project" / "workspace" / "MyMod").mkdir(parents=True)

    def gate():
        raise SystemExit(1)

    project = tmp_path / "project"
    monkeypatch.setattr(scaf.h, "resolve_project_dir", lambda: project)
    monkeypatch.setattr(scaf.h, "gate_on_preflight", gate)
    monkeypatch.setattr(scaf.sys, "argv", ["add_scaffold.py", "MyMod", "--piece", "junction"])
    with pytest.raises(SystemExit):
        scaf.main()
    assert p_drive[1] == []


def test_main_refuses_author_with_quote(monkeypatch, tmp_path):
    target = tmp_path / "project" / "workspace" / "MyMod"
    target.mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, tmp_path, ["MyMod", "--piece", "config", "--author", 'Bad"Name'])
    assert "double quote" in str(exc.value.code)
    assert not (target / "config.cpp").exists()


class _NoTty:
    def isatty(self):
        return False


@pytest.mark.parametrize("existing", [None, "config.cpp"])
def test_main_without_author_writes_nothing(monkeypatch, tmp_path, fake_tools, existing):
    """No flag, no cache, no TTY: exit before any piece is written (README still needs the author)."""
    target = tmp_path / "project" / "workspace" / "MyMod"
    target.mkdir(parents=True)
    if existing:
        (target / existing).write_text("mine", encoding="utf-8")
    before = _snapshot(target)
    monkeypatch.setattr(scaf._nm.sys, "stdin", _NoTty())
    monkeypatch.setattr(scaf._nm, "PROJECT_DIR", tmp_path)  # error message shows the cache path relative to it
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, tmp_path, ["MyMod"])
    assert "No author handle available" in str(exc.value.code)
    assert _snapshot(target) == before
    assert sorted(p.name for p in target.iterdir()) == ([existing] if existing else [])


def test_main_without_author_ok_when_no_author_piece_needed(monkeypatch, tmp_path, fake_tools):
    target = tmp_path / "project" / "workspace" / "MyMod"
    target.mkdir(parents=True)
    monkeypatch.setattr(scaf._nm.sys, "stdin", _NoTty())
    assert _run_main(monkeypatch, tmp_path, ["MyMod", "--piece", "prefix"]) == 0
    assert (target / "$PBOPREFIX$").exists()


def test_main_prints_native_separators(monkeypatch, tmp_path, capsys, fake_tools):
    (tmp_path / "project" / "workspace" / "MyMod").mkdir(parents=True)
    _run_main(monkeypatch, tmp_path, ["MyMod", "--author", "Tester"])
    sep = scaf.os.sep
    assert f"Scaffolding workspace{sep}MyMod{sep}\n" in capsys.readouterr().out


def test_main_from_mod_subfolder_uses_cached_project(monkeypatch, tmp_path, fake_tools):
    """Run from inside workspace/MyMod with no CLAUDE_PROJECT_DIR: the project
    comes from the /dayz-init cache found above cwd, not from cwd itself."""
    project = (tmp_path / "project").resolve()
    target = project / "workspace" / "MyMod"
    target.mkdir(parents=True)
    cache = project / ".claude" / "local-memory" / "dayz-current-project.txt"
    cache.parent.mkdir(parents=True)
    cache.write_text(str(project), encoding="utf-8")
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(target)
    monkeypatch.setattr(scaf.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(scaf.sys, "argv", ["add_scaffold.py", "MyMod", "--piece", "prefix"])
    assert scaf.main() == 0
    assert (target / "$PBOPREFIX$").is_file()
    assert not (target / "workspace").exists()


def test_main_junction_present_prints_link_summary(monkeypatch, tmp_path, p_drive, capsys):
    drive, made = p_drive
    target = tmp_path / "project" / "workspace" / "MyMod"
    target.mkdir(parents=True)
    (drive / "MyMod").mkdir()
    monkeypatch.setattr(scaf.h, "link_target", lambda p: target)
    monkeypatch.setattr(scaf.h, "paths_equal", lambda a, b: a == b)
    assert _run_main(monkeypatch, tmp_path, ["MyMod", "--piece", "junction"]) == 0
    out = capsys.readouterr().out
    assert "link already in place" in out
    assert "fully scaffolded" not in out
    assert made == []


def test_main_junction_created_prints_link_summary(monkeypatch, tmp_path, p_drive, capsys):
    (tmp_path / "project" / "workspace" / "MyMod").mkdir(parents=True)
    assert _run_main(monkeypatch, tmp_path, ["MyMod", "--piece", "junction"]) == 0
    out = capsys.readouterr().out
    assert "link created" in out
    assert "fully scaffolded" not in out


# --- exit code and $PBOPREFIX$ content ---------------------------------------------

def test_main_single_piece_skipped_exits_nonzero(monkeypatch, tmp_path, capsys):
    """--piece workbench without DayZ Tools writes nothing, so the exit must fail."""
    monkeypatch.setattr(scaf._nm, "find_dayz_tools", lambda: None)
    target = tmp_path / "project" / "workspace" / "MyMod"
    target.mkdir(parents=True)
    assert _run_main(monkeypatch, tmp_path, ["MyMod", "--piece", "workbench"]) == 1
    assert "workbench was not written" in capsys.readouterr().out
    assert not (target / "workbench").exists()


def test_main_all_with_a_skipped_piece_still_exits_zero(monkeypatch, tmp_path):
    """`all` reports skipped pieces in its summary; the other pieces were written."""
    monkeypatch.setattr(scaf._nm, "find_dayz_tools", lambda: None)
    (tmp_path / "project" / "workspace" / "MyMod").mkdir(parents=True)
    assert _run_main(monkeypatch, tmp_path, ["MyMod", "--author", "Tester"]) == 0


def test_existing_prefix_with_other_content_warns_build_will_refuse(tmp_path, capsys):
    target = tmp_path / "MyMod"
    target.mkdir()
    (target / "$PBOPREFIX$").write_text("OtherMod", encoding="utf-8")
    assert scaf.add_prefix(target, "MyMod") == scaf.WRONG
    out = capsys.readouterr().out
    assert scaf.WARN in out and "'OtherMod'" in out and "/dayz-build-pbo will refuse" in out
    assert "[SKIP]" not in out
    assert (target / "$PBOPREFIX$").read_text(encoding="utf-8") == "OtherMod"


def test_existing_prefix_matching_after_bom_and_newline_is_plain_skip(tmp_path, capsys):
    """Same normalisation as /dayz-build-pbo's gate: BOM and trailing newline are fine."""
    target = tmp_path / "MyMod"
    target.mkdir()
    (target / "$PBOPREFIX$").write_bytes(b"\xef\xbb\xbfMyMod\r\n")
    assert scaf.add_prefix(target, "MyMod") == scaf.PRESENT
    out = capsys.readouterr().out
    assert "$PBOPREFIX$ present" in out and scaf.WARN not in out


def test_main_single_prefix_piece_left_wrong_exits_nonzero(monkeypatch, tmp_path, capsys):
    """--piece prefix on a $PBOPREFIX$ /dayz-build-pbo will refuse must not report success."""
    target = tmp_path / "project" / "workspace" / "MyMod"
    target.mkdir(parents=True)
    (target / "$PBOPREFIX$").write_text("OtherMod", encoding="utf-8")
    assert _run_main(monkeypatch, tmp_path, ["MyMod", "--piece", "prefix"]) == 1
    out = capsys.readouterr().out
    assert f"{scaf.FAIL} prefix is present but wrong" in out
    assert "1 need fixing by hand." in out
    assert "fully scaffolded" not in out
    assert (target / "$PBOPREFIX$").read_text(encoding="utf-8") == "OtherMod"


def test_main_all_with_wrong_prefix_warns_in_summary(monkeypatch, tmp_path, capsys, fake_tools):
    """`all` on a fully present folder whose prefix is wrong is not 'fully scaffolded'."""
    target = tmp_path / "project" / "workspace" / "MyMod"
    target.mkdir(parents=True)
    _run_main(monkeypatch, tmp_path, ["MyMod", "--author", "Tester"])
    (target / "$PBOPREFIX$").write_text("OtherMod", encoding="utf-8")
    capsys.readouterr()
    assert _run_main(monkeypatch, tmp_path, ["MyMod"]) == 0
    out = capsys.readouterr().out
    assert "fully scaffolded" not in out
    assert f"{scaf.WARN} 0 piece(s) added, 4 already present, 0 skipped, 1 need fixing by hand." in out


def test_main_all_summary_tag_is_warn_when_a_piece_was_skipped(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(scaf._nm, "find_dayz_tools", lambda: None)
    (tmp_path / "project" / "workspace" / "MyMod").mkdir(parents=True)
    _run_main(monkeypatch, tmp_path, ["MyMod", "--author", "Tester"])
    out = capsys.readouterr().out
    assert f"{scaf.WARN} 4 piece(s) added, 0 already present, 1 skipped." in out
    assert f"{scaf.OK} 4 piece(s) added" not in out


def test_main_all_summary_tag_is_ok_when_everything_added(monkeypatch, tmp_path, capsys, fake_tools):
    (tmp_path / "project" / "workspace" / "MyMod").mkdir(parents=True)
    _run_main(monkeypatch, tmp_path, ["MyMod", "--author", "Tester"])
    assert f"{scaf.OK} 5 piece(s) added, 0 already present, 0 skipped." in capsys.readouterr().out
