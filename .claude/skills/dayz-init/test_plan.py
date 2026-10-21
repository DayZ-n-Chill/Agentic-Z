"""Tests for dayz-init/plan.py: step building, env gating and execution order."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan  # noqa: E402
from env_check import EnvIssue, Severity  # noqa: E402
from plan import Intent, build_steps  # noqa: E402
from state import read_state  # noqa: E402


def _actions(steps):
    return [s.action for s in steps]


def test_new_mod_minimal():
    assert _actions(build_steps(Intent("MyMod"), False)) == ["new-mod", "record"]


def test_existing_mod_skips_scaffold():
    assert _actions(build_steps(Intent("MyMod"), True)) == ["record"]


def test_import_uses_import_step():
    steps = build_steps(Intent("M", source="D:/src", scaffold=False), False)
    assert _actions(steps) == ["import-mod", "record"]
    assert steps[0].params == {"mod": "M", "source": "D:/src", "scaffold": False}


def test_scaffold_import_passes_author():
    steps = build_steps(Intent("M", source="D:/src", scaffold=True, author="Me"), False)
    assert steps[0].params == {"mod": "M", "source": "D:/src", "scaffold": True, "author": "Me"}
    # Link-only import writes no config.cpp, so the author is not passed.
    steps = build_steps(Intent("M", source="D:/src", scaffold=False, author="Me"), False)
    assert "author" not in steps[0].params


def test_execute_forwards_author_to_import_mod(env_ok, runs, tmp_path):
    rc = plan.main(
        ["--mod", "M", "--import-from", "D:/src", "--scaffold", "--author", "Me", "--execute"], project=tmp_path
    )
    assert rc == 0
    assert runs["argv"][0][-3:] == ["--scaffold", "--author", "Me"]


def test_full_plan_order_and_launch_implies_build():
    intent = Intent("MyMod", author="Me", server_map="chernarus", launch=True)
    steps = build_steps(intent, False)
    assert _actions(steps) == ["new-mod", "record", "add-server", "build", "launch"]
    assert steps[0].params == {"mod": "MyMod", "author": "Me"}
    assert steps[-1].params == {"mod": "MyMod", "server": "chernarus"}


def test_record_precedes_server_and_build():
    # add-server, build and launch read the project cache written by "record".
    actions = _actions(build_steps(Intent("M", server_map="sakhal", build=True), False))
    assert actions.index("record") < actions.index("add-server") < actions.index("build")


@pytest.fixture
def env_ok(monkeypatch):
    monkeypatch.setattr(plan, "run_all", lambda: [])
    monkeypatch.setattr(plan, "mod_exists", lambda project, mod: False)


@pytest.fixture
def runs(monkeypatch):
    record = {"argv": [], "rc": {}}

    def fake_run(argv):
        record["argv"].append(argv)
        return record["rc"].get(Path(argv[1]).parent.name, 0)

    monkeypatch.setattr(plan, "run", fake_run)
    return record


def _skills_run(runs):
    return [Path(a[1]).parent.name for a in runs["argv"]]


def test_print_only_runs_nothing(env_ok, runs, tmp_path, capsys):
    assert plan.main(["--mod", "MyMod", "--build"], project=tmp_path) == 0
    assert runs["argv"] == []
    assert "Build MyMod.pbo" in capsys.readouterr().out
    assert not (tmp_path / ".claude").exists()


def test_execute_runs_steps_and_records_state(env_ok, runs, tmp_path):
    rc = plan.main(["--mod", "MyMod", "--server", "chernarus", "--launch", "--execute"], project=tmp_path)
    assert rc == 0
    assert _skills_run(runs) == ["dayz-new-mod", "dayz-add-server", "dayz-build-pbo", "dayz-launch-test"]
    mem = tmp_path / ".claude" / "local-memory"
    assert (mem / "dayz-current-project.txt").read_text() == str(tmp_path)
    assert '"mod_name": "MyMod"' in (mem / "dayz-init-state.json").read_text()


def test_execute_stops_at_first_failure_with_its_code(env_ok, runs, tmp_path):
    runs["rc"]["dayz-add-server"] = 3
    rc = plan.main(["--mod", "MyMod", "--server", "livonia", "--build", "--execute"], project=tmp_path)
    assert rc == 3
    assert _skills_run(runs) == ["dayz-new-mod", "dayz-add-server"]


def test_hard_stop_refuses(monkeypatch, runs, tmp_path):
    monkeypatch.setattr(plan, "run_all", lambda: [EnvIssue("dayz_tools", Severity.HARD_STOP, "no tools")])
    assert plan.main(["--mod", "M", "--execute"], project=tmp_path) == 2
    assert runs["argv"] == []


def test_unmounted_p_refuses(monkeypatch, runs, tmp_path):
    monkeypatch.setattr(plan, "run_all", lambda: [EnvIssue("p_drive", Severity.AUTOFIX, "P:\\ not mounted")])
    assert plan.main(["--mod", "M", "--execute"], project=tmp_path) == 2
    assert runs["argv"] == []


def test_launch_without_server_is_a_usage_error():
    with pytest.raises(SystemExit) as exc:
        plan.parse_args(["--mod", "M", "--launch"])
    assert exc.value.code == 2


def test_scaffold_flag_requires_import():
    with pytest.raises(SystemExit):
        plan.parse_args(["--mod", "M", "--scaffold"])


def test_rerun_after_no_scaffold_import_skips_the_import(monkeypatch, runs, tmp_path):
    monkeypatch.setattr(plan, "run_all", lambda: [])
    (tmp_path / "workspace" / "Linked").mkdir(parents=True)  # linked source, no config.cpp
    rc = plan.main(["--mod", "Linked", "--import-from", "D:/src", "--no-scaffold", "--execute"], project=tmp_path)
    assert rc == 0
    assert runs["argv"] == []


def test_import_requires_a_scaffold_choice(capsys):
    with pytest.raises(SystemExit) as exc:
        plan.parse_args(["--mod", "M", "--import-from", "D:/src"])
    assert exc.value.code == 2
    assert "--import-from needs --scaffold or --no-scaffold" in capsys.readouterr().err


def test_record_project_stores_only_the_active_mod(tmp_path):
    plan.record_project(tmp_path, Intent("MyMod", source="D:/src", scaffold=False, server_map="chernarus"))
    assert read_state(tmp_path) == {"last_intent": {"mod_name": "MyMod"}}
