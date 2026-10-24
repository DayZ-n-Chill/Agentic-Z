"""Tests for check.py: repo-root resolution, failure parsing, and baseline comparison.

No real pytest or docs-sync run happens here: run_checks gets a fake runner.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

_SPEC = importlib.util.spec_from_file_location(
    "record_correction_check", Path(__file__).resolve().parent / "check.py")
check = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check)


def _clone(tmp_path, conventions=True, claude_md=True):
    root = tmp_path / "Agentic-Z"
    skill = root / ".claude" / "skills" / "dayz-record-correction"
    skill.mkdir(parents=True)
    if conventions:
        f = root / ".claude" / "skills" / "_shared" / "dayz-conventions.md"
        f.parent.mkdir(parents=True)
        f.write_text("x", encoding="utf-8")
    if claude_md:
        (root / "CLAUDE.md").write_text("x", encoding="utf-8")
    return root, skill


def test_clone_with_both_files_is_usable(tmp_path):
    root, skill = _clone(tmp_path)
    info = check.resolve_root(str(skill))
    assert info["kind"] == "clone"
    assert Path(info["root"]) == root.resolve()
    assert info["missing"] == []
    assert check.main(["root", str(skill)]) == 0


def test_clone_missing_conventions_is_refused(tmp_path):
    _, skill = _clone(tmp_path, conventions=False)
    info = check.resolve_root(str(skill))
    assert info["kind"] == "clone"
    assert any("dayz-conventions.md" in m for m in info["missing"])
    assert check.main(["root", str(skill)]) == 2


def test_copied_into_home_skills_is_refused(tmp_path):
    # Copied (not linked) into ~/.claude/skills: three levels up is the home folder, no CLAUDE.md.
    _, skill = _clone(tmp_path, conventions=False, claude_md=False)
    info = check.resolve_root(str(skill))
    assert sorted(Path(m).name for m in info["missing"]) == ["CLAUDE.md", "dayz-conventions.md"]
    assert check.main(["root", str(skill)]) == 2


def test_plugin_cache_path_is_plugin(tmp_path):
    skill = tmp_path / ".claude" / "plugins" / "cache" / "agentic-z" / "skills" / "dayz-record-correction"
    skill.mkdir(parents=True)
    info = check.resolve_root(str(skill))
    assert info["kind"] == "plugin" and info["root"] is None
    assert check.main(["root", str(skill)]) == 0


def test_unrelated_folder_is_unknown(tmp_path):
    skill = tmp_path / "somewhere" / "dayz-record-correction"
    skill.mkdir(parents=True)
    assert check.resolve_root(str(skill))["kind"] == "unknown"
    assert check.main(["root", str(skill)]) == 2


def test_pytest_failures_parses_failed_and_error_lines():
    out = ("..F.E\n=== short test summary info ===\n"
           "FAILED evals/test_run_evals.py::test_baseline - AssertionError: dayz-router missing\n"
           "ERROR hooks/test_x.py - ImportError\n"
           "1 failed, 1 error, 3 passed in 1.0s\n")
    assert check.pytest_failures(out) == ["evals/test_run_evals.py::test_baseline", "hooks/test_x.py"]


def test_docs_problems_ignores_wiki_line_numbers():
    before = check.docs_problems("wiki/src/content/guide.md:400: says 23, expected 26 (agents) [fixable]\n"
                                 "\n13 problem(s); 11 fixable\n")
    after = check.docs_problems("wiki/src/content/guide.md:402: says 23, expected 26 (agents) [fixable]\n")
    assert before == after == ["wiki/src/content/guide.md: says 23, expected 26 (agents) [fixable]"]


def _runner(pytest_out, docs_out, pytest_rc=1):
    def run(cmd, **kw):
        if "pytest" in cmd:
            return SimpleNamespace(returncode=pytest_rc, stdout=pytest_out, stderr="")
        return SimpleNamespace(returncode=1, stdout=docs_out, stderr="")
    return run


OLD_FAIL = "FAILED a/test_a.py::test_old - boom\n"
OLD_DOC = "wiki/src/App.jsx:235: says 163, expected 164 (graded) [fixable]\n"


def test_compare_ignores_failures_already_in_baseline(tmp_path, capsys):
    base = tmp_path / "base.json"
    assert check.main(["baseline", "--root", str(tmp_path), "--out", str(base)],
                      runner=_runner(OLD_FAIL, OLD_DOC)) == 0
    assert json.loads(base.read_text())["pytest"] == ["a/test_a.py::test_old"]
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base)],
                    runner=_runner(OLD_FAIL, OLD_DOC))
    assert rc == 0
    assert "no new failures" in capsys.readouterr().out


def test_compare_reports_only_new_failures(tmp_path, capsys):
    base = tmp_path / "base.json"
    check.main(["baseline", "--root", str(tmp_path), "--out", str(base)], runner=_runner(OLD_FAIL, OLD_DOC))
    capsys.readouterr()
    new_doc = "wiki/src/content/guide.md:10: says 5, expected 6 (lines) [fixable]\n"
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base)],
                    runner=_runner(OLD_FAIL + "FAILED b/test_b.py::test_new - x\n", OLD_DOC + new_doc))
    out = capsys.readouterr().out
    assert rc == 1
    assert "NEW test: b/test_b.py::test_new" in out
    assert "NEW wiki problem: wiki/src/content/guide.md: says 5" in out
    assert "test_old" not in out


def test_crashed_pytest_without_summary_counts_as_failure():
    result = check.run_checks(".", runner=_runner("internal error", "", pytest_rc=3))
    assert result["pytest"] == ["pytest exited 3 without a failure summary"]
