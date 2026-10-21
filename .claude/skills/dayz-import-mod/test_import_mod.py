"""Tests for import_mod.py: source validation, mod naming, non-TTY refusals."""
from __future__ import annotations

import importlib.util
import io
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_import_mod_under_test", HERE / "import_mod.py")
imp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(imp)


class _NoTTY(io.StringIO):
    def isatty(self):
        return False


@pytest.fixture
def workspace(monkeypatch, tmp_path):
    ws = tmp_path / "project" / "workspace"
    ws.mkdir(parents=True)
    monkeypatch.setattr(imp, "WORKSPACE", ws)
    return ws


# --- resolve_source -----------------------------------------------------------

@pytest.mark.parametrize("raw", ["\\\\server\\share\\MyMod", "//server/share/MyMod"])
def test_unc_paths_refused(raw, workspace):
    with pytest.raises(SystemExit) as exc:
        imp.resolve_source(raw)
    assert "UNC" in str(exc.value.code)


def test_missing_source_refused(tmp_path, workspace):
    with pytest.raises(SystemExit) as exc:
        imp.resolve_source(str(tmp_path / "nope"))
    assert "does not exist" in str(exc.value.code)


def test_file_source_refused(tmp_path, workspace):
    f = tmp_path / "mod.zip"
    f.write_bytes(b"")
    with pytest.raises(SystemExit) as exc:
        imp.resolve_source(str(f))
    assert "not a directory" in str(exc.value.code)


def test_source_inside_workspace_refused(workspace):
    inside = workspace / "Already"
    inside.mkdir()
    with pytest.raises(SystemExit) as exc:
        imp.resolve_source(str(inside))
    assert "inside this project's workspace" in str(exc.value.code)
    assert "--piece junction" in str(exc.value.code)


def test_outside_source_accepted(tmp_path, workspace):
    src = tmp_path / "repos" / "MyMod"
    src.mkdir(parents=True)
    assert imp.resolve_source(str(src)) == src.resolve()


def test_missing_source_flag_refused_without_tty(monkeypatch, workspace):
    monkeypatch.setattr(imp.sys, "stdin", _NoTTY())
    with pytest.raises(SystemExit) as exc:
        imp.resolve_source(None)
    assert "--source is required" in str(exc.value.code)


# --- derive_modname -------------------------------------------------------------

def test_basename_used_when_valid():
    assert imp.derive_modname(Path("C:/repos/MyMod"), None) == "MyMod"


@pytest.mark.parametrize("basename", ["My Mod", "my-mod", "1stMod", "Mod.v2"])
def test_invalid_basename_asks_for_name(basename):
    with pytest.raises(SystemExit) as exc:
        imp.derive_modname(Path("C:/repos") / basename, None)
    assert "--name" in str(exc.value.code)


def test_override_wins_over_basename():
    assert imp.derive_modname(Path("C:/repos/my-mod"), "MyMod") == "MyMod"


def test_invalid_override_refused():
    with pytest.raises(SystemExit) as exc:
        imp.derive_modname(Path("C:/repos/MyMod"), "bad name")
    assert "Invalid mod name" in str(exc.value.code)


# --- missing pieces and the scaffold decision ------------------------------------

def test_detect_missing_pieces(tmp_path):
    (tmp_path / "config.cpp").write_text("", encoding="utf-8")
    assert [key for key, _rel, _why in imp.detect_missing_pieces(tmp_path)] == ["prefix", "workbench"]


def test_non_tty_without_flag_refused():
    missing = [("prefix", "$PBOPREFIX$", "why")]
    with pytest.raises(SystemExit) as exc:
        imp.require_scaffold_decision(missing, scaffold=False, no_scaffold=False, interactive=False)
    assert "--scaffold" in str(exc.value.code) and "$PBOPREFIX$" in str(exc.value.code)


@pytest.mark.parametrize(
    "scaffold, no_scaffold, interactive",
    [(True, False, False), (False, True, False), (False, False, True)],
)
def test_explicit_decision_or_tty_passes(scaffold, no_scaffold, interactive):
    imp.require_scaffold_decision([("prefix", "$PBOPREFIX$", "why")], scaffold, no_scaffold, interactive)


def test_nothing_missing_never_refuses():
    imp.require_scaffold_decision([], scaffold=False, no_scaffold=False, interactive=False)


def test_existing_workspace_entry_refused(workspace):
    (workspace / "MyMod").mkdir()
    with pytest.raises(SystemExit) as exc:
        imp.check_workspace_target(workspace / "MyMod")
    assert "already exists" in str(exc.value.code)


# --- add_missing_pieces (runs after the links exist) ---------------------------------

ALL_MISSING = list(imp.SCAFFOLD_CHECKS)


def test_scaffold_writes_in_process_without_rerunning_preflight(tmp_path, monkeypatch):
    monkeypatch.setattr(imp.h, "gate_on_preflight", lambda: pytest.fail("preflight must not re-run"))
    monkeypatch.setattr(imp._scaffold._nm, "find_dayz_tools", lambda: None)
    monkeypatch.setattr(imp._scaffold._nm, "resolve_author", lambda cli: "Tester")
    rc = imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING, scaffold=True, no_scaffold=False)
    assert rc == 0
    assert (tmp_path / "config.cpp").is_file() and (tmp_path / "$PBOPREFIX$").is_file()


def test_no_scaffold_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(imp._scaffold, "add_piece", lambda *a: pytest.fail("must not write"))
    assert imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING, scaffold=False, no_scaffold=True) == 0


def test_declined_prompt_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(imp, "prompt_yn", lambda prompt: False)
    monkeypatch.setattr(imp._scaffold, "add_piece", lambda *a: pytest.fail("must not write"))
    assert imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING, scaffold=False, no_scaffold=False) == 0


def test_failed_piece_reports_retry_and_keeps_going(tmp_path, monkeypatch, capsys):
    def no_author(cli):
        raise SystemExit("[FAIL] No author handle available.")

    monkeypatch.setattr(imp._scaffold._nm, "resolve_author", no_author)
    monkeypatch.setattr(imp._scaffold._nm, "find_dayz_tools", lambda: None)
    rc = imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING, scaffold=True, no_scaffold=False)
    out = capsys.readouterr().out
    assert rc == 1
    assert "No author handle available" in out
    assert "Retry: /dayz-add-scaffold MyMod --piece config" in out
    assert "/dayz-clean-workspace --mod MyMod" in out
    assert (tmp_path / "$PBOPREFIX$").is_file()  # later pieces still written


def test_os_error_while_writing_is_reported(tmp_path, monkeypatch, capsys):
    def boom(*a):
        raise PermissionError("Access is denied")

    monkeypatch.setattr(imp._scaffold, "add_piece", boom)
    rc = imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING[1:2], scaffold=True, no_scaffold=False)
    assert rc == 1
    assert "Access is denied" in capsys.readouterr().out


def test_author_flag_reaches_resolve_author(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(imp._scaffold._nm, "find_dayz_tools", lambda: None)
    monkeypatch.setattr(imp._scaffold._nm, "resolve_author", lambda cli: seen.append(cli) or cli)
    rc = imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING, scaffold=True, no_scaffold=False, author="Handle")
    assert rc == 0
    assert seen == ["Handle"]
    assert 'author = "Handle"' in (tmp_path / "config.cpp").read_text(encoding="utf-8")
