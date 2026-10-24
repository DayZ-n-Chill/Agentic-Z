"""Large drift: a clone hundreds of template files behind upstream.

compute_drift must use a fixed number of git processes (not about three per
file), so the SessionStart hook finishes inside its timeout, and
stage_and_commit must pass its path list on stdin, not the command line, which
Windows caps at about 32,000 characters.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "agentic_z_update_large", Path(__file__).resolve().parent / "update.py"
)
update = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(update)
S = update.FileStatus

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

N_FILES = 400
SETTINGS = Path(__file__).resolve().parents[2] / "settings.json"


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def _init(root: Path) -> None:
    _git(root, "init", "-q")
    for key, val in [("user.name", "t"), ("user.email", "t@example.com"),
                     ("commit.gpgsign", "false"), ("core.autocrlf", "false"),
                     ("core.hooksPath", ".no-hooks")]:
        _git(root, "config", key, val)


def _hook_timeout() -> int:
    hooks = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
    return next(h["timeout"] for block in hooks for h in block["hooks"]
                if "agentic-z-update" in h["command"])


def _fast_import_lines(changes: dict[str, str | None]) -> list[str]:
    """fast-import file commands: content to write, or None to delete."""
    lines = []
    for path, text in changes.items():
        if text is None:
            lines.append(f"D {path}")
        else:
            data = text.encode("utf-8")
            lines += [f"M 100644 inline {path}", f"data {len(data)}", text]
    return lines


@pytest.fixture(scope="module")
def behind_repo(tmp_path_factory):
    """A clone whose upstream/main changed N_FILES docs, deleted 20 and added 30;
    the clone edited 50 of the changed files itself.

    Both commits are written with one `git fast-import` (a single pack) instead
    of hundreds of loose objects, which keeps the setup to about a second.
    """
    root = tmp_path_factory.mktemp("behind")
    _init(root)
    base = {f"docs/page-{i:04}.md": f"v0 {i}\n" for i in range(N_FILES + 20)}
    up = {f"docs/page-{i:04}.md": f"v1 {i}\n" for i in range(N_FILES)}
    up.update({f"docs/page-{i:04}.md": None for i in range(N_FILES, N_FILES + 20)})
    up.update({f"docs/added-{i:02}.md": "new\n" for i in range(30)})
    stream = [
        "commit refs/heads/base", "committer t <t@example.com> 0 +0000", "data 8", "baseline",
        *_fast_import_lines(base), "",
        "commit refs/remotes/upstream/main", "committer t <t@example.com> 1 +0000", "data 8",
        "upstream", "from refs/heads/base", *_fast_import_lines(up), "",
    ]
    # Bytes, not text: a Windows text pipe turns \n into \r\n and breaks the data counts.
    subprocess.run(["git", "fast-import", "--quiet"], cwd=root, check=True,
                   input=("\n".join(stream) + "\n").encode("utf-8"))
    _git(root, "checkout", "-q", "base")
    for i in range(50):
        (root / "docs" / f"page-{i:04}.md").write_text(f"mine {i}\n", encoding="utf-8")
    return root, _git(root, "rev-parse", "base").strip()


@pytest.fixture
def behind(behind_repo, monkeypatch):
    monkeypatch.chdir(behind_repo[0])
    return behind_repo


def _count_git_calls(monkeypatch) -> list:
    calls = []
    real = update.subprocess.run

    def spy(cmd, *a, **k):
        if cmd and cmd[0] == "git":
            calls.append(cmd)
        return real(cmd, *a, **k)

    monkeypatch.setattr(update.subprocess, "run", spy)
    return calls


def test_large_drift_uses_a_fixed_number_of_git_calls(behind, monkeypatch):
    _root, baseline = behind
    calls = _count_git_calls(monkeypatch)
    drift = update.compute_drift(baseline, "upstream/main")
    # 2 diffs + status for candidates, 2 ls-tree, 1 hash-object; was ~3 per file.
    assert len(calls) <= 8, [c[:3] for c in calls]
    counts = {st: sum(1 for s in drift.values() if s == st) for st in set(drift.values())}
    assert counts == {S.CONFLICT: 50, S.SAFE_OVERWRITE: N_FILES - 50,
                      S.DELETED_CLEAN: 20, S.NEW: 30}


def test_quiet_check_on_large_drift_prints_nudge_inside_hook_timeout(behind, monkeypatch, capsys):
    root, baseline = behind
    (root / ".claude").mkdir()
    (root / ".claude" / ".upstream-baseline").write_text(baseline + "\n", encoding="utf-8")
    monkeypatch.setattr(update, "_QUIET", False)
    monkeypatch.setattr(update, "ensure_upstream", lambda: True)
    monkeypatch.setattr(update, "fetch_upstream", lambda: True)
    monkeypatch.setattr(update, "search_index_update_available", lambda: None)
    monkeypatch.setattr(sys, "argv", ["update.py", "--check", "--quiet"])
    start = time.monotonic()
    assert update.main() == 0
    elapsed = time.monotonic() - start
    out = capsys.readouterr().out.strip()
    assert out == (f"agentic-z: {N_FILES + 50} template change(s), 50 conflict(s) available. "
                   "Run /agentic-z-update.")
    # The hook also spends time on git fetch and the 5 s release check, so the
    # classification itself must leave most of the budget.
    assert elapsed < _hook_timeout() / 2, f"{elapsed:.1f}s"


def test_working_tree_ids_fall_back_per_file_when_batch_fails(behind, monkeypatch):
    paths = ["docs/page-0000.md", "docs/page-0001.md", "docs/missing.md"]
    expected = update.working_tree_object_ids(paths)
    assert set(expected) == {"docs/page-0000.md", "docs/page-0001.md"}
    real = update.subprocess.run

    def batch_fails(cmd, *a, **k):
        if "--stdin-paths" in cmd:
            return subprocess.CompletedProcess(cmd, 128, "", "fatal: could not open")
        return real(cmd, *a, **k)

    monkeypatch.setattr(update.subprocess, "run", batch_fails)
    assert update.working_tree_object_ids(paths) == expected


# ---------- stage_and_commit with a path list longer than a command line ----------

def test_commit_of_hundreds_of_long_paths_stays_off_the_command_line(tmp_path, monkeypatch):
    _init(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    names = [f"docs/{'long-template-file-name-' * 3}{i:04}.md" for i in range(600)]
    assert sum(len(n) + 1 for n in names) > 32_767  # past the Windows limit
    for n in names:
        (tmp_path / n).write_text("old\n", encoding="utf-8")
    (tmp_path / "docs" / "gone.md").write_text("x\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    for n in names:
        (tmp_path / n).write_text("upstream\n", encoding="utf-8")
    (tmp_path / "docs" / "gone.md").unlink()  # an applied deleted-clean path

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(update, "_QUIET", True)
    calls = _count_git_calls(monkeypatch)
    assert update.stage_and_commit([*names, "docs/gone.md"], "d" * 40) is True
    assert max(len(" ".join(c)) for c in calls) < 1000
    committed = _git(tmp_path, "show", "--name-only", "--format=", "HEAD").split()
    assert sorted(committed) == sorted([*names, "docs/gone.md"])
    assert _git(tmp_path, "status", "--porcelain") == ""


def test_commit_treats_glob_characters_in_names_literally(tmp_path, monkeypatch):
    """As a pathspec, docs/[a].md also matches docs/a.md; the update must not
    commit the user's unrelated edit to docs/a.md."""
    _init(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "[a].md").write_text("old\n", encoding="utf-8")
    (tmp_path / "docs" / "a.md").write_text("old\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    (tmp_path / "docs" / "[a].md").write_text("upstream\n", encoding="utf-8")
    (tmp_path / "docs" / "a.md").write_text("user edit\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(update, "_QUIET", True)
    assert update.stage_and_commit(["docs/[a].md"], "d" * 40) is True
    assert _git(tmp_path, "show", "--name-only", "--format=", "HEAD").split() == ["docs/[a].md"]
    assert _git(tmp_path, "status", "--porcelain").strip() == "M docs/a.md"


def test_no_commit_when_applied_paths_match_but_other_files_are_staged(tmp_path, monkeypatch):
    _init(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("same\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("v1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    head = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "notes.txt").write_text("staged by the user\n", encoding="utf-8")
    _git(tmp_path, "add", "notes.txt")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(update, "_QUIET", True)
    assert update.stage_and_commit(["docs/a.md"], "d" * 40) is True
    assert _git(tmp_path, "rev-parse", "HEAD") == head
    assert _git(tmp_path, "diff", "--cached", "--name-only").split() == ["notes.txt"]
