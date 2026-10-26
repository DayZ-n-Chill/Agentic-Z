"""Tests for the Step 1 and Step 2 entry points: check_setup.py and check_env.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_env  # noqa: E402
import check_setup  # noqa: E402
from env_check import EnvIssue, Severity  # noqa: E402


def _project(tmp_path: Path, cached: Path | None, mod: str | None = "MyMod", mod_dir: bool = True) -> Path:
    mem = tmp_path / ".claude" / "local-memory"
    mem.mkdir(parents=True)
    if cached is not None:
        (mem / "dayz-current-project.txt").write_text(str(cached), encoding="utf-8")
    if mod:
        (mem / "dayz-init-state.json").write_text(
            '{"last_intent": {"mod_name": "%s"}}' % mod, encoding="utf-8")
        if mod_dir:
            (tmp_path / "workspace" / mod).mkdir(parents=True)
    return tmp_path


def _setup_output(monkeypatch, capsys, project: Path) -> str:
    monkeypatch.setattr(check_setup, "PROJECT_DIR", project.resolve())
    monkeypatch.setattr(check_setup, "cached_project_root", lambda: _read_cache(project))
    assert check_setup.main() == 0
    return capsys.readouterr().out


def _read_cache(project: Path):
    import state
    return state.cached_project_root(project / ".claude" / "local-memory")


def test_setup_prints_root_when_cache_matches_and_mod_exists(monkeypatch, capsys, tmp_path):
    project = _project(tmp_path, cached=tmp_path)
    assert _setup_output(monkeypatch, capsys, project).strip() == str(tmp_path)


def test_setup_prints_nothing_when_cache_points_at_another_clone(monkeypatch, capsys, tmp_path):
    project = _project(tmp_path / "here", cached=tmp_path / "other")
    (tmp_path / "other").mkdir()
    assert _setup_output(monkeypatch, capsys, project) == ""


def test_setup_prints_nothing_without_a_cache(monkeypatch, capsys, tmp_path):
    project = _project(tmp_path, cached=None)
    assert _setup_output(monkeypatch, capsys, project) == ""


def test_setup_prints_nothing_when_active_mod_folder_is_gone(monkeypatch, capsys, tmp_path):
    project = _project(tmp_path, cached=tmp_path, mod_dir=False)
    assert _setup_output(monkeypatch, capsys, project) == ""


def test_setup_prints_nothing_without_an_active_mod(monkeypatch, capsys, tmp_path):
    project = _project(tmp_path, cached=tmp_path, mod=None)
    assert _setup_output(monkeypatch, capsys, project) == ""


def _env_output(monkeypatch, capsys, issues) -> list[str]:
    monkeypatch.setattr(check_env, "run_all", lambda: issues)
    assert check_env.main() == 0
    return capsys.readouterr().out.splitlines()


def test_env_ok_when_no_issues(monkeypatch, capsys):
    assert _env_output(monkeypatch, capsys, []) == ["OK"]


def test_env_hard_then_auto_lines(monkeypatch, capsys):
    issues = [
        EnvIssue(name="p_drive", severity=Severity.AUTOFIX, message="P: is not mounted"),
        EnvIssue(name="dayz_tools", severity=Severity.HARD_STOP, message="DayZ Tools missing",
                 fix_link="steam://install/830640"),
        EnvIssue(name="mods_junction", severity=Severity.HARD_STOP, message="P:\\Mods is a file"),
    ]
    assert _env_output(monkeypatch, capsys, issues) == [
        "HARD dayz_tools DayZ Tools missing steam://install/830640",
        "HARD mods_junction P:\\Mods is a file",
        "AUTO p_drive P: is not mounted",
    ]
