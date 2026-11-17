"""Tests for run_regression_tests.py: the synthetic fixtures and the no-Blender skip."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_regression_tests as runner  # noqa: E402


def test_synthetic_fixtures_give_their_expected_verdicts():
    result = runner.run_synthetic_fixtures()
    assert result["status"] == "PASS"
    assert set(result["negative_cases"]) >= runner.REQUIRED_NEGATIVE_CASES
    assert all(case["status"] == "PASS" for case in result["negative_cases"].values())


def test_real_fixture_contract_names_the_three_expected_failures():
    contract = runner.read_json(runner.FIXTURE_DIR / "sr2m-v44.contract.json")
    check_ids = {check["id"] for check in contract["checks"]}
    assert runner.EXPECTED_V44_FAILURES <= check_ids
    assert contract["contract_mode"] == "diagnostic"  # it can never grant OFFLINE_PASS


def test_blender_comes_from_the_environment_or_path(monkeypatch, tmp_path):
    fake = tmp_path / "blender.exe"
    fake.write_bytes(b"")
    monkeypatch.setenv("BLENDER_EXE", str(fake))
    assert runner.find_blender() == fake

    monkeypatch.delenv("BLENDER_EXE")
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    assert runner.find_blender() is None


def test_missing_blender_is_a_skip_not_a_pass():
    result = runner.run_blender_sampler_test(None)
    assert result["status"] == "SKIP_NO_BLENDER"
