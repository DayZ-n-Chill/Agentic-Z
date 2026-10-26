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
    skill = root / "skills" / "dayz-record-correction"
    skill.mkdir(parents=True)
    if conventions:
        f = root / "skills" / "_shared" / "dayz-conventions.md"
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
    # Copied (not linked) into ~/.claude/skills: two levels up is ~/.claude, no CLAUDE.md.
    _, skill = _clone(tmp_path, conventions=False, claude_md=False)
    info = check.resolve_root(str(skill))
    assert sorted(Path(m).name for m in info["missing"]) == ["CLAUDE.md", "dayz-conventions.md"]
    assert check.main(["root", str(skill)]) == 2


def test_copy_in_home_claude_skills_is_unknown(tmp_path):
    # ~/.claude often has its own CLAUDE.md and a linked skills/_shared; it is still not a clone.
    home = tmp_path / ".claude"
    skill = home / "skills" / "dayz-record-correction"
    skill.mkdir(parents=True)
    (home / "skills" / "_shared").mkdir()
    (home / "skills" / "_shared" / "dayz-conventions.md").write_text("x", encoding="utf-8")
    (home / "CLAUDE.md").write_text("x", encoding="utf-8")
    assert check.resolve_root(str(skill))["kind"] == "unknown"
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


def test_docs_problems_reads_whole_file_problems_without_a_line_number():
    out = "wiki/src/content/skills-table.md: missing row for dayz-new [fixable]\n"
    assert check.docs_problems(out) == ["wiki/src/content/skills-table.md: missing row for dayz-new [fixable]"]


def test_crashed_docs_sync_without_problems_counts_as_failure():
    def run(cmd, **kw):
        if "pytest" in cmd:
            return SimpleNamespace(returncode=0, stdout="3 passed", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="Traceback (most recent call last):\n  boom\n")
    assert check.run_checks(".", runner=run)["docs"] == ["docs-sync exited 1 without a problem list"]


def test_compare_flags_docs_sync_crash_as_new(tmp_path, capsys):
    base = tmp_path / "base.json"
    clean = lambda cmd, **kw: SimpleNamespace(returncode=0, stdout="", stderr="")
    check.main(["baseline", "--root", str(tmp_path), "--out", str(base)], runner=clean)
    saved = json.loads(base.read_text())
    assert (saved["pytest"], saved["docs"]) == ([], [])
    assert saved["root"] == str(tmp_path.resolve()) and isinstance(saved["created"], float)
    capsys.readouterr()

    def crashing(cmd, **kw):
        if "pytest" in cmd:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="Traceback ...\n")
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base)], runner=crashing)
    assert rc == 1
    assert "NEW wiki problem: docs-sync exited 1" in capsys.readouterr().out


def test_compare_with_missing_baseline_exits_2_with_a_message(tmp_path, capsys):
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(tmp_path / "nope.json")],
                    runner=_runner("", ""))
    assert rc == 2
    assert "no baseline at" in capsys.readouterr().err


def test_compare_with_corrupt_baseline_exits_2_with_a_message(tmp_path, capsys):
    base = tmp_path / "base.json"
    base.write_text("{not json", encoding="utf-8")
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base)], runner=_runner("", ""))
    assert rc == 2
    assert "could not read the baseline" in capsys.readouterr().err


def test_baseline_to_unwritable_path_exits_2_with_a_message(tmp_path, capsys):
    out = tmp_path / "no-such-dir" / "base.json"
    rc = check.main(["baseline", "--root", str(tmp_path), "--out", str(out)], runner=_runner("", ""))
    assert rc == 2
    assert "could not write the baseline" in capsys.readouterr().err


def test_compare_reports_a_second_identical_wiki_problem_as_new(tmp_path, capsys):
    # Same text in the same file, on another line: the edit added a problem, it is not a shift.
    base = tmp_path / "base.json"
    doc = "wiki/src/content/guide.md:{}: says 23, expected 30 (agents) [fixable]\n"
    check.main(["baseline", "--root", str(tmp_path), "--out", str(base)],
               runner=_runner("", doc.format(10), pytest_rc=0))
    capsys.readouterr()
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base)],
                    runner=_runner("", doc.format(12) + doc.format(90), pytest_rc=0))
    out = capsys.readouterr().out
    assert rc == 1
    assert out.count("NEW wiki problem: wiki/src/content/guide.md: says 23, expected 30") == 1


def test_diff_counts_a_removed_duplicate_as_fixed():
    d = check.diff({"pytest": [], "docs": ["w: x", "w: x"]}, {"pytest": [], "docs": ["w: x"]})
    assert d["docs"] == {"new": [], "fixed": ["w: x"]}


def test_pytest_failures_keeps_parametrized_ids_with_spaces():
    out = ("FAILED t/test_p.py::test_case[a b] - AssertionError: no\n"
           "FAILED t/test_p.py::test_case[x - y] - ValueError: [bad - input]\n"
           "ERROR t/test_q.py::test_e[one two]\n"
           "FAILED my tests/test_r.py::test_r - boom\n")
    assert check.pytest_failures(out) == ["t/test_p.py::test_case[a b]", "t/test_p.py::test_case[x - y]",
                                          "t/test_q.py::test_e[one two]", "my tests/test_r.py::test_r"]


def test_pytest_exit_1_without_parsable_ids_counts_as_failure():
    result = check.run_checks(".", runner=_runner("1 failed in 0.1s\n", "", pytest_rc=1))
    assert result["pytest"] == ["pytest exited 1 without a failure summary"]


def test_timed_out_checks_count_as_failures_and_print_progress(capsys):
    seen = []

    def hanging(cmd, **kw):
        seen.append(kw.get("timeout"))
        raise check.subprocess.TimeoutExpired(cmd, kw["timeout"])
    result = check.run_checks(".", runner=hanging, timeout=7)
    assert seen == [7, 7]
    assert result == {"pytest": ["pytest timed out after 7s"], "docs": ["docs-sync timed out after 7s"]}
    err = capsys.readouterr().err
    assert "running pytest" in err and "running docs-sync --check" in err


def test_baseline_and_compare_default_to_the_system_temp_file(tmp_path, monkeypatch, capsys):
    default = tmp_path / "record-correction-baseline.json"
    monkeypatch.setattr(check, "DEFAULT_BASELINE", default)
    clean = lambda cmd, **kw: SimpleNamespace(returncode=0, stdout="", stderr="")
    assert check.main(["baseline", "--root", str(tmp_path)], runner=clean) == 0
    assert default.is_file()
    assert check.main(["compare", "--root", str(tmp_path)], runner=clean) == 0
    assert check.DEFAULT_BASELINE.parent == tmp_path


def _clean(cmd, **kw):
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_compare_refuses_a_baseline_from_another_root(tmp_path, capsys):
    # A baseline made in another clone must not be diffed against: exit 2, run nothing.
    other, mine = tmp_path / "other-clone", tmp_path / "my-clone"
    other.mkdir(), mine.mkdir()
    base = tmp_path / "base.json"
    assert check.main(["baseline", "--root", str(other), "--out", str(base)], runner=_runner(OLD_FAIL, "")) == 0
    capsys.readouterr()
    ran = []
    rc = check.main(["compare", "--root", str(mine), "--baseline", str(base)],
                    runner=lambda cmd, **kw: ran.append(cmd))
    err = capsys.readouterr().err
    assert rc == 2 and ran == []
    assert "was made for" in err and "run `check.py baseline` again" in err


def test_compare_refuses_a_baseline_older_than_the_max_age(tmp_path, capsys):
    # Last week's baseline would hide new failures that happened to fail then too.
    base = tmp_path / "base.json"
    week_ago = 1_000_000.0
    check.main(["baseline", "--root", str(tmp_path), "--out", str(base)],
               runner=_runner(OLD_FAIL, "", pytest_rc=1), now=lambda: week_ago)
    capsys.readouterr()
    later = week_ago + 7 * 24 * 3600
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base)],
                    runner=_runner(OLD_FAIL, "", pytest_rc=1), now=lambda: later)
    assert rc == 2
    assert "hours old" in capsys.readouterr().err
    # The same baseline is accepted when --max-age-hours allows it.
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base), "--max-age-hours", "200"],
                    runner=_runner(OLD_FAIL, "", pytest_rc=1), now=lambda: later)
    assert rc == 0


def test_compare_accepts_a_fresh_baseline_within_the_max_age(tmp_path):
    base = tmp_path / "base.json"
    check.main(["baseline", "--root", str(tmp_path), "--out", str(base)], runner=_clean, now=lambda: 5000.0)
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base)],
                    runner=_clean, now=lambda: 5000.0 + 11 * 3600)
    assert rc == 0


def test_compare_refuses_an_old_format_baseline_without_root_or_time(tmp_path, capsys):
    base = tmp_path / "base.json"
    base.write_text(json.dumps({"pytest": [], "docs": []}), encoding="utf-8")
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base)], runner=_clean)
    assert rc == 2
    assert "records no repo root or creation time" in capsys.readouterr().err


def test_compare_refuses_valid_json_that_is_not_a_baseline(tmp_path, capsys):
    base = tmp_path / "base.json"
    base.write_text("[1, 2]", encoding="utf-8")
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base)], runner=_clean)
    assert rc == 2
    assert "no pytest and docs failure lists" in capsys.readouterr().err


def test_compare_refuses_a_baseline_dated_in_the_future(tmp_path, capsys):
    base = tmp_path / "base.json"
    check.main(["baseline", "--root", str(tmp_path), "--out", str(base)], runner=_clean, now=lambda: 9000.0)
    capsys.readouterr()
    rc = check.main(["compare", "--root", str(tmp_path), "--baseline", str(base)],
                    runner=_clean, now=lambda: 100.0)
    assert rc == 2
    assert "in the future" in capsys.readouterr().err
