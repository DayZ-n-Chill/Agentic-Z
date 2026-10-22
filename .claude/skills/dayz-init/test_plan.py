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


def test_launch_step_carries_deps():
    intent = Intent("M", source="D:/src", scaffold=False, server_map="chernarus", launch=True, deps=["@CF", "Dabs"])
    launch = build_steps(intent, False)[-1]
    assert launch.action == "launch"
    assert launch.params == {"mod": "M", "server": "chernarus", "deps": ["@CF", "Dabs"]}
    assert "after @CF, Dabs" in launch.label


def test_execute_launches_import_after_its_deps(env_ok, runs, tmp_path):
    rc = plan.main(
        ["--mod", "M", "--import-from", "D:/src", "--no-scaffold", "--server", "chernarus", "--launch",
         "--deps", "@CF", "--deps", "Dabs", "--execute"],
        project=tmp_path,
    )
    assert rc == 0
    launch = runs["argv"][-1]
    assert Path(launch[1]).parent.name == "dayz-launch-test"
    assert launch[2:] == ["CF", "Dabs", "M", "--server", "chernarus"]


def test_deps_without_launch_is_a_usage_error():
    with pytest.raises(SystemExit) as exc:
        plan.parse_args(["--mod", "M", "--server", "chernarus", "--deps", "CF"])
    assert exc.value.code == 2


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


@pytest.mark.parametrize("name", ["1Mod", "_Mod", "My-Mod", "My Mod", "Mod.v2", ""])
def test_bad_mod_name_is_a_usage_error(name):
    with pytest.raises(SystemExit) as exc:
        plan.parse_args(["--mod", name])
    assert exc.value.code == 2


@pytest.mark.parametrize("name", ["M", "MyMod", "My_Mod_2"])
def test_good_mod_names_are_accepted(name):
    assert plan.parse_args(["--mod", name]).mod == name


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


SPEC_ARGS = [
    "--goal", "Adds a craftable radio",
    "--item", "MyMod_Radio",
    "--behavior", "A player can hold the radio",
    "--behavior", "Using it plays a sound",
    "--done-check", "The radio spawns on the server",
]


def test_spec_step_follows_scaffold_and_precedes_record():
    intent = Intent("MyMod", spec=plan.Spec("Adds a radio"), server_map="chernarus")
    assert _actions(build_steps(intent, False)) == ["new-mod", "spec", "record", "add-server"]


def test_spec_step_skipped_without_goal_or_when_spec_exists():
    assert "spec" not in _actions(build_steps(Intent("MyMod"), False))
    assert "spec" not in _actions(build_steps(Intent("MyMod", spec=plan.Spec("x")), True, spec_exists=True))
    # An existing mod with no spec.md yet still gets one.
    assert _actions(build_steps(Intent("MyMod", spec=plan.Spec("x")), True)) == ["spec", "record"]


def test_execute_writes_spec_for_the_architect(env_ok, runs, tmp_path):
    rc = plan.main(["--mod", "MyMod", *SPEC_ARGS, "--execute"], project=tmp_path)
    assert rc == 0
    assert _skills_run(runs) == ["dayz-new-mod"]
    assert (tmp_path / "workspace" / "MyMod" / "spec.md").read_text(encoding="utf-8") == (
        "# MyMod spec\n\n"
        "## Goal\n\nAdds a craftable radio\n\n"
        "## Items\n\n- MyMod_Radio\n\n"
        "## Behaviors\n\n- A player can hold the radio\n- Using it plays a sound\n\n"
        "## Done checks\n\n- The radio spawns on the server\n"
    )


def test_print_only_shows_spec_step_but_writes_nothing(env_ok, runs, tmp_path, capsys):
    assert plan.main(["--mod", "MyMod", "--goal", "Adds a radio"], project=tmp_path) == 0
    assert r"Write workspace\MyMod\spec.md" in capsys.readouterr().out
    assert not (tmp_path / "workspace").exists()


def test_existing_spec_is_never_overwritten(monkeypatch, runs, tmp_path):
    monkeypatch.setattr(plan, "run_all", lambda: [])
    spec = tmp_path / "workspace" / "MyMod" / "spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("hand edited\n", encoding="utf-8")
    assert plan.main(["--mod", "MyMod", "--goal", "Something else", "--execute"], project=tmp_path) == 0
    assert spec.read_text(encoding="utf-8") == "hand edited\n"


def test_rerun_on_linked_import_never_writes_spec(monkeypatch, runs, tmp_path):
    # Re-running /dayz-init for a link-only import passes no --import-from, so
    # the plan must spot the link itself and keep out of the user's source.
    monkeypatch.setattr(plan, "run_all", lambda: [])
    monkeypatch.setattr(plan, "mod_exists", lambda project, mod: True)
    monkeypatch.setattr(plan, "is_link", lambda path: True)
    assert plan.main(["--mod", "MyMod", "--goal", "x", "--execute"], project=tmp_path) == 0
    assert not (tmp_path / "workspace" / "MyMod" / "spec.md").exists()
    assert "spec" not in _actions(build_steps(Intent("MyMod", spec=plan.Spec("x")), True, linked=True))
    # A --scaffold import may still write into its linked folder.
    scaffold = Intent("MyMod", source="C:/src", scaffold=True, spec=plan.Spec("x"))
    assert "spec" in _actions(build_steps(scaffold, True, linked=True))


def test_render_spec_keeps_entries_on_one_line_and_marks_empty_sections():
    text = plan.render_spec("M", plan.Spec("Adds\n a radio", items=["Radio\nwith  dial"]))
    assert "Adds a radio\n" in text
    assert "- Radio with dial\n" in text
    assert text.count("- None yet.") == 2


@pytest.mark.parametrize("argv, message", [
    (["--item", "Radio"], "--item, --behavior and --done-check need --goal"),
    (["--goal", "  "], "--goal is empty"),
    (["--import-from", "D:/src", "--no-scaffold", "--goal", "x"], "--goal does not apply with --no-scaffold"),
])
def test_spec_usage_errors(argv, message, capsys):
    with pytest.raises(SystemExit) as exc:
        plan.parse_args(["--mod", "M", *argv])
    assert exc.value.code == 2
    assert message in capsys.readouterr().err
