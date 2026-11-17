from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from packctl_testlib import REPO_ROOT


def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    project_root = str(Path(__file__).resolve().parents[2])
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "packctl", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def test_missing_arguments_return_usage_exit_2(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "validate")

    assert result.returncode == 2


def test_validate_writes_stable_json_report(repo_factory, tmp_path: Path) -> None:
    root = repo_factory()
    report_path = tmp_path / "report.json"

    result = run_cli(
        root,
        "validate",
        "--root",
        str(root),
        "--report",
        str(report_path),
    )

    assert result.returncode == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 1
    assert report["command"] == "validate"
    assert report["verdict"] == "PASS"
    assert report["findings"] == []


def test_validation_finding_returns_exit_1(repo_factory, tmp_path: Path) -> None:
    root = repo_factory({"notes.md": "C:\\Users\\person\\secret\n"})
    report_path = tmp_path / "report.json"

    result = run_cli(
        root,
        "validate",
        "--root",
        str(root),
        "--report",
        str(report_path),
    )

    assert result.returncode == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["verdict"] == "FAIL"
    assert any(item["code"] == "PRIVACY-PRIVATE-PATH" for item in report["findings"])


def test_eval_cli_runs_versioned_case(tmp_path: Path) -> None:
    root = REPO_ROOT
    output = tmp_path / "eval"

    result = run_cli(
        root,
        "eval",
        "run",
        "--case",
        "api-enforce",
        "--variant",
        "current",
        "--out",
        str(output),
    )

    assert result.returncode == 0
    assert (output / "grading.json").is_file()


def test_promotion_cli_apply_uses_existing_plan(
    repo_factory,
    tmp_path: Path,
) -> None:
    from test_packctl_promotion import promotion_fixture

    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )

    checked = run_cli(
        root,
        "promote",
        "--check",
        "--root",
        str(root),
        "--promotion-map",
        str(map_path),
        "--local-targets",
        str(config_path),
        "--plan",
        str(plan_path),
    )
    applied = run_cli(root, "promote", "--apply", "--plan", str(plan_path))

    assert checked.returncode == 0
    assert applied.returncode == 0
    assert (paths["claude"] / "demo" / "SKILL.md").is_file()


def _promotion_check_report(result) -> dict[str, object]:
    assert "requires --plan" not in result.stderr
    report = json.loads(result.stdout)
    assert "verdict" in report
    findings = report["findings"]
    assert isinstance(findings, list)
    return report


def test_promotion_cli_check_without_plan_prints_failure_report(
    repo_factory,
    tmp_path: Path,
) -> None:
    from test_packctl_promotion import promotion_fixture, seed_installed_demo

    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_installed_demo(root, paths["claude"] / "demo")

    result = run_cli(
        root,
        "promote",
        "--check",
        "--root",
        str(root),
        "--promotion-map",
        str(map_path),
        "--local-targets",
        str(config_path),
    )

    report = _promotion_check_report(result)
    assert result.returncode == 1
    assert report["verdict"] == "FAIL"
    assert report["findings"]
    first = report["findings"][0]
    assert first["code"]
    assert "path" in first
    assert any(
        item["code"] == "PROMOTION-TARGET-UNEXPLAINED"
        for item in report["findings"]
    )
    assert not plan_path.exists()


def test_promotion_cli_check_without_plan_prints_pass_report(
    repo_factory,
    tmp_path: Path,
) -> None:
    from test_packctl_promotion import promotion_fixture

    root, map_path, config_path, plan_path, _paths = promotion_fixture(
        repo_factory, tmp_path
    )

    result = run_cli(
        root,
        "promote",
        "--check",
        "--root",
        str(root),
        "--promotion-map",
        str(map_path),
        "--local-targets",
        str(config_path),
    )

    report = _promotion_check_report(result)
    assert result.returncode == 0
    assert report["verdict"] in {"PASS", "WARN"}
    assert all(item["severity"] != "error" for item in report["findings"])
    first = report["findings"][0] if report["findings"] else {"code": "", "path": ""}
    assert "code" in first
    assert "path" in first
    assert not plan_path.exists()


def test_promotion_cli_check_with_plan_still_prints_failure_report(
    repo_factory,
    tmp_path: Path,
) -> None:
    from test_packctl_promotion import promotion_fixture, seed_installed_demo

    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_installed_demo(root, paths["claude"] / "demo")

    result = run_cli(
        root,
        "promote",
        "--check",
        "--root",
        str(root),
        "--promotion-map",
        str(map_path),
        "--local-targets",
        str(config_path),
        "--plan",
        str(plan_path),
    )

    report = _promotion_check_report(result)
    assert result.returncode == 1
    assert report["verdict"] == "FAIL"
    assert report["findings"]
    first = report["findings"][0]
    assert first["code"]
    assert "path" in first
    assert not plan_path.exists()


def test_promotion_cli_bootstrap_requires_plan(
    repo_factory,
    tmp_path: Path,
) -> None:
    from test_packctl_promotion import promotion_fixture

    root, map_path, config_path, _plan_path, _paths = promotion_fixture(
        repo_factory, tmp_path
    )

    result = run_cli(
        root,
        "promote",
        "--bootstrap",
        "--root",
        str(root),
        "--promotion-map",
        str(map_path),
        "--local-targets",
        str(config_path),
    )

    assert result.returncode == 2
    assert "requires --plan" in result.stderr


def test_promotion_cli_bootstrap_is_exclusive_with_check(
    repo_factory,
    tmp_path: Path,
) -> None:
    from test_packctl_promotion import promotion_fixture

    root, map_path, config_path, plan_path, _paths = promotion_fixture(
        repo_factory, tmp_path
    )

    result = run_cli(
        root,
        "promote",
        "--check",
        "--bootstrap",
        "--root",
        str(root),
        "--promotion-map",
        str(map_path),
        "--local-targets",
        str(config_path),
        "--plan",
        str(plan_path),
    )

    assert result.returncode == 2
    assert not plan_path.exists()


def test_promotion_cli_bootstrap_writes_v2_plan(
    repo_factory,
    tmp_path: Path,
) -> None:
    from test_packctl_promotion import INSTALLATION_A, promotion_fixture, write_v2_config

    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    write_v2_config(config_path, INSTALLATION_A)

    checked = run_cli(
        root,
        "promote",
        "--bootstrap",
        "--root",
        str(root),
        "--promotion-map",
        str(map_path),
        "--local-targets",
        str(config_path),
        "--plan",
        str(plan_path),
    )
    applied = run_cli(root, "promote", "--apply", "--plan", str(plan_path))

    assert checked.returncode in {0, 1}
    assert applied.returncode == 0
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["schema_version"] == 2
    assert plan["bootstrap"] is True
    assert plan["installation_id"] == INSTALLATION_A
    assert (paths["claude"] / "demo" / "SKILL.md").is_file()


def test_test_folders_runs_the_named_tree_and_prints_its_report(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(
        {
            "skills/bad/tests/test_bad.py": "def test_fails():\n    assert 1 + 1 == 3\n",
            "scripts/tools/demo/tests/test_demo.py": "def test_fails():\n    assert False\n",
        },
    )
    report_dir = tmp_path / "reports"

    result = run_cli(
        root,
        "test-folders",
        "--root",
        str(root),
        "--tree",
        "skills",
        "--report-dir",
        str(report_dir),
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["command"] == "test-folders"
    assert [item["code"] for item in report["findings"]] == ["SKILL-TESTS-FAILED"]
    assert report["checks"] == {
        "skill_tests": {
            "verdict": "FAIL",
            "suite_count": 1,
            "suites": {"bad": {"verdict": "FAIL", "returncode": 1}},
        }
    }
    assert json.loads(
        (report_dir / "test-folders.json").read_text(encoding="utf-8")
    ) == report
    assert not (report_dir / "tool-tests").exists()


def test_test_folders_refuses_a_report_dir_inside_the_root(
    repo_factory,
) -> None:
    root = repo_factory(
        {"skills/good/tests/test_good.py": "def test_passes():\n    assert True\n"},
    )

    result = run_cli(
        root,
        "test-folders",
        "--root",
        str(root),
        "--tree",
        "skills",
        "--report-dir",
        str(root / "reports"),
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert [item["code"] for item in report["findings"]] == ["GATE-REPORT-IN-ROOT"]
    assert not (root / "reports").exists()


def test_test_folders_runs_tools_py3d_tests_too(
    repo_factory,
    tmp_path: Path,
) -> None:
    # The gate runs scripts/tools/py3d/tests in its own py3d_tests check; test-folders
    # has no such check, so its tools tree includes the folder.
    root = repo_factory(
        {"scripts/tools/py3d/tests/test_py3d.py": "def test_fails():\n    assert False\n"},
    )

    result = run_cli(
        root,
        "test-folders",
        "--root",
        str(root),
        "--tree",
        "tools",
        "--report-dir",
        str(tmp_path / "reports"),
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["checks"]["tool_tests"]["suites"] == {
        "py3d": {"verdict": "FAIL", "returncode": 1},
    }
