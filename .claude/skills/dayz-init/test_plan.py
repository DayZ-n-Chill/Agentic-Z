"""Tests for plan.py rendering. Execution is integration-tested separately."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intent import Intent  # noqa: E402
from plan import build_steps, render_plan, Step  # noqa: E402
from env_check import EnvIssue, Severity  # noqa: E402


def _intent(**overrides) -> Intent:
    base = dict(
        is_new=True,
        mod_name="MyMod",
        project_path=Path("G:/repos/MyMod"),
        add_server=True,
        server_map="chernarus",
        build_pbo=False,
        launch_diag=False,
        rag_choice="skip",
    )
    base.update(overrides)
    return Intent(**base)


class TestBuildSteps(unittest.TestCase):
    def test_required_steps_always_present(self):
        steps = build_steps(_intent(add_server=False), autofix_issues=[])
        kinds = [s.kind for s in steps]
        self.assertIn("scaffold", kinds)
        self.assertIn("junction_mod", kinds)
        self.assertIn("cache_project", kinds)

    def test_server_step_only_when_opted_in(self):
        without = build_steps(_intent(add_server=False), autofix_issues=[])
        with_srv = build_steps(_intent(add_server=True), autofix_issues=[])
        self.assertNotIn("stage_server", [s.kind for s in without])
        self.assertIn("stage_server", [s.kind for s in with_srv])

    def test_build_step_only_when_opted_in(self):
        without = build_steps(_intent(build_pbo=False), autofix_issues=[])
        with_b = build_steps(_intent(build_pbo=True), autofix_issues=[])
        self.assertNotIn("build_pbo", [s.kind for s in without])
        self.assertIn("build_pbo", [s.kind for s in with_b])

    def test_launch_step_only_when_opted_in(self):
        without = build_steps(_intent(launch_diag=False), autofix_issues=[])
        with_l = build_steps(
            _intent(launch_diag=True, build_pbo=True), autofix_issues=[]
        )
        self.assertNotIn("launch_diag", [s.kind for s in without])
        self.assertIn("launch_diag", [s.kind for s in with_l])

    def test_autofix_steps_prepended(self):
        issues = [
            EnvIssue("p_drive", Severity.AUTOFIX, "P: missing"),
            EnvIssue("mods_junction", Severity.AUTOFIX, "junction missing"),
        ]
        steps = build_steps(_intent(), autofix_issues=issues)
        # Autofix steps come before required steps
        first_two_kinds = [s.kind for s in steps[:2]]
        self.assertEqual(
            first_two_kinds, ["autofix:p_drive", "autofix:mods_junction"]
        )

    def test_import_uses_import_step_not_scaffold(self):
        steps = build_steps(_intent(is_new=False), autofix_issues=[])
        kinds = [s.kind for s in steps]
        self.assertIn("import_mod", kinds)
        self.assertNotIn("scaffold", kinds)


class TestRenderPlan(unittest.TestCase):
    def test_render_includes_each_step_label(self):
        steps = [
            Step(kind="scaffold", label="Scaffold MyMod at G:/repos/MyMod"),
            Step(kind="cache_project", label="Cache project root"),
        ]
        text = render_plan(steps)
        self.assertIn("Scaffold MyMod", text)
        self.assertIn("Cache project root", text)


if __name__ == "__main__":
    unittest.main()
