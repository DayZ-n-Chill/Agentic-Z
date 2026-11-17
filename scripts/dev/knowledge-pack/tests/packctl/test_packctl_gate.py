from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from packctl.gate import _run_test_suites, _suite_passed, run_gate


PASSING_SUITE = "def test_passes():\n    assert 1 + 1 == 2\n"
FAILING_SUITE = "def test_fails():\n    assert 1 + 1 == 3\n"
# What a Blender-only module does on a machine without Blender: it skips itself
# at import, so pytest collects no test and exits 5 with one skip recorded.
SKIPPED_SUITE = (
    "import pytest\n\n"
    'pytest.importorskip("packctl_fixture_module_that_is_not_installed")\n\n\n'
    "def test_needs_the_module():\n"
    "    assert False\n"
)
# A script-style check: pytest imports it, finds no test and exits 5 too.
SCRIPT_SUITE = "FAILURES = ['the check this script makes failed']\n"
# A module that cannot be imported: a collection error, exit 2.
BROKEN_SUITE = "raise ImportError('a module this test needs')\n"
# A conftest that deselects every test it collects.
DESELECT_ALL = (
    "def pytest_collection_modifyitems(config, items):\n"
    "    config.hook.pytest_deselected(items=list(items))\n"
    "    items[:] = []\n"
)
# A conftest that ends the session once collection is done, with exit 0.
EXIT_AFTER_COLLECTION = (
    "import pytest\n\n\n"
    "def pytest_collection_finish(session):\n"
    "    pytest.exit('stop before running', returncode=0)\n"
)
# Two modules: one that skips itself at import, one that fails.
SKIP_AND_FAIL = {
    "tests/test_needs_blender.py": SKIPPED_SUITE,
    "tests/test_bad.py": FAILING_SUITE,
}


def test_gate_runs_validation_and_two_reproducible_builds(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})
    report_dir = tmp_path / "reports"

    report = run_gate(root, report_dir)

    assert report["verdict"] == "PASS"
    assert report["checks"]["validate"]["verdict"] == "PASS"
    assert report["checks"]["build_reproducible"]["verdict"] == "PASS"
    assert report["artifacts"]["build_a_sha256"] == report["artifacts"][
        "build_b_sha256"
    ]
    assert (report_dir / "gate.json").is_file()


def test_gate_detects_non_reproducible_build_bytes(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})
    report_dir = tmp_path / "reports"
    calls = 0

    def fake_build(_root: Path, output: Path) -> dict[str, object]:
        nonlocal calls
        calls += 1
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(f"build-{calls}".encode("ascii"))
        return {
            "schema_version": 1,
            "command": "build",
            "source_commit": "fixture",
            "verdict": "PASS",
            "findings": [],
            "checks": {},
            "artifacts": {"archive_sha256": str(calls)},
        }

    monkeypatch.setattr("packctl.gate.build_archive", fake_build)

    report = run_gate(root, report_dir)

    assert report["verdict"] == "FAIL"
    assert [item["code"] for item in report["findings"]] == [
        "BUILD-NONDETERMINISTIC"
    ]


def test_gate_requires_external_skills_ref_when_skills_exist(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: Gate fixture.\n---\n# Demo\n"
            )
        },
        payload={"LICENSE", "README.md", "skills/demo/SKILL.md"},
    )
    monkeypatch.delenv("PACK_SKILLS_REF_ROOT", raising=False)

    report = run_gate(root, tmp_path / "reports")

    assert "SKILLS-REF-NOT-CONFIGURED" in [
        item["code"] for item in report["findings"]
    ]


def test_gate_rejects_missing_evidence_even_when_fail_is_expected(
    repo_factory,
    tmp_path: Path,
) -> None:
    case = {
        "schema_version": 1,
        "case_id": "missing-evidence",
        "family": "api",
        "prompt": "Answer from evidence.",
        "fixtures": {"fixture.c": "class Demo {};\n"},
        "assertions": [
            {
                "assertion_id": "mentions-demo",
                "type": "contains",
                "value": "Demo",
                "evidence": ["proof.txt"],
            }
        ],
        "grader": {"type": "mechanical"},
        "required_evidence": ["proof.txt"],
        "variants": [
            {
                "variant_id": "baseline",
                "skill_revision": "absent",
                "baseline_revision": "absent",
                "runner_id": "fixture",
                "expected_verdict": "FAIL",
                "response": "Demo",
                "evidence": {},
                "tokens_input": 1,
                "tokens_output": 1,
            },
            {
                "variant_id": "current",
                "skill_revision": "current",
                "baseline_revision": "absent",
                "runner_id": "fixture",
                "expected_verdict": "PASS",
                "response": "Demo",
                "evidence": {"proof.txt": "fixture.c:1\n"},
                "tokens_input": 1,
                "tokens_output": 1,
            }
        ],
    }
    root = repo_factory(
        {"evals/cases/missing-evidence.json": json.dumps(case)},
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert "EVAL-MISSING-EVIDENCE" in [
        item["code"] for item in report["findings"]
    ]
    assert report["checks"]["evals"]["verdict"] == "FAIL"


def test_gate_fails_when_a_skill_test_fails(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(
        {
            "skills/bad/tests/test_bad.py": FAILING_SUITE,
            "skills/good/tests/test_good.py": PASSING_SUITE,
        },
        payload={"LICENSE", "README.md"},
    )
    report_dir = tmp_path / "reports"

    report = run_gate(root, report_dir)

    assert report["verdict"] == "FAIL"
    assert [item["code"] for item in report["findings"]] == [
        "SKILL-TESTS-FAILED"
    ]
    assert report["checks"]["skill_tests"] == {
        "verdict": "FAIL",
        "suite_count": 2,
        "suites": {
            "bad": {"verdict": "FAIL", "returncode": 1},
            "good": {"verdict": "PASS", "returncode": 0},
        },
    }
    assert "bad (exit 1)" in report["findings"][0]["evidence"]
    assert "1 failed" in (report_dir / "skill-tests" / "bad.txt").read_text(
        encoding="utf-8"
    )


def test_gate_fails_when_a_tool_test_fails_and_runs_py3d_once(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(
        {
            "tools/broken/tests/test_broken.py": FAILING_SUITE,
            "tools/py3d/tests/test_py3d.py": PASSING_SUITE,
        },
        payload={"LICENSE", "README.md"},
    )
    report_dir = tmp_path / "reports"

    report = run_gate(root, report_dir)

    assert [item["code"] for item in report["findings"]] == [
        "TOOL-TESTS-FAILED"
    ]
    assert report["checks"]["py3d_tests"]["verdict"] == "PASS"
    assert report["checks"]["tool_tests"]["suites"] == {
        "broken": {"verdict": "FAIL", "returncode": 1},
    }
    assert sorted(path.name for path in (report_dir / "tool-tests").iterdir()) == [
        "broken.json",
        "broken.txt",
    ]


def test_gate_passes_same_named_and_cleanly_skipped_suites(
    repo_factory,
    tmp_path: Path,
) -> None:
    # Two skills shipping test files with one basename abort a single pytest
    # run ("import file mismatch", exit 2) -- the state of main before the
    # gate ran these folders.
    root = repo_factory(
        {
            "skills/alpha/tests/test_install.py": PASSING_SUITE,
            "skills/beta/tests/test_install.py": PASSING_SUITE,
            "skills/blender/tests/test_needs_blender.py": SKIPPED_SUITE,
            "tools/demo/tests/test_install.py": PASSING_SUITE,
        },
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert report["verdict"] == "PASS"
    assert report["checks"]["skill_tests"]["suites"] == {
        "alpha": {"verdict": "PASS", "returncode": 0},
        "beta": {"verdict": "PASS", "returncode": 0},
        "blender": {"verdict": "PASS", "returncode": 5},
    }
    assert report["checks"]["tool_tests"]["suites"] == {
        "demo": {"verdict": "PASS", "returncode": 0},
    }


def test_gate_fails_test_folders_that_run_nothing_or_do_not_collect(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(
        {
            "skills/broken/tests/test_broken.py": BROKEN_SUITE,
            "skills/deselected/tests/conftest.py": DESELECT_ALL,
            "skills/deselected/tests/test_bad.py": FAILING_SUITE,
            "skills/deselected/tests/test_needs_blender.py": SKIPPED_SUITE,
            "skills/script/tests/test_script.py": SCRIPT_SUITE,
        },
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert [item["code"] for item in report["findings"]] == [
        "SKILL-TESTS-FAILED"
    ]
    # "deselected" exits 5 with one skip recorded, like a clean skip: its
    # summary line, "1 skipped, 1 deselected", is what fails it.
    assert report["checks"]["skill_tests"]["suites"] == {
        "broken": {"verdict": "FAIL", "returncode": 2},
        "deselected": {"verdict": "FAIL", "returncode": 5},
        "script": {"verdict": "FAIL", "returncode": 5},
    }


def test_gate_ignores_pytest_addopts_from_the_environment(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    # --collect-only would turn the failing test into an exit 0 that runs
    # nothing; the gate drops the variable, so the test runs and fails.
    monkeypatch.setenv("PYTEST_ADDOPTS", "--collect-only")
    root = repo_factory(
        {"skills/bad/tests/test_bad.py": FAILING_SUITE},
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert report["checks"]["skill_tests"]["suites"] == {
        "bad": {"verdict": "FAIL", "returncode": 1},
    }


def test_gate_fails_a_collection_only_run_configured_in_the_repository(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(
        {
            "pytest.ini": "[pytest]\naddopts = --collect-only\n",
            "skills/bad/tests/test_bad.py": FAILING_SUITE,
        },
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert report["checks"]["skill_tests"]["suites"] == {
        "bad": {"verdict": "FAIL", "returncode": 0},
    }


def test_gate_fails_tests_deselected_by_quiet_coloured_configuration(
    repo_factory,
    tmp_path: Path,
) -> None:
    # With -q twice pytest prints no closing counts, and --color=yes puts
    # escape codes before them: the deselection is read from the run itself.
    root = repo_factory(
        {
            "pytest.ini": "[pytest]\naddopts = -q -k test_passes --color=yes\n",
            "skills/selected/tests/test_selected.py": (
                PASSING_SUITE + "\n\n" + FAILING_SUITE
            ),
        },
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert report["checks"]["skill_tests"]["suites"] == {
        "selected": {"verdict": "FAIL", "returncode": 0},
    }


@pytest.mark.parametrize(
    "narrowing",
    [
        {"pytest.ini": "[pytest]\npython_files = test_needs_blender.py\n"},
        {
            "pytest.ini": (
                "[pytest]\naddopts = --ignore=skills/narrowed/tests/test_bad.py\n"
            )
        },
        {"skills/narrowed/tests/conftest.py": "collect_ignore = ['test_bad.py']\n"},
    ],
    ids=["python_files", "ignore", "collect_ignore"],
)
def test_gate_fails_a_test_module_kept_out_of_collection(
    repo_factory,
    tmp_path: Path,
    narrowing: dict[str, str],
) -> None:
    # Only the module that skips itself is collected: exit 5 with one skip,
    # while the failing module never runs.
    root = repo_factory(
        {
            **{
                f"skills/narrowed/{path}": content
                for path, content in SKIP_AND_FAIL.items()
            },
            **narrowing,
        },
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert report["checks"]["skill_tests"]["suites"] == {
        "narrowed": {"verdict": "FAIL", "returncode": 5},
    }


def test_gate_fails_a_run_ended_after_collection(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(
        {
            **{
                f"skills/stopped/{path}": content
                for path, content in SKIP_AND_FAIL.items()
            },
            "skills/stopped/tests/conftest.py": EXIT_AFTER_COLLECTION,
        },
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert report["checks"]["skill_tests"]["suites"] == {
        "stopped": {"verdict": "FAIL", "returncode": 0},
    }


ITEM = "tests/test_a.py::test_a"
NOTHING_COLLECTED = {"collected": [], "items": [], "finished": [], "modules": []}


def observed_run(module: str, **changes: object) -> dict[str, object]:
    # The observer's record of a clean run of one module holding one test.
    run: dict[str, object] = {
        "exitstatus": 0,
        "collected": [ITEM],
        "items": [ITEM],
        "finished": [ITEM],
        "deselected": 0,
        "failed": 0,
        "modules": [module],
        "skipped_modules": [],
    }
    run.update(changes)
    return run


@pytest.mark.parametrize(
    ("returncode", "changes", "passed"),
    [
        (0, lambda module: {}, True),
        # Every module skipped itself at import: a clean skip.
        (
            5,
            lambda module: {
                **NOTHING_COLLECTED,
                "exitstatus": 5,
                "skipped_modules": [module],
            },
            True,
        ),
        (1, lambda module: {"exitstatus": 1}, False),
        (2, lambda module: {"exitstatus": 2}, False),
        (3, lambda module: {"exitstatus": 3}, False),
        (4, lambda module: {"exitstatus": 4}, False),
        # A record that does not match the process, or reports a failure.
        (0, lambda module: {"exitstatus": 1}, False),
        (0, lambda module: {"failed": 1}, False),
        (0, lambda module: {"deselected": 1}, False),
        # Collection never finished.
        (0, lambda module: {"items": None}, False),
        # An item dropped, or added, between collection and the run.
        (0, lambda module: {"items": []}, False),
        (
            0,
            lambda module: {
                "items": [ITEM, "tests/test_a.py::test_b"],
                "finished": [ITEM, "tests/test_a.py::test_b"],
            },
            False,
        ),
        # A collected item that never ran to the end: a collection-only run,
        # or pytest.exit after collection.
        (0, lambda module: {"finished": []}, False),
        # A test module that neither yielded an item nor skipped itself.
        (0, lambda module: {"modules": []}, False),
        # Exit 5 with no module that skipped itself: nothing ran.
        (5, lambda module: {**NOTHING_COLLECTED, "exitstatus": 5}, False),
        (0, lambda module: {"deselected": "0"}, False),
    ],
)
def test_suite_pass_rule(
    tmp_path: Path,
    returncode: int,
    changes,
    passed: bool,
) -> None:
    folder = tmp_path / "tests"
    folder.mkdir()
    module = folder / "test_a.py"
    module.write_text(PASSING_SUITE, encoding="utf-8")
    observed = tmp_path / "run.json"
    observed.write_text(
        json.dumps(observed_run(str(module), **changes(str(module)))),
        encoding="utf-8",
    )

    assert _suite_passed(returncode, observed, folder) is passed


@pytest.mark.parametrize(
    "content",
    [None, "{", json.dumps({"exitstatus": 0})],
    ids=["missing", "malformed", "incomplete"],
)
def test_suite_pass_rule_needs_a_whole_record(
    tmp_path: Path,
    content: str | None,
) -> None:
    folder = tmp_path / "tests"
    folder.mkdir()
    observed = tmp_path / "run.json"
    if content is not None:
        observed.write_text(content, encoding="utf-8")

    assert _suite_passed(0, observed, folder) is False


def test_a_record_left_by_an_earlier_run_is_not_read(
    tmp_path: Path,
    monkeypatch,
) -> None:
    folder = tmp_path / "repo" / "skills" / "demo" / "tests"
    folder.mkdir(parents=True)
    module = folder / "test_a.py"
    module.write_text(PASSING_SUITE, encoding="utf-8")
    log_dir = tmp_path / "reports" / "skill-tests"
    log_dir.mkdir(parents=True)
    (log_dir / "demo.json").write_text(
        json.dumps(observed_run(str(module))),
        encoding="utf-8",
    )
    # A run that exits 0 and writes no record of its own.
    monkeypatch.setattr(
        "packctl.gate._run_process",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""),
    )

    check, _ = _run_test_suites(
        tmp_path / "repo",
        [folder],
        log_dir,
        pycache_dir=tmp_path / "pycache",
    )

    assert check["suites"] == {"demo": {"verdict": "FAIL", "returncode": 0}}


def test_gate_refuses_a_report_dir_inside_the_root_before_any_suite_runs(
    repo_factory,
    tmp_path: Path,
) -> None:
    marker = tmp_path / "suite-ran.txt"
    root = repo_factory(
        {
            "skills/demo/tests/test_marks.py": (
                "from pathlib import Path\n\n\n"
                "def test_marks():\n"
                f"    Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n"
            )
        },
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, root / "gate-reports")

    assert [item["code"] for item in report["findings"]] == [
        "GATE-REPORT-IN-ROOT"
    ]
    assert not marker.exists()
    assert not (root / "gate-reports").exists()
