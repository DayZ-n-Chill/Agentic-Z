"""Tests for apply.py and the --apply / --apply --dry-run modes of sync.py.

Uses the fake repo builder from test_docs_sync.py, so the real wiki is never written.
"""
from __future__ import annotations

import builtins
import errno
import importlib.util
import io
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module


apply = _load("docs_sync_apply_under_test", HERE / "apply.py")
t = _load("docs_sync_test_helpers", HERE / "test_docs_sync.py")
sync = t.sync


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "REPO_ROOT", tmp_path)
    monkeypatch.delenv(sync.WIKI_ENV, raising=False)  # the fixture's own wiki/ folder is the wiki
    return t.build_repo(tmp_path)


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def patch_open(monkeypatch, fake):
    # Path.write_text goes through io.open and the builtin open is the same
    # function, so patch both names to catch every way a file is opened.
    monkeypatch.setattr(io, "open", fake)
    monkeypatch.setattr(builtins, "open", fake)


# ---------------------------------------------------------------- apply_to_text

def test_apply_to_text_replaces_spans_right_to_left_on_one_line():
    text = "a\nhas 3 agents and 7 skills\nz"
    fixes = [(2, (4, 5, "30")), (2, (17, 18, "44"))]
    assert apply.apply_to_text(text, fixes) == "a\nhas 30 agents and 44 skills\nz"


def test_apply_to_text_keeps_crlf_line_endings():
    text = "x 3 y\r\nz 4\r\n"
    assert apply.apply_to_text(text, [(1, (2, 3, "5")), (2, (2, 3, "6"))]) == "x 5 y\r\nz 6\r\n"


# ---------------------------------------------------------------- apply_fixes

def test_apply_fixes_ignores_unfixable_problems(repo, capsys):
    problems = [sync.Problem(sync.GUIDE, 1, "names agent `x`, which does not exist")]
    before = snapshot(repo)
    assert apply.apply_fixes(repo, problems) == 0
    assert snapshot(repo) == before
    assert "Nothing to fix" in capsys.readouterr().out


def test_dry_run_writes_nothing_and_prints_each_change(repo, capsys):
    t.edit(repo, sync.GUIDE, "has 2 agents", "has 4 agents")
    before = snapshot(repo)
    assert sync.main(["--apply", "--dry-run"]) == 0
    assert snapshot(repo) == before
    out = capsys.readouterr().out
    assert "wiki/src/content/guide.md:11: would change 4 -> 2" in out
    assert "Would apply 1 fix(es) in 1 file(s)." in out


def test_dry_run_tells_apart_two_fixes_on_one_line(repo, capsys):
    t.edit(repo, sync.GUIDE, "includes 2 agents, 2 skills", "includes 4 agents, 4 skills")
    assert sync.main(["--apply", "--dry-run"]) == 0
    out = capsys.readouterr().out
    line = (repo / sync.GUIDE).read_text(encoding="utf-8").split("\n")[2]
    first, second = line.index("4 agents") + 1, line.index("4 skills") + 1
    assert f"guide.md:3: would change 4 -> 2 (column {first})" in out
    assert f"guide.md:3: would change 4 -> 2 (column {second})" in out


def test_apply_fixes_counts_in_every_file_and_nothing_else(repo, capsys):
    t.edit(repo, sync.GUIDE, "includes 2 agents, 2 skills", "includes 3 agents, 9 skills")
    t.edit(repo, sync.TEAM, "and two topic files of", "and four topic files of")
    t.edit(repo, sync.APP_JSX, "['6', 'items graded A+']", "['7', 'items graded A+']")
    t.edit(repo, sync.APP_JSX, "['3', 'hooks']", "['9', 'hooks']")  # 3 hook scripts in hooks/
    before = snapshot(repo)

    assert sync.main(["--apply"]) == 0
    after = snapshot(repo)
    changed = {k for k in after if after[k] != before[k]}
    assert changed == {sync.GUIDE, sync.TEAM, sync.APP_JSX}
    assert "includes 2 agents, 2 skills" in (repo / sync.GUIDE).read_text(encoding="utf-8")
    assert "and two topic files of" in (repo / sync.TEAM).read_text(encoding="utf-8")
    app = (repo / sync.APP_JSX).read_text(encoding="utf-8")
    assert "['6', 'items graded A+']" in app and "['3', 'hooks']" in app
    assert "Applied 5 fix(es) in 3 file(s)." in capsys.readouterr().out
    assert sync.main(["--check"]) == 0


def test_apply_keeps_the_file_line_endings(repo):
    path = repo / sync.TEAM
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n").replace(b"the 2 agents and", b"the 6 agents and"))
    assert sync.main(["--apply"]) == 0
    data = path.read_bytes()
    assert b"the 2 agents and" in data and b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b"")


def test_apply_exits_1_and_reports_what_it_cannot_fix(repo, capsys):
    t.edit(repo, sync.GUIDE, "has 2 agents", "has 4 agents")
    t.edit(repo, sync.SKILLS_TABLE, "| `/bar` | Bar. |\n", "")
    assert sync.main(["--apply"]) == 1
    out = capsys.readouterr().out
    assert "1 problem(s) need a hand edit:" in out
    assert "skill `bar` exists but is not listed in the skills table" in out
    assert "has 2 agents" in (repo / sync.GUIDE).read_text(encoding="utf-8")  # the count was still fixed
    assert sync.main(["--check"]) == 1


def test_dry_run_exits_1_when_hand_edits_remain(repo):
    t.edit(repo, sync.TEAM, "| `foo` | B | A+ |\n", "")
    before = snapshot(repo)
    assert sync.main(["--apply", "--dry-run"]) == 1
    assert snapshot(repo) == before


def test_apply_with_nothing_wrong_writes_nothing(repo, capsys):
    before = snapshot(repo)
    assert sync.main(["--apply"]) == 0
    assert snapshot(repo) == before
    assert "Nothing to fix" in capsys.readouterr().out


def test_write_error_exits_1(repo, monkeypatch, capsys):
    t.edit(repo, sync.GUIDE, "has 2 agents", "has 4 agents")

    real_open = io.open

    def refuse(file, mode="r", *args, **kwargs):
        if "w" in mode:
            raise PermissionError("read-only")
        return real_open(file, mode, *args, **kwargs)

    patch_open(monkeypatch, refuse)
    assert sync.main(["--apply"]) == 1
    assert "could not write the wiki" in capsys.readouterr().err


def test_write_error_partway_leaves_no_file_changed(repo, monkeypatch, capsys):
    # Fixes in three files; the second write fails. The first file must be put back.
    t.edit(repo, sync.GUIDE, "has 2 agents", "has 4 agents")
    t.edit(repo, sync.TEAM, "provides 2 slash commands", "provides 5 slash commands")
    t.edit(repo, sync.APP_JSX, "['2', 'agents']", "['8', 'agents']")
    before = snapshot(repo)
    real_open = io.open
    calls = []

    def fail_second(file, mode="r", *args, **kwargs):
        if "w" in mode:
            calls.append(file)
            if len(calls) == 2:
                raise PermissionError("read-only")
        return real_open(file, mode, *args, **kwargs)

    patch_open(monkeypatch, fail_second)
    assert sync.main(["--apply"]) == 1
    assert snapshot(repo) == before
    captured = capsys.readouterr()
    assert "could not write the wiki" in captured.err and "changed" not in captured.out


def _three_file_fixes(repo):
    t.edit(repo, sync.GUIDE, "has 2 agents", "has 4 agents")
    t.edit(repo, sync.TEAM, "provides 2 slash commands", "provides 5 slash commands")
    t.edit(repo, sync.APP_JSX, "['2', 'agents']", "['8', 'agents']")


def _fail_on_writes(monkeypatch, failures: dict):
    """Open files as usual, but raise failures[n] on the n-th open for writing."""
    real_open = io.open
    calls = []

    def fake(file, mode="r", *args, **kwargs):
        if "w" in mode:
            calls.append(file)
            if len(calls) in failures:
                raise failures[len(calls)]
        return real_open(file, mode, *args, **kwargs)

    patch_open(monkeypatch, fake)
    return calls


def test_ctrl_c_between_writes_leaves_no_file_changed(repo, monkeypatch, capsys):
    # Ctrl+C lands on the second write; the first file must still be put back.
    _three_file_fixes(repo)
    before = snapshot(repo)
    _fail_on_writes(monkeypatch, {2: KeyboardInterrupt()})
    assert sync.main(["--apply"]) == 1
    monkeypatch.undo()
    assert snapshot(repo) == before
    captured = capsys.readouterr()
    assert "stopped; the wiki files were put back" in captured.err and "Traceback" not in captured.err


def test_ctrl_c_after_the_last_write_says_the_fixes_were_written(repo, monkeypatch, capsys):
    # Ctrl+C lands while the changes are printed, after every write finished:
    # the fixes stay in place and the message must not claim they were put back.
    _three_file_fixes(repo)
    before = snapshot(repo)
    real_print = builtins.print

    def interrupt_printout(*args, **kwargs):
        if args and ": changed " in str(args[0]):
            raise KeyboardInterrupt
        real_print(*args, **kwargs)

    monkeypatch.setattr(builtins, "print", interrupt_printout)
    assert sync.main(["--apply"]) == 1
    monkeypatch.setattr(builtins, "print", real_print)  # not undo(): that would drop the fake repo root too
    assert snapshot(repo) != before
    assert not any(p.fix for p in sync.run_checks()[1])
    err = capsys.readouterr().err
    assert "stopped after writing the fixes" in err and "put back" not in err and "Traceback" not in err


def test_change_list_prints_fixes_on_one_line_left_to_right(tmp_path, capsys):
    # Problems may arrive out of column order; the change list is sorted by line, then column.
    (tmp_path / "page.md").write_text("has 3 agents and 7 skills\n", encoding="utf-8")
    problems = [
        sync.Problem("page.md", 1, "skills", (17, 18, "44"), "7"),
        sync.Problem("page.md", 1, "agents", (4, 5, "30"), "3"),
    ]
    apply.apply_fixes(tmp_path, problems, dry_run=True)
    out = capsys.readouterr().out.splitlines()
    assert out[:2] == ["page.md:1: would change 3 -> 30 (column 5)", "page.md:1: would change 7 -> 44 (column 18)"]


def test_ctrl_c_during_the_check_says_nothing_was_written(repo, monkeypatch, capsys):
    def interrupted():
        raise KeyboardInterrupt
    monkeypatch.setattr(sync, "run_checks", interrupted)
    before = snapshot(repo)
    assert sync.main(["--apply"]) == 1
    assert snapshot(repo) == before
    err = capsys.readouterr().err
    assert "stopped; nothing was written" in err and "Traceback" not in err


def test_file_edited_between_check_and_write_is_not_fixed(repo, monkeypatch, capsys):
    # An editor saves the page after the check, shifting the text the fix offsets point at.
    t.edit(repo, sync.GUIDE, "has 2 agents", "has 4 agents")
    problems = sync.run_checks()[1]
    monkeypatch.setattr(sync, "run_checks", lambda: (None, problems))
    t.edit(repo, sync.GUIDE, "has 4 agents", "now has 4 agents")
    before = snapshot(repo)
    assert sync.main(["--apply"]) == 1
    assert snapshot(repo) == before
    assert f"{sync.GUIDE} changed since the check; run again" in capsys.readouterr().err


def test_unreadable_wiki_file_during_apply_is_a_read_error(repo, monkeypatch, capsys):
    # apply.py re-reads each file it fixes; a failed read is not a failed write.
    t.edit(repo, sync.GUIDE, "has 2 agents", "has 4 agents")
    problems = sync.run_checks()[1]
    monkeypatch.setattr(sync, "run_checks", lambda: (None, problems))
    real_open = io.open

    def refuse_read(file, mode="r", *args, **kwargs):
        if "w" not in mode and Path(file) == repo / sync.GUIDE:
            raise PermissionError(13, "Permission denied")
        return real_open(file, mode, *args, **kwargs)

    before = snapshot(repo)
    patch_open(monkeypatch, refuse_read)
    assert sync.main(["--apply"]) == 1
    monkeypatch.undo()
    assert snapshot(repo) == before
    err = capsys.readouterr().err
    assert f"could not read {sync.GUIDE}: Permission denied" in err and "could not write" not in err


def test_failed_put_back_keeps_the_first_error(repo, monkeypatch):
    # The second write fails, then putting the first file back (the third write) fails too.
    # The error raised is still the first one, with the put-back failure noted on it.
    _three_file_fixes(repo)
    problems = sync.run_checks()[1]
    _fail_on_writes(monkeypatch, {2: PermissionError("read-only"), 3: OSError("disk gone")})
    with pytest.raises(PermissionError, match="read-only") as exc:
        apply.apply_fixes(repo, problems)
    monkeypatch.undo()
    assert any("could not put back" in n and "disk gone" in n for n in exc.value.__notes__)


def test_failed_put_back_is_shown_on_the_command_line(repo, monkeypatch, capsys):
    # Same failure through main(): the user must be told which file was not put back.
    _three_file_fixes(repo)
    _fail_on_writes(monkeypatch, {2: PermissionError("read-only"), 3: OSError("disk gone")})
    assert sync.main(["--apply"]) == 1
    monkeypatch.undo()
    err = capsys.readouterr().err
    assert "could not write the wiki: read-only" in err
    # The first file written (and so the one put back) is the first in the fix order.
    first = repo / sync.APP_JSX
    assert f"could not put back {first}: disk gone" in err


class _DiskFullWriter:
    """A file opened for writing that writes half its text, then fails like a full disk."""

    def __init__(self, f):
        self._f = f

    def write(self, text):
        self._f.write(text[: len(text) // 2])
        self._f.flush()
        raise OSError(errno.ENOSPC, "No space left on device")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._f.close()
        return False

    def __getattr__(self, name):
        return getattr(self._f, name)


@pytest.mark.parametrize("failing_write", [1, 2])
def test_write_failing_after_the_file_is_open_leaves_every_file_unchanged(repo, monkeypatch, capsys, failing_write):
    # The disk fills up in the middle of a write, after the file was opened and
    # half the text went out. Neither the file being written (1st write) nor the
    # file already fixed before it (2nd write) may end up empty, cut short or fixed.
    t.edit(repo, sync.GUIDE, "has 2 agents", "has 4 agents")
    t.edit(repo, sync.TEAM, "provides 2 slash commands", "provides 5 slash commands")
    t.edit(repo, sync.APP_JSX, "['2', 'agents']", "['8', 'agents']")
    before = snapshot(repo)
    real_open = io.open
    calls = []

    def disk_full(file, mode="r", *args, **kwargs):
        f = real_open(file, mode, *args, **kwargs)
        if "w" in mode:
            calls.append(file)
            if len(calls) == failing_write:
                return _DiskFullWriter(f)
        return f

    patch_open(monkeypatch, disk_full)
    assert sync.main(["--apply"]) == 1
    monkeypatch.undo()
    assert len(calls) >= failing_write
    assert snapshot(repo) == before  # same bytes, and no temporary file left behind
    captured = capsys.readouterr()
    assert "could not write the wiki" in captured.err and "changed" not in captured.out


@pytest.mark.parametrize("what", t.SOURCES)
@pytest.mark.parametrize("args", [["--apply"], ["--apply", "--dry-run"]])
def test_apply_writes_nothing_when_a_source_is_missing_or_unreadable(repo, capsys, what, args):
    # Wiki counts that are wrong only if the missing source read as 0.
    t.edit(repo, sync.GUIDE, "has 2 agents", "has 4 agents")
    message = t.remove_source(repo, what)
    before = snapshot(repo)
    assert sync.main(args) == 1
    assert snapshot(repo) == before
    captured = capsys.readouterr()
    assert message in captured.err and "changed" not in captured.out


# ---------------------------------------------------------------- real process

def test_cli_apply_and_dry_run(tmp_path):
    root = t.build_repo(tmp_path, with_scripts=True)
    t.edit(root, sync.GUIDE, "has 2 agents", "has 4 agents")
    r = t.run_cli(root, "--apply", "--dry-run")
    assert r.returncode == 0 and "would change 4 -> 2" in r.stdout
    assert "has 4 agents" in (root / sync.GUIDE).read_text(encoding="utf-8")
    r = t.run_cli(root, "--apply")
    assert r.returncode == 0 and "changed 4 -> 2" in r.stdout
    assert t.run_cli(root, "--check").returncode == 0
